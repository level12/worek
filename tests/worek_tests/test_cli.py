from click.testing import CliRunner
import sqlalchemy as sa

from worek.tests.helpers import PostgresDialectTestBase
from worek.cli import cli


class TestCLIPGBackup(PostgresDialectTestBase):

    def engine_to_cli_params(self, engine):
        return [
            '--host', engine.url.host,
            '--user', engine.url.username,
            '--port', engine.url.port,
            '--dbname', engine.url.database,
        ]

    def test_cli_can_create_restoreable_backup(self, tmpdir, pg_clean_engine):
        backup_file = tmpdir.join('test.backup.bin').strpath

        runner = CliRunner()
        result = runner.invoke(
            cli, ['backup', '-f', backup_file] + self.engine_to_cli_params(pg_clean_engine)
        )

        assert result.exit_code == 0

        with open(backup_file, 'rb') as fp:
            assert fp.read(5) == b'PGDMP'
            data = fp.read()
            assert b'CREATE SCHEMA public' in data

        self.create_table(pg_clean_engine, 'manualtest')

        assert pg_clean_engine.execute('SELECT * from manualtest')

        result = runner.invoke(
            cli,
            ['restore', '-f', backup_file] + self.engine_to_cli_params(pg_clean_engine),
        )

        assert result.exit_code == 0

        try:
            assert pg_clean_engine.execute('SELECT * from manualtest')
        except sa.exc.ProgrammingError as e:
            assert 'relation "manualtest" does not exist' in str(e)
