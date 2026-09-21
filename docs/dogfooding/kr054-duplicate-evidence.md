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

## Slice 4 — compact/full comparison

On 2026-09-21, the in-process MCP replayed `python.duplicates` and
`python.duplicates.compact` against the same five repositories. Serialized payloads were measured
with sorted, separator-minimized JSON; the percentages are directional output-size measures, not
model billing measurements.

| repository | full chars | compact chars | reduction | full groups | pairs omitted | warnings preserved | identity/citations/shapes preserved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| gitminer-dash | 66,189 | 12,862 | 80.6% | 26 | 41 | 0 → 0 | yes |
| quizzology | 3,538 | 957 | 73.0% | 2 | 2 | 0 → 0 | yes |
| OpenModelica | 16,560 | 7,150 | 56.8% | 5 | 5 | 22 → 22 | yes |
| otter-kr | 216,515 | 17,336 | 92.0% | 28 | 223 | 0 → 0 | yes |
| kettle | 6,168 | 1,851 | 70.0% | 4 | 6 | 0 → 0 | yes |

The compact operation removes expanded pair duplication and raw normalized-AST fingerprints while
retaining digest identity, occurrence paths/names/locations, bounded shape, and parse warnings.
The comparison supports the planned token-frugality goal without claiming that compact output is a
complete replacement: callers needing raw structural identity or explicit pair relationships must
continue using `python.duplicates`.

Slice 4 acceptance: compact output is materially smaller on every target, and independent
comparison confirms equal digest groups, occurrence citations, shapes, and warning counts.
