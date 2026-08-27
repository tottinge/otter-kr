"""Evidence-preserving canonicalization of Git-detected rename chains."""

from __future__ import annotations

from dataclasses import replace

from otter_kr.git_ports import CommitFileChange


def canonicalize_file_changes(records: list[CommitFileChange]) -> list[CommitFileChange]:
    """Map older paths onto their newest Git-detected names, newest commit first."""
    aliases: dict[str, str] = {}
    canonical: list[CommitFileChange] = []
    for record in records:
        path = _resolve(aliases, record.path)
        previous_path = record.previous_path
        if previous_path is not None:
            old_path = _resolve(aliases, previous_path)
            aliases[old_path] = path
            previous_path = old_path
        canonical.append(replace(record, path=path, previous_path=previous_path))
    return canonical


def _resolve(aliases: dict[str, str], path: str) -> str:
    while path in aliases and aliases[path] != path:
        path = aliases[path]
    return path
