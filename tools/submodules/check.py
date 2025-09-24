#!/usr/bin/env python3
import sys

from tools.gitutils import git_top, parse_submodules
from tools.helpers import symlink_targets


# --- main ---
def main():
    repo = git_top()
    gm = repo / ".gitmodules"
    if not gm.exists():
        print("No .gitmodules found.")
        return 0

    subs = parse_submodules(gm)
    print(subs)
    if not subs:
        print("No submodules found.")
        return 0

    targets = symlink_targets(repo)
    bad_paths = []
    unused = []

    for name, item in subs.items():
        path = str(repo / item["path"])
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
