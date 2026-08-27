from pathlib import Path

from otter_kr.python_tests import find_tests_for_symbol
from tests.support import (
    assert_invalid_python_warning,
    assert_unreadable_file_warning,
    git_repository,
    write_bytes,
    write_python,
)


class ReversedFileSource:
    def python_files(self, repository: Path) -> list[Path]:
        return [
            repository / "tests/test_b.py",
            repository / "tests/test_a.py",
            repository / "broken.py",
            repository / "bad_encoding.py",
        ]


def assert_evidence_matches_source(candidate, source: str) -> None:
    lines = source.splitlines()
    for evidence in candidate.evidence:
        line = lines[evidence.line - 1]
        assert evidence.expression in line
        assert line[evidence.column :].startswith(evidence.name)


def assert_import_matches_source(matching_import, source: str) -> None:
    lines = source.splitlines()
    line = lines[matching_import.line - 1]
    assert line[matching_import.column :].startswith(matching_import.imported_name)


def import_summary(matching_import) -> dict[str, object]:
    return {
        "path": matching_import.path,
        "module": matching_import.module,
        "relative_level": matching_import.relative_level,
        "imported_name": matching_import.imported_name,
        "local_name": matching_import.local_name,
    }


def evidence_summary(candidate) -> dict[str, str]:
    evidence = candidate.evidence[0]
    return {
        "kind": evidence.kind,
        "name": evidence.name,
        "expression": evidence.expression,
    }


def test_reports_direct_and_aliased_symbol_evidence_for_candidate_tests(tmp_path: Path) -> None:
    source = (
        "from app.service import collect_payment, collect_payment as pay\n\n"
        "def helper():\n"
        "    collect_payment()\n\n"
        "def test_direct_reference():\n"
        "    collect_payment()\n\n"
        "def test_alias_reference():\n"
        "    pay()\n\n"
        "def test_import_only_not_candidate():\n"
        "    assert True\n"
    )
    write_python(
        tmp_path,
        "tests/test_service.py",
        source,
    )
    git_repository(tmp_path, "tests")

    report = find_tests_for_symbol(tmp_path, "collect_payment")

    assert report.mapping_status == "matched"
    assert [item.qualified_name for item in report.candidates] == [
        "test_direct_reference",
        "test_alias_reference",
    ]
    assert [evidence_summary(item) for item in report.candidates] == [
        {
            "kind": "imported_name",
            "name": "collect_payment",
            "expression": "collect_payment()",
        },
        {
            "kind": "imported_alias",
            "name": "pay",
            "expression": "pay()",
        },
    ]
    assert [import_summary(item) for item in report.matching_imports] == [
        {
            "path": "tests/test_service.py",
            "module": "app.service",
            "relative_level": 0,
            "imported_name": "collect_payment",
            "local_name": "collect_payment",
        },
        {
            "path": "tests/test_service.py",
            "module": "app.service",
            "relative_level": 0,
            "imported_name": "collect_payment",
            "local_name": "pay",
        },
    ]
    for candidate in report.candidates:
        assert_evidence_matches_source(candidate, source)
    for matching_import in report.matching_imports:
        assert_import_matches_source(matching_import, source)


def test_reports_shadowed_import_name_truthfully(tmp_path: Path) -> None:
    source = (
        "from app.service import collect_payment\n\n"
        "def test_shadowed_parameter(collect_payment):\n"
        "    collect_payment()\n\n"
        "def test_shadowed_assignment():\n"
        "    collect_payment = build_fake()\n"
        "    collect_payment()\n"
    )
    write_python(tmp_path, "tests/test_shadowing.py", source)
    git_repository(tmp_path, "tests")

    report = find_tests_for_symbol(tmp_path, "collect_payment")

    assert report.mapping_status == "matched"
    assert [item.qualified_name for item in report.candidates] == [
        "test_shadowed_parameter",
        "test_shadowed_assignment",
    ]
    assert [evidence_summary(item) for item in report.candidates] == [
        {
            "kind": "shadowed_name",
            "name": "collect_payment",
            "expression": "collect_payment()",
        },
        {
            "kind": "shadowed_name",
            "name": "collect_payment",
            "expression": "collect_payment()",
        },
    ]
    for candidate in report.candidates:
        assert_evidence_matches_source(candidate, source)


def test_requires_exact_symbol_match_and_ignores_helpers(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "tests/test_symbols.py",
        (
            "from app.symbols import Symbol\n"
            "from app.factories import SymbolFactory\n\n"
            "def helper():\n"
            "    Symbol()\n\n"
            "def test_symbol_factory_only():\n"
            "    SymbolFactory()\n"
        ),
    )
    git_repository(tmp_path, "tests")

    report = find_tests_for_symbol(tmp_path, "Symbol")

    assert report.mapping_status == "no_mapping_found"
    assert report.candidates == ()


