import enum
import getpass
import logging
import os
import re
import shutil
import subprocess

import sqlalchemy as sa
import psycopg2

from worek.exc import WorekException


log = logging.getLogger(__name__)


class WorekPostgresError(WorekException):
    pass


class PostgresCLIError(WorekPostgresError):
    def __init__(self, command_result):
        self.command_result = command_result


class PostgresInputError(WorekPostgresError):
    pass


class PostgresCommand(enum.Enum):
    BACKUP = 'pg_dump'
    RESTORE_BINARY = 'pg_restore'
    RESTORE_TEXT = 'psql'


class Postgres:
    """A logical backup / restore implementation for Postgres databases.

    Utilizes the pg_dump and pg_restore commands and some extra features to allow database users to
    manage backups and restores of their own data.
    """

    def __init__(self, engine, schemas=None, executor=None, version=None):
        """Postgres Database Management Tool

        :param engine: a SQLAlchemy Engine which connects to the relevant database
        :param schemas: schemas you want to restore or backup
        :param executor: the method for executing the PG commands against the database. By default
            this uses `subprocess.run` but you can use the `tests.helpers.MockCLIExecutor` or any
            callable that accepts a list of CLI arguments and `**kwargs`.
        :param version: the version of PG client executables to use

        .. note:: `schemas` is ignored when working with a RESTORE_TEXT operation because postgres
            can not selectively restore a plain text backup. Use a binary backup if you want to
            manage schemas manually.
        """
        self.engine = engine
        self._schemas = schemas

        self.errors = []
        self.executor = subprocess.run if executor is None else executor
        self.version = version

    @property
    def schemas(self):
        if not self._schemas:
            self._schemas = self.get_non_system_schemas()

        return self._schemas

    def _default_version(self):
        sql = sa.select([sa.func.current_setting('server_version')])
        result = self.engine.execute(sql).fetchone()

        match = re.match(r'(\d+\.\d+)', result[0])
        version = match.group(1)
        if version.startswith('9'):
            return version
        return version.split('.')[0]

    @property
    def engine_can_connect(self):
        try:
            self.engine.execute("SELECT 1")
            return True
        except psycopg2.Error:
            return False

    @classmethod
    def construct_engine_from_params(cls, **params):
        """Create a SQLAlchemy Engine from the passed params and sensible defaults


        .. note:: Because we have to clean the database manually when running as a non-superuser
            (can't drop the database) we have to have a fully resolved database URL for SQLAlchemy.
            The Postgres commands will use the same URL params in the execution of the cli commands
        """

        driver = params.get('driver') or 'postgresql'

        if 'postgresql' not in driver:
            raise ValueError('The database driver must be for postgresql, got {}.'.format(driver))

        user = params.get('user') or os.environ.get('PGUSER') or getpass.getuser()
        password = params.get('password') or os.environ.get('PGPASSWORD', '')
        host = params.get('host') or os.environ.get('PGHOST', 'localhost')
        port = params.get('port') or os.environ.get('PGPORT', 5432)
        dbname = params.get('dbname') or os.environ.get('PGDATABASE', user)

        return sa.create_engine(
            'postgresql://{user}:{password}@{host}:{port}/{dbname}'.format(
                user=user,
                password=password,
                host=host,
                port=port,
                dbname=dbname
            )
        )

    @classmethod
    def cli_flags_for_url(cls, url):
        flags = []

        if url.username:
            flags += ['--username={}'.format(url.username)]

        if url.host:
            flags += ['--host={}'.format(url.host)]

        if url.port:
            flags += ['--port={}'.format(url.port)]

        if url.database:
            flags += ['--dbname={}'.format(url.database)]

        return flags

    def _pg_wrapper_cluster(self, exe_name):
        if not is_pg_wrapper_available(exe_name) and self.version:
            raise OSError('pg_wrapper is required if a version is specified')
        return '{}/localhost:'.format(self.version or self._default_version())

    def _execute_cli_command(self, command, additional_args=None, stdin=None, stdout=None,
                             stderr=None):
        """
        Execute a CLI Command putting STDOUT into output.

        .. note:: While you could pass `--file` in `command_args` for pg_dump and pg_restore, it is
        much more flexible to allow those programs to dump to STDOUT and then use `subprocess` to
        pipe the data into the file you choose. This allows neat things like passing in sys.stdout
        so that it can get all the way to the console or passed to GZIP or an encryption protocol,
        all without having to save to disk first.

        :param command: the postgres command you want to run, should be an instance of
            `PostgresCommand`
        :param additional_args: a list of arguments which should be passed to the CLI command.
        :param stdin: a stream or pipe to use for standard input, useful when you want to pipe a
            restore command from some other tool like gzip or openssl.
        :param stdout: a stream or pipe to use for standard output, useful when you want to pipe a
            backup command to some other tool like gzip or openssl.
        :param stderr: a stream or pipe to use for standard error, by default this is just a
            subprocess pipe.
        """
        stdin = stdin or subprocess.PIPE
        stdout = stdout or subprocess.PIPE
        stderr = stderr or subprocess.PIPE

        if not isinstance(command, PostgresCommand):
            raise NotImplementedError(
                'Unknown postgresql command. Are you using the PostgresCommand enum.'
            )

        env = os.environ.copy()
        url = self.engine.url

        cli_args = [command.value] + self.cli_flags_for_url(url)

        if command != PostgresCommand.RESTORE_TEXT:
            cli_args += ['--schema={}'.format(x) for x in self.schemas]

        env['PGCLUSTER'] = self._pg_wrapper_cluster(command.value)
        if url.password:
            env['PGPASSWORD'] = url.password

        cli_args.extend(additional_args or [])

        result = self.executor(cli_args, env=env, stdin=stdin, stdout=stdout, stderr=stderr)

        if result.returncode != 0:
            raise PostgresCLIError(result)

        return result

    def drop_schema(self, schema):
        for funcname, funcargs in self.get_function_list_from_db(schema):
            try:
                sql = 'DROP FUNCTION "{}"."{}" ({}) CASCADE'.format(schema, funcname, funcargs)
                self.engine.execute(sql)
            except Exception:
                raise

        for table in self.get_table_list_from_db(schema):
            try:
                self.engine.execute('DROP TABLE "{}"."{}" CASCADE'.format(schema, table))
            except Exception:
                raise

        for seq in self.get_seq_list_from_db(schema):
            try:
                self.engine.execute('DROP SEQUENCE "{}"."{}" CASCADE'.format(schema, seq))
            except Exception:
                raise

        for dbtype in self.get_type_list_from_db(schema):
            try:
                self.engine.execute('DROP TYPE "{}"."{}" CASCADE'.format(schema, dbtype))
            except Exception:
                raise

    def get_function_list_from_db(self, schema):
        """Returns a list of functions not associated with an extension

        .. note:: original versions of this function would return all functions even if they were
            related to installed extensions. Since our app users can't install extensions, we need
            to leave those function intact along with the extensions that installed them.
        """
        sql = """
            SELECT
                PR.proname,
                pg_get_function_identity_arguments(PR.oid) AS params
            FROM
                pg_proc PR
                JOIN pg_namespace NS ON NS.oid = PR.pronamespace
                LEFT JOIN pg_depend D ON D.objid = PR.oid
                AND D.deptype = 'e'
            WHERE
                NS.nspname = '{schema}'
                AND D.objid IS NULL;
        """.format(schema=schema)

        return [row for row in self.engine.execute(sql)]

    def get_table_list_from_db(self, schema):
        """
        Return a list of table names from the passed schema
        """

        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='{schema}';
        """.format(schema=schema)

        return [name for (name, ) in self.engine.execute(sql)]

    def get_seq_list_from_db(self, schema):
        """return a list of the sequence names from the current
           databases public schema
        """
        sql = """
            SELECT sequence_name
            FROM information_schema.sequences
            WHERE sequence_schema='{schema}';
        """.format(schema=schema)

        return [name for (name, ) in self.engine.execute(sql)]

    def get_non_system_schemas(self):
        """
        Return a list of non-postgres default schema

        .. note:: the use of pg_%, find the relevant documenation on determining system schemas
            here: https://www.postgresql.org/docs/10/static/ddl-schemas.html#DDL-SCHEMAS-CATALOG
        """

        all_non_default_schemas_query = """
            SELECT schema_name
            FROM information_schema.schemata
            WHERE
                "schema_name" NOT LIKE 'pg_%%'
            AND "schema_name" != 'information_schema';
        """

        result = self.engine.execute(all_non_default_schemas_query)

        return [x[0] for x in result.fetchall()]

    def get_type_list_from_db(self, schema):
        """return a list of the sequence names from the passed schema
        """
        sql = """
            SELECT t.typname as type
            FROM pg_type t
            LEFT JOIN pg_catalog.pg_namespace n
                ON n.oid = t.typnamespace
            WHERE
                ( t.typrelid = 0 OR
                    (
                        SELECT c.relkind = 'c'
                        FROM pg_catalog.pg_class c
                        WHERE c.oid = t.typrelid
                    )
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM pg_catalog.pg_type el
                    WHERE el.oid = t.typelem
                        AND el.typarray = t.oid
                )
                AND n.nspname = '{}'
        """.format(schema)

        return [name for (name, ) in self.engine.execute(sql)]

    def clean_existing_database(self, schemas=None):
        schemas = schemas if schemas is not None else self.schemas

        for schema in schemas:
            self.drop_schema(schema)

    def restore(self, buf, **kwargs):
        """Perform a "smart" restore, properly choosing between a binary or text version"""
        return self.restore_binary(buf, **kwargs)

        try:
            header = buf.peek(5)
        except AttributeError:
            raise PostgresInputError(
                'You must use a peekable stream when trying to automatically detect the backup file'
                ' type. If you are pipe data into worek from the CLI, you should explicitly set the'
                ' backup file type that you are piping to the restore command.')

        if header[:5] in ('PGDMP', b'PGDMP'):
            return self.restore_binary(buf, **kwargs)
        else:
            return self.restore_text(buf, **kwargs)

    def restore_binary(self, buf, no_owner=True, no_privileges=True, **kwargs):
        """Restore a binary backup from the passed buf

        :param buf: the buffer with the backup to restore
        :param no_owner: do not keep the owner information from the backup (default: True)
        :param no_privileges: do not restore privileges information from the backup (default: True)

        .. note:: Depending on the `self.executor`, the options for `buf` depend on the supported
            values. By default this class uses `subprocess.run` to execute the restore command, so
            you can pass anything to `buf` that the `stdin` argument would take for that function
            (i.e. PIPE, file, DEVNULL)
        """
        command_args = (
            []
            + (['--no-owner' if no_owner else ''])
            + (['--no-privileges' if no_privileges else ''])
        )
        return self._execute_cli_command(PostgresCommand.RESTORE_BINARY, command_args, stdin=buf)

    def restore_text(self, buf, **kwargs):
        """Restore a plain text backup from the passed buf

        :param buf: the buffer with the backup to restore

        .. note:: Depending on the `self.executor`, the options for `buf` depend on the supported
            values. By default this class uses `subprocess.run` to execute the restore command, so
            you can pass anything to `buf` that the `stdin` argument would take for that function
            (i.e. PIPE, file, DEVNULL)
        """
        return self._execute_cli_command(PostgresCommand.RESTORE_TEXT, [], stdin=buf)

    def backup_binary(self, buf, blobs=True):
        """Create a binary (--format=custom) backup of the postgres context

        :param buf: the buffer to store the results of the backup
        :param blobs: include blob data in backup (default: True)

        .. note:: Depending on the `self.executor`, the options for `buf` depend on the supported
            values. By default this class uses `subprocess.run` to execute the backup command, so
            you can pass anything to `buf` that the `stdout` argument would take for that function
            (i.e. PIPE, file, DEVNULL)
        """
        command_args = ['--format', 'custom'] + (['--blobs'] if blobs else [])
        return self._execute_cli_command(PostgresCommand.BACKUP, command_args, stdout=buf)

    def backup_text(self, buf):
        """Create a plain text backup of the postgres context

        :param buf: the buffer to store the results of the backup

        .. note:: Depending on the `self.executor`, the options for `buf` depend on the support
            values. By default this class uses `subprocess.run` to execute the backup command, so
            you can pass anything to `buf` that the `stdout` argument would take for that function
            (i.e. PIPE, file, DEVNULL)
        """

        command_args = ['--format', 'plain']
        return self._execute_cli_command(PostgresCommand.BACKUP, command_args, stdout=buf)


def is_pg_wrapper_available(exe_name):
    path = shutil.which(exe_name)
    if path is None:
        return False

    if not os.path.islink(path):
        return False
    real_path = os.path.realpath(path)
    exe_name = os.path.basename(real_path)
    return exe_name == 'pg_wrapper'
