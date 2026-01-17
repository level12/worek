import click
import worek.core as core


@click.group()
def cli():
    pass


@cli.command(help="Create a database backup")
@click.option('-h', '--host', default=None, help="connection hostname for server")
@click.option('-p', '--port', default=None, help="connection port for server")
@click.option('-u', '--user', default=None, help="connection username for server")
@click.option('-d', '--dbname', default=None, help="database to backup")
@click.option('-e', '--engine', default='postgres', help="database type [postgres]")
@click.option('-s', '--schema', multiple=True,
              help="schemas to backup up, can be used multiple times")
@click.option('-f', '--file', 'output_file', default=None, type=click.File(mode='w'),
              help="path to file backup location, otherwise pipe to STDOUT")
@click.option('-v', '--version', default=None, help="major version of PG client utilities")
def backup(host, port, user, dbname, engine, schema, output_file, version):
    file_name = output_file if output_file is not None else click.get_text_stream('stdout')

    try:
        core.backup(
            file_name,
            schemas=schema,
            host=host,
            port=port,
            user=user,
            dbname=dbname,
            version=version
        )
    except core.WorekOperationException as e:
        click.echo(str(e), err=True)


@cli.command(help="Restore a database backup")
@click.option('-h', '--host', default=None, help="connection hostname for server")
@click.option('-p', '--port', default=None, help="connection port for server")
@click.option('-u', '--user', default=None, help="connection username for server")
@click.option('-d', '--dbname', default=None, help="database to backup")
@click.option('-e', '--engine', default='postgres', help="database type [postgres]")
@click.option('-s', '--schema', multiple=True,
              help="schemas to backup up, can be used multiple times")
@click.option('-f', '--file', 'restore_file', default=None, type=click.File(mode='rb'),
              help="path to file backup location, otherwise the read from STDIN")
@click.option('-F', '--format', 'file_format', type=click.Choice(['c', 't']), default=None,
              help="backup file format, ([c]ustom, [t]ext)")
@click.option('-v', '--version', default=None, help="major version of PG client utilities")
def restore(host, port, user, dbname, engine, schema, restore_file, file_format, version):
    file_name = restore_file if restore_file is not None else click.get_binary_stream('stdin')

    if not restore_file and not file_format:
        raise click.BadArgumentUsage(
            'You must specify the file format (-F) when using a pipe to STDIN. We can not'
            ' automatically determine the file format when using a pipe.',
        )

    core.restore(file_name, schema=schema, host=host, port=port, user=user, dbname=dbname,
                 file_format=file_format, version=version)
