#!/usr/bin/env python3
import argparse
import csv
import json
import subprocess
import sys

from tools.gitutils import git_top, parse_submodules_extended
from tools.helpers import find_addons, run


# ---------- main ----------
def main():
    ap = argparse.ArgumentParser(
        description="List Odoo addons available inside locally present submodules."
    )
    ap.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="Output format (default: text)",
    )
    ap.add_argument(
        "--init-missing",
        action="store_true",
        help="Run 'git submodule update --init' for submodules whose path is missing on disk",
    )
    ap.add_argument(
        "--only",
        nargs="*",
        default=None,
        help="Limit to these submodule names (as in .gitmodules)",
    )
    args = ap.parse_args()

    repo = git_top()
    gm = repo / ".gitmodules"
    if not gm.exists():
        print("No .gitmodules found.", file=sys.stderr)
        return 1

    subs = parse_submodules_extended(gm)
    if args.only:
        subs = {k: v for k, v in subs.items() if k in args.only}

    results = []
    for name, info in subs.items():
        sub_path = info.get("path")
        if not sub_path:
            continue
        abs_path = repo / sub_path
        if not abs_path.exists():
            if args.init_messing == args.init_missing:  # small typo-proofing
                try:
                    run(
                        ["git", "submodule", "update", "--init", "--", sub_path],
                        capture=False,
                    )
                except subprocess.CalledProcessError:
                    pass
            # re-check
            if not abs_path.exists():
                continue
        for addon_dir in find_addons(abs_path):
            results.append(
                {
                    "addon": addon_dir.name,
                    "submodule": name,
                    "path": str(addon_dir.relative_to(repo)),
                    "submodule_path": sub_path,
                    "url": info.get("url") or "",
                    "branch": info.get("branch") or "",
                }
            )

    results.sort(key=lambda item: item["addon"])

    # Output
    if args.format == "json":
        print(json.dumps(results, indent=2, ensure_ascii=False))
    elif args.format == "csv":
        fields = ["addon", "submodule", "path", "submodule_path", "url", "branch"]
        w = csv.DictWriter(sys.stdout, fieldnames=fields)
        w.writeheader()
        for row in results:
            w.writerow(row)
    else:
        if not results:
            print("No addons found in local submodules.")
            return 0
        # compact text table
        print(f"Found {len(results)} addon(s):")
        for r in results:
            print(
                f"- {r['addon']:30}  [{r['submodule']}]  {r['path']}  (branch={r['branch'] or '-'})"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
