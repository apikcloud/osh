import os

import click

from tools.utils import run_script


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    default=".",
)
def flatten_submodules(path: str):
    click.echo(os.getcwd())
    click.echo()

    output = run_script("scripts/flatten_submodules.sh", path)
    click.echo(output)
