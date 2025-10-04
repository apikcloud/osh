import requests

from osh.compat import Optional
from osh.settings import DEFAULT_TIMEOUT


def make_json_get(url: str, headers: Optional[dict] = None, params: Optional[dict] = None) -> dict:
    """Make a GET request and return the JSON response."""

    options = {}
    if headers:
        options["headers"] = headers
    if params:
        options["params"] = params

    r = requests.get(
        url,
        **options,
        timeout=DEFAULT_TIMEOUT,
    )
    r.raise_for_status()

    return r.json()
