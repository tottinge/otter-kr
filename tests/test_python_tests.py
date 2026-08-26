import subprocess
from pathlib import Path

from otter_kr.python_tests import find_tests_for_symbol


class ReversedFileSource:
    def python_files(self, repository: Path) -> list[Path]:
        return [
            repository / "tests/test_b.py",
            repository / "tests/test_a.py",
            repository / "broken.py",
            repository / "bad_encoding.py",
        ]


def write_python(repository: Path, relative_path: str, source: str) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source)


def write_bytes(repository: Path, relative_path: str, source: bytes) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)


def git_repository(repository: Path, *paths: str) -> None:
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", *paths], check=True)


def assert_evidence_matches_source(candidate, source: str) -> None:
    lines = source.splitlines()
    for evidence in candidate.evidence:
        line = lines[evidence.line - 1]
        assert evidence.expression in line
        assert line[evidence.column :].startswith(evidence.name)


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
    for candidate in report.candidates:
        assert_evidence_matches_source(candidate, source)


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
    assert list(report.warnings) == [
        {
            "code": "unreadable_file",
            "path": "bad_encoding.py",
            "message": "File could not be decoded as UTF-8.",
        },
        {
            "code": "invalid_python",
            "path": "broken.py",
            "message": "Syntax error at line 1, column 10: invalid syntax",
        },
    ]


def test_reports_no_mapping_found_for_selected_symbol(tmp_path: Path) -> None:
    write_python(tmp_path, "tests/test_service.py", "def test_other():\n    assert True\n")
    git_repository(tmp_path, "tests")

    report = find_tests_for_symbol(tmp_path, "collect_payment")

    assert report.mapping_status == "no_mapping_found"
    assert report.candidates == ()
    assert report.warnings == ()
