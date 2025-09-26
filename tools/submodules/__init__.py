import click

from tools.submodules.add import main as add
from tools.submodules.check import main as check
from tools.submodules.clean import main as clean
from tools.submodules.prune import main as prune
from tools.submodules.rewrite import main as rewrite


@click.group()
def submodules():
    """submodules"""


submodules.add_command(add)
submodules.add_command(check)
submodules.add_command(clean)
submodules.add_command(prune)
submodules.add_command(rewrite)
