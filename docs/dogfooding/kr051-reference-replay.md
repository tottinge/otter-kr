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

## Evidence delta — 2026-09-21

The same mature-reference query was replayed against the current immutable revisions. The MCP
reported three commits for every repository, and the direct Git oracle reported the same three
Python commits and the same unique changed-Python-path counts. Response sizes and elapsed times
are raw operational measures from one in-process session.

| repository | revision | MCP commits/files | direct commits/paths | response chars | elapsed ms | warnings |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| gitminer-dash | `6a9d5a2a743a8d5e317dfe440cf27e951930c47f` | 3 / 5 | 3 / 5 | 251,363 | 7,227.0 | 0 |
| quizzology | `52ab3d21e99be2ac64dd05499b81aa6fbb4202e0` | 3 / 2 | 3 / 2 | 38,646 | 1,094.0 | 0 |
| OpenModelica | `94185df6b625689a7cfcbc30a3a47cf4978cd51f` | 3 / 6 | 3 / 6 | 156,193 | 3,245.4 | 0 |
| otter-kr | `65fd2483a51a8eae02f3c2f05836d899575f1564` | 3 / 6 | 3 / 6 | 336,998 | 3,817.9 | 0 |

## Blind packet replay — 2026-09-21

The fixed KR-039 four-request order was replayed at the same revisions: `python.inventory`,
`python.graph_topology`, bounded `git.review_packet`, and blinded `python.term_change_evidence`
for `run`. These are raw packets only; no refactoring claims are encoded here.

| repository | inventory chars/ms (warnings) | topology chars/ms | review chars/ms | term-change chars/ms |
| --- | --- | --- | --- | --- |
| gitminer-dash | 27,186 / 112.2 (0) | 126,932 / 284.9 | 159,937 / 3,859.1 | 3,204 / 623.6 |
| quizzology | 8,866 / 20.0 (0) | 42,597 / 56.5 | 34,733 / 816.0 | 1,632 / 95.7 |
| OpenModelica | 20,603 / 61.3 (22) | 43,613 / 126.7 | 81,676 / 2,164.7 | 20,151 / 862.1 |
| otter-kr | 15,659 / 55.9 (0) | 76,453 / 181.5 | 294,084 / 3,207.2 | 5,598 / 403.7 |

All sixteen blind requests returned `status: ok`. OpenModelica's inventory retained 22 parse
warnings; the other inventory packets reported none. The packet records operational size and time,
but does not collapse them into a quality score or infer analyst conclusions.
