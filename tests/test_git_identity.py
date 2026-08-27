from otter_kr.git_identity import canonicalize_file_changes
from otter_kr.git_ports import CommitFileChange


def test_maps_history_before_rename_to_newest_path() -> None:
    records = [
        CommitFileChange("rename", 3, "new.py", 1, 0, previous_path="old.py"),
        CommitFileChange("before", 2, "old.py", 2, 1),
    ]

    canonical = canonicalize_file_changes(records)

    assert [record.path for record in canonical] == ["new.py", "new.py"]
    assert canonical[0].previous_path == "old.py"
