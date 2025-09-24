#!/usr/bin/env python3
import argparse
import os
import sys
from pathlib import Path

from tools.gitutils import git_top
from tools.helpers import (
    desired_path,
    ensure_parent,
    parse_org_repo_from_url,
    relpath,
    run,
)

# -------- helpers --------


# def parse_org_repo_from_url(url: str):
#     # Supports https://host/org/repo(.git), git@host:org/repo(.git), ssh://git@host/org/repo(.git)
#     if re.match(r"^[\w.-]+@[\w.-]+:", url):
#         host_path = url.split(":", 1)[1]
#         parts = host_path.strip("/").split("/")
#     else:
#         u = urlparse(url)
#         parts = u.path.strip("/").split("/")
#     if len(parts) < 2:
#         raise ValueError(f"Cannot parse org/repo from URL: {url}")
#     org, repo = parts[-2], parts[-1]
#     if repo.endswith(".git"):
#         repo = repo[:-4]
#     return org, repo


def find_addons(submodule_dir: Path):
    """Return addon directories (contain __manifest__.py or __openerp__.py)."""
    addons = []
    for root, dirs, files in os.walk(submodule_dir):
        # speed: ignore .git and typical junk
        if ".git" in dirs:
            dirs.remove(".git")
        if "__manifest__.py" in files or "__openerp__.py" in files:
            addons.append(Path(root))
    return addons


# -------- main --------
def main():
    ap = argparse.ArgumentParser(
        description="Add a git submodule from URL/branch to .third-party/<ORG>/<REPO> and optionally create addon symlinks."
    )
    ap.add_argument(
        "url",
        help="Remote URL of the submodule (e.g., https://github.com/OCA/server-ux.git)",
    )
    ap.add_argument(
        "-b",
        "--branch",
        required=True,
        help="Branch to track for the submodule (e.g., 18.0)",
    )
    ap.add_argument(
        "--base-dir",
        default=".third-party",
        help="Base dir for submodules (default: .third-party)",
    )
    ap.add_argument(
        "--name",
        default=None,
        help="Optional submodule name (defaults to '<ORG>/<REPO>')",
    )
    ap.add_argument(
        "--auto-symlinks",
        action="store_true",
        help="Auto-create symlinks at repo root for each addon folder detected in the submodule",
    )
    ap.add_argument(
        "--symlink-prefix",
        default="",
        help="Optional prefix for created symlinks (default: '')",
    )
    ap.add_argument(
        "--no-commit",
        action="store_true",
        help="Do not commit automatically at the end",
    )
    ap.add_argument("--dry-run", action="store_true", help="Show planned actions only")
    args = ap.parse_args()

    repo = git_top()
    os.chdir(repo)

    # Compute target path and name
    try:
        org, repo_name = parse_org_repo_from_url(args.url)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    sub_path_str = desired_path(args.url, args.base_dir)
    sub_path = repo / sub_path_str
    sub_name = args.name or f"{org}/{repo_name}"

    # Plan summary
    print("=== Plan ===")
    print(f"Repo Root         : {repo}")
    print(f"URL               : {args.url}")
    print(f"Branch            : {args.branch}")
    print(f"Submodule name    : {sub_name}")
    print(f"Target path       : {sub_path_str}")
    print(f"Auto symlinks     : {'yes' if args.auto_symlinks else 'no'}")
    print(f"Symlink prefix    : {args.symlink_prefix!r}")
    print(f"Commit at the end : {'no' if args.no_commit else 'yes'}")
    print(f"Dry-run           : {'yes' if args.dry_run else 'no'}")
    print("==============\n")

    if args.dry_run:
        return 0

    # Safety: prevent overwrite
    if sub_path.exists():
        print(f"Error: destination already exists: {sub_path_str}", file=sys.stderr)
        sys.exit(1)

    ensure_parent(sub_path)

    # Add submodule
    print("[add] git submodule add")
    run(
        [
            "git",
            "submodule",
            "add",
            "-b",
            args.branch,
            "--name",
            sub_name,
            args.url,
            sub_path_str,
        ]
    )

    # Pin branch in .gitmodules (redundant but explicit)
    print("[config] record branch in .gitmodules")
    run(
        [
            "git",
            "config",
            "-f",
            str(repo / ".gitmodules"),
            f"submodule.{sub_name}.branch",
            args.branch,
        ]
    )

    # Sync and fetch content
    print("[sync] git submodule sync --recursive")
    run(["git", "submodule", "sync", "--recursive"])
    print("[update] git submodule update --init --recursive")
    run(["git", "submodule", "update", "--init", "--recursive"])

    created_links = []
    if args.auto_symlinks:
        print("[scan] detecting addon folders…")
        addons = find_addons(sub_path)
        if not addons:
            print("  no addon folders detected.")
        else:
            print(
                f"  found {len(addons)} addon folder(s). Creating symlinks at repo root…"
            )
            for addon_dir in addons:
                link_name = f"{args.symlink_prefix}{addon_dir.name}"
                link_path = repo / link_name
                # Determine relative target from repo root to the addon_dir
                target_rel = relpath(repo, addon_dir)
                if link_path.exists() or link_path.is_symlink():
                    print(f"  [skip] {link_name} already exists")
                    continue
                os.symlink(target_rel, link_path)
                created_links.append(link_name)
                # Stage symlink
                run(["git", "add", link_name])

    # Stage .gitmodules and submodule path
    run(["git", "add", "-A", ".gitmodules", sub_path_str])

    if not args.no_commit:
        lines = [
            f"chore: add submodule {sub_name}",
            "",
            f"- url: {args.url}",
            f"- branch: {args.branch}",
            f"- path: {sub_path_str}",
        ]
        if created_links:
            lines.append("")
            lines.append("Created symlinks:")
            for ln in created_links:
                lines.append(f"- {ln} -> {relpath(repo, repo / ln)}")
        # Preserve newlines robustly
        run(["git", "commit", "-m", lines[0], "-m", "\n".join(lines[2:])])
        print("✅ Submodule added and committed.")
    else:
        print("⚠️  Changes staged but not committed (--no-commit).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
