from otter_kr.operation_registry import (
    BoundedOperationSpec,
    BoundedPairOperationSpec,
    BoundedPairQuery,
    BoundedPathOperationSpec,
    BoundedPathQuery,
    BoundedTermOperationSpec,
    CarrierGuardsOperationSpec,
    CarrierGuardsQuery,
    LifecycleOperationSpec,
    LifecycleQuery,
    LineOriginsOperationSpec,
    LineOriginsQuery,
    OperationContext,
    OperationRegistry,
    OperationSpec,
    ResearchRequest,
    VariableClusterOperationSpec,
    VariableClusterQuery,
    VariableOccurrenceQuery,
)
from otter_kr.server import OPERATION_REGISTRY


def execution_context(
    runner,
    *,
    bounded=None,
    reject=None,
    unimplemented=None,
) -> OperationContext:
    return OperationContext(
        run=runner,
        query_run=runner,
        bounded=bounded or runner,
        reject=reject or runner,
        unimplemented=unimplemented or runner,
    )


def test_registry_finds_an_admitted_operation() -> None:
    analyzer = object()
    registry = OperationRegistry({"python.example": OperationSpec(analyzer)})

    assert registry.find("python.example") == OperationSpec(analyzer)


def test_registry_rejects_an_unknown_operation() -> None:
    registry = OperationRegistry({})

    assert registry.find("python.unknown") is None


def test_research_request_develops_the_transport_argument_boundary() -> None:
    request = ResearchRequest.create(
        "/repo",
        "python.variable_cluster",
        term="count",
        terms=["count", "limit"],
        since_unix_time=1,
        limit=2,
        left_path="src/a.py",
        right_path="src/b.py",
        path="src/a.py",
        lines=[3, 5],
    )

    assert request == ResearchRequest(
        "/repo",
        "python.variable_cluster",
        "count",
        ("count", "limit"),
        1,
        2,
        "src/a.py",
        "src/b.py",
        "src/a.py",
        (3, 5),
    )


def test_bounded_pair_query_develops_its_validation_boundary() -> None:
    query = BoundedPairQuery.create("src/a.py", "src/b.py", 1, 2)

    assert query == BoundedPairQuery("src/a.py", "src/b.py", 1, 2)


def test_bounded_path_query_develops_its_validation_boundary() -> None:
    query = BoundedPathQuery.create(
        "src/a.py",
        1,
        2,
        operation="git.cochange.file",
        term_message="term",
        path_message="path",
    )

    assert query == BoundedPathQuery("src/a.py", 1, 2)


def test_bounded_operation_spec_owns_its_execution_shape() -> None:
    calls: list[tuple[object, ...]] = []
    analyzer = object()

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    request = ResearchRequest.create("/repo", "git.history", since_unix_time=1, limit=2)
    result = BoundedOperationSpec(analyzer).execute(request, execution_context(runner))

    assert result == "ran"
    assert calls == [("git.history", "/repo", analyzer, {"since_unix_time": 1, "limit": 2})]


