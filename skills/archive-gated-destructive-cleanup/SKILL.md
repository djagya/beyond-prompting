---
name: archive-gated-destructive-cleanup
description: Delete caches, scratch trees, git worktrees, experiment outputs or other payloads only after classifying every child and, for anything valuable, proving it is recoverable from a verified archive. Use before any bulk, recursive or space-reclaiming delete on an agent host or data directory.
compatibility: Tool-agnostic (POSIX shell, git, any archive store with read-back). Application-managed state such as databases and checkpoint stores needs its own native procedure.
metadata:
  author: Danil
  version: "0.1.0"
  category: operations
  tags: cleanup, deletion, archives, disk, worktrees, fail-closed
---

# Archive-Gated Destructive Cleanup

## When to use

- disk is filling and someone proposes deleting a directory (especially one named `cache`, `tmp`, `old`, `backup`, `scratch`);
- removing git worktrees, leased task workspaces or forensic copies;
- pruning experiment outputs, renders, logs, delivery duplicates or generated corpora;
- cleaning up after an archive migration.

Not for files created and consumed inside one bounded command. Not for databases, package stores or checkpoint stores — use their native prune/repair commands and the state-store procedure.

Core invariant:

> A path may be deleted only when it is classified as disposable, or its exact current bytes are recoverable from a named, verified archive member — and it is not part of a protected live surface.

## Modes and authority

Default to **ASSESS**.

1. **ASSESS** — inventory and classify. No deletion, no moves.
2. **PLAN** — the deletion manifest: every candidate with its class and proof, blocked items with reasons, expected byte delta.
3. **APPLY** — delete exactly the manifest.
4. **VERIFY** — reconcile what remains.

**Authority for deletion is separate.** Permission to inspect, archive or "free some space" is not permission to delete. Deletion needs explicit authorization covering the roots or artifact class. Some directories are operator-only (for example a recovery or forensic directory); agents and cron must not delete them even when asked indirectly.

## Tiers

| Tier | Examples | Gate |
|---|---|---|
| Regenerable | package-manager caches (npm, uv, pip), build caches, dangling images | Classify; confirm the tool recreates it; delete with mandate |
| Leased scratch | task workspaces, temp trees, forensic copies, local full-store snapshots | Lease must be closed: purpose done, nothing unique inside |
| Git worktrees | per-task checkouts | `git worktree remove` on a clean tree only (below) |
| Valuable payload | experiment outputs, media, generated corpora, logs with evidence value | Full archive gate (below) |
| Unknown | anything not classified | **Keep / blocked** |

## Procedure

### 1. Freeze scope

Record approved roots, intended deletion classes, protected paths, archive destinations, and whether deletion is authorized now or only the manifest. Reject candidates outside approved roots after path normalization; never follow symlinks out of a root.

### 2. Classify children, not parents

A directory name is not a classification. A directory called `cache` can hold, side by side: the live model-weight store, voice clips awaiting ingestion, a skill's state directory, and the only copy of mail or media. List children with sizes and owners first:

```bash
du -xh --max-depth=2 <root> | sort -h | tail -40
find <root> -maxdepth 2 -type l -printf '%p -> %l\n'     # symlinks: block
```

Check references from configs, scripts, registries and notes (e.g. a model path symlinked into the weight store). Mark each child **protected**, **disposable**, **archive-then-delete** or **blocked**.

### 3. Git worktrees

- Run git from a context that can see the worktree's gitdir (inside a container, paths recorded there may be invisible to host git; run as the owning user).
- Remove only when `git -C <worktree> status --porcelain` is empty: `git worktree remove <worktree>`. The branch stays.
- Leave a dirty tree, and leave a detached HEAD whose commit is on no branch or remote (`git branch -a --contains <sha>` is empty) — report it instead.
- Never `rm -rf` a worktree or any directory inside one; that deletes tracked files and leaves stale metadata. Finish with `git worktree prune --dry-run` to review.

### 4. Leased scratch

Every scratch tree or full-copy snapshot a task creates gets a lease: creator, purpose, bytes, integrity evidence, delete-after condition. Close it **in the same task** once the condition holds (e.g. the repaired store verified and a later backup passed). A success path with undefined cleanup is incomplete. Do not collect scratch owned by an active writer, an in-progress deploy or an unresolved failure.

### 5. Archive gate for valuable payloads

1. Identity = normalized path + size + SHA-256 (not name, mtime or looks).
2. Map each candidate to an actual archive member with matching size and hash; open the real archive, not just an index CSV.
3. Independently read back the remote archive (re-download or authenticated stream) — upload success is not durability.
4. Missing from archive → stays **blocked**; close gaps with a separate, secret-scanned supplement archive, then re-read it back.
5. Build and hash a manifest; store it durably **before** the first deletion.

Details, decision table and execution modes: [`references/manifest-and-execution.md`](references/manifest-and-execution.md).

### 6. Execute narrowly

- Quiesce producers (stop, lock or snapshot) so hashes are stable.
- Run a global preflight over the whole candidate set; if any candidate drifted, delete **nothing**.
- Delete manifest-listed files individually with a just-in-time recheck; remove empty directories with `rmdir`. No `rm -rf` on approved roots for valuable tiers.
- Journal each mutation (append + fsync) so an interruption is reconstructible.

### 7. Reconcile

Deleted paths absent; protected paths present (critical hashes match); archives still verify; references to deleted local paths updated to archive locations; disk delta measured (logical and allocated bytes can differ).

## Output

Scope and authority; per-tier counts and bytes; manifest hash; blocked items with reasons; deleted count and bytes; journal/receipt location; reconciliation result; leases closed and leases left open with reasons.

## Negative controls

- A directory named `cache` is not disposable by name.
- Upload success is not remote durability; an index entry is not an archive member.
- A successful `rm` is not a verified cleanup.
- A clean `git status` in the parent repo says nothing about a worktree's unpushed commits.
- Failed attempts, mismatch reports and interrupted journals are evidence, not trash.
- Logical bytes deleted are not necessarily disk space freed.
