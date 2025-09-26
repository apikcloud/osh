import click

from tools.addons.add import main as add
from tools.addons.download import main as download
from tools.addons.gen_table import main as gen_table
from tools.addons.list import main as list


@click.group()
def addons():
    """addons"""


addons.add_command(add)
addons.add_command(download)
addons.add_command(gen_table)
addons.add_command(list)
