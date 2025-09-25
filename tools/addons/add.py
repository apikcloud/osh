#!/usr/bin/env python3
import logging
import os
import sys

import click

from tools.gitutils import git_top, list_available_addons
from tools.helpers import find_addons_extended, relpath, run, str_to_list


@click.command()
@click.argument("addons")
@click.option("--commit/--no-commit", is_flag=True, default=True)
def main(addons: str, commit: bool):
    repo = git_top()
    os.chdir(repo)

    existing_addons = [name for name, _, _ in find_addons_extended(repo)]
    addons = set(str_to_list(addons)) - set(existing_addons)

    addons_to_link = {}
    for name, path, manifest in list_available_addons(repo):
        if name in addons:
            addons_to_link[name] = {"path": path, "version": None}

    if not addons_to_link:
        logging.waring("Not found...")
        return 0

    missing_addons = set(addons_to_link.keys()).difference(addons)

    if missing_addons:
        print(f"Missing addons len({missing_addons}): {', '.join(missing_addons)}")

    created_links = []
    for name, vals in addons_to_link.items():
        link_path = repo / name
        # Determine relative target from repo root to the addon_dir
        target_rel = relpath(repo, vals["path"])
        if link_path.exists() or link_path.is_symlink():
            print(f"  [skip] {name} already exists")
            continue
        os.symlink(target_rel, link_path)
        created_links.append(name)
        # Stage symlink
        run(["git", "add", name])

    if created_links and commit:
        run(
            [
                "git",
                "commit",
                "--no-verify",
                "-m",
                "chore: new addons",
                "-m",
                "\n".join(created_links),
            ]
        )


if __name__ == "__main__":
    sys.exit(main())
