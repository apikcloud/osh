#!/usr/bin/env python3


import click

from osh.gitutils import git_top
from osh.odoo import check_image, find_available_images, parse_image_tag
from osh.project.common import check_project, parse_odoo_version, parse_packages, parse_requirements
from osh.utils import human_readable


@click.command(name="check")
@click.option("--strict", is_flag=True, help="Enforce check")
def main(strict: bool):  # noqa: C901
    repo = git_top()

    check_project(repo, strict)
    packages = parse_packages(repo)
    requirements = parse_requirements(repo)
    odoo_version = parse_odoo_version(repo)
    image_infos = parse_image_tag(odoo_version)
    check_image(image_infos)

    available_images = find_available_images(
        release=image_infos.release,
        version=image_infos.major_version,
        enterprise=image_infos.enterprise,
    )

    summary = (
        f"System packages ({len(packages)}): "
        f"{human_readable(packages) or '--'}\n"
        f"Python requirements ({len(requirements)}): "
        f"{human_readable(requirements)}\n"
        f"Odoo version: {image_infos.major_version}\n"
        f"Source: {image_infos.registry}/{image_infos.repository}"
    )

    click.echo(summary)

    click.echo(f"Available images: {len(available_images)}")
    click.echo("Day(s)\t\tRegistry\t\tImage")
    for item in available_images:
        click.echo(f"{item['delta']}\t\t{item['registry']}\t\t{item['image']}")
