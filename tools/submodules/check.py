#!/usr/bin/env python3
import os
import subprocess
import sys
from pathlib import Path


# --- helpers ---
def run(cmd, capture=True):
    res = subprocess.run(cmd, text=True, capture_output=capture, check=True)
    return res.stdout if capture else None


def git_top():
    out = run(["git", "rev-parse", "--show-toplevel"]).strip()
    return Path(out)


def git_get_regexp(gitmodules: Path, pattern: str):
    try:
        out = run(["git", "config", "-f", str(gitmodules), "--get-regexp", pattern])
        lines = [l for l in out.splitlines() if l.strip()]
        kv = []
        for l in lines:
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
    bad_paths = []
    unused = []

    for name, path in subs.items():
        if not path.startswith(".third-party/"):
            bad_paths.append((name, path))
        # Check if any symlink target mentions this path
        if not any(path in t for t in targets):
            unused.append((name, path))

    ok = True
    if bad_paths:
        print("❌ Submodules not under .third-party:")
        for name, path in bad_paths:
            print(f"  - {name}: {path}")
        ok = False

    if unused:
        print("❌ Unused submodules (no symlink points to them):")
        for name, path in unused:
            print(f"  - {name}: {path}")
        ok = False

    if ok:
        print(
            "✅ All submodules are under .third-party and used by at least one symlink."
        )
        return 0
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
