import subprocess
from pathlib import Path

from otter_kr.python_literals import find_repeated_literals


def test_reports_repeated_non_trivial_literals_with_locations(tmp_path: Path) -> None:
    source = (
        'MESSAGE = "retry later"\n\ndef run():\n'
        '    return "retry later", 42\n\ndef again():\n'
        '    return "retry later", 42\n'
    )
    (tmp_path / "app.py").write_text(source)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "app.py"], check=True)

    report = find_repeated_literals(tmp_path)

    assert [(literal.kind, literal.value, literal.count) for literal in report.literals] == [
        ("integer", "42", 2),
        ("string", "retry later", 3),
    ]
    lines = source.splitlines()
    for literal in report.literals:
        assert all(occurrence.path == "app.py" for occurrence in literal.occurrences)
        assert all(
            literal.value in lines[occurrence.line - 1] for occurrence in literal.occurrences
        )


def test_excludes_trivial_constants_and_untracked_files(tmp_path: Path) -> None:
    (tmp_path / "tracked.py").write_text('def f():\n    return None, True, 0, 1, "", 42\n')
    (tmp_path / "untracked.py").write_text("value = 42\nvalue = 42\n")
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "tracked.py"], check=True)

    report = find_repeated_literals(tmp_path)

    assert report.literals == ()
