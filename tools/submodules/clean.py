#!/usr/bin/env python3
import logging
import shutil
import sys

import click

from tools.gitutils import git_top, parse_submodules
from tools.helpers import run

"""
blabla
"""


@click.command(help=__doc__)
@click.option("--reset", is_flag=True, help="Do a hard reset before")
def main(reset: bool):
    """Clean..."""
    repo = git_top()
    gm = repo / ".gitmodules"
    if not gm.exists():
        print("No .gitmodules found.")
        return 0

    if reset:
        run(["git", "reset", "--hard"])

    subs = parse_submodules(gm)
    if not subs:
        print("No submodules found.")
        return 0

    for path in ["third-party", ".third-party"]:
        old_base_path = repo / path

        if old_base_path.exists():
            print(f"[prune] removing empty dir: {old_base_path}")
            try:
                shutil.rmtree(old_base_path)
            except OSError as error:
                logging.error(error)

    run(["git", "submodule", "update", "--init", "--recursive"])


if __name__ == "__main__":
    sys.exit(main())
