from otter_kr.git_identity import PathAliases, canonicalize_file_changes
from otter_kr.git_ports import CommitFileChange


def test_unmapped_path_resolves_to_itself() -> None:
    aliases = PathAliases()

    assert aliases.resolve("current.py") == "current.py"


def test_path_aliases_resolve_a_rename_chain() -> None:
    aliases = PathAliases()
    aliases.bind("old.py", "renamed.py")
    aliases.bind("renamed.py", "current.py")

    assert aliases.resolve("old.py") == "current.py"


def test_maps_history_before_rename_to_newest_path() -> None:
    records = [
        CommitFileChange("rename", 3, "new.py", 1, 0, previous_path="old.py"),
        CommitFileChange("before", 2, "old.py", 2, 1),
    ]

    canonical = canonicalize_file_changes(records)

    assert [record.path for record in canonical] == ["new.py", "new.py"]
    assert canonical[0].previous_path == "old.py"
