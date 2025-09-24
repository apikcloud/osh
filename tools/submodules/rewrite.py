#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path

from tools.gitutils import git_top, move_with_git, parse_submodules
from tools.helpers import ask, desired_path, is_dir_empty, rewrite_symlink, run

# -------- helpers --------


# -------- main --------
def main():
    ap = argparse.ArgumentParser(
        description="Rewrite submodule paths from remote URL (url -> .third-party/<ORG>/<REPO>), move folders, fix symlinks, and commit."
    )
    ap.add_argument(
        "--base-dir",
        default=".third-party",
        help="Base directory for rewritten paths (default: .third-party)",
    )
    ap.add_argument(
        "--yes", "-y", action="store_true", help="Apply all changes without prompting"
    )
    ap.add_argument("--dry-run", action="store_true", help="Show planned changes only")
    ap.add_argument(
        "--no-commit",
        action="store_true",
        help="Do not commit automatically at the end",
    )
    ap.add_argument(
        "--old-base-dir",
        default=None,
        help="Old base dir to prune if empty (default: auto-detect, fallback 'third-party')",
    )
    args = ap.parse_args()

    repo = git_top()
    os.chdir(repo)

    gm = repo / ".gitmodules"
    if not gm.exists():
        print("No .gitmodules found.")
        return 0

    subs = parse_submodules(gm)
    plan = []
    for name, d in subs.items():
        url = d.get("url")
        path = d.get("path")
        if not url or not path:
            continue
        target = desired_path(url, args.base_dir)
        if path != target:
            plan.append((name, url, path, target))

    if not plan:
        print("No submodule needs rewriting.")
        return 0

    print(f"Repo: {repo}")
    for name, url, oldp, newp in plan:
        print(f"[plan] {name}\n  url : {url}\n  path: {oldp} -> {newp}")

    if args.dry_run:
        print("Dry-run only.")
        return 0

    accepted = []
    for name, url, oldp, newp in plan:
        if args.yes:
            accepted.append((name, url, oldp, newp))
        else:
            ans = ask(
                f"\nApply change for '{name}' ({oldp} -> {newp})? [Y/n/e] ", default="y"
            )
            if ans in ("y", "yes"):
                accepted.append((name, url, oldp, newp))
            elif ans == "e":
                custom = input("Enter custom target path: ").strip()
                if custom:
                    accepted.append((name, url, oldp, custom))

    if not accepted:
        print("Nothing accepted. Exiting.")
        return 0

    # Update .gitmodules
    for name, _, oldp, newp in accepted:
        key = f"submodule.{name}.path"
        run(["git", "config", "-f", str(gm), key, newp])
    run(["git", "add", str(gm)])

    # Move folders
    for _, _, oldp, newp in accepted:
        src = repo / oldp
        dst = repo / newp
        if src.exists():
            print(f"[move] {oldp} -> {newp}")
            move_with_git(src, dst)
        else:
            # try to init submodule if missing
            print(f"[info] '{oldp}' not found; trying submodule init")
            try:
                run(["git", "submodule", "update", "--init", "--", oldp])
            except subprocess.CalledProcessError:
                pass
            if (repo / oldp).exists():
                print(f"[move] {oldp} -> {newp}")
                move_with_git(repo / oldp, dst)
            else:
                print(f"[warn] skip move: {oldp} still not found")

    # Sync and update submodule metadata
    run(["git", "submodule", "sync", "--recursive"])
    run(["git", "submodule", "update", "--init", "--recursive"])

    # Rewrite symlinks
    rewrites = 0
    # Build a quick lookup for old->new prefixes
    renames = [(oldp, newp) for (_, _, oldp, newp) in accepted]
    for root, dirs, files in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in dirs + files:
            p = Path(root) / name
            if p.is_symlink():
                for oldp, newp in renames:
                    if rewrite_symlink(p, oldp, newp):
                        rewrites += 1
                        break
    print(f"Symlinks rewritten: {rewrites}")

    # Prune old base dir if empty (auto-detect or --old-base-dir)
    old_base = args.old_base_dir
    if not old_base:
        # auto-detect from first path segment of old paths if unique, else fallback
        first_segments = {
            op.split("/", 1)[0] for (_, _, op, _) in accepted if "/" in op
        }
        old_base = first_segments.pop() if len(first_segments) == 1 else "third-party"

    old_base_path = repo / old_base
    if is_dir_empty(old_base_path):
        print(f"[prune] removing empty dir: {old_base_path}")
        try:
            old_base_path.rmdir()
        except OSError:
            # not empty (race) or permission -> skip silently
            pass

    # Stage everything just in case (symlinks/renames)
    run(["git", "add", "-A"])

    # Auto commit with detailed message
    if not args.no_commit:
        lines = [
            "chore: rewrite submodule paths based on remote URL",
            "",
            "Modified submodules:",
        ]
        lines += [f"- {name}: {oldp} -> {newp}" for (name, _, oldp, newp) in accepted]
        msg = "\n".join(lines)
        # Use -m twice to preserve newlines robustly
        run(["git", "commit", "-m", lines[0], "-m", "\n".join(lines[2:])])
        print("Changes committed.")
    else:
        print("Changes staged but not committed (--no-commit).")


if __name__ == "__main__":
    sys.exit(main())
