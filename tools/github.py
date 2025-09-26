import os
import zipfile

import requests

from tools.compat import Optional, Tuple
from tools.settings import GITHUB_API


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

    with requests.get(url, headers=_headers(token), stream=True, timeout=300) as r:
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
