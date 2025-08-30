# ruff: noqa: E501

from datetime import date
from pathlib import Path

import pytest

from osh.utils import (
    clean_string,
    date_from_string,
    human_readable,
    parse_repository_url,
    read_and_parse,
    removesuffix,
    str_to_list,
)

data = [
    {
        "inputs": "https://github.com/oca/stock-logistics-workflow.git",
        "results": [
            "https://github.com/oca/stock-logistics-workflow",
            "OCA",
            "stock-logistics-workflow",
        ],
    },
    {
        "inputs": "https://github.com/oca/bank-statement-import.git",
        "results": [
            "https://github.com/oca/bank-statement-import",
            "OCA",
            "bank-statement-import",
        ],
    },
    {
        "inputs": "https://github.com/akretion/bank-statement-reconcile-simple.git",
        "results": [
            "https://github.com/akretion/bank-statement-reconcile-simple",
            "akretion",
            "bank-statement-reconcile-simple",
        ],
    },
    {
        "inputs": "ssh://git@github.com/odoo/odoo.git",
        "results": [
            "https://github.com/odoo/odoo",
            "odoo",
            "odoo",
        ],
    },
    {
        "inputs": "git@github.com:odoo/odoo.git",
        "results": [
            "https://github.com/odoo/odoo",
            "odoo",
            "odoo",
        ],
    },
    {
        "inputs": "https://x-access-token:00000000@github.com/odoo/enterprise.git",
        "results": [
            "https://github.com/odoo/enterprise",
            "odoo",
            "enterprise",
        ],
    },
    {
        "inputs": "https://user1:00000000@github.com/odoo/docker",
        "results": [
            "https://github.com/odoo/docker",
            "odoo",
            "docker",
        ],
    },
]


def test_parse_repository_url():
    for line in data:
        canonical, owner, repo = parse_repository_url(line["inputs"])
        assert [canonical, owner, repo] == line["results"]


def test_human_readable():
    data = [
        [True, "yes"],
        [False, "no"],
        [1, "1"],
        [0, "0"],
        [99, "99"],
        [[1, 2, 3], "1, 2, 3"],
        ["1... 2...", "1... 2..."],
    ]

    for line in data:
        assert human_readable(line[0]) == line[1]


def test_str_to_list():
    data = [
        [
            "Lorem,ipsum,dolor,sit,amet,",
            ["Lorem", "ipsum", "dolor", "sit", "amet"],
        ],
        [
            "1,2,3,4,5",
            ["1", "2", "3", "4", "5"],
        ],
    ]
    for line in data:
        assert str_to_list(line[0]) == line[1]


def test_date_from_string():
    assert date_from_string("20250115") == date(2025, 1, 15)

    with pytest.raises(
        ValueError, match="The string does not have the correct length to be converted to a date."
    ):
        assert date_from_string("0000") == date(2025, 1, 15)


def test_clean_string():
    data = [
        [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        ],
        [
            "  Lorem ipsum dolor sit amet, consectetur adipiscing elit. ",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
        ],
        [
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. \nNulla suscipit quam non odio accumsan pellentesque.\n",
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. \nNulla suscipit quam non odio accumsan pellentesque.",
        ],
        [None, ""],
    ]
    for item in data:
        assert clean_string(item[0]) == item[1]


def test_removesuffix():
    suffix = ".git"
    data = [
        [
            "https://github.com/oca/stock-logistics-workflow.git",
            "https://github.com/oca/stock-logistics-workflow",
        ],
        [
            "https://github.com/oca/stock-logistics-workflow",
            "https://github.com/oca/stock-logistics-workflow",
        ],
    ]

    for item in data:
        assert removesuffix(item[0], suffix=suffix) == item[1]


# def test_read_and_parse():
#     data = [
#         [
#             "apik/odoo:15-20230103-enterprise\n",
#             ["apik/odoo:15-20230103-enterprise"],
#         ],
#         [
#             "unidecode\nxlrd\nnumpy\ncryptography\nfintech\npython-stdnum>=1.16\nnumpy-financial<=1.0.0\nxlsxwriter\n\n",
#             [
#                 "cryptography",
#                 "fintech",
#                 "numpy-financial<=1.0.0",
#                 "numpy",
#                 "python-stdnum>=1.16",
#                 "unidecode",
#                 "xlrd",
#                 "xlsxwriter",
#             ],
#         ],
#         ["# packages.txt\n", []],
#     ]

#     for item in data:
#         assert read_and_parse(item[0]) == item[1]


@pytest.mark.parametrize(
    "content, expected",
    [
        ("apik/odoo:15-20230103-enterprise\n\n", ["apik/odoo:15-20230103-enterprise"]),
        (
            "unidecode\nxlrd\nnumpy\ncryptography\nfintech\npython-stdnum>=1.16\n"
            "numpy-financial<=1.0.0\nxlsxwriter\n\n",
            [
                "cryptography",
                "fintech",
                "numpy",
                "numpy-financial<=1.0.0",
                "python-stdnum>=1.16",
                "unidecode",
                "xlrd",
                "xlsxwriter",
            ],
        ),
        ("# packages.txt\n", []),
    ],
)
def test_read_and_parse(content, expected, monkeypatch):
    def fake_read_text(self):
        return content  # string content for this parametrized case

    monkeypatch.setattr(Path, "read_text", fake_read_text)
    assert read_and_parse(Path("whatever.txt")) == expected
