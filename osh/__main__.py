import click

from osh.addons import addons
from osh.manifest import manifest
from osh.project import project
from osh.submodules import submodules


@click.group()
def main():
    """Odoo Scripts & Heplers (osh) - Manage Odoo projects with ease."""


main.add_command(addons)
main.add_command(manifest)
main.add_command(submodules)
main.add_command(project)
