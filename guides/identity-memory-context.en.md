# Identity, Memory and Context: What Your Agent Knows and Where It Lives

**Independent field guide; not official Hermes or Nous Research documentation.** Hermes behaviour below is checked against the official docs where marked *documented*; everything else is *practice* from one long-running deployment. Version-sensitive details say "verify on your version".

A long-running agent knows things through several stores: a persona file, a topology file, two small memory files, a skill library, a notes vault and its own session history. Each has a different loader, cap and owner. Most "the agent forgot" or "the agent ignores my rule" problems are a fact sitting in the wrong store, or a store silently over its cap. This guide shows where each fact belongs and how to keep the stores honest when the agent edits its own identity.

`$HERMES_HOME` below means the agent's data directory (`~/.hermes` on a plain install; the mounted data dir in Docker).

## 1. The prompt stack

What the model sees at session start, roughly top to bottom:

| Slot | Source | Cap | Notes |
| --- | --- | --- | --- |
| Identity | `$HERMES_HOME/SOUL.md` only, never the working dir | context-file cap (documented: 20,000-char floor, scales with model context, `context_file_max_chars` overrides) | Injected verbatim after an injection scan. Empty file → built-in default identity. |
| Topology | `$HERMES_HOME/ARCHITECTURE.md` | same 20k budget (practice) | **Observed in our build (a fork); verify on yours.** Not in the upstream docs. Loaded right after SOUL and in identity-bearing cron runs. |
| Tool guidance | built in | — | — |
| Skills index | names + descriptions only | — | Full skill loaded on demand (`skill_view`). |
| Project context | first match from the working dir: `.hermes.md`/`HERMES.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules`/`.cursor/rules/*.mdc` | same cap, head/tail truncation | Only **one** type loads. Newer docs add `AGENTS.override.md` before `AGENTS.md`. |
| Memory | `$HERMES_HOME/memories/MEMORY.md`, `USER.md` | `memory.memory_char_limit`, `memory.user_char_limit` (documented defaults 2,200 / 1,375) | **Frozen at session start.** Mid-session writes reach disk, not the prompt. |
| Timestamp, platform hint, optional `/personality` overlay | built in / config | — | — |

The documented order is three tiers: *stable* (SOUL, tool guidance, skills, platform hints) → *context* (project files) → *volatile* (memory, user profile, timestamp). Exact order has moved between releases; do not build anything that depends on it.

What bites in practice:

- **Silent truncation.** A file over the cap is cut. Current docs describe a 70% head / 20% tail split with a marker where the middle was removed; check how your version cuts. The agent sees only a marker, never the lost rules, and nobody else is alerted (our build logged it at debug level only).
- **Memory over its limit.** The memory tool refuses a write past the limit (documented). A file edited by hand, or a lowered limit, can still leave it over; in our build the injected block was then truncated without warning. Verify on yours.
- **Frozen snapshot.** A memory change made during a session takes effect next session. "I told you yesterday" with a still-open session is a frozen-snapshot problem, not a forgetting problem.
- **Cron is different.** Documented: cron jobs load no `AGENTS.md`/`CLAUDE.md`/`.cursorrules` unless the job has a `workdir`. An invariant that lives only in project context is invisible to scheduled runs.

## 2. Where things belong

