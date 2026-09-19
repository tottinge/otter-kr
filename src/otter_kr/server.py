"""FastMCP transport for repository evidence tools."""

from pathlib import Path

from fastmcp import FastMCP
from mcp.types import ToolAnnotations

from otter_kr.change_evidence import collect_term_change_evidence
from otter_kr.evidence_envelope import EvidenceEnvelope
from otter_kr.git_branch_growth import collect_branch_additions
from otter_kr.git_cli_history import GitCliHistory, GitHistoryValidationError
from otter_kr.git_cochange import collect_global_cochange
from otter_kr.git_distributions import collect_git_distributions
from otter_kr.git_files import GitFileSourceError
from otter_kr.git_history_context import collect_git_history
from otter_kr.git_history_snapshot import collect_git_history_snapshot
from otter_kr.git_hotspots import collect_git_hotspots
from otter_kr.git_hunk_family import collect_topic_family
from otter_kr.git_hunks import collect_topic_hunks
from otter_kr.git_pair_cochange import collect_pair_cochange
from otter_kr.git_scoped_cochange import collect_scoped_cochange
from otter_kr.git_topic import describe_topic_commit
from otter_kr.git_topic_walk import walk_topic_history
from otter_kr.operation_registry import (
    BoundedOperationSpec,
    BoundedPairOperationSpec,
    BoundedPathOperationSpec,
    BoundedTermOperationSpec,
    CarrierGuardsOperationSpec,
    LifecycleOperationSpec,
    LineOriginsOperationSpec,
    OperationContext,
    OperationRegistry,
    OperationSpec,
    ResearchRequest,
    VariableClusterOperationSpec,
)
from otter_kr.python_behavioral_neighborhood import find_behavioral_neighborhood
from otter_kr.python_carrier_guards import find_carrier_guards
from otter_kr.python_complexity import analyze_python_complexity
from otter_kr.python_discriminations import find_type_discriminations
from otter_kr.python_duplicates import find_duplicate_helpers
from otter_kr.python_graph import build_python_import_graph
from otter_kr.python_groups import find_repeated_groups
from otter_kr.python_historical_neighborhood import find_historical_neighborhood
from otter_kr.python_imports import import_python
from otter_kr.python_inventory import inventory_python
from otter_kr.python_literals import find_repeated_literals
from otter_kr.python_names import find_names
from otter_kr.python_neighborhood import find_python_neighborhood
from otter_kr.python_object_lifecycle import find_object_lifecycle
from otter_kr.python_structural_neighborhood import find_structural_neighborhood
from otter_kr.python_tests import find_tests_for_symbol
from otter_kr.python_variable_cluster import find_variable_cluster, find_variable_occurrences
from otter_kr.representation_inventory import collect_representation_inventory
from otter_kr.review_packet import collect_review_packet
from otter_kr.seed_evidence import project_python_neighborhood

