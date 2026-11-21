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

IMPORT_PATH = ROOT / "scripts" / "import_standard.py"
IMPORT_SPEC = importlib.util.spec_from_file_location("catalog_import_standard", IMPORT_PATH)
assert IMPORT_SPEC and IMPORT_SPEC.loader
import_standard = importlib.util.module_from_spec(IMPORT_SPEC)
sys.modules["catalog_import_standard"] = import_standard
IMPORT_SPEC.loader.exec_module(import_standard)


class RuleCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads((ROOT / "rules" / "common.json").read_text(encoding="utf-8"))
        cls.rules = {rule["id"]: rule for rule in payload["rules"]}
        cls.mysql_rules = {
            rule["id"]: rule
            for rule in json.loads((ROOT / "rules" / "mysql.json").read_text(encoding="utf-8"))["rules"]
        }

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
        self.assertEqual("mandatory", self.mysql_rules["MYSQL-ENC-001"]["level"])
        self.assertEqual("prohibition", self.rules["G.TAB.06"]["level"])

    def test_dialect_differences_are_not_kept_as_common_rules(self) -> None:
        split_sources = {
            source for rule in self.mysql_rules.values() for source in rule["source"]
        }
        self.assertTrue(split_sources.isdisjoint(self.rules))

    def test_mysql_update_static_rule_is_declared_by_guard(self) -> None:
        self.assertEqual("static", self.mysql_rules["MYSQL-UPD-001"]["check"]["kind"])
        self.assertIn("MYSQL-UPD-001", sql_guard.DIALECT_GUARD_RULES["mysql"])

    def test_markdown_cleanup_preserves_sql_asterisks(self) -> None:
        self.assertEqual(
            "禁止 select *，使用 count(*)",
            import_standard.clean("**禁止** `select *`，使用 `count(*)`"),
        )

    def test_imported_select_star_clause_keeps_its_operator(self) -> None:
        markdown = "### **G.SEL.12 禁止使用 `select *`**\n\n不得使用 `select *`。"
        rule = import_standard.parse_clauses(markdown)[0]
        self.assertIn("select *", rule["name"])
        self.assertIn("select *", rule["condition"])


if __name__ == "__main__":
    unittest.main()
