#!/usr/bin/env python3


import click

from osh.github import get_latest_workflow_run
from osh.gitutils import (
    get_last_commit,
    get_last_release,
    get_next_releases,
    get_remote_url,
    git_top,
)
from osh.odoo import check_image, find_available_images, parse_image_tag
from osh.project.common import check_project, parse_odoo_version, parse_packages, parse_requirements
from osh.utils import format_datetime, human_readable, render_table


@click.command(name="info")
@click.option(
    "--token",
    envvar=["TOKEN", "GH_TOKEN", "GITHUB_TOKEN"],
    help="GitHub token to request API, needs actions:read or repo scope."
    " Envvar is also supported: TOKEN, GH_TOKEN, GITHUB_TOKEN.",
)
def main(token: str):  # noqa: C901
    """Display information about the current project and Odoo image."""

    repo = git_top()

    warnings, errors = check_project(repo, strict=False)
    packages = parse_packages(repo)
    requirements = parse_requirements(repo)
    odoo_version = parse_odoo_version(repo)
    image_infos = parse_image_tag(odoo_version)
    warnings += check_image(image_infos, strict=False)
    last_release = get_last_release()
    url, owner, repo = get_remote_url()

    try:
        stable, fix, major = get_next_releases()
        next_releases = f"stable: {stable}, fix: {fix}, major: {major}"
    except ValueError:
        next_releases = "no valid release found"

    if image_infos.release:
        available_images = find_available_images(
            release=image_infos.release,
            version=image_infos.major_version,
            enterprise=image_infos.enterprise,
        )

        if available_images:
            latest = available_images[0]
            message = (
                f"Found {len(available_images)} available images, "
                f"the latest is {latest.delta} days newer ({latest.release.isoformat()})"
            )
        else:
            message = "No available images found"

    else:
        message = "Current odoo version does not specify a release date, cannot proceed"

    rows = [
        ["Odoo version", f"{image_infos.major_version} ({image_infos.edition})"],
        ["Date of current image", image_infos.release or "no valid release found"],
        ["Registry", image_infos.source],
        ["Available image(s)", message],
        ["System package(s)", human_readable(packages) or "--"],
        ["Python requirement(s)", human_readable(requirements) or "--"],
        ["Git:", ""],
        ["Remote URL", url or "no remote found"],
        ["Last release", last_release or "no valid release found"],
        ["Next release", next_releases],
        ["Last commit", get_last_commit() or "no valid commit found"],
    ]

    if token:
        data = get_latest_workflow_run(owner=owner, repo=repo, token=token, branch="main")

        rows.append(["GitHub Actions:", ""])
        # rows.append(
        #     [data["workflow"], f"On {data['event']}: {data['status']} ({data['conclusion']})"]
        # )
        rows.append(["Workflow", data["workflow"]])
        rows.append(["Event", data["event"]])
        rows.append(["Status", data["status"]])
        rows.append(["Conclusion", data["conclusion"]])
        rows.append(["SHA", data["sha"]])
        rows.append(
            ["Created at", f"{format_datetime(data['created_at'])} ({data['age']} days ago)"]
        )
        rows.append(["URL", data["url"]])

    if warnings:
        for row in warnings:
            rows.append([click.style("Warning", fg="yellow"), click.style(row, fg="yellow")])

    if errors:
        for row in errors:
            rows.append([click.style("Error", fg="red"), click.style(row, fg="red")])

    click.echo(render_table(rows))
