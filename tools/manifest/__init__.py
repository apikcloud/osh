import click

from tools.manifest.check import main as check
from tools.manifest.fix import main as fix
from tools.manifest.parser import main as parser


@click.group()
def manifest():
    """manifest"""


manifest.add_command(fix)
manifest.add_command(parser)
manifest.add_command(check)
