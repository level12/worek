from sqlalchemy import text
from sqlalchemy.engine import Engine


class MockCLIExecutor:
    def __init__(self, returncode=0, stderr=b'', stdout=b''):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout

    def __call__(self, *args, **kwargs):
        self.captured_args = args
        self.captured_kwargs = kwargs
        return self


class PostgresDialectTestBase:
    def _get_connection(self, engine_or_conn):
        """Helper to get a connection from either an Engine or Connection"""
        if isinstance(engine_or_conn, Engine):
            return engine_or_conn.connect()
        return engine_or_conn

    def create_extension(self, engine_or_conn, ext, schema=None):
        schema = f'WITH SCHEMA "{schema}"' if schema else ''
        sql = f'CREATE EXTENSION IF NOT EXISTS "{ext}" {schema}'
        conn = self._get_connection(engine_or_conn)
        try:
            conn.execute(text(sql))
            conn.commit()
        finally:
            if isinstance(engine_or_conn, Engine):
                conn.close()

    def create_table(self, engine_or_conn, table, schema=None):
        with_schema = '.'.join([schema, table]) if schema else table
        sql = f'CREATE TABLE {with_schema} ( id integer PRIMARY KEY );'
        conn = self._get_connection(engine_or_conn)
        try:
            conn.execute(text(sql))
            conn.commit()
        finally:
            if isinstance(engine_or_conn, Engine):
                conn.close()

    def create_sequence(self, engine_or_conn, sequence, schema=None):
        with_schema = '.'.join([schema, sequence]) if schema else sequence
        sql = f'CREATE SEQUENCE {with_schema};'
        conn = self._get_connection(engine_or_conn)
        try:
            conn.execute(text(sql))
            conn.commit()
        finally:
            if isinstance(engine_or_conn, Engine):
                conn.close()

    def create_function(self, engine_or_conn, function, schema=None):
        with_schema = '.'.join([schema, function]) if schema else function
        sql = f"""
            CREATE OR REPLACE FUNCTION {with_schema}(int) RETURNS int
            AS $$ SELECT 1 $$ LANGUAGE SQL;
            """
        conn = self._get_connection(engine_or_conn)
        try:
            conn.execute(text(sql))
            conn.commit()
        finally:
            if isinstance(engine_or_conn, Engine):
                conn.close()

    def create_type(self, engine_or_conn, type_, schema=None):
        with_schema = '.'.join([schema, type_]) if schema else type_
        sql = f'CREATE TYPE {with_schema};'
        conn = self._get_connection(engine_or_conn)
        try:
            conn.execute(text(sql))
            conn.commit()
        finally:
            if isinstance(engine_or_conn, Engine):
                conn.close()
