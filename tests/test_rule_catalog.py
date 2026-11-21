from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GUARD_PATH = ROOT / "scripts" / "sql_guard.py"
SPEC = importlib.util.spec_from_file_location("catalog_sql_guard", GUARD_PATH)
assert SPEC and SPEC.loader
sql_guard = importlib.util.module_from_spec(SPEC)
sys.modules["catalog_sql_guard"] = sql_guard
SPEC.loader.exec_module(sql_guard)


class RuleCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads((ROOT / "rules" / "common.json").read_text(encoding="utf-8"))
        cls.rules = {rule["id"]: rule for rule in payload["rules"]}

    def test_static_catalog_matches_guard_coverage(self) -> None:
        static_ids = {
            rule_id for rule_id, rule in self.rules.items()
            if rule["check"]["kind"] == "static"
        }
        self.assertEqual(sql_guard.COMMON_GUARD_RULES, static_ids)

    def test_examples_are_concrete_scenarios(self) -> None:
        for rule in self.rules.values():
            for example in rule["examples"].values():
                self.assertTrue(example.strip())
                self.assertFalse(example.startswith("满足“"))
                self.assertFalse(example.startswith("违反“"))

    def test_source_body_contributes_to_severity(self) -> None:
        self.assertEqual("recommendation", self.rules["G.DBS.05"]["level"])
        self.assertEqual("prohibition", self.rules["G.TAB.06"]["level"])


if __name__ == "__main__":
    unittest.main()
