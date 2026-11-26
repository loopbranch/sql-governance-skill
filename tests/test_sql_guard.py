from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sql_guard.py"
SPEC = importlib.util.spec_from_file_location("sql_guard", MODULE_PATH)
assert SPEC and SPEC.loader
sql_guard = importlib.util.module_from_spec(SPEC)
sys.modules["sql_guard"] = sql_guard
SPEC.loader.exec_module(sql_guard)


class SqlGuardTest(unittest.TestCase):
    def test_archive_gate_requires_matching_replay_for_every_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sql = {
                "upgrade.sql": "INSERT INTO t (id) VALUES (1);\n",
                "rollback.sql": "DELETE FROM t WHERE id = 1;\n",
            }
            runs = [{"database": "isolated", "success": True, "schema_sha256": "a" * 64, "data_sha256": "b" * 64}] * 2
            receipt = {"version": 1, "batches": [
                {"dialect": "postgresql", "files": [{"path": path, "sha256": sha256(source.encode()).hexdigest()}],
                 "runs": runs} for path, source in sql.items()
            ]}
            for path, source in sql.items():
                (root / path).write_text(source, encoding="utf-8")
            command = [sys.executable, str(MODULE_PATH), "--dialect", "postgresql", "--archived-sql", "--format", "json"]

            def result(extra: list[str]) -> int:
                return subprocess.run(command + extra + list(sql), cwd=root, capture_output=True, check=False).returncode

            self.assertEqual(1, result([]))
            path = root / "replay.json"
            args = ["--archive-replay-evidence", str(path)]
            path.write_text(json.dumps(receipt), encoding="utf-8")
            self.assertEqual(0, result(args))
            first, second = receipt["batches"]
            for changed in (
                [first],
                [first, first],
                [first, {**second, "dialect": "mysql"}],
                [first, {**second, "files": [{**second["files"][0], "sha256": "c" * 64}]}],
                [first, {**second, "runs": runs[:1]}],
                *([
                    first, {**second, "runs": [runs[0], {**runs[1], **update}]}
                ] for update in (
                    {"database": "another"},
                    {"success": False},
                    {"schema_sha256": "c" * 64},
                    {"data_sha256": "c" * 64},
                )),
            ):
                with self.subTest(batches=changed):
                    path.write_text(json.dumps({**receipt, "batches": changed}), encoding="utf-8")
                    self.assertEqual(1, result(args))

    def test_archived_postgresql_add_column_requires_replay_protection(self) -> None:
        for sql, blocked in (
            ("ALTER TABLE t_project ADD COLUMN template_id character varying(128);", True),
            ('ALTER TABLE "t_project"ADD COLUMN "template_id"varchar(128);', True),
            ('ALTER TABLE"t_project" ADD COLUMN"template_id"varchar(128);', True),
            ('ALTER TABLE t_project ADD"template_id"text;', True),
            ('ALTER TABLE t_project ADD COLUMN IF NOT EXISTS"template_id"text;', False),
            ('ALTER TABLE ONLY (t_project) ADD COLUMN template_id text;', True),
            ('ALTER TABLE ONLY"t_project" ADD COLUMN template_id text;', True),
            ('ALTER TABLE U&"t_project" ADD COLUMN U&"template_id" text;', True),
            ('ALTER TABLE ONLY "t,project" ADD COLUMN IF NOT EXISTS a numeric(12,2), ADD "template,id" text;', True),
            ("ALTER TABLE t_project ADD COLUMN /* replay */ IF NOT EXISTS template_id text;", False),
            ("ALTER TABLE t_project ADD CONSTRAINT sample CHECK (true);", False),
            ('ALTER TABLE t_project ADD IF NOT EXISTS "constraint" text;', False),
        ):
            with self.subTest(sql=sql):
                _, findings = sql_guard.inspect("archive.sql", sql, "postgresql", archived_sql=True)
                self.assertEqual(blocked, any(
                    item.rule_id == "POSTGRESQL-UPG-012" for item in findings
                ))

    def test_verified_rollback_only_covers_the_exact_inverse_operation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            upgrade = "sql/upgrade/v0101/ddl.sql"
            rollback = "sql/rollback/v0101/ddl.sql"
            drop = "ALTER TABLE t DROP COLUMN IF EXISTS feature;"
            files = {
                upgrade: "-- upgrade\nALTER TABLE t ADD COLUMN feature text;\n",
                rollback: f"-- verified inverse\n{drop}\nALTER TABLE t DROP COLUMN old_column;\n",
            }
            members = []
            for direction, path in (("upgrade", upgrade), ("rollback", rollback)):
                (root / path).parent.mkdir(parents=True)
                (root / path).write_text(files[path], encoding="utf-8")
                members.append({
                    "path": path, "direction": direction, "kind": "ddl", "execution": "sql",
                    "sha256": sha256(files[path].encode()).hexdigest(),
                })
            batch = {
                "batch": "v0101", "dialect": "postgresql", "database_version": "16.15", "files": members,
                "schema_equal": True, "data_equal": True, "syntax_verified": True,
                "operations": [{"path": rollback, "line": 2, "sql": drop}],
            }
            receipt = root / "receipt.json"
            command = [sys.executable, str(MODULE_PATH), "--dialect", "postgresql", "--format", "json"]
            baseline = subprocess.run(command + [upgrade, rollback], cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(1, baseline.returncode)
            self.assertEqual(2, len(json.loads(baseline.stdout)["findings"]))

            command += ["--migration-evidence", str(receipt), upgrade, rollback]
            for updates, expected_remaining in (({}, 1), ({"data_equal": False}, 2),
                                                 ({"operations": [{"path": upgrade, "line": 2, "sql": drop}]}, 2)):
                with self.subTest(updates=updates):
                    receipt.write_text(json.dumps({"version": 1, "batches": [batch | updates]}), encoding="utf-8")
                    result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
                    self.assertEqual(1, result.returncode)
                    report = json.loads(result.stdout)
                    self.assertEqual(expected_remaining, len(report["findings"]))
                    self.assertEqual(not updates, bool(report["normal_rollbacks"]))
                    self.assertEqual(bool(updates), bool(report["migration_evidence_errors"]))

            receipt.write_text(json.dumps({"version": 1, "batches": [batch]}), encoding="utf-8")
            (root / upgrade).write_text(files[upgrade] + "-- changed\n", encoding="utf-8")
            stale = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(1, stale.returncode)
            self.assertIn("different digest", json.loads(stale.stdout)["migration_evidence_errors"][0])

    def rule_ids(self, sql: str, dialect: str) -> set[str]:
        _, findings = sql_guard.inspect("example.sql", sql, dialect)
        return {finding.rule_id for finding in findings}

    def split_id(self, dialect: str, source_id: str) -> str:
        return sql_guard.split_rule_id(dialect, source_id)

    def test_truncate_is_blocked_in_both_dialects(self) -> None:
        for dialect, sql in [
            ("mysql", "TRUNCATE TABLE `t_job`;"),
            ("mysql", "/* archived */\n/*!50000 TRUNCATE t_job */;"),
            ("postgresql", 'TRUNCATE ONLY "t_job", t_other RESTART IDENTITY CASCADE;'),
        ]:
            with self.subTest(dialect=dialect, sql=sql):
                _, findings = sql_guard.inspect("example.sql", sql, dialect)
                self.assertEqual([(f"{dialect.upper()}-DML-001", "block")], [(item.rule_id, item.gate) for item in findings])

    def test_truncate_in_literal_or_comment_is_not_a_command(self) -> None:
        for dialect in ["mysql", "postgresql"]:
            with self.subTest(dialect=dialect):
                sql = "/* TRUNCATE TABLE t_job; */ SELECT '/*!50000 TRUNCATE TABLE t_job */' AS note;"
                self.assertNotIn(f"{dialect.upper()}-DML-001", self.rule_ids(sql, dialect))

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

    def test_postgresql_table_syntax_ignores_ordinary_identifiers(self) -> None:
        for sql in (
            "select id from import_batch where engine = 'ffmpeg' and auto_increment = true;",
            "update import_batch set engine = 'ffmpeg' where id = 42;",
            "select engine, charset, auto_increment from import_batch;",
            "create view enabled as select id from t where auto_increment = true;",
            "create table if not exists inventory (id uuid primary key, auto_increment boolean, "
            "engine text check (engine = 'x'), charset text check (charset = 'utf8'));",
            "create table if not exists inventory (id uuid primary key, value custom.auto_increment, "
            "flag int default case when true then auto_increment '1' else 0 end) using engine tablespace charset;",
            "alter table café alter column flag set default engine 'on' = engine 'off';",
            "alter table inventory add column auto_increment boolean;",
            "alter table inventory add index varchar(10);",
            "alter table inventory add column engine text constraint auto_increment check (engine = 'x');",
            'create table if not exists "engine" (id uuid primary key, "auto_increment" boolean);',
            'select id from "legacy`name" where id = 1;',
        ):
            with self.subTest(sql=sql):
                self.assertNotIn("POSTGRESQL-TAB-001", self.rule_ids(sql, "postgresql"))

    def test_postgresql_warns_on_mysql_table_syntax(self) -> None:
        for sql in (
            "create table if not exists t_user (id uuid primary key) engine=InnoDB;",
            "create table if not exists t_user (id int primary key) engine InnoDB;",
            "create table if not exists t_user (id int primary key) default character set utf8mb4;",
            "create table if not exists t_user (id bigint comment 'identity' auto_increment primary key);",
            "create table if not exists t_user (id bigint primary key) auto_increment 1024;",
            "alter table café add column status int, engine=InnoDB;",
            "alter table t_user auto_increment = 1024;",
            "alter table t_user add (id bigint auto_increment primary key, quantity bigint);",
            "alter table t_user add column total bigint generated always as (0) stored, "
            "add column id bigint auto_increment primary key;",
            "alter table t_user modify column name varchar(64) not null;",
            "alter table t_user change column old_name new_name varchar(64);",
            "alter table t_user convert to character set utf8mb4;",
            "alter table t_user add column name varchar(20) character set utf8mb4;",
            "alter table t_user drop index idx_user;",
            "alter table t_user drop foreign key fk_user;",
            "alter table t_user drop primary key;",
            "alter table t_user drop partition p1;",
            "alter table t_user add index idx_user (id);",
            "create table if not exists t_user (id int unsigned primary key);",
            "create table if not exists t_user (id int primary key) row_format=dynamic;",
            "create table if not exists t_user (id int primary key) comment='users';",
            "select id from `inventory`;",
        ):
            with self.subTest(sql=sql):
                _, findings = sql_guard.inspect("table.sql", sql, "postgresql")
                self.assertEqual([("POSTGRESQL-TAB-001", "warn")], [
                    (item.rule_id, item.gate) for item in findings
                ])

    def test_postgresql_drop_column_named_index_is_still_blocked(self) -> None:
        for action in ("drop index cascade", "drop column index", "drop index idx_user, drop column legacy"):
            with self.subTest(action=action):
                _, findings = sql_guard.inspect("table.sql", f"alter table t_user {action};", "postgresql")
                self.assertIn(("POSTGRESQL-GUPG-003", "block"), [
                    (item.rule_id, item.gate) for item in findings
                ])

    def test_adding_postgresql_foreign_key_is_still_blocked(self) -> None:
        sql = "alter table t_child add constraint fk_parent foreign key (parent_id) references t_parent(id);"
        _, findings = sql_guard.inspect("table.sql", sql, "postgresql")
        self.assertEqual([("POSTGRESQL-GTAB-004", "block")], [
            (item.rule_id, item.gate) for item in findings
        ])

    def test_postgresql_inline_foreign_keys_can_omit_referenced_columns(self) -> None:
        for sql in (
            "create table if not exists child (id int primary key, parent_id int references public.parent);",
            'alter table public.child add column parent_id int references "other schema"."parent table";',
            "alter table child add column parent_id int references public.parent (id);",
        ):
            with self.subTest(sql=sql):
                _, findings = sql_guard.inspect("table.sql", sql, "postgresql")
                self.assertEqual([("POSTGRESQL-GTAB-004", "block")], [
                    (item.rule_id, item.gate) for item in findings
                ])

        for sql in (
            '''create table if not exists child (id int primary key, note text default 'references public.parent');''',
            'alter table child add column value int constraint "references parent" check (value is not null);',
            'alter table child drop constraint "references parent";',
        ):
            with self.subTest(sql=sql):
                self.assertNotIn("POSTGRESQL-GTAB-004", self.rule_ids(sql, "postgresql"))

    def test_auto_detects_table_syntax_by_position(self) -> None:
        pg = "create table if not exists t_user (id uuid primary key, engine text check (engine = 'x'));"
        mysql = "create table if not exists t_user (id int primary key) engine innodb;"
        self.assertEqual("postgresql", sql_guard.detect_dialect(pg))
        self.assertEqual("mysql", sql_guard.detect_dialect(mysql))

    def test_postgresql_index_concurrency_remains_hybrid(self) -> None:
        self.assertNotIn("POSTGRESQL-DDL-001", self.rule_ids("create index idx_user_name on t_user(name);", "postgresql"))
        self.assertNotIn("POSTGRESQL-DDL-001", self.rule_ids("create index concurrently idx_user_name on t_user(name);", "postgresql"))

    def test_auto_dialect_requires_unambiguous_evidence(self) -> None:
        with self.assertRaises(ValueError):
            sql_guard.inspect("portable.sql", "select id from t_user where id=?;", "auto")

    def test_full_join_is_allowed_only_in_postgresql(self) -> None:
        for sql in (
            "select a.id from t_a a full join t_b b on b.id=a.id;",
            "select a.id from t_a a full outer join t_b b on b.id=a.id;",
        ):
            self.assertIn("MYSQL-SEL-008", self.rule_ids(sql, "mysql"))
            self.assertNotIn("POSTGRESQL-SEL-008", self.rule_ids(sql, "postgresql"))

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
        for action in (
            "add constraint ck_name check (name is not null)",
            "add column name text check (name is not null)",
            'add column "full name" text check ("full name" is not null)',
            "add column name text default 'not null'",
        ):
            with self.subTest(action=action):
                self.assertNotIn(
                    "POSTGRESQL-UPG-007",
                    self.rule_ids(f"alter table t_user {action};", "postgresql"),
                )

    def test_postgresql_add_column_with_declared_not_null_is_blocked(self) -> None:
        for action in (
            'add column "full name" varchar(64) not null',
            "add column code int, add column name varchar(64) not null",
            "add column name text not null default null",
            "add column name text not null default (null)",
            "add column token double precision not null default random()",
            "add column token text default ('prefix' || random()::text) not null",
            "add column flag boolean not null default 1 not in (random())",
            "add column label text not null default 'prefix' collate \"C\" || random()::text",
            "add column code int not null default 0, add column name text not null",
            "add column name text not null default current_setting('app.name', true)",
        ):
            with self.subTest(action=action):
                _, findings = sql_guard.inspect("table.sql", f"alter table t_user {action};", "postgresql")
                self.assertEqual([("POSTGRESQL-UPG-007", "block")], [
                    (item.rule_id, item.gate) for item in findings
                ])

    def test_postgresql_nonnull_nonvolatile_defaults_pass_not_null_check(self) -> None:
        for action in (
            "add column flag boolean not null default false",
            "add column flag boolean default (false) not null",
            "add column flag boolean default false constraint flag_required not null",
            "add column code int not null default 0 check (code >= 0)",
            "add column name text not null default /* empty string */ ''",
            "add column name text default E'a\\'b, not null' not null",
            "add column name text default $$a,not null;$$ not null",
            "add column received_at timestamp not null default current_timestamp(3)",
        ):
            with self.subTest(action=action):
                self.assertNotIn(
                    "POSTGRESQL-UPG-007",
                    self.rule_ids(f"alter table t_user {action};", "postgresql"),
                )

    def test_postgresql_alter_column_variants_are_detected(self) -> None:
        sql = "alter table t_user alter column name type varchar(64); alter table t_user alter column name set not null;"
        self.assertEqual({"POSTGRESQL-UPG-005", "POSTGRESQL-UPG-008"}, self.rule_ids(sql, "postgresql"))

    def test_postgresql_serial_and_identity_primary_keys_block(self) -> None:
        for sql in (
            "create table if not exists t_user (id smallserial primary key);",
            "create table if not exists t_user (id bigserial, primary key (id));",
            "create table if not exists t_user (id bigint generated always as identity, constraint pk_user primary key (id));",
            'CREATE TABLE IF NOT EXISTS t_user (tenant_id bigint, "Ledger ID)" bigint GENERATED BY DEFAULT AS IDENTITY, '
            'CONSTRAINT "PK" PRIMARY KEY (tenant_id, "Ledger ID)"));',
        ):
            with self.subTest(sql=sql):
                _, findings = sql_guard.inspect("table.sql", sql, "postgresql")
                self.assertEqual([("POSTGRESQL-PK-001", "block")], [
                    (item.rule_id, item.gate) for item in findings
                ])

    def test_postgresql_only_blocks_auto_increment_on_primary_keys(self) -> None:
        for sql in (
            "create table if not exists t_user (id uuid primary key, auto_increment boolean);",
            "create table if not exists t_user (id uuid primary key, sequence_no bigserial);",
            'create table if not exists t_user (id uuid primary key, seq bigint generated always as identity '
            'constraint "primary key" unique);',
            'create table if not exists t_user (id bigint primary key constraint "generated always as identity" unique);',
            'create table if not exists t_user (id uuid, "ID" bigint generated always as identity, primary key (id));',
            'create table if not exists t_user (id uuid, "entry""id" bigserial, primary key (id));',
        ):
            with self.subTest(sql=sql):
                self.assertEqual(set(), self.rule_ids(sql, "postgresql"))

    def test_postgresql_utf8_identifiers_preserve_gate_results(self) -> None:
        for sql, expected in (
            ("CREATE TABLE IF NOT EXISTS cafe\u0301 (id BIGSERIAL PRIMARY KEY);",
             [("POSTGRESQL-PK-001", "block")]),
            ("ALTER TABLE public.q\u0301 ENGINE=InnoDB;",
             [("POSTGRESQL-TAB-001", "warn")]),
            ("CREATE TABLE IF NOT EXISTS café (cafe\u0301 BIGSERIAL, café UUID, PRIMARY KEY (café));", []),
            ("CREATE TABLE IF NOT EXISTS café (café BIGSERIAL, cafÉ UUID, PRIMARY KEY (CAFÉ));", []),
        ):
            with self.subTest(sql=sql):
                _, findings = sql_guard.inspect("table.sql", sql, "postgresql")
                self.assertEqual(expected, [(item.rule_id, item.gate) for item in findings])

    def test_postgresql_primary_key_gate_exit_status(self) -> None:
        for columns, code, expected_rules in (
            ("id uuid primary key, auto_increment boolean", 0, []),
            ("id bigint generated always as identity primary key, auto_increment boolean", 1, ["POSTGRESQL-PK-001"]),
        ):
            with self.subTest(columns=columns):
                run = subprocess.run(
                    [sys.executable, str(MODULE_PATH), "--dialect", "postgresql", "--format", "json", "-"],
                    input=f"create table if not exists t_user ({columns});",
                    text=True, capture_output=True, check=False,
                )
                self.assertEqual(code, run.returncode, run.stderr)
                self.assertEqual(expected_rules, [item["rule_id"] for item in json.loads(run.stdout)["findings"]])

    def test_temporary_and_unlogged_tables_receive_table_checks(self) -> None:
        for sql in ("create temporary table t_tmp (id bigint);", "create unlogged table t_tmp (id bigint);"):
            rules = self.rule_ids(sql, "postgresql")
            self.assertIn(self.split_id("postgresql", "G.UPG.10"), rules)
            self.assertIn(self.split_id("postgresql", "G.TAB.16"), rules)

    def test_cte_insert_without_columns_is_detected(self) -> None:
        sql = "with source as (select 1 as id) insert into t_user values (1);"
        self.assertIn(self.split_id("postgresql", "G.INS.01"), self.rule_ids(sql, "postgresql"))

    def test_insert_recognizes_dialect_specific_target_column_lists(self) -> None:
        for dialect, sql, expected_block in (
            ("mysql", "insert ignore into `system_configs` (`config_key`) values ('example');", False),
            ("mysql", "insert ignore into system_configs values ('example');", True),
            ("mysql", "insert low_priority ignore `app` . `settings` partition (p0) (id) values (1);", False),
            ("mysql", "insert into settings partition (p0) values (1);", True),
            ("mysql", "insert into settings () values ();", True),
            ("postgresql", 'insert into "app"."settings" as s ("key") values (1) on conflict do nothing;', False),
            ("postgresql", 'insert into "app"."settings" as s values (1) on conflict do nothing;', True),
            ("postgresql", 'with s as (select 1) insert into "app" . "settings" ("key") select 1 from s;', False),
        ):
            with self.subTest(dialect=dialect, sql=sql):
                _, findings = sql_guard.inspect("insert.sql", sql, dialect)
                expected = [(self.split_id(dialect, "G.INS.01"), "block")] if expected_block else []
                self.assertEqual(expected, [(item.rule_id, item.gate) for item in findings])

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

    def test_possible_uuid_primary_keys_require_semantic_review(self) -> None:
        for dialect, types in (
            ("mysql", ("char(32)", "char(36)", "varchar(40)", "binary(8)")),
            ("postgresql", ("char(36)", "binary(16)", "bytea", "text", "varchar", "varchar(40)")),
        ):
            for data_type in types:
                with self.subTest(dialect=dialect, data_type=data_type):
                    sql = f"create table if not exists t_key (business_code {data_type}, scope_id int, primary key (scope_id, business_code));"
                    _, findings = sql_guard.inspect("key.sql", sql, dialect)
                    self.assertEqual([(f"{dialect.upper()}-PK-001", "warn")],
                                     [(finding.rule_id, finding.gate) for finding in findings])
        sql = 'create table if not exists t_key ("order-code" text, primary key ("order-code"));'
        self.assertIn("POSTGRESQL-PK-001", self.rule_ids(sql, "postgresql"))

    def test_weak_identifier_names_do_not_decide_auto_dialect(self) -> None:
        for sql in (
            "select jsonb from t_user where id=?;",
            "select id from t_user where id in (select jsonb from t_meta);",
            "select returning, concurrently, auto_increment from t_user;",
        ):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                sql_guard.inspect("weak.sql", sql, "auto")
        dialect, _ = sql_guard.inspect(
            "postgres.sql",
            "create table if not exists t_user (id uuid primary key, unsigned text);",
            "auto",
        )
        self.assertEqual("postgresql", dialect)

    def test_mysql_drop_column_without_column_keyword(self) -> None:
        for action in ("drop legacy_code", "drop `index`", "drop key idx, drop legacy_code"):
            self.assertIn("MYSQL-GUPG-003", self.rule_ids(f"alter table app.t {action};", "mysql"))
        for action in ("drop key idx", "drop foreign key fk", "drop partition p1", "alter column c drop default"):
            self.assertNotIn("MYSQL-GUPG-003", self.rule_ids(f"alter table app.t {action};", "mysql"))

    def test_postgresql_join_screening_preserves_lateral_queries(self) -> None:
        lateral = "select a.id, b.id from t_a a cross join lateral (select id from t_b where a.id=t_b.id) b;"
        self.assertEqual(set(), self.rule_ids(lateral, "postgresql"))
        _, findings = sql_guard.inspect("query.sql", "select a.id from t_a a cross join t_b b;", "postgresql")
        self.assertEqual([("POSTGRESQL-SEL-008", "warn")], [(item.rule_id, item.gate) for item in findings])

    def test_mysql_no_backslash_escapes_keeps_later_statements(self) -> None:
        sql = "select 'a\\'; select * from t_user;"
        _, findings = sql_guard.inspect("query.sql", sql, "mysql", mysql_no_backslash_escapes=True)
        self.assertEqual(["MYSQL-GSEL-012"], [item.rule_id for item in findings])

    def test_cli_hybrid_warnings_do_not_block_or_count_as_static_checks(self) -> None:
        cases = {
            "mysql": ("create table if not exists t_user (id int primary key) engine=MyISAM default charset=latin1; xa start 'x';",
                      {"MYSQL-TAB-001", "MYSQL-ENC-001", "MYSQL-TXN-007"}),
            "postgresql": (
                "prepare transaction 'x'; alter table t_user engine=InnoDB;",
                {"POSTGRESQL-TXN-007", "POSTGRESQL-TAB-001"},
            ),
        }
        for dialect, (sql, expected) in cases.items():
            for statement, code in ((sql, 0), (sql + " delete from t_user;", 1)):
                run = subprocess.run(
                    [sys.executable, str(MODULE_PATH), "--dialect", dialect, "--format", "json", "-"],
                    input=statement, text=True, capture_output=True, check=False,
                )
                self.assertEqual(code, run.returncode, run.stderr)
                output = json.loads(run.stdout)
                self.assertEqual("fail" if code else "pass", output["result"])
                self.assertEqual(expected, {f["rule_id"] for f in output["findings"] if f["gate"] == "warn"})
                self.assertTrue(expected <= set(output["screened_rules"]))
                self.assertTrue(expected.isdisjoint(output["checked_rules"]))
                if code:
                    self.assertIn(self.split_id(dialect, "G.DEL.01"), {
                        f["rule_id"] for f in output["findings"] if f["gate"] == "block"
                    })

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
