import logging
import os
import re
import subprocess
from urllib.parse import urlparse

from osh.compat import Any, Optional, Tuple, Union
from osh.exceptions import ScriptNotFound


def get_exec_dir():
    return os.path.dirname(__file__)


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

    def extract_data(parts: list) -> tuple:
        owner, repo = parts[0], parts[1]
        repo = repo.removesuffix(".git")
        canonical = f"https://{host}/{owner}/{repo}"

        if owner == "oca":
            owner = owner.upper()

        return canonical, owner, repo

    def get_host_and_path(url):
        # 1) SCP-like SSH form: git@host:owner/repo(.git)?
        m = re.match(r"^(?P<user>[^@]+)@(?P<host>[^:]+):(?P<path>.+)$", url)
        if m:
            host = m.group("host")
            path = m.group("path").lstrip("/")

            return host, path

        # 2) URL-like forms (https, http, ssh, git+ssh)
        parsed = urlparse(url)
        scheme = (parsed.scheme or "").lower()

        if scheme in ("ssh", "git+ssh"):
            host = parsed.hostname or ""
            path = (parsed.path or "").lstrip("/")

            return host, path

        if scheme in ("http", "https", ""):
            # Strip possible credentials from netloc (user:pass@host)
            netloc = parsed.netloc or ""
            host = netloc.split("@")[-1] if netloc else ""
            path = (parsed.path or "").lstrip("/")

            return host, path

        raise ValueError(f"Unsupported URL scheme in: {url}")

    host, path = get_host_and_path(url)
    parts = path.split("/")

    if len(parts) < 2:
        raise ValueError(f"Malformed url (missing owner/repo): {url}")
    return extract_data(parts)


def human_readable(raw: Any, sep: str = ", ") -> str:
    if isinstance(raw, bool):
        return "yes" if raw else "no"
    if isinstance(raw, (list, tuple, set)):
        return sep.join(map(str, raw))
    return str(raw)


def str_to_list(raw: str, sep=",") -> list:
    if not raw:
        return []
    return [item.strip().rstrip() for item in raw.split(sep)]


def clean_string(raw: Any):
    raw.strip().rstrip() if raw else ""


def run(
    cmd: list,
    check: bool = True,
    capture: bool = False,
    cwd: Optional[str] = None,
    name: Optional[str] = None,
) -> Union[str, None]:
    kwargs: dict = dict(text=True, cwd=cwd)
    if capture:
        # assign explicitly to avoid static type checkers inferring incompatible dict value types
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE

    logging.debug(f"[{name or 'run'}] {' '.join(cmd)}")

    res = subprocess.run(cmd, check=check, **kwargs)
    return res.stdout if capture else None


def run_script(filepath: str, *args: str) -> str:
    """Run a shell script and return its output as a string."""

    path = os.path.join(get_exec_dir(), filepath)
    logging.debug(f"[script] Running script from {path}")

    if not os.path.exists(path):
        raise ScriptNotFound()

    result = subprocess.run([path, *args], capture_output=True, text=True, check=True)
    return result.stdout


def deep_visit(obj, prefix=""):
    """
    Yield flattened (path, value) pairs for recursive inspection.
    Example: 'assets.web.assets_backend[0]' -> '/module/static/...'
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k)
            yield from deep_visit(v, f"{prefix}.{key}" if prefix else key)
    elif isinstance(obj, (list, tuple)):
        for i, v in enumerate(obj):
            yield from deep_visit(v, f"{prefix}[{i}]")
    else:
        yield prefix, obj
