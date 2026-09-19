import asyncio
from pathlib import Path

import pytest
from fastmcp import Client

from otter_kr.operation_registry import (
    OperationContext,
    OperationRegistry,
    OperationSpec,
    ResearchRequest,
)
from otter_kr.server import create_server, dispatch_research
from tests.support import (
    assert_invalid_python_warning,
    assert_syntax_error_details,
    assert_unreadable_file_warning,
    call_research,
    git_commit,
    git_repository,
    list_tools,
    write_bytes,
    write_python,
)


def assert_ok_report(
    report: dict,
    *,
    operation: str,
    repository_root: str,
    term: str | None = None,
    since_unix_time: int | None = None,
    limit: int | None = None,
    left_path: str | None = None,
    right_path: str | None = None,
) -> dict:
    assert report["schema_version"] == "1"
    assert report["status"] == "ok"
    assert report["operation"] == operation
    expected_query = {"repository_root": repository_root}
    if term is not None:
        expected_query["term"] = term
    if since_unix_time is not None:
        expected_query["since_unix_time"] = since_unix_time
    if limit is not None:
        expected_query["limit"] = limit
    if left_path is not None:
        expected_query["left_path"] = left_path
    if right_path is not None:
        expected_query["right_path"] = right_path
    assert report["query"] == expected_query
    return report["data"]


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


