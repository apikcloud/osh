#!/usr/bin/env python3

import logging
import os
from pathlib import Path

import click

from osh.exceptions import MissingMandatoryFiles, MissingRecommendedFiles
from osh.gitutils import git_top
from osh.odoo import check_image, fetch_odoo_images, find_available_images, parse_image_tag
from osh.utils import human_readable, read_and_parse

PROJECT_MANDATORY_FILES = {"requirements.txt", "odoo_version.txt", "packages.txt"}
PROJECT_RECOMMENDED_FILES = {"README.md", "CODEOWNERS", "CHANGELOG.md", "blabla"}

PROJECT_FILE_PACKAGES = "packages.txt"
PROJECT_FILE_REQUIREMENTS = "requirements.txt"
PROJECT_FILE_ODOO_VERSION = "odoo_version.txt"

NEW_LINE = "\n"


def check_project(path: Path, strict: bool = True):
    files = set(os.listdir(path))
    missing_files = PROJECT_MANDATORY_FILES.difference(files)
    if missing_files:
        raise MissingMandatoryFiles(missing_files)

    missing_recommended_files = PROJECT_RECOMMENDED_FILES.difference(files)
    if missing_recommended_files:
        if strict:
            raise MissingRecommendedFiles(missing_recommended_files)
        else:
            logging.warning(MissingRecommendedFiles.message.format(files=missing_recommended_files))


def parse_packages(path: Path) -> list:
    return read_and_parse(path / PROJECT_FILE_PACKAGES)


def parse_requirements(path) -> list:
    return read_and_parse(path / PROJECT_FILE_REQUIREMENTS)


def parse_odoo_version(path) -> str:
    res = read_and_parse(path / PROJECT_FILE_ODOO_VERSION)
    if not res:
        raise ValueError()
    return res[0]


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

    return
    res = fetch_odoo_images()
    print(res)
