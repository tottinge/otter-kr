"""Pure co-change affinity weighting and accumulation."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass
from itertools import combinations
from math import isfinite


@dataclass(frozen=True, slots=True)
class CochangeAffinityMetadata:
    formula: str
    pair_count_formula: str
    per_pair_formula: str
    invariant: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CochangeWeightingPolicy:
    metadata: CochangeAffinityMetadata
    weight_for_file_count: Callable[[int], float]

    def weight(self, file_count: int) -> float:
        weight = self.weight_for_file_count(file_count)
        if not isfinite(weight) or weight <= 0:
            raise ValueError(f"weight must be positive and finite: {weight}")
        return weight


@dataclass(frozen=True, slots=True)
class CochangeAffinityPair:
    left_path: str
    right_path: str
    score: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CochangeAffinityReport:
    metadata: CochangeAffinityMetadata
    pairs: tuple[CochangeAffinityPair, ...]
    excluded_single_file_commits: int
    eligible_commit_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "metadata": self.metadata.to_dict(),
            "pairs": [pair.to_dict() for pair in self.pairs],
            "excluded_single_file_commits": self.excluded_single_file_commits,
            "eligible_commit_count": self.eligible_commit_count,
        }


DEFAULT_METADATA = CochangeAffinityMetadata(
    formula="1/C(N,2)",
    pair_count_formula="N*(N-1)/2",
    per_pair_formula="2/(N*(N-1))",
    invariant="each_eligible_commit_contributes_one_total_pair_affinity_mass",
)


def normalized_pair_weight(file_count: int) -> float:
    """Return the per-pair mass for one eligible commit."""
    if file_count < 2:
        raise ValueError(f"file_count must be at least 2: {file_count}")
    return 2 / (file_count * (file_count - 1))


DEFAULT_POLICY = CochangeWeightingPolicy(
    metadata=DEFAULT_METADATA,
    weight_for_file_count=normalized_pair_weight,
)


def calculate_cochange_affinity(
    commits: Iterable[Sequence[str]],
    *,
    policy: CochangeWeightingPolicy = DEFAULT_POLICY,
) -> CochangeAffinityReport:
    """Accumulate deterministic file-pair affinity scores across commits."""
    scores: dict[tuple[str, str], float] = {}
    excluded_single_file_commits = 0
    eligible_commit_count = 0

    for commit in commits:
        paths = tuple(sorted(set(commit)))
        if len(paths) < 2:
            if len(paths) == 1:
                excluded_single_file_commits += 1
            continue

        eligible_commit_count += 1
        weight = policy.weight(len(paths))
        for left_path, right_path in combinations(paths, 2):
            key = (left_path, right_path)
            scores[key] = scores.get(key, 0.0) + weight

    return CochangeAffinityReport(
        metadata=policy.metadata,
        pairs=tuple(
            CochangeAffinityPair(left_path=left, right_path=right, score=score)
            for (left, right), score in sorted(scores.items())
        ),
        excluded_single_file_commits=excluded_single_file_commits,
        eligible_commit_count=eligible_commit_count,
    )
