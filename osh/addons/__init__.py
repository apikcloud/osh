import click

from osh.addons.add import main as add
from osh.addons.diff import main as diff
from osh.addons.download import main as download
from osh.addons.gen_table import main as gen_table
from osh.addons.list import main as list
from osh.addons.materialize import main as materialize


@click.group()
def addons():
    """Manage addons"""


addons.add_command(add)
addons.add_command(diff)
addons.add_command(download)
addons.add_command(gen_table)
addons.add_command(list)
addons.add_command(materialize)
