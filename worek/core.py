import worek.dialects.postgres as pgdialect
import psycopg2


class WorekOperationException(Exception):
    pass


def engine_can_connect(engine):
    try:
        engine.execute("SELECT 1")
        return True
    except psycopg2.Error:
        return False


def backup(backup_file, engine, backup_type='full', **params):
    if engine == 'postgres':
        sa_engine = pgdialect.construct_engine_from_params(**params)

        if not engine_can_connect(sa_engine):
            raise WorekOperationException('Can not connect to database.')

        schemas = params.get('schemas')
        return pgdialect.backup(
            backup_file,
            sa_engine,
            backup_type=backup_type,
            schemas=schemas
        )
    else:
        raise NotImplementedError()


def restore(restore_file, engine, **params):
    if engine == 'postgres':
        sa_engine = pgdialect.construct_engine_from_params(**params)

        if not engine_can_connect(sa_engine):
            raise WorekOperationException('Can not connect to database.')

        schemas = params.get('schemas')
        return pgdialect.restore(
            restore_file,
            sa_engine,
            schemas=schemas
        )
    else:
        raise NotImplementedError()
