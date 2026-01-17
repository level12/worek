import sqlalchemy as sa
import worek

from worek.tests.helpers import PostgresDialectTestBase


class TestCorePGBackup(PostgresDialectTestBase):

    def test_backup_creates_full_restoreable_backup(self, tmpdir, pg_clean_engine):
        backup_file = tmpdir.join('test.backup.bin').strpath

        with open(backup_file, 'w+') as fp:
            worek.backup(fp, saengine=pg_clean_engine)

        with open(backup_file, 'rb') as fp:
            assert fp.read(5) == b'PGDMP'
            assert b'CREATE SCHEMA public' in fp.read()

        self.create_table(pg_clean_engine, 'should_be_removed')

        with open(backup_file, 'r') as fp:
            worek.restore(fp, saengine=pg_clean_engine)

        try:
            pg_clean_engine.execute('SELECT * FROM should_be_removed;')
        except sa.exc.ProgrammingError as e:
            assert 'relation "should_be_removed" does not exist' in str(e)
