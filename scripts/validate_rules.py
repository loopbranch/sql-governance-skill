#!/usr/bin/env python3
"""Validate catalog routing, full source coverage, and all dialect rule files."""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RULES_DIR = ROOT / "rules"
CATALOG_PATH = RULES_DIR / "catalog.json"
VALID_LEVELS = {"prohibition", "mandatory", "recommendation", "reference"}
VALID_GATES = {"block", "warn", "info"}
VALID_KINDS = {"static", "manual", "hybrid"}
VALID_DIALECTS = {"mysql", "postgresql"}
EXPECTED_SOURCE_COUNT = 154
EXPECTED_SOURCE_DOMAINS = {
    "DBS": 6, "TAB": 19, "IDX": 11, "FMT": 13, "NAM": 9,
    "CMT": 10, "SEL": 35, "INS": 3, "DEL": 3, "UPD": 7,
    "CLI": 5, "TXN": 8, "UPG": 13, "SEC": 3, "KOO": 9,
}
REQUIRED = {"id", "source", "name", "level", "gate", "scope", "dialects", "condition", "check", "examples", "remediation", "confirmation_required"}


def fail(message: str) -> None:
    raise ValueError(message)


def load_json(path: Path) -> object:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def validate_rule(rule: object, file_name: str, index: int, seen: set[str]) -> None:
    if not isinstance(rule, dict):
        fail(f"{file_name}: rules[{index}] must be an object")
    missing, extra = REQUIRED - set(rule), set(rule) - REQUIRED
    if missing or extra:
        fail(f"{file_name}: rules[{index}] fields invalid: missing={sorted(missing)}, extra={sorted(extra)}")
    rule_id = rule["id"]
    if not isinstance(rule_id, str) or not re.fullmatch(r"(?:G\.[A-Z]+\.[0-9]+|MYSQL-[A-Z]+-[0-9]{3}|POSTGRESQL-[A-Z]+-[0-9]{3})", rule_id):
        fail(f"{file_name}: invalid id {rule_id!r}")
    if rule_id in seen:
        fail(f"duplicate rule id: {rule_id}")
    seen.add(rule_id)
    if rule["level"] not in VALID_LEVELS or rule["gate"] not in VALID_GATES:
        fail(f"{rule_id}: invalid level/gate")
    expected_gate = "block" if rule["level"] in {"prohibition", "mandatory"} else "warn" if rule["level"] == "recommendation" else "info"
    if rule["gate"] != expected_gate:
        fail(f"{rule_id}: {rule['level']} must map to {expected_gate}")
    if not isinstance(rule["dialects"], list) or not set(rule["dialects"]) <= VALID_DIALECTS or not rule["dialects"]:
        fail(f"{rule_id}: invalid dialects")
    if not isinstance(rule["source"], list) or not rule["source"]:
        fail(f"{rule_id}: source must be non-empty")
    if not isinstance(rule["scope"], list) or not rule["scope"]:
        fail(f"{rule_id}: scope must be non-empty")
    if not isinstance(rule["confirmation_required"], bool):
        fail(f"{rule_id}: confirmation_required must be boolean")
    check = rule["check"]
    if not isinstance(check, dict) or set(check) != {"kind", "detector"} or check["kind"] not in VALID_KINDS:
        fail(f"{rule_id}: invalid check")
    examples = rule["examples"]
    if not isinstance(examples, dict) or set(examples) != {"positive", "negative"}:
        fail(f"{rule_id}: invalid examples")
    for example_name, example in examples.items():
        if not isinstance(example, str) or not example.strip():
            fail(f"{rule_id}: examples.{example_name} must be non-empty")
    for field in ("name", "condition", "remediation"):
        if not isinstance(rule[field], str) or not rule[field].strip():
            fail(f"{rule_id}: {field} must be non-empty")
    if not isinstance(check["detector"], str) or not check["detector"].strip():
        fail(f"{rule_id}: check.detector must be non-empty")


def main() -> int:
    catalog = load_json(CATALOG_PATH)
    if not isinstance(catalog, dict) or catalog.get("catalog_version") != "2.0.0":
        fail("catalog_version must be 2.0.0")
    if set(catalog.get("supported_dialects", [])) != VALID_DIALECTS:
        fail("catalog must support mysql and postgresql")
    expected_order = {"mysql": ["common.json", "mysql.json"], "postgresql": ["common.json", "postgresql.json"]}
    if catalog.get("load_order") != expected_order:
        fail("load_order must apply common plus exactly one dialect file")

    seen: set[str] = set()
    files: dict[str, dict[str, object]] = {}
    for dialect, file_name in catalog["rules"].items():
        payload = load_json(RULES_DIR / file_name)
        if not isinstance(payload, dict) or payload.get("dialect") != dialect:
            fail(f"{file_name}: dialect mismatch")
        for index, rule in enumerate(payload.get("rules", [])):
            validate_rule(rule, file_name, index, seen)
        files[dialect] = payload

    common_ids = {rule["id"] for rule in files["common"]["rules"]}
    if len(common_ids) != EXPECTED_SOURCE_COUNT or not all(re.fullmatch(r"G\.[A-Z]+\.[0-9]+", rule_id) for rule_id in common_ids):
        fail(f"common catalog must contain all {EXPECTED_SOURCE_COUNT} numbered source clauses; got {len(common_ids)}")
    source_domains = Counter(rule_id.split(".")[1] for rule_id in common_ids)
    if dict(source_domains) != EXPECTED_SOURCE_DOMAINS:
        fail(f"common catalog domain coverage mismatch: {dict(source_domains)}")
    for dialect in VALID_DIALECTS:
        if not files[dialect]["rules"]:
            fail(f"{dialect}: dialect catalog must not be empty")
        for rule in files[dialect]["rules"]:
            if rule["dialects"] != [dialect]:
                fail(f"{rule['id']}: dialect file must target only {dialect}")

    levels = Counter(rule["level"] for rule in files["common"]["rules"])
    print(f"OK: {len(seen)} rules ({len(common_ids)} source + {len(seen)-len(common_ids)} dialect), catalog v{catalog['catalog_version']}")
    print(f"common levels: {dict(levels)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
