#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path

from tools.helpers import run


# --- helpers ---
def run(cmd, check=True, capture=False):
    kwargs = dict(text=True)
    if capture:
        kwargs.update(stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res = subprocess.run(cmd, check=check, **kwargs)
    return res.stdout if capture else None


def git_top():
    out = run(["git", "rev-parse", "--show-toplevel"], capture=True).strip()
    return Path(out)


def git_get_regexp(gitmodules: Path, pattern: str):
    try:
        out = run(
            ["git", "config", "-f", str(gitmodules), "--get-regexp", pattern],
            capture=True,
        )
        kv = []
        for l in out.splitlines():
            k, v = l.split(" ", 1)
            kv.append((k.strip(), v.strip()))
        return kv
    except subprocess.CalledProcessError:
        return []


def parse_submodules(gitmodules: Path):
    paths = git_get_regexp(gitmodules, r"^submodule\..*\.path$")
    info = {}
    for k, v in paths:
        name = k.split(".")[1]
        info[name] = v
    return info


def symlink_targets(repo: Path):
    targets = []
    for root, dirs, files in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")
        for n in dirs + files:
            p = Path(root) / n
            if p.is_symlink():
                try:
                    targets.append(os.readlink(p))
                except OSError:
                    pass
    return targets


# --- main ---
def main():
    repo = git_top()
    gm = repo / ".gitmodules"
    if not gm.exists():
        print("No .gitmodules found.")
        return 0

    subs = parse_submodules(gm)
    if not subs:
        print("No submodules found.")
        return 0

    targets = symlink_targets(repo)

    unused = []
    for name, path in subs.items():
        if not any(path in t for t in targets):
            unused.append((name, path))

    if not unused:
        print("✅ No unused submodules detected.")
        return 0

    print("The following submodules appear unused (no symlinks point to them):")
    for name, path in unused:
        print(f"  - {name}: {path}")

    confirm = input("\nRemove these submodules? [y/N] ").strip().lower()
    if confirm not in ("y", "yes"):
        print("Aborted.")
        return 1

    for name, path in unused:
        print(f"[remove] {name}: {path}")
        # Deinit
        run(["git", "submodule", "deinit", "-f", path])
        # Remove from index + working tree
        run(["git", "rm", "-f", path])
        # Cleanup .git/modules leftovers
        moddir = repo / ".git" / "modules" / path
        if moddir.exists():
            print(f"[cleanup] removing {moddir}")
            subprocess.run(["rm", "-rf", str(moddir)])

    print("\n✅ Unused submodules removed. Don't forget to commit:")
    print("   git commit -m 'chore: remove unused submodules'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
