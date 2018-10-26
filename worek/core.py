import worek.dialects.postgres as pgdialect
import psycopg2


class WorekOperationException(Exception):
    pass


def backup(backup_file, engine, backup_type='full', **params):
    if engine != 'postgres':
        raise NotImplementedError()

    PG = pgdialect.Postgres(
        engine=pgdialect.Postgres.construct_engine_from_params(**params),
        schemas=params.get('schemas'))

    if not PG.engine_can_connect:
        raise WorekOperationException('Can\'t connect to the database.')

    if backup_type == 'full':
        PG.backup_binary(backup_file)


def restore(restore_file, engine, **params):
    if engine != 'postgres':
        raise NotImplementedError()

    PG = pgdialect.Postgres(
        engine=pgdialect.Postgres.construct_engine_from_params(**params),
        schemas=params.get('schemas'))

    if not PG.engine_can_connect:
        raise WorekOperationException('Can\'t connect to the database.')

    PG.clean_existing_database()

    # perform the restore
    return PG.restore(
        restore_file,
        schemas=schemas
    )
