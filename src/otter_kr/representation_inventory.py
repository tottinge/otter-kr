"""Composite, measurement-only representation evidence."""

from dataclasses import dataclass
from pathlib import Path

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_distributions import collect_git_distributions
from otter_kr.git_hotspots import collect_git_hotspots
from otter_kr.python_duplicates import find_duplicate_helpers
from otter_kr.python_groups import find_repeated_groups


@dataclass(frozen=True, slots=True)
class RepresentationInventory:
    hotspots: dict[str, object]
    duplicates: dict[str, object]
    repeated_groups: dict[str, object]
    distributions: dict[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "hotspots": self.hotspots,
            "duplicates": self.duplicates,
            "repeated_groups": self.repeated_groups,
            "distributions": self.distributions,
        }


def collect_representation_inventory(
    repository: Path, *, since_unix_time: int, limit: int
) -> RepresentationInventory:
    history = GitCliHistory()
    return RepresentationInventory(
        hotspots=collect_git_hotspots(
            repository, since_unix_time=since_unix_time, limit=limit, changes=history
        ).to_dict(),
        duplicates=find_duplicate_helpers(repository).to_dict(),
        repeated_groups=find_repeated_groups(repository).to_dict(),
        distributions=collect_git_distributions(
            repository, since_unix_time=since_unix_time, limit=limit, history=history
        ).to_dict(),
    )