OPERATION_REGISTRY = OperationRegistry(
    {
        "git.topic": OperationSpec(
            describe_topic_commit,
            requires_term=True,
            term_message="A commit reference is required for git.topic.",
            echo_unused_query_fields=False,
        ),
        "git.topic_hunks": OperationSpec(
            collect_topic_hunks,
            requires_term=True,
            term_message="A commit reference is required for git.topic_hunks.",
            echo_unused_query_fields=False,
        ),
        "git.topic_walk": BoundedTermOperationSpec(
            walk_topic_history,
            term_message="A commit reference is required for git.topic_walk.",
        ),
        "git.topic_family": BoundedTermOperationSpec(
            collect_topic_family,
            term_message="A commit reference is required for git.topic_family.",
        ),
        "python.term_change_evidence": BoundedTermOperationSpec(
            collect_term_change_evidence,
            term_message="A term is required.",
        ),
        "python.representation_inventory": BoundedOperationSpec(
            collect_representation_inventory,
        ),
        "git.review_packet": BoundedOperationSpec(collect_review_packet),
        "git.history": BoundedOperationSpec(
            lambda repository, *, since_unix_time, limit: collect_git_history(
                repository,
                since_unix_time=since_unix_time,
                limit=limit,
                history=GitCliHistory(),
            )
        ),
        "git.snapshot": BoundedOperationSpec(
            lambda repository, *, since_unix_time, limit: collect_git_history_snapshot(
                repository,
                since_unix_time=since_unix_time,
                limit=limit,
                changes=GitCliHistory(),
            )
        ),
        "git.distributions": BoundedOperationSpec(
            lambda repository, *, since_unix_time, limit: collect_git_distributions(
                repository,
                since_unix_time=since_unix_time,
                limit=limit,
                history=GitCliHistory(),
            )
        ),
        "git.hotspots": BoundedOperationSpec(
            lambda repository, *, since_unix_time, limit: collect_git_hotspots(
                repository,
                since_unix_time=since_unix_time,
                limit=limit,
                changes=GitCliHistory(),
            )
        ),
        "git.cochange": BoundedOperationSpec(
            lambda repository, *, since_unix_time, limit: collect_global_cochange(
                repository,
                since_unix_time=since_unix_time,
                limit=limit,
                changes=GitCliHistory(),
            )
        ),
        "git.cochange.file": BoundedPathOperationSpec(
            lambda repository, focus_path, *, since_unix_time, limit: collect_scoped_cochange(
                repository,
                focus_path,
                since_unix_time=since_unix_time,
                limit=limit,
                changes=GitCliHistory(),
            ),
            term_message="A focus file term is required for git.cochange.file.",
            path_message="focus_path must be repository-relative.",
        ),
        "git.branch_additions": BoundedPathOperationSpec(
            lambda repository, path, *, since_unix_time, limit: collect_branch_additions(
                repository,
                path,
                since_unix_time=since_unix_time,
                limit=limit,
                history=GitCliHistory(),
                patches=GitCliHistory(),
            ),
            term_message="A Python file path is required for git.branch_additions.",
            path_message="path must be a repository-relative path without '..'.",
        ),
        "git.line_origins": LineOriginsOperationSpec(
            lambda repository, query: {
                "revision": query.revision,
                "path": query.path,
                "origins": [
                    origin.__dict__
                    if hasattr(origin, "__dict__")
                    else {
                        "path": origin.path,
                        "line": origin.line,
                        "text": origin.text,
                        "origin_commit": origin.origin_commit,
                        "status": origin.status,
                    }
                    for origin in GitCliHistory().line_origins(
                        repository, query.path, query.revision, query.lines
                    )
                ],
            }
        ),
        "python.variable_cluster": VariableClusterOperationSpec(
            cluster_analyzer=find_variable_cluster,
            occurrence_analyzer=find_variable_occurrences,
        ),
        "python.object_lifecycle": LifecycleOperationSpec(find_object_lifecycle),
        "python.carrier_guards": CarrierGuardsOperationSpec(find_carrier_guards),
        "git.cochange.pair": BoundedPairOperationSpec(
            lambda repository,
            *,
            left_path,
            right_path,
            since_unix_time,
            limit: collect_pair_cochange(
                repository,
                left_path,
                right_path,
                since_unix_time=since_unix_time,
                limit=limit,
                changes=GitCliHistory(),
            ),
        ),
        "python.inventory": OperationSpec(inventory_python),
        "python.names": OperationSpec(
            find_names, requires_term=True, term_message="A term is required for python.names."
        ),
        "python.neighborhood": OperationSpec(
            find_python_neighborhood,
            requires_term=True,
            term_message="A seed is required for python.neighborhood.",
        ),
        "python.neighborhood.structural": OperationSpec(
            find_structural_neighborhood,
            requires_term=True,
            term_message="A seed is required for python.neighborhood.structural.",
        ),
        "python.neighborhood.historical": BoundedTermOperationSpec(
            find_historical_neighborhood,
            term_message="A seed is required for python.neighborhood.historical.",
        ),
        "python.neighborhood.behavioral": OperationSpec(
            find_behavioral_neighborhood,
            requires_term=True,
            term_message="A seed is required for python.neighborhood.behavioral.",
        ),
        "python.seed_evidence": OperationSpec(
            project_python_neighborhood,
            requires_term=True,
            term_message="A seed is required for python.seed_evidence.",
        ),
        "python.graph_topology": OperationSpec(build_python_import_graph),
        "python.discriminations": OperationSpec(
            find_type_discriminations,
            requires_term=True,
            term_message="A term is required for python.discriminations.",
        ),
        "python.tests": OperationSpec(
            find_tests_for_symbol,
            requires_term=True,
            term_message="A term is required for python.tests.",
        ),
        "python.imports": OperationSpec(import_python),
        "python.complexity": OperationSpec(analyze_python_complexity, catches_value_error=False),
        "python.literals": OperationSpec(find_repeated_literals),
        "python.groups": OperationSpec(find_repeated_groups),
        "python.duplicates": OperationSpec(find_duplicate_helpers),
    }
)


