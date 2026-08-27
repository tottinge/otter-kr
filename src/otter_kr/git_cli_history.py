"""Git CLI adapter for bounded commit metadata and patch retrieval."""

import re
import subprocess
from collections.abc import Callable
from pathlib import Path, PurePosixPath

from otter_kr.git_files import GitFileSourceError
from otter_kr.git_ports import (
    CommitFileChange,
    CommitFileChangeSource,
    CommitHistoryQuery,
    CommitMetadata,
    CommitMetadataSource,
    CommitPatchRequest,
    CommitPatchSource,
    RawCommitPatch,
)

_LOG_FORMAT = "%H%x00%P%x00%ct%x00%an%x00%ae%x00%s"
_MAX_COMMIT_LIMIT = 5000
_SHA_PATTERN = re.compile(r"^[0-9a-f]{7,40}$")

GitRunner = Callable[[tuple[str, ...]], tuple[int, bytes, bytes]]


class GitHistoryError(GitFileSourceError):
    """History adapter failures with reproducible command evidence."""


class GitHistoryValidationError(ValueError):
    """A history query is not safely or deterministically bounded."""


class GitHistoryPatchTooLargeError(GitHistoryError):
    """Patch output exceeded the requested byte ceiling."""

    def __init__(self, command: tuple[str, ...], max_bytes: int, actual_bytes: int) -> None:
        self.max_bytes = max_bytes
        self.actual_bytes = actual_bytes
        super().__init__(
            command,
            None,
            f"Patch output exceeded {max_bytes} bytes.",
        )


def _default_runner(command: tuple[str, ...]) -> tuple[int, bytes, bytes]:
    result = subprocess.run(command, check=False, capture_output=True)
    return result.returncode, result.stdout, result.stderr


class GitCliHistory(CommitMetadataSource, CommitFileChangeSource, CommitPatchSource):
    """Fulfill bounded history ports by invoking Git directly."""

    def __init__(self, runner: GitRunner = _default_runner) -> None:
        self._runner = runner

    def commit_metadata(self, repository: Path, query: CommitHistoryQuery) -> list[CommitMetadata]:
        _validate_limit(query.limit)
        _validate_since_unix_time(query.since_unix_time)
        tip = _validate_sha(query.tip_sha, field_name="tip_sha") if query.tip_sha else "HEAD"
        path_args = _validate_paths(query.paths)
        command = (
            "git",
            "-C",
            str(repository),
            "log",
            "-z",
            f"--format={_LOG_FORMAT}",
            "--date-order",
            f"--max-count={query.limit + 1}",
            f"--since=@{query.since_unix_time}",
            tip,
            *(_with_path_separator(path_args)),
        )
        stdout = self._run(command)
        return _parse_commit_metadata(stdout)

    def commit_patch(self, repository: Path, request: CommitPatchRequest) -> RawCommitPatch:
        commit_sha = _validate_sha(request.commit_sha, field_name="commit_sha")
        parent_sha = _validate_sha(request.parent_sha, field_name="parent_sha")
        _validate_max_bytes(request.max_bytes)
        path_args = _validate_paths(request.paths)
        command = (
            "git",
            "-C",
            str(repository),
            "diff",
            "--no-color",
            "--no-ext-diff",
            "--binary",
            parent_sha,
            commit_sha,
            *(_with_path_separator(path_args)),
        )
        stdout = self._run(command)
        if len(stdout) > request.max_bytes:
            raise GitHistoryPatchTooLargeError(command, request.max_bytes, len(stdout))
        return RawCommitPatch(commit_sha=commit_sha, parent_sha=parent_sha, patch=stdout)

    def commit_file_changes(
        self, repository: Path, query: CommitHistoryQuery
    ) -> list[CommitFileChange]:
        _validate_limit(query.limit)
        _validate_since_unix_time(query.since_unix_time)
        tip = _validate_sha(query.tip_sha, field_name="tip_sha") if query.tip_sha else "HEAD"
        path_args = _validate_paths(query.paths)
        command = (
            "git",
            "-C",
            str(repository),
            "log",
            "--numstat",
            "--find-renames",
            "-z",
            "--format=%H%x00%ct%x00",
            "--date-order",
            f"--max-count={query.limit + 1}",
            f"--since=@{query.since_unix_time}",
            tip,
            *(_with_path_separator(path_args)),
        )
        return _parse_file_changes(self._run(command))

    def _run(self, command: tuple[str, ...]) -> bytes:
        try:
            returncode, stdout, stderr = self._runner(command)
        except OSError as error:
            raise GitHistoryError(command, None, str(error)) from error
        if returncode != 0:
            raise GitHistoryError(command, returncode, stderr.decode(errors="replace"))
        return stdout


