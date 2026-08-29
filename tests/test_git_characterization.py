import subprocess
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_hunks import extract_hunks
from otter_kr.git_ports import CommitHistoryQuery, CommitPatchRequest


def _commit(repository: Path, message: str) -> str:
    subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "commit",
            "-q",
            "-m",
            message,
        ],
        check=True,
    )
    return subprocess.run(
        ["git", "-C", str(repository), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "fixture"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    return repository


def test_planted_two_file_change_and_rename_have_independent_git_oracles(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (repository / "a.py").write_text("a = 1\n", encoding="utf-8")
    (repository / "b.py").write_text("b = 1\n", encoding="utf-8")
    initial = _commit(repository, "initial")
    (repository / "a.py").write_text("a = 2\n", encoding="utf-8")
    (repository / "b.py").write_text("b = 2\n", encoding="utf-8")
    focused = _commit(repository, "change pair")
    (repository / "a.py").rename(repository / "renamed.py")
    renamed = _commit(repository, "rename a")

    history = GitCliHistory()
    commits = history.commit_metadata(repository, CommitHistoryQuery(5, 1, tip_sha=renamed))
    changes = history.commit_file_changes(repository, CommitHistoryQuery(5, 1, tip_sha=renamed))

    assert [commit.sha for commit in commits[:3]] == [renamed, focused, initial]
    rename_change = next(change for change in changes if change.commit_sha == renamed)
    assert rename_change.path == "renamed.py"
    assert rename_change.previous_path == "a.py"


def test_planted_repeated_edits_and_deletion_preserve_commit_order(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (repository / "tracked.py").write_text("value = 1\n", encoding="utf-8")
    first = _commit(repository, "initial")
    (repository / "tracked.py").write_text("value = 2\n", encoding="utf-8")
    second = _commit(repository, "edit one")
    (repository / "tracked.py").write_text("value = 3\n", encoding="utf-8")
    third = _commit(repository, "edit two")
    (repository / "tracked.py").unlink()
    deleted = _commit(repository, "delete file")

    history = GitCliHistory()
    commits = history.commit_metadata(repository, CommitHistoryQuery(6, 1, tip_sha=deleted))
    changes = history.commit_file_changes(repository, CommitHistoryQuery(6, 1, tip_sha=deleted))

    assert [item.sha for item in commits[:4]] == [deleted, third, second, first]
    assert next(item for item in changes if item.commit_sha == deleted).path == "tracked.py"


def test_planted_binary_change_is_explicitly_unavailable_in_numstat(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (repository / "image.bin").write_bytes(b"\x00\x01")
    _commit(repository, "binary initial")
    (repository / "image.bin").write_bytes(b"\x00\x02")
    changed = _commit(repository, "binary change")

    changes = GitCliHistory().commit_file_changes(
        repository, CommitHistoryQuery(2, 1, tip_sha=changed)
    )

    assert all(item.path != "image.bin" for item in changes)


def test_planted_fix_and_preimage_hunks_have_known_path_and_distinct_bodies(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (repository / "bug.py").write_text("return_value = 1\n", encoding="utf-8")
    _commit(repository, "baseline")
    (repository / "bug.py").write_text("return_value = 0\n", encoding="utf-8")
    initial = _commit(repository, "introduce defect")
    (repository / "bug.py").write_text("return_value = 1\n", encoding="utf-8")
    fix = _commit(repository, "fix defect")
    source = GitCliHistory()
    fix_metadata = source.commit_metadata(repository, CommitHistoryQuery(1, 1, tip_sha=fix))[0]
    fix_patch = source.commit_patch(
        repository, CommitPatchRequest(fix, fix_metadata.parent_shas[0])
    )
    prior_metadata = source.commit_metadata(repository, CommitHistoryQuery(1, 1, tip_sha=initial))[
        0
    ]
    prior_patch = source.commit_patch(
        repository, CommitPatchRequest(initial, prior_metadata.parent_shas[0])
    )

    fix_hunk = extract_hunks(fix_patch.patch)[0]
    prior_hunk = extract_hunks(prior_patch.patch)[0]

    assert fix_hunk.path == prior_hunk.path == "bug.py"
    assert fix_hunk.fingerprint != prior_hunk.fingerprint


def test_planted_merge_exposes_multiple_parents_without_first_parent_guess(tmp_path: Path) -> None:
    repository = _repository(tmp_path)
    (repository / "base.py").write_text("base = 1\n", encoding="utf-8")
    _commit(repository, "base")
    subprocess.run(["git", "checkout", "-q", "-b", "side"], cwd=repository, check=True)
    (repository / "side.py").write_text("side = 1\n", encoding="utf-8")
    _commit(repository, "side")
    subprocess.run(["git", "checkout", "-q", "-"], cwd=repository, check=True)
    (repository / "main.py").write_text("main = 1\n", encoding="utf-8")
    _commit(repository, "main")
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.test",
            "merge",
            "--no-ff",
            "-q",
            "side",
            "-m",
            "merge",
        ],
        cwd=repository,
        check=True,
    )

    merge_sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repository, check=True, capture_output=True, text=True
    ).stdout.strip()
    merge = GitCliHistory().commit_metadata(
        repository, CommitHistoryQuery(1, 1, tip_sha=merge_sha)
    )[0]

    assert len(merge.parent_shas) == 2
