#!/usr/bin/env python3
import logging
import subprocess
import sys

from tools.gitutils import git_top, parse_submodules
from tools.helpers import run, symlink_targets

# --- helpers ---


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
    for name, item in subs.items():
        path = str(repo / item["path"])
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

    for path in ["third-party", ".third-party"]:
        old_base_path = repo / path

        if old_base_path.exists():
            print(f"[prune] removing empty dir: {old_base_path}")
            try:
                old_base_path.rmdir()
            except OSError as error:
                logging.error(error)

    print("\n✅ Unused submodules removed. Don't forget to commit:")
    print("   git commit -m 'chore: remove unused submodules'")

    return 0


if __name__ == "__main__":
    sys.exit(main())