def _query(
    repository_root: str,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
    terms: list[str] | tuple[str, ...] | None = None,
) -> dict:
    query = {"repository_root": repository_root}
    if term is not None:
        query["term"] = term
    if terms is not None:
        query["terms"] = list(terms)
    if since_unix_time is not None:
        query["since_unix_time"] = since_unix_time
    if limit is not None:
        query["limit"] = limit
    if left_path is not None:
        query["left_path"] = left_path
    if right_path is not None:
        query["right_path"] = right_path
    return query


def _success(
    operation: str,
    repository_root: str,
    data: dict,
    term: str | None = None,
    terms: list[str] | tuple[str, ...] | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return EvidenceEnvelope(
        operation,
        _query(
            repository_root,
            term,
            since_unix_time,
            limit,
            left_path,
            right_path,
            terms,
        ),
        data,
    ).to_dict()


def _invalid_query(
    operation: str,
    repository_root: str,
    message: str,
    *,
    term: str | None = None,
    terms: list[str] | tuple[str, ...] | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(
            repository_root,
            term,
            since_unix_time,
            limit,
            left_path,
            right_path,
            terms,
        ),
        "error": {
            "code": "invalid_query",
            "message": message,
        },
    }


def _not_implemented(operation: str, repository_root: str) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root),
        "error": {
            "code": "not_implemented",
            "message": "Variable-cluster evidence has not been admitted yet.",
        },
    }


def _not_admitted(operation: str, repository_root: str) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(repository_root),
        "error": {
            "code": "not_implemented",
            "message": "No repository research capabilities have been admitted yet.",
        },
    }


def dispatch_research(
    request: ResearchRequest,
    registry: OperationRegistry,
    context: OperationContext,
) -> dict:
    """Dispatch one normalized request through an injectable registry."""
    spec = registry.find(request.operation)
    if spec is None:
        return _not_admitted(request.operation, request.repository_root)
    return spec.execute(request, context)


def _not_a_repository(
    operation: str,
    repository_root: str,
    error: ValueError,
    term: str | None = None,
    terms: tuple[str, ...] | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(
            repository_root, term, since_unix_time, limit, left_path, right_path, terms
        ),
        "error": {
            "code": "not_a_repository",
            "message": str(error),
        },
    }


