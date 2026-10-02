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

Runtime copies that are *apply-only* (source → runtime, never exported back — scripts and supervised-service trees) lose any in-place edit at the next deploy. Surfaces the agent is allowed to self-edit (identity files, config, skills, plugins, hooks) move in both directions and need a sync that can tell who changed what.

## Two-direction sync that refuses instead of guessing

The pattern used here, for surfaces both the operator (in git) and the agent (at runtime) may change:

- **Runtime → git (export/publish).** A scheduled job copies tracked runtime files into the repository and commits them. Config written with stable key order makes edits line-local, so different keys merge and same-key divergence becomes a visible rebase conflict, never a silent winner. Tracked skill directories refresh wholesale from runtime.
- **Git → runtime (apply).** The apply records the checksum of the git copy it last installed (a per-file marker). With that third data point it can tell an operator edit from an agent edit: an unexported runtime edit on a file git did not change is kept (and published); a file changed on **both** sides refuses before anything is touched. A runtime file whose bytes git itself committed after the last apply is stale, not an edit — overwriting it loses nothing, so it is not a conflict. A forced overwrite is an explicit, named override.
- **Order guard.** The export refuses while git is ahead of the last applied tree, so a freshly pushed change is never overwritten by stale runtime bytes; the publish job applies a git-ahead tree first. Both directions take one lock so an export never reads a half-applied tree.
- **Deletions need a command.** Apply is additive, so a git-only deletion never reaches runtime and the next export resurrects it. A retire command removes the path from git and runtime together, and the publish fails on an export that re-creates a retired path.
- **Dirty trees stall the publish.** Uncommitted work in the deployment checkout blocks the publish's rebase; recover by restoring only the synced tree, never a repo-wide reset, and refuse to commit conflict markers.

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
2. Put the implementation in source under the exact basename the scheduler uses (cron resolves `script:` under `$HERMES_HOME/scripts/` and rejects absolute paths). If the agent maintains the program live, keep it as a replicated companion instead and make the cron script a thin adapter.
3. Preserve executable mode and dependency declarations.
4. Deploy through the normal apply path; do not add a second `cp` step in a deploy helper.
5. Compare live bytes with source; run syntax checks and the job's own dry-run.
6. Confirm the scheduler resolves the entrypoint from a fresh context.
7. Confirm state and output still resolve to runtime paths, not the source tree.
8. Commit, push, and confirm the commit is on the remote.
9. Update the domain skill so it names the live entrypoint and the adapter basename.

Do not migrate while a bounded watchdog owns a live external resource unless the live launcher stays atomic and behaviourally identical.

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
