from pathlib import Path

import pytest

from otter_kr.git_hunks import collect_topic_hunks
from otter_kr.git_ports import CommitMetadata, CommitPatchRequest, RawCommitPatch


class FakeMetadata:
    def __init__(self, parents: tuple[str, ...]) -> None:
        self.parents = parents

    def commit_metadata(self, repository: Path, query: object) -> list[CommitMetadata]:
        return [CommitMetadata("abc123", self.parents, 10, "author", "a@example.com", "subject")]


class FakePatches:
    def __init__(self, patch: bytes) -> None:
        self.patch = patch

    def commit_patch(self, repository: Path, request: CommitPatchRequest) -> RawCommitPatch:
        return RawCommitPatch(request.commit_sha, request.parent_sha, self.patch)


@pytest.mark.parametrize(
    ("parents", "patch", "status", "uncertainty"),
    [
        ((), b"", "initial", "no_parent"),
        (("p1", "p2"), b"", "merge", "multiple_parents"),
        (("p1",), b"GIT binary patch\n", "binary", "binary_patch"),
        (("p1",), b"not a unified diff\n", "no_hunks", "no_unified_hunks"),
    ],
)
def test_reports_why_hunks_are_unavailable_or_uncertain(
    tmp_path: Path,
    parents: tuple[str, ...],
    patch: bytes,
    status: str,
    uncertainty: str,
) -> None:
    report = collect_topic_hunks(
        tmp_path,
        "abc123",
        metadata=FakeMetadata(parents),
        patches=FakePatches(patch),
    )

    assert report.status == status
    assert uncertainty in report.uncertainties


def test_reports_duplicate_hunk_fingerprints_as_ambiguous(tmp_path: Path) -> None:
    patch = b"+++ b/a.py\n@@ -1 +1 @@\n-old\n+new\n@@ -4 +4 @@\n-old\n+new\n"

    report = collect_topic_hunks(
        tmp_path,
        "abc123",
        metadata=FakeMetadata(("p1",)),
        patches=FakePatches(patch),
    )

    assert report.status == "ambiguous"
    assert report.to_dict()["uncertainties"] == ["duplicate_fingerprints"]
