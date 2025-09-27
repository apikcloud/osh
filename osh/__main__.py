import click

from osh.addons import addons
from osh.manifest import manifest
from osh.submodules import submodules


@click.group()
def main():
    """OSH"""


main.add_command(addons)
main.add_command(manifest)
main.add_command(submodules)
