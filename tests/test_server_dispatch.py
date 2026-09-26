from pathlib import Path

from otter_kr.operation_registry import (
    OperationContext,
    OperationRegistry,
    OperationSpec,
    ResearchRequest,
)
from otter_kr.server import dispatch_research


def test_dispatch_research_admits_a_registry_entry_without_dispatcher_changes() -> None:
    def analyzer(repository: Path) -> dict[str, str]:
        return {"repository": str(repository)}

    def run(*args: object, **kwargs: object) -> dict[str, bool]:
        return {"executed": True}

    context = OperationContext(
        run=run,
        query_run=run,
        bounded=run,
        reject=run,
        unimplemented=run,
    )
    registry = OperationRegistry({"python.example": OperationSpec(analyzer)})

    result = dispatch_research(ResearchRequest.create("/repo", "python.example"), registry, context)

    assert result == {"executed": True}
