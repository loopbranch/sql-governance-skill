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

    def test_postgresql_index_concurrency_remains_hybrid(self) -> None:
        self.assertNotIn("POSTGRESQL-DDL-001", self.rule_ids("create index idx_user_name on t_user(name);", "postgresql"))
        self.assertNotIn("POSTGRESQL-DDL-001", self.rule_ids("create index concurrently idx_user_name on t_user(name);", "postgresql"))

    def test_auto_dialect_requires_unambiguous_evidence(self) -> None:
        with self.assertRaises(ValueError):
            sql_guard.inspect("portable.sql", "select id from t_user where id=?;", "auto")

    def test_full_join_is_blocked_for_both_dialects(self) -> None:
        for sql in (
            "select a.id from t_a a full join t_b b on b.id=a.id;",
            "select a.id from t_a a full outer join t_b b on b.id=a.id;",
        ):
            self.assertIn("G.SEL.08", self.rule_ids(sql, "mysql"))
            self.assertIn("G.SEL.08", self.rule_ids(sql, "postgresql"))

    def test_update_word_outside_main_dml_is_not_misclassified(self) -> None:
        sql = "select id from t_user where id=1 for update;"
        self.assertNotIn("G.UPD.01", self.rule_ids(sql, "postgresql"))
        ddl = "create table if not exists t_user (id bigint primary key, updated_at datetime on update current_timestamp);"
        self.assertNotIn("G.UPD.01", self.rule_ids(ddl, "mysql"))

    def test_tautology_with_real_predicate_is_valid(self) -> None:
        self.assertNotIn("G.UPD.01", self.rule_ids("update t_user set name=? where 1=1 and id=?;", "mysql"))
        self.assertIn("G.UPD.01", self.rule_ids("update t_user set name=? where (1=1);", "mysql"))

    def test_quoted_identifiers_are_not_clause_keywords(self) -> None:
        rules = self.rule_ids('update t_user set "where" = 1;', "postgresql")
        self.assertIn("G.UPD.01", rules)
        rules = self.rule_ids("update t_user set `limit` = 1 where id = 2;", "mysql")
        self.assertNotIn("G.UPD.03", rules)

    def test_update_clauses_only_apply_at_top_level(self) -> None:
        sql = "with batch as (select id from t_user order by id limit 1000) update t_user set active=false from batch where t_user.id=batch.id;"
        rules = self.rule_ids(sql, "postgresql")
        self.assertNotIn("G.UPD.02", rules)
        self.assertNotIn("G.UPD.03", rules)
        self.assertNotIn("G.UPD.01", rules)

    def test_drop_non_column_objects_is_not_drop_column(self) -> None:
        for action in ("drop index idx_user", "drop constraint ck_user", "drop primary key"):
            self.assertNotIn("G.UPG.03", self.rule_ids(f"alter table t_user {action};", "mysql"))
        self.assertIn("G.UPG.03", self.rule_ids("alter table t_user drop column name;", "mysql"))

    def test_check_constraint_is_not_new_not_null_column(self) -> None:
        sql = "alter table t_user add constraint ck_name check (name is not null);"
        self.assertNotIn("G.UPG.07", self.rule_ids(sql, "postgresql"))

    def test_postgresql_alter_column_variants_are_detected(self) -> None:
        sql = "alter table t_user alter column name type varchar(64); alter table t_user alter column name set not null;"
        self.assertEqual({"G.UPG.05", "G.UPG.08"}, self.rule_ids(sql, "postgresql"))

    def test_postgresql_table_level_serial_and_identity_pk_are_detected(self) -> None:
        for sql in (
            "create table if not exists t_user (id bigserial, primary key (id));",
            "create table if not exists t_user (id bigint generated always as identity, constraint pk_user primary key (id));",
        ):
            self.assertIn("POSTGRESQL-PK-001", self.rule_ids(sql, "postgresql"))

    def test_temporary_and_unlogged_tables_receive_table_checks(self) -> None:
        for sql in ("create temporary table t_tmp (id bigint);", "create unlogged table t_tmp (id bigint);"):
            rules = self.rule_ids(sql, "postgresql")
            self.assertIn("G.UPG.10", rules)
            self.assertIn("G.TAB.16", rules)

    def test_cte_insert_without_columns_is_detected(self) -> None:
        sql = "with source as (select 1 as id) insert into t_user values (1);"
        self.assertIn("G.INS.01", self.rule_ids(sql, "postgresql"))

    def test_all_mysql_charset_declarations_are_checked(self) -> None:
        sql = "create table if not exists t_user (id binary(16) primary key, name varchar(20) character set latin1) engine=InnoDB default charset=utf8mb4;"
        self.assertIn("MYSQL-ENC-001", self.rule_ids(sql, "mysql"))

    def test_auto_detects_all_postgresql_serial_types(self) -> None:
        for data_type in ("smallserial", "serial", "bigserial"):
            dialect, _ = sql_guard.inspect("example.sql", f"create table if not exists t_user (id {data_type} primary key);", "auto")
            self.assertEqual("postgresql", dialect)

    def test_hash_comment_is_mysql_only(self) -> None:
        pg = "select 5 # 3; select * from t_user;"
        self.assertEqual(2, len(sql_guard.split_statements(pg, "postgresql")))
        self.assertIn("G.SEL.12", self.rule_ids(pg, "postgresql"))
        mysql = "select 5 # comment ; hidden\n; select id from t_user;"
        self.assertEqual(2, len(sql_guard.split_statements(mysql, "mysql")))


if __name__ == "__main__":
    unittest.main()
