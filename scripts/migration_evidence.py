"""Validate exact migration evidence supplied by a trusted isolated test runner."""
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
TYPE_ACTION = rf"alter\s+column\s+{IDENTIFIER}\s+(?:set\s+data\s+)?type\s+[^;]+"
FOREIGN_ACTION = (
    rf"add\s+constraint\s+{IDENTIFIER}\s+foreign\s+key\s*\([^)]+\)\s+references\s+{TABLE}\s*\([^)]+\)"
    r"(?:\s+on\s+delete\s+cascade)?(?:\s+deferrable\s+initially\s+deferred)?"
)
INVERSE_RULES = (
    (rf"{DROP_COLUMN}(?:\s*,\s*{DROP_COLUMN})*", "GUPG-003"),
    (rf"alter\s+column\s+{IDENTIFIER}\s+set\s+not\s+null", "UPG-008"),
    (FOREIGN_ACTION, "GTAB-004"),
)
EXPANSION_RULES = {f"POSTGRESQL-{rule}" for rule in ("GTAB-004", "GUPG-003", "UPG-005", "UPG-007", "UPG-008")}


def sql_tokens(sql: str) -> list[str]:
    # Keep quoted values/identifiers intact: only whitespace and comments differ.
    tokens = re.findall(r"--[^\n]*|/\*[\s\S]*?\*/|[eE]'(?:''|\\.|[^'\\])*'|'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[^\W\d][\w$]*|\d+|[^\s]", sql)
    return [token if token.startswith(("'", '\"')) or re.match(r"^[eE]'", token) else token.lower()
            for token in tokens if not token.startswith(("--", "/*"))]


def source_range(sql: str, line: int, end_line: int) -> tuple[str, int, int]:
    lines = sql.splitlines(keepends=True)
    if type(line) is not int or type(end_line) is not int or not 1 <= line <= end_line <= len(lines):
        raise ValueError("invalid SQL operation line range")
    start = sum(map(len, lines[:line-1]))
    end = start + sum(map(len, lines[line-1:end_line]))
    return sql[start:end], start, end


def checked_action(sql: str, action: dict, dialect: str) -> tuple[int, str]:
    import sql_guard
    line, statement = action["line"], action["sql"]
    end = action.get("end_line", line)
    raw, _, _ = source_range(sql, line, end)
    if not isinstance(statement, str) or sql_tokens(raw) != sql_tokens(statement):
        raise ValueError("operation does not match the complete source range")
    pieces = sql_guard.split_statements(statement, dialect)
    if len(pieces) != 1 or not statement.rstrip().endswith(";"):
        raise ValueError("evidence must locate one complete SQL statement")
    matched = False
    for first_line, candidate in sql_guard.split_statements(sql, dialect):
        masked = sql_guard.mask_literals_and_comments(candidate, dialect)
        leading = len(masked) - len(masked.lstrip())
        actual_line = first_line + masked[:leading].count("\n")
        if actual_line == line and sql_tokens(candidate) == sql_tokens(statement.rstrip().removesuffix(";")):
            matched = True
            break
    if not matched:
        raise ValueError("operation is not a complete top-level statement")
    return line, statement


def inverse_rule(statement: str, dialect: str) -> str | None:
    import sql_guard
    prefix = re.match(ALTER_TABLE, statement, re.I)
    if not prefix:
        return None
    tail = statement[prefix.end():].strip().removesuffix(";").strip()
    # Multi-action receipts only cover homogeneous type conversions. A comma
    # inside numeric(12,2) or an expression is not a new ALTER action.
    actions = sql_guard.comma_separated(sql_guard.mask_literals_and_comments(tail, dialect, preserve_identifiers=True))
    if actions and all(re.fullmatch(TYPE_ACTION, action, re.I) for action in actions):
        return "UPG-005"
    return next((rule for pattern, rule in INVERSE_RULES if re.fullmatch(pattern, tail, re.I | re.S)), None)


def executable_reference(sql: str) -> str:
    import sql_guard
    code = list(sql_guard.mask_literals_and_comments(sql, "postgresql", preserve_identifiers=True))
    cursor = 0
    for _, statement in sql_guard.split_statements(sql, "postgresql"):
        start = sql.find(statement, cursor)
        cursor = start + len(statement)
        bodies = []
        outer = sql_guard.mask_literals_and_comments(statement, "postgresql", preserve_identifiers=True, dollar_ranges=bodies)
        if not re.match(r"^\s*DO\b", outer, re.I):
            continue
        # Expose executable DO source, but leave strings, comments and nested
        # routine bodies masked. Never search arbitrary text for an old action.
        for body_start, body_end in bodies:
            body = sql_guard.mask_literals_and_comments(statement[body_start:body_end], "postgresql", preserve_identifiers=True)
            code[start+body_start:start+body_end] = body
    return "".join(code)


