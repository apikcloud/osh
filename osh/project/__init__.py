import click

from osh.project.check import main as check
from osh.project.exclusions import main as exclude
from osh.project.info import main as info
from osh.project.update import main as update


@click.group()
def project():
    """Manage project"""


project.add_command(check)
project.add_command(update)
project.add_command(exclude)
project.add_command(info)
