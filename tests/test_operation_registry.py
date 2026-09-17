from otter_kr.operation_registry import (
    BoundedOperationSpec,
    BoundedTermOperationSpec,
    OperationRegistry,
    OperationSpec,
)
from otter_kr.server import OPERATION_REGISTRY


def test_registry_finds_an_admitted_operation() -> None:
    analyzer = object()
    registry = OperationRegistry({"python.example": OperationSpec(analyzer)})

    assert registry.find("python.example") == OperationSpec(analyzer)


def test_registry_rejects_an_unknown_operation() -> None:
    registry = OperationRegistry({})

    assert registry.find("python.unknown") is None


def test_registry_admits_bounded_topic_operations() -> None:
    assert OPERATION_REGISTRY.find("git.topic") is not None
    assert OPERATION_REGISTRY.find("git.topic_hunks") is not None
    assert isinstance(OPERATION_REGISTRY.find("git.topic_walk"), BoundedTermOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.topic_family"), BoundedTermOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.history"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.snapshot"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.distributions"), BoundedOperationSpec)
    assert isinstance(OPERATION_REGISTRY.find("git.hotspots"), BoundedOperationSpec)
