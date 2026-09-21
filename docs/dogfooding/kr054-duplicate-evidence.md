# KR-054 duplicate-evidence baseline

Slice 0 measures the current `python.duplicates` response before changing its contract. The
measurement was run through the in-process MCP against the five default dogfood repositories on
2026-09-21. Fingerprint token estimates use four characters per token; they are directional, not
model billing measurements.

| repository | groups | pairs | warnings | fingerprint chars | estimated fingerprint tokens | estimated group payload tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| gitminer-dash | 26 | 41 | 0 | 13,862 | 3,466 | 5,824 |
| quizzology | 2 | 2 | 0 | 807 | 202 | 365 |
| OpenModelica | 5 | 5 | 22 | 3,330 | 832 | 1,326 |
| otter-kr | 27 | 222 | 0 | 12,129 | 3,032 | 6,368 |
| kettle | 4 | 6 | 0 | 707 | 177 | 499 |

The baseline confirms that the current normalized-AST fingerprint is useful as a deterministic
identity but expensive as a default explanation. The largest savings opportunity is in repositories
with many groups or pairs; the compact form must preserve the group identity, occurrence paths and
locations, and enough structural shape to distinguish unrelated helpers. OpenModelica also shows
that parse warnings must remain visible alongside any compact duplicate result.

Slice 0 acceptance: the existing operation remains unchanged, the measurement is reproducible,
and the next slice can compare a short digest and compact shape against this baseline.
