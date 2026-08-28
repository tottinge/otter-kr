from pathlib import Path

from otter_kr.git_branch_growth import collect_branch_additions
from otter_kr.git_ports import CommitMetadata, RawCommitPatch


class FakeHistory:
    def __init__(self, commits):
        self.commits = commits

    def commit_metadata(self, repository: Path, query):
        return self.commits


class FakePatches:
    def __init__(self, patches):
        self.patches = patches

    def commit_patch(self, repository: Path, request):
        return RawCommitPatch(
            request.commit_sha,
            request.parent_sha,
            self.patches[request.commit_sha],
        )


def commit(sha: str, parent: str, subject: str = "change") -> CommitMetadata:
    return CommitMetadata(sha, (parent,), 1, "Test", "test@example.com", subject)


def test_reports_added_branch_constructs_with_new_line_locations(tmp_path: Path) -> None:
    report = collect_branch_additions(
        tmp_path,
        "pkg/service.py",
        since_unix_time=1,
        limit=2,
        history=FakeHistory([commit("c2", "c1"), commit("c1", "p1")]),
        patches=FakePatches(
            {
                "c2": b"@@ -1,1 +1,3 @@\n value = 1\n+if ready:\n+    value = 2\n",
                "c1": b"@@ -1,1 +1,2 @@\n value = 0\n+for item in items:\n",
            }
        ),
    )

    assert report.to_dict()["events"] == [
        {
            "commit_sha": "c2",
            "parent_sha": "c1",
            "line": 2,
            "construct": "if",
            "text": "if ready:",
        },
        {
            "commit_sha": "c1",
            "parent_sha": "p1",
            "line": 2,
            "construct": "for",
            "text": "for item in items:",
        },
    ]
    assert report.to_dict()["branch_addition_count"] == 2
