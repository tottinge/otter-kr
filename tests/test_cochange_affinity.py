import pytest

from otter_kr.cochange_affinity import (
    DEFAULT_POLICY,
    CochangeAffinityMetadata,
    CochangeAffinityPair,
    CochangeWeightingPolicy,
    calculate_cochange_affinity,
    normalized_pair_weight,
)


def test_two_file_commit_contributes_one_total_pair_mass() -> None:
    report = calculate_cochange_affinity([("pkg/a.py", "pkg/b.py")])

    assert report.metadata.to_dict() == {
        "formula": "1/C(N,2)",
        "pair_count_formula": "N*(N-1)/2",
        "per_pair_formula": "2/(N*(N-1))",
        "invariant": "each_eligible_commit_contributes_one_total_pair_affinity_mass",
    }
    assert report.excluded_single_file_commits == 0
    assert report.eligible_commit_count == 1
    assert report.pairs == (
        CochangeAffinityPair(
            left_path="pkg/a.py",
            right_path="pkg/b.py",
            score=pytest.approx(1.0),
        ),
    )


def test_three_file_commit_splits_weight_evenly_across_pairs() -> None:
    report = calculate_cochange_affinity([("pkg/c.py", "pkg/a.py", "pkg/b.py")])

    assert [pair.to_dict() for pair in report.pairs] == [
        {"left_path": "pkg/a.py", "right_path": "pkg/b.py", "score": pytest.approx(1 / 3)},
        {"left_path": "pkg/a.py", "right_path": "pkg/c.py", "score": pytest.approx(1 / 3)},
        {"left_path": "pkg/b.py", "right_path": "pkg/c.py", "score": pytest.approx(1 / 3)},
    ]


def test_broad_ten_file_commit_is_heavily_diluted_per_pair() -> None:
    files = tuple(f"pkg/{index:02}.py" for index in range(10))

    report = calculate_cochange_affinity([files])

    assert len(report.pairs) == 45
    assert report.pairs[0].score == pytest.approx(1 / 45)
    assert report.pairs[-1].score == pytest.approx(1 / 45)
    assert sum(pair.score for pair in report.pairs) == pytest.approx(1.0)


def test_single_file_commits_are_excluded_and_counted() -> None:
    report = calculate_cochange_affinity(
        [
            ("pkg/a.py",),
            ("pkg/b.py", "pkg/c.py"),
            ("pkg/c.py",),
        ]
    )

    assert report.excluded_single_file_commits == 2
    assert report.eligible_commit_count == 1
    assert [pair.to_dict() for pair in report.pairs] == [
        {"left_path": "pkg/b.py", "right_path": "pkg/c.py", "score": pytest.approx(1.0)}
    ]


def test_duplicate_paths_in_one_commit_do_not_create_duplicate_pairs() -> None:
    report = calculate_cochange_affinity([("pkg/b.py", "pkg/a.py", "pkg/a.py", "pkg/b.py")])

    assert [pair.to_dict() for pair in report.pairs] == [
        {"left_path": "pkg/a.py", "right_path": "pkg/b.py", "score": pytest.approx(1.0)}
    ]


def test_scores_accumulate_across_commits() -> None:
    report = calculate_cochange_affinity(
        [
            ("pkg/a.py", "pkg/b.py"),
            ("pkg/c.py", "pkg/a.py", "pkg/b.py"),
            ("pkg/a.py", "pkg/b.py"),
        ]
    )

    assert [pair.to_dict() for pair in report.pairs] == [
        {"left_path": "pkg/a.py", "right_path": "pkg/b.py", "score": pytest.approx(7 / 3)},
        {"left_path": "pkg/a.py", "right_path": "pkg/c.py", "score": pytest.approx(1 / 3)},
        {"left_path": "pkg/b.py", "right_path": "pkg/c.py", "score": pytest.approx(1 / 3)},
    ]


def test_injected_policy_controls_weighting_and_metadata() -> None:
    metadata = CochangeAffinityMetadata(
        formula="custom",
        pair_count_formula="unused",
        per_pair_formula="0.25",
        invariant="test_only",
    )
    policy = CochangeWeightingPolicy(
        metadata=metadata,
        weight_for_file_count=lambda file_count: 0.25 * file_count,
    )

    report = calculate_cochange_affinity([("pkg/a.py", "pkg/b.py", "pkg/c.py")], policy=policy)

    assert report.metadata == metadata
    assert [pair.to_dict() for pair in report.pairs] == [
        {"left_path": "pkg/a.py", "right_path": "pkg/b.py", "score": pytest.approx(0.75)},
        {"left_path": "pkg/a.py", "right_path": "pkg/c.py", "score": pytest.approx(0.75)},
        {"left_path": "pkg/b.py", "right_path": "pkg/c.py", "score": pytest.approx(0.75)},
    ]


def test_default_policy_exposes_normalized_metadata() -> None:
    assert DEFAULT_POLICY.metadata.to_dict() == {
        "formula": "1/C(N,2)",
        "pair_count_formula": "N*(N-1)/2",
        "per_pair_formula": "2/(N*(N-1))",
        "invariant": "each_eligible_commit_contributes_one_total_pair_affinity_mass",
    }


def test_normalized_pair_weight_rejects_invalid_counts() -> None:
    with pytest.raises(ValueError, match="file_count must be at least 2"):
        normalized_pair_weight(0)

    with pytest.raises(ValueError, match="file_count must be at least 2"):
        normalized_pair_weight(1)
