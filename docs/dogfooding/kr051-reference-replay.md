# KR-051 mature-reference replay

Run date: 2026-09-20
Server: `otter-kr` FastMCP 3.4.7
Query budget: three Python-history commits per repository (`since_unix_time=1700000000`, `limit=3`)

The replay uses the selected mature-reference corpus and records immutable revisions before any
interpretation. Direct Git commands are the independent oracle; they do not replace the MCP
packet, but provide a small check on commit and path counts. The lower bound is deliberately
explicit: Git interprets `--since=@1` as a near-present boundary, not as the Unix epoch.

## Pinned revisions and direct checks

| repository | revision | MCP commits | MCP truncated | direct Python commits | unique changed Python paths |
| --- | --- | ---: | :---: | ---: | ---: |
| gitminer-dash | `6a9d5a2a743a8d5e317dfe440cf27e951930c47f` | 3 | yes | 3 | 5 |
| quizzology | `52ab3d21e99be2ac64dd05499b81aa6fbb4202e0` | 3 | yes | 3 | 2 |
| OpenModelica | `94185df6b625689a7cfcbc30a3a47cf4978cd51f` | 3 | yes | 3 | 6 |
| otter-kr | `f820c6c02036ebd963bea11b37bb7b1179d9730e` | 3 | yes | 3 | 3 |

The independent checks were run at each pinned revision with:

```shell
git log --format=%H --max-count=3 --since=@1700000000 -- '*.py'
git log --format= --name-only --max-count=3 --since=@1700000000 -- '*.py' \
  | sed '/^$/d' | sort -u
```

## Evidence boundary

The counts above are directly observed from Git. They establish that a bounded Python-history
query has non-empty reference material at these revisions; they do not validate affinity scores,
rename identity, topic-family matches, or any design interpretation. Those remain separate MCP
queries with their own citeable outputs.

## Replay record

The revision table, query bounds, and oracle commands are the reproducibility record for this
slice. A future run must append an evidence delta when a packet disagrees with these direct facts;
it must not silently replace the pinned revision or reinterpret a discrepancy as a judgment.
