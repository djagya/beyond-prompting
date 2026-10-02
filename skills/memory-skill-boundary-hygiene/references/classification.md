# Classification table and report template

## Dispositions

| Disposition | Use when | Required evidence before memory changes |
|---|---|---|
| `KEEP` | Passes all four retention-test fields | Retention test written out |
| `COMPRESS_IN_PLACE` | Passes retention test but is verbose | New text contains exactly the retained claims, nothing new |
| `MOVE_SKILL` | Procedure, trigger map, tool convention | Owning skill exists, contains the full behaviour, loads on the needed trigger; read back |
| `MOVE_NOTES` | Rich personal/project context, long profile, reflection | Note written and read back |
| `KEEP_POINTER` | Destination exists but the pointer itself passes the retention test | One line naming the destination |
| `PROPOSE_IDENTITY` | Persona, voice, broad stance that should apply every turn | Owner approval of the exact delta; identity file patched and read back before source removal |
| `DROP_DUPLICATE` | Same claim retained elsewhere in memory or identity | Name the retained copy; confirm it survives this pass |
| `DROP_FALSE` | Claim is wrong | Correction evidence and source of truth |
| `DROP_REVOKED` | User explicitly withdrew it | Revocation evidence |
| `DROP_STALE` | Task progress, transient IDs, completed work | None beyond classification; never use for global preferences or environment facts |

Global preferences and environment facts cannot disappear as merely "stale".

## Common patterns

- **Many trigger → path entries** ("dreams go to folder A", "training logs to file B"): build or update one router skill; keep at most one memory pointer to it if that pointer passes the retention test.
- **Persona/voice corrections in memory**: if they should apply every turn, propose them for the identity file; remove from memory only after approved patch and read-back.
- **"Identity file lives at X"**: drop; the identity file is auto-loaded and can describe its own location.
- **Charged or personal phrases stored too literally**: decide whether it is an explicit preference (memory may fit), a taste artifact (notes), or a durable voice rule (identity proposal).
- **Audit memory against notes**: break entries into atomic claims; mark each confirmed / partially anchored / not found / interface preference / memory-only. Do not edit during an audit; propose a canonical note where a source of truth is missing.
- **Pending skill-write queue**: turning `skills.write_approval` off does not clear old staged writes; review or reject the backlog explicitly.

## Report template

```text
Mode: ASSESS | PLAN | APPLY | VERIFY
Status: NOOP | MUTATED | BOUND_HIT | FAILED_VERIFY | PARTIAL
Limits: memory=<n> chars, user=<n> chars (source: config get)

Store     before -> after   % of limit
MEMORY    <n> -> <n>        <p>%
USER      <n> -> <n>        <p>%

Moved:     <claim class> -> <destination>  (read back: ok)
Dropped:   <count> by reason class
Proposals: <identity/skill proposals awaiting approval; sources retained>
Warnings:  <drift, bounds, failed read-backs>
```
