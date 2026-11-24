from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256

GUARD = Path(__file__).resolve().parents[1] / 'scripts' / 'sql_guard.py'

class MigrationExpansionTest(unittest.TestCase):
    def prepare(self, root: Path, sql: str, old: str | None = None, version: str = '03'):
        files = []
        references = []
        for direction, prefix in (('upgrade', 'V'), ('rollback', 'U')):
            for kind in ('ddl', 'dml'):
                path = root / 'sql' / direction / '20261123' / f'{prefix}{version}_{kind}.sql'
                path.parent.mkdir(parents=True, exist_ok=True)
                contents = sql if direction == 'upgrade' and kind == 'ddl' else '-- no operation\n'
                path.write_text(contents)
                files.append({'path': str(path), 'direction': direction, 'kind': kind, 'execution': 'sql' if contents == sql else 'none', 'sha256': sha256(contents.encode()).hexdigest()})
                reference = root / 'reference' / direction / path.name
                reference.parent.mkdir(parents=True, exist_ok=True)
                ref_contents = old if direction == 'upgrade' and kind == 'ddl' and old is not None else contents
                reference.write_text(ref_contents)
                references.append({'path': str(path), 'reference_path': str(reference), 'sha256': sha256(ref_contents.encode()).hexdigest()})
        target = files[0]['path']
        action = {'path': target, 'line': 1, 'end_line': len(sql.splitlines()), 'sql': sql.strip(), 'rule_id': 'POSTGRESQL-UPG-005', 'reference_line': 2 if old else 1, 'reference_end_line': 1 + len(sql.splitlines()) if old else len(sql.splitlines())}
        expansion = {'reference_files': references, 'same_precondition': True, 'same_fixture': True, 'schema_equal': True, 'data_equal': True,
                     'comparisons': {key: {'reference_sha256': 'a'*64, 'current_sha256': 'a'*64} for key in ('precondition','fixture','schema','data')}, 'operations': [action]}
        batch = {'batch': '20261123', 'upgrade_id': 'V'+version, 'rollback_id': 'U'+version, 'dialect': 'postgresql', 'database_version': '16.15', 'files': files, 'schema_equal': True, 'data_equal': True, 'syntax_verified': True, 'operations': [], 'expansion': expansion}
        return batch

    def check(self, root: Path, batches):
        receipt = root / 'receipt.json'
        receipt.write_text(json.dumps({'version': 1, 'batches': batches}))
        paths = [file['path'] for batch in batches for file in batch['files']]
        result = subprocess.run([sys.executable, str(GUARD), '--dialect', 'postgresql', '--format', 'json', '--migration-evidence', str(receipt), *paths], capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_exact_existing_native_statement_can_be_expanded(self):
        sql = 'ALTER TABLE t_order\n  ALTER COLUMN amount TYPE bigint USING (amount * 100)::bigint;'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            batch = self.prepare(root, sql, 'DO $$ BEGIN\n'+sql+'\nEND $$;')
            code, report = self.check(root, [batch])
            self.assertEqual(0, code, report)
            self.assertEqual('existing-migration-expansion', report['normal_rollbacks'][0]['state'])

    def test_expansion_requires_hashes_comparisons_and_exact_original_sql(self):
        sql = 'ALTER TABLE t_order ALTER COLUMN amount TYPE bigint;'
        for problem in ('old_hash', 'new_hash', 'different_action', 'comment', 'literal', 'false_comparison', 'false_fixture', 'missing_side', 'forbidden_rule'):
            with self.subTest(problem=problem), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                old = ('DO $$ BEGIN\n'+sql+'\nEND $$;')
                if problem == 'different_action': old = old.replace('TYPE bigint', 'TYPE integer')
                if problem == 'comment': old = '/*\n'+sql+'\n*/'
                if problem == 'literal': old = "SELECT '\n"+sql+"\n';"
                batch = self.prepare(root, sql, old)
                expansion = batch['expansion']
                if problem == 'old_hash': expansion['reference_files'][0]['sha256'] = 'b'*64
                if problem == 'new_hash': batch['files'][0]['sha256'] = 'b'*64
                if problem == 'false_comparison': expansion['comparisons']['schema']['current_sha256'] = 'b'*64
                if problem == 'false_fixture': expansion['same_fixture'] = False
                if problem == 'missing_side': expansion['reference_files'].pop()
                if problem == 'forbidden_rule': expansion['operations'][0]['rule_id'] = 'POSTGRESQL-DBS-003'
                code, report = self.check(root, [batch])
                self.assertEqual(1, code)
                self.assertTrue(report['migration_evidence_errors'], report)
                self.assertIn('POSTGRESQL-UPG-005', [f['rule_id'] for f in report['findings']])

    def test_new_operation_and_do_prohibition_cannot_be_waived(self):
        sql = 'ALTER TABLE t_order ALTER COLUMN amount TYPE bigint;'
        for suffix, rule in (('\nALTER TABLE t_order DROP COLUMN unrelated;', 'POSTGRESQL-GUPG-003'), ('\nDO $$ BEGIN NULL; END $$;', 'POSTGRESQL-DBS-003')):
            with self.subTest(rule=rule), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                batch = self.prepare(root, sql)
                path=Path(batch['files'][0]['path']); path.write_text(sql+suffix)
                batch['files'][0]['sha256'] = sha256(path.read_bytes()).hexdigest()
                code, report=self.check(root,[batch])
                self.assertEqual(1,code)
                self.assertIn(rule,[f['rule_id'] for f in report['findings']])

    def test_multiple_versions_on_same_date_are_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            sql='ALTER TABLE t_order ALTER COLUMN amount TYPE bigint;'
            batches=[self.prepare(root,sql,version=version) for version in ('03','04')]
            code,report=self.check(root,batches)
            self.assertEqual(0,code,report)
            code,report=self.check(root,[batches[0],batches[0]])
            self.assertEqual(1,code)
            self.assertTrue(report['migration_evidence_errors'])

    def test_normal_rollback_accepts_only_complete_homogeneous_actions(self):
        supported=(
            'ALTER TABLE t_child ADD CONSTRAINT child_fk FOREIGN KEY (id) REFERENCES t_parent(id) ON DELETE CASCADE;',
            'ALTER TABLE t_child ADD CONSTRAINT child_fk FOREIGN KEY (id, selected) REFERENCES t_parent(id, selected) DEFERRABLE INITIALLY DEFERRED;',
            'ALTER TABLE t_order\n ALTER COLUMN created_at TYPE timestamptz,\n ALTER COLUMN updated_at TYPE timestamptz;',
            'ALTER TABLE t_order ALTER COLUMN amount TYPE numeric(12,2) USING (amount::numeric / 100)::numeric(12,2);',
        )
        unsupported='ALTER TABLE t_order ALTER COLUMN created_at TYPE timestamptz, DROP COLUMN unrelated;'
        for sql in supported+(unsupported,):
            with self.subTest(sql=sql), tempfile.TemporaryDirectory() as directory:
                root=Path(directory)
                batch=self.prepare(root,'-- no operation')
                del batch['expansion']
                file=batch['files'][2]; path=Path(file['path']); path.write_text(sql)
                file['sha256']=sha256(path.read_bytes()).hexdigest(); file['execution']='sql'
                batch['operations']=[{'path':str(path),'line':1,'end_line':len(sql.splitlines()),'sql':sql}]
                code,report=self.check(root,[batch])
                self.assertEqual(1 if sql == unsupported else 0,code,report)
                self.assertEqual(sql == unsupported,bool(report['migration_evidence_errors']))
