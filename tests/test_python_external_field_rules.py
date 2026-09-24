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
        "test_evidence": [],
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


def test_reports_repeated_direct_calculation_rules(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Order:\n"
        "    total: int\n"
        "\n"
        "def adjusted(order: Order):\n"
        "    return order.total * 2\n"
        "\n"
        "def projected(order: Order):\n"
        "    return order.total * 2\n",
    )
    git_repository(tmp_path, "orders.py")

    report = find_external_field_rules(tmp_path, "Order")

    assert report.to_dict()["rules"] == [
        {
            "kind": "calculation",
            "normalized": {"field": "total", "operator": "*", "operand": "2"},
            "occurrence_count": 2,
            "functions": ["adjusted", "projected"],
            "occurrence_refs": [
                {
                    "path": "orders.py",
                    "line": 5,
                    "column": 11,
                    "function": "adjusted",
                    "expression": "order.total * 2",
                },
                {
                    "path": "orders.py",
                    "line": 8,
                    "column": 11,
                    "function": "projected",
                    "expression": "order.total * 2",
                },
            ],
        }
    ]


def test_reports_repeated_direct_field_call_rules(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Order:\n"
        "    status: str\n"
        "\n"
        "def clean(order: Order):\n"
        "    return order.status.strip()\n"
        "\n"
        "def display(order: Order):\n"
        "    return order.status.strip()\n",
    )
    git_repository(tmp_path, "orders.py")

    report = find_external_field_rules(tmp_path, "Order")

    assert report.to_dict()["rules"] == [
        {
            "kind": "call",
            "normalized": {"field": "status", "method": "strip", "arguments": ""},
            "occurrence_count": 2,
            "functions": ["clean", "display"],
            "occurrence_refs": [
                {
                    "path": "orders.py",
                    "line": 5,
                    "column": 11,
                    "function": "clean",
                    "expression": "order.status.strip()",
                },
                {
                    "path": "orders.py",
                    "line": 8,
                    "column": 11,
                    "function": "display",
                    "expression": "order.status.strip()",
                },
            ],
        }
    ]


def test_reports_repeated_direct_field_calls_with_one_positional_argument(
    tmp_path: Path,
) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Order:\n"
        "    status: str\n"
        "\n"
        "def clean(order: Order):\n"
        "    return order.status.startswith('open')\n"
        "\n"
        "def display(order: Order):\n"
        "    return order.status.startswith('open')\n",
    )
    git_repository(tmp_path, "orders.py")

    report = find_external_field_rules(tmp_path, "Order")

    assert report.to_dict()["rules"] == [
        {
            "kind": "call",
            "normalized": {
                "field": "status",
                "method": "startswith",
                "arguments": "'open'",
            },
            "occurrence_count": 2,
            "functions": ["clean", "display"],
            "occurrence_refs": [
                {
                    "path": "orders.py",
                    "line": 5,
                    "column": 11,
                    "function": "clean",
                    "expression": "order.status.startswith('open')",
                },
                {
                    "path": "orders.py",
                    "line": 8,
                    "column": 11,
                    "function": "display",
                    "expression": "order.status.startswith('open')",
                },
            ],
        }
    ]


def test_reports_repeated_direct_field_format_rules(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Order:\n"
        "    status: str\n"
        "\n"
        "def label(order: Order):\n"
        "    return f'status={order.status}'\n"
        "\n"
        "def describe(order: Order):\n"
        "    return f'status={order.status}'\n",
    )
    git_repository(tmp_path, "orders.py")

    report = find_external_field_rules(tmp_path, "Order")

    assert report.to_dict()["rules"] == [
        {
            "kind": "format",
            "normalized": {"field": "status", "format": "f-string"},
            "occurrence_count": 2,
            "functions": ["describe", "label"],
            "occurrence_refs": [
                {
                    "path": "orders.py",
                    "line": 5,
                    "column": 11,
                    "function": "label",
                    "expression": "f'status={order.status}'",
                },
                {
                    "path": "orders.py",
                    "line": 8,
                    "column": 11,
                    "function": "describe",
                    "expression": "f'status={order.status}'",
                },
            ],
        }
    ]


def test_links_test_evidence_for_observed_external_functions(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "orders.py",
        "class Order:\n    status: str\n\ndef close(order: Order):\n    return order.status\n",
    )
    write_python(
        tmp_path,
        "tests/test_orders.py",
        "from orders import close\n\ndef test_close():\n    close(None)\n",
    )
    git_repository(tmp_path, "orders.py", "tests")

    report = find_external_field_rules(tmp_path, "Order")

    assert report.to_dict()["test_evidence"][0]["function"] == "close"
    assert report.to_dict()["test_evidence"][0]["report"]["mapping_status"] == "matched"
