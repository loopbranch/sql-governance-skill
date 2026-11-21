#!/usr/bin/env python3
"""Dependency-free high-confidence SQL gate for MySQL and PostgreSQL.

The CLI covers only catalog rules that can be decided without a live schema.
Hybrid/manual rules remain mandatory review work in SKILL.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    rule_id: str
    gate: str
    dialect: str
    message: str
    snippet: str


COMMON_GUARD_RULES = {
    "G.DEL.01", "G.INS.01", "G.SEL.12", "G.TAB.04",
    "G.TAB.16", "G.TXN.01", "G.UPD.01", "G.UPG.03", "G.UPG.10",
    "G.UPG.11",
}
DIALECT_GUARD_RULES = {
    "mysql": {
        "MYSQL-ENC-001", "MYSQL-PK-001", "MYSQL-SEL-008", "MYSQL-TAB-001",
        "MYSQL-TXN-007", "MYSQL-UPD-001", "MYSQL-UPD-002", "MYSQL-UPG-005",
        "MYSQL-UPG-007", "MYSQL-UPG-008",
    },
    "postgresql": {
        "POSTGRESQL-PK-001", "POSTGRESQL-SEL-008", "POSTGRESQL-TAB-001",
        "POSTGRESQL-TXN-007", "POSTGRESQL-UPD-001", "POSTGRESQL-UPD-002",
        "POSTGRESQL-UPG-005", "POSTGRESQL-UPG-007", "POSTGRESQL-UPG-008",
    },
}


def starts_line_comment(sql: str, index: int, dialect: str | None) -> bool:
    """Return whether the token at index starts a dialect-valid line comment."""
    if sql[index:index + 2] != "--":
        return sql[index:index + 1] == "#" and dialect == "mysql"
    if dialect != "mysql":
        return True
    next_index = index + 2
    return next_index >= len(sql) or sql[next_index].isspace() or ord(sql[next_index]) < 32


def quote_uses_backslash(sql: str, index: int, dialect: str | None, quote: str) -> bool:
    """Model server defaults: MySQL escapes backslashes; PostgreSQL only does so in E''."""
    if dialect == "mysql":
        return True
    return dialect == "postgresql" and quote == "'" and index > 0 and sql[index - 1:index].lower() == "e"


def split_statements(sql: str, dialect: str | None = None) -> list[tuple[int, str]]:
    """Split on semicolons outside strings, quoted identifiers, dollar strings, and comments."""
    result: list[tuple[int, str]] = []
    start, line, start_line, index = 0, 1, 1, 0
    quote: str | None = None
    dollar: str | None = None
    block_comment_depth = 0
    line_comment = False
    while index < len(sql):
        char = sql[index]
        pair = sql[index:index + 2]
        if char == "\n":
            line += 1
            line_comment = False
        if line_comment:
            index += 1
            continue
        if block_comment_depth:
            if pair == "/*" and dialect == "postgresql":
                block_comment_depth += 1
                index += 2
            elif pair == "*/":
                block_comment_depth -= 1
                index += 2
            else:
                index += 1
            continue
        if dollar:
            if sql.startswith(dollar, index):
                index += len(dollar)
                dollar = None
            else:
                index += 1
            continue
        if quote:
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    index += 2
                    continue
                quote = None
            elif char == "\\" and quote_uses_backslash(sql, quote_start, dialect, quote):
                index += 2
                continue
            index += 1
            continue
        if pair == "/*":
            block_comment_depth = 1
            index += 2
            continue
        if starts_line_comment(sql, index, dialect):
            line_comment = True
            index += 2 if pair == "--" else 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            quote_start = index
            index += 1
            continue
        if char == "$" and dialect == "postgresql":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
            if match:
                dollar = match.group(0)
                index += len(dollar)
                continue
        if char == ";":
            statement = sql[start:index].strip()
            if statement:
                leading = len(sql[start:index]) - len(sql[start:index].lstrip())
                result.append((start_line + sql[start:start + leading].count("\n"), statement))
            start, start_line = index + 1, line
        index += 1
    statement = sql[start:].strip()
    if statement:
        leading = len(sql[start:]) - len(sql[start:].lstrip())
        result.append((start_line + sql[start:start + leading].count("\n"), statement))
    return result


def mask_literals_and_comments(sql: str, dialect: str | None = None) -> str:
    """Replace literal/comment contents with spaces while preserving layout and identifiers."""
    chars = list(sql)
    index = 0
    while index < len(chars):
        if sql.startswith("/*", index):
            depth, end = 1, index + 2
            while end < len(sql) and depth:
                if sql.startswith("/*", end) and dialect == "postgresql":
                    depth += 1; end += 2
                elif sql.startswith("*/", end):
                    depth -= 1; end += 2
                else:
                    end += 1
            for pos in range(index, end):
                if chars[pos] != "\n": chars[pos] = " "
            index = end
            continue
        if starts_line_comment(sql, index, dialect):
            end = sql.find("\n", index)
            end = len(sql) if end < 0 else end
            for pos in range(index, end): chars[pos] = " "
            index = end
            continue
        if chars[index] in {"'", '"'}:
            quote = chars[index]
            quote_start = index
            end = index + 1
            while end < len(chars):
                if chars[end] == quote:
                    if end + 1 < len(chars) and chars[end + 1] == quote:
                        end += 2
                        continue
                    end += 1
                    break
                if chars[end] == "\\" and quote_uses_backslash(sql, quote_start, dialect, quote): end += 1
                end += 1
            for pos in range(index, min(end, len(chars))):
                if chars[pos] != "\n": chars[pos] = " "
            index = end
            continue
        if chars[index] == "$" and dialect in {None, "postgresql"}:
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
            if match:
                tag = match.group(0); end = sql.find(tag, index + len(tag)); end = len(sql) if end < 0 else end + len(tag)
                for pos in range(index, end):
                    if chars[pos] != "\n": chars[pos] = " "
                index = end
                continue
        index += 1
    return "".join(chars)


def detect_dialect(sql: str) -> str | None:
    masked = mask_literals_and_comments(sql).lower()
    mysql = bool(re.search(
        r"`|\bauto_increment\b|\bengine\s*=|\bdefault\s+charset\b|"
        r"\b(?:tinyint|smallint|mediumint|int|integer|bigint|decimal|numeric|float|double)\b[^,)]*\bunsigned\b",
        masked,
    ))
    postgres = bool(re.search(
        r"::[a-z]|\bconcurrently\b|\breturning\b|"
        r"(?:\(|,)\s*[a-z_][a-z0-9_$]*\s+(?:timestamptz|jsonb|uuid|smallserial|serial|bigserial)\b",
        masked,
    ))
    if mysql == postgres:
        return None
    return "mysql" if mysql else "postgresql"


def compact(statement: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", statement).strip()
    return value if len(value) <= limit else value[:limit - 3] + "..."


def add(findings: list[Finding], file: str, line: int, rule_id: str, dialect: str, message: str, statement: str, gate: str = "block") -> None:
    findings.append(Finding(file, line, rule_id, gate, dialect, message, compact(statement)))


def top_level_words(sql: str) -> list[tuple[str, int, int]]:
    """Return lowercase word tokens outside parentheses, with source offsets."""
    words: list[tuple[str, int, int]] = []
    depth, index = 0, 0
    while index < len(sql):
        char = sql[index]
        if char in {'"', '`'}:
            quote = char
            index += 1
            while index < len(sql):
                if sql[index] == quote:
                    if index + 1 < len(sql) and sql[index + 1] == quote:
                        index += 2
                        continue
                    index += 1
                    break
                index += 1
            continue
        if char == "(":
            depth += 1
            index += 1
            continue
        if char == ")":
            depth = max(0, depth - 1)
            index += 1
            continue
        match = re.match(r"[a-z_][a-z0-9_$]*", sql[index:], re.IGNORECASE)
        if match:
            end = index + len(match.group(0))
            if depth == 0:
                words.append((match.group(0).lower(), index, end))
            index = end
            continue
        index += 1
    return words


def main_statement(words: list[tuple[str, int, int]]) -> tuple[int, str, int, int] | None:
    for index, (word, start, end) in enumerate(words):
        if word in {"select", "update", "delete", "insert", "create", "alter", "drop"}:
            return index, word, start, end
    return None


def is_trivial_where(expression: str) -> bool:
    value = re.sub(r"\s+", "", expression).lower()
    while value.startswith("(") and value.endswith(")"):
        value = value[1:-1]
    return value in {"true", "1=1"}


CREATE_TABLE_RE = re.compile(
    r"^create\s+(?:(?:global|local)\s+)?(?:(?:temporary|temp|unlogged)\s+)?table\b",
    re.IGNORECASE,
)


def table_segments(normalized: str) -> list[str]:
    """Split a CREATE TABLE body on top-level commas."""
    start = normalized.find("(")
    if start < 0:
        return []
    depth, segment_start = 0, start + 1
    segments: list[str] = []
    for index in range(start + 1, len(normalized)):
        char = normalized[index]
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                segments.append(normalized[segment_start:index].strip())
                break
            depth -= 1
        elif char == "," and depth == 0:
            segments.append(normalized[segment_start:index].strip())
            segment_start = index + 1
    return [segment for segment in segments if segment]


def postgresql_serial_pk(normalized: str) -> bool:
    banned_columns: set[str] = set()
    primary_columns: set[str] = set()
    for segment in table_segments(normalized):
        table_pk = re.search(r"\bprimary\s+key\s*\(([^)]*)\)", segment)
        if table_pk and re.match(r"^(?:constraint\s+\S+\s+)?primary\s+key\b", segment):
            primary_columns.update(re.findall(r"[a-z_][a-z0-9_$]*", table_pk.group(1)))
            continue
        column = re.match(r'^("[^"]+"|[a-z_][a-z0-9_$]*)\s+(.+)$', segment)
        if not column:
            continue
        name, definition = column.group(1).strip('"').lower(), column.group(2)
        if re.search(r"\b(?:smallserial|serial|bigserial)\b|\bgenerated\s+(?:always|by\s+default)\s+as\s+identity\b", definition):
            banned_columns.add(name)
            if re.search(r"\bprimary\s+key\b", definition):
                primary_columns.add(name)
    return bool(banned_columns & primary_columns)


def primary_key_definitions(normalized: str) -> list[str]:
    """Return column definitions participating in inline or table-level primary keys."""
    columns: dict[str, str] = {}
    primary_columns: set[str] = set()
    for segment in table_segments(normalized):
        table_pk = re.search(r"\bprimary\s+key\s*\(([^)]*)\)", segment)
        if table_pk and re.match(r"^(?:constraint\s+\S+\s+)?primary\s+key\b", segment):
            primary_columns.update(re.findall(r"[a-z_][a-z0-9_$]*", table_pk.group(1)))
            continue
        column = re.match(r'^(?:`([^`]+)`|"([^"]+)"|([a-z_][a-z0-9_$]*))\s+(.+)$', segment)
        if not column:
            continue
        name = next(value for value in column.groups()[:3] if value).lower()
        definition = column.group(4)
        columns[name] = definition
        if re.search(r"\bprimary\s+key\b", definition):
            primary_columns.add(name)
    return [columns[name] for name in primary_columns if name in columns]


def cte_bodies(normalized: str) -> list[tuple[int, str]]:
    """Extract WITH item bodies after AS, including nested PostgreSQL CTEs."""
    bodies: list[tuple[int, str]] = []
    for match in re.finditer(r"\bas\s*\(", normalized):
        start = match.end()
        depth, index = 1, start
        while index < len(normalized) and depth:
            if normalized[index] == "(":
                depth += 1
            elif normalized[index] == ")":
                depth -= 1
            index += 1
        if depth == 0:
            bodies.append((start, normalized[start:index - 1].strip()))
    return bodies


def inspect_statement(file: str, line: int, statement: str, dialect: str) -> list[Finding]:
    findings: list[Finding] = []
    masked = mask_literals_and_comments(statement, dialect)
    normalized = re.sub(r"\s+", " ", masked).strip().lower()
    words = top_level_words(normalized)
    main = main_statement(words)

    if dialect == "postgresql" and normalized.startswith("with "):
        for offset, body in cte_bodies(normalized):
            if re.match(r"^(?:with\b[\s\S]*?\b)?(?:insert|update|delete)\b", body):
                body_line = line + normalized[:offset].count("\n")
                findings.extend(inspect_statement(file, body_line, body, dialect))

    if re.search(r"\bselect\s+(?:(?:all|distinct)\s+)?(?:[a-z0-9_]+\.)?\*(?:\s|,|$)", normalized):
        add(findings, file, line, "G.SEL.12", dialect, "SELECT * requires a documented catalog exception", statement)
    if re.search(r"\b(?:cross|full(?:\s+outer)?)\s+join\b", normalized):
        add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-SEL-008", dialect, "CROSS JOIN and FULL JOIN require dialect-specific remediation", statement)

    if main and main[1] in {"update", "delete"}:
        main_index, dml_kind, _, _ = main
        tail_words = words[main_index + 1:]
        where_token = next((token for token in tail_words if token[0] == "where"), None)
        where_expression = ""
        if where_token:
            end = len(normalized)
            for word, start, _ in tail_words:
                if start > where_token[1] and word in {"order", "limit", "returning"}:
                    end = start
                    break
            where_expression = normalized[where_token[2]:end]
        invalid_where = where_token is None or is_trivial_where(where_expression)
        if invalid_where:
            add(findings, file, line, "G.UPD.01" if dml_kind == "update" else "G.DEL.01", dialect, "UPDATE/DELETE must have a non-trivial WHERE clause", statement)
        if dml_kind == "update":
            tail_names = [word for word, _, _ in tail_words]
            if any(tail_names[index:index + 2] == ["order", "by"] for index in range(len(tail_names) - 1)):
                add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPD-002", dialect, "Top-level UPDATE ORDER BY is prohibited", statement)
            if "limit" in tail_names:
                add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPD-001", dialect, "Top-level UPDATE LIMIT is prohibited; use a stable-key batch design", statement)

    if re.search(r"\bforeign\s+key\b|\breferences\s+[a-z0-9_`\"]+\s*\(", normalized):
        add(findings, file, line, "G.TAB.04", dialect, "Foreign keys are prohibited", statement)
    create_table = CREATE_TABLE_RE.match(normalized)
    if create_table:
        after_table = normalized[create_table.end():].lstrip()
        if not re.match(r"^if\s+not\s+exists\b", after_table):
            add(findings, file, line, "G.UPG.10", dialect, "CREATE TABLE must use IF NOT EXISTS", statement)
        if not re.search(r"\bprimary\s+key\b", normalized):
            add(findings, file, line, "G.TAB.16", dialect, "Every table must define a primary key", statement)
    if re.match(r"^drop\s+table\b", normalized) and not re.match(r"^drop\s+table\s+if\s+exists\b", normalized):
        add(findings, file, line, "G.UPG.11", dialect, "DROP TABLE must use IF EXISTS", statement)
    if re.match(r"^alter\s+table\b", normalized):
        if re.search(r"\bdrop\s+column\s+(?:if\s+exists\s+)?[a-z0-9_`\"]+", normalized):
            add(findings, file, line, "G.UPG.03", dialect, "Dropping columns is prohibited", statement)
        if re.search(r"\b(?:modify|change)\s+(?:column\s+)?|\balter\s+column\s+[a-z0-9_\"]+\s+(?:set\s+data\s+)?type\b", normalized):
            add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPG-005", dialect, "Direct column type modification requires a compatible expand-contract plan", statement)
        if re.search(r"\balter\s+column\s+[a-z0-9_\"]+\s+set\s+not\s+null\b", normalized):
            add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPG-008", dialect, "Changing an existing column to NOT NULL is prohibited", statement)
        if dialect == "mysql" and re.search(r"\b(?:modify|change)\s+(?:column\s+)?[a-z0-9_`]+\s+[^,;]+\bnot\s+null\b", normalized):
            add(findings, file, line, "MYSQL-UPG-008", dialect, "Changing an existing column to NOT NULL is prohibited", statement)
        if re.search(r"\badd\s+(?:column\s+)?(?!constraint\b)[a-z0-9_`\"]+\s+[^,;]+\bnot\s+null\b", normalized):
            add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPG-007", dialect, "Adding a NOT NULL column directly is prohibited", statement)
    if main and main[1] == "insert":
        insert_sql = normalized[main[2]:]
        if not re.match(r"^insert\s+into\s+[a-z0-9_.`\"]+\s*\(", insert_sql):
            add(findings, file, line, "G.INS.01", dialect, "INSERT must list target columns", statement)
    if re.search(r"\bxa\s+(?:start|begin|end|prepare|commit|rollback)\b", normalized):
        add(findings, file, line, "MYSQL-TXN-007" if dialect == "mysql" else "POSTGRESQL-TXN-007", dialect, "Distributed transactions require explicit approval", statement)
    if dialect == "postgresql" and re.search(r"\b(?:prepare\s+transaction|commit\s+prepared|rollback\s+prepared)\b", normalized):
        add(findings, file, line, "POSTGRESQL-TXN-007", dialect, "Prepared transactions require explicit approval", statement)
    if re.search(r"\bset\s+(?:(?:session|global)\s+)?transaction\s+isolation\s+level\b", normalized):
        add(findings, file, line, "G.TXN.01", dialect, "Explicit transaction isolation levels are prohibited", statement)

    if dialect == "mysql":
        if re.search(r"\bauto_increment\b", normalized):
            add(findings, file, line, "MYSQL-PK-001", dialect, "AUTO_INCREMENT primary keys are prohibited", statement)
        if create_table and any(re.search(r"\b(?:char|varchar)\s*\(\s*3[26]\s*\)", definition) for definition in primary_key_definitions(normalized)):
            add(findings, file, line, "MYSQL-PK-001", dialect, "Text UUID primary keys must use BINARY(16)", statement)
        engine = re.search(r"\bengine\s*=\s*([a-z0-9_]+)", normalized)
        if engine and engine.group(1) != "innodb":
            add(findings, file, line, "MYSQL-TAB-001", dialect, "MySQL tables must use InnoDB", statement)
        charsets = re.findall(r"\b(?:default\s+)?(?:character\s+set|charset)\s*=?\s*([a-z0-9_]+)", normalized)
        if any(charset != "utf8mb4" for charset in charsets):
            add(findings, file, line, "MYSQL-ENC-001", dialect, "MySQL character set must be utf8mb4", statement)
    else:
        if re.search(r"\bengine\s*=|\b(?:default\s+)?charset\s*=|\bauto_increment\b|`", normalized):
            add(findings, file, line, "POSTGRESQL-TAB-001", dialect, "MySQL-only table syntax is invalid in PostgreSQL", statement)
        if create_table and postgresql_serial_pk(normalized):
            add(findings, file, line, "POSTGRESQL-PK-001", dialect, "Serial/identity distributed primary keys are prohibited", statement)
        if create_table and any(re.search(r"\b(?:bytea\b|binary\s*\(\s*16\s*\)|(?:char|varchar)\s*\(\s*3[26]\s*\))", definition) for definition in primary_key_definitions(normalized)):
            add(findings, file, line, "POSTGRESQL-PK-001", dialect, "Distributed UUID primary keys must use native uuid", statement)
    return findings


def inspect(file: str, sql: str, requested_dialect: str) -> tuple[str, list[Finding]]:
    dialect = detect_dialect(sql) if requested_dialect == "auto" else requested_dialect
    if dialect is None:
        raise ValueError(f"{file}: cannot determine SQL dialect; pass --dialect mysql or --dialect postgresql")
    findings: list[Finding] = []
    for line, statement in split_statements(sql, dialect):
        findings.extend(inspect_statement(file, line, statement, dialect))
    return dialect, findings


def read_inputs(paths: list[str]) -> list[tuple[str, str]]:
    inputs = []
    for raw_path in paths:
        if raw_path == "-": inputs.append(("<stdin>", sys.stdin.read())); continue
        path = Path(raw_path)
        if not path.is_file(): raise ValueError(f"not a file: {path}")
        inputs.append((str(path), path.read_text(encoding="utf-8")))
    return inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run high-confidence MySQL/PostgreSQL Block rules")
    parser.add_argument("paths", nargs="+", help="SQL files, or - for stdin")
    parser.add_argument("--dialect", choices=("auto", "mysql", "postgresql"), default="auto")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args(); findings: list[Finding] = []; dialects: dict[str, str] = {}
    try:
        for file, sql in read_inputs(args.paths):
            dialect, current = inspect(file, sql, args.dialect); dialects[file] = dialect; findings.extend(current)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr); return 2
    if args.format == "json":
        checked_rules = sorted(COMMON_GUARD_RULES | set().union(*(DIALECT_GUARD_RULES[dialect] for dialect in set(dialects.values()))))
        print(json.dumps({"result": "fail" if findings else "pass", "dialects": dialects, "checked_rules": checked_rules, "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    elif findings:
        for item in findings: print(f"{item.file}:{item.line}: {item.gate.upper()} {item.rule_id} [{item.dialect}] {item.message}\n  {item.snippet}")
    else:
        print(f"PASS: no high-confidence Block violations found ({', '.join(sorted(set(dialects.values())))})")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
