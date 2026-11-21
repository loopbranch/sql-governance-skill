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


def split_statements(sql: str) -> list[tuple[int, str]]:
    """Split on semicolons outside strings, quoted identifiers, dollar strings, and comments."""
    result: list[tuple[int, str]] = []
    start, line, start_line, index = 0, 1, 1, 0
    quote: str | None = None
    dollar: str | None = None
    block_comment = False
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
        if block_comment:
            if pair == "*/":
                block_comment = False
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
            elif char == "\\" and quote == "'":
                index += 2
                continue
            index += 1
            continue
        if pair == "/*":
            block_comment = True
            index += 2
            continue
        if pair == "--" or char == "#":
            line_comment = True
            index += 2 if pair == "--" else 1
            continue
        if char in {"'", '"', "`"}:
            quote = char
            index += 1
            continue
        if char == "$":
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


def mask_literals_and_comments(sql: str) -> str:
    """Replace literal/comment contents with spaces while preserving layout and identifiers."""
    chars = list(sql)
    index = 0
    while index < len(chars):
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            end = len(sql) if end < 0 else end + 2
            for pos in range(index, end):
                if chars[pos] != "\n": chars[pos] = " "
            index = end
            continue
        if sql.startswith("--", index) or chars[index] == "#":
            end = sql.find("\n", index)
            end = len(sql) if end < 0 else end
            for pos in range(index, end): chars[pos] = " "
            index = end
            continue
        if chars[index] == "'":
            end = index + 1
            while end < len(chars):
                if chars[end] == "'":
                    if end + 1 < len(chars) and chars[end + 1] == "'":
                        end += 2
                        continue
                    end += 1
                    break
                if chars[end] == "\\": end += 1
                end += 1
            for pos in range(index, min(end, len(chars))):
                if chars[pos] != "\n": chars[pos] = " "
            index = end
            continue
        if chars[index] == "$":
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
    mysql = bool(re.search(r"`|\bauto_increment\b|\bengine\s*=|\bdefault\s+charset\b|\bunsigned\b", masked))
    postgres = bool(re.search(r"::[a-z]|\btimestamptz\b|\bjsonb\b|\bconcurrently\b|\bbigserial\b|\breturning\b", masked))
    if mysql == postgres:
        return None
    return "mysql" if mysql else "postgresql"


