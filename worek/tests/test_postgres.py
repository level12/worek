import getpass
import sqlalchemy as sa


from worek.dialects.postgres import (
    Postgres as PG,
    PostgresCommand
)
from worek.tests.helpers import (
    MockCLIExecutor,
    PostgresDialectTestBase,
)


class TestPostgresDialectInternals(PostgresDialectTestBase):
    def test_construct_engine_from_params_with_passed_values(self):
        engine = PG.construct_engine_from_params(
            user='testuser',
            password='testpassword',
            host='testhost',
            port='1111',
            dbname='testname'
        )
        assert engine.url.drivername == 'postgresql'
        assert engine.url.username == 'testuser'
        assert engine.url.password == 'testpassword'
        assert engine.url.host == 'testhost'
        assert engine.url.port == 1111
        assert engine.url.database == 'testname'

    def test_construct_engine_from_env(self, monkeypatch):
        monkeypatch.setenv('PGUSER', 'envuser')
        monkeypatch.setenv('PGPASSWORD', 'envpass')
        monkeypatch.setenv('PGHOST', 'envhost')
        monkeypatch.setenv('PGPORT', '1234')
        monkeypatch.setenv('PGDATABASE', 'envdb')
        engine = PG.construct_engine_from_params()

        assert engine.url.drivername == 'postgresql'
        assert engine.url.username == 'envuser'
        assert engine.url.password == 'envpass'
        assert engine.url.host == 'envhost'
        assert engine.url.port == 1234
        assert engine.url.database == 'envdb'

    def test_construct_engine_from_default(self):
        engine = PG.construct_engine_from_params()

        assert engine.url.drivername == 'postgresql'
        assert engine.url.username == getpass.getuser()
        assert engine.url.password == ''
        assert engine.url.host == 'localhost'
        assert engine.url.port == 5432
        assert engine.url.database == engine.url.username

    def test_autodetects_schemas(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        assert pg.schemas == ['public', pg_uniqueschema]

    def test_uses_passed_in_schemas(self):
        pg = PG(None, schemas=['other'])

        assert pg.schemas == ['other']

    def test_get_table_list_from_db(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        conn = pg_unclean_engine.connect()
        self.create_table(conn, 'testtbl_other')
        self.create_table(conn, 'testtbl', schema=pg_uniqueschema)

        assert pg.get_table_list_from_db(pg_uniqueschema) == ['testtbl']

    def test_get_seq_list_from_db(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        conn = pg_unclean_engine.connect()
        self.create_sequence(conn, 'testseq_other')
        self.create_sequence(conn, 'testseq', schema=pg_uniqueschema)

        assert pg.get_seq_list_from_db(pg_uniqueschema) == ['testseq']

    def test_get_function_list_from_db(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        conn = pg_unclean_engine.connect()
        self.create_function(conn, 'testfunc_other')
        self.create_function(conn, 'testfunc', schema=pg_uniqueschema)

        assert pg.get_function_list_from_db(pg_uniqueschema) == [('testfunc', 'integer')]

    def test_get_function_list_from_db_does_not_include_extensions(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        conn = pg_unclean_engine.connect()
        self.create_function(conn, 'testfunc_other')
        self.create_extension(conn, 'uuid-ossp', schema=pg_uniqueschema)
        self.create_function(conn, 'testfunc', schema=pg_uniqueschema)

        assert pg.get_function_list_from_db(pg_uniqueschema) == [('testfunc', 'integer')]

    def test_get_type_list_from_db(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        conn = pg_unclean_engine.connect()
        self.create_type(conn, 'testtype_other')
        self.create_type(conn, 'testtype', schema=pg_uniqueschema)

        assert pg.get_type_list_from_db(pg_uniqueschema) == ['testtype']

    def test_get_non_system_schemas_list_from_db(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        assert pg.get_non_system_schemas() == ['public', pg_uniqueschema]

    def test_drop_an_entire_schema(self, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine)

        conn = pg_unclean_engine.connect()
        self.create_function(conn, 'testfunc', schema=pg_uniqueschema)
        self.create_sequence(conn, 'testseq', schema=pg_uniqueschema)
        self.create_table(conn, 'testtbl', schema=pg_uniqueschema)
        self.create_type(conn, 'testtype', schema=pg_uniqueschema)

        pg.drop_schema(pg_uniqueschema)

        assert pg.errors == []
        assert pg.get_function_list_from_db(pg_uniqueschema) == []
        assert pg.get_seq_list_from_db(pg_uniqueschema) == []
        assert pg.get_table_list_from_db(pg_uniqueschema) == []
        assert pg.get_type_list_from_db(pg_uniqueschema) == []

    def test_url_translation_to_cli_commands_with_schemas(self):
        executor = MockCLIExecutor()
        engine = sa.create_engine('postgresql://user:password@host:1111/dbname')
        pg = PG(engine, executor=executor, schemas=['public', 'other'])
        pg._execute_cli_command(PostgresCommand.BACKUP)

        assert executor.captured_args[0][0].endswith('/pg_dump')
        assert set(executor.captured_args[0][1:]) == {
            '--dbname=dbname',
            '--host=host',
            '--schema=public',
            '--schema=other',
            '--username=user',
            '--port=1111',
        }
        assert executor.captured_kwargs['env']['PGPASSWORD'] == 'password'

    def test_command_doesnt_use_schema_for_text_restore(self):
        executor = MockCLIExecutor()
        engine = sa.create_engine('postgresql://user:password@host:1111/dbname')
        pg = PG(engine, executor=executor, schemas=['public', 'other'])
        pg._execute_cli_command(PostgresCommand.RESTORE_TEXT)

        assert executor.captured_args[0][0].endswith('/psql')
        assert set(executor.captured_args[0][1:]) == {
            '--dbname=dbname',
            '--host=host',
            '--username=user',
            '--port=1111',
        }
        assert executor.captured_kwargs['env']['PGPASSWORD'] == 'password'


class TestPostgresDialectBackup(PostgresDialectTestBase):

    def test_backup_creates_basic_sql_backup(self, tmpdir, pg_unclean_engine, pg_uniqueschema):
        pg = PG(pg_unclean_engine, schemas=[pg_uniqueschema])

        with open(tmpdir + '/test.backup', mode='w+') as fp:
            pg.backup_text(fp)
            fp.seek(0)
            result = fp.read()

        assert 'CREATE SCHEMA {};'.format(pg_uniqueschema) in result
        assert 'CREATE SCHEMA public;' not in result


class TestPostgresDialectIntegration(PostgresDialectTestBase):

    def test_create_and_restore_database_text_backup(self, tmpdir, pg_clean_engine):
        pg = PG(pg_clean_engine)
        backup_file = tmpdir + '/test.backup.text'

        self.create_table(pg_clean_engine, 'testtbl')
        pg_clean_engine.execute('INSERT INTO testtbl VALUES (1),(2),(3)')

        with open(backup_file, mode='w+') as fp:
            pg.backup_text(fp)

        pg_clean_engine.execute('DROP TABLE testtbl;')

        try:
            pg_clean_engine.execute('SELECT * FROM testtbl;')
        except sa.exc.ProgrammingError as e:
            if 'relation "testtbl" does not exist' not in str(e):
                raise

        with open(backup_file, mode='r') as fp:
            command_result = pg.restore_text(fp)

        assert command_result.returncode == 0

        result = pg_clean_engine.execute('SELECT * FROM testtbl;')
        assert result.rowcount == 3
        assert set([x[0] for x in result.fetchall()]) == {1, 2, 3}

    def test_create_and_restore_database_binary_backup(self, tmpdir, pg_clean_engine):
        pg = PG(pg_clean_engine)
        backup_file = tmpdir + '/test.backup.bin'

        self.create_table(pg_clean_engine, 'testtbl')
        pg_clean_engine.execute('INSERT INTO testtbl VALUES (1),(2),(3)')

        with open(backup_file, mode='w+') as fp:
            pg.backup_binary(fp)

        pg_clean_engine.execute('DROP TABLE testtbl;')

        try:
            pg_clean_engine.execute('SELECT * FROM testtbl;')
        except sa.exc.ProgrammingError as e:
            if 'relation "testtbl" does not exist' not in str(e):
                raise

        with open(backup_file, mode='r') as fp:
            command_result = pg.restore_binary(fp)

        assert command_result.returncode == 0

        result = pg_clean_engine.execute('SELECT * FROM testtbl;')
        assert result.rowcount == 3
        assert set([x[0] for x in result.fetchall()]) == {1, 2, 3}
