import click
from .local_cli import local

@click.group()
@click.option('--debug', is_flag=True, help='Enable debug logging')
@click.pass_context
def cli(ctx, debug):
    """Marinabox - Manage browser containers"""
    ctx.ensure_object(dict)
    ctx.obj['DEBUG'] = debug
    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

cli.add_command(local)

if __name__ == '__main__':
    cli()