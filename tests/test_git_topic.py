from pathlib import Path

import pytest

from otter_kr.git_ports import (
    CommitChangeSource,
    CommitMetadata,
    CommitPatchRequest,
    CommitPathChange,
    RawCommitPatch,
)
from otter_kr.git_topic import describe_topic_commit


class FakeMetadata:
    def __init__(self, parents: tuple[str, ...]) -> None:
        self.parents = parents

    def commit_metadata(self, repository: Path, query: object) -> list[CommitMetadata]:
        return [CommitMetadata("abc123", self.parents, 10, "author", "a@example.com", "subject")]


class FakeChanges(CommitChangeSource):
    def __init__(self, status: str, path: str, previous_path: str | None = None) -> None:
        self.status = status
        self.path = path
        self.previous_path = previous_path

    def commit_changes(self, repository: Path, commit_sha: str) -> list[CommitPathChange]:
        return [CommitPathChange(self.status, self.path, self.previous_path)]


class FakePatches:
    def __init__(self, patch: bytes) -> None:
        self.patch = patch

    def commit_patch(self, repository: Path, request: CommitPatchRequest) -> RawCommitPatch:
        return RawCommitPatch(request.commit_sha, request.parent_sha, self.patch)


def test_topic_changes_carry_matching_hunk_references(tmp_path: Path) -> None:
    report = describe_topic_commit(
        tmp_path,
        "abc123",
        metadata=FakeMetadata(("parent",)),
        changes=FakeChanges("M", "src/service.py"),
        patches=FakePatches(
            b"diff --git a/src/service.py b/src/service.py\n"
            b"--- a/src/service.py\n+++ b/src/service.py\n"
            b"@@ -1 +1 @@\n-old\n+new\n"
        ),
    )

    change = report.to_dict()["changes"][0]
    assert change["hunk_status"] == "available"
    assert change["hunks"][0]["path"] == "src/service.py"


@pytest.mark.parametrize(
    ("parents", "status", "path", "previous_path", "patch", "expected"),
    [
        ((), "A", "src/new.py", None, b"", "initial"),
        (("parent", "other"), "M", "src/service.py", None, b"", "merge"),
        (("parent",), "R100", "src/new.py", "src/old.py", b"", "rename_only"),
        (("parent",), "M", "src/data.bin", None, b"GIT binary patch\n", "binary"),
    ],
)
def test_topic_change_status_preserves_non_text_cases(
    tmp_path: Path,
    parents: tuple[str, ...],
    status: str,
    path: str,
    previous_path: str | None,
    patch: bytes,
    expected: str,
) -> None:
    report = describe_topic_commit(
        tmp_path,
        "abc123",
        metadata=FakeMetadata(parents),
        changes=FakeChanges(status, path, previous_path),
        patches=FakePatches(patch),
    )

    assert report.to_dict()["changes"][0]["hunk_status"] == expected
