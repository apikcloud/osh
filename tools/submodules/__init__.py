import os

import click

from tools.submodules.add import main as add
from tools.submodules.check import main as check
from tools.submodules.clean import main as clean
from tools.submodules.prune import main as prune
from tools.submodules.rewrite import main as rewrite
from tools.utils import run_script


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    default=".",
)
def flatten(path: str):
    output = run_script("submodules/flatten.sh", path)
    if output:
        click.echo(output)


@click.group()
def submodules():
    """submodules"""


submodules.add_command(add)
submodules.add_command(check)
submodules.add_command(clean)
submodules.add_command(prune)
submodules.add_command(rewrite)
submodules.add_command(flatten)
