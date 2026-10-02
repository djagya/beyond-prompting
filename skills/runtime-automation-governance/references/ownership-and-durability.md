# Ownership and durability of automation artifacts

Practice for keeping user-local automation recoverable without duplicate editable copies or needless new repositories.

## Four surfaces

| Surface | Contents | Versioned? |
|---|---|---|
| Canonical source | code, job seeds, tests, fixtures, deploy logic | yes, one owner |
| Runtime deployment | live copies under the agent's scripts/plugins/hooks/services directories | no — derived from source; never hand-edited |
| Mutable state | locks, cursors, phase JSON, retry counters | no |
| Generated output | logs, images, caches, downloads | no |

Secrets belong in none of these; reference them by name.

Runtime copies that are *apply-only* (source → runtime, never exported back) lose any in-place edit at the next deploy. If the agent is allowed to self-edit some surface, decide explicitly which direction owns it and use a mechanism that refuses when both sides changed.

## Repository-boundary probe

From the runtime context:

```bash
findmnt -T <live-path> -o TARGET,SOURCE,FSTYPE,OPTIONS
```

From a context that can see the host repository root:

```bash
git -C <repo-root> ls-files -- <path>          # tracked?
git -C <repo-root> check-ignore -v <path>      # ignored, by which rule?
git -C <repo-root> status --short -- <path>    # clean?
git -C <repo-root> log -1 --oneline -- <path>  # committed?
git -C <repo-root> branch -vv                  # pushed to upstream?
```

A missing `.git/` inside a container says nothing when the repository root sits above the mounted subtree.

## Migrating a live script into source

1. Name the domain owner (skill, existing repo).
2. Put the implementation in source under the exact runtime filename the scheduler uses.
3. Preserve executable mode and dependency declarations.
4. Deploy through the normal apply path; do not add a second `cp` step in a deploy helper.
5. Compare live bytes with source; run syntax checks and the job's own dry-run.
6. Confirm the scheduler resolves the entrypoint from a fresh context.
7. Confirm state and output still resolve to runtime paths, not the source tree.
8. Commit, push, and confirm the commit is on the remote.

## When a new repository is justified

Only when at least one holds: multiple independent consumers; its own release or deploy lifecycle; sharing outside this install; materially different access control; the existing repo deliberately excludes the artifact class; restore must happen independently. Importance, privacy or length alone do not justify one.

## Done

- one named canonical owner;
- runtime derived from it, no duplicate editable copy;
- secrets and mutable state excluded;
- syntax/tests/dry-run pass after deployment;
- scheduler or supervisor resolves the deployed entrypoint;
- tracking status known from the real repository root;
- commit present on the intended remote.
