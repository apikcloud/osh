from dataclasses import asdict
from datetime import date

from osh.odoo import parse_image_tag

data = [
    {
        "inputs": "loginline/odoo:15-20230103-enterprise-legacy",
        "results": {
            "registry": "loginline",
            "repository": "odoo",
            "major_version": 15.0,
            "release": date(2023, 1, 3),
            "enterprise": True,
            "legacy": True,
        },
    },
    {
        "inputs": "odoo:19.0-20250918",
        "results": {
            "registry": "odoo",
            "repository": "odoo",
            "major_version": 19.0,
            "release": date(2025, 9, 18),
            "enterprise": False,
            "legacy": False,
        },
    },
    {
        "inputs": "odoo:19",
        "results": {
            "registry": "odoo",
            "repository": "odoo",
            "major_version": 19.0,
            "release": None,
            "enterprise": False,
            "legacy": False,
        },
    },
    {
        "inputs": "ofleet/odoo:18-20250915",
        "results": {
            "registry": "ofleet",
            "repository": "odoo",
            "major_version": 18.0,
            "release": date(2025, 9, 15),
            "enterprise": False,
            "legacy": False,
        },
    },
    {
        "inputs": "apik/odoo:19.0-20250919-enterprise",
        "results": {
            "registry": "apik",
            "repository": "odoo",
            "major_version": 19.0,
            "release": date(2025, 9, 19),
            "enterprise": True,
            "legacy": False,
        },
    },
]


def test_parse_image_tag():
    for line in data:
        res = parse_image_tag(line["inputs"])
        assert asdict(res) == line["results"]