def _parse_commit_metadata(stdout: bytes) -> list[CommitMetadata]:
    if not stdout:
        return []
    fields = stdout.split(b"\0")
    if fields[-1] == b"":
        fields.pop()
    if len(fields) % 6 != 0:
        raise GitHistoryValidationError(
            "Git log output was not a whole number of metadata records."
        )

    commits: list[CommitMetadata] = []
    for index in range(0, len(fields), 6):
        sha = _decode_field(fields[index], "sha")
        parents = _decode_field(fields[index + 1], "parent_shas")
        committed_at = _decode_field(fields[index + 2], "committed_unix_time")
        author_name = _decode_field(fields[index + 3], "author_name")
        author_email = _decode_field(fields[index + 4], "author_email")
        subject = _decode_field(fields[index + 5], "subject")
        commits.append(
            CommitMetadata(
                sha=sha,
                parent_shas=tuple(part for part in parents.split() if part),
                committed_unix_time=int(committed_at),
                author_name=author_name,
                author_email=author_email,
                subject=subject,
            )
        )
    return commits


def _parse_file_changes(stdout: bytes) -> list[CommitFileChange]:
    if not stdout:
        return []
    fields = stdout.split(b"\0")
    if fields[-1] == b"":
        fields.pop()
    changes: list[CommitFileChange] = []
    index = 0
    while index < len(fields):
        sha = _decode_field(fields[index], "sha")
        committed_at = _decode_field(fields[index + 1], "committed_unix_time")
        if not _SHA_PATTERN.fullmatch(sha) or fields[index + 2] != b"":
            raise GitHistoryValidationError("Git numstat output had an invalid commit header.")
        index += 3
        while index < len(fields) and not _SHA_PATTERN.fullmatch(
            fields[index].decode(errors="replace")
        ):
            fields[index] = fields[index].lstrip(b"\n")
            if not fields[index]:
                index += 1
                continue
            additions, separator, remainder = fields[index].partition(b"\t")
            deletions, separator2, path = remainder.partition(b"\t")
            if not separator or not separator2:
                raise GitHistoryValidationError("Git numstat output had an invalid file record.")
            if additions == b"-" or deletions == b"-":
                index += 1
                continue
            try:
                previous_path = None
                if not path and index + 2 < len(fields):
                    previous_path = _decode_field(fields[index + 1], "previous_path")
                    path = fields[index + 2]
                    index += 2
                elif (
                    index + 1 < len(fields)
                    and b"\t" not in fields[index + 1]
                    and not _SHA_PATTERN.fullmatch(fields[index + 1].decode(errors="replace"))
                ):
                    previous_path = _decode_field(path, "previous_path")
                    path = fields[index + 1]
                    index += 1
                changes.append(
                    CommitFileChange(
                        commit_sha=sha,
                        committed_unix_time=int(committed_at),
                        path=_decode_field(path, "path"),
                        additions=int(additions),
                        deletions=int(deletions),
                        previous_path=previous_path,
                    )
                )
            except ValueError as error:
                raise GitHistoryValidationError(
                    "Git numstat output had invalid line counts."
                ) from error
            index += 1
    return changes


def _decode_field(value: bytes, name: str) -> str:
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError as error:
        raise GitHistoryValidationError(f"Git returned invalid UTF-8 for {name}.") from error


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= _MAX_COMMIT_LIMIT:
        raise GitHistoryValidationError(f"limit must be between 1 and {_MAX_COMMIT_LIMIT}: {limit}")


def _validate_max_bytes(max_bytes: int) -> None:
    if max_bytes <= 0:
        raise GitHistoryValidationError("max_bytes must be positive.")


def _validate_since_unix_time(since_unix_time: int) -> None:
    if since_unix_time <= 0:
        raise GitHistoryValidationError(f"since_unix_time must be positive: {since_unix_time}")


def _validate_sha(value: str, *, field_name: str) -> str:
    if not _SHA_PATTERN.fullmatch(value):
        raise GitHistoryValidationError(f"{field_name} must be a Git SHA: {value}")
    return value


def _validate_paths(paths: tuple[str, ...]) -> tuple[str, ...]:
    validated: list[str] = []
    for path in paths:
        normalized = PurePosixPath(path).as_posix()
        if (
            not path
            or "\\" in path
            or normalized in {"", "."}
            or path != normalized
            or normalized.startswith("/")
            or any(part == ".." for part in PurePosixPath(normalized).parts)
        ):
            raise GitHistoryValidationError(f"paths must be repository-relative: {path}")
        validated.append(normalized)
    return tuple(validated)


def _with_path_separator(paths: tuple[str, ...]) -> tuple[str, ...]:
    if not paths:
        return ()
    return ("--", *paths)
