"""Evidence of branch constructs added to one Python file over Git history."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from otter_kr.git_ports import (
    CommitHistoryQuery,
    CommitMetadataSource,
    CommitPatchRequest,
    CommitPatchSource,
)
from otter_kr.git_provenance import BoundedHistoryProvenance, python_history_provenance

_BRANCH_START = re.compile(r"(?:if|for|while|try|except|match|case)\b")


@dataclass(frozen=True, slots=True)
class BranchAdditionEvent:
    commit_sha: str
    parent_sha: str | None
    line: int
    construct: str
    text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "parent_sha": self.parent_sha,
            "line": self.line,
            "construct": self.construct,
            "text": self.text,
        }


@dataclass(frozen=True, slots=True)
class GitBranchAdditionReport:
    path: str
    provenance: BoundedHistoryProvenance
    events: tuple[BranchAdditionEvent, ...]
    skipped_commits: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            **self.provenance.to_dict(),
            "branch_addition_count": len(self.events),
            "events": [event.to_dict() for event in self.events],
            "skipped_commits": list(self.skipped_commits),
        }


def collect_branch_additions(
    repository: Path,
    path: str,
    *,
    since_unix_time: int,
    limit: int,
    history: CommitMetadataSource,
    patches: CommitPatchSource,
) -> GitBranchAdditionReport:
    _validate_path(path)
    resolved = repository.resolve()
    if not resolved.is_dir():
        raise ValueError(f"Repository is not a directory: {resolved}")
    if since_unix_time <= 0:
        raise ValueError("since_unix_time must be positive.")
    if limit <= 0:
        raise ValueError("limit must be positive.")
    commits = history.commit_metadata(
        resolved,
        CommitHistoryQuery(limit=limit, since_unix_time=since_unix_time, paths=(path,)),
    )
    visible = commits[:limit]
    events: list[BranchAdditionEvent] = []
    skipped: list[dict[str, str]] = []
    for commit in visible:
        if len(commit.parent_shas) != 1:
            skipped.append({"commit_sha": commit.sha, "reason": "not_first_parent_commit"})
            continue
        patch = patches.commit_patch(
            resolved,
            CommitPatchRequest(commit.sha, commit.parent_shas[0], paths=(path,)),
        )
        events.extend(_branch_additions(patch.patch, commit.sha, commit.parent_shas[0]))
    provenance = python_history_provenance(
        str(resolved),
        since_unix_time=since_unix_time,
        limit=limit,
        commit_count=len(visible),
        truncated=len(commits) > limit,
    )
    return GitBranchAdditionReport(path, provenance, tuple(events), tuple(skipped))


def _branch_additions(patch: bytes, commit_sha: str, parent_sha: str) -> list[BranchAdditionEvent]:
    events: list[BranchAdditionEvent] = []
    new_line = 0
    for raw_line in patch.decode("utf-8", errors="replace").splitlines():
        if raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)", raw_line)
            new_line = int(match.group(1)) if match else 0
            continue
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            text = raw_line[1:].strip()
            match = _BRANCH_START.match(text)
            if match:
                events.append(
                    BranchAdditionEvent(commit_sha, parent_sha, new_line, match.group(0), text)
                )
            new_line += 1
        elif not raw_line.startswith("-"):
            new_line += 1
    return events


def _validate_path(path: str) -> None:
    normalized = PurePosixPath(path).as_posix()
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or path != normalized
        or not path.endswith(".py")
        or any(part == ".." for part in PurePosixPath(path).parts)
    ):
        raise ValueError("path must be a repository-relative Python file.")