def compact(statement: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", statement).strip()
    return value if len(value) <= limit else value[:limit - 3] + "..."


def add(findings: list[Finding], file: str, line: int, rule_id: str, dialect: str, message: str, statement: str, gate: str = "block") -> None:
    findings.append(Finding(file, line, rule_id, gate, dialect, message, compact(statement)))


def inspect_statement(file: str, line: int, statement: str, dialect: str) -> list[Finding]:
    findings: list[Finding] = []
    masked = mask_literals_and_comments(statement)
    normalized = re.sub(r"\s+", " ", masked).strip().lower()

    if re.search(r"\bselect\s+(?:(?:all|distinct)\s+)?(?:[a-z0-9_]+\.)?\*(?:\s|,|$)", normalized):
        add(findings, file, line, "G.SEL.12", dialect, "SELECT * requires a documented catalog exception", statement)
    if re.search(r"\b(?:cross|full)\s+join\b", normalized):
        add(findings, file, line, "G.SEL.08", dialect, "CROSS JOIN and FULL JOIN are prohibited by the shared profile", statement)

    dml = re.search(r"\b(update|delete\s+from)\b", normalized)
    if dml:
        tail = normalized[dml.end():]
        where_match = re.search(r"\bwhere\b(.+)$", tail)
        invalid_where = where_match is None or re.fullmatch(r"\s*(?:1\s*=\s*1|true)(?:\s+.*)?", where_match.group(1))
        if invalid_where:
            add(findings, file, line, "G.UPD.01" if dml.group(1) == "update" else "G.DEL.01", dialect, "UPDATE/DELETE must have a non-trivial WHERE clause", statement)
    if re.search(r"\bupdate\b.+\border\s+by\b", normalized):
        add(findings, file, line, "G.UPD.02", dialect, "UPDATE ORDER BY is prohibited", statement)
    if re.search(r"\bupdate\b.+\blimit\b", normalized):
        add(findings, file, line, "G.UPD.03", dialect, "UPDATE LIMIT is prohibited; use a stable-key batch design", statement)

    if re.search(r"\bforeign\s+key\b|\breferences\s+[a-z0-9_`\"]+\s*\(", normalized):
        add(findings, file, line, "G.TAB.04", dialect, "Foreign keys are prohibited", statement)
    if re.match(r"^create\s+table\b", normalized) and not re.match(r"^create\s+table\s+if\s+not\s+exists\b", normalized):
        add(findings, file, line, "G.UPG.10", dialect, "CREATE TABLE must use IF NOT EXISTS", statement)
    if re.match(r"^create\s+table\b", normalized) and not re.search(r"\bprimary\s+key\b", normalized):
        add(findings, file, line, "G.TAB.16", dialect, "Every table must define a primary key", statement)
    if re.match(r"^drop\s+table\b", normalized) and not re.match(r"^drop\s+table\s+if\s+exists\b", normalized):
        add(findings, file, line, "G.UPG.11", dialect, "DROP TABLE must use IF EXISTS", statement)
    if re.match(r"^alter\s+table\b", normalized):
        if re.search(r"\bdrop\s+(?:column\s+)?[a-z0-9_`\"]+", normalized):
            add(findings, file, line, "G.UPG.03", dialect, "Dropping columns is prohibited", statement)
        if re.search(r"\b(?:modify|change)\s+(?:column\s+)?", normalized):
            add(findings, file, line, "G.UPG.05", dialect, "Direct column type modification requires a compatible expand-contract plan", statement)
        if re.search(r"\badd\s+(?:column\s+)?[a-z0-9_`\"]+\s+[^,;]+\bnot\s+null\b", normalized):
            add(findings, file, line, "G.UPG.07", dialect, "Adding a NOT NULL column directly is prohibited", statement)
    if re.match(r"^insert\s+into\b", normalized) and not re.match(r"^insert\s+into\s+[a-z0-9_.`\"]+\s*\(", normalized):
        add(findings, file, line, "G.INS.01", dialect, "INSERT must list target columns", statement)
    if re.search(r"\bxa\s+(?:start|begin|end|prepare|commit|rollback)\b", normalized):
        add(findings, file, line, "G.TXN.07", dialect, "XA transactions are prohibited", statement)
    if re.search(r"\bset\s+(?:(?:session|global)\s+)?transaction\s+isolation\s+level\b", normalized):
        add(findings, file, line, "G.TXN.01", dialect, "Explicit transaction isolation levels are prohibited", statement)

    if dialect == "mysql":
        if re.search(r"\bauto_increment\b", normalized):
            add(findings, file, line, "MYSQL-PK-001", dialect, "AUTO_INCREMENT primary keys are prohibited", statement)
        engine = re.search(r"\bengine\s*=\s*([a-z0-9_]+)", normalized)
        if engine and engine.group(1) != "innodb":
            add(findings, file, line, "MYSQL-TAB-001", dialect, "MySQL tables must use InnoDB", statement)
        charset = re.search(r"\b(?:default\s+)?(?:character\s+set|charset)\s*=?\s*([a-z0-9_]+)", normalized)
        if charset and charset.group(1) != "utf8mb4":
            add(findings, file, line, "MYSQL-ENC-001", dialect, "MySQL character set must be utf8mb4", statement)
    else:
        if re.search(r"\bengine\s*=|\b(?:default\s+)?charset\s*=|\bauto_increment\b|`", normalized):
            add(findings, file, line, "POSTGRESQL-TAB-001", dialect, "MySQL-only table syntax is invalid in PostgreSQL", statement)
        if re.search(r"\b(?:smallserial|serial|bigserial)\b[^,]*\bprimary\s+key\b|\bgenerated\s+(?:always|by\s+default)\s+as\s+identity\b[^,]*\bprimary\s+key\b", normalized):
            add(findings, file, line, "POSTGRESQL-PK-001", dialect, "Serial/identity distributed primary keys are prohibited", statement)
        if re.match(r"^create\s+(?:unique\s+)?index\b", normalized) and not re.match(r"^create\s+(?:unique\s+)?index\s+concurrently\b", normalized):
            add(findings, file, line, "POSTGRESQL-DDL-001", dialect, "Production index creation requires CONCURRENTLY or explicit manual exception", statement)
    return findings


def inspect(file: str, sql: str, requested_dialect: str) -> tuple[str, list[Finding]]:
    dialect = detect_dialect(sql) if requested_dialect == "auto" else requested_dialect
    if dialect is None:
        raise ValueError(f"{file}: cannot determine SQL dialect; pass --dialect mysql or --dialect postgresql")
    findings: list[Finding] = []
    for line, statement in split_statements(sql):
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
        print(json.dumps({"result": "fail" if findings else "pass", "dialects": dialects, "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    elif findings:
        for item in findings: print(f"{item.file}:{item.line}: {item.gate.upper()} {item.rule_id} [{item.dialect}] {item.message}\n  {item.snippet}")
    else:
        print(f"PASS: no high-confidence Block violations found ({', '.join(sorted(set(dialects.values())))})")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
