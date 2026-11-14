import ast
from pathlib import Path

import pytest

from otter_kr.python_structural_complexity import (
    UnsupportedStructuralSyntax,
    analyze_python_structural_complexity,
    count_operands,
    count_operations,
    count_paths,
)
from tests.support import git_repository, write_python


def test_reports_structural_paths_for_tracked_functions(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "paths.py",
        "def direct():\n    return 1\n\n"
        "def choose(flag):\n    if flag:\n        return 1\n    return 0\n\n"
        "def sequential(xs, ys):\n    for x in xs:\n        pass\n"
        "    for y in ys:\n        pass\n\n"
        "def nested(rows):\n    for row in rows:\n        for value in row:\n            pass\n",
    )
    git_repository(tmp_path, "paths.py")

    report = analyze_python_structural_complexity(tmp_path, "paths")

    assert [(row.qualified_name, row.count) for row in report.functions] == [
        ("direct", 1),
        ("choose", 2),
        ("sequential", 3),
        ("nested", 4),
    ]


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ("if a:\n        pass\n    if b:\n        pass", 3),
        ("if a:\n        return 1\n    for x in xs:\n        pass", 3),
        ("if a:\n        return 1\n    else:\n        return 2\n    for x in xs:\n        pass", 2),
        ("for x in xs:\n        return x\n    if a:\n        pass", 3),
        ("for x in xs:\n        if a:\n            pass", 4),
        ("while a:\n        pass", 2),
        ("for x in [y for y in ys]:\n        pass", 2),
        ("for x in xs:\n        for y in ys:\n            for z in zs:\n                pass", 8),
        ("first = [x for x in xs]\n    second = [y for y in ys]", 1),
        ("return [y for x in xs for y in ys]", 1),
        ("return [[y for y in ys] for x in xs]", 1),
        ("return build(items=[x for x in xs])", 1),
        ("return {x: x if a else 0 for x in xs if x}", 1),
        ("if [x for x in xs if x]:\n        return 1\n    return 0", 2),
        ("while [x for x in xs]:\n        pass", 2),
        ("if a and b or c:\n        return 1\n    return 0", 2),
    ],
)
def test_paths_compose_choices_loops_and_comprehensions(body: str, expected: int) -> None:
    function = ast.parse(f"def inspect(a, b, c, xs, ys, zs):\n    {body}\n").body[0]
    assert isinstance(function, ast.FunctionDef)
    assert count_paths(function) == expected


@pytest.mark.parametrize(
    "body",
    [
        "return 1 if a else 0",
        "return build(item=1 if a else 0)",
        "for x in xs:\n        break",
        "for items[0] in xs:\n        pass",
        "for x in xs:\n        pass\n    else:\n        pass",
        "raise ValueError()",
        "try:\n        pass\n    except Exception:\n        pass",
    ],
)
def test_paths_report_unmodeled_control_flow(body: str) -> None:
    function = ast.parse(f"def inspect(a, xs):\n    {body}\n").body[0]
    assert isinstance(function, ast.FunctionDef)
    with pytest.raises(UnsupportedStructuralSyntax):
        count_paths(function)


