from pathlib import Path

from otter_kr.python_names import find_names
from tests.support import git_repository, write_python


def test_finds_exact_definition_and_reference(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "payments/service.py",
        "def collect_payment(payment):\n    return payment\n",
    )
    git_repository(tmp_path, "payments")

    report = find_names(tmp_path, "collect_payment")

    assert report.files_scanned == 1
    assert [(item.path, item.line, item.name, item.kind) for item in report.occurrences] == [
        ("payments/service.py", 1, "collect_payment", "function"),
    ]


def test_finds_lexical_family_across_identifier_styles(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "payments.py",
        "class PaymentProcessor:\n    pass\n\npayment_processor = PaymentProcessor()\n",
    )
    git_repository(tmp_path, "payments.py")

    report = find_names(tmp_path, "payment")

    assert {(item.name, item.kind) for item in report.occurrences} == {
        ("PaymentProcessor", "class"),
        ("PaymentProcessor", "reference"),
        ("payment_processor", "assignment"),
    }


def test_reports_syntax_failures_without_losing_valid_evidence(tmp_path: Path) -> None:
    write_python(tmp_path, "valid.py", "customer_id = 1\n")
    write_python(tmp_path, "broken.py", "def nope(:\n")
    git_repository(tmp_path, "valid.py", "broken.py")

    report = find_names(tmp_path, "customer")

    assert [item.name for item in report.occurrences] == ["customer_id"]
    assert len(report.parse_failures) == 1
    assert report.parse_failures[0].path == "broken.py"
    assert report.parse_failures[0].line == 1


def test_ignores_hidden_and_environment_directories(tmp_path: Path) -> None:
    write_python(tmp_path, "app.py", "visible_name = 1\n")
    write_python(tmp_path, ".hidden/secret.py", "visible_name = 2\n")
    write_python(tmp_path, ".venv/library.py", "visible_name = 3\n")
    git_repository(tmp_path, "app.py")

    report = find_names(tmp_path, "visible")

    assert report.files_scanned == 1
    assert [item.path for item in report.occurrences] == ["app.py"]
