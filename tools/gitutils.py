# Copyright (c) 2018 ACSONE SA/NV
# License AGPLv3 (https://www.gnu.org/licenses/agpl-3.0-standalone.html)
import subprocess
import sys
from pathlib import Path
from typing import Iterable

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


def update_gitignore(
    file_path: str | Path,
    folders: Iterable[str],
    header: str = "# Ignored addons (auto)",
) -> bool:
    """
    Ensure given folder names are present in .gitignore under a bottom 'header' section.
    - Adds missing entries only (idempotent).
    - Normalizes folder patterns to 'name/'.
    - Appends a header at EOF if absent, then the new folders under it.

    Returns True if the file was modified, False otherwise.
    """
    p = Path(file_path)
    lines: list[str] = []
    if p.exists():
        lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

    # Normalize target patterns to directory form 'name/'
    def canon(s: str) -> str:
        base = s.strip().strip("/").lstrip("./")
        return f"{base}/" if base else ""

    wanted = sorted({canon(f) for f in folders if canon(f)})
    if not wanted:
        return False

    # Collect existing patterns (treat 'foo' and 'foo/' as duplicates)
    existing = set()
    for raw in lines:
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        existing.add(s.rstrip("/"))

    missing = [w for w in wanted if w.rstrip("/") not in existing]
    if not missing:
        return False

    # Find or create header location
    header_line = header.strip()
    try:
        idx = next(i for i, l in enumerate(lines) if l.strip() == header_line)
        insert_at = idx + 1
        block = []
        # Add a blank line after header if not already
        if insert_at >= len(lines) or lines[insert_at].strip():
            block.append("\n")
        block += [f"{m}\n" for m in missing]
        lines[insert_at:insert_at] = block
    except StopIteration:
        # Ensure file ends with a newline
        if lines and not lines[-1].endswith("\n"):
            lines[-1] = lines[-1] + "\n"
        # Append header + entries at EOF
        tail = []
        if lines and lines[-1].strip():
            tail.append("\n")
        tail.append(f"{header_line}\n")
        tail += [f"{m}\n" for m in missing]
        lines.extend(tail)

    p.write_text("".join(lines), encoding="utf-8")
    return True


# Example:
# update_gitignore(".gitignore", [".venv", "dist", "build", "node_modules"], header="# Project folders (managed)")