def expansion_evidence(record: dict, members: dict, batch: str) -> list[dict]:
    import sql_guard
    expansion = record.get("expansion")
    if expansion is None:
        return []
    if record["dialect"] != "postgresql" or not all(expansion.get(key) is True for key in ("same_precondition", "same_fixture", "schema_equal", "data_equal")):
        raise ValueError(f"{batch}: existing migration equivalence has not been verified")
    if {(member[0]["direction"], member[0]["kind"]) for member in members.values()} != {(d, k) for d in ("upgrade", "rollback") for k in ("ddl", "dml")}:
        raise ValueError(f"{batch}: expansion needs all four paired files")
    for key in ("precondition", "fixture", "schema", "data"):
        comparison = expansion["comparisons"][key]
        old, new = comparison["reference_sha256"], comparison["current_sha256"]
        if not isinstance(old, str) or re.fullmatch(r"[a-f0-9]{64}", old) is None or old != new:
            raise ValueError(f"{batch}: {key} comparison differs or lacks a valid digest")
    references = {}
    for reference in expansion["reference_files"]:
        target = Path(reference["path"]).resolve()
        if target not in members or target in references:
            raise ValueError(f"{batch}: invalid or duplicate reference member")
        old = Path(reference["reference_path"]).read_bytes()
        if sha256(old).hexdigest() != reference["sha256"]:
            raise ValueError(f"{batch}: reference script has a different digest")
        text = old.decode("utf-8")
        references[target] = (text, executable_reference(text))
    if set(references) != set(members):
        raise ValueError(f"{batch}: missing reference script")
    results, seen = [], set()
    for action in expansion["operations"]:
        target = Path(action["path"]).resolve()
        member, display, sql = members[target]
        if member["execution"] != "sql" or member["kind"] != "ddl":
            raise ValueError(f"{batch}: expansion may only cover existing DDL actions")
        rule = action["rule_id"]
        if rule not in EXPANSION_RULES:
            raise ValueError(f"{batch}: rule cannot be covered by expansion evidence: {rule}")
        line, statement = checked_action(sql, action, "postgresql")
        old, executable = references[target]
        ref_line = action["reference_line"]
        ref_end = action.get("reference_end_line", ref_line)
        raw, start, end = source_range(old, ref_line, ref_end)
        if sql_tokens(raw) != sql_tokens(statement) or not re.match(r"^\s*(?:ALTER|CREATE)\b", executable[start:end], re.I):
            raise ValueError(f"{batch}: {display}:{line} {rule}: action is not the same executable native reference SQL at reference lines {ref_line}-{ref_end}")
        found = sql_guard.inspect_statement(display, line, statement.rstrip().removesuffix(";"), "postgresql")
        if rule not in {finding.rule_id for finding in found}:
            raise ValueError(f"{batch}: {display}:{line} {rule}: evidence rule does not match the located action (found {sorted({finding.rule_id for finding in found})})")
        key = (display, line, rule)
        if key in seen:
            raise ValueError(f"{batch}: duplicate expansion action")
        seen.add(key)
        results.append({"file": display, "line": line, "rule_id": rule, "batch": batch, "dialect": "postgresql", "database_version": record["database_version"], "state": "existing-migration-expansion"})
    return results



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
        line, statement = checked_action(sql, action, dialect)
        rule = inverse_rule(statement, dialect)
        if rule is None or (display, line) in seen:
            raise ValueError(f"{batch}: unsupported or duplicate inverse operation at {display}:{line}")
        seen.add((display, line))
        results.append({"file": display, "line": line, "rule_id": f"{prefix}-{rule}", "batch": batch,
                        "dialect": dialect, "database_version": record["database_version"], "state": "normal-rollback"})
    results.extend(expansion_evidence(record, members, batch))
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
        upgrade, rollback = record.get("upgrade_id"), record.get("rollback_id")
        if upgrade is not None or rollback is not None:
            if not isinstance(upgrade, str) or re.fullmatch(r"V[0-9]+", upgrade) is None or rollback != "U" + upgrade[1:]:
                raise ValueError(f"{batch}: invalid paired version identity")
        key = (record["dialect"], batch, upgrade, rollback)
        if key in seen:
            raise ValueError(f"{batch}: duplicate verified batch for {record['dialect']}")
        seen.add(key)
        operations.extend(verified)
    return operations
