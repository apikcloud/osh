#!/usr/bin/env python3
import logging
import os
import shutil
import sys
import tempfile

import click

from tools.github import fetch_branch_zip
from tools.gitutils import git_top, update_gitignore
from tools.helpers import find_addons, run, str_to_list
from tools.utils import parse_repository_url

logging.basicConfig(level=logging.INFO)


@click.command()
@click.argument("url")
@click.argument("branch")
@click.option("--token")
@click.option("--addons")
def main(url: str, branch: str, token: str = None, addons: str = None):
    local_repo = git_top()
    gitignore = local_repo / ".gitignore"
    url, owner, repo = parse_repository_url(url)
    addon = str_to_list(addons)

    options = {}
    if token:
        options["token"] = token

    with tempfile.TemporaryDirectory() as tmpdirname:
        _, extracted_root = fetch_branch_zip(owner, repo, branch, tmpdirname, **options)

        logging.debug(extracted_root)
        logging.debug(os.listdir(extracted_root))

        new_addons = []
        skipped_addons = []
        for addon in find_addons(extracted_root):
            if addons and addon.name not in addons:
                skipped_addons.append(addon.name)
                continue

            target_path = os.path.join(local_repo, addon.name)

            try:
                logging.debug(f"Copy {addon.name} from {addon} to {target_path}")
                shutil.copytree(addon, target_path)
            except FileExistsError:
                logging.warning(f"Skip {addon.name}")
                skipped_addons.append(addon.name)
                continue

            new_addons.append(addon.name)

        if skipped_addons:
            logging.debug(" ".join(skipped_addons))

        if not new_addons:
            return 0

        logging.info(f"Addons added ({len(new_addons)}): {', '.join(new_addons)}")
        update_gitignore(gitignore, new_addons)
        run(["git", "add", gitignore])
        run(
            [
                "git",
                "commit",
                "-m",
                "chore: ignored addons",
            ]
        )


if __name__ == "__main__":
    sys.exit(main())
