import os

import click

from osh.gitutils import (
    commit,
    git_add,
    git_top,
    guess_submodule_name,
    parse_submodules,
    rename_submodule,
)
from osh.messages import GIT_SUBMODULES_RENAME
from osh.utils import is_pull_request_path


@click.command("rename")
@click.option("--dry-run", is_flag=True, help="Show planned changes only")
@click.option("--no-commit", is_flag=True, help="Do not commit changes")
def main(dry_run: bool, no_commit: bool):
    """
    Rename git submodules
    """

    repo = git_top()
    os.chdir(repo)

    gm = repo / ".gitmodules"
    if not gm.exists():
        click.echo("No .gitmodules found.")
        raise click.Abort()

    subs = parse_submodules(gm)

    # print(subs)

    for name, values in subs.items():
        pull_request = is_pull_request_path(values["path"]) or is_pull_request_path(name)
        new_name = guess_submodule_name(values["url"], pull_request=pull_request)
        if name != new_name:
            click.echo(f"Renaming submodule '{name}' -> '{new_name}'")
            rename_submodule(str(gm), name, new_name, values, dry_run)

    if not no_commit and not dry_run:
        click.echo("Committing changes...")
        git_add([str(gm), ".git/config"])
        commit(GIT_SUBMODULES_RENAME, skip_hook=True)
    else:
        click.echo("Done. Commit .gitmodules changes to share them with the team.")