def test_research_tool_reports_python_inventory_and_parse_health(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/__init__.py", '"""Package."""\n')
    write_python(
        tmp_path, "pkg/service.py", "def collect_payment(amount: int) -> int:\n    return amount\n"
    )
    write_python(tmp_path, "broken.py", "def nope(:\n")
    write_bytes(tmp_path, "bad_encoding.py", b"\xff\n")
    write_python(tmp_path, ".hidden/secret.py", "secret = 1\n")
    write_python(tmp_path, ".venv/lib.py", "virtual = 1\n")
    write_python(tmp_path, "venv/lib.py", "virtual = 2\n")
    git_repository(tmp_path, "pkg", "broken.py", "bad_encoding.py")

    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {"repository_root": str(tmp_path), "operation": "python.inventory"},
        )
    )
    tool_names = asyncio.run(list_tools(server))

    assert tool_names == ["research"]
    assert report["schema_version"] == "1"
    assert report["status"] == "ok"
    assert report["operation"] == "python.inventory"
    assert report["query"] == {"repository_root": str(tmp_path)}
    data = report["data"]
    assert data["language"] == "python"
    assert data["files"][0] == {
        "path": "bad_encoding.py",
        "module": "bad_encoding",
        "module_kind": "module",
        "bytes": 2,
        "lines": 1,
        "parse_status": "unreadable",
    }
    assert data["files"][1]["path"] == "broken.py"
    assert data["files"][1]["module"] == "broken"
    assert data["files"][1]["module_kind"] == "module"
    assert data["files"][1]["bytes"] == 11
    assert data["files"][1]["lines"] == 1
    assert data["files"][1]["parse_status"] == "syntax_error"
    assert_syntax_error_details(data["files"][1]["syntax_error"], "def nope(:\n")
    assert data["files"][2] == {
        "path": "pkg/__init__.py",
        "module": "pkg",
        "module_kind": "package",
        "bytes": 15,
        "lines": 1,
        "parse_status": "ok",
    }
    assert data["files"][3] == {
        "path": "pkg/service.py",
        "module": "pkg.service",
        "module_kind": "module",
        "bytes": 59,
        "lines": 2,
        "parse_status": "ok",
    }
    assert_unreadable_file_warning(data["warnings"][0], "bad_encoding.py")
    assert_invalid_python_warning(data["warnings"][1], "broken.py")


def test_research_tool_rejects_non_admitted_operations_with_stable_shape() -> None:
    server = create_server()

    async def call_research(repository_root: str, operation: str) -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": repository_root, "operation": operation},
            )
            return result.data

    rejection = asyncio.run(call_research("/repo/two", "git.affinity"))

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.affinity",
        "query": {"repository_root": "/repo/two"},
        "error": {
            "code": "not_implemented",
            "message": "No repository research capabilities have been admitted yet.",
        },
    }


def test_git_topic_missing_commit_rejects_without_irrelevant_bounds_in_query() -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": "/repo",
                "operation": "git.topic",
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.topic",
        "query": {"repository_root": "/repo"},
        "error": {
            "code": "invalid_query",
            "message": "A commit reference is required for git.topic.",
        },
    }


def test_git_topic_reports_one_commit_without_irrelevant_bounds_in_query(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    commit_sha = git_commit(tmp_path, "initial import")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "git.topic",
                "term": commit_sha,
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="git.topic",
        repository_root=str(tmp_path),
        term=commit_sha,
    )
    assert data["commit_sha"] == commit_sha
    assert data["subject"] == "initial import"
    assert data["status"] == "initial"
    assert data["changes"] == [
        {
            "status": "A",
            "path": "pkg/service.py",
            "previous_path": None,
            "hunk_status": "initial",
            "hunks": [],
        }
    ]


def test_git_topic_invalid_commit_retains_invalid_query_envelope(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "initial import")
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "git.topic",
                "term": "missing-commit",
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.topic",
        "query": {"repository_root": str(tmp_path), "term": "missing-commit"},
        "error": {
            "code": "invalid_query",
            "message": "tip_sha must be a Git SHA: missing-commit",
        },
    }


def test_git_topic_hunks_missing_commit_rejects_without_irrelevant_bounds_in_query() -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": "/repo",
                "operation": "git.topic_hunks",
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.topic_hunks",
        "query": {"repository_root": "/repo"},
        "error": {
            "code": "invalid_query",
            "message": "A commit reference is required for git.topic_hunks.",
        },
    }


def test_git_topic_hunks_reports_one_commit_without_irrelevant_bounds_in_query(
    tmp_path: Path,
) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "initial import")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    commit_sha = git_commit(tmp_path, "adjust service", "pkg/service.py")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "git.topic_hunks",
                "term": commit_sha,
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="git.topic_hunks",
        repository_root=str(tmp_path),
        term=commit_sha,
    )
    assert data["commit_sha"] == commit_sha
    assert len(data["hunks"]) == 1
    assert data["hunks"][0]["path"] == "pkg/service.py"
    assert data["hunks"][0]["lines"] == ["-value = 1", "+value = 2"]


def test_git_topic_walk_missing_commit_rejects_without_bounds_in_query() -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": "/repo",
                "operation": "git.topic_walk",
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.topic_walk",
        "query": {"repository_root": "/repo"},
        "error": {
            "code": "invalid_query",
            "message": "A commit reference is required for git.topic_walk.",
        },
    }


def test_git_topic_family_missing_commit_rejects_without_bounds_in_query() -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": "/repo",
                "operation": "git.topic_family",
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.topic_family",
        "query": {"repository_root": "/repo"},
        "error": {
            "code": "invalid_query",
            "message": "A commit reference is required for git.topic_family.",
        },
    }


@pytest.mark.parametrize(
    ("bounds", "query", "message"),
    [
        (
            {"limit": 2},
            {"repository_root": "/repo", "term": "topic", "limit": 2},
            "A positive since_unix_time is required for git.topic_family.",
        ),
        (
            {"since_unix_time": 1, "limit": 0},
            {
                "repository_root": "/repo",
                "term": "topic",
                "since_unix_time": 1,
                "limit": 0,
            },
            "A positive limit is required for git.topic_family.",
        ),
    ],
)
def test_git_topic_family_rejects_missing_or_non_positive_bounds(
    bounds: dict[str, int], query: dict[str, object], message: str
) -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": "/repo",
                "operation": "git.topic_family",
                "term": "topic",
                **bounds,
            },
        )
    )

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.topic_family",
        "query": query,
        "error": {"code": "invalid_query", "message": message},
    }


def test_git_topic_family_reports_a_bounded_family_in_the_query_envelope(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    first = git_commit(tmp_path, "initial import")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    topic = git_commit(tmp_path, "adjust service", "pkg/service.py")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "git.topic_family",
                "term": topic,
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="git.topic_family",
        repository_root=str(tmp_path),
        term=topic,
        since_unix_time=1,
        limit=2,
    )
    assert data["topic_sha"] == topic
    assert data["budget_limit"] == 2
    assert [commit["sha"] for commit in data["history_commits"]] == [topic, first]


@pytest.mark.parametrize(
    ("bounds", "query", "message"),
    [
        (
            {"limit": 2},
            {"repository_root": "/repo", "term": "topic", "limit": 2},
            "A positive since_unix_time is required for git.topic_walk.",
        ),
        (
            {"since_unix_time": 0, "limit": 2},
            {
                "repository_root": "/repo",
                "term": "topic",
                "since_unix_time": 0,
                "limit": 2,
            },
            "A positive since_unix_time is required for git.topic_walk.",
        ),
        (
            {"since_unix_time": 1},
            {"repository_root": "/repo", "term": "topic", "since_unix_time": 1},
            "A positive limit is required for git.topic_walk.",
        ),
        (
            {"since_unix_time": 1, "limit": 0},
            {
                "repository_root": "/repo",
                "term": "topic",
                "since_unix_time": 1,
                "limit": 0,
            },
            "A positive limit is required for git.topic_walk.",
        ),
    ],
)
def test_git_topic_walk_rejects_missing_or_non_positive_bounds(
    bounds: dict[str, int], query: dict[str, object], message: str
) -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": "/repo",
                "operation": "git.topic_walk",
                "term": "topic",
                **bounds,
            },
        )
    )

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "git.topic_walk",
        "query": query,
        "error": {"code": "invalid_query", "message": message},
    }


def test_git_topic_walk_reports_bounded_first_parent_history(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    first = git_commit(tmp_path, "initial import")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    second = git_commit(tmp_path, "adjust service", "pkg/service.py")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "git.topic_walk",
                "term": second,
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="git.topic_walk",
        repository_root=str(tmp_path),
        term=second,
        since_unix_time=1,
        limit=2,
    )
    assert data["topic_sha"] == second
    assert data["termination"] == "root"
    assert data["commits"][0]["parent_shas"] == [first]
    assert data["commits"][1]["parent_shas"] == []
    assert data["commits"][0]["changes"] == [
        {"status": "M", "path": "pkg/service.py", "previous_path": None}
    ]
    assert data["commits"][0]["hunk_status"] == "available"
    assert data["commits"][0]["hunks"]
    assert data["commits"][1]["changes"] == [
        {"status": "A", "path": "pkg/service.py", "previous_path": None}
    ]
    assert data["commits"][1]["hunk_status"] == "initial"
    assert data["commits"][1]["hunks"] == []


def test_research_tool_reports_bounded_git_history_context(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    first = git_commit(tmp_path, "initial import")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    second = git_commit(tmp_path, "adjust service", "pkg/service.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.history",
                    "since_unix_time": 1,
                    "limit": 2,
                },
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="git.history",
        repository_root=str(tmp_path),
        since_unix_time=1,
        limit=2,
    )
    assert data["report_version"] == "1"
    assert data["repository_root"] == str(tmp_path)
    assert data["tip_revision"] == "HEAD"
    assert data["since_unix_time"] == 1
    assert data["limit"] == 2
    assert data["commit_count"] == 2
    assert data["truncated"] is False
    assert data["source_file_filter"] == {
        "tracked_by": "git",
        "language": "python",
        "pathspec": "*.py",
        "tip_revision": "HEAD",
    }
    assert data["commits"] == [
        {
            "sha": second,
            "parent_shas": [first],
            "committed_unix_time": data["commits"][0]["committed_unix_time"],
            "subject": "adjust service",
        },
        {
            "sha": first,
            "parent_shas": [],
            "committed_unix_time": data["commits"][1]["committed_unix_time"],
            "subject": "initial import",
        },
    ]


def test_research_tool_reports_git_hotspots(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "initial import")
    write_python(tmp_path, "pkg/service.py", "value = 2\nvalue2 = 3\n")
    git_commit(tmp_path, "adjust service", "pkg/service.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.hotspots",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="git.hotspots",
        repository_root=str(tmp_path),
        since_unix_time=1,
        limit=10,
    )
    assert data["commit_count"] == 2
    assert data["truncated"] is False
    assert data["files"][0]["path"] == "pkg/service.py"


def test_research_tool_reports_git_history_snapshot(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "initial")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    git_commit(tmp_path, "update", "pkg/service.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.snapshot",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="git.snapshot",
        repository_root=str(tmp_path),
        since_unix_time=1,
        limit=10,
    )
    assert data["files"][0]["path"] == "pkg/service.py"
    assert data["files"][0]["commit_count"] == 2


def test_research_tool_reports_git_distributions(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "value = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "feat: initial")
    write_python(tmp_path, "pkg/service.py", "value = 2\n")
    git_commit(tmp_path, "routine maintenance", "pkg/service.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.distributions",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="git.distributions",
        repository_root=str(tmp_path),
        since_unix_time=1,
        limit=10,
    )
    assert data["weeks"]
    assert data["unknown_category_count"] == 1


def test_research_tool_reports_global_git_cochange(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/a.py", "a = 1\n")
    write_python(tmp_path, "pkg/b.py", "b = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "initial pair")
    write_python(tmp_path, "pkg/a.py", "a = 2\n")
    write_python(tmp_path, "pkg/b.py", "b = 2\n")
    git_commit(tmp_path, "adjust pair", "pkg/a.py", "pkg/b.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.cochange",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="git.cochange",
        repository_root=str(tmp_path),
        since_unix_time=1,
        limit=10,
    )
    assert data["eligible_commit_count"] == 2
    assert data["pairs"][0]["left_path"] == "pkg/a.py"
    assert data["pairs"][0]["right_path"] == "pkg/b.py"
    assert data["pairs"][0]["score"] == 2.0
    assert data["pairs"][0]["commit_count"] == 2


def test_research_tool_reports_focus_file_cochange(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/a.py", "a = 1\n")
    write_python(tmp_path, "pkg/b.py", "b = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "initial pair")
    write_python(tmp_path, "pkg/a.py", "a = 2\n")
    write_python(tmp_path, "pkg/b.py", "b = 2\n")
    git_commit(tmp_path, "adjust pair", "pkg/a.py", "pkg/b.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.cochange.file",
                    "term": "pkg/a.py",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="git.cochange.file",
        repository_root=str(tmp_path),
        term="pkg/a.py",
        since_unix_time=1,
        limit=10,
    )
    assert data["focus_path"] == "pkg/a.py"
    assert len(data["pairs"]) == 1
    assert data["pairs"][0]["right_path"] == "pkg/b.py"
    assert data["pairs"][0]["score"] == 2.0


def test_research_tool_reports_explicit_pair_cochange(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/a.py", "a = 1\n")
    write_python(tmp_path, "pkg/b.py", "b = 1\n")
    git_repository(tmp_path, "pkg")
    git_commit(tmp_path, "initial pair")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.cochange.pair",
                    "left_path": "pkg/a.py",
                    "right_path": "pkg/b.py",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="git.cochange.pair",
        repository_root=str(tmp_path),
        since_unix_time=1,
        limit=10,
        left_path="pkg/a.py",
        right_path="pkg/b.py",
    )
    assert report["query"]["left_path"] == "pkg/a.py"
    assert report["query"]["right_path"] == "pkg/b.py"
    assert data["pair"]["score"] == 1.0


def test_research_tool_rejects_pair_without_both_paths() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": "/repo",
                    "operation": "git.cochange.pair",
                    "left_path": "pkg/a.py",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"]["code"] == "invalid_query"


def test_research_tool_rejects_focus_file_cochange_without_term() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": "/repo",
                    "operation": "git.cochange.file",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A focus file term is required for git.cochange.file.",
    }


def test_research_tool_rejects_non_relative_focus_file() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": "/repo",
                    "operation": "git.cochange.file",
                    "term": "/pkg/a.py",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "focus_path must be repository-relative.",
    }


def test_research_tool_rejects_git_cochange_without_bounds() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": "/repo", "operation": "git.cochange"},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A positive since_unix_time is required for git.cochange.",
    }


def test_research_tool_rejects_git_hotspots_without_bounds() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": "/repo", "operation": "git.hotspots"},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A positive since_unix_time is required for git.hotspots.",
    }


def test_research_tool_rejects_git_history_without_explicit_since_boundary() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": "/repo", "operation": "git.history", "limit": 10},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A positive since_unix_time is required for git.history.",
    }


def test_research_tool_rejects_git_history_without_explicit_limit() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": "/repo", "operation": "git.history", "since_unix_time": 1},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A positive limit is required for git.history.",
    }


def test_research_tool_reports_git_history_failure_evidence(tmp_path: Path) -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.history",
                    "since_unix_time": 1,
                    "limit": 10,
                },
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["status"] == "rejected"
    assert rejection["error"]["code"] == "repository_access_failed"
    assert rejection["error"]["returncode"] != 0
    assert rejection["error"]["command"][:2] == ["git", "-C"]


def test_research_tool_reports_python_complexity(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/logic.py",
        (
            "class Service:\n"
            "    def decide(self, value: int) -> int:\n"
            "        if value > 10:\n"
            "            return value\n"
            "        for item in range(value):\n"
            "            if item % 2 == 0 and item > 3:\n"
            "                return item\n"
            "        return 0\n"
            "\n"
            "def outer(flag: bool) -> int:\n"
            "    def inner(sample: int) -> int:\n"
            "        return sample\n"
            "    if flag:\n"
            "        return inner(1)\n"
            "    return inner(0)\n"
        ),
    )
    git_repository(tmp_path, "pkg")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {"repository_root": str(tmp_path), "operation": "python.complexity"},
        )
    )
    data = assert_ok_report(
        report,
        operation="python.complexity",
        repository_root=str(tmp_path),
    )

    assert data["language"] == "python"
    assert data["warnings"] == []
    assert data["functions"] == [
        {
            "path": "pkg/logic.py",
            "qualified_name": "Service.decide",
            "kind": "method",
            "line": 2,
            "column": 4,
            "end_line": 8,
            "max_nesting_depth": 2,
            "branch_count": 3,
            "line_count": 7,
            "cyclomatic_count": 5,
        },
        {
            "path": "pkg/logic.py",
            "qualified_name": "outer",
            "kind": "function",
            "line": 10,
            "column": 0,
            "end_line": 15,
            "max_nesting_depth": 1,
            "branch_count": 1,
            "line_count": 6,
            "cyclomatic_count": 2,
        },
        {
            "path": "pkg/logic.py",
            "qualified_name": "outer.inner",
            "kind": "function",
            "line": 11,
            "column": 4,
            "end_line": 12,
            "max_nesting_depth": 0,
            "branch_count": 0,
            "line_count": 2,
            "cyclomatic_count": 1,
        },
    ]


def test_research_tool_reports_python_complexity_parse_warnings(tmp_path: Path) -> None:
    write_python(tmp_path, "broken.py", "def nope(:\n")
    write_bytes(tmp_path, "bad_encoding.py", b"\xff\n")
    git_repository(tmp_path, "broken.py", "bad_encoding.py")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {"repository_root": str(tmp_path), "operation": "python.complexity"},
        )
    )
    data = assert_ok_report(
        report,
        operation="python.complexity",
        repository_root=str(tmp_path),
    )

    assert data["language"] == "python"
    assert data["functions"] == []
    warnings = data["warnings"]
    assert_unreadable_file_warning(warnings[0], "bad_encoding.py")
    assert_invalid_python_warning(warnings[1], "broken.py")


def test_research_tool_calls_are_independent(tmp_path: Path) -> None:
    write_python(tmp_path, "alpha.py", "alpha = 1\n")
    other = tmp_path / "other"
    write_python(other, "beta.py", "beta = 1\n")
    git_repository(tmp_path, "alpha.py", "other")
    git_repository(other, "beta.py")

    server = create_server()

    async def call_research(repository_root: str) -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": repository_root, "operation": "python.inventory"},
            )
            return result.data

    first = asyncio.run(call_research(str(tmp_path)))
    second = asyncio.run(call_research(str(other)))

    assert [item["path"] for item in first["data"]["files"]] == [
        "alpha.py",
        "other/beta.py",
    ]
    assert [item["path"] for item in second["data"]["files"]] == ["beta.py"]


def test_research_tool_admits_python_inventory(tmp_path) -> None:
    (tmp_path / "module.py").write_text("answer = 42\n")
    git_repository(tmp_path, "module.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": str(tmp_path), "operation": "python.inventory"},
            )
            return result.data

    report = asyncio.run(call_research())

    assert report["status"] == "ok"
    assert report["operation"] == "python.inventory"
    assert report["data"]["files"][0]["path"] == "module.py"


def test_research_tool_reports_python_name_occurrences(tmp_path: Path) -> None:
    write_python(tmp_path, "orders.py", "class OrderBook:\n    pass\n")
    git_repository(tmp_path, "orders.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "python.names",
                    "term": "order",
                },
            )
            return result.data

    report = asyncio.run(call_research())

    assert report["status"] == "ok"
    assert report["query"]["term"] == "order"
    assert report["data"]["occurrences"][0] == {
        "path": "orders.py",
        "line": 1,
        "column": 0,
        "name": "OrderBook",
        "kind": "class",
    }


def test_research_tool_reports_structural_import_target_edges(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "service.py",
        "from app.models import Payment\n\ndef quote():\n    return Payment()\n",
    )
    git_repository(tmp_path, "service.py")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "python.neighborhood.structural",
                "term": "Payment",
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="python.neighborhood.structural",
        repository_root=str(tmp_path),
        term="Payment",
    )
    assert {
        "seed": "Payment",
        "neighbor": "app.models",
        "weight": 1,
        "reason": "import target",
    } in data["edges"]


def test_research_tool_reports_plain_import_alias_target_edges(tmp_path: Path) -> None:
    write_python(tmp_path, "service.py", "import app.models as Payment\nPayment.quote()\n")
    git_repository(tmp_path, "service.py")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "python.neighborhood.structural",
                "term": "Payment",
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="python.neighborhood.structural",
        repository_root=str(tmp_path),
        term="Payment",
    )
    assert {
        "seed": "Payment",
        "neighbor": "app.models",
        "weight": 1,
        "reason": "import target",
    } in data["edges"]


def test_research_tool_reports_relative_import_target_edges(tmp_path: Path) -> None:
    write_python(tmp_path, "pkg/service.py", "from .models import Payment\nPayment()\n")
    git_repository(tmp_path, "pkg/service.py")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "python.neighborhood.structural",
                "term": "Payment",
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="python.neighborhood.structural",
        repository_root=str(tmp_path),
        term="Payment",
    )
    assert {
        "seed": "Payment",
        "neighbor": "pkg.models",
        "weight": 1,
        "reason": "import target",
    } in data["edges"]


def test_research_tool_reports_python_import_edges(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/service.py",
        "import os\nfrom pkg.helpers import helper\n",
    )
    write_python(tmp_path, "pkg/helpers.py", "def helper():\n    return 1\n")
    git_repository(tmp_path, "pkg")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": str(tmp_path), "operation": "python.imports"},
            )
            return result.data

    report = asyncio.run(call_research())
    data = assert_ok_report(
        report,
        operation="python.imports",
        repository_root=str(tmp_path),
    )

    assert data["language"] == "python"
    assert data["warnings"] == []
    assert data["edges"] == [
        {
            "path": "pkg/service.py",
            "source_module": "pkg.service",
            "target_module": "os",
            "imported_names": [],
            "relative_level": 0,
            "line": 1,
        },
        {
            "path": "pkg/service.py",
            "source_module": "pkg.service",
            "target_module": "pkg.helpers",
            "imported_names": ["helper"],
            "relative_level": 0,
            "line": 2,
        },
    ]


def test_research_tool_rejects_python_names_without_term() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": "/repo", "operation": "python.names"},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A term is required for python.names.",
    }


def test_research_tool_reports_git_failure_evidence(tmp_path: Path) -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": str(tmp_path), "operation": "python.inventory"},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["status"] == "rejected"
    assert rejection["error"]["code"] == "repository_access_failed"
    assert rejection["error"]["returncode"] != 0
    assert rejection["error"]["command"][:2] == ["git", "-C"]


def test_research_tool_rejects_missing_repository_root() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": "/repo/missing",
                    "operation": "python.imports",
                    "term": "Widget",
                    "since_unix_time": 123,
                    "limit": 7,
                    "left_path": "left.py",
                    "right_path": "right.py",
                },
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "python.imports",
        "query": {
            "repository_root": "/repo/missing",
            "term": "Widget",
            "since_unix_time": 123,
            "limit": 7,
            "left_path": "left.py",
            "right_path": "right.py",
        },
        "error": {
            "code": "not_a_repository",
            "message": "Repository is not a directory: /repo/missing",
        },
    }


def test_research_tool_reports_repeated_python_literals(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "app.py",
        'def first():\n    return "retry", 42\n\ndef second():\n    return "retry", 42\n',
    )
    git_repository(tmp_path, "app.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": str(tmp_path), "operation": "python.literals"},
            )
            return result.data

    report = asyncio.run(call_research())

    assert report["status"] == "ok"
    assert report["operation"] == "python.literals"
    assert [
        (item["kind"], item["value"], item["count"]) for item in report["data"]["literals"]
    ] == [
        ("integer", "42", 2),
        ("string", "retry", 2),
    ]


def test_research_tool_reports_duplicate_python_helpers(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/helpers.py",
        (
            "def first(item, limit):\n"
            "    if item > limit:\n"
            "        return item - limit\n"
            "    return limit - item\n\n"
            "def second(value, cap):\n"
            "    if value > cap:\n"
            "        return value - cap\n"
            "    return cap - value\n"
        ),
    )
    git_repository(tmp_path, "pkg")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": str(tmp_path), "operation": "python.duplicates"},
            )
            return result.data

    report = asyncio.run(call_research())

    assert report["status"] == "ok"
    assert report["operation"] == "python.duplicates"
    assert [item["qualified_name"] for item in report["data"]["groups"][0]["occurrences"]] == [
        "first",
        "second",
    ]
    assert [
        (
            item["left"]["qualified_name"],
            item["right"]["qualified_name"],
        )
        for item in report["data"]["pairs"]
    ] == [("first", "second")]


def test_research_tool_reports_python_type_discriminations(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/service.py",
        (
            "from enum import Enum\n\n"
            "class Status(Enum):\n"
            '    OPEN = "open"\n'
            '    CLOSED = "closed"\n\n'
            'LABELS = {Status.OPEN: "Open", Status.CLOSED: "Closed"}\n\n'
            "def describe(status):\n"
            "    if status is Status.OPEN:\n"
            "        return LABELS[Status.OPEN]\n"
            "    if Status.CLOSED == status:\n"
            "        return LABELS[Status.CLOSED]\n"
            "    return LABELS[status]\n"
        ),
    )
    git_repository(tmp_path, "pkg")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "python.discriminations",
                    "term": "Status",
                },
            )
            return result.data

    report = asyncio.run(call_research())

    assert report["status"] == "ok"
    assert report["operation"] == "python.discriminations"
    assert report["query"]["term"] == "Status"
    assert [item["member"] for item in report["data"]["comparisons"]] == ["OPEN", "CLOSED"]


def test_research_tool_reports_python_test_candidates_for_selected_symbol(tmp_path: Path) -> None:
    source = (
        "from app.service import collect_payment, collect_payment as pay\n\n"
        "def test_collect_payment_path():\n"
        "    collect_payment()\n"
    )
    write_python(
        tmp_path,
        "tests/test_service.py",
        source,
    )
    git_repository(tmp_path, "tests")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "python.tests",
                    "term": "collect_payment",
                },
            )
            return result.data

    report = asyncio.run(call_research())

    assert report["status"] == "ok"
    assert report["operation"] == "python.tests"
    assert report["query"]["term"] == "collect_payment"
    assert [item["qualified_name"] for item in report["data"]["candidates"]] == [
        "test_collect_payment_path"
    ]
    assert [
        {
            key: item[key]
            for key in (
                "path",
                "module",
                "relative_level",
                "imported_name",
                "local_name",
            )
        }
        for item in report["data"]["matching_imports"]
    ] == [
        {
            "path": "tests/test_service.py",
            "module": "app.service",
            "relative_level": 0,
            "imported_name": "collect_payment",
            "local_name": "collect_payment",
        },
        {
            "path": "tests/test_service.py",
            "module": "app.service",
            "relative_level": 0,
            "imported_name": "collect_payment",
            "local_name": "pay",
        },
    ]
    source_line = source.splitlines()[0]
    for item in report["data"]["matching_imports"]:
        assert source_line[item["column"] :].startswith(item["imported_name"])


def test_research_tool_reports_python_carrier_guards(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/service.py",
        (
            "def advance(order):\n"
            "    if order.status != 'open':\n"
            "        return\n"
            "    order.closed = True\n"
        ),
    )
    git_repository(tmp_path, "pkg")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "python.carrier_guards",
                "term": "order",
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="python.carrier_guards",
        repository_root=str(tmp_path),
        term="order",
    )
    assert data["carrier"] == "order"
    assert [item["control_shape"] for item in data["occurrences"]] == ["early_exit"]
    assert data["occurrences"][0]["exit_kind"] == "return"


def test_seed_evidence_composite_includes_carrier_guards_for_identifier(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "pkg/service.py",
        "def advance(order):\n    if order.status == 'open':\n        order.close()\n",
    )
    git_repository(tmp_path, "pkg")
    server = create_server()

    report = asyncio.run(
        call_research(
            server,
            {
                "repository_root": str(tmp_path),
                "operation": "python.seed_evidence",
                "term": "order",
            },
        )
    )

    data = assert_ok_report(
        report,
        operation="python.seed_evidence",
        repository_root=str(tmp_path),
        term="order",
    )
    assert data["carrier_guards"]["carrier"] == "order"
    assert data["carrier_guards"]["occurrences"][0]["path"] == "pkg/service.py"


def test_research_tool_rejects_python_discriminations_without_term() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": "/repo", "operation": "python.discriminations"},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A term is required for python.discriminations.",
    }


def test_research_tool_rejects_python_carrier_guards_without_term() -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {"repository_root": "/repo", "operation": "python.carrier_guards"},
        )
    )

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A carrier name is required for python.carrier_guards.",
    }


def test_research_tool_rejects_unsafe_carrier_guards_path() -> None:
    server = create_server()

    rejection = asyncio.run(
        call_research(
            server,
            {
                "repository_root": "/repo",
                "operation": "python.carrier_guards",
                "term": "order",
                "path": "../secret.py",
            },
        )
    )

    assert rejection["status"] == "rejected"
    assert rejection["error"]["code"] == "invalid_query"


def test_research_tool_rejects_python_tests_without_term() -> None:
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": "/repo", "operation": "python.tests"},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection["error"] == {
        "code": "invalid_query",
        "message": "A term is required for python.tests.",
    }


def test_research_tool_reports_line_origins(tmp_path: Path) -> None:
    write_python(tmp_path, "service.py", "value = 1\n")
    git_repository(tmp_path, "service.py")
    git_commit(tmp_path, "initial", "service.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "git.line_origins",
                    "term": "HEAD",
                    "path": "service.py",
                    "lines": [1],
                },
            )
            return result.data

    report = asyncio.run(call_research())
    assert report["status"] == "ok"
    assert report["data"]["origins"][0]["text"] == "value = 1"


def test_review_packet_characterizes_composite_sources(tmp_path: Path) -> None:
    write_python(tmp_path, "service.py", "def collect():\n    return 1\n")
    git_repository(tmp_path, "service.py")
    git_commit(tmp_path, "initial", "service.py")
    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": str(tmp_path),
                "operation": "git.review_packet",
                "since_unix_time": 1,
                "limit": 1,
            },
        )
    )

    assert report["status"] == "ok"
    assert report["data"]["scope"]["limit"] == 1
    assert "files" in report["data"]["history"]
    assert set(report["data"]["inventory"]) == {
        "hotspots",
        "duplicates",
        "repeated_groups",
        "distributions",
        "branch_growth",
        "ownership",
    }
    assert {"names", "dependencies", "tests"} <= set(report["data"])
    data = report["data"]
    names = data["names"]
    dependencies = data["dependencies"]
    tests = data["tests"]
    assert [name["name"] for name in names] == ["collect"]
    assert dependencies["edges"] == []
    assert [mapping["symbol"] for mapping in tests] == ["collect"]


def test_review_packet_file_scopes_history_and_python_context(tmp_path: Path) -> None:
    write_python(tmp_path, "service.py", "def collect():\n    return 1\n")
    write_python(tmp_path, "other.py", "def ignore():\n    return 2\n")
    git_repository(tmp_path, "service.py", "other.py")
    git_commit(tmp_path, "initial", "service.py", "other.py")

    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": str(tmp_path),
                "operation": "git.review_packet.file",
                "term": "service.py",
                "since_unix_time": 1,
                "limit": 1,
            },
        )
    )

    assert report["status"] == "ok"
    assert report["data"]["scope"]["path"] == "service.py"
    assert "status" not in report["data"]["inventory"]
    assert [item["path"] for item in report["data"]["inventory"]["hotspots"]["files"]] == [
        "service.py"
    ]
    assert report["data"]["dependencies"]["edges"] == []
    assert report["data"]["dependencies"]["edge_count"] == 0
    assert report["data"]["dependencies"]["edges_truncated"] is False
    assert [item["path"] for item in report["data"]["history"]["files"]] == ["service.py"]
    assert [item["name"] for item in report["data"]["names"]] == ["collect"]


def test_review_packet_revision_walks_from_explicit_tip(tmp_path: Path) -> None:
    write_python(tmp_path, "service.py", "def collect():\n    return 1\n")
    git_repository(tmp_path, "service.py")
    first = git_commit(tmp_path, "first", "service.py")
    write_python(tmp_path, "service.py", "def collect():\n    return 2\n")
    git_commit(tmp_path, "second", "service.py")

    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": str(tmp_path),
                "operation": "git.review_packet.revision",
                "term": first,
                "since_unix_time": 1,
                "limit": 1,
            },
        )
    )

    assert report["status"] == "ok"
    assert report["data"]["scope"]["tip_sha"] == first
    assert report["data"]["scope"]["source_evidence"] == "unavailable_at_revision"
    assert report["data"]["names"] == []
    assert report["data"]["tests"] == []
    assert report["data"]["inventory"]["status"] == "unavailable_at_revision"
    assert report["data"]["history"]["files"][0]["recent_commits"] == [first]


def test_review_packet_files_scopes_to_multiple_paths(tmp_path: Path) -> None:
    write_python(tmp_path, "service.py", "def collect():\n    return 1\n")
    write_python(tmp_path, "other.py", "def ignore():\n    return 2\n")
    git_repository(tmp_path, "service.py", "other.py")
    git_commit(tmp_path, "initial", "service.py", "other.py")

    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": str(tmp_path),
                "operation": "git.review_packet.files",
                "paths": ["service.py", "other.py"],
                "since_unix_time": 1,
                "limit": 2,
            },
        )
    )

    assert report["status"] == "ok"
    assert report["data"]["scope"]["paths"] == ["service.py", "other.py"]
    assert [item["path"] for item in report["data"]["names"]] == [
        "other.py",
        "service.py",
    ]


def test_variable_cluster_rejects_without_an_exact_name() -> None:
    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": "/repo",
                "operation": "python.variable_cluster",
            },
        )
    )

    assert report["status"] == "rejected"
    assert report["error"] == {
        "code": "not_implemented",
        "message": "Variable-cluster evidence has not been admitted yet.",
    }


def test_variable_cluster_admits_two_explicit_names(tmp_path: Path) -> None:
    write_python(
        tmp_path,
        "sample.py",
        "def adjust(count, limit):\n"
        "    if count < limit:\n"
        "        count += 1\n"
        "        limit -= 1\n",
    )
    git_repository(tmp_path, "sample.py")
    git_commit(tmp_path, "initial", "sample.py")

    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": str(tmp_path),
                "operation": "python.variable_cluster",
                "terms": ["count", "limit"],
                "since_unix_time": 1,
                "limit": 5,
            },
        )
    )

    assert report["status"] == "ok"
    assert report["query"]["terms"] == ["count", "limit"]
    assert report["data"]["names"] == ["count", "limit"]
    assert report["data"]["shared_scopes"] == [{"path": "sample.py", "scope": "adjust"}]
    assert report["data"]["shared_guards"][0]["expression"] == "count < limit"
    assert {item["name"] for item in report["data"]["occurrences"]} == {"count", "limit"}


def test_variable_cluster_rejects_more_than_eight_names() -> None:
    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": "/repo",
                "operation": "python.variable_cluster",
                "terms": [
                    "one",
                    "two",
                    "three",
                    "four",
                    "five",
                    "six",
                    "seven",
                    "eight",
                    "nine",
                ],
            },
        )
    )

    assert report["status"] == "rejected"
    assert report["error"]["code"] == "invalid_query"


def test_variable_cluster_preserves_terms_on_repository_error() -> None:
    report = asyncio.run(
        call_research(
            create_server(),
            {
                "repository_root": "/repo/missing",
                "operation": "python.variable_cluster",
                "terms": ["count", "limit"],
            },
        )
    )

    assert report["status"] == "rejected"
    assert report["query"]["terms"] == ["count", "limit"]


def test_research_tool_rejects_object_lifecycle_without_term() -> None:
    report = asyncio.run(
        call_research(
            create_server(),
            {"repository_root": "/repo", "operation": "python.object_lifecycle"},
        )
    )

    assert report["status"] == "rejected"
    assert report["error"] == {
        "code": "invalid_query",
        "message": "A carrier name is required for python.object_lifecycle.",
    }
