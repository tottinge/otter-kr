import ast
from pathlib import Path

import pytest

from tests.support import git_commit, git_repository, write_python


def _module_path(name: str) -> Path:
    return Path(__file__).parents[1] / "src" / "otter_kr" / f"{name}.py"


def _imports_for(name: str) -> set[str]:
    tree = ast.parse(_module_path(name).read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.add(node.module)
    return imports


def test_git_ports_do_not_depend_on_adapters_or_server() -> None:
    imports = _imports_for("git_ports")

    assert "otter_kr.git_cli_history" not in imports
    assert "otter_kr.server" not in imports


def test_git_cli_history_depends_on_ports_but_not_server() -> None:
    imports = _imports_for("git_cli_history")

    assert "otter_kr.git_ports" in imports
    assert "otter_kr.server" not in imports


def test_lists_bounded_commit_metadata_with_injected_runner(tmp_path: Path) -> None:
    from otter_kr.git_cli_history import GitCliHistory
    from otter_kr.git_ports import CommitHistoryQuery, CommitMetadata

    calls: list[tuple[str, ...]] = []
    first = "1" * 40
    second = "2" * 40

    def runner(command: tuple[str, ...]) -> tuple[int, bytes, bytes]:
        calls.append(command)
        stdout = (
            first.encode("utf-8")
            + b"\0"
            + b"\0"
            + b"1700000001"
            + b"\0Test User\0test@example.com\0first change\0"
            + second.encode("utf-8")
            + b"\0"
            + first.encode("utf-8")
            + b"\0"
            + b"1700000002"
            + b"\0Other User\0other@example.com\0second change\0"
        )
        return 0, stdout, b""

    history = GitCliHistory(runner=runner)

    commits = history.commit_metadata(
        tmp_path,
        CommitHistoryQuery(
            limit=2,
            since_unix_time=1_700_000_000,
            tip_sha=second,
            paths=("*.py",),
        ),
    )

    assert calls == [
        (
            "git",
            "-C",
            str(tmp_path),
            "log",
            "-z",
            "--format=%H%x00%P%x00%ct%x00%an%x00%ae%x00%s",
            "--date-order",
            "--max-count=3",
            "--since=@1700000000",
            second,
            "--",
            "*.py",
        )
    ]
    assert commits == [
        CommitMetadata(
            sha=first,
            parent_shas=(),
            committed_unix_time=1700000001,
            author_name="Test User",
            author_email="test@example.com",
            subject="first change",
        ),
        CommitMetadata(
            sha=second,
            parent_shas=(first,),
            committed_unix_time=1700000002,
            author_name="Other User",
            author_email="other@example.com",
            subject="second change",
        ),
    ]


def test_lists_bounded_numstat_file_changes_with_injected_runner(tmp_path: Path) -> None:
    from otter_kr.git_cli_history import GitCliHistory
    from otter_kr.git_ports import CommitFileChange, CommitHistoryQuery

    sha = "1" * 40
    output = (
        sha.encode()
        + b"\0"
        + b"1700000001\0\0"
        + b"\n4\t2\tpkg/service.py\0"
        + b"1\t0\tpkg/helpers.py\0"
    )
    calls: list[tuple[str, ...]] = []

    def runner(command: tuple[str, ...]) -> tuple[int, bytes, bytes]:
        calls.append(command)
        return 0, output, b""

    changes = GitCliHistory(runner=runner).commit_file_changes(
        tmp_path,
        CommitHistoryQuery(limit=2, since_unix_time=1_700_000_000, paths=("*.py",)),
    )

    assert calls == [
        (
            "git",
            "-C",
            str(tmp_path),
            "log",
            "--numstat",
            "--no-renames",
            "-z",
            "--format=%H%x00%ct%x00",
            "--date-order",
            "--max-count=3",
            "--since=@1700000000",
            "HEAD",
            "--",
            "*.py",
        )
    ]
    assert changes == [
        CommitFileChange(
            commit_sha=sha,
            committed_unix_time=1_700_000_001,
            path="pkg/service.py",
            additions=4,
            deletions=2,
        ),
        CommitFileChange(
            commit_sha=sha,
            committed_unix_time=1_700_000_001,
            path="pkg/helpers.py",
            additions=1,
            deletions=0,
        ),
    ]


def test_commit_metadata_rejects_invalid_query_values(tmp_path: Path) -> None:
    from otter_kr.git_cli_history import GitCliHistory, GitHistoryValidationError
    from otter_kr.git_ports import CommitHistoryQuery

    history = GitCliHistory(runner=lambda command: (0, b"", b""))

    with pytest.raises(GitHistoryValidationError, match="limit must be between 1 and 5000"):
        history.commit_metadata(tmp_path, CommitHistoryQuery(limit=0, since_unix_time=1))

    with pytest.raises(GitHistoryValidationError, match="since_unix_time must be positive"):
        history.commit_metadata(tmp_path, CommitHistoryQuery(limit=1, since_unix_time=0))

    with pytest.raises(GitHistoryValidationError, match="tip_sha must be a Git SHA"):
        history.commit_metadata(
            tmp_path, CommitHistoryQuery(limit=1, since_unix_time=1, tip_sha="HEAD")
        )

    with pytest.raises(GitHistoryValidationError, match="paths must be repository-relative"):
        history.commit_metadata(
            tmp_path,
            CommitHistoryQuery(limit=1, since_unix_time=1, paths=("/tmp/file.py",)),
        )


def test_reads_parent_based_patch_with_injected_runner(tmp_path: Path) -> None:
    from otter_kr.git_cli_history import GitCliHistory
    from otter_kr.git_ports import CommitPatchRequest, RawCommitPatch

    calls: list[tuple[str, ...]] = []
    parent = "a" * 40
    commit = "b" * 40
    patch_bytes = b"diff --git a/pkg/service.py b/pkg/service.py\n@@ -1 +1 @@\n-old\n+new\n"

    def runner(command: tuple[str, ...]) -> tuple[int, bytes, bytes]:
        calls.append(command)
        return 0, patch_bytes, b""

    history = GitCliHistory(runner=runner)

    patch = history.commit_patch(
        tmp_path,
        CommitPatchRequest(
            commit_sha=commit,
            parent_sha=parent,
            paths=("pkg/service.py",),
            max_bytes=4096,
        ),
    )

    assert calls == [
        (
            "git",
            "-C",
            str(tmp_path),
            "diff",
            "--no-color",
            "--no-ext-diff",
            "--binary",
            parent,
            commit,
            "--",
            "pkg/service.py",
        )
    ]
    assert patch == RawCommitPatch(
        commit_sha=commit,
        parent_sha=parent,
        patch=patch_bytes,
    )


def test_patch_reader_rejects_oversized_output(tmp_path: Path) -> None:
    from otter_kr.git_cli_history import GitCliHistory, GitHistoryPatchTooLargeError
    from otter_kr.git_ports import CommitPatchRequest

    history = GitCliHistory(runner=lambda command: (0, b"x" * 9, b""))

    with pytest.raises(GitHistoryPatchTooLargeError, match="Patch output exceeded 8 bytes"):
        history.commit_patch(
            tmp_path,
            CommitPatchRequest(
                commit_sha="b" * 40,
                parent_sha="a" * 40,
                max_bytes=8,
            ),
        )


def test_adapter_preserves_git_failure_evidence(tmp_path: Path) -> None:
    from otter_kr.git_cli_history import GitCliHistory, GitHistoryError
    from otter_kr.git_ports import CommitHistoryQuery

    history = GitCliHistory(runner=lambda command: (128, b"", b"fatal: not a git repository\n"))

    with pytest.raises(GitHistoryError) as error:
        history.commit_metadata(tmp_path, CommitHistoryQuery(limit=1, since_unix_time=1))

    assert error.value.command[:4] == ("git", "-C", str(tmp_path), "log")
    assert error.value.returncode == 128
    assert error.value.stderr == "fatal: not a git repository"


def test_lists_real_commit_metadata_in_deterministic_order(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    first = git_commit(tmp_path, "initial import")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    second = git_commit(tmp_path, "adjust service", "pkg/service.py")
    write_python(tmp_path, "notes.txt", "ignored by path filter\n")
    third = git_commit(tmp_path, "notes only", "notes.txt")

    from otter_kr.git_cli_history import GitCliHistory
    from otter_kr.git_ports import CommitHistoryQuery

    commits = GitCliHistory().commit_metadata(
        tmp_path,
        CommitHistoryQuery(
            limit=2,
            since_unix_time=1,
            tip_sha=third,
            paths=("*.py",),
        ),
    )

    assert [item.sha for item in commits] == [second, first]
    assert commits[0].parent_shas == (first,)
    assert commits[0].subject == "adjust service"
    assert commits[1].parent_shas == ()
    assert commits[1].subject == "initial import"


def test_commit_metadata_marks_truncation_when_limit_plus_one_records_arrive(
    tmp_path: Path,
) -> None:
    from otter_kr.git_cli_history import GitCliHistory
    from otter_kr.git_ports import CommitHistoryQuery

    records = []
    for index in range(3):
        sha = str(index + 1) * 40
        records.extend(
            [
                sha.encode("utf-8"),
                b"",
                str(1_700_000_000 + index).encode("utf-8"),
                b"Test User",
                b"test@example.com",
                f"change {index}".encode(),
            ]
        )
    stdout = b"\0".join(records) + b"\0"

    history = GitCliHistory(runner=lambda command: (0, stdout, b""))

    commits = history.commit_metadata(
        tmp_path,
        CommitHistoryQuery(limit=2, since_unix_time=1, tip_sha="1" * 40, paths=("*.py",)),
    )

    assert len(commits) == 3
    assert [item.subject for item in commits] == ["change 0", "change 1", "change 2"]


def test_reads_real_parent_based_patch(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    parent = git_commit(tmp_path, "initial import")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    commit = git_commit(tmp_path, "adjust service", "pkg/service.py")

    from otter_kr.git_cli_history import GitCliHistory
    from otter_kr.git_ports import CommitPatchRequest

    patch = GitCliHistory().commit_patch(
        tmp_path,
        CommitPatchRequest(
            commit_sha=commit,
            parent_sha=parent,
            paths=("pkg/service.py",),
            max_bytes=4096,
        ),
    )

    assert patch.commit_sha == commit
    assert patch.parent_sha == parent
    assert b"diff --git a/pkg/service.py b/pkg/service.py" in patch.patch
    assert b"-value = 1" in patch.patch
    assert b"+value = 2" in patch.patch
