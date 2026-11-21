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

    def split_id(self, dialect: str, source_id: str) -> str:
        return sql_guard.split_rule_id(dialect, source_id)

    def test_string_where_does_not_satisfy_update_filter(self) -> None:
        self.assertIn(self.split_id("mysql", "G.UPD.01"), self.rule_ids("update t_user set note='where x';", "mysql"))

    def test_cte_select_star_is_detected(self) -> None:
        sql = "with active as (select id from t_user) select * from active;"
        self.assertIn(self.split_id("postgresql", "G.SEL.12"), self.rule_ids(sql, "postgresql"))

    def test_semicolon_inside_literal_does_not_split_statement(self) -> None:
        statements = sql_guard.split_statements("update t_user set note='a;b' where id=1;")
        self.assertEqual(1, len(statements))

    def test_destructive_alter_variants_are_detected(self) -> None:
        sql = "alter table t_user modify name varchar(32) not null; alter table t_user add column tenant_id bigint not null;"
        self.assertEqual({"MYSQL-UPG-005", "MYSQL-UPG-007", "MYSQL-UPG-008"}, self.rule_ids(sql, "mysql"))

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
            self.assertIn("MYSQL-SEL-008", self.rule_ids(sql, "mysql"))
            self.assertIn("POSTGRESQL-SEL-008", self.rule_ids(sql, "postgresql"))

    def test_update_word_outside_main_dml_is_not_misclassified(self) -> None:
        sql = "select id from t_user where id=1 for update;"
        self.assertNotIn(self.split_id("postgresql", "G.UPD.01"), self.rule_ids(sql, "postgresql"))
        ddl = "create table if not exists t_user (id bigint primary key, updated_at datetime on update current_timestamp);"
        self.assertNotIn(self.split_id("mysql", "G.UPD.01"), self.rule_ids(ddl, "mysql"))

    def test_tautology_with_real_predicate_is_valid(self) -> None:
        mysql_update = self.split_id("mysql", "G.UPD.01")
        self.assertNotIn(mysql_update, self.rule_ids("update t_user set name=? where 1=1 and id=?;", "mysql"))
        self.assertIn(mysql_update, self.rule_ids("update t_user set name=? where (1=1);", "mysql"))

    def test_quoted_identifiers_are_not_clause_keywords(self) -> None:
        rules = self.rule_ids('update t_user set "where" = 1;', "postgresql")
        self.assertIn(self.split_id("postgresql", "G.UPD.01"), rules)
        rules = self.rule_ids("update t_user set `limit` = 1 where id = 2;", "mysql")
        self.assertNotIn("POSTGRESQL-UPD-001", rules)

    def test_update_clauses_only_apply_at_top_level(self) -> None:
        sql = "with batch as (select id from t_user order by id limit 1000) update t_user set active=false from batch where t_user.id=batch.id;"
        rules = self.rule_ids(sql, "postgresql")
        self.assertNotIn("POSTGRESQL-UPD-002", rules)
        self.assertNotIn("POSTGRESQL-UPD-001", rules)
        self.assertNotIn(self.split_id("postgresql", "G.UPD.01"), rules)

    def test_drop_non_column_objects_is_not_drop_column(self) -> None:
        for action in ("drop index idx_user", "drop constraint ck_user", "drop primary key"):
            self.assertNotIn(self.split_id("mysql", "G.UPG.03"), self.rule_ids(f"alter table t_user {action};", "mysql"))
        self.assertIn(self.split_id("mysql", "G.UPG.03"), self.rule_ids("alter table t_user drop column name;", "mysql"))

    def test_check_constraint_is_not_new_not_null_column(self) -> None:
        sql = "alter table t_user add constraint ck_name check (name is not null);"
        self.assertNotIn("POSTGRESQL-UPG-007", self.rule_ids(sql, "postgresql"))

    def test_postgresql_alter_column_variants_are_detected(self) -> None:
        sql = "alter table t_user alter column name type varchar(64); alter table t_user alter column name set not null;"
        self.assertEqual({"POSTGRESQL-UPG-005", "POSTGRESQL-UPG-008"}, self.rule_ids(sql, "postgresql"))

    def test_postgresql_table_level_serial_and_identity_pk_are_detected(self) -> None:
        for sql in (
            "create table if not exists t_user (id bigserial, primary key (id));",
            "create table if not exists t_user (id bigint generated always as identity, constraint pk_user primary key (id));",
        ):
            self.assertIn("POSTGRESQL-PK-001", self.rule_ids(sql, "postgresql"))

    def test_temporary_and_unlogged_tables_receive_table_checks(self) -> None:
        for sql in ("create temporary table t_tmp (id bigint);", "create unlogged table t_tmp (id bigint);"):
            rules = self.rule_ids(sql, "postgresql")
            self.assertIn(self.split_id("postgresql", "G.UPG.10"), rules)
            self.assertIn(self.split_id("postgresql", "G.TAB.16"), rules)

    def test_cte_insert_without_columns_is_detected(self) -> None:
        sql = "with source as (select 1 as id) insert into t_user values (1);"
        self.assertIn(self.split_id("postgresql", "G.INS.01"), self.rule_ids(sql, "postgresql"))

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
        self.assertIn(self.split_id("postgresql", "G.SEL.12"), self.rule_ids(pg, "postgresql"))
        mysql = "select 5 # comment ; hidden\n; select id from t_user;"
        self.assertEqual(2, len(sql_guard.split_statements(mysql, "mysql")))

    def test_mysql_double_dash_requires_following_whitespace(self) -> None:
        sql = "select 1--2; select * from t_user;"
        self.assertEqual(2, len(sql_guard.split_statements(sql, "mysql")))
        self.assertIn(self.split_id("mysql", "G.SEL.12"), self.rule_ids(sql, "mysql"))

    def test_postgresql_plain_strings_do_not_backslash_escape_quotes(self) -> None:
        sql = "select 'a\\'; select * from t_user;"
        self.assertEqual(2, len(sql_guard.split_statements(sql, "postgresql")))
        self.assertIn(self.split_id("postgresql", "G.SEL.12"), self.rule_ids(sql, "postgresql"))
        escaped = "select E'a\\\';b'; select id from t_user;"
        self.assertEqual(2, len(sql_guard.split_statements(escaped, "postgresql")))

    def test_mysql_default_double_quoted_strings_use_backslash_escapes(self) -> None:
        sql = 'select "a\\\";b"; select id from t_user;'
        self.assertEqual(2, len(sql_guard.split_statements(sql, "mysql")))

    def test_mysql_does_not_treat_dollar_tags_as_strings(self) -> None:
        sql = "select $tag$; select * from t_user; select $tag$;"
        self.assertEqual(3, len(sql_guard.split_statements(sql, "mysql")))
        self.assertIn(self.split_id("mysql", "G.SEL.12"), self.rule_ids(sql, "mysql"))

    def test_postgresql_nested_block_comments_do_not_leak_sql(self) -> None:
        sql = "/* outer /* select * from hidden; */ still hidden */ select id from shown;"
        self.assertEqual(1, len(sql_guard.split_statements(sql, "postgresql")))
        self.assertNotIn(self.split_id("postgresql", "G.SEL.12"), self.rule_ids(sql, "postgresql"))

    def test_postgresql_data_modifying_ctes_receive_dml_checks(self) -> None:
        cases = {
            "with deleted as (delete from t_user returning id) select count(*) from deleted;": self.split_id("postgresql", "G.DEL.01"),
            "with changed as (update t_user set active=false returning id) select count(*) from changed;": self.split_id("postgresql", "G.UPD.01"),
            "with inserted as (insert into t_user values (1) returning id) select count(*) from inserted;": self.split_id("postgresql", "G.INS.01"),
        }
        for sql, expected in cases.items():
            self.assertIn(expected, self.rule_ids(sql, "postgresql"))

    def test_uuid_primary_key_storage_is_dialect_specific(self) -> None:
        mysql = "create table if not exists t_user (id char(36) primary key) engine=InnoDB default charset=utf8mb4;"
        self.assertIn("MYSQL-PK-001", self.rule_ids(mysql, "mysql"))
        for definition in ("id char(36) primary key", "id binary(16) primary key", "id bytea primary key"):
            sql = f"create table if not exists t_user ({definition});"
            self.assertIn("POSTGRESQL-PK-001", self.rule_ids(sql, "postgresql"))

    def test_weak_identifier_names_do_not_decide_auto_dialect(self) -> None:
        with self.assertRaises(ValueError):
            sql_guard.inspect("weak.sql", "select jsonb from t_user where id=?;", "auto")
        dialect, _ = sql_guard.inspect(
            "postgres.sql",
            "create table if not exists t_user (id uuid primary key, unsigned text);",
            "auto",
        )
        self.assertEqual("postgresql", dialect)

    def test_findings_never_use_the_other_dialect_rule_ids(self) -> None:
        mysql_sql = "create table t_user (id bigint auto_increment primary key); select * from t_user;"
        _, mysql_findings = sql_guard.inspect("mysql.sql", mysql_sql, "mysql")
        self.assertTrue(mysql_findings)
        self.assertTrue(all(item.rule_id.startswith("MYSQL-") for item in mysql_findings))

        postgresql_sql = "create table t_user (id bigserial primary key) engine=InnoDB; select * from t_user;"
        _, postgresql_findings = sql_guard.inspect("postgresql.sql", postgresql_sql, "postgresql")
        self.assertTrue(postgresql_findings)
        self.assertTrue(all(item.rule_id.startswith("POSTGRESQL-") for item in postgresql_findings))


if __name__ == "__main__":
    unittest.main()
