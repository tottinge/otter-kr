from otter_kr.operation_registry import OperationRegistry, OperationSpec
from otter_kr.server import OPERATION_REGISTRY


def test_registry_finds_an_admitted_operation() -> None:
    analyzer = object()
    registry = OperationRegistry({"python.example": OperationSpec(analyzer)})

    assert registry.find("python.example") == OperationSpec(analyzer)


def test_registry_rejects_an_unknown_operation() -> None:
    registry = OperationRegistry({})

    assert registry.find("python.unknown") is None


def test_git_topic_is_the_only_admitted_git_topic_operation() -> None:
    assert OPERATION_REGISTRY.find("git.topic") is not None
    assert OPERATION_REGISTRY.find("git.topic_hunks") is None
    assert OPERATION_REGISTRY.find("git.topic_walk") is None
    assert OPERATION_REGISTRY.find("git.topic_family") is None
