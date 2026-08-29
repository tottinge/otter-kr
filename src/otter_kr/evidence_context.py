"""Shared capability context for composite evidence collectors."""

from dataclasses import dataclass

from otter_kr.git_cli_history import GitCliHistory
from otter_kr.git_ports import CommitFileChangeSource, CommitMetadataSource


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    history: GitCliHistory

    @classmethod
    def from_git(cls) -> "EvidenceContext":
        return cls(GitCliHistory())

    @property
    def changes(self) -> CommitFileChangeSource:
        return self.history

    @property
    def metadata(self) -> CommitMetadataSource:
        return self.history