def test_sorts_deterministically_and_reports_parse_warnings(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "tests/test_a.py",
        ("from app.service import collect_payment\n\ndef test_alpha():\n    collect_payment()\n"),
    )
    write_python(
        tmp_path,
        "tests/test_b.py",
        ("from app.service import collect_payment as pay\n\ndef test_beta():\n    pay()\n"),
    )
    write_python(tmp_path, "broken.py", "def nope(:\n")
    write_bytes(tmp_path, "bad_encoding.py", b"\xff\n")
    git_repository(tmp_path, "tests", "broken.py", "bad_encoding.py")

    report = find_tests_for_symbol(tmp_path, "collect_payment", file_source=ReversedFileSource())

    assert [item.path for item in report.candidates] == ["tests/test_a.py", "tests/test_b.py"]
    assert [item.qualified_name for item in report.candidates] == ["test_alpha", "test_beta"]
    warnings = list(report.warnings)
    assert_unreadable_file_warning(warnings[0], "bad_encoding.py")
    assert_invalid_python_warning(warnings[1], "broken.py")


def test_reports_no_mapping_found_for_selected_symbol(tmp_path: Path) -> None:
    write_python(tmp_path, "tests/test_service.py", "def test_other():\n    assert True\n")
    git_repository(tmp_path, "tests")

    report = find_tests_for_symbol(tmp_path, "collect_payment")

    assert report.mapping_status == "no_mapping_found"
    assert report.candidates == ()
    assert report.matching_imports == ()
    assert report.warnings == ()


def test_reports_matching_imports_without_promoting_import_only_tests_to_candidates(
    tmp_path: Path,
) -> None:
    source = (
        "from app.service import collect_payment\n\n"
        "def helper():\n"
        "    return collect_payment\n\n"
        "def test_import_only():\n"
        "    assert True\n"
    )
    write_python(tmp_path, "tests/test_import_only.py", source)
    git_repository(tmp_path, "tests")

    report = find_tests_for_symbol(tmp_path, "collect_payment")

    assert report.mapping_status == "no_mapping_found"
    assert report.candidates == ()
    assert [import_summary(item) for item in report.matching_imports] == [
        {
            "path": "tests/test_import_only.py",
            "module": "app.service",
            "relative_level": 0,
            "imported_name": "collect_payment",
            "local_name": "collect_payment",
        }
    ]
    assert_import_matches_source(report.matching_imports[0], source)


def test_reports_relative_nested_and_deterministically_sorted_matching_imports(
    tmp_path: Path,
) -> None:
    class ReversedTestFileSource:
        def python_files(self, repository: Path) -> list[Path]:
            return [
                repository / "tests/test_beta.py",
                repository / "tests/test_alpha.py",
                repository / "tests/service.py",
            ]

    alpha_source = (
        "from pkg.service import collect_payment as module_alias\n\n"
        "def test_alpha():\n"
        "    from . import collect_payment as local_alias\n"
        "    local_alias()\n"
    )
    beta_source = (
        "def test_beta():\n    from pkg.service import collect_payment\n    collect_payment()\n"
    )
    write_python(tmp_path, "tests/test_beta.py", beta_source)
    write_python(tmp_path, "tests/test_alpha.py", alpha_source)
    write_python(tmp_path, "tests/service.py", "def collect_payment():\n    return 1\n")
    git_repository(tmp_path, "tests")

    report = find_tests_for_symbol(
        tmp_path,
        "collect_payment",
        file_source=ReversedTestFileSource(),
    )

    assert [import_summary(item) for item in report.matching_imports] == [
        {
            "path": "tests/test_alpha.py",
            "module": "pkg.service",
            "relative_level": 0,
            "imported_name": "collect_payment",
            "local_name": "module_alias",
        },
        {
            "path": "tests/test_alpha.py",
            "module": None,
            "relative_level": 1,
            "imported_name": "collect_payment",
            "local_name": "local_alias",
        },
        {
            "path": "tests/test_beta.py",
            "module": "pkg.service",
            "relative_level": 0,
            "imported_name": "collect_payment",
            "local_name": "collect_payment",
        },
    ]
    for matching_import, source in [
        (report.matching_imports[0], alpha_source),
        (report.matching_imports[1], alpha_source),
        (report.matching_imports[2], beta_source),
    ]:
        assert_import_matches_source(matching_import, source)