def _repository_access_failed(
    operation: str,
    repository_root: str,
    error: GitFileSourceError,
    term: str | None = None,
    terms: tuple[str, ...] | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    return {
        "schema_version": "1",
        "status": "rejected",
        "operation": operation,
        "query": _query(
            repository_root, term, since_unix_time, limit, left_path, right_path, terms
        ),
        "error": {
            "code": "repository_access_failed",
            "message": str(error),
            "command": list(error.command),
            "returncode": error.returncode,
            "stderr": error.stderr,
        },
    }


def _validate_history_bounds(
    operation: str,
    repository_root: str,
    since_unix_time: int | None,
    limit: int | None,
    *,
    term: str | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict | None:
    if since_unix_time is None or since_unix_time <= 0:
        return _invalid_query(
            operation,
            repository_root,
            f"A positive since_unix_time is required for {operation}.",
            term=term,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
        )
    if limit is None or limit <= 0:
        return _invalid_query(
            operation,
            repository_root,
            f"A positive limit is required for {operation}.",
            term=term,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
        )
    return None


def _run_operation(
    operation: str,
    repository_root: str,
    analyzer,
    *,
    term: str | None = None,
    terms: tuple[str, ...] | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
    query_term: str | None = None,
    query_terms: tuple[str, ...] | None = None,
    query_since_unix_time: int | None = None,
    query_limit: int | None = None,
    query_left_path: str | None = None,
    query_right_path: str | None = None,
    require_term: bool = False,
    term_message: str | None = None,
    catches_value_error: bool = True,
    pass_bounds_with_term: bool = False,
    pass_bounds_with_terms: bool = False,
    pass_pair_paths: bool = False,
    query_object: object | None = None,
) -> dict:
    query_term = term if query_term is None else query_term
    query_since_unix_time = (
        since_unix_time if query_since_unix_time is None else query_since_unix_time
    )
    query_limit = limit if query_limit is None else query_limit
    query_left_path = left_path if query_left_path is None else query_left_path
    query_right_path = right_path if query_right_path is None else query_right_path
    if require_term and term is None:
        return _invalid_query(
            operation,
            repository_root,
            term_message or "A term is required.",
            term=term,
            terms=query_terms,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
        )

    repository = Path(repository_root)

    try:
        if query_object is not None:
            report = analyzer(repository, query_object)
        elif terms is not None:
            if pass_bounds_with_terms:
                report = analyzer(
                    repository,
                    terms,
                    since_unix_time=since_unix_time,
                    limit=limit,
                )
            else:
                report = analyzer(repository, terms)
        elif term is not None and pass_bounds_with_term:
            report = analyzer(repository, term, since_unix_time=since_unix_time, limit=limit)
        elif term is not None:
            report = analyzer(repository, term)
        elif pass_pair_paths:
            report = analyzer(
                repository,
                left_path=left_path,
                right_path=right_path,
                since_unix_time=since_unix_time,
                limit=limit,
            )
        elif since_unix_time is not None or limit is not None:
            report = analyzer(repository, since_unix_time=since_unix_time, limit=limit)
        else:
            report = analyzer(repository)
    except GitHistoryValidationError as error:
        return _invalid_query(
            operation,
            repository_root,
            str(error),
            term=query_term,
            terms=query_terms,
            since_unix_time=query_since_unix_time,
            limit=query_limit,
            left_path=query_left_path,
            right_path=query_right_path,
        )
    except ValueError as error:
        if catches_value_error:
            return _not_a_repository(
                operation,
                repository_root,
                error,
                query_term,
                query_terms,
                query_since_unix_time,
                query_limit,
                query_left_path,
                query_right_path,
            )
        raise
    except GitFileSourceError as error:
        return _repository_access_failed(
            operation,
            repository_root,
            error,
            term,
            terms,
            since_unix_time,
            limit,
            left_path,
            right_path,
        )

    data = report.to_dict() if hasattr(report, "to_dict") else report
    return _success(
        operation,
        repository_root,
        data,
        term,
        terms,
        since_unix_time,
        limit,
        left_path,
        right_path,
    )


def _run_bounded(
    operation: str,
    repository_root: str,
    analyzer,
    *,
    since_unix_time: int | None,
    limit: int | None,
    term: str | None = None,
    term_required: bool = False,
    term_message: str | None = None,
    pass_bounds_with_term: bool = False,
) -> dict:
    rejection = _validate_history_bounds(
        operation, repository_root, since_unix_time, limit, term=term
    )
    if rejection is not None:
        return rejection
    return _run_operation(
        operation,
        repository_root,
        analyzer,
        term=term,
        since_unix_time=since_unix_time,
        limit=limit,
        require_term=term_required,
        term_message=term_message,
        pass_bounds_with_term=pass_bounds_with_term,
    )


def create_server() -> FastMCP:
    server = FastMCP(
        name="otter-kr",
        instructions=(
            "Research source repositories using deterministic evidence. "
            "Use the returned locations and counts as evidence; reserve semantic conclusions "
            "for your own reasoning."
        ),
    )

    @server.tool(
        name="research",
        title="Research a repository",
        annotations=ToolAnnotations(
            readOnlyHint=True,
            idempotentHint=True,
            openWorldHint=False,
        ),
    )
    def research(
        repository_root: str,
        operation: str,
        term: str | None = None,
        terms: list[str] | None = None,
        since_unix_time: int | None = None,
        limit: int | None = None,
        left_path: str | None = None,
        right_path: str | None = None,
        path: str | None = None,
        lines: list[int] | None = None,
    ) -> dict:
        """Dispatch admitted research operations and reject the remainder."""

        request = ResearchRequest.create(
            repository_root,
            operation,
            term=term,
            terms=terms,
            since_unix_time=since_unix_time,
            limit=limit,
            left_path=left_path,
            right_path=right_path,
            path=path,
            lines=lines,
        )
        repository_root = request.repository_root
        operation = request.operation
        term = request.term
        terms = request.terms
        since_unix_time = request.since_unix_time
        limit = request.limit
        left_path = request.left_path
        right_path = request.right_path
        path = request.path
        lines = request.lines

        def run(analyzer, **kwargs):
            return _run_operation(
                operation,
                repository_root,
                analyzer,
                query_term=term,
                query_since_unix_time=since_unix_time,
                query_limit=limit,
                query_left_path=left_path,
                query_right_path=right_path,
                **kwargs,
            )

        context = OperationContext(
            run=_run_operation,
            query_run=run,
            bounded=_run_bounded,
            reject=_invalid_query,
            unimplemented=_not_implemented,
        )
        return dispatch_research(request, OPERATION_REGISTRY, context)

    return server


mcp = create_server()


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
