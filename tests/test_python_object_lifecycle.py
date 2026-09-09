from pathlib import Path

from otter_kr.python_object_lifecycle import find_object_lifecycle


class SingleFileSource:
    def __init__(self, path: Path) -> None:
        self.path = path

    def python_files(self, repository: Path) -> list[Path]:
        return [self.path]


def test_reports_construction_and_field_operations(tmp_path: Path) -> None:
    source = tmp_path / "pkg.py"
    source.write_text(
        """
class Order:
    pass

order = Order()
order.total = 1
value = order.total
del order.total
order.items.append(value)
""",
        encoding="utf-8",
    )

    report = find_object_lifecycle(tmp_path, "order", file_source=SingleFileSource(source))

    assert report.to_dict() == {
        "language": "python",
        "carrier": "order",
        "files_scanned": 1,
        "constructions": [
            {
                "carrier": "order",
                "path": "pkg.py",
                "line": 5,
                "column": 0,
                "scope": "",
                "kind": "assignment",
                "expression": "Order()",
            }
        ],
        "operations": [
            {
                "carrier": "order",
                "field": "total",
                "path": "pkg.py",
                "line": 6,
                "column": 0,
                "scope": "",
                "kind": "field_write",
                "expression": "order.total",
                "guards": [],
            },
            {
                "carrier": "order",
                "field": "total",
                "path": "pkg.py",
                "line": 7,
                "column": 8,
                "scope": "",
                "kind": "field_read",
                "expression": "order.total",
                "guards": [],
            },
            {
                "carrier": "order",
                "field": "total",
                "path": "pkg.py",
                "line": 8,
                "column": 4,
                "scope": "",
                "kind": "field_delete",
                "expression": "order.total",
                "guards": [],
            },
            {
                "carrier": "order",
                "field": "items",
                "path": "pkg.py",
                "line": 9,
                "column": 0,
                "scope": "",
                "kind": "mutative_call",
                "expression": "order.items",
                "guards": [],
            },
        ],
        "operation_groups": [
            {
                "field": "items",
                "kind": "mutative_call",
                "occurrence_count": 1,
                "occurrence_refs": [{"path": "pkg.py", "line": 9, "column": 0}],
            },
            {
                "field": "total",
                "kind": "field_delete",
                "occurrence_count": 1,
                "occurrence_refs": [{"path": "pkg.py", "line": 8, "column": 4}],
            },
            {
                "field": "total",
                "kind": "field_read",
                "occurrence_count": 1,
                "occurrence_refs": [{"path": "pkg.py", "line": 7, "column": 8}],
            },
            {
                "field": "total",
                "kind": "field_write",
                "occurrence_count": 1,
                "occurrence_refs": [{"path": "pkg.py", "line": 6, "column": 0}],
            },
        ],
        "transitions": [
            {
                "path": "pkg.py",
                "scope": "",
                "field": "total",
                "from_kind": "field_write",
                "to_kind": "field_read",
                "from_line": 6,
                "to_line": 7,
            },
            {
                "path": "pkg.py",
                "scope": "",
                "field": "total",
                "from_kind": "field_read",
                "to_kind": "field_delete",
                "from_line": 7,
                "to_line": 8,
            },
        ],
        "parse_failures": [],
    }


def test_rejects_non_identifier_carrier(tmp_path: Path) -> None:
    try:
        find_object_lifecycle(tmp_path, "order.total")
    except ValueError as error:
        assert str(error) == "Carrier must be a Python identifier"
    else:
        raise AssertionError("expected invalid carrier to be rejected")


def test_attaches_guard_context_to_field_operation(tmp_path: Path) -> None:
    source = tmp_path / "pkg.py"
    source.write_text(
        """
def update(order):
    if order.ready:
        order.total = 1
""",
        encoding="utf-8",
    )

    report = find_object_lifecycle(tmp_path, "order", file_source=SingleFileSource(source))

    operation = report.operations[-1]
    assert operation.kind == "field_write"
    assert operation.guards[0].to_dict() == {
        "path": "pkg.py",
        "kind": "if",
        "line": 3,
        "column": 7,
        "expression": "order.ready",
        "branch": "body",
        "depth": 1,
    }
