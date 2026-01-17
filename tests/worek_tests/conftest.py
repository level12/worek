import random
import string

import sqlalchemy as sa
import pytest
from worek.dialects.postgres import Postgres as PG

DBNAME = 'worek-tests'


def pytest_configure(config):
    # clean / create the database for this run
    clean_database()


@pytest.fixture(scope='function')
def pg_unclean_engine():
    """Return a handle to the test database

    Use this fixture when you can reuse the DB across tests and it doesn't matter what else is in
    there. Try to use this fixture as often as possible since it is expensive to drop and create a
    clean database.
    """
    engine = PG.construct_engine_from_params(dbname=DBNAME)

    try:
        testconn = engine.connect()
        testconn.close()
    except sa.exc.OperationalError:
        clean_database()

    return engine


@pytest.fixture(scope='function')
def pg_clean_engine():
    clean_database()
    return PG.construct_engine_from_params(dbname=DBNAME)


def clean_database():
    """Return a handle to the test database

    :param admin_engine: you need to have a handle to the database with superuser abilities so you
        can drop and create the database

    Use this fixture when you need the database absolutely fresh, no data from other tests, be them
    schemas, functions, or otherwise, will be present. Note, this drops and creates the database, so
    try to only use this when absolutely necessary.
    """

    admin_engine = PG.construct_engine_from_params(dbname='postgres')
    local_conn = admin_engine.connect()

    # This bumps us out of a transaction because a DROP/CREATE command can't run in a transaction
    local_conn.execute('COMMIT')

    local_conn.execute('''
        SELECT pg_terminate_backend(pg_stat_activity.pid)
        FROM pg_stat_activity
        WHERE datname = '{}'
        AND pid <> pg_backend_pid();
    '''.format(DBNAME))
    local_conn.execute('DROP DATABASE IF EXISTS "{}";'.format(DBNAME))

    local_conn.execute('COMMIT')
    local_conn.execute('CREATE DATABASE "{}";'.format(DBNAME))


@pytest.fixture(scope='function')
def pg_uniqueschema(pg_unclean_engine):
    """Create and return the name of a unique schema, which will be cleaned up after the test

    """
    schema_name = ''.join(random.sample(string.ascii_lowercase, k=20))

    conn = pg_unclean_engine.connect()
    conn.execute('CREATE SCHEMA {}'.format(schema_name))
    conn.close()

    yield schema_name

    conn = pg_unclean_engine.connect()
    conn.execute('DROP SCHEMA IF EXISTS {} CASCADE'.format(schema_name))
    conn.close()
