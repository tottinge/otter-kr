from otter_kr.operation_registry import OperationRegistry, PythonOperationSpec


def test_registry_finds_an_admitted_operation() -> None:
    analyzer = object()
    registry = OperationRegistry({"python.example": PythonOperationSpec(analyzer)})

    assert registry.find("python.example") == PythonOperationSpec(analyzer)


def test_registry_rejects_an_unknown_operation() -> None:
    registry = OperationRegistry({})

    assert registry.find("python.unknown") is None
