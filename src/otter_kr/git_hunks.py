"""Stable, line-number-independent unified-diff hunk evidence."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_ports import (
    CommitHistoryQuery,
    CommitMetadataSource,
    CommitPatchRequest,
    CommitPatchSource,
)

_HEADER = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


@dataclass(frozen=True, slots=True)
class TopicHunk:
    path: str
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: tuple[str, ...]
    normalized_body: str
    fingerprint: str

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "lines": list(self.lines),
            "normalized_body": self.normalized_body,
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True, slots=True)
class TopicHunkReport:
    commit_sha: str
    hunks: tuple[TopicHunk, ...]
    status: str = "available"
    uncertainties: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "hunks": [hunk.to_dict() for hunk in self.hunks],
            "status": self.status,
            "uncertainties": list(self.uncertainties),
        }


def extract_hunks(patch: bytes) -> tuple[TopicHunk, ...]:
    path = ""
    hunks: list[TopicHunk] = []
    current: tuple[int, int, int, int, list[str]] | None = None
    for line in patch.decode("utf-8", errors="replace").splitlines():
        if line.startswith("+++ b/"):
            path = line[6:]
        match = _HEADER.match(line)
        if match:
            if current is not None:
                hunks.append(_finish(path, current))
            current = (
                int(match.group(1)),
                int(match.group(2) or 1),
                int(match.group(3)),
                int(match.group(4) or 1),
                [],
            )
        elif current is not None and (
            line.startswith(("+", "-", " ")) or line == "\\ No newline at end of file"
        ):
            current[4].append(line)
    if current is not None:
        hunks.append(_finish(path, current))
    return tuple(hunks)


def _finish(path: str, data: tuple[int, int, int, int, list[str]]) -> TopicHunk:
    old_start, old_count, new_start, new_count, lines = data
    normalized = "\n".join(line[:1] + line[1:].rstrip() for line in lines)
    fingerprint = hashlib.sha256(normalized.encode()).hexdigest()
    return TopicHunk(
        path, old_start, old_count, new_start, new_count, tuple(lines), normalized, fingerprint
    )


def collect_topic_hunks(
    repository: Path,
    commit_sha: str,
    *,
    metadata: CommitMetadataSource | None = None,
    patches: CommitPatchSource | None = None,
) -> TopicHunkReport:
    history = metadata or GitCliHistory()
    commit = next(
        iter(history.commit_metadata(repository, CommitHistoryQuery(1, 1, tip_sha=commit_sha))),
        None,
    )
    if commit is None:
        return TopicHunkReport(commit_sha, (), "unavailable", ("commit_not_found",))
    if not commit.parent_shas:
        return TopicHunkReport(commit_sha, (), "initial", ("no_parent",))
    if len(commit.parent_shas) != 1:
        return TopicHunkReport(commit_sha, (), "merge", ("multiple_parents",))
    source = patches or GitCliHistory()
    patch = source.commit_patch(repository, CommitPatchRequest(commit.sha, commit.parent_shas[0]))
    try:
        patch.patch.decode("utf-8")
        encoding_uncertainty: tuple[str, ...] = ()
    except UnicodeDecodeError:
        encoding_uncertainty = ("non_utf8_patch",)
    hunks = extract_hunks(patch.patch)
    binary_patch = any(
        line == b"GIT binary patch" or line.startswith(b"Binary files ")
        for line in patch.patch.splitlines()
    )
    if binary_patch:
        return TopicHunkReport(commit_sha, hunks, "binary", ("binary_patch",))
    if not hunks:
        return TopicHunkReport(
            commit_sha,
            (),
            "encoding" if encoding_uncertainty else "no_hunks",
            encoding_uncertainty or ("no_unified_hunks",),
        )
    fingerprints = [hunk.fingerprint for hunk in hunks]
    if len(set(fingerprints)) != len(fingerprints):
        return TopicHunkReport(
            commit_sha,
            hunks,
            "ambiguous",
            encoding_uncertainty + ("duplicate_fingerprints",),
        )
    return TopicHunkReport(commit_sha, hunks, "available", encoding_uncertainty)
