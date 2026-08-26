import subprocess
from pathlib import Path

from otter_kr.python_groups import find_repeated_groups


def test_reports_repeated_parameter_groups_and_field_sets(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text(
        "def first(user, account, flag):\n    pass\n\n"
        "def second(user, account, flag):\n    pass\n\n"
        "class One:\n    user: str\n    account: str\n\n"
        "class Two:\n    user: str\n    account: str\n"
    )
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "add", "app.py"], check=True)

    report = find_repeated_groups(tmp_path)

    assert [(item.kind, item.members, item.count) for item in report.groups] == [
        ("fields", ("user", "account"), 2),
        ("parameters", ("user", "account", "flag"), 2),
    ]
