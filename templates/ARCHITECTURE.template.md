# ARCHITECTURE.md template

> **Template notes — delete this block before installing.**
> A compact, always-loaded runtime contract: topology, who may receive what, routing, and which store owns which state.
> It holds invariants that must survive even if memory is reconciled away. It is not persona (SOUL.md), not a runbook (skills), not a task log.
> Loading `$HERMES_HOME/ARCHITECTURE.md` right after SOUL was **observed in our build (a fork); verify on yours.** If your Hermes does not load it, put these invariants in the agent's fixed-workdir `.hermes.md` and a short SOUL section, and remember that cron jobs without a `workdir` load no project context.
> Keep it under ~10,000 characters (WARN) and never over the 20,000-character cap. No secrets, chat IDs, tokens or hostnames — use descriptive names.
> Guide: [Identity, Memory and Context](../guides/identity-memory-context.en.md).

---

# [Agent name] Runtime Architecture

Compact operational contract for the `[profile]` profile. It owns current topology and routing invariants; it is not personality, user memory, a task log or a substitute for runbooks.

## Precedence

- Direct, current statements from [owner] about their own channels outrank platform labels and inferred membership.
- Transport metadata ("group", "multi-user", a display name) describes the container, not who is present.
- Do not copy these invariants into MEMORY.md or USER.md.

## Channels and privacy

| Channel | Who is present | May receive | Must never receive |
| --- | --- | --- | --- |
| [Private DM with owner] | [owner] only | anything for the owner | — |
| [Shared group] | [owner, named others] | [what is shareable] | [private, financial, health, credentials] |
| [Alerts channel] | [operator] | system alerts | [conversation content] |

- Default for a new or unknown channel: treat as public until the owner confirms otherwise.
- Never forward content across channels without the owner's instruction.

## Profiles and roles

- `[profile]`: [user-facing / internal worker / research]. Reads only its own SOUL, ARCHITECTURE, config, skills and state.
- [Which profile may start or delegate to which.]

## Routing

- [Request type] → [skill or profile that owns it].
- Scheduled jobs: create or edit them from chat, then return; do not run the loop in the chat session.
- Anything not routed here: answer directly or ask.

## Durable-state ownership

- `SOUL.md`: identity, voice, behaviour invariants.
- `ARCHITECTURE.md`: this topology and routing contract.
- `MEMORY.md` / `USER.md`: compact facts needed before any lookup; never the only owner of load-bearing topology.
- Skills: procedures. Notes vault ([name]): rich state and long-form design.
- Session history: chronology and evidence, not current truth.

## Off-limits

- [Files and settings the agent must not change: e.g. approval policy, deploy pins, secrets, backup credentials.]
- [Actions that always need the owner: outward messages to new recipients, payments, deletions, restarts.]
- Identity edits (this file, SOUL.md) are proposed, then applied after owner approval.

## Lifecycle

Source of truth: [git repo / path]. Deploy applies it to `$HERMES_HOME/ARCHITECTURE.md`; agent edits are published back. Keep it small and current; history and diagnostics go to notes.