def test_bounded_term_operation_spec_owns_term_admission() -> None:
    calls: list[tuple[object, ...]] = []
    analyzer = object()

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    def reject(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "rejected"

    request = ResearchRequest.create("/repo", "git.topic_walk", term="HEAD", limit=2)
    context = execution_context(runner, reject=reject)
    result = BoundedTermOperationSpec(analyzer, "commit required").execute(request, context)

    assert result == "ran"
    assert calls == [
        (
            "git.topic_walk",
            "/repo",
            analyzer,
            {"term": "HEAD", "since_unix_time": None, "limit": 2, "pass_bounds_with_term": True},
        )
    ]

    rejected = BoundedTermOperationSpec(analyzer, "commit required").execute(
        ResearchRequest.create("/repo", "git.topic_walk"), context
    )

    assert rejected == "rejected"
    assert calls[-1] == ("git.topic_walk", "/repo", "commit required", {})


def test_bounded_path_operation_spec_owns_path_admission() -> None:
    calls: list[tuple[object, ...]] = []
    analyzer = object()

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    def reject(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "rejected"

    request = ResearchRequest.create(
        "/repo", "git.cochange.file", term="src/a.py", since_unix_time=1, limit=2
    )
    result = BoundedPathOperationSpec(analyzer, "path required", "path invalid").execute(
        request, execution_context(runner, reject=reject)
    )

    assert result == "ran"
    assert calls == [
        (
            "git.cochange.file",
            "/repo",
            analyzer,
            {
                "term": "src/a.py",
                "since_unix_time": 1,
                "limit": 2,
                "pass_bounds_with_term": True,
            },
        )
    ]


def test_bounded_pair_operation_spec_owns_pair_admission() -> None:
    calls: list[tuple[object, ...]] = []
    analyzer = object()

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    def reject(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "rejected"

    request = ResearchRequest.create(
        "/repo",
        "git.cochange.pair",
        left_path="src/a.py",
        right_path="src/b.py",
        since_unix_time=1,
        limit=2,
    )
    result = BoundedPairOperationSpec(analyzer).execute(
        request, execution_context(runner, reject=reject)
    )

    assert result == "ran"
    assert calls == [
        (
            "git.cochange.pair",
            "/repo",
            analyzer,
            {
                "since_unix_time": 1,
                "limit": 2,
                "left_path": "src/a.py",
                "right_path": "src/b.py",
                "pass_pair_paths": True,
            },
        )
    ]


def test_line_origins_operation_spec_owns_query_admission() -> None:
    calls: list[tuple[object, ...]] = []
    analyzer = object()

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    def reject(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "rejected"

    request = ResearchRequest.create(
        "/repo", "git.line_origins", term="HEAD", path="src/a.py", lines=[3, 5]
    )
    result = LineOriginsOperationSpec(analyzer).execute(
        request, execution_context(runner, reject=reject)
    )

    assert result == "ran"
    assert calls[0][0:3] == ("git.line_origins", "/repo", analyzer)
    assert calls[0][3]["term"] == "HEAD"
    assert calls[0][3]["query_object"] == LineOriginsQuery("HEAD", "src/a.py", (3, 5))


def test_lifecycle_operation_spec_owns_optional_bounds() -> None:
    calls: list[tuple[object, ...]] = []
    analyzer = object()

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    def bounded_runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "bounded"

    def reject(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "rejected"

    result = LifecycleOperationSpec(analyzer).execute(
        ResearchRequest.create("/repo", "python.object_lifecycle", term="state"),
        execution_context(runner, bounded=bounded_runner, reject=reject),
    )

    assert result == "ran"
    assert calls == [("python.object_lifecycle", "/repo", analyzer, {"term": "state"})]

    bounded = LifecycleOperationSpec(analyzer).execute(
        ResearchRequest.create(
            "/repo", "python.object_lifecycle", term="state", since_unix_time=1, limit=2
        ),
        execution_context(runner, bounded=bounded_runner, reject=reject),
    )

    assert bounded == "bounded"
    assert calls[-1] == (
        "python.object_lifecycle",
        "/repo",
        analyzer,
        {
            "term": "state",
            "since_unix_time": 1,
            "limit": 2,
            "term_required": True,
            "pass_bounds_with_term": True,
        },
    )


def test_carrier_guards_operation_spec_owns_path_scope() -> None:
    calls: list[tuple[object, ...]] = []

    def analyzer(repository: object, carrier: str, *, paths: tuple[str, ...] | None) -> str:
        calls.append((repository, carrier, paths))
        return "evidence"

    def runner(*args: object, **kwargs: object) -> str:
        result = args[2]("/repo", kwargs["term"])
        calls.append((*args[:2], result))
        return "ran"

    def reject(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "rejected"

    result = CarrierGuardsOperationSpec(analyzer).execute(
        ResearchRequest.create(
            "/repo", "python.carrier_guards", term="state", path="src/service.py"
        ),
        execution_context(runner, reject=reject),
    )

    assert result == "ran"
    assert calls == [
        ("/repo", "state", ("src/service.py",)),
        ("python.carrier_guards", "/repo", "evidence"),
    ]


def test_variable_cluster_operation_spec_owns_both_query_forms() -> None:
    calls: list[tuple[object, ...]] = []
    cluster_analyzer = object()
    occurrence_analyzer = object()

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    def reject(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "rejected"

    def unimplemented(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "unimplemented"

    spec = VariableClusterOperationSpec(cluster_analyzer, occurrence_analyzer)
    cluster = spec.execute(
        ResearchRequest.create(
            "/repo", "python.variable_cluster", terms=["count", "limit"], limit=2
        ),
        execution_context(runner, reject=reject, unimplemented=unimplemented),
    )
    assert cluster == "ran"
    assert calls[-1] == (
        "python.variable_cluster",
        "/repo",
        cluster_analyzer,
        {
            "terms": ("count", "limit"),
            "query_terms": ("count", "limit"),
            "since_unix_time": None,
            "limit": 2,
            "pass_bounds_with_terms": True,
        },
    )

    occurrence = spec.execute(
        ResearchRequest.create("/repo", "python.variable_cluster", term="count"),
        execution_context(runner, reject=reject, unimplemented=unimplemented),
    )
    assert occurrence == "ran"
    assert calls[-1] == ("python.variable_cluster", "/repo", occurrence_analyzer, {"term": "count"})

    assert (
        spec.execute(
            ResearchRequest.create("/repo", "python.variable_cluster"),
            execution_context(runner, reject=reject, unimplemented=unimplemented),
        )
        == "unimplemented"
    )


def test_operation_spec_owns_term_and_envelope_policy() -> None:
    analyzer = object()
    calls: list[tuple[object, ...]] = []

    def runner(*args: object, **kwargs: object) -> str:
        calls.append((*args, kwargs))
        return "ran"

    result = OperationSpec(analyzer, requires_term=True, term_message="term required").execute(
        ResearchRequest.create(
            "/repo",
            "python.names",
            term="count",
            since_unix_time=1,
            limit=2,
            left_path="src/a.py",
            right_path="src/b.py",
        ),
        execution_context(runner),
    )

    assert result == "ran"
    assert calls == [
        (
            analyzer,
            {
                "term": "count",
                "require_term": True,
                "term_message": "term required",
                "catches_value_error": True,
            },
        )
    ]


def test_line_origins_query_develops_its_validation_boundary() -> None:
    query = LineOriginsQuery.create("HEAD", "src/a.py", [1, 2])

    assert query == LineOriginsQuery("HEAD", "src/a.py", (1, 2))


def test_variable_cluster_query_develops_its_validation_boundary() -> None:
    query = VariableClusterQuery.create(["count", "limit"], 1, 2)

    assert query == VariableClusterQuery(("count", "limit"), 1, 2)


def test_variable_occurrence_query_develops_its_validation_boundary() -> None:
    query = VariableOccurrenceQuery.create("count")

    assert query == VariableOccurrenceQuery("count")


def test_lifecycle_query_develops_its_validation_boundary() -> None:
    query = LifecycleQuery.create("state", 1, 2)

    assert query == LifecycleQuery("state", 1, 2)


def test_carrier_guards_query_develops_its_path_boundary() -> None:
    query = CarrierGuardsQuery.create("state", "pkg/service.py")

    assert query == CarrierGuardsQuery("state", ("pkg/service.py",))


def test_registry_admits_bounded_topic_operations() -> None:
    assert OPERATION_REGISTRY.find("git.topic") is not None
    assert OPERATION_REGISTRY.find("git.topic_hunks") is not None
    assert isinstance(OPERATION_REGISTRY.find("git.topic_walk"), BoundedTermOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.topic_family"), BoundedTermOperationSpec)
    assert isinstance(
        OPERATION_REGISTRY.find("python.term_change_evidence"), BoundedTermOperationSpec
    )
    assert isinstance(
        OPERATION_REGISTRY.find("python.representation_inventory"), BoundedOperationSpec
    )
    assert isinstance(OPERATION_REGISTRY.find("git.review_packet"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.history"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.snapshot"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.distributions"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.hotspots"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.cochange"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.cochange.file"), BoundedPathOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.branch_additions"), BoundedPathOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("python.object_lifecycle"), LifecycleOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("python.carrier_guards"), CarrierGuardsOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.line_origins"), LineOriginsOperationSpec)
    assert isinstance(
        OPERATION_REGISTRY.find("python.variable_cluster"), VariableClusterOperationSpec
    )
    assert isinstance(OPERATION_REGISTRY.find("git.cochange.pair"), BoundedPairOperationSpec)
