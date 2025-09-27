import click

from osh.project.check import main as check
from osh.project.update import main as update


@click.group()
def project():
    """project"""


project.add_command(check)
project.add_command(update)