| If the fact is… | Put it in | Why |
| --- | --- | --- |
| Who the agent is, voice, values, how it treats the owner vs others | `SOUL.md` | Loaded every turn; no paths, tools or project detail. |
| Channels, who may receive what, routing, which store owns which state | `ARCHITECTURE.md` (or, without one, the agent's fixed-workdir `.hermes.md` plus a short SOUL section) | Must hold even if memory is reconciled away. |
| A compact fact the agent needs *before* it could look anything up | `MEMORY.md` / `USER.md` | Always loaded, tightly capped. |
| A procedure, workflow, trigger map, API convention | a skill | Loaded when relevant; testable; patchable. |
| A rich profile, project state, reflections, source material | notes vault / documents | Unlimited; searched or routed to by a skill. |
| What happened and when | session history (`session_search`) | Chronology and evidence, not current truth. |
| Locks, cursors, receipts | runtime state files | Machine-owned. |
| Repo conventions for a codebase the agent works in | that repo's `AGENTS.md` / `.hermes.md` | Project-scoped, only when that is the working dir. |

Rules of thumb: if it should follow the agent everywhere, SOUL; if it belongs to one project, project context; if you had to discover it by trial and error, it is a procedure → skill. Never duplicate a SOUL or ARCHITECTURE fact into memory "to be safe" — the copy drifts and wastes the smallest budget you have.

## 3. Memory: retention test and hygiene

An entry stays in always-loaded memory only if **all four** hold:

1. **Global** — applies across domains, not one project or tool.
2. **Pre-lookup** — its absence causes an error before the agent could search for it.
3. **Not trigger-retrievable** — no skill or SOUL router loads it in time.
4. **Prevents a known error** — a concrete, repeated failure.

Short is not a reason to keep it. Write declarative facts ("Owner's timezone is X"), not imperatives ("ALWAYS do X"). Task progress, completed-work logs and temporary IDs never belong in memory.

Watermarks (practice): reconcile when a store passes **~70–75%** of its limit and bring it down to **~55%**, so new corrections have room. The docs suggest consolidating above 80%; earlier is calmer.

Hygiene is something the **agent runs**, not something you do behind its back:

- Ask the agent to run its hygiene procedure ([memory-skill-boundary-hygiene](../skills/memory-skill-boundary-hygiene/SKILL.md)): classify each entry as keep / compress / move to skill / move to vault / propose SOUL change / remove.
- Hygiene only shrinks. It never adds entries.
- Move first, delete second: the destination (skill, note) is written **and read back** before the source entry is removed.
- SOUL changes go through the owner's approval, never an unattended job.
- Follow up next session: check the new usage figure in the memory header and that nothing global was lost.

If you must edit memory files directly (rare), do it atomically (write a temp file, rename it over the original, keep it owner-only `chmod 600`) and only between sessions.

## 4. Size guards on deploy

Silent truncation is a script problem, not a discipline problem. Add a check to every deploy and to your periodic health check:

```bash
# practice: WARN near the cap, FAIL (refuse the deploy) over it
rc=0
check() { # file warn_at cap
  [ -f "$1" ] || return 0
  n=$(wc -m < "$1"); s=OK
  [ "$n" -gt "$2" ] && s=WARN
  [ "$n" -gt "$3" ] && { s=FAIL; rc=1; }
  echo "$s $(basename "$1"): $n/$3 chars"
}
check "$HERMES_HOME/SOUL.md"         18000 20000
check "$HERMES_HOME/ARCHITECTURE.md" 10000 20000
mem=$(hermes config get memory.memory_char_limit | awk '{print $NF}')
usr=$(hermes config get memory.user_char_limit | awk '{print $NF}')
check "$HERMES_HOME/memories/MEMORY.md" $((mem * 75 / 100)) "$mem"
check "$HERMES_HOME/memories/USER.md"   $((usr * 75 / 100)) "$usr"
exit "$rc"
```

Adapt the `awk` to your `config get` output (check `--json` on your version), and run `hermes` inside the container on a Docker install.

- Run it on the **git copy** before applying (refuse the deploy on FAIL) and on the **live copy** in the health check (the agent may have grown it).
- `wc -m` counts whitespace Hermes strips, so it slightly over-counts; that errs safe.
- If your build sets `context_file_max_chars`, use that value as the cap. Read the effective memory limits with `hermes config get` (this install's limits may differ from upstream defaults).
- A WARN never exits non-zero; only a FAIL blocks.
- Fix an over-cap SOUL by moving detail to skills or notes, not by raising the cap.

## 5. Project context: precedence and the hijack shield

Only the first matching project file loads. That creates a quiet failure: if the agent's working directory is a notes vault or an unrelated repo that carries its own `AGENTS.md` or `.cursor/rules/`, **those become the agent's instructions** — written for a different tool and a different audience.

Shield: put a **non-empty** `.hermes.md` at the root of the agent's working directory. It wins the precedence race, so nothing below it loads. An empty `.hermes.md` falls through to the next file (practice; verify on your version), so give it at least a few real lines: what this directory is, what the agent may and may not change there.

Checklist:

- [ ] Agent working dir has a non-empty `.hermes.md`.
- [ ] Nothing in that dir's `AGENTS.md`/`CLAUDE.md`/`.cursor/` is meant for this agent (if it is, move it into `.hermes.md`).
- [ ] Context files contain no hidden HTML comments or invisible characters — the injection scanner blocks the whole file (documented).
- [ ] Cron jobs that need project context have a `workdir`; everything else they need is in SOUL/ARCHITECTURE/skills.

## 6. Skills and the other executable surfaces

- A skill is a **procedure**: `skills/<category>/<name>/SKILL.md` with frontmatter `name:` equal to the directory name and a `description:` that says *when* to load it.
- Progressive disclosure (documented): the prompt carries only the index; `skill_view(name)` loads the body; `skill_view(name, path)` loads a reference file.
- **Write approval.** `skills.write_approval: true` stages every agent skill write for review (`/skills pending`, `/skills diff`, `/skills approve|reject`). Recommended: on for skills, **off** for memory (`memory.write_approval: false`) — scheduled jobs have no operator to approve, so a staged memory write deadlocks them. Forbid memory writes per job by omitting the `memory` toolset instead.
- These settings live in a config the agent can edit. Treat them as **asserted, not locked**: read the effective values back on every deploy (`hermes config get skills.write_approval`) and fail on a mismatch.

Keep each surface separate (practice):

| Surface | What it is | Not |
| --- | --- | --- |
| Skill `scripts/` | helpers the skill runs | a copy of a cron adapter or plugin |
| Cron adapter | the script a scheduled job names; documented: it must resolve inside `$HERMES_HOME/scripts/` (we name it by basename) | a skill |
| Plugin | `$HERMES_HOME/plugins/<name>/` with its manifest | nested under a skill (not loaded there) |
| Hook | event handler in the hooks dir | a procedure |

## 7. Identity in git with a self-editing agent

Keep the identity (SOUL, ARCHITECTURE, config, skills, hooks, plugins) in git so it is reviewable and recoverable. The agent will also edit it at runtime. Two writers need a protocol, or one silently erases the other.

| Rule | What it prevents |
| --- | --- |
| **Git owns identity.** Operator edits: pull → edit → commit → push → deploy applies. | Untracked drift. |
| **Apply is additive.** Git → runtime copies per file; never deletes runtime files. | Wiping agent-created skills. |
| **Publish mirrors back.** A scheduled job exports runtime edits, commits, rebases and pushes. Commits may skip CI but still get a secret scan. | Agent edits existing in one place only. |
| **Three-way marker.** Record the checksum of the git copy last applied. Runtime ≠ marker → the agent edited it; git ≠ marker → the operator did. | Guessing who changed what. |
| **Refuse on both-sides change.** Same file changed on both sides since the marker → the apply refuses and names the file. Human merges; a force switch exists but is a deliberate "git wins". | A deploy silently reverting the agent's newer edits. |
| **Accept what git has committed.** A runtime file that matches any version committed since the last apply is published, not a conflict; content git never saw is. | False conflicts after a publish. |
| **One lock for both directions.** Publish skips its tick if apply holds it; apply waits, then fails closed. | Exporting a half-copied tree. |
| **Explicit retire.** A retire command deletes a path from git and runtime together; the publish refuses to recreate a retired path. | Inferring deletion from absence (one such script once wiped dozens of skills). |
| **No conflict markers.** Publish refuses to commit `<<<<<<<` in identity files. | Markers landing in the live config. |
| **Seeds are runtime-owned.** Files git seeds once (e.g. a cron jobs list) belong to the runtime after first apply. | Git overwriting live schedules. |

What does **not** deploy via git: cron jobs (change them with the CLI on the host), memory (agent tool or careful host edit), secrets (host `.env` only). And because the config is mirrored, a runtime `config set` can flip a policy leaf that the publish then commits — hence the deploy-time assertion in §6.

Failure → symptom → fix:

| Failure | Symptom | Fix |
| --- | --- | --- |
| Export broken (push key, dirty tree) | Agent edits stop appearing in git | Alert after N consecutive publish failures; fix the tree, don't force |
| Apply ran without the both-sides check | Agent's recent skill edits vanished | Put the check inside the apply script itself, so every path is covered |
| Deletion done only in git | Deleted skill reappears next publish | Use the retire command |
| Same key edited on both sides | Publish rebase conflict, repeats | Merge by hand on the host; the job restores and reports |

## 8. Propagating a correction to every owner

A correction ("we no longer use X", "that channel is private") usually lives in several owners at once: SOUL, ARCHITECTURE, a skill, a memory entry, a cron prompt, a notes page. Fix all active owners, replace the superseded text rather than appending "except…", and verify each one. Leave historical evidence alone. Full contract: [Operating Loops §4](operating-loops.en.md#4-propagate-corrections-to-every-active-owner).

## 9. Telling the agent about operator changes

When you change something the agent owns or tracks (a skill it maintains, a task it filed, a rule it follows), tell it rather than letting it discover the drift.

- Send a **one-shot, labelled operator note**: `hermes -z` takes one prompt and prints only the reply (documented). Pipe the note on stdin so nothing needs quoting:

  ```bash
  ssh <host> 'cd <repo> && hermes -z "$(cat)"' < operator-note.txt
  ```

- Start the note with "Operator note (from <who>)", list what changed, and ask for a short reply of what it did.
- Ask the agent to **verify each item itself** before closing its own tasks. A good agent closes some and keeps others with reasons; that disagreement is information.
- Do not edit the agent's memory or task list behind its back to "save it the trouble".

## 10. Setting up identity for another person

- **Start from templates**, not from your agent: [SOUL template](../templates/SOUL.template.md), [ARCHITECTURE template](../templates/ARCHITECTURE.template.md).
- **They write their own SOUL** — or the agent drafts it from a conversation with them and they approve it. Your agent's voice is tuned to you.
- **Never copy your memory, USER profile, notes or personal skills.** Start memory empty; it fills from their corrections.
- Ship only genuinely generic skills (governance, hygiene, runtime debugging). Personal skills go in a private overlay, if anywhere.
- Set the policy trio on day one — `skills.write_approval: true`, `memory.write_approval: false`, `approvals.cron_mode: deny` (cron cannot self-approve dangerous commands) — and assert it on every deploy.
- Give their agent its own data directory and profile. One agent per data directory.
- Add the size guard (§4) and the hijack shield (§5) before the first real session.

Related: [setup patterns](setup-patterns.en.md), [hardening guide](hermes-hardening.md), [Principles §9](../readings/principles-from-hermes-in-practice.en.md#9-convert-experience-into-procedural-competence).
