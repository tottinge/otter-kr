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
    OperationRegistry,
    OperationSpec,
    ResearchRequest,
    VariableClusterOperationSpec,
    VariableClusterQuery,
    VariableOccurrenceQuery,
)
from otter_kr.server import OPERATION_REGISTRY


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
    result = BoundedOperationSpec(analyzer).execute(request, runner)

    assert result == "ran"
    assert calls == [("git.history", "/repo", analyzer, {"since_unix_time": 1, "limit": 2})]


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