def test_counts_distinct_parameters_body_names_and_typed_literals() -> None:
    function = ast.parse(
        """def inspect(pos, /, ordinary, *extras, keyword_only, **options):
    pos = ordinary
    return ordinary, True, 1
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operands(function) == 7


def test_measures_operation_occurrences_in_tracked_functions(tmp_path: Path) -> None:
    write_python(
        tmp_path, "app.py", "def inspect(value):\n    result = value + 1\n    return result\n"
    )
    git_repository(tmp_path, "app.py")

    report = analyze_python_structural_complexity(tmp_path, "operations")

    assert [(item.qualified_name, item.count) for item in report.functions] == [("inspect", 2)]


def test_counts_assignment_variants_arithmetic_and_target_lookups() -> None:
    function = ast.parse(
        """def update(value, other, items):
    value += other
    value: int
    value: int = other
    items[0] = value
    value = (other := items[1])
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operations(function) == 8


def test_counts_boolean_comparison_and_unary_operators_by_occurrence() -> None:
    function = ast.parse(
        """def check(a, b, c, x, y, z):
    return a and b and c, x < y <= z, -x, not y
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operations(function) == 7


@pytest.mark.parametrize(
    ("expression", "expected"),
    [
        ("outer(inner(value))", 2),
        ("value.first.second", 2),
        ("values[0]", 1),
        ("[left, right]", 1),
        ("(left, right)", 1),
        ("{value}", 1),
        ("{key: value}", 1),
        ("{**values}", 1),
        ("{**load(values), key: values[0]}", 3),
        ("tuple((1, 2))", 2),
        ("list(values)", 1),
    ],
)
def test_counts_calls_lookup_hops_and_collection_construction(
    expression: str, expected: int
) -> None:
    function = ast.parse(f"def build(values):\n    return {expression}\n").body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operations(function) == expected


def test_destructuring_does_not_count_tuple_construction() -> None:
    function = ast.parse("def unpack(values):\n    left, right = values\n").body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operations(function) == 1


def test_empty_function_has_zero_operations_and_nested_bodies_are_separate(
    tmp_path: Path,
) -> None:
    write_python(
        tmp_path,
        "app.py",
        'def outer():\n    "outer docs"\n    value = 1\n'
        "    def inner():\n        value + 2\n"
        "    class Nested:\n        def method(self):\n            return 3\n"
        "    return value\n\n"
        "def empty():\n    pass\n",
    )
    git_repository(tmp_path, "app.py")

    report = analyze_python_structural_complexity(tmp_path, "operations")

    assert [(item.qualified_name, item.count) for item in report.functions] == [
        ("outer", 1),
        ("outer.inner", 1),
        ("outer.Nested.method", 0),
        ("empty", 0),
    ]


@pytest.mark.parametrize(
    "expression",
    [
        "[transform(value) for value in values if value]",
        "{value for value in values}",
        "{value: value if flag else 0 for value in values}",
        "(value for value in values)",
        "[value async for value in values if value]",
    ],
)
def test_counts_comprehension_as_one_operation_and_continuation(expression: str) -> None:
    function = ast.parse(f"async def inspect(values, flag):\n    result = {expression}\n").body[0]

    assert isinstance(function, ast.AsyncFunctionDef)
    assert count_operations(function) == 2
    assert count_paths(function) == 1


def test_counts_maximal_attribute_chains_without_implicit_prefixes() -> None:
    function = ast.parse(
        """def inspect():
    return x.a, x.b, x.c.d, x, x.c
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operands(function) == 5


def test_excludes_signature_and_docstring_and_measures_nested_functions_separately(
    tmp_path: Path,
) -> None:
    write_python(
        tmp_path,
        "app.py",
        "def outer(arg: annotation = default):\n"
        '    "documentation literal"\n'
        "    local = 3\n"
        "    def inner():\n"
        '        return local, "inner literal"\n'
        "    return local\n",
    )
    git_repository(tmp_path, "app.py")

    report = analyze_python_structural_complexity(tmp_path, "operands")

    assert [(item.qualified_name, item.count) for item in report.functions] == [
        ("outer", 3),
        ("outer.inner", 2),
    ]
    assert report.warnings == ()


def test_lambda_makes_function_count_explicitly_unsupported() -> None:
    function = ast.parse("def apply():\n    return lambda value: value\n").body[0]

    assert isinstance(function, ast.FunctionDef)
    with pytest.raises(UnsupportedStructuralSyntax, match="Lambda expressions are unsupported"):
        count_operands(function)


def test_import_and_pattern_bindings_are_names() -> None:
    function = ast.parse(
        """def bind(value):
    import package.module as loaded
    match value:
        case {"item": captured, **remaining}:
            pass
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operands(function) == 5


def test_dynamic_attribute_chain_is_explicitly_unsupported() -> None:
    function = ast.parse("def read(values):\n    return values[0].field\n").body[0]

    assert isinstance(function, ast.FunctionDef)
    with pytest.raises(UnsupportedStructuralSyntax, match="Dynamic attribute chains"):
        count_operands(function)


def test_report_omits_counts_for_unsupported_functions_and_retains_other_rows(
    tmp_path: Path,
) -> None:
    write_python(
        tmp_path,
        "tracked.py",
        "def supported(value):\n    return value, 1\n\n"
        "def unsupported(value):\n    return lambda item: item\n",
    )
    write_python(tmp_path, "broken.py", "def broken(:\n")
    write_python(tmp_path, "untracked.py", "def ignored():\n    return 99\n")
    git_repository(tmp_path, "tracked.py", "broken.py")

    report = analyze_python_structural_complexity(tmp_path, "operands")

    assert [row.qualified_name for row in report.functions] == ["supported", "unsupported"]
    assert report.functions[0].count == 2
    assert report.functions[1].to_dict() == {
        "path": "tracked.py",
        "qualified_name": "unsupported",
        "kind": "function",
        "line": 4,
        "column": 0,
        "end_line": 5,
        "diagnostic": "Lambda expressions are unsupported in operand measurements.",
    }
    assert [warning["path"] for warning in report.warnings] == ["broken.py"]
