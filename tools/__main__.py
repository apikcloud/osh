import click

from tools.addons import addons
from tools.manifest import manifest
from tools.submodules import submodules


@click.group()
def main():
    """OSH"""


main.add_command(addons)
main.add_command(manifest)
main.add_command(submodules)
