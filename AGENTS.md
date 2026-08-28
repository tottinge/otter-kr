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

## MCP support-process lifecycle

During an editing or TDD session, run at most one otter-kr support server. Check
for an existing server before starting it; do not launch additional one-shot
servers alongside the owned session. The session owner is responsible for
stopping the server in a `finally`/cleanup path before the commit protocol, then
verifying the process table contains no otter-kr or FastMCP leftovers. If a
child process survives shutdown, terminate that specific child immediately and
recheck before continuing.
