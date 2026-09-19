"""Shared lexical identity rules for Python evidence analyzers."""

from __future__ import annotations

import re
from pathlib import Path

_CAMEL_CASE_TRANSITION_PATTERN = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")
_NON_IDENTIFIER_CHARACTER_PATTERN = re.compile(r"[^A-Za-z0-9]+")


def identifier_words(identifier: str) -> tuple[str, ...]:
    """Split an identifier into case-folded lexical words."""
    lexical_form = _CAMEL_CASE_TRANSITION_PATTERN.sub("_", identifier)
    return tuple(
        word.casefold() for word in _NON_IDENTIFIER_CHARACTER_PATTERN.split(lexical_form) if word
    )


def module_name(relative_path: Path) -> str:
    """Represent a repository-relative Python path as an import module name."""
    parts = list(relative_path.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)
