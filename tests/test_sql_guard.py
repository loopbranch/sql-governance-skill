from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sql_guard.py"
SPEC = importlib.util.spec_from_file_location("sql_guard", MODULE_PATH)
assert SPEC and SPEC.loader
sql_guard = importlib.util.module_from_spec(SPEC)
sys.modules["sql_guard"] = sql_guard
SPEC.loader.exec_module(sql_guard)


class SqlGuardTest(unittest.TestCase):
    def rule_ids(self, sql: str, dialect: str) -> set[str]:
        _, findings = sql_guard.inspect("example.sql", sql, dialect)
        return {finding.rule_id for finding in findings}

    def test_string_where_does_not_satisfy_update_filter(self) -> None:
        self.assertIn("G.UPD.01", self.rule_ids("update t_user set note='where x';", "mysql"))

    def test_cte_select_star_is_detected(self) -> None:
        sql = "with active as (select id from t_user) select * from active;"
        self.assertIn("G.SEL.12", self.rule_ids(sql, "postgresql"))

    def test_semicolon_inside_literal_does_not_split_statement(self) -> None:
        statements = sql_guard.split_statements("update t_user set note='a;b' where id=1;")
        self.assertEqual(1, len(statements))

    def test_destructive_alter_variants_are_detected(self) -> None:
        sql = "alter table t_user modify name varchar(32) not null; alter table t_user add column tenant_id bigint not null;"
        self.assertEqual({"G.UPG.05", "G.UPG.07"}, self.rule_ids(sql, "mysql"))

    def test_mysql_valid_create_table_passes_static_checks(self) -> None:
        sql = "create table if not exists t_user (id binary(16) not null, primary key(id)) engine=InnoDB default charset=utf8mb4;"
        self.assertEqual(set(), self.rule_ids(sql, "mysql"))

    def test_postgresql_rejects_mysql_table_options(self) -> None:
        sql = "create table if not exists t_user (id uuid primary key) engine=InnoDB;"
        self.assertIn("POSTGRESQL-TAB-001", self.rule_ids(sql, "postgresql"))

    def test_postgresql_requires_concurrent_index(self) -> None:
        self.assertIn("POSTGRESQL-DDL-001", self.rule_ids("create index idx_user_name on t_user(name);", "postgresql"))
        self.assertNotIn("POSTGRESQL-DDL-001", self.rule_ids("create index concurrently idx_user_name on t_user(name);", "postgresql"))

    def test_auto_dialect_requires_unambiguous_evidence(self) -> None:
        with self.assertRaises(ValueError):
            sql_guard.inspect("portable.sql", "select id from t_user where id=?;", "auto")

    def test_full_join_is_blocked_for_both_dialects(self) -> None:
        sql = "select a.id from t_a a full join t_b b on b.id=a.id;"
        self.assertIn("G.SEL.08", self.rule_ids(sql, "mysql"))
        self.assertIn("G.SEL.08", self.rule_ids(sql, "postgresql"))


if __name__ == "__main__":
    unittest.main()
