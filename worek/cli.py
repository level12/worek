import click
import worek.core as core


@click.group()
def cli():
    pass


@cli.command()
@click.option('-h', '--host', default=None)
@click.option('-p', '--port', default=None)
@click.option('-u', '--user', default=None)
@click.option('-d', '--dbname', default=None)
@click.option('-e', '--engine', default='postgres')
@click.option('-s', '--schema', multiple=True)
@click.option('-f', '--file', 'output_file', default=None, type=click.File(mode='w'))
def backup(host, port, user, dbname, engine, schema, output_file):
    file_name = output_file if output_file is not None else click.get_text_stream('stdout')

    try:
        core.backup(file_name, engine,
                    schemas=schema, host=host, port=port, user=user, dbname=dbname)
    except core.WorekOperationException as e:
        click.echo(str(e), err=True)


@cli.command()
@click.option('-h', '--host', default=None)
@click.option('-p', '--port', default=None)
@click.option('-u', '--user', default=None)
@click.option('-d', '--dbname', default=None)
@click.option('-e', '--engine', default='postgres')
@click.option('-s', '--schema', multiple=True)
@click.option('-f', '--file', 'restore_file', default=None, type=click.File(mode='r'))
def restore(host, port, user, dbname, engine, schema, restore_file):
    file_name = restore_file if restore_file is not None else click.get_text_stream('stdin')

    core.restore(file_name, engine,
                 schema=schema, host=host, port=port, user=user, dbname=dbname)
