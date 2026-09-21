# KR-050 planted Git characterization replay

This packet is the versioned replay manifest for `tests/test_git_characterization.py`.
It describes the fixture contract without depending on temporary-directory names or a moving
working tree.

## Manifest

| field | value |
| --- | --- |
| manifest version | `git-characterization-v1` |
| replay source | `tests/test_git_characterization.py` |
| test command | `./run_tests tests/test_git_characterization.py` |
| repository construction | `git init` in a disposable directory |
| fixture commit identity | author/committer `Fixture <fixture@example.test>` |
| fixture commit time | `2099-01-01T00:00:00Z` |
| commit-id policy | content, parent, message, identity, and fixed timestamp determine the SHA; temporary paths do not |
| independent oracle | direct `git log`, `git show --numstat`, `git diff`, and `git rev-parse` checks |

## Scenario inventory

| scenario | positive evidence | negative or boundary evidence |
| --- | --- | --- |
| focused two-file change and rename | commit order and `previous_path` | rename is not treated as a new unrelated identity |
| reproducible commit IDs | identical initial commits produce the same 40-character SHA | temporary checkout location is irrelevant |
| unrelated single-file edits | no eligible co-change pair | four single-file commits are explicitly excluded |
| repeated edits and deletion | newest-to-oldest order and deleted path | deletion remains a change record rather than disappearing |
| broad commit | six file pairs and `1 / C(4,2)` per pair | pair mass sums to one |
| binary change | binary file remains explicit in topic evidence | binary numstat does not invent line counts |
| empty repository | zero commits and zero pairs | no placeholder history is fabricated |
| fix and preimage hunks | same path with distinct hunk fingerprints | matching is not inferred from path alone |
| merge commit | two parent SHAs are retained | first-parent-only interpretation is not substituted |

## Replay rule

Run the test file at the checked-out revision of this manifest. Compare failures against the
scenario inventory and inspect the direct Git oracle named above before changing an evidence
implementation. A changed fixture invariant requires a new manifest version and a corresponding
regression-corpus entry; incidental temporary paths and generated timestamps are not evidence.
