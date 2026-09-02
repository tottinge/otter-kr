"""Bounded calendar and commit-message distribution evidence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from otter_kr.git_ports import CommitHistoryQuery, CommitMetadataSource
from otter_kr.git_provenance import BoundedHistoryProvenance, python_history_provenance

_CONVENTIONAL = re.compile(r"^(?P<raw>[A-Za-z]+)(?:\([^)]*\))?!?:\s")
_KNOWN = {
    "build": "build",
    "chore": "chore",
    "ci": "ci",
    "docs": "docs",
    "feat": "feature",
    "fix": "fix",
    "perf": "performance",
    "refactor": "refactor",
    "revert": "revert",
    "style": "style",
    "test": "test",
}


@dataclass(frozen=True, slots=True)
class CommitMessageCategory:
    commit_sha: str
    subject: str
    raw_category: str | None
    normalized_category: str | None

    def to_dict(self) -> dict[str, object]:
        return {
            "commit_sha": self.commit_sha,
            "subject": self.subject,
            "raw_category": self.raw_category,
            "normalized_category": self.normalized_category,
        }


@dataclass(frozen=True, slots=True)
class WeeklyCommitRow:
    week_start: str
    commit_count: int
    categories: tuple[CommitMessageCategory, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "week_start": self.week_start,
            "commit_count": self.commit_count,
            "categories": [category.to_dict() for category in self.categories],
        }


@dataclass(frozen=True, slots=True)
class GitDistributionReport:
    provenance: BoundedHistoryProvenance
    weeks: tuple[WeeklyCommitRow, ...]
    minimum_weekly_count: int
    maximum_weekly_count: int
    average_weekly_count: float
    unknown_category_count: int

    def to_dict(self) -> dict[str, object]:
        return self.provenance.to_dict() | {
            "weeks": [week.to_dict() for week in self.weeks],
            "minimum_weekly_count": self.minimum_weekly_count,
            "maximum_weekly_count": self.maximum_weekly_count,
            "average_weekly_count": self.average_weekly_count,
            "unknown_category_count": self.unknown_category_count,
        }


def collect_git_distributions(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    history: CommitMetadataSource,
) -> GitDistributionReport:
    resolved = repository.resolve()
    if not resolved.is_dir():
        raise ValueError(f"Repository is not a directory: {resolved}")
    if since_unix_time <= 0:
        raise ValueError("since_unix_time must be positive.")
    if limit <= 0:
        raise ValueError("limit must be positive.")
    commits = history.commit_metadata(
        resolved,
        CommitHistoryQuery(limit=limit, since_unix_time=since_unix_time),
    )
    weeks = _weekly_rows(commits, since_unix_time)
    counts = [week.commit_count for week in weeks]
    categories = [category for week in weeks for category in week.categories]
    return GitDistributionReport(
        provenance=python_history_provenance(
            str(resolved),
            since_unix_time=since_unix_time,
            limit=limit,
            commit_count=len(commits[:limit]),
            truncated=len(commits) > limit,
        ),
        weeks=tuple(weeks),
        minimum_weekly_count=min(counts, default=0),
        maximum_weekly_count=max(counts, default=0),
        average_weekly_count=round(sum(counts) / len(counts), 2) if counts else 0.0,
        unknown_category_count=sum(category.normalized_category is None for category in categories),
    )


def _weekly_rows(commits, since_unix_time: int) -> list[WeeklyCommitRow]:
    since = datetime.fromtimestamp(since_unix_time, tz=UTC).date()
    observed = [
        datetime.fromtimestamp(commit.committed_unix_time, tz=UTC).date() for commit in commits
    ]
    first = _week_start(min(observed, default=since))
    latest = max(
        (_week_start(committed_date) for committed_date in observed),
        default=first,
    )
    grouped: dict[date, list[CommitMessageCategory]] = {}
    for commit in commits:
        committed_date = datetime.fromtimestamp(commit.committed_unix_time, tz=UTC).date()
        week = _week_start(committed_date)
        raw, normalized = _categorize(commit.subject)
        grouped.setdefault(week, []).append(
            CommitMessageCategory(commit.sha, commit.subject, raw, normalized)
        )
    rows: list[WeeklyCommitRow] = []
    cursor = first
    while cursor <= latest:
        rows.append(
            WeeklyCommitRow(
                cursor.isoformat(),
                len(grouped.get(cursor, [])),
                tuple(grouped.get(cursor, [])),
            )
        )
        cursor += timedelta(days=7)
    return rows


def _week_start(value: date) -> date:
    return value - timedelta(days=value.weekday())


def _categorize(subject: str) -> tuple[str | None, str | None]:
    match = _CONVENTIONAL.match(subject)
    if not match:
        return None, None
    raw = match.group("raw").lower()
    return raw, _KNOWN.get(raw)
