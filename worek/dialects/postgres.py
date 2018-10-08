import getpass
import logging
import os
import subprocess

import sqlalchemy as sa

import worek.utils


log = logging.getLogger(__name__)


def construct_engine_from_params(**params):
    # Resolve all the parameters for this connection, we try to be smart about all of this and
    # use the environment variables that PG supports. It might be better to allow pg_dump and
    # pg_restore to discover the properties themselves, but we have the issue of clearing the
    # schema which we must do manually.
    user = params.get('user') or os.environ.get('PGUSER') or getpass.getuser()
    password = params.get('password') or os.environ.get('PGPASSWORD', '')
    host = params.get('host') or os.environ.get('PGHOST', 'localhost')
    port = params.get('port') or os.environ.get('PGPORT', 5432)
    dbname = params.get('dbname') or os.environ.get('PGDATABASE', user)

    return sa.create_engine(f'postgresql://{user}:{password}@{host}:{port}/{dbname}')


def backup(backup_file, engine, backup_type='full', bin_dpath=None, schemas=None):
    pg = Postgres(engine, schemas=schemas)

    pg.backup_binary(backup_file)


def restore(restore_file, engine, backup_type='full', bin_dpath=None, schemas=None):
    pg = Postgres(engine, schemas=schemas)

    pg.clean_existing_database()

    if backup_type == 'full':
        pg.restore_binary(restore_file)
    else:
        raise NotImplementedError('Unknown Backup Type.')


class Postgres:

    def __init__(self, engine, schemas=None):
        self.engine = engine
        self.schemas = schemas or self.get_non_system_schemas()
        self._did_pass_schemas = (schemas is not None)

        self.pg_bin_dpath = os.path.dirname(worek.utils.latest_version('pg_restore'))
        self.errors = []

    def _execute_cli_command(self, command, command_args, stream=None):
        """
        Execute a CLI Command putting STDOUT into output.

        .. note:: While you could pass `--file` in `command_args` for pg_dump and pg_restore, it is
        much more flexible to allow those programs to dump to STDOUT and then use `subprocess` to
        pipe the data into the file you choose. This allows neat things like passing in sys.stdout
        so that it can get all the way to the console or passed to GZIP or an encryption protocol,
        all without having to save to disk first.
        """
        url = self.engine.url
        env = os.environ.copy()

        call_args = ['{}/{}'.format(self.pg_bin_dpath, command)]

        if self._did_pass_schemas:
            call_args += [f'--schema={x}' for x in self.schemas]

        if url.database:
            call_args += [f'--dbname={url.database}']

        if url.username:
            call_args += [f'--username={url.username}']

        if url.password:
            env['PGPASSWORD'] = url.password

        if url.host:
            call_args += [f'--host={url.host}']

        if url.port:
            call_args += [f'--port={url.port}']

        call_args.extend(command_args)

        if command == 'pg_dump':
            completed = subprocess.run(
                call_args,
                env=env,
                stdout=stream,
                stderr=subprocess.PIPE
            )
        elif command == 'pg_restore':
            completed = subprocess.run(
                call_args,
                env=env,
                stdin=stream,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        else:
            raise NotImplementedError('Unknown PG Command')


        if completed.returncode != 0:
            self.errors.append('Exit code: {}'.format(completed.returncode))
            self.errors.append('--------STDOUT---------')
            self.errors.append(completed.stdout.decode('utf-8'))
            self.errors.append('--------STDERR---------')

        self.errors.append(completed.stderr.decode('utf-8'))

    def drop_schema(self, schema):
        for funcname, funcargs in self.get_function_list_from_db(schema):
            try:
                sql = 'DROP FUNCTION "{}"."{}" ({}) CASCADE'.format(schema, funcname, funcargs)
                self.engine.execute(sql)
            except Exception as e:
                self.errors.append(str(e))

        for table in self.get_table_list_from_db(schema):
            try:
                self.engine.execute('DROP TABLE "{}"."{}" CASCADE'.format(schema, table))
            except Exception as e:
                self.errors.append(str(e))

        for seq in self.get_seq_list_from_db(schema):
            try:
                self.engine.execute('DROP SEQUENCE "{}"."{}" CASCADE'.format(schema, seq))
            except Exception as e:
                self.errors.append(str(e))

        for dbtype in self.get_type_list_from_db(schema):
            try:
                self.engine.execute('DROP TYPE "{}"."{}" CASCADE'.format(schema, dbtype))
            except Exception as e:
                self.errors.append(str(e))

    def get_function_list_from_db(self, schema):
        sql = """
            SELECT proname, oidvectortypes(proargtypes)
            FROM pg_proc
            INNER JOIN pg_namespace ns
                on (pg_proc.pronamespace = ns.oid)
            WHERE ns.nspname = '{schema}';
        """.format(schema=schema)

        return [row for row in self.engine.execute(sql)]

    def get_table_list_from_db(self, schema):
        """
        Return a list of table names from the passed schema
        """

        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='{}';
        """.format(schema)

        return [name for (name, ) in self.engine.execute(sql)]

    def get_seq_list_from_db(self, schema):
        """return a list of the sequence names from the current
           databases public schema
        """
        sql = """
            SELECT sequence_name
            FROM information_schema.sequences
            WHERE sequence_schema='{}';
        """.format(schema)

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
        schemas = schemas if schemas else self.schemas

        for schema in schemas:
            self.drop_schema(schema)

    def restore_binary(self, restore_fp):
        args = ['--no-owner', '--no-privileges']

        self._execute_cli_command('pg_restore', args, stream=restore_fp)

    def backup_binary(self, backup_fp, backup_type='full'):
        if backup_type == 'full':
            command_args = ['--format', 'custom', '--blobs']
        else:
            raise NotImplementedError('Only full backups are supported at this time.')

        self._execute_cli_command('pg_dump', command_args, stream=backup_fp)
