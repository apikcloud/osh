import contextlib
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path

from osh.compat import Optional, Union
from osh.exceptions import NoGitRepository
from osh.helpers import ensure_parent, find_addons_extended
from osh.utils import format_datetime, human_readable, parse_repository_url, run

pattern = re.compile(r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
pattern = re.compile(r"^v(?P<x>0|[1-9]\d*)\.(?P<y>0|[1-9]\d*)\.(?P<z>0|[1-9]\d*)$")


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


def git_add(paths: list):
    cmd = ["git", "add"] + paths
    subprocess.check_call(cmd)


def git_config_submodule(filepath: str, submodule: str, key: str, value: str):
    cmd = [
        "git",
        "config",
        "-f",
        filepath,
        f"submodule.{submodule}.{key}",
        value,
    ]
    run(cmd, name="config")


def submodule_deinit(path: str, delete: bool = False) -> None:
    run(["git", "submodule", "deinit", "-f", path], name="submodule deinit")

    if delete:
        # Remove from index + working tree
        run(["git", "rm", "-f", path], name="submodule delete")


def commit(message: str, description: Optional[str] = None, skip_hook: bool = False):
    cmd = [
        "git",
        "commit",
        "-m",
        message,
    ]
    if description:
        # Use -m twice to preserve newlines robustly
        cmd.extend(["-m", description])
    if skip_hook:
        cmd.insert(2, "--no-verify")
    run(cmd, name="commit")


def add_submodule(url: str, name: str, path: str, branch: Optional[str] = None) -> None:
    cmd = [
        "git",
        "submodule",
        "add",
        "--name",
        name,
    ]
    if branch:
        cmd.extend(["-b", branch])
    cmd.extend([url, path])
    run(cmd, name="add submodule")


def submodule_sync() -> None:
    cmd = ["git", "submodule", "sync", "--recursive"]
    run(cmd, name="sync")


def submodule_update(path: Optional[str] = None) -> None:
    cmd = ["git", "submodule", "update", "--init"]

    if path:
        cmd.extend(["--", path])
    else:
        cmd.extend(["--recursive"])

    run(cmd, name="update")


def git_reset_hard() -> None:
    run(["git", "reset", "--hard"])


def git_top() -> Path:
    out = run(["git", "rev-parse", "--show-toplevel"], capture=True, name="top")
    if not out:
        raise NoGitRepository()

    return Path(out.strip())


def git_add_all():
    run(["git", "add", "-A"], name="add")


def git_get_regexp(gitmodules: Path, pattern: str):
    try:
        out = run(
            ["git", "config", "-f", str(gitmodules), "--get-regexp", pattern],
            capture=True,
        )

        if not out:
            return []

        kv = []
        for line in out.splitlines():
            k, v = line.split(" ", 1)
            kv.append((k.strip(), v.strip()))
        return kv
    except subprocess.CalledProcessError:
        return []


def parse_submodules(gitmodules: Path):
    urls = git_get_regexp(gitmodules, r"^submodule\..*\.url$")
    paths = git_get_regexp(gitmodules, r"^submodule\..*\.path$")
    branches = git_get_regexp(gitmodules, r"^submodule\..*\.branch$")
    info = {}
    for k, v in urls:
        name = k.split(".")[1]
        info.setdefault(name, {})["url"] = v
    for k, v in paths:
        name = k.split(".")[1]
        info.setdefault(name, {})["path"] = v
    for k, v in branches:
        name = k.split(".")[1]
        info.setdefault(name, {})["branch"] = v
    return info


def parse_submodules_extended(gitmodules: Path):
    """Return dict name -> {'path': str, 'url': str, 'branch': str|None}"""
    paths = {k.split(".")[1]: v for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.path$")}
    urls = {k.split(".")[1]: v for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.url$")}
    branches = {
        k.split(".")[1]: v for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.branch$")
    }  # noqa: E501
    out = {}
    for name in set(paths) | set(urls) | set(branches):
        out[name] = {
            "path": paths.get(name),
            "url": urls.get(name),
            "branch": branches.get(name),
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
        with contextlib.suppress(subprocess.CalledProcessError):
            run(["git", "rm", "-f", "--cached", str(src)])


def update_gitignore(  # noqa: C901
    file_path: Union[str, Path],
    folders: list,
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
        idx = next(i for i, line in enumerate(lines) if line.strip() == header_line)
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

    p.write_text(human_readable(lines), encoding="utf-8")
    return True


def list_available_addons(root: Path):
    gitmodules = root / ".gitmodules"

    if not gitmodules.exists():
        raise FileNotFoundError()

    subs = parse_submodules_extended(gitmodules)

    for _, info in subs.items():
        sub_path = info.get("path")
        if not sub_path:
            continue
        abs_path = root / sub_path
        if not abs_path.exists():
            with contextlib.suppress(subprocess.CalledProcessError):
                submodule_update(sub_path)

            # re-check
            if not abs_path.exists():
                continue
        yield from find_addons_extended(abs_path)


def guess_submodule_name(url: str, pull_request: bool = False) -> str:
    """Return a guessed submodule name from its URL, or None if not possible."""
    _, owner, repo = parse_repository_url(url)
    if owner == "oca":
        owner = owner.upper()

    if pull_request:
        return f"PRs/{owner}/{repo}"

    return f"{owner}/{repo}"


def get_submodule_config(filepath: str, name: str, key: str) -> str:
    # Read current path/url/branch from .gitmodules (old name)

    return run(
        ["git", "config", "-f", filepath, f"submodule.{name}.{key}"],
        capture=True,
        check=False,
    ).strip()


def rename_submodule(  # noqa: PLR0913
    gitmodules_file: str,
    name: str,
    new_name: str,
    values: dict,
    dry_run: bool = False,
):
    # Guard if new_name already exists
    existing_new_path = run(
        ["git", "config", "-f", gitmodules_file, f"submodule.{new_name}.path"],
        capture=True,
        check=False,
    ).strip()
    if existing_new_path:
        raise ValueError(f"A submodule named '{new_name}' already exists in .gitmodules.")

    path = values.get("path")
    url = values.get("url")
    branch = values.get("branch")

    logging.debug(f"Renaming submodule identifier '{name}' -> '{new_name}' (path stays '{path}')")
    if dry_run:
        logging.info("[dry-run] Would write .gitmodules: submodule.{name} -> submodule.{new_name}")
        logging.info("[dry-run] Would remove old sections from .gitmodules and .git/config")
        logging.info("[dry-run] Would run: git submodule sync --recursive")
        return

    # Write new section in .gitmodules
    run(["git", "config", "-f", gitmodules_file, f"submodule.{new_name}.path", path])
    run(["git", "config", "-f", gitmodules_file, f"submodule.{new_name}.url", url])
    if branch:
        run(["git", "config", "-f", gitmodules_file, f"submodule.{new_name}.branch", branch])

    # Remove old section from .gitmodules and local .git/config
    run(
        ["git", "config", "-f", gitmodules_file, "--remove-section", f"submodule.{name}"],
        check=False,
    )
    # run(["git", "config", "--remove-section", f"submodule.{name}"], check=False)

    # Sync .git/config from .gitmodules
    run(["git", "submodule", "sync", "--recursive"])


def get_last_tag() -> Optional[str]:
    try:
        out = run(["git", "describe", "--tags", "--abbrev=0"], capture=True)
        return out.strip() if out else None
    except subprocess.CalledProcessError:
        return None


def get_last_release():
    try:
        last_tag = get_last_tag()
        if not last_tag:
            return None
    except Exception:
        return None

    if not bool(pattern.match(last_tag)):
        return None

    return last_tag


def get_next_releases() -> tuple:
    last_release = get_last_release()
    if not last_release:
        raise ValueError("No valid last release tag found")
    m = pattern.match(last_release)

    if not m:
        raise ValueError(f"Last release tag '{last_release}' is not in valid semver format")

    x, y, z = int(m.group("x")), int(m.group("y")), int(m.group("z"))

    normal = f"v{x}.{y + 1}.0"
    fix = f"v{x}.{y}.{z + 1}"
    major = f"v{x + 1}.0.0"

    return normal, fix, major


def get_last_commit() -> Optional[str]:
    try:
        output = run(
            ["git", "log", "-1", "--date=iso-strict", "--pretty=format:%h;%an <%ae>;%ad;%s"],
            capture=True,
        )
        if not output:
            return None

        sha, author, date_str, message = output.split(";", 3)
        commit_date = datetime.fromisoformat(date_str)
        return f"{message} by {author} on {format_datetime(commit_date)} ({sha})"
    except subprocess.CalledProcessError:
        return None


def get_remote_url(path=".", origin="origin") -> tuple:
    result = subprocess.run(
        ["git", "-C", path, "remote", "get-url", origin],
        check=True,
        text=True,
        capture_output=True,
    )

    return parse_repository_url(result.stdout.strip())
