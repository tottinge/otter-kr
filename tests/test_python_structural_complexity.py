import ast
from pathlib import Path

import pytest

from otter_kr.python_structural_complexity import (
    UnsupportedStructuralSyntax,
    analyze_python_structural_complexity,
    count_operands,
)
from tests.support import git_repository, write_python


def test_counts_distinct_parameters_body_names_and_typed_literals() -> None:
    function = ast.parse(
        """def inspect(pos, /, ordinary, *extras, keyword_only, **options):
    pos = ordinary
    return ordinary, True, 1
"""
    ).body[0]

    assert isinstance(function, ast.FunctionDef)
    assert count_operands(function) == 7


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
