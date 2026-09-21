# Repository workflow

Use the `atomic-commit` skill for every commit. It is the authoritative
procedure for choosing a coherent batch, maintaining a green exact state,
resolving untracked files, reviewing the complete staged snapshot, obtaining
human approval, and verifying the post-commit workspace.

For this repository, treat the untracked-file disposition assessment as a hard
safety boundary: every non-ignored path must be explicitly classified as
**add**, **gitignore**, or **delete**, with the chosen action performed before
staging. Ignored paths need not be listed unless the ignore rules are changing.

Do not assume a previously clean workspace is still clean without validating it.

## TDD and refactoring slice gate

Every feature, fix, or characterization slice must make its evidence explicit:

1. Before production edits, record the preflight scope, direct callers, and
   the smallest behavior to admit.
2. Add or identify the focused test, run it against the unchanged production
   code, and record the failing (red) result. If no red result can be
   established, classify the work honestly as characterization, documentation,
   or a retrospective repair rather than claiming strict TDD.
3. Make the smallest production change, run the focused test and the complete
   fast suite, and record the green result.
4. Refactor the tests for resilient behavior (and the changed production code
   for representation) while green; then rerun the fast suite.
5. Perform a scoped post-slice review covering the changed code, siblings, and
   callers. Record whether it found a follow-up or nothing to do.

Do not advance to the atomic-commit protocol until these checks are complete.
The commit summary must state the slice, red/green evidence, test-refactor
decision, post-slice review result, and untracked-file dispositions.

## MCP support-process lifecycle

During an editing or TDD session, run at most one otter-kr support server. Check
for an existing server before starting it; do not launch additional one-shot
servers alongside the owned session. The session owner is responsible for
stopping the server in a `finally`/cleanup path before the commit protocol, then
verifying the process table contains no otter-kr or FastMCP leftovers. If a
child process survives shutdown, terminate that specific child immediately and
recheck before continuing.
