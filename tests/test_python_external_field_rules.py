from pathlib import Path

from otter_kr.python_external_field_rules import find_external_field_rules
from tests.support import git_repository, write_python


def test_reports_carrier_fields_and_repeated_external_field_affinity(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Order:\n"
        "    status: str\n"
        "    total: int\n"
        "\n"
        "def close(order: Order):\n"
        "    if order.status == 'open':\n"
        "        order.status = 'closed'\n"
        "        return order.total\n"
        "\n"
        "def summarize(order: Order):\n"
        "    return f'{order.status}:{order.total}'\n"
        "\n"
        "class OrderView:\n"
        "    def render(self, order: Order):\n"
        "        return (order.status, order.total)\n",
    )
    git_repository(tmp_path, "orders.py")

    report = find_external_field_rules(tmp_path, "Order")
    assert report.to_dict() == {
        "language": "python",
        "carrier": "Order",
        "declarations": [
            {
                "path": "orders.py",
                "line": 1,
                "column": 0,
                "kind": "class",
                "fields": [
                    {"name": "status", "line": 2, "column": 4},
                    {"name": "total", "line": 3, "column": 4},
                ],
            }
        ],
        "affinities": [
            {
                "fields": ["status", "total"],
                "function_count": 3,
                "functions": ["OrderView.render", "close", "summarize"],
                "occurrence_count": 7,
                "role_counts": {"read": 6, "write": 1},
                "occurrence_refs": [
                    {
                        "path": "orders.py",
                        "line": 6,
                        "column": 7,
                        "function": "close",
                        "field": "status",
                        "role": "read",
                    },
                    {
                        "path": "orders.py",
                        "line": 7,
                        "column": 8,
                        "function": "close",
                        "field": "status",
                        "role": "write",
                    },
                    {
                        "path": "orders.py",
                        "line": 8,
                        "column": 15,
                        "function": "close",
                        "field": "total",
                        "role": "read",
                    },
                    {
                        "path": "orders.py",
                        "line": 11,
                        "column": 14,
                        "function": "summarize",
                        "field": "status",
                        "role": "read",
                    },
                    {
                        "path": "orders.py",
                        "line": 11,
                        "column": 29,
                        "function": "summarize",
                        "field": "total",
                        "role": "read",
                    },
                    {
                        "path": "orders.py",
                        "line": 15,
                        "column": 16,
                        "function": "OrderView.render",
                        "field": "status",
                        "role": "read",
                    },
                    {
                        "path": "orders.py",
                        "line": 15,
                        "column": 30,
                        "function": "OrderView.render",
                        "field": "total",
                        "role": "read",
                    },
                ],
            }
        ],
        "warnings": [],
        "rules": [],
    }


def test_reports_dataclass_and_excludes_carrier_methods_and_untyped_access(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "from dataclasses import dataclass\n"
        "\n"
        "@dataclass\n"
        "class Order:\n"
        "    status: str\n"
        "    total: int\n"
        "\n"
        "    def own_rule(self):\n"
        "        return self.status\n"
        "\n"
        "def one(order: Order):\n"
        "    return order.status\n"
        "\n"
        "def unknown(order):\n"
        "    return order.status, order.total\n",
    )
    git_repository(tmp_path, "orders.py")

    report = find_external_field_rules(tmp_path, "Order")

    assert report.declarations[0].kind == "dataclass"
    assert report.affinities == ()
    assert report.warnings == ()


def test_reports_repeated_direct_comparison_rules(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Order:\n"
        "    status: str\n"
        "    total: int\n"
        "\n"
        "def close(order: Order):\n"
        "    if order.status == 'open':\n"
        "        return order.total\n"
        "\n"
        "def reopen(order: Order):\n"
        "    if order.status == 'open':\n"
        "        return order.total\n",
    )
    git_repository(tmp_path, "orders.py")

    report = find_external_field_rules(tmp_path, "Order")

    assert report.to_dict()["rules"] == [
        {
            "kind": "comparison",
            "normalized": {"field": "status", "operator": "==", "value": "'open'"},
            "occurrence_count": 2,
            "functions": ["close", "reopen"],
            "occurrence_refs": [
                {
                    "path": "orders.py",
                    "line": 6,
                    "column": 7,
                    "function": "close",
                    "expression": "order.status == 'open'",
                },
                {
                    "path": "orders.py",
                    "line": 10,
                    "column": 7,
                    "function": "reopen",
                    "expression": "order.status == 'open'",
                },
            ],
        }
    ]
