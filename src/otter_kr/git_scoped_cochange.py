"""Focus-file projection of bounded global co-change evidence."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from otter_kr.cochange_affinity import DEFAULT_POLICY, CochangeWeightingPolicy
from otter_kr.git_cochange import GlobalCochangePair, collect_global_cochange
from otter_kr.git_ports import CommitFileChangeSource
from otter_kr.git_provenance import BoundedHistoryProvenance


@dataclass(frozen=True, slots=True)
class ScopedCochangeReport:
    focus_path: str
    provenance: BoundedHistoryProvenance
    excluded_single_file_commits: int
    eligible_commit_count: int
    pairs: tuple[GlobalCochangePair, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "focus_path": self.focus_path,
            **self.provenance.to_dict(),
            "excluded_single_file_commits": self.excluded_single_file_commits,
            "eligible_commit_count": self.eligible_commit_count,
            "pairs": [pair.to_dict() for pair in self.pairs],
        }


def collect_scoped_cochange(
    repository: Path,
    focus_path: str,
    *,
    since_unix_time: int,
    limit: int,
    changes: CommitFileChangeSource,
    policy: CochangeWeightingPolicy = DEFAULT_POLICY,
) -> ScopedCochangeReport:
    """Project global weighted co-change evidence onto one repository-relative file."""
    normalized = PurePosixPath(focus_path).as_posix()
    if (
        not focus_path
        or focus_path.startswith("/")
        or "\\" in focus_path
        or focus_path != normalized
        or any(part == ".." for part in PurePosixPath(normalized).parts)
    ):
        raise ValueError("focus_path must be repository-relative.")
    report = collect_global_cochange(
        repository,
        since_unix_time=since_unix_time,
        limit=limit,
        changes=changes,
        policy=policy,
    )
    pairs = tuple(
        pair
        for pair in report.pairs
        if pair.left_path == focus_path or pair.right_path == focus_path
    )
    return ScopedCochangeReport(
        focus_path=focus_path,
        provenance=report.provenance,
        excluded_single_file_commits=report.excluded_single_file_commits,
        eligible_commit_count=report.eligible_commit_count,
        pairs=pairs,
    )
