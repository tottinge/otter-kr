import asyncio
import subprocess
from pathlib import Path

from fastmcp import Client

from otter_kr.server import create_server


def write_text(repository: Path, relative_path: str, source: str) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(source, encoding="utf-8")


def write_bytes(repository: Path, relative_path: str, source: bytes) -> None:
    target = repository / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(source)


def git_repository(repository: Path, *paths: str) -> None:
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(["git", "-C", str(repository), "add", *paths], check=True)


def test_research_tool_reports_python_inventory_and_parse_health(tmp_path: Path) -> None:
    write_text(tmp_path, "pkg/__init__.py", '"""Package."""\n')
    write_text(
        tmp_path, "pkg/service.py", "def collect_payment(amount: int) -> int:\n    return amount\n"
    )
    write_text(tmp_path, "broken.py", "def nope(:\n")
    write_bytes(tmp_path, "bad_encoding.py", b"\xff\n")
    write_text(tmp_path, ".hidden/secret.py", "secret = 1\n")
    write_text(tmp_path, ".venv/lib.py", "virtual = 1\n")
    write_text(tmp_path, "venv/lib.py", "virtual = 2\n")
    git_repository(tmp_path, "pkg", "broken.py", "bad_encoding.py")

    server = create_server()

    async def call_research() -> tuple[list[str], dict]:
        async with Client(server) as client:
            tools = await client.list_tools()
            result = await client.call_tool(
                "research",
                {
                    "repository_root": str(tmp_path),
                    "operation": "python.inventory",
                },
            )
            return [tool.name for tool in tools], result.data

    tool_names, report = asyncio.run(call_research())

    assert tool_names == ["research"]
    assert report == {
        "schema_version": "1",
        "status": "ok",
        "operation": "python.inventory",
        "query": {"repository_root": str(tmp_path)},
        "data": {
            "language": "python",
            "files": [
                {
                    "path": "bad_encoding.py",
                    "module": "bad_encoding",
                    "module_kind": "module",
                    "bytes": 2,
                    "lines": 1,
                    "parse_status": "unreadable",
                },
                {
                    "path": "broken.py",
                    "module": "broken",
                    "module_kind": "module",
                    "bytes": 11,
                    "lines": 1,
                    "parse_status": "syntax_error",
                    "syntax_error": {
                        "line": 1,
                        "column": 10,
                        "message": "invalid syntax",
                    },
                },
                {
                    "path": "pkg/__init__.py",
                    "module": "pkg",
                    "module_kind": "package",
                    "bytes": 15,
                    "lines": 1,
                    "parse_status": "ok",
                },
                {
                    "path": "pkg/service.py",
                    "module": "pkg.service",
                    "module_kind": "module",
                    "bytes": 59,
                    "lines": 2,
                    "parse_status": "ok",
                },
            ],
            "warnings": [
                {
                    "code": "unreadable_file",
                    "path": "bad_encoding.py",
                    "message": "File could not be decoded as UTF-8.",
                },
                {
                    "code": "invalid_python",
                    "path": "broken.py",
                    "message": "Syntax error at line 1, column 10: invalid syntax",
                },
            ],
        },
    }


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


def test_research_tool_reports_python_complexity(tmp_path: Path) -> None:
    write_text(
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

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": str(tmp_path), "operation": "python.complexity"},
            )
            return result.data

    report = asyncio.run(call_research())

    assert report == {
        "schema_version": "1",
        "status": "ok",
        "operation": "python.complexity",
        "query": {"repository_root": str(tmp_path)},
        "data": {
            "language": "python",
            "functions": [
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
            ],
            "warnings": [],
        },
    }


def test_research_tool_reports_python_complexity_parse_warnings(tmp_path: Path) -> None:
    write_text(tmp_path, "broken.py", "def nope(:\n")
    write_bytes(tmp_path, "bad_encoding.py", b"\xff\n")
    git_repository(tmp_path, "broken.py", "bad_encoding.py")
    server = create_server()

    async def call_research() -> dict:
        async with Client(server) as client:
            result = await client.call_tool(
                "research",
                {"repository_root": str(tmp_path), "operation": "python.complexity"},
            )
            return result.data

    report = asyncio.run(call_research())

    assert report == {
        "schema_version": "1",
        "status": "ok",
        "operation": "python.complexity",
        "query": {"repository_root": str(tmp_path)},
        "data": {
            "language": "python",
            "functions": [],
            "warnings": [
                {
                    "code": "unreadable_file",
                    "path": "bad_encoding.py",
                    "message": "File could not be decoded as UTF-8.",
                },
                {
                    "code": "invalid_python",
                    "path": "broken.py",
                    "message": "Syntax error at line 1, column 10: invalid syntax",
                },
            ],
        },
    }


def test_research_tool_calls_are_independent(tmp_path: Path) -> None:
    write_text(tmp_path, "alpha.py", "alpha = 1\n")
    other = tmp_path / "other"
    write_text(other, "beta.py", "beta = 1\n")
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
    write_text(tmp_path, "orders.py", "class OrderBook:\n    pass\n")
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


def test_research_tool_reports_python_import_edges(tmp_path: Path) -> None:
    write_text(
        tmp_path,
        "pkg/service.py",
        "import os\nfrom pkg.helpers import helper\n",
    )
    write_text(tmp_path, "pkg/helpers.py", "def helper():\n    return 1\n")
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

    assert report == {
        "schema_version": "1",
        "status": "ok",
        "operation": "python.imports",
        "query": {"repository_root": str(tmp_path)},
        "data": {
            "language": "python",
            "edges": [
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
            ],
            "warnings": [],
        },
    }


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
                {"repository_root": "/repo/missing", "operation": "python.imports"},
            )
            return result.data

    rejection = asyncio.run(call_research())

    assert rejection == {
        "schema_version": "1",
        "status": "rejected",
        "operation": "python.imports",
        "query": {"repository_root": "/repo/missing"},
        "error": {
            "code": "not_a_repository",
            "message": "Repository is not a directory: /repo/missing",
        },
    }


def test_research_tool_reports_repeated_python_literals(tmp_path: Path) -> None:
    write_text(
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
