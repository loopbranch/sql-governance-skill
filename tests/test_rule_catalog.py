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

VALIDATE_PATH = ROOT / "scripts" / "validate_rules.py"
VALIDATE_SPEC = importlib.util.spec_from_file_location("catalog_validate_rules", VALIDATE_PATH)
assert VALIDATE_SPEC and VALIDATE_SPEC.loader
validate_rules = importlib.util.module_from_spec(VALIDATE_SPEC)
sys.modules["catalog_validate_rules"] = validate_rules
VALIDATE_SPEC.loader.exec_module(validate_rules)


class RuleCatalogTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload = json.loads((ROOT / "rules" / "common.json").read_text(encoding="utf-8"))
        cls.rules = {rule["id"]: rule for rule in payload["rules"]}
        cls.mysql_rules = {
            rule["id"]: rule
            for rule in json.loads((ROOT / "rules" / "mysql.json").read_text(encoding="utf-8"))["rules"]
        }
        cls.postgresql_rules = {
            rule["id"]: rule
            for rule in json.loads((ROOT / "rules" / "postgresql.json").read_text(encoding="utf-8"))["rules"]
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

    def test_common_catalog_is_exactly_the_audited_allowlist(self) -> None:
        self.assertEqual(validate_rules.EXPECTED_COMMON_IDS, set(self.rules))

    def test_every_noncommon_source_has_both_dialect_variants(self) -> None:
        expected_sources = {
            f"G.{domain}.{number:02d}"
            for domain, count in validate_rules.EXPECTED_SOURCE_DOMAINS.items()
            for number in range(1, count + 1)
        }
        mysql_sources = {source for rule in self.mysql_rules.values() for source in rule["source"]}
        postgresql_sources = {source for rule in self.postgresql_rules.values() for source in rule["source"]}
        expected_split = expected_sources - set(self.rules)
        self.assertEqual(expected_split, mysql_sources)
        self.assertEqual(expected_split, postgresql_sources)

    def test_generated_variants_are_dialect_scoped_and_have_evidence_examples(self) -> None:
        for dialect, rules in (("mysql", self.mysql_rules), ("postgresql", self.postgresql_rules)):
            for rule in rules.values():
                self.assertEqual([dialect], rule["dialects"])
                self.assertTrue(rule["examples"]["positive"].strip())
                self.assertTrue(rule["examples"]["negative"].strip())

    def test_audit_table_lists_all_154_sources_once(self) -> None:
        audit = (ROOT / "references" / "dialect-isolation-audit.md").read_text(encoding="utf-8")
        for domain, count in validate_rules.EXPECTED_SOURCE_DOMAINS.items():
            for number in range(1, count + 1):
                source = f"G.{domain}.{number:02d}"
                self.assertEqual(1, audit.count(f"| `{source}` |"), source)

    def test_mysql_update_static_rule_is_declared_by_guard(self) -> None:
        self.assertEqual("static", self.mysql_rules["MYSQL-UPD-001"]["check"]["kind"])
        self.assertIn("MYSQL-UPD-001", sql_guard.DIALECT_GUARD_RULES["mysql"])

    def test_shared_examples_and_style_gate(self) -> None:
        for rule_id in ("G.FMT.02", "G.FMT.03", "G.FMT.07", "G.NAM.05"):
            self.assertEqual("warn", self.rules[rule_id]["gate"])
        self.assertIn("decimal(19,4)", self.rules["G.TAB.09"]["examples"]["positive"])
        self.assertIn("= null", self.rules["G.SEL.21"]["examples"]["negative"])
        self.assertIn("date(created_at)", self.rules["G.SEL.25"]["examples"]["negative"])

    def test_dialect_catalog_matches_executable_checks(self) -> None:
        for dialect, rules in (("mysql", self.mysql_rules), ("postgresql", self.postgresql_rules)):
            expected = {
                r["id"] for r in rules.values()
                if r["check"]["kind"] == "static" or "review_gate" in r["check"]
            }
            self.assertEqual(expected, sql_guard.DIALECT_GUARD_RULES[dialect])
            self.assertEqual("warn", rules[f"{dialect.upper()}-DEL-002"]["gate"])

    def test_markdown_cleanup_preserves_sql_asterisks(self) -> None:
        self.assertEqual(
            "禁止 select *，使用 count(*)",
            import_standard.clean("**禁止** `select *`，使用 `count(*)`"),
        )

    def test_imported_select_star_clause_keeps_its_operator(self) -> None:
        markdown = "### **G.SEL.12 禁止使用 `select *`**\n\n不得使用 `select *`。"
        self.assertEqual([], import_standard.parse_clauses(markdown))
        self.assertIn("select *", import_standard.clean("禁止使用 `select *`"))


if __name__ == "__main__":
    unittest.main()
