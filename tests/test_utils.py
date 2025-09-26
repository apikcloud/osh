from tools.utils import human_readable, parse_repository_url, str_to_list

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
        ["one,two,three", ["one", "two", "three"]],
    ]
    for line in data:
        assert str_to_list(line[0]) == line[1]
