import requests

from osh.settings import DEFAULT_TIMEOUT


def make_get(url):
    """Make GET request"""
    return requests.get(url, timeout=DEFAULT_TIMEOUT).json()
