"""Explicit file-pair projection of bounded global co-change evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from otter_kr.cochange_affinity import DEFAULT_POLICY, CochangeWeightingPolicy
from otter_kr.git_cochange import GlobalCochangePair, collect_global_cochange
from otter_kr.git_ports import CommitFileChangeSource
from otter_kr.git_provenance import BoundedHistoryProvenance


@dataclass(frozen=True, slots=True)
class PairCochangeReport:
    left_path: str
    right_path: str
    provenance: BoundedHistoryProvenance
    excluded_single_file_commits: int
    eligible_commit_count: int
    pair: GlobalCochangePair | None

    def to_dict(self) -> dict[str, object]:
        return {
            "left_path": self.left_path,
            "right_path": self.right_path,
            **self.provenance.to_dict(),
            "excluded_single_file_commits": self.excluded_single_file_commits,
            "eligible_commit_count": self.eligible_commit_count,
            "pair": self.pair.to_dict() if self.pair is not None else None,
        }


def collect_pair_cochange(
    repository: Path,
    left_path: str,
    right_path: str,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource,
    policy: CochangeWeightingPolicy = DEFAULT_POLICY,
) -> PairCochangeReport:
    """Project global weighted co-change evidence onto one explicit file pair."""
    _validate_path(left_path)
    _validate_path(right_path)
    if left_path == right_path:
        raise ValueError("left_path and right_path must be different files.")
    report = collect_global_cochange(
        repository,
        since_unix_time=since_unix_time,
        limit=limit,
        changes=changes,
        policy=policy,
    )
    normalized_pair = tuple(sorted((left_path, right_path)))
    pair = next(
        (
            candidate
            for candidate in report.pairs
            if (candidate.left_path, candidate.right_path) == normalized_pair
        ),
        None,
    )
    return PairCochangeReport(
        left_path=left_path,
        right_path=right_path,
        provenance=report.provenance,
        excluded_single_file_commits=report.excluded_single_file_commits,
        eligible_commit_count=report.eligible_commit_count,
        pair=pair,
    )


def _validate_path(path: str) -> None:
    normalized = PurePosixPath(path).as_posix()
    if (
        not path
        or path.startswith("/")
        or "\\" in path
        or path != normalized
        or any(part == ".." for part in PurePosixPath(normalized).parts)
    ):
        raise ValueError("file paths must be repository-relative.")
