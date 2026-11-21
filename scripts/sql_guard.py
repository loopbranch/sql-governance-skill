#!/usr/bin/env python3
"""Conservative, dependency-free SQL static gate for high-confidence rules.

This checker intentionally covers only syntax patterns that can be judged with
high confidence without a database schema. Manual and hybrid catalog rules stay
in the SKILL review workflow.
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
    message: str
    snippet: str


def strip_comments(sql: str) -> str:
    """Remove comments while preserving line numbers."""
    without_blocks = re.sub(
        r"/\*.*?\*/",
        lambda match: "\n" * match.group(0).count("\n"),
        sql,
        flags=re.DOTALL,
    )
    return re.sub(r"(?m)--[^\n]*|#[^\n]*", "", without_blocks)


def statements(sql: str) -> list[tuple[int, str]]:
    """Split ordinary migration SQL; semicolons inside strings are unsupported."""
    result: list[tuple[int, str]] = []
    offset = 0
    for part in sql.split(";"):
        if part.strip():
            leading = len(part) - len(part.lstrip())
            line = sql.count("\n", 0, offset + leading) + 1
            result.append((line, part.strip()))
        offset += len(part) + 1
    return result


def compact(statement: str, limit: int = 180) -> str:
    value = re.sub(r"\s+", " ", statement).strip()
    return value if len(value) <= limit else value[: limit - 3] + "..."


def add(findings: list[Finding], file: str, line: int, rule_id: str, message: str, statement: str) -> None:
    findings.append(Finding(file, line, rule_id, "block", message, compact(statement)))


def inspect_statement(file: str, line: int, statement: str) -> list[Finding]:
    findings: list[Finding] = []
    normalized = re.sub(r"\s+", " ", statement).strip().lower()

    if re.match(r"^select\s+(?:[a-z0-9_]+\.)?\*(?:\s|,|$)", normalized):
        add(findings, file, line, "SQL-DML-001", "SELECT * requires a documented catalog exception", statement)

    if re.match(r"^(update|delete\s+from)\b", normalized):
        where_match = re.search(r"\bwhere\b(.+)$", normalized)
        invalid_where = where_match is None or re.fullmatch(
            r"\s*(?:1\s*=\s*1|true)(?:\s+(?:order\s+by|limit)\b.*)?\s*",
            where_match.group(1) if where_match else "",
        )
        if invalid_where:
            add(findings, file, line, "SQL-DML-002", "UPDATE/DELETE must have a non-trivial WHERE clause", statement)

    if re.search(r"\bforeign\s+key\b|\breferences\s+[a-z0-9_`]+\s*\(", normalized):
        add(findings, file, line, "SQL-TAB-002", "Foreign keys are prohibited", statement)

    if re.search(r"\bauto_increment\b", normalized):
        add(findings, file, line, "SQL-IDX-004", "AUTO_INCREMENT primary-key strategy is prohibited", statement)

    if re.match(r"^create\s+table\b", normalized) and not re.match(
        r"^create\s+table\s+if\s+not\s+exists\b", normalized
    ):
        add(findings, file, line, "SQL-UPG-002", "CREATE TABLE must use IF NOT EXISTS", statement)

    if re.match(r"^drop\s+table\b", normalized) and not re.match(
        r"^drop\s+table\s+if\s+exists\b", normalized
    ):
        add(findings, file, line, "SQL-UPG-002", "DROP TABLE must use IF EXISTS", statement)

    if re.match(r"^alter\s+table\b", normalized) and re.search(r"\bdrop\s+(?:column\s+)?[a-z0-9_`]+", normalized):
        add(findings, file, line, "SQL-UPG-001", "Dropping columns is prohibited", statement)

    if re.match(r"^insert\s+into\b", normalized) and not re.match(
        r"^insert\s+into\s+[a-z0-9_.`]+\s*\(", normalized
    ):
        add(findings, file, line, "SQL-DML-003", "INSERT must list target columns", statement)

    if re.search(r"\bxa\s+(?:start|begin|end|prepare|commit|rollback)\b", normalized):
        add(findings, file, line, "SQL-TXN-002", "XA transactions are prohibited", statement)

    if re.search(r"\bset\s+(?:(?:session|global)\s+)?transaction\s+isolation\s+level\b", normalized):
        add(findings, file, line, "SQL-TXN-002", "Explicit transaction isolation levels are prohibited", statement)

    return findings


def inspect(file: str, sql: str) -> list[Finding]:
    clean_sql = strip_comments(sql)
    findings: list[Finding] = []
    for line, statement in statements(clean_sql):
        findings.extend(inspect_statement(file, line, statement))
    return findings


def read_inputs(paths: list[str]) -> list[tuple[str, str]]:
    inputs: list[tuple[str, str]] = []
    for raw_path in paths:
        if raw_path == "-":
            inputs.append(("<stdin>", sys.stdin.read()))
            continue
        path = Path(raw_path)
        if not path.is_file():
            raise ValueError(f"not a file: {path}")
        inputs.append((str(path), path.read_text(encoding="utf-8")))
    return inputs


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run high-confidence SQL Block rules")
    parser.add_argument("paths", nargs="+", help="SQL files, or - for stdin")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    findings: list[Finding] = []
    try:
        for file, sql in read_inputs(args.paths):
            findings.extend(inspect(file, sql))
    except (OSError, UnicodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps({"result": "fail" if findings else "pass", "findings": [asdict(item) for item in findings]}, ensure_ascii=False, indent=2))
    elif findings:
        for item in findings:
            print(f"{item.file}:{item.line}: BLOCK {item.rule_id} {item.message}\n  {item.snippet}")
    else:
        print("PASS: no high-confidence Block violations found")

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
