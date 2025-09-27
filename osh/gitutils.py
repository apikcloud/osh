import contextlib
import subprocess
from pathlib import Path

from osh.compat import Iterable, Optional, Union
from osh.exceptions import NoGitRepository
from osh.helpers import ensure_parent, find_addons_extended
from osh.utils import human_readable, run


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
        cmd.insert(2, "--no-veritfy")
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
        (k.split(".")[1], v) for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.path$")
    )
    urls = dict(
        (k.split(".")[1], v) for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.url$")
    )
    branches = dict(
        (k.split(".")[1], v) for k, v in git_get_regexp(gitmodules, r"^submodule\..*\.branch$")
    )
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
