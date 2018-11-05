
class MockCLIExecutor:
    def __init__(self, returncode=0, stderr=b'', stdout=b''):
        self.returncode = returncode
        self.stderr = stderr
        self.stdout = stdout

    def __call__(self, *args, **kwargs):
        self.captured_args = args
        self.captured_kwargs = kwargs
        return self


class PostgresDialectTestBase():
    def create_extension(self, conn, ext, schema=None):
        schema = 'WITH SCHEMA "{}"'.format(schema) if schema else ''
        sql = 'CREATE EXTENSION IF NOT EXISTS "{}" {}'.format(ext, schema)
        conn.execute(sql)

    def create_table(self, conn, table, schema=None):
        with_schema = '.'.join([schema, table]) if schema else table
        sql = 'CREATE TABLE {} ( id integer PRIMARY KEY );'.format(with_schema)
        conn.execute(sql)

    def create_sequence(self, conn, sequence, schema=None):
        with_schema = '.'.join([schema, sequence]) if schema else sequence
        sql = 'CREATE SEQUENCE {};'.format(with_schema)
        conn.execute(sql)

    def create_function(self, conn, function, schema=None):
        with_schema = '.'.join([schema, function]) if schema else function
        sql = (
            '''
            CREATE OR REPLACE FUNCTION {}(int) RETURNS int
            AS $$ SELECT 1 $$ LANGUAGE SQL;
            '''.format(with_schema)
        )
        conn.execute(sql)

    def create_type(self, conn, type_, schema=None):
        with_schema = '.'.join([schema, type_]) if schema else type_
        sql = 'CREATE TYPE {};'.format(with_schema)
        conn.execute(sql)
