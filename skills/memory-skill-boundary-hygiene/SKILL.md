---
name: memory-skill-boundary-hygiene
description: Classify, relocate and shrink an agent's always-loaded memory (for example Hermes MEMORY.md and USER.md) so it holds only compact facts needed before any lookup. Use when memory nears its cap, accumulates procedures or project detail, or must be reconciled with notes, skills or identity files.
compatibility: Written against Hermes Agent built-in memory (character-capped stores, frozen at session start). Confirm limits and tool behaviour against current Hermes docs.
metadata:
  author: Danil
  version: "0.1.0"
  category: memory
  tags: hermes, memory, skills, hygiene, context
---

# Memory / Skill Boundary Hygiene

## When to use

Use when:

- a memory store is near or above its character limit, or writes fail with a "would exceed the limit" error;
- memory holds procedures, trigger → path maps, project state, long profiles or task progress;
- someone asks whether memory matches the notes vault, skills or identity file;
- an operator wants the agent's memory cleaned before handover or after a busy period.

Core principle: **memory is an index, not a config dump.** Not official Nous Research documentation.

## Modes and authority

Default to **ASSESS**.

1. **ASSESS** — read memory (from the injected block or a memory-tool result already visible) and classify. No writes. Do not add and remove dummy entries to "probe" the store.
2. **PLAN** — per entry: disposition, destination, exact replacement text, expected before → after size.
3. **APPLY** — move, compress or remove only the planned entries.
4. **VERIFY** — re-read stores and destinations; report.

Changes to the identity/persona file (for Hermes, `SOUL.md`) need the owner's explicit approval for that exact delta, separate from a memory-hygiene mandate. Unattended hygiene never edits identity.

**Operator note.** If you are a coding agent or human operating someone else's agent, prefer asking that agent to run this procedure on its own memory (and following up on its report) over editing its stores behind its back. Edits from outside are invisible to its current session and easy to undo by accident.

## Layers — where a fact belongs

| Layer | Holds | Loaded |
|---|---|---|
| Identity file (`SOUL.md`) | persona, voice, durable stance; no paths or tooling | every turn |
| Topology file (e.g. an `ARCHITECTURE.md`, if your build loads one) | runtime topology, channel/privacy invariants that must not depend on memory | every turn — verify on your version |
| Memory (`MEMORY.md`, `USER.md`) | compact facts needed **before any lookup** | frozen at session start |
| Skills | procedures, routing, decision trees, tool conventions | on trigger |
| Notes / vault | rich context, profiles, project state, reflections | on lookup |
| Session history | chronology, past progress | on search; not current truth |

## Retention test

An entry stays always-loaded only if **all four** hold:

1. **Global scope** — applies across domains, not one project or tool.
2. **Pre-lookup required** — its absence can cause an error before any lookup happens.
3. **Not trigger-retrievable** — no mandatory skill or identity router loads it in time.
4. **Prevents a known error** — it stops a concrete, repeated failure.

Shortness alone is not a reason to keep. One genuinely global router pointer may survive; a row of project business cards may not. A direct, global correction from the user usually passes — do not drop it merely because the identity file says something similar.

## Watermarks (practice)

Read the live limits first (`hermes config get memory.memory_char_limit` and `memory.user_char_limit`; this install's values may differ from upstream defaults).

- **High water:** ~70–75% of a store's limit — start a hygiene pass.
- **Target after a pass:** ~55%.
- Hygiene is **shrink-only**: a pass never adds entries or grows either store. If a bound (time, destinations) prevents reaching target, report `BOUND_HIT` rather than success.

Upstream docs suggest consolidating above 80%; the lower watermark leaves headroom so a busy day does not hit the hard limit mid-task.

## Procedure

1. **Snapshot.** Record each store's entries and character counts, and the limits. Keep this private.
2. **Classify** every entry using [`references/classification.md`](references/classification.md): keep, compress in place, move to skill, move to notes, propose identity change, or drop (duplicate, false, revoked, stale progress).
3. **Split compound entries** into atomic claims; each claim gets its own disposition. Never delete a whole entry on the strength of one clause.
4. **Write the destination first.** Create or update the skill / note / identity file; then **read it back** and confirm the claim is present and loadable on the trigger that needs it. A staged or pending skill proposal does not count — keep the source until it is approved and active.
5. **Then change memory.** Replace or remove using text that identifies exactly one full entry (Hermes `replace`/`remove` match a unique substring — make it unambiguous). Write declarative facts, not imperatives ("X uses Y", not "always do Z").
6. **Re-read both stores.** Confirm sizes went down, every retained entry passed the retention test, and no unintended entry changed.
7. **Remember the freeze.** The running session still sees the old snapshot; changes take effect next session.

## Unattended (cron) hygiene

- Shrink-only, bounded (e.g. at most one new note, a few updates, a couple of staged skill proposals per run).
- Never edits identity; never edits active skills — it stages proposals and retains the source.
- Report every terminal state visibly; only a verified no-op may be silent.
- Watch the approval trap: with `memory.write_approval: true`, unattended writes are staged for review that never comes. Keep that gate off for unattended runs and restrict who can write by omitting the memory toolset from jobs that must not write.

## Deploy-time guard (operators)

On each deploy, measure both stores against their limits: print `WARN` near the high watermark, refuse (non-zero) only when a store is over its limit. Over-limit content may be rejected on write or fail to load as expected — do not rely on either behaviour.

## Output

- per store: entries and chars before → after, limit, watermark state;
- per moved claim: destination path and read-back result;
- dropped claims with reason class (duplicate / false / revoked / stale);
- identity-file proposals awaiting owner approval;
- `MUTATED`, `NOOP`, `BOUND_HIT`, or failure — never a vague "cleaned up".

Do not paste private memory content into shared reports.

## Negative controls

- Short is not the same as global.
- A pending skill proposal is not a destination.
- Task progress and completed-work logs are not memory.
- "The identity file says it philosophically" does not license dropping a direct correction.
- A memory change is not visible to the current session.
- An empty diff on one store does not prove the other store is unchanged.
