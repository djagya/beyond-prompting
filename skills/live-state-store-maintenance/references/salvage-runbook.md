# Salvage runbook for a malformed SQLite state store

Practice derived from repeated real recoveries; adapt names to your deployment. Paths use `<data-dir>` (the agent's data home, e.g. `$HERMES_HOME`) and `<scratch>` (a directory **outside** the data home with enough space for several copies). Commands that need the store's own engine run inside the agent image.

## 0. Preconditions

- Confirm nothing will restart the service: no watchdog cron, no restart loop, supervisor set to stay down.
  ```bash
  crontab -l                       # no restart/heal entry for the agent
  ```
- Check free disk (the user-facing error may blame "disk full" even when it is not).

## 1. Copy

If the service is still running and the store still opens, a consistent online copy uses the SQLite backup API **with the service's engine** (inside the container):

```bash
python -c "import sqlite3; s=sqlite3.connect('file:<data-dir>/state.db?mode=ro', uri=True); d=sqlite3.connect('<scratch-in-container>/state.copy.db'); s.backup(d); d.close()"
```

If the service is failing writes, **stop it first** (clean stop, not a restart), then copy the three files together:

```bash
cp <data-dir>/state.db <data-dir>/state.db-wal <data-dir>/state.db-shm <scratch>/
```

## 2. Scope the damage (read-only, on the copy)

```bash
python -c "import sqlite3; c=sqlite3.connect('file:<scratch>/state.db?mode=ro', uri=True); print(c.execute('PRAGMA quick_check(30)').fetchall())"
```

Map reported tree/page numbers to objects:

```sql
SELECT type, name, rootpage FROM sqlite_master ORDER BY rootpage;
```

- Only `*_fts*` shadow tables → derived damage.
- `sessions`, `messages`, `sqlite_master` → canonical damage, salvage.

## 3. Native paths first (service stopped)

Run the agent CLI as the service user, not root, against the stopped store:

```bash
hermes sessions repair
hermes sessions recover          # offline, writes a separate clean database; see --help for flags
```

Both can refuse when the corrupt pages are in the objects they must drop or read ("required table … is not completely readable").

## 4. `.recover` in a throwaway container

When the image has no `sqlite3` shell and the host's should not touch the file:

```bash
docker run --rm -v <scratch>:/out alpine:latest sh -c \
  'apk add --no-cache sqlite && sqlite3 /out/state.db ".recover" | sqlite3 /out/recovered.db'
```

`.recover` also copies corrupt index content. On `recovered.db`:

1. drop the FTS triggers, any FTS source views and the FTS virtual tables (list them from `sqlite_master`; names are version-specific);
2. drop `lost_and_found` once you have decided unattributable fragments are not needed;
3. `VACUUM`;
4. require `PRAGMA integrity_check` = `ok`;
5. compare `sessions` / `messages` counts with the last snapshot.

For structurally corrupt b-trees, one traversal mode can silently skip rows; reconcile expected id ranges with point lookups before declaring loss.

## 5. Install

```bash
cd <data-dir>
mv state.db state.db.broken-$(date +%Y%m%d)   # keep, do not delete yet
rm -f state.db-wal state.db-shm               # stale sidecars of the old file
cp <scratch>/recovered.db state.db
chown <uid>:<gid> state.db && chmod <mode> state.db   # match the original file's owner and mode
```

Start the service through its normal deploy path, once.

## 6. Let the first boot finish

The service will rebuild FTS from canonical rows. Do not restart, upgrade or run maintenance until the log shows the rebuild completed.

## 7. Verify and clean up

- `quick_check` = `ok` under the live engine (via a copy if the file is large);
- a real search returns known recent messages;
- gateway, scheduler and deliveries healthy;
- after a later backup verifies clean, delete the forensic copies and scratch directory — they are leased, not permanent.

## Large but healthy WAL

Not a repair case. Checkpoint online from a second connection **using the engine the writer runs**: `PRAGMA wal_checkpoint(TRUNCATE);`. If it returns busy, report; do not kill the writer to force it.
