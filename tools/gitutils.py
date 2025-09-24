# Copyright (c) 2018 ACSONE SA/NV
# License AGPLv3 (https://www.gnu.org/licenses/agpl-3.0-standalone.html)
import subprocess
import sys
from pathlib import Path

from tools.helpers import ensure_parent, run


def commit_if_needed(paths, message, add=True):
    if add:
        cmd = ["git", "add"] + paths
        subprocess.check_call(cmd)
    cmd = ["git", "diff", "--quiet", "--exit-code", "--cached", "--"] + paths
    r = subprocess.call(cmd)
    if r != 0:
        cmd = ["git", "commit", "-m", message, "--"] + paths
        subprocess.check_call(cmd)
        return True
    else:
        return False


# def git_top():
#     out = run(["git", "rev-parse", "--show-toplevel"], capture=True).strip()
#     return Path(out)


def git_top() -> Path:
    out = run(["git", "rev-parse", "--show-toplevel"], capture=True).strip()
    if not out:
        print("Error: not inside a Git repo.", file=sys.stderr)
        sys.exit(1)
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


def parse_submodules_extended(gitmodules: Path):
    """Return dict name -> {'path': str, 'url': str, 'branch': str|None}"""
    paths = dict(
        (k.split(".")[1], v)
        for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.path$")
    )
    urls = dict(
        (k.split(".")[1], v)
        for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.url$")
    )
    brs = dict(
        (k.split(".")[1], v)
        for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.branch$")
    )
    out = {}
    for name in set(paths) | set(urls) | set(brs):
        out[name] = {
            "path": paths.get(name),
            "url": urls.get(name),
            "branch": brs.get(name),
        }
    return out


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
