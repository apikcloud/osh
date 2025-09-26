import os
import re
import subprocess
from urllib.parse import urlparse

from tools.compat import Any, Tuple


def get_exec_dir():
    return os.path.dirname(__file__)


def run_script(script_path: str, *args: str) -> str:
    """Run a shell script and return its output as a string."""

    path = os.path.join(get_exec_dir(), script_path)

    result = subprocess.run([path, *args], capture_output=True, text=True, check=True)
    return result.stdout


def clean_url(url):
    """Removes credentials from a URL if present and replaces http with https."""
    # Regex to match URLs with credentials
    pattern = re.compile(r"(https?://|http://)([^@]+@)?(.+)")

    # Substitute the matched pattern to remove credentials and ensure https
    cleaned_url = pattern.sub(lambda m: f"https://{m.group(3)}", url)  # noqa: E231

    return cleaned_url


def parse_repository_url(url: str) -> Tuple[str, str, str]:
    """
    Parse any GitHub URL (HTTPS or SSH) and return:
    (canonical_https_repo_url, owner, repo)

    Supported examples:
      - https://github.com/odoo/odoo
      - https://github.com/odoo/odoo.git
      - http://github.com/odoo/odoo/tree/19.0
      - ssh://git@github.com/odoo/odoo.git
      - git@github.com:odoo/odoo.git
      - git@github.mycorp.local:team/project.git  (GH Enterprise)

    Returns:
      ("https://<host>/<owner>/<repo>", owner, repo)

    Raises:
      ValueError if the URL cannot be parsed into owner/repo.
    """
    url = url.strip()

    # 1) SCP-like SSH form: git@host:owner/repo(.git)?
    m = re.match(r"^(?P<user>[^@]+)@(?P<host>[^:]+):(?P<path>.+)$", url)
    if m:
        host = m.group("host")
        path = m.group("path").lstrip("/")
        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Malformed GitHub SSH URL (missing owner/repo): {url}")
        owner, repo = parts[0], parts[1]
        repo = repo.removesuffix(".git")
        canonical = f"https://{host}/{owner}/{repo}"
        return canonical, owner, repo

    # 2) URL-like forms (https, http, ssh, git+ssh)
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    if scheme in ("ssh", "git+ssh"):
        host = parsed.hostname or ""
        path = (parsed.path or "").lstrip("/")
        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Malformed SSH URL (missing owner/repo): {url}")
        owner, repo = parts[0], parts[1]
        repo = repo.removesuffix(".git")
        canonical = f"https://{host}/{owner}/{repo}"
        return canonical, owner, repo

    if scheme in ("http", "https", ""):
        # Strip possible credentials from netloc (user:pass@host)
        netloc = parsed.netloc or ""
        host = netloc.split("@")[-1] if netloc else ""
        path = (parsed.path or "").lstrip("/")
        parts = path.split("/")
        if len(parts) < 2:
            raise ValueError(f"Malformed HTTPS URL (missing owner/repo): {url}")
        owner, repo = parts[0], parts[1]
        repo = repo.removesuffix(".git")
        canonical = f"https://{host}/{owner}/{repo}"
        return canonical, owner, repo

    raise ValueError(f"Unsupported URL scheme in: {url}")


def human_readable(raw: Any) -> str:
    if isinstance(raw, bool):
        return "yes" if raw else "no"
    return str(raw)
