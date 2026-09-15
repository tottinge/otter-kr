"""Evidence-preserving canonicalization of Git-detected rename chains."""

from __future__ import annotations

from dataclasses import replace

from otter_kr.git_ports import CommitFileChange


class PathAliases:
    """Resolve Git rename chains to their newest known path."""

    def __init__(self) -> None:
        self._aliases: dict[str, str] = {}

    def bind(self, old_path: str, current_path: str) -> None:
        """Record that ``old_path`` was renamed to ``current_path``."""
        self._aliases[old_path] = current_path

    def resolve(self, path: str) -> str:
        """Return the newest path known for ``path``."""
        while path in self._aliases and self._aliases[path] != path:
            path = self._aliases[path]
        return path


def canonicalize_file_changes(records: list[CommitFileChange]) -> list[CommitFileChange]:
    """Map older paths onto their newest Git-detected names, newest commit first."""
    aliases = PathAliases()
    canonical: list[CommitFileChange] = []
    for record in records:
        path = aliases.resolve(record.path)
        previous_path = record.previous_path
        if previous_path is not None:
            old_path = aliases.resolve(previous_path)
            aliases.bind(old_path, path)
            previous_path = old_path
        canonical.append(replace(record, path=path, previous_path=previous_path))
    return canonical
