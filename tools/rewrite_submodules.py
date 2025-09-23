#!/usr/bin/env python3
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


# -------- helpers --------
def run(cmd, check=True, capture=False, cwd=None):
    kwargs = dict(text=True, cwd=cwd)
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
    urls = git_get_regexp(gitmodules, r"^submodule\..*\.url$")
    paths = git_get_regexp(gitmodules, r"^submodule\..*\.path$")
    info = {}
    for k, v in urls:
        name = k.split(".")[1]
        info.setdefault(name, {})["url"] = v
    for k, v in paths:
        name = k.split(".")[1]
        info.setdefault(name, {})["path"] = v
    return info


def parse_org_repo_from_url(url: str):
    if re.match(r"^[\w.-]+@[\w.-]+:", url):
        host_path = url.split(":", 1)[1]
        parts = host_path.strip("/").split("/")
    else:
        u = urlparse(url)
        parts = u.path.strip("/").split("/")
    if len(parts) < 2:
        raise ValueError(f"Cannot parse org/repo from URL: {url}")
    org, repo = parts[-2], parts[-1]
    if repo.endswith(".git"):
        repo = repo[:-4]
    return org, repo


def desired_path(url: str, base_dir: str):
    org, repo = parse_org_repo_from_url(url)
    if org == "oca":
        org = org.upper()
    return f"{base_dir.rstrip('/')}/{org}/{repo}"


def ask(prompt: str, default="y"):
    ans = input(prompt).strip().lower()
    if not ans:
        ans = default
    return ans


def ensure_parent(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)


def move_with_git(src: Path, dst: Path):
    ensure_parent(dst)
    try:
        run(["git", "mv", "-k", str(src), str(dst)])
    except subprocess.CalledProcessError:
        if src.exists():
            src.rename(dst)
        run(["git", "add", "-A", str(dst)])
        try:
            run(["git", "rm", "-f", "--cached", str(src)])
        except subprocess.CalledProcessError:
            pass


def rewrite_symlink(link: Path, old_prefix: str, new_prefix: str):
    try:
        target = os.readlink(link)
    except OSError:
        return False
    if old_prefix in target:
        new_target = target.replace(old_prefix, new_prefix)
        link.unlink()
        os.symlink(new_target, link)
        return True
    return False


# -------- main --------
def main():
    ap = argparse.ArgumentParser(
        description="Rewrite submodule paths based on remote URL (url -> .third-party/org/repo)."
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
            print(f"[warn] skip move: {oldp} not found")

    run(["git", "submodule", "sync", "--recursive"])
    run(["git", "submodule", "update", "--init", "--recursive"])

    # Rewrite symlinks
    rewrites = 0
    for root, dirs, files in os.walk(repo):
        if ".git" in dirs:
            dirs.remove(".git")
        for name in dirs + files:
            p = Path(root) / name
            if p.is_symlink():
                for _, _, oldp, newp in accepted:
                    if rewrite_symlink(p, oldp, newp):
                        rewrites += 1
                        break
    print(f"Symlinks rewritten: {rewrites}")

    # Auto commit
    if not args.no_commit:
        run(
            [
                "git",
                "commit",
                "-am",
                "chore: rewrite submodule paths based on remote URL",
            ]
        )
        print("Changes committed.")


if __name__ == "__main__":
    sys.exit(main())
