import os
import zipfile
from datetime import datetime, timezone

import requests

from osh.compat import Optional, Tuple
from osh.net import make_json_get
from osh.settings import GITHUB_API


def _get_headers(token: Optional[str]) -> dict:
    """Return the headers to use for GitHub API requests."""

    res = {"Accept": "application/vnd.github+json"}
    if token:
        res["Authorization"] = f"token {token}"
    return res


def _get_api_url(owner: str, repo: str, endpoint: str) -> str:
    """Return the full GitHub API URL for this owner/repo/endpoint."""

    return f"{GITHUB_API}/repos/{owner}/{repo}/{endpoint}"


def fetch_branch_zip(  # noqa: PLR0913
    owner: str,
    repo: str,
    branch: str,
    out_dir: str,
    token: Optional[str] = None,
    extract: bool = True,
) -> Tuple[str, Optional[str]]:
    """
    Download the latest zipball of `owner/repo`'s `branch`.
    Returns (zip_path, extracted_root_or_None).
    """
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, f"{repo}-{branch}.zip")

    with requests.get(
        _get_api_url(owner, repo, f"zipball/{branch}"),
        headers=_get_headers(token),
        stream=True,
    ) as r:
        r.raise_for_status()
        with open(zip_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

    if not extract:
        return zip_path, None

    with zipfile.ZipFile(zip_path) as zf:
        # GitHub zipballs have a single top-level folder like "<repo>-<sha>/"
        top = zf.namelist()[0].split("/")[0] + "/"
        zf.extractall(out_dir)
    extracted_root = os.path.join(out_dir, top.rstrip("/"))
    return zip_path, extracted_root


def get_latest_workflow_run(
    owner: str, repo: str, token: str, branch: Optional[str] = None
) -> dict:  # pragma: no cover
    """Fetch the latest GitHub Actions workflow run for this repo."""

    params = {"per_page": "1"}
    if branch:
        params["branch"] = branch

    r = make_json_get(
        _get_api_url(owner, repo, "actions/runs"),
        headers=_get_headers(token),
        params=params,
    )

    run = r["workflow_runs"][0]

    # ISO8601 -> datetime (handles trailing 'Z')
    created = datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")).astimezone(
        timezone.utc
    )

    return {
        "workflow": run["name"],
        "event": run["event"],
        "status": run["status"],
        "conclusion": run["conclusion"],
        "sha": run["head_sha"][:7],
        "created_at": created,
        "age": (datetime.now(timezone.utc) - created).days,
        "url": run["html_url"],
    }
