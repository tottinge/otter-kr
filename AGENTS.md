# Repository workflow

## Atomic commit disposition protocol

Before every commit, assess the workspace so the commit remains a clean, coherent
unit of work and does not capture machine-specific artifacts or unrelated tests.

1. Inspect Git status and determine whether non-ignored untracked paths exist.
2. If there are non-ignored paths, classify each as **add**, **gitignore**, or
   **delete**, and perform those disposition actions. Ignored paths do not need
   to be listed unless the ignore rules themselves are changing.
3. Review the complete diff and verify the intended unit of work and test health.
4. Stage the repository root with `git add .`.
5. Review the staged diff and check it for whitespace/errors.
6. Commit only after the staged review passes.
7. Verify the post-commit workspace is clean.

The disposition assessment is the purpose of this protocol. Do not skip it or
assume that a previously clean workspace is still clean without validation.
