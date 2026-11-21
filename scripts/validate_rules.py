#!/usr/bin/env python3
"""Validate the SQL governance catalog without third-party dependencies."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "rules" / "catalog.json"
VALID_LEVELS = {"prohibition", "mandatory", "recommendation", "reference"}
VALID_GATES = {"block", "warn", "info"}
VALID_KINDS = {"static", "manual", "hybrid"}
REQUIRED = {
    "id",
    "source",
    "name",
    "level",
    "gate",
    "scope",
    "condition",
    "check",
    "examples",
    "remediation",
    "confirmation_required",
}


def fail(message: str) -> None:
    raise ValueError(message)


def validate_rule(rule: object, index: int, seen: set[str]) -> None:
    if not isinstance(rule, dict):
        fail(f"rules[{index}] must be an object")
    missing = REQUIRED - set(rule)
    extra = set(rule) - REQUIRED
    if missing or extra:
        fail(f"rules[{index}] fields invalid: missing={sorted(missing)}, extra={sorted(extra)}")

    rule_id = rule["id"]
    if not isinstance(rule_id, str) or not re.fullmatch(r"SQL-[A-Z]+-[0-9]{3}", rule_id):
        fail(f"rules[{index}].id is invalid: {rule_id!r}")
    if rule_id in seen:
        fail(f"duplicate rule id: {rule_id}")
    seen.add(rule_id)

    if rule["level"] not in VALID_LEVELS or rule["gate"] not in VALID_GATES:
        fail(f"{rule_id}: invalid level/gate")
    expected_gate = "block" if rule["level"] in {"prohibition", "mandatory"} else "warn" if rule["level"] == "recommendation" else "info"
    if rule["gate"] != expected_gate:
        fail(f"{rule_id}: {rule['level']} must map to {expected_gate}")
    if not isinstance(rule["source"], list) or not rule["source"]:
        fail(f"{rule_id}: source must be a non-empty list")
    if not isinstance(rule["scope"], list) or not rule["scope"]:
        fail(f"{rule_id}: scope must be a non-empty list")
    if not isinstance(rule["confirmation_required"], bool):
        fail(f"{rule_id}: confirmation_required must be boolean")

    check = rule["check"]
    if not isinstance(check, dict) or set(check) != {"kind", "detector"}:
        fail(f"{rule_id}: check must contain kind and detector")
    if check["kind"] not in VALID_KINDS:
        fail(f"{rule_id}: invalid check kind")
    examples = rule["examples"]
    if not isinstance(examples, dict) or set(examples) != {"positive", "negative"}:
        fail(f"{rule_id}: examples must contain positive and negative")
    for field in ("name", "condition", "remediation"):
        if not isinstance(rule[field], str) or not rule[field].strip():
            fail(f"{rule_id}: {field} must be a non-empty string")


def main() -> int:
    with CATALOG_PATH.open(encoding="utf-8") as catalog_file:
        catalog = json.load(catalog_file)
    if set(catalog) != {"catalog_version", "dialect", "rules"}:
        fail("catalog must contain exactly catalog_version, dialect, and rules")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", catalog["catalog_version"]):
        fail("catalog_version must use SemVer without a v prefix")
    if not isinstance(catalog["rules"], list) or not catalog["rules"]:
        fail("rules must be a non-empty list")

    seen: set[str] = set()
    for index, rule in enumerate(catalog["rules"]):
        validate_rule(rule, index, seen)
    print(f"OK: {len(seen)} rules, catalog v{catalog['catalog_version']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
