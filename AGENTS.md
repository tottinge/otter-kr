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
