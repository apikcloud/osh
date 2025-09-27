"""
Minimal, end-to-end flavored test for 'osh-sub-rewrite'.

We simulate a repo with a .gitmodules pointing to remote URLs and ensure that
your command rewrites submodule paths to '.third-party/<owner>/<repo>'.
No network calls; we only check file transformations & git config.

Assumptions:
- The CLI entry point 'osh-sub-rewrite' accepts '--force' and '--dry-run' flags,
  and a '--commit/--no-commit' switch (default commit on).
- It uses GitPython under the hood but can operate on the filesystem with
  an existing .git and .gitmodules.

Adjust module/function names if they differ in your codebase.
"""

import subprocess
import textwrap
from pathlib import Path


def _run(cmd: list, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, check=False, capture_output=True, text=True)


def _init_git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q"], repo)
    # minimal identity
    _run(["git", "config", "user.email", "ci@example.com"], repo)
    _run(["git", "config", "user.name", "CI"], repo)
    # add a dummy file
    (repo / "README.md").write_text("# dummy\n")
    _run(["git", "add", "README.md"], repo)
    _run(["git", "commit", "-m", "init"], repo)
    return repo


def _write_gitmodules(repo: Path) -> None:
    """
    We emulate two submodules. Paths are deliberately 'addons/<name>' to test rewrite.
    """
    content = textwrap.dedent(
        """
        [submodule "server-ux"]
            path = addons/server-ux
            url = https://github.com/OCA/server-ux.git
            branch = 17.0
        [submodule "hr-holidays"]
            path = addons/hr-holidays
            url = git@github.com:odoo/odoo.git
            branch = 17.0
        """
    ).lstrip()
    (repo / ".gitmodules").write_text(content)
    _run(["git", "add", ".gitmodules"], repo)
    _run(["git", "commit", "-m", "add .gitmodules"], repo)


def test_sub_rewrite_rewrites_paths(tmp_path: Path):
    repo = _init_git_repo(tmp_path)
    _write_gitmodules(repo)

    # Dry-run first (should not commit changes)
    pr = _run(["osh-sub-rewrite", "--dry-run", "--force"], repo)
    assert pr.returncode == 0, pr.stderr

    # Now actual rewrite (with commit)
    pr = _run(["osh-sub-rewrite", "--force"], repo)
    assert pr.returncode == 0, pr.stderr

    # Verify .gitmodules paths were rewritten
    data = (repo / ".gitmodules").read_text()
    assert "path = .third-party/OCA/server-ux" in data
    assert "path = .third-party/odoo/odoo" in data

    # Optional: ensure a commit was created
    log = _run(["git", "log", "-1", "--pretty=%s"], repo).stdout.strip()
    assert "chore: rewrite submodule paths based on remote URL" in log
