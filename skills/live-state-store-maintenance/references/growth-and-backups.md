# Growth, retention and backup verification

Practice, not an official guarantee. Table and column names differ by version; inspect your schema first.

## Measure before choosing a lever

Read-only, on a copy:

```sql
SELECT name, SUM(pgsize)/1048576.0 AS mib
FROM dbstat GROUP BY name ORDER BY mib DESC LIMIT 20;   -- needs SQLITE_ENABLE_DBSTAT_VTAB
SELECT COUNT(*) FROM messages;
SELECT strftime('%Y-%m', timestamp, 'unixepoch') AS month, COUNT(*)
FROM messages GROUP BY month;                           -- adjust to your timestamp type
```

Also estimate duplication: count rows whose (session, role, tool call id, content) repeat. On long-running agents with context compaction, compaction can re-insert carried rows, so the same content appears several times — in practice this dominated growth (multiples of the canonical rows) while age-based pruning would have freed almost nothing.

Report the split: canonical rows, duplicate copies, provider/blob columns, FTS indexes, free pages.

## Levers, least destructive first

1. `hermes sessions optimize` — merges FTS segments and vacuums; no session data changes (documented).
2. `hermes sessions optimize-storage` — migrates the FTS layout to a compact form (documented). Run in a dedicated window: verified snapshot → stop every writer → baseline integrity/counts → migrate → integrity, counts and search proof → start. Do not combine with an image upgrade in one rollback domain.
3. Archive-then-prune (below).
4. Removing duplicate compaction copies in place — rewrites history rows; needs the owner's explicit approval, a verified archive and proof that display/replay uses only the retained copies.

## Archive-then-prune

Use when the live store should hold only recent history but the full history must stay minable.

1. Pick cutoff `T`.
2. Export every session whose last activity is before `T` into a separate append-only archive (idempotent upsert keyed by the original message id; deduplicate to one row per conversation item).
3. **Verify per session that every source message id resolves in the archive.** Refuse step 4 on any miss.
4. Prune with the native command (`hermes sessions prune --older-than … --dry-run` first, then for real).
5. Keep the archive in the backup set.

If the built-in auto-prune deletes directly with no archive hook, keep it **off** and assert that on every deploy.

## Backup canary

- Stage the store with the service's own engine (backup API or a stopped copy) into a staging directory outside the service's memory accounting.
- `PRAGMA quick_check` the staged file.
- Only a passing check earns the "good" tag; a failing one uploads untagged and prints `WARN`.
- Never let host SQLite open the live WAL file during backup.
- Hermes' quick pre-update snapshot skips files over 1 GiB (documented); do not treat it as a copy of a large session store.
- Very large live `quick_check` scans can hang a small host; for big stores rely on staged-copy checks.
- Quarterly: restore the latest tagged copy into a scratch location, open it with the service's engine, run a real search.

## Keep the data home clean

- Test fixtures, experimental databases and forensic copies live outside the data home.
- Maintain backup exclude lists for scratch paths and a test proving the excludes match.
- Treat every full-store copy as leased: record purpose, size, integrity evidence and a delete-after condition; delete it in the same task once that condition holds.
