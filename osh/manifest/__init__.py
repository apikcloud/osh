import click

from osh.manifest.check import main as check
from osh.manifest.fix import main as fix


@click.group()
def manifest():
    """Manage manifests"""


manifest.add_command(fix)
manifest.add_command(check)
