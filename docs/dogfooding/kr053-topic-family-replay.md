# KR-053 topic-family replay

Run date: 2026-09-20
Server: `otter-kr` FastMCP 3.4.7
Repository revision: `0eb8a2e`
Topic commit: `6515a5c73d4b6e127f797c9de4ca9c16ce4d4bcb`
Query: `git.topic_family`, `since_unix_time=1700000000`, `limit=5`

## MCP observation

The bounded replay returned `status: ok` with:

| field | value |
| --- | ---: |
| members | 5 |
| matches | 5 |
| ancestry edges | 5 |
| path transitions | 4 |
| unmatched hunks | 2 |
| termination | `limit` |

The report retained the canonical topic SHA in both `topic_sha` and `topic_metadata.sha`.
The family output is evidence of matching and traversal only; it does not identify a defect
introduction or assign causality.

## Regression observation

Before the canonical-reference fix, the same request with the accepted 7-character reference
`6515a5c` produced an empty family because the short input was used as an internal lookup key while
Git returned the full SHA. The current report normalizes the reference before walking; the focused
MCP characterization in `tests/test_server.py` preserves this contract.

The query bounds, topic revision, and report counts are the replay record. A later discrepancy
must be added as an evidence delta rather than silently changing the interpretation.
