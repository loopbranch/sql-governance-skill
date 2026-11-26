#!/usr/bin/env python3
"""Dependency-free high-confidence SQL gate for MySQL and PostgreSQL.

The CLI runs static checks and screens hybrid rules with executable branches.
Rules that depend on schema, business semantics or approvals still need review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from functools import lru_cache
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


COMMON_GUARD_RULES: set[str] = set()
ARCHIVE_REPLAY_RULE = "POSTGRESQL-UPG-012"
DIALECT_GUARD_RULES = {
    "mysql": {
        "MYSQL-ENC-001", "MYSQL-PK-001", "MYSQL-SEL-008", "MYSQL-TAB-001",
        "MYSQL-TXN-007", "MYSQL-UPD-001", "MYSQL-UPD-002", "MYSQL-UPG-005",
        "MYSQL-UPG-007", "MYSQL-UPG-008", "MYSQL-GDEL-001", "MYSQL-GINS-001",
        "MYSQL-GSEL-012", "MYSQL-GTAB-004", "MYSQL-GTAB-016", "MYSQL-GTXN-001",
        "MYSQL-GUPD-001", "MYSQL-GUPG-003", "MYSQL-GUPG-010", "MYSQL-GUPG-011",
    },
    "postgresql": {
        "POSTGRESQL-PK-001", "POSTGRESQL-SEL-008", "POSTGRESQL-TAB-001",
        "POSTGRESQL-TXN-007", "POSTGRESQL-UPD-001", "POSTGRESQL-UPD-002",
        "POSTGRESQL-UPG-005", "POSTGRESQL-UPG-007", "POSTGRESQL-UPG-008",
        "POSTGRESQL-GDEL-001", "POSTGRESQL-GINS-001", "POSTGRESQL-GSEL-012",
        "POSTGRESQL-GTAB-004", "POSTGRESQL-GTAB-016", "POSTGRESQL-GTXN-001",
        "POSTGRESQL-GUPD-001", "POSTGRESQL-GUPG-003", "POSTGRESQL-GUPG-010",
        "POSTGRESQL-GUPG-011", ARCHIVE_REPLAY_RULE,
    },
}


def split_rule_id(dialect: str, source_id: str) -> str:
    """Map a G.DOMAIN.NN source to its generated dialect rule ID."""
    _, domain, number = source_id.split(".")
    prefix = "MYSQL" if dialect == "mysql" else "POSTGRESQL"
    return f"{prefix}-G{domain}-{int(number):03d}"


def starts_line_comment(sql: str, index: int, dialect: str | None) -> bool:
    """Return whether the token at index starts a dialect-valid line comment."""
    if sql[index:index + 2] != "--":
        return sql[index:index + 1] == "#" and dialect == "mysql"
    if dialect != "mysql":
        return True
    next_index = index + 2
    return next_index >= len(sql) or sql[next_index].isspace() or ord(sql[next_index]) < 32


def quote_uses_backslash(sql: str, index: int, dialect: str | None, quote: str, mysql_no_backslash_escapes: bool) -> bool:
    """Model server defaults: MySQL escapes backslashes; PostgreSQL only does so in E''."""
    if dialect == "mysql":
        return quote != "`" and not mysql_no_backslash_escapes
    return (
        dialect == "postgresql" and quote == "'" and index > 0
        and sql[index - 1].lower() == "e"
        and (index == 1 or not re.match(r"[\w$]", sql[index - 2]))
    )


def split_statements(sql: str, dialect: str | None = None, *, mysql_no_backslash_escapes: bool = False) -> list[tuple[int, str]]:
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
            elif char == "\\" and quote_uses_backslash(sql, quote_start, dialect, quote, mysql_no_backslash_escapes):
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


def mask_literals_and_comments(
    sql: str, dialect: str | None = None, *, mysql_no_backslash_escapes: bool = False,
    preserve_identifiers: bool = False, mark_strings: bool = False,
) -> str:
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
        if chars[index] in {"'", '"', "`"}:
            quote = chars[index]
            quote_start = index
            end = index + 1
            closed = False
            while end < len(chars):
                if chars[end] == quote:
                    if end + 1 < len(chars) and chars[end + 1] == quote:
                        end += 2
                        continue
                    end += 1
                    closed = True
                    break
                if chars[end] == "\\" and quote_uses_backslash(sql, quote_start, dialect, quote, mysql_no_backslash_escapes): end += 1
                end += 1
            identifier = quote == "`" or (quote == '"' and dialect == "postgresql")
            if quote != "`" and not (identifier and preserve_identifiers):
                for pos in range(index, min(end, len(chars))):
                    if chars[pos] != "\n":
                        chars[pos] = " "
                if mark_strings and quote == "'" and closed:
                    chars[index] = "?"
            index = end
            continue
        if chars[index] == "$" and dialect in {None, "postgresql"}:
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
            if match:
                tag = match.group(0)
                closing = sql.find(tag, index + len(tag))
                end = len(sql) if closing < 0 else closing + len(tag)
                for pos in range(index, end):
                    if chars[pos] != "\n": chars[pos] = " "
                if mark_strings and closing >= 0:
                    chars[index] = "?"
                index = end
                continue
        index += 1
    return "".join(chars)


def detect_dialect(sql: str, *, mysql_no_backslash_escapes: bool = False) -> str | None:
    evidence = set()
    for dialect in DIALECT_GUARD_RULES:
        options = {"mysql_no_backslash_escapes": mysql_no_backslash_escapes}
        for _, statement in split_statements(sql, dialect, **options):
            masked = mask_literals_and_comments(statement, dialect, **options).strip().lower()
            ddl = mask_literals_and_comments(statement, dialect, preserve_identifiers=True, **options).strip().lower()
            create_table = CREATE_TABLE_RE.match(ddl)
            columns = table_segments(ddl) if create_table else []
            if dialect == "mysql":
                if "`" in masked or has_mysql_table_options(ddl):
                    evidence.add(dialect)
            else:
                pg_column = any(re.match(
                    rf"{IDENTIFIER}\s+(?:timestamptz|jsonb|uuid|smallserial|serial|bigserial)\b",
                    column,
                ) for column in columns)
                if pg_column or re.search(r"::\s*[a-z_]", masked) or re.match(
                    r"^create\s+(?:unique\s+)?index\s+concurrently\b", masked,
                ):
                    evidence.add(dialect)
    return next(iter(evidence)) if len(evidence) == 1 else None


def compact(statement: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", statement).strip()
    return value if len(value) <= limit else value[:limit - 3] + "..."


@lru_cache(maxsize=2)
def rule_metadata(dialect: str) -> dict[str, dict]:
    path = Path(__file__).resolve().parents[1] / "rules" / f"{dialect}.json"
    return {rule["id"]: rule for rule in json.loads(path.read_text(encoding="utf-8"))["rules"]}


def add(findings: list[Finding], file: str, line: int, rule_id: str, dialect: str, message: str, statement: str, *, review: bool = False) -> None:
    rule = rule_metadata(dialect)[rule_id]
    gate = rule["check"]["review_gate"] if review else rule["gate"]
    findings.append(Finding(file, line, rule_id, gate, dialect, message, compact(statement)))


# PostgreSQL's lexer permits high-bit bytes in bare identifiers, including
# UTF-8 combining characters that Python's \w excludes.
UNQUOTED_IDENTIFIER = r"[a-zA-Z_\u0080-\U0010ffff][a-zA-Z0-9_$\u0080-\U0010ffff]*"
ASCII_LOWERCASE = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


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
        match = re.match(UNQUOTED_IDENTIFIER, sql[index:])
        if match:
            end = index + len(match.group(0))
            if depth == 0:
                words.append((match.group(0).lower(), index, end))
            index = end
            continue
        index += 1
    return words


def main_statement(words: list[tuple[str, int, int]]) -> tuple[int, str, int, int] | None:
    candidates = words if words and words[0][0] == "with" else words[:1]
    for index, (word, start, end) in enumerate(candidates):
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


IDENTIFIER = rf'(?:`(?:[^`]|``)+`|"(?:[^"]|"")+"|{UNQUOTED_IDENTIFIER})'
TABLE_NAME = rf"{IDENTIFIER}(?:\s*\.\s*{IDENTIFIER})?"
MYSQL_INSERT_TARGET = re.compile(
    rf"insert\s+(?:(?:low_priority|delayed|high_priority)\s+)?(?:ignore\s+)?(?:into\s+)?{TABLE_NAME}"
    rf"(?:\s+partition\s*\(\s*{IDENTIFIER}(?:\s*,\s*{IDENTIFIER})*\s*\))?\s*\(\s*{IDENTIFIER}",
    re.I,
)
POSTGRESQL_INSERT_TARGET = re.compile(
    rf"insert\s+into\s+{TABLE_NAME}(?:\s+as\s+{IDENTIFIER})?\s*\(\s*{IDENTIFIER}", re.I,
)


def comma_separated(sql: str) -> list[str]:
    """Split at depth-zero commas, ignoring quoted identifier contents."""
    segments = []
    start, depth = 0, 0
    for token in re.finditer(rf'{IDENTIFIER}|[(),]', sql):
        value = token.group()
        if value == "(":
            depth += 1
        elif value == ")":
            if depth == 0:
                sql = sql[:token.start()]
                break
            depth -= 1
        elif value == "," and depth == 0:
            segments.append(sql[start:token.start()].strip())
            start = token.end()
    segments.append(sql[start:].strip())
    return segments


def table_segments(normalized: str) -> list[str]:
    """Extract the column and constraint definitions from a CREATE TABLE."""
    create = CREATE_TABLE_RE.match(normalized)
    if not create:
        return []
    table = re.match(rf"\s+(?:if\s+not\s+exists\s+)?{TABLE_NAME}\s*\(", normalized[create.end():], re.I)
    if not table:
        return []
    return comma_separated(normalized[create.end() + table.end():])


MYSQL_TABLE_OPTION = re.compile(
    rf"^(?:engine|row_format|(?:default\s+)?(?:charset|character\s+set))(?:\s*=|\s+{IDENTIFIER})"
    r"|^auto_increment(?:\s*=\s*|\s+)\d+\b|^comment\s*="
)
MYSQL_DROP_TABLE_ACTION = re.compile(
    rf"^drop\s+(?:primary\s+key\b|foreign\s+key\s+{IDENTIFIER}"
    rf"|(?:index|key|partition)\s+(?!(?:cascade|restrict)\b){IDENTIFIER})"
)
MYSQL_ALTER_TABLE_ACTION = re.compile(
    r"^(?:modify|change)\s+|^convert\s+to\s+character\s+set\s+"
    rf"|^add\s+(?:index|key)\s+{IDENTIFIER}\s*\(\s*(?:{IDENTIFIER}|\()"
)
ADD_COLUMN = re.compile(r"^add\s+(?:column\s+)?(?:if\s+not\s+exists\s+)?")


def has_mysql_column_attributes(columns: list[str]) -> bool:
    for column in columns:
        name = re.match(IDENTIFIER, column)
        if not name or name.group() in {"check", "constraint", "foreign", "key", "like", "primary", "unique"}:
            continue
        definition = column[name.end():]
        previous = ""
        # The first word is the type. Defaults and generated expressions can
        # legitimately refer to a type, function or column named auto_increment.
        for word, start, _ in top_level_words(definition)[1:]:
            if word in {"check", "constraint", "default", "generated", "references"}:
                break
            if word == "set" and previous == "character":
                return True
            if word in {"auto_increment", "unsigned", "zerofill"}:
                if previous != "collate" and not definition[:start].rstrip().endswith("."):
                    return True
            previous = word
    return False


def has_mysql_table_options(ddl: str) -> bool:
    """Screen table options and column attributes at their DDL positions."""
    create = CREATE_TABLE_RE.match(ddl)
    if create:
        header = re.match(rf"\s+(?:if\s+not\s+exists\s+)?{TABLE_NAME}", ddl[create.end():])
        if not header:
            return False
        tail = ddl[create.end() + header.end():]
        for word, start, _ in top_level_words(tail):
            if word in {"as", "inherits", "like", "of", "on", "partition", "select", "tablespace", "using", "with"}:
                break
            if MYSQL_TABLE_OPTION.match(tail[start:]):
                return True
        return has_mysql_column_attributes(table_segments(ddl))

    alter = re.match(rf"^alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?{TABLE_NAME}(?:\s*\*)?\s+", ddl)
    if not alter:
        return False
    for action in comma_separated(ddl[alter.end():]):
        if any(check.match(action) for check in (MYSQL_TABLE_OPTION, MYSQL_ALTER_TABLE_ACTION, MYSQL_DROP_TABLE_ACTION)):
            return True
        column = ADD_COLUMN.match(action)
        if column:
            definition = action[column.end():].lstrip()
            columns = comma_separated(definition[1:]) if definition.startswith("(") else [definition]
            if has_mysql_column_attributes(columns):
                return True
    return False


def column_key(identifier: str, dialect: str) -> str:
    if dialect == "postgresql":
        if identifier.startswith('"'):
            return identifier[1:-1].replace('""', '"')
        # The PostgreSQL profile uses UTF-8, where bare names fold ASCII only.
        return identifier.strip("`").translate(ASCII_LOWERCASE)
    return identifier.strip('`"').lower()


def has_top_level_clause(definition: str, keyword: str, pattern: str) -> bool:
    return any(
        word == keyword and re.match(pattern, definition[start:], re.I)
        for word, start, _ in top_level_words(definition)
    )


PG_QUOTED_NAME = r'(?:u&)?"(?:[^"]|"")+"'
PG_NAME = rf"(?:{PG_QUOTED_NAME}|{UNQUOTED_IDENTIFIER})"
PG_TABLE = rf"{PG_NAME}(?:\s*\.\s*{PG_NAME})?"
PG_NAME_BOUNDARY = r'(?:\s+|(?=(?:u&)?"))'
PG_ADD_COLUMN = re.compile(
    rf"^add{PG_NAME_BOUNDARY}(?:column{PG_NAME_BOUNDARY})?"
    rf"(?P<guard>if\s+not\s+exists{PG_NAME_BOUNDARY})?", re.I,
)
PG_ALTER_TARGET = re.compile(
    rf"^alter\s+table{PG_NAME_BOUNDARY}(?:if\s+exists{PG_NAME_BOUNDARY})?(?:only\s*\(\s*{PG_TABLE}\s*\)|"
    rf"(?:only{PG_NAME_BOUNDARY})?{PG_TABLE}(?:\s*\*)?)(?:\s+|(?<=[\")*]))", re.I,
)


def postgresql_added_columns(ddl: str, *, unprotected_only: bool = False) -> list[str]:
    table = PG_ALTER_TARGET.match(ddl)
    if not table:
        return []
    columns = []
    for action in comma_separated(ddl[table.end():]):
        add_column = PG_ADD_COLUMN.match(action)
        if add_column and not (unprotected_only and add_column.group("guard")):
            columns.append(action[add_column.end():])
    return columns


def postgresql_column_definitions(columns: list[str]) -> list[str]:
    definitions = []
    for column in columns:
        name = re.match(rf"{PG_NAME}(?:\s+|(?<=\"))", column, re.I)
        if name and name.group().strip().lower() not in {"check", "constraint", "exclude", "foreign", "primary", "unique"}:
            definitions.append(column[name.end():])
    return definitions


def postgresql_has_nonnull_stable_default(definition: str) -> bool:
    """Recognize non-null literals and standard time expressions without server metadata."""
    for word, _, end in top_level_words(definition):
        if word != "default":
            continue
        value = definition[end:].strip()
        for _, start, _ in top_level_words(value):
            if re.match(r"(?:check|constraint|generated|not\s+null|primary\s+key|references|unique)\b", value[start:], re.I):
                value = value[:start].rstrip()
                break
        while value.startswith("(") and value.endswith(")"):
            value = value[1:-1].strip()
        return re.fullmatch(
            r"(?:e?\?|[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?|true|false|current_date"
            r"|(?:current_time|current_timestamp|localtime|localtimestamp)(?:\s*\(\s*\d+\s*\))?)",
            value, re.I,
        ) is not None
    return False


def primary_key_definitions(ddl: str, dialect: str) -> list[str]:
    """Return definitions for columns declared in inline or table-level primary keys."""
    columns = {}
    primary_columns = set()
    for segment in table_segments(ddl):
        table_pk = re.match(rf"^(?:constraint\s+(?:{IDENTIFIER}\s+)?)?primary\s+key\s*\(", segment, re.I)
        if table_pk:
            for column in comma_separated(segment[table_pk.end():]):
                name = re.match(IDENTIFIER, column)
                if name:
                    primary_columns.add(column_key(name.group(), dialect))
            continue
        column = re.match(rf"^({IDENTIFIER})\s+(.+)$", segment, re.S)
        if not column:
            continue
        identifier, definition = column.groups()
        name = column_key(identifier, dialect)
        columns[name] = definition.lower()
        if has_top_level_clause(definition, "primary", r"primary\s+key\b"):
            primary_columns.add(name)
    return [definition for name, definition in columns.items() if name in primary_columns]


def drops_column(normalized: str, dialect: str) -> bool:
    table = re.match(rf"^alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?{TABLE_NAME}\s+", normalized)
    if not table:
        return False
    # An action starts after the table name or a top-level comma.
    exclusions = "index|key|primary|foreign|partition|constraint" if dialect == "mysql" else "constraint"
    actions = comma_separated(normalized[table.end():])
    if dialect == "postgresql":
        actions = [action for action in actions if not MYSQL_DROP_TABLE_ACTION.match(action)]
    return any(re.match(
        rf"^drop\s+(?:column\s+(?:if\s+exists\s+)?{IDENTIFIER}|(?!(?:{exclusions})\b)(?:if\s+exists\s+)?{IDENTIFIER})",
        action,
    ) for action in actions)


def cte_bodies(masked: str) -> list[tuple[int, int]]:
    """Extract WITH item bodies after AS, including nested PostgreSQL CTEs."""
    bodies: list[tuple[int, int]] = []
    for match in re.finditer(r"\bas\s*\(", masked, re.I):
        start = match.end()
        depth, index = 1, start
        while index < len(masked) and depth:
            if masked[index] == "(":
                depth += 1
            elif masked[index] == ")":
                depth -= 1
            index += 1
        if depth == 0:
            bodies.append((start, index - 1))
    return bodies


def inspect_statement(file: str, line: int, statement: str, dialect: str, *, mysql_no_backslash_escapes: bool = False,
                      archived_sql: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    masked = mask_literals_and_comments(statement, dialect, mysql_no_backslash_escapes=mysql_no_backslash_escapes)
    normalized = re.sub(r"\s+", " ", masked).strip().lower()
    words = top_level_words(normalized)
    main = main_statement(words)

    if dialect == "postgresql" and normalized.startswith("with "):
        for start, end in cte_bodies(masked):
            body = masked[start:end]
            if re.match(r"\s*(?:insert|update|delete)\b", body, re.I):
                offset = start + len(body) - len(body.lstrip())
                body_line = line + masked[:offset].count("\n")
                findings.extend(inspect_statement(file, body_line, statement[offset:end], dialect))

    if re.search(r"\bselect\s+(?:(?:all|distinct)\s+)?(?:[a-z0-9_]+\.)?\*(?:\s|,|\)|$)", normalized):
        add(findings, file, line, split_rule_id(dialect, "G.SEL.12"), dialect, "SELECT * requires a documented catalog exception", statement)
    if dialect == "mysql" and re.search(r"\b(?:cross|full(?:\s+outer)?)\s+join\b", normalized):
        add(findings, file, line, "MYSQL-SEL-008", dialect, "Avoid CROSS JOIN; MySQL does not support FULL JOIN", statement)
    if dialect == "postgresql" and re.search(r"\bcross\s+join\b(?!\s+lateral\b)", normalized):
        add(findings, file, line, "POSTGRESQL-SEL-008", dialect, "Review whether the Cartesian product of this CROSS JOIN is intentional", statement, review=True)

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
            source_id = "G.UPD.01" if dml_kind == "update" else "G.DEL.01"
            add(findings, file, line, split_rule_id(dialect, source_id), dialect, "UPDATE/DELETE must have a non-trivial WHERE clause", statement)
        if dml_kind == "update":
            tail_names = [word for word, _, _ in tail_words]
            if any(tail_names[index:index + 2] == ["order", "by"] for index in range(len(tail_names) - 1)):
                add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPD-002", dialect, "Top-level UPDATE ORDER BY is prohibited", statement)
            if "limit" in tail_names:
                add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPD-001", dialect, "Top-level UPDATE LIMIT is prohibited; use a stable-key batch design", statement)

    create_table = CREATE_TABLE_RE.match(normalized)
    alter_table = re.match(r"^alter\s+table\b", normalized)
    ddl = ""
    if create_table or alter_table:
        ddl = mask_literals_and_comments(
            statement, dialect, mysql_no_backslash_escapes=mysql_no_backslash_escapes,
            preserve_identifiers=True, mark_strings=dialect == "postgresql" and bool(alter_table),
        ).strip()
    foreign_key = bool(re.search(r"(?<!\bdrop )\bforeign\s+key\b|\breferences\s+[a-z0-9_`\"]+\s*\(", normalized))
    added_columns = postgresql_column_definitions(postgresql_added_columns(ddl)) if dialect == "postgresql" and alter_table else []
    if dialect == "postgresql" and not foreign_key:
        columns = postgresql_column_definitions(table_segments(ddl)) if create_table else added_columns
        foreign_key = any(
            has_top_level_clause(column, "references", rf"references\s+{TABLE_NAME}") for column in columns
        )
    if foreign_key:
        add(findings, file, line, split_rule_id(dialect, "G.TAB.04"), dialect, "Foreign keys are prohibited", statement)
    if create_table:
        after_table = normalized[create_table.end():].lstrip()
        if not re.match(r"^if\s+not\s+exists\b", after_table):
            add(findings, file, line, split_rule_id(dialect, "G.UPG.10"), dialect, "CREATE TABLE must use IF NOT EXISTS", statement)
        if not re.search(r"\bprimary\s+key\b", normalized):
            add(findings, file, line, split_rule_id(dialect, "G.TAB.16"), dialect, "Every table must define a primary key", statement)
    if re.match(r"^drop\s+table\b", normalized) and not re.match(r"^drop\s+table\s+if\s+exists\b", normalized):
        add(findings, file, line, split_rule_id(dialect, "G.UPG.11"), dialect, "DROP TABLE must use IF EXISTS", statement)
    if alter_table:
        if dialect == "postgresql" and archived_sql and postgresql_column_definitions(
            postgresql_added_columns(ddl, unprotected_only=True)
        ):
            add(findings, file, line, ARCHIVE_REPLAY_RULE, dialect, "Archived ADD COLUMN must use IF NOT EXISTS", statement)
        if drops_column(ddl.lower(), dialect):
            add(findings, file, line, split_rule_id(dialect, "G.UPG.03"), dialect, "Dropping columns is prohibited", statement)
        mysql_type_change = dialect == "mysql" and re.search(r"\b(?:modify|change)\s+(?:column\s+)?", normalized)
        if mysql_type_change or re.search(
            r'\balter\s+column\s+[a-z0-9_"]+\s+(?:set\s+data\s+)?type\b', normalized,
        ):
            add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPG-005", dialect, "Direct column type modification requires a compatible expand-contract plan", statement)
        if re.search(r"\balter\s+column\s+[a-z0-9_\"]+\s+set\s+not\s+null\b", normalized):
            add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPG-008", dialect, "Changing an existing column to NOT NULL is prohibited", statement)
        if dialect == "mysql" and re.search(r"\b(?:modify|change)\s+(?:column\s+)?[a-z0-9_`]+\s+[^,;]+\bnot\s+null\b", normalized):
            add(findings, file, line, "MYSQL-UPG-008", dialect, "Changing an existing column to NOT NULL is prohibited", statement)
        if dialect == "postgresql":
            add_not_null = any(
                has_top_level_clause(column, "not", r"not\s+null\b")
                and not postgresql_has_nonnull_stable_default(column)
                for column in added_columns
            )
        else:
            add_not_null = re.search(r"\badd\s+(?:column\s+)?(?!constraint\b)[a-z0-9_`\"]+\s+[^,;]+\bnot\s+null\b", normalized)
        if add_not_null:
            add(findings, file, line, f"{'MYSQL' if dialect == 'mysql' else 'POSTGRESQL'}-UPG-007", dialect, "Adding a NOT NULL column directly is prohibited", statement)
    if main and main[1] == "insert":
        insert_sql = mask_literals_and_comments(
            statement, dialect, mysql_no_backslash_escapes=mysql_no_backslash_escapes, preserve_identifiers=True,
        )
        insert = main_statement(top_level_words(insert_sql))
        target = MYSQL_INSERT_TARGET if dialect == "mysql" else POSTGRESQL_INSERT_TARGET
        if insert is None or not target.match(insert_sql, insert[2]):
            add(findings, file, line, split_rule_id(dialect, "G.INS.01"), dialect, "INSERT must list target columns", statement)
    if dialect == "mysql" and re.match(r"^xa\s+(?:start|begin|end|prepare|commit|rollback)\b", normalized):
        add(findings, file, line, "MYSQL-TXN-007", dialect, "Verify approval for this XA transaction", statement, review=True)
    if dialect == "postgresql" and re.match(r"^(?:prepare\s+transaction|commit\s+prepared|rollback\s+prepared)\b", normalized):
        add(findings, file, line, "POSTGRESQL-TXN-007", dialect, "Verify approval for this prepared transaction", statement, review=True)
    if re.search(r"\bset\s+(?:(?:session|global)\s+)?transaction\s+isolation\s+level\b", normalized):
        add(findings, file, line, split_rule_id(dialect, "G.TXN.01"), dialect, "Explicit transaction isolation levels are prohibited", statement)

    if create_table:
        primary_keys = primary_key_definitions(ddl, dialect)
        if dialect == "mysql":
            if any(re.search(r"\bauto_increment\b", definition) for definition in primary_keys):
                add(findings, file, line, "MYSQL-PK-001", dialect, "AUTO_INCREMENT primary keys are prohibited", statement)
        elif any(
            re.match(r"(?:smallserial|serial|bigserial)\b(?!\s*\.)", definition)
            or has_top_level_clause(definition, "generated", r"generated\s+(?:always|by\s+default)\s+as\s+identity\b")
            for definition in primary_keys
        ):
            add(findings, file, line, "POSTGRESQL-PK-001", dialect, "Serial/identity primary keys are prohibited", statement)
        candidate_type = (
            r"(?:char(?:acter)?|varchar|text|tinytext|mediumtext|longtext|varbinary)\b|binary\s*\((?!\s*16\s*\))"
            if dialect == "mysql" else r"(?:char(?:acter)?|varchar|text|bytea|binary|varbinary)\b"
        )
        if any(re.match(candidate_type, definition) for definition in primary_keys):
            storage = "BINARY(16)" if dialect == "mysql" else "native uuid"
            add(findings, file, line, f"{dialect.upper()}-PK-001", dialect, f"Verify primary-key semantics in the data model; UUID keys must use {storage}", statement, review=True)

    if dialect == "mysql":
        engine = re.search(r"\bengine\s*=\s*([a-z0-9_]+)", normalized)
        if engine and engine.group(1) != "innodb":
            add(findings, file, line, "MYSQL-TAB-001", dialect, "Verify the non-InnoDB engine and any approved exception", statement, review=True)
        charsets = re.findall(r"\b(?:default\s+)?(?:character\s+set|charset)\s*=?\s*([a-z0-9_]+)", normalized)
        if any(charset != "utf8mb4" for charset in charsets):
            add(findings, file, line, "MYSQL-ENC-001", dialect, "Verify the non-utf8mb4 character set and any approved exception", statement, review=True)
    elif "`" in normalized or has_mysql_table_options(ddl.lower()):
        add(
            findings, file, line, "POSTGRESQL-TAB-001", dialect,
            "Review MySQL-specific table syntax for PostgreSQL compatibility", statement, review=True,
        )
    return findings


def inspect(file: str, sql: str, requested_dialect: str, *, mysql_no_backslash_escapes: bool = False,
            archived_sql: bool = False) -> tuple[str, list[Finding]]:
    dialect = detect_dialect(sql, mysql_no_backslash_escapes=mysql_no_backslash_escapes) if requested_dialect == "auto" else requested_dialect
    if dialect is None:
        raise ValueError(f"{file}: cannot determine SQL dialect; pass --dialect mysql or --dialect postgresql")
    findings: list[Finding] = []
    for line, statement in split_statements(sql, dialect, mysql_no_backslash_escapes=mysql_no_backslash_escapes):
        findings.extend(inspect_statement(
            file, line, statement, dialect, archived_sql=archived_sql, mysql_no_backslash_escapes=mysql_no_backslash_escapes,
        ))
    return dialect, findings


def read_inputs(paths: list[str]) -> list[tuple[str, str]]:
    inputs = []
    for raw_path in paths:
        if raw_path == "-": inputs.append(("<stdin>", sys.stdin.read())); continue
        path = Path(raw_path)
        if not path.is_file(): raise ValueError(f"not a file: {path}")
        inputs.append((str(path), path.read_bytes().decode("utf-8")))
    return inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run high-confidence MySQL/PostgreSQL Block rules")
    parser.add_argument("paths", nargs="+", help="SQL files, or - for stdin")
    parser.add_argument("--dialect", choices=("auto", "mysql", "postgresql"), default="auto")
    parser.add_argument("--mysql-no-backslash-escapes", action="store_true", help="Use MySQL NO_BACKSLASH_ESCAPES for the input")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--migration-evidence", help="Trusted migration-test receipt for the scanned batch")
    parser.add_argument("--archived-sql", action="store_true", help="Require static checks and trusted replay evidence for archived SQL")
    parser.add_argument("--archive-replay-evidence", help="Trusted receipt of two consecutive executions covering all archived inputs")
    return parser.parse_args()


def apply_rollback_evidence(receipt: str, inputs: list[tuple[str, str]], dialects: dict[str, str],
                            findings: list[Finding], *, mysql_no_backslash_escapes: bool) -> tuple[list[Finding], list[dict]]:
    from migration_evidence import read_rollback_receipt

    selected = {Path(file).resolve(): (file, sql, dialects[file]) for file, sql in inputs if file != "<stdin>"}
    operations = read_rollback_receipt(receipt, selected)
    verified = {(item["file"], item["line"], item["rule_id"]) for item in operations}
    starts = {}
    for file, sql in inputs:
        dialect = dialects[file]
        for line, statement in split_statements(sql, dialect, mysql_no_backslash_escapes=mysql_no_backslash_escapes):
            masked = mask_literals_and_comments(statement, dialect, mysql_no_backslash_escapes=mysql_no_backslash_escapes)
            leading = len(masked) - len(masked.lstrip())
            starts[file, line] = line + masked[:leading].count("\n")
    remaining = [
        finding for finding in findings
        if (finding.file, starts.get((finding.file, finding.line), finding.line), finding.rule_id) not in verified
    ]
    return remaining, operations


def main() -> int:
    args = parse_args(); findings: list[Finding] = []; dialects: dict[str, str] = {}
    archived = bool(args.archived_sql or args.archive_replay_evidence)
    try:
        inputs = read_inputs(args.paths)
        for file, sql in inputs:
            dialect, current = inspect(
                file, sql, args.dialect, archived_sql=archived, mysql_no_backslash_escapes=args.mysql_no_backslash_escapes,
            )
            dialects[file] = dialect
            findings.extend(current)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr); return 2
    operations = []
    evidence_errors = []
    if args.migration_evidence:
        try:
            findings, operations = apply_rollback_evidence(
                args.migration_evidence, inputs, dialects, findings, mysql_no_backslash_escapes=args.mysql_no_backslash_escapes,
            )
        except (OSError, ValueError) as error:
            evidence_errors.append(str(error))
    if archived:
        from migration_evidence import read_archive_replay_receipt

        covered = set()
        problem = "Missing verified same-database replay evidence"
        selected = {Path(file).resolve(): (file, sql, dialects[file]) for file, sql in inputs if file != "<stdin>"}
        if args.archive_replay_evidence:
            try:
                covered = read_archive_replay_receipt(args.archive_replay_evidence, selected)
            except (OSError, ValueError) as error:
                problem = f"Invalid archive replay evidence: {error}"
        for file, _ in inputs:
            if file == "<stdin>" or Path(file).resolve() not in covered:
                dialect = dialects[file]
                add(findings, file, 1, f"{dialect.upper()}-DBS-003", dialect, problem, "")
    failed = bool(evidence_errors) or any(item.gate == "block" for item in findings)
    if args.format == "json":
        checked_rules = set(COMMON_GUARD_RULES)
        screened_rules = set()
        for dialect in set(dialects.values()):
            metadata = rule_metadata(dialect)
            for rule_id in DIALECT_GUARD_RULES[dialect]:
                if rule_id == ARCHIVE_REPLAY_RULE and not archived:
                    continue
                if metadata[rule_id]["check"]["kind"] == "static":
                    checked_rules.add(rule_id)
                else:
                    screened_rules.add(rule_id)
        print(json.dumps({
            "result": "fail" if failed else "pass",
            "dialects": dialects,
            "checked_rules": sorted(checked_rules),
            "screened_rules": sorted(screened_rules),
            "findings": [asdict(item) for item in findings],
            **({"normal_rollbacks": operations, "migration_evidence_errors": evidence_errors} if args.migration_evidence else {}),
        }, ensure_ascii=False, indent=2))
    elif findings or operations or evidence_errors:
        for error in evidence_errors:
            print(f"BLOCK migration evidence: {error}")
        for item in findings:
            print(f"{item.file}:{item.line}: {item.gate.upper()} {item.rule_id} [{item.dialect}] {item.message}\n  {item.snippet}")
        for item in operations:
            print(f"{item['file']}:{item['line']}: PASS normal-rollback {item['rule_id']} ({item['batch']})")
    else:
        print(f"PASS: no findings ({', '.join(sorted(set(dialects.values())))})")
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
