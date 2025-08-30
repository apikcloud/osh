#!/usr/bin/env python3
import contextlib
import csv
import json
import subprocess
import sys

import click

from osh.gitutils import git_top, parse_submodules_extended, submodule_update
from osh.helpers import find_addons
from osh.settings import NEW_LINE
from osh.utils import human_readable


@click.command(name="list")
@click.option(
    "--format",
    type=click.Choice(["text", "json", "csv"]),
    default="text",
    show_default=True,
    help="Output format (default: text)",
)
@click.option(
    "--init/--no-init",
    is_flag=True,
    help="Run 'git submodule update --init' for submodules whose path is missing on disk",
)
@click.option(
    "--name",
    "-n",
    "submodules",
    multiple=True,
    help="Limit to these submodule names (as in .gitmodules)",
)
@click.option(
    "--symlinks-only",
    is_flag=True,
    help="Limit to these submodule names (as in .gitmodules)",
)
def main(format: str, init: bool, submodules: tuple, symlinks_only: bool):  # noqa: C901, PLR0912
    """List all addons found in git submodules."""

    repo = git_top()
    gm = repo / ".gitmodules"
    if not gm.exists():
        click.echo("No .gitmodules found.", file=sys.stderr)
        return 1

    if symlinks_only:
        click.echo("Filtering to addons that are symlinks on disk...")
        names = []
        for addon_dir in find_addons(repo, shallow=True):
            if addon_dir.is_symlink():
                names.append(addon_dir.name)

        if names:
            click.echo(f"Found {len(names)} symlinked addon(s):")
            click.echo(human_readable(sorted(names), sep=NEW_LINE))
        return 0

    subs = parse_submodules_extended(gm)
    if submodules:
        subs = {k: v for k, v in subs.items() if k in submodules}

    results = []
    for name, info in subs.items():
        sub_path = info.get("path")
        if not sub_path:
            continue
        abs_path = repo / sub_path
        if not abs_path.exists():
            if init:  # small typo-proofing
                with contextlib.suppress(subprocess.CalledProcessError):
                    submodule_update(sub_path)

            # re-check
            if not abs_path.exists():
                continue
        for addon_dir in find_addons(abs_path):
            results.append(
                {
                    "addon": addon_dir.name,
                    "submodule": name,
                    "path": str(addon_dir.relative_to(repo)),
                    "submodule_path": sub_path,
                    "url": info.get("url") or "",
                    "branch": info.get("branch") or "",
                }
            )

    results.sort(key=lambda item: item["addon"])

    # Output
    if format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif format == "csv":
        fields = ["addon", "submodule", "path", "submodule_path", "url", "branch"]
        w = csv.DictWriter(sys.stdout, fieldnames=fields)
        w.writeheader()
        for row in results:
            w.writerow(row)
    else:
        if not results:
            click.echo("No addons found in local submodules.")
            return 0
        # compact text table
        click.echo(f"Found {len(results)} addon(s):")
        for r in results:
            click.echo(
                f"- {r['addon']:30}  [{r['submodule']}]  {r['path']}  (branch={r['branch'] or '-'})"
            )

    return 0
