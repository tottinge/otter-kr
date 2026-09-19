"""Composite, measurement-only representation evidence."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.evidence_context import EvidenceContext
from otter_kr.git_branch_growth import collect_branch_additions
from otter_kr.git_distributions import collect_git_distributions
from otter_kr.git_files import GitCliFileSource
from otter_kr.git_hotspots import collect_git_hotspots
from otter_kr.git_ownership import collect_git_ownership
from otter_kr.python_duplicates import find_duplicate_helpers
from otter_kr.python_groups import find_repeated_groups


@dataclass(frozen=True, slots=True)
class RepresentationInventory:
    hotspots: dict[str, object]
    duplicates: dict[str, object]
    repeated_groups: dict[str, object]
    distributions: dict[str, object]
    branch_growth: dict[str, object]
    ownership: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "hotspots": self.hotspots,
            "duplicates": self.duplicates,
            "repeated_groups": self.repeated_groups,
            "distributions": self.distributions,
            "branch_growth": self.branch_growth,
            "ownership": self.ownership,
        }


def collect_representation_inventory(
    repository: Path,
    *,
    since_unix_time: int,
    limit: int,
    paths: tuple[str, ...] | None = None,
) -> RepresentationInventory:
    context = EvidenceContext.from_git()
    python_files = GitCliFileSource().python_files(repository.resolve())
    selected_paths = set(paths) if paths is not None else None
    if selected_paths is not None:
        python_files = [
            path
            for path in python_files
            if path.relative_to(repository.resolve()).as_posix() in selected_paths
        ]
    branch_reports = tuple(
        collect_branch_additions(
            repository,
            path.relative_to(repository.resolve()).as_posix(),
            since_unix_time=since_unix_time,
            limit=limit,
            history=context.metadata,
            patches=context.history,
        )
        for path in python_files
    )
    hotspots = collect_git_hotspots(
        repository, since_unix_time=since_unix_time, limit=limit, changes=context.changes
    ).to_dict()
    duplicates = find_duplicate_helpers(repository).to_dict()
    repeated_groups = find_repeated_groups(repository).to_dict()
    if selected_paths is not None:
        hotspots["files"] = [item for item in hotspots["files"] if item["path"] in selected_paths]
        duplicates["groups"] = [
            group
            for group in duplicates["groups"]
            if any(item["path"] in selected_paths for item in group["occurrences"])
        ]
        duplicates["pairs"] = [
            pair
            for pair in duplicates["pairs"]
            if pair["left"]["path"] in selected_paths or pair["right"]["path"] in selected_paths
        ]
        repeated_groups["groups"] = [
            group
            for group in repeated_groups["groups"]
            if any(item["path"] in selected_paths for item in group["occurrences"])
        ]
    return RepresentationInventory(
        hotspots=hotspots,
        duplicates=duplicates,
        repeated_groups=repeated_groups,
        distributions=collect_git_distributions(
            repository, since_unix_time=since_unix_time, limit=limit, history=context.metadata
        ).to_dict(),
        branch_growth={
            "file_count": len(branch_reports),
            "branch_addition_count": sum(len(report.events) for report in branch_reports),
            "files": [report.to_dict() for report in branch_reports],
        },
        ownership=collect_git_ownership(
            repository, since_unix_time=since_unix_time, limit=limit, history=context.metadata
        ).to_dict(),
    )
