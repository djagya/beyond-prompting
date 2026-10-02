---
name: live-state-store-maintenance
description: Diagnose, back up, repair and shrink a live SQLite session/state store (for example Hermes state.db) without corrupting it. Use for "database disk image is malformed" errors, storage growth, full-text index problems, backup verification, or archive-then-prune retention.
compatibility: Written against Hermes Agent's SQLite (WAL-mode) session store and its `hermes sessions` / `hermes backup` commands. Schema, command names and migrations are version-sensitive; confirm against current Hermes docs and CLI help.
metadata:
  author: Danil
  version: "0.1.0"
  category: operations
  tags: hermes, sqlite, wal, fts, backup, recovery, retention
---

# Live State Store Maintenance

## When to use

- turns fail with "session storage could not be written" or logs show `database disk image is malformed`, `file is not a database`, `disk I/O error` on the state store;
- the store grew unexpectedly and someone proposes vacuum, prune, compaction or an index migration;
- a full-text (FTS) index is reported malformed or stale;
- you need to prove a backup of the store is restorable;
- retention or pruning is being designed.

Not for ordinary file cleanup or schema design. Not official Nous Research documentation.

## Modes and authority

Default to **ASSESS**.

1. **ASSESS** — read-only diagnosis **on a copy**. No writes to the live file, no service restarts.
2. **PLAN** — exact window, stop/copy/repair steps, what can be lost, rollback, acceptance checks.
3. **APPLY** — the authorized maintenance only. Stopping the service, replacing the store, pruning rows and restoring a snapshot each need explicit authorization unless the mandate names them.
4. **VERIFY** — integrity, counts and real queries on the resulting store.

A request to "optimize storage" authorizes the named operation, not a new retention policy.

## Hard rules

1. **Never open the live WAL database with a different SQLite.** A host `sqlite3` may embed a different (possibly defective) engine than the service. Diagnose a copy, made with the service's own engine or after the writer stopped.
2. **Stop → copy → repair the copy.** Never "bounce" a service that is already failing writes to the store; a restart mid-storm can overwrite pages. Stop it cleanly, copy the database plus `-wal`/`-shm`, and work on the copy.
3. **Nothing restarts the service under you.** Before any repair, disable or confirm absence of watchdogs, restart loops and cron jobs that could revive the writer. A watchdog that ignores a deliberate stop turns a repair into new corruption.
4. **Clean shutdown is a precondition.** The supervisor's stop grace (container `stop_grace_period`, s6 kill grace, etc.) must exceed the service's real drain time. A killed writer can leave FTS marked stale; the next boot then rebuilds the index under live writes.
5. **Rebuild FTS only offline.** A full-text rebuild under concurrent writers is a recurring corruption trigger in practice. Let a boot-time rebuild finish before touching the service again.
6. **Salvage beats restore when canonical tables still read.** Restoring the last snapshot discards everything since; salvaging the live file keeps history up to the break.
7. **If corruption recurs with clean shutdowns and no live rebuild, test the hardware** (overnight memory test, disk SMART) before blaming software.
8. **Keep test fixtures and scratch databases out of the data home.** Corrupt fixtures there fail snapshots and boot-time disk checks; experimental copies bloat every backup.

## Procedure

### 1. Classify state

Authoritative (sessions, messages), derived (FTS shadow tables, caches), recovery (snapshots, journals), runtime (WAL/SHM, locks, writers), waste. A failed global integrity check does not mean all layers are lost — localize first.

### 2. Inventory writers and engines

List every process that can write the store: gateway, scheduler, workers, maintenance CLI, backup helpers. For each, record the **embedded SQLite version actually loaded** (`python -c "import sqlite3; print(sqlite3.sqlite_version)"` inside the service's environment), not the package version. A defect that is concurrency-sensitive needs every concurrent writer above the fixed floor. At the time of writing, SQLite's WAL-reset fix shipped in 3.51.3 with backports in 3.50.7 and 3.44.6 — confirm against sqlite.org.

### 3. Diagnose on a copy

Follow [`references/salvage-runbook.md`](references/salvage-runbook.md) steps 1–2: make a consistent copy, run `PRAGMA quick_check` on it, and map damaged b-tree root pages to object names via `sqlite_master.rootpage`.

- Damage only in FTS shadow tables → derived; native repair or drop-and-rebuild.
- Damage in `sessions`/`messages`/schema → salvage path.

### 4. Choose salvage vs restore

| Situation | Choose |
|---|---|
| Canonical tables read; damage in derived index | Native `hermes sessions repair`, else drop FTS on the copy and let it rebuild |
| Canonical tables partly unreadable; native `repair`/`recover` refuse | SQLite `.recover` on the copy into a clean database |
| Copy unrecoverable (e.g. page 1 smashed) and history since snapshot is small | Restore last **verified** snapshot |
| Unsure | Keep both: salvage into a new file, compare counts against the snapshot, choose with the owner |

A page grafted from an older snapshot is forensic scaffolding; validate table by table before trusting it, and never swap a stitched image into service.

### 5. Repair offline, install, verify

Runbook steps 3–7: native commands first, `.recover` in a throwaway container if needed, drop FTS objects from the salvage and `VACUUM`, require `PRAGMA integrity_check` = `ok`, move the broken file aside (do not delete), remove stale `-wal`/`-shm`, match ownership, start once, let the FTS rebuild finish.

### 6. Growth and retention

See [`references/growth-and-backups.md`](references/growth-and-backups.md). In short: measure *what* is large before choosing a lever (on long-running agents, compaction duplicates often dominate, not age); try the non-destructive `hermes sessions optimize` first; run index-layout migrations (`hermes sessions optimize-storage`) in a dedicated window with writers stopped and a verified snapshot, never combined with an upgrade; prune only after archiving and verifying every message id resolves in the archive; keep built-in auto-prune off if it has no archive hook.

### 7. Backups that prove restorability

A backup job that ran is not a restorable backup. Stage the store with the service's own engine, `quick_check` the staged copy, and only then tag it as good; an unverified copy must not carry the "good" tag. Note that Hermes' quick pre-update snapshot skips files over 1 GiB (documented), so a large session store may not be in it. Drill a restore on a schedule.

## Stop conditions

Stop and report when: authoritative integrity is unknown; a snapshot cannot be verified; a writer remains on an unsafe engine; scratch space is insufficient; repair would delete authoritative rows; or a restart cannot be scheduled while the agent is idle.

## Output

- mandate, target store, window;
- writers and embedded engine versions;
- diagnosis: integrity result, damaged objects, layer;
- decision (salvage / native repair / restore) with expected loss;
- before/after: session and message counts, file sizes (db, wal, shm), integrity result;
- a real search/query smoke test result;
- recovery artifacts kept, with a delete-after condition;
- residual risk.

## Negative controls

- "Backup exited 0" is not "backup is restorable".
- Package upgraded is not engine upgraded.
- A readable `COUNT(*)` is not an intact b-tree.
- A fixed maintenance CLI beside an unfixed gateway is still a mixed writer set.
- FTS corruption is not lost conversations.
- Age-based prune freeing little is a measurement, not a reason to prune harder.
