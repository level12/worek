import worek.dialects.postgres as pgdialect


class WorekOperationException(Exception):
    pass


def backup(backup_file, backup_type='full', **params):
    """Create backup of the database to the backup file

    :param backup_file: The file to send the backup to, this can be any file-like object including a
        a stream like. sys.stdin and sys.stdout should work no problem.
    :param backup_type: The type of database backup requested. The only option is 'full'.

    :param driver: the driver to use for connecting to the database
    :param host: the host of the database server
    :param port: the port of the database server
    :param user: the user of the database server
    :param password: the password of the database server
    :param dbname: the database name to backup
    :param saengine: an optional sqlalchemy engine, if this is passed, this will be used for the
        backup and other connection type parameters (e.g. driver, host, port) will be ignored
    """
    PG = pgdialect.Postgres(
        engine=params.get('saengine') or pgdialect.Postgres.construct_engine_from_params(**params),
        schemas=params.get('schemas'))

    if not PG.engine_can_connect:
        raise WorekOperationException('Can\'t connect to the database.')

    if backup_type == 'full':
        PG.backup_binary(backup_file)
    else:
        raise NotImplementedError('Only full backups are available at this time.')


def restore(restore_file, **params):
    """Restore a backup file to the specified database

    :param restore_file: The file to pull the backup from, this can be any file-like object
        including a a stream like. sys.stdin and sys.stdout should work no problem.

    :param driver: the driver to use for connecting to the database
    :param host: the host of the database server
    :param port: the port of the database server
    :param user: the user of the database server
    :param password: the password of the database server
    :param dbname: the database name to backup
    :param saengine: an optional sqlalchemy engine, if this is passed, this will be used for the
        backup and other connection type parameters (e.g. driver, host, port) will be ignored
    """
    PG = pgdialect.Postgres(
        engine=params.get('saengine') or pgdialect.Postgres.construct_engine_from_params(**params),
        schemas=params.get('schemas'))

    if not PG.engine_can_connect:
        raise WorekOperationException('Can\'t connect to the database.')

    PG.clean_existing_database()

    # perform the restore
    return PG.restore(restore_file)
