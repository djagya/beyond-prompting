# Manifest, decision table and execution

## State machine

```text
DISCOVERED → CLASSIFIED → ARCHIVED → REMOTE_READBACK_VERIFIED → MANIFESTED
  → GLOBAL_PREFLIGHT_VERIFIED → DELETED_OR_QUARANTINED → RECEIPTED → RECONCILED
```

Never infer a later state from an earlier one.

## Invariants

1. Exact identity: normalized path + logical size + SHA-256.
2. Occurrence provenance: one archived payload may map to many source paths; keep every mapping.
3. Protected-first: declare protected roots and roles before computing candidates; unknown defaults to keep.
4. No recursive broad deletion for valuable tiers; files individually, then `rmdir`.
5. No symlink traversal; record hard-link counts; block ambiguous hard links when reclaiming space matters.
6. Immutable, hashed manifest stored durably before mutation.
7. Independent remote read-back of archives and supplements.
8. Fail closed on gaps, mismatches, ambiguous mappings, secret-bearing gap payloads or protected overlap.
9. Quiesced producers, or a quarantine phase.
10. Audit survives interruption: append-only journal or quarantine, not only a final receipt.

## Decision table

| Local state | Archive state | Protected? | Action |
|---|---|---|---|
| exact size/hash | exact member size/hash | no | verified-delete |
| exact size/hash | absent from primary, exact in supplement | no | verified-delete via supplement |
| exact size/hash | missing or ambiguous | no | blocked |
| size/hash drift | any | no | blocked |
| any | any | yes | protected |
| unknown role | any | no | keep / blocked |
| symlink or outside approved root | any | no | blocked |

## Role table (example)

| Role | Default |
|---|---|
| final / selected output | keep |
| source input / reference / control | keep |
| reproduction manifest / workflow / receipt | keep |
| candidate / rejected / raw output | delete if archived |
| repair / transfer / derived review artifact | delete if archived |
| unknown | keep / blocked |

## Manifest contents

Schema version and timestamp; approved roots and protected surfaces; archive and supplement hashes; pre-cleanup file and byte totals; per candidate: path, bytes, SHA-256, archive layer and member, archived bytes and hash; blocked entries with reasons; expected delta; policy hash. Canonicalize serialization, hash it, write `<manifest>.sha256`, store both durably and read them back.

## Closing archive gaps

1. leave gap files blocked; 2. inventory them; 3. scan for credentials, tokens, keys, credential-bearing URLs and sensitive logs; 4. sanitize only where provenance policy allows, otherwise retain locally; 5. build a separate supplement preserving source paths and hashes; 6. write its manifest and checksum; 7. upload and read back; 8. index its members; 9. rebuild the deletion manifest against both layers. Never convert "missing from archive" into "delete by root policy".

## Execution modes

**Quarantine (high risk):** move verified files into a quarantine tree on the **same filesystem** (check `st_dev` of source and quarantine parent; treat a cross-device error as a no-mutation signal), journal and fsync each move, verify quarantine inventory against the manifest, then delete quarantined files individually and remove empty directories.

**Direct unlink (durable recovery proven, producers quiesced):** after global preflight, recheck each file's size and hash immediately before unlinking; on drift, stop and report partial execution from the journal. Never claim atomicity.

## Receipt

Run id and timestamps; manifest path and hash; archive identifiers; every deleted path with bytes, hash, archive member and time; skipped/failed/blocked entries; before/after logical and allocated bytes; removed directories; journal hash. Hash the receipt, store it durably, read it back. Preserve interrupted journals.

## Reconciliation

Deleted paths absent; protected paths present with matching hashes; archives still verify; no runtime resource orphaned; references to deleted paths updated to archive locations; trackers record totals and evidence location without closing unrelated acceptance criteria; remote evidence set has 0 missing / 0 extra / 0 mismatched.
