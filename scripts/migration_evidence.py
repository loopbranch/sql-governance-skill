"""Validate rollback receipts supplied by a trusted migration test runner."""
from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path


# Require a complete supported statement; a receipt cannot cover a mixed action.
IDENTIFIER = r'(?:[^\W\d][\w$]*|"(?:[^"]|"")+"|`(?:[^`]|``)+`)'
TABLE = rf"{IDENTIFIER}(?:\s*\.\s*{IDENTIFIER})?"
ALTER_TABLE = rf"alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?{TABLE}\s+"
DROP_COLUMN = rf"drop\s+column\s+(?:if\s+exists\s+)?{IDENTIFIER}"
INVERSE_RULES = (
    (rf"{DROP_COLUMN}(?:\s*,\s*{DROP_COLUMN})*", "GUPG-003"),
    (rf"alter\s+column\s+{IDENTIFIER}\s+(?:set\s+data\s+)?type\s+[^,;]+", "UPG-005"),
    (rf"alter\s+column\s+{IDENTIFIER}\s+set\s+not\s+null", "UPG-008"),
    (rf"add\s+constraint\s+{IDENTIFIER}\s+foreign\s+key\s*\([^)]+\)\s+references\s+{TABLE}\s*\([^)]+\)", "GTAB-004"),
)


def verified_batch(record: dict, selected: dict[Path, tuple[str, str, str]]) -> tuple[str, list[dict]]:
    for key in ("batch", "dialect", "database_version"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise ValueError(f"migration evidence is missing {key}")
    batch = record["batch"]
    dialect = record["dialect"]
    if not all(record.get(key) is True for key in ("schema_equal", "data_equal", "syntax_verified")):
        raise ValueError(f"{batch}: migration round-trip has not been verified")

    files = record["files"]
    if not isinstance(files, list) or not files:
        raise ValueError(f"{batch}: missing paired scripts")
    members = {}
    roots = set()
    kinds = {"upgrade": set(), "rollback": set()}
    for member in files:
        path = Path(member["path"])
        direction, kind = member["direction"], member["kind"]
        resolved = path.resolve()
        if direction not in kinds or kind not in {"ddl", "dml"} or resolved in members or kind in kinds[direction]:
            raise ValueError(f"{batch}: duplicate or invalid migration file {path}")
        if resolved.parent.name != batch or resolved.parent.parent.name != direction:
            raise ValueError(f"{batch}: unexpected migration location {path}")
        if member.get("execution") not in {"sql", "none"}:
            raise ValueError(f"{batch}: invalid execution marker for {path}")
        display, sql, actual_dialect = selected[resolved]
        if actual_dialect != dialect or sha256(sql.encode("utf-8")).hexdigest() != member["sha256"]:
            raise ValueError(f"{batch}: migration file has a different digest or dialect: {path}")
        kinds[direction].add(kind)
        roots.add(resolved.parent.parent.parent)
        members[resolved] = (member, display, sql)
    if len(roots) != 1 or not kinds["upgrade"] or kinds["upgrade"] != kinds["rollback"]:
        raise ValueError(f"{batch}: upgrade and rollback kinds do not match")
    for prerequisite in record.get("predecessors", []):
        path = Path(prerequisite["path"]).resolve()
        if path in members or path not in selected:
            raise ValueError(f"{batch}: missing predecessor file: {prerequisite['path']}")
        _, sql, prerequisite_dialect = selected[path]
        if prerequisite_dialect != dialect or sha256(sql.encode("utf-8")).hexdigest() != prerequisite["sha256"]:
            raise ValueError(f"{batch}: predecessor has a different digest or dialect: {prerequisite['path']}")

    prefix = {"mysql": "MYSQL", "postgresql": "POSTGRESQL"}[dialect]
    results = []
    seen = set()
    operations = record["operations"]
    if not isinstance(operations, list):
        raise ValueError(f"{batch}: expected a list of inverse operations")
    for action in operations:
        member, display, sql = members[Path(action["path"]).resolve()]
        line, statement = action["line"], action["sql"]
        if member["direction"] != "rollback" or member["execution"] != "sql":
            raise ValueError(f"{batch}: evidence cannot cover a non-rollback operation")
        source = sql.splitlines()
        if type(line) is not int or not 1 <= line <= len(source) or source[line - 1].strip() != statement:
            raise ValueError(f"{batch}: rollback operation does not match {display}:{line}")
        rule = next((rule for pattern, rule in INVERSE_RULES if re.fullmatch(ALTER_TABLE + pattern + r"\s*;", statement, re.I)), None)
        if rule is None or not statement.endswith(";") or statement.count(";") != 1 or (display, line) in seen:
            raise ValueError(f"{batch}: unsupported or duplicate inverse operation at {display}:{line}")
        seen.add((display, line))
        results.append({"file": display, "line": line, "rule_id": f"{prefix}-{rule}", "batch": batch,
                        "dialect": dialect, "database_version": record["database_version"], "state": "normal-rollback"})
    return batch, results


def read_rollback_receipt(path: str, selected: dict[Path, tuple[str, str, str]]) -> list[dict]:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("version") != 1 or not isinstance(document.get("batches"), list) or not document["batches"]:
        raise ValueError("expected a version 1 migration receipt with at least one batch")
    seen = set()
    operations = []
    for record in document["batches"]:
        try:
            batch, verified = verified_batch(record, selected)
        except (AttributeError, KeyError, TypeError) as error:
            raise ValueError(f"incomplete migration receipt or missing scanned file: {error}") from error
        key = (record["dialect"], batch)
        if key in seen:
            raise ValueError(f"{batch}: duplicate verified batch for {record['dialect']}")
        seen.add(key)
        operations.extend(verified)
    return operations
