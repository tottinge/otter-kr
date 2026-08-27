"""Bounded Git integration for global weighted co-change evidence."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from otter_kr.cochange_affinity import (
    DEFAULT_POLICY,
    CochangeWeightingPolicy,
    calculate_cochange_affinity,
)
from otter_kr.git_identity import canonicalize_file_changes
from otter_kr.git_ports import CommitFileChange, CommitFileChangeSource, CommitHistoryQuery

_REPORT_VERSION = "1"
_PYTHON_PATHSPEC = "*.py"


@dataclass(frozen=True, slots=True)
class GlobalCochangePair:
    left_path: str
    right_path: str
    score: float
    commit_count: int
    contributing_commits: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "left_path": self.left_path,
            "right_path": self.right_path,
            "score": self.score,
            "commit_count": self.commit_count,
            "contributing_commits": list(self.contributing_commits),
        }


@dataclass(frozen=True, slots=True)
class GlobalCochangeReport:
    report_version: str
    repository_root: str
    tip_revision: str
    since_unix_time: int
    limit: int
    commit_count: int
    truncated: bool
    source_file_filter: dict[str, str]
    excluded_single_file_commits: int
    eligible_commit_count: int
    pairs: tuple[GlobalCochangePair, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "report_version": self.report_version,
            "repository_root": self.repository_root,
            "tip_revision": self.tip_revision,
            "since_unix_time": self.since_unix_time,
            "limit": self.limit,
            "commit_count": self.commit_count,
            "truncated": self.truncated,
            "source_file_filter": self.source_file_filter,
            "excluded_single_file_commits": self.excluded_single_file_commits,
            "eligible_commit_count": self.eligible_commit_count,
            "pairs": [pair.to_dict() for pair in self.pairs],
        }


def collect_global_cochange(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource,
    policy: CochangeWeightingPolicy = DEFAULT_POLICY,
) -> GlobalCochangeReport:
    """Calculate normalized co-change evidence for bounded tracked Python history."""
    resolved_repository = repository.resolve()
    if not resolved_repository.is_dir():
        raise ValueError(f"Repository is not a directory: {resolved_repository}")
    if since_unix_time <= 0:
        raise ValueError("since_unix_time must be positive.")
    if limit <= 0:
        raise ValueError("limit must be positive.")

    records = canonicalize_file_changes(
        changes.commit_file_changes(
            resolved_repository,
            CommitHistoryQuery(
                limit=limit, since_unix_time=since_unix_time, paths=(_PYTHON_PATHSPEC,)
            ),
        )
    )
    commit_order = list(dict.fromkeys(record.commit_sha for record in records))
    visible_commits = tuple(commit_order[:limit])
    visible_records = [record for record in records if record.commit_sha in visible_commits]
    commits = _paths_by_commit(visible_records)
    affinity = calculate_cochange_affinity((paths for _, paths in commits), policy=policy)
    pair_commits = _pair_commits(commits)
    pairs = tuple(
        GlobalCochangePair(
            left_path=pair.left_path,
            right_path=pair.right_path,
            score=pair.score,
            commit_count=len(pair_commits[(pair.left_path, pair.right_path)]),
            contributing_commits=pair_commits[(pair.left_path, pair.right_path)],
        )
        for pair in sorted(
            affinity.pairs,
            key=lambda pair: (-pair.score, pair.left_path, pair.right_path),
        )
    )
    return GlobalCochangeReport(
        report_version=_REPORT_VERSION,
        repository_root=str(resolved_repository),
        tip_revision="HEAD",
        since_unix_time=since_unix_time,
        limit=limit,
        commit_count=len(visible_commits),
        truncated=len(commit_order) > limit,
        source_file_filter={
            "tracked_by": "git",
            "language": "python",
            "pathspec": _PYTHON_PATHSPEC,
            "tip_revision": "HEAD",
        },
        excluded_single_file_commits=affinity.excluded_single_file_commits,
        eligible_commit_count=affinity.eligible_commit_count,
        pairs=pairs,
    )


def _paths_by_commit(records: list[CommitFileChange]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    grouped: dict[str, list[str]] = {}
    for record in records:
        grouped.setdefault(record.commit_sha, []).append(record.path)
    return tuple((sha, tuple(paths)) for sha, paths in grouped.items())


def _pair_commits(
    commits: tuple[tuple[str, tuple[str, ...]], ...],
) -> dict[tuple[str, str], tuple[str, ...]]:
    result: dict[tuple[str, str], list[str]] = {}
    for commit_sha, paths in commits:
        unique_paths = tuple(sorted(set(paths)))
        for left_path, right_path in combinations(unique_paths, 2):
            result.setdefault((left_path, right_path), []).append(commit_sha)
    return {pair: tuple(shas) for pair, shas in result.items()}
