from pathlib import Path

import pytest

from otter_kr.git_cli_history import GitHistoryValidationError
from otter_kr.git_files import GitFileSourceError
from otter_kr.operation_registry import (
    OperationContext,
    OperationRegistry,
    OperationSpec,
    ResearchRequest,
)
from otter_kr.server import _run_operation, dispatch_research


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


@pytest.mark.parametrize(
    ("error", "code", "echo_request"),
    [
        (GitHistoryValidationError("bad history"), "invalid_query", True),
        (ValueError("bad repository"), "not_a_repository", True),
        (GitFileSourceError(("git",), 1, "failed"), "repository_access_failed", False),
        (None, None, False),
    ],
)
def test_runner_echoes_request_fields_only_for_validation_errors(error, code, echo_request) -> None:
    def analyzer(repository):
        if error is not None:
            raise error
        return {}

    result = _run_operation(
        "python.example",
        "/repo",
        analyzer,
        terms=("count", "limit"),
        query_detail="compact",
        validation_query={"term": "requested", "since_unix_time": 1, "limit": 2},
    )

    query = {"repository_root": "/repo", "terms": ["count", "limit"], "detail": "compact"}
    if echo_request:
        query.update(term="requested", since_unix_time=1, limit=2)
    assert result["query"] == query
    assert result.get("error", {}).get("code") == code
