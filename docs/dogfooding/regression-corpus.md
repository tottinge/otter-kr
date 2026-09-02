# Dogfooding regression corpus

This corpus records evidence contracts that must remain replayable. Tests and packets are the
oracles; human interpretations never replace them.

| case | replay source | contract |
| --- | --- | --- |
| focused co-change and rename | `tests/test_git_characterization.py` | commit order and `previous_path` are Git-derived |
| repeated edits and deletion | `tests/test_git_characterization.py` | bounded history is deterministic; deleted paths remain explicit |
| binary change | `tests/test_git_characterization.py` | unavailable numstat evidence is not invented |
| merge commit | `tests/test_git_characterization.py` | multiple parents are preserved |
| current Python inventory | `tests/test_python_characterization.py` | tracked files and parse warnings agree with independent AST facts |
| carrier-guard polarity and rollup | `tests/test_python_carrier_guard_characterization.py` | enclosed and early-exit forms retain their locations while sharing one normalized group |
| mature-history triangulation | `docs/dogfooding/kr038-history-triangulation.md` | revisions and query bounds are pinned |
| blind discovery protocol | `docs/dogfooding/kr039-blind-discovery.md` | analyst claims remain separate from MCP evidence |
| repeatability measure | `docs/dogfooding/kr040-operational-viability.md` | unchanged requests serialize byte-stably |

When a new discrepancy or useful edge case is confirmed, add a minimized fixture or pinned packet
here before changing production behavior. Replay runs must identify the report schema and matching
policy versions; output changes are recorded as evidence deltas rather than silently blessed.
