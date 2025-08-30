import os
import zipfile
from datetime import datetime, timezone

import requests

from osh.compat import Optional, Tuple
from osh.settings import GITHUB_API


def _headers(token: Optional[str]) -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if token:
        h["Authorization"] = f"token {token}"
    return h


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
    url = f"{GITHUB_API}/repos/{owner}/{repo}/zipball/{branch}"
    zip_path = os.path.join(out_dir, f"{repo}-{branch}.zip")

    with requests.get(
        url,
        headers=_headers(token),
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
    """Fetch and print the latest GitHub Actions workflow run for this repo."""

    params = {"per_page": "1"}
    if branch:
        params["branch"] = branch

    headers = {"Accept": "application/vnd.github+json", "Authorization": f"token {token}"}
    url = f"https://api.github.com/repos/{owner}/{repo}/actions/runs"

    r = requests.get(url, headers=headers, params=params, timeout=20)
    r.raise_for_status()

    run = r.json()["workflow_runs"][0]

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
