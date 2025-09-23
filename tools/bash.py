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


@click.command()
@click.argument(
    "path",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    default=".",
)
def rewrite_submodules(path: str):
    click.echo(os.getcwd())
    click.echo()

    output = run_script("scripts/rewrite_submodules.sh", "third-party", ".third-party")
    # output = run_script("scripts/rewrite_symlinks.sh", path)
    click.echo(output)
