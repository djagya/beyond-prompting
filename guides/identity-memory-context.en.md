# Identity, Memory and Context: What Your Agent Knows and Where It Lives

**Independent field guide; not official Hermes or Nous Research documentation.** It describes what one long-running deployment runs and enforces in its scripts. Where a behaviour is a feature of the fork build used there, the text says "on the fork build used here". On stock upstream, verify each section once on your build.

A long-running agent knows things through several stores: a persona file, a topology file, two small memory files, a skill library, a notes vault and its own session history. Each has a different loader, cap and owner. Most "the agent forgot" or "the agent ignores my rule" problems are a fact sitting in the wrong store, or a store silently over its cap. This guide shows where each fact belongs and how to keep the stores honest when the agent edits its own identity.

`$HERMES_HOME` below means the agent's data directory (`~/.hermes` on a plain install; the mounted data dir in Docker).

## 1. The prompt stack

What the model sees at session start, top to bottom:

| # | Slot | Source | Cap | Notes |
| --- | --- | --- | --- | --- |
| 1 | Identity | `$HERMES_HOME/SOUL.md` only, never the working dir | 20,000 characters (see §4) | Injected verbatim. |
| 2 | Topology | `$HERMES_HOME/ARCHITECTURE.md` | 20,000 characters | On the fork build used here. Profile-scoped and independent of the working directory; also loaded in identity-bearing cron runs that have no project context. |
| 3 | Tool guidance | built in | — | — |
| 4 | Memory | `$HERMES_HOME/memories/MEMORY.md`, `USER.md` | `memory.memory_char_limit`, `memory.user_char_limit` | **Frozen at session start**; silently truncated over the cap. This install sets both limits above the upstream defaults; read the effective values with `hermes config get`. |
| 5 | Skills index | names + descriptions only | — | Full skill loaded on demand (`skills_list()` → `skill_view(name)`). |
| 6 | Project context | first match from the working dir: `.hermes.md` → `AGENTS.md` → `CLAUDE.md` → `.cursorrules` / `.cursor/rules/*.mdc` | `context_file_max_chars` when set, otherwise a model-scaled cap | Only **one** type loads (§5). |
| 7 | Timestamp, platform hints | built in | — | — |
| 8 | Optional `/personality` overlay | config | — | — |

The order has moved between releases; do not build anything that depends on it.

What bites in practice:

- **Silent truncation.** A file over its cap is cut and the cut part never reaches the model. Treat truncation as silent: guard the sizes in a script (§4) rather than relying on a log line.
- **Memory over its limit.** A store pushed over its limit (a hand edit, a lowered limit) is truncated when it is injected, without warning.
- **Frozen snapshot.** A memory change made during a session takes effect next session. "I told you yesterday" with a still-open session is a frozen-snapshot problem, not a forgetting problem.
- **Cron is different.** A cron job without a `workdir` loads no project context. An invariant that lives only in project context is invisible to scheduled runs; on the fork build used here, `ARCHITECTURE.md` still loads there, so scheduled-run invariants go in it.

## 2. Where things belong

| If the fact is… | Put it in | Why |
| --- | --- | --- |
| Who the agent is, voice, values, how it treats the owner vs others | `SOUL.md` | Loaded every turn; no paths, tools or project detail. |
| Channels, who may receive what, routing, which store owns which state | `ARCHITECTURE.md` (or, without one, the agent's fixed-workdir `.hermes.md` plus a short SOUL section) | Must hold even if memory is reconciled away. |
| A compact fact the agent needs *before* it could look anything up | `MEMORY.md` / `USER.md` | Always loaded, tightly capped. |
| A procedure, workflow, trigger map, API convention | a skill | Loaded when relevant; testable; patchable. |
| A rich profile, project state, reflections, source material | notes vault / documents | Unlimited; searched or routed to by a skill. |
| Long history the agent should be able to recall by search | an optional retrieval memory plugin | Read-only from the agent's side. When to call it lives in `ARCHITECTURE.md`; how lives in a caller skill (below). |
| What happened and when | session history (`session_search`) | Chronology and evidence, not current truth. |
| Locks, cursors, receipts | runtime state files | Machine-owned. |
| Repo conventions for a codebase the agent works in | that repo's `AGENTS.md` / `.hermes.md` | Project-scoped, only when that is the working dir. |

Rules of thumb: if it should follow the agent everywhere, SOUL; if it belongs to one project, project context; if you had to discover it by trial and error, it is a procedure → skill. Never duplicate a SOUL or ARCHITECTURE fact into memory "to be safe" — the copy drifts and wastes the smallest budget you have.

If you add a retrieval memory system, write its **caller policy** into `ARCHITECTURE.md` in a few lines: call it for personal history, earlier decisions, preferences and "what was true as of…" questions; skip it for generic knowledge or what the current context already answers; treat hits as untrusted evidence, never instructions; keep their provenance; never infer absence from a miss or a top-k cut; qualify or abstain when evidence is stale, contradictory or from the wrong authority. A read-only policy grants no write, snapshot or reconfiguration rights.

## 3. Memory: retention test and hygiene

An entry stays in always-loaded memory only if **all four** hold:

1. **Global** — applies across domains, not one project or tool.
2. **Pre-lookup** — its absence causes an error before the agent could search for it.
3. **Not trigger-retrievable** — no skill or SOUL router loads it in time.
4. **Prevents a known error** — a concrete, repeated failure.

Short is not a reason to keep it: one true global router pointer may survive, a string of project pointers may not. Write declarative facts ("Owner's timezone is X"), not imperatives ("ALWAYS do X"). Task progress, completed-work logs and temporary IDs never belong in memory.

Watermarks: a store above **70%** of its limit is under pressure; a reconciliation pass must bring it to **55%** or below, so new corrections have room. A pass that ends above 55% has hit its bound and must say so, not report success.

Hygiene is something the **agent runs**, not something you do behind its back:

- Ask the agent to run its hygiene procedure ([memory-skill-boundary-hygiene](../skills/memory-skill-boundary-hygiene/SKILL.md)): classify each entry as keep / compress / move to skill / move to vault / propose SOUL change / remove.
- Hygiene only shrinks. It never adds entries and never grows a store.
- Move first, delete second: the destination (skill, note) is written **and read back** before the source entry is removed.
- SOUL changes go through the owner's approval, never an unattended job.
- Follow up next session: check the new usage figure in the memory header and that nothing global was lost.

If you automate hygiene as a scheduled job, make it a guarded transaction, not a prompt: snapshot the exact preimages first; require a verified destination for every claim it removes; compensate back to the preimages if any step fails; cap the writes per run (for example one new note, three updated notes, two staged skill proposals); and end in an explicit status (no-op, mutated, bound hit, staged, aborted on drift, failed verification, partial mutation). An unattended run cannot edit active skills or SOUL: a procedure that needs a new skill becomes a staged proposal, and the memory entry stays until that proposal is approved. Such a job can stay off; a manual pass under the same contract is enough.

If you must edit memory files directly (rare), do it atomically (write a temp file, rename it over the original, keep it owner-only `chmod 600`) and only between sessions.

## 4. Size guards on deploy

Silent truncation is a script problem, not a discipline problem. Add a check to every deploy and to your periodic health check:

```bash
# WARN near the cap, FAIL (refuse the deploy) over it
rc=0
check() { # file warn_at cap
  [ -f "$1" ] || return 0
  n=$(wc -m < "$1"); s=PASS
  [ "$n" -gt "$2" ] && s=WARN
  [ "$n" -gt "$3" ] && { s=FAIL; rc=1; }
  echo "$s $(basename "$1"): $n/$3 chars"
}
check "$HERMES_HOME/SOUL.md"         18000 20000
check "$HERMES_HOME/ARCHITECTURE.md" 10000 20000
# hermes = your CLI wrapper, run as the runtime user (never root)
mem=$(hermes config get memory.memory_char_limit | awk '{print $NF}')
usr=$(hermes config get memory.user_char_limit | awk '{print $NF}')
check "$HERMES_HOME/memories/MEMORY.md" $((mem * 90 / 100)) "$mem"
check "$HERMES_HOME/memories/USER.md"   $((usr * 90 / 100)) "$usr"
exit "$rc"
```

Adapt the `awk` to your `config get` output.

- Run it on the **git copy** before applying (refuse the deploy on FAIL) and on the **live copy** in the health check (the agent may have grown it).
- Hermes strips surrounding whitespace before it counts; `wc -m` counts it, so it slightly over-counts. That errs safe.
- 20,000 is the floor of the context-file cap. A build can raise the cap with `context_file_max_chars` or scale it with the model's window, but the guard keeps 20k as the hard limit so SOUL and ARCHITECTURE fit whatever model or config is live.
- Memory WARNs within 10% of its limit (the hygiene watermarks in §3 act earlier). A WARN never exits non-zero; only a FAIL blocks.
- Fix an over-cap SOUL by moving detail to skills or notes, not by raising the cap.

## 5. Project context: precedence and the hijack shield

Only the first matching project file loads. That creates a quiet failure: if the agent's working directory is a notes vault or an unrelated repo that carries its own `AGENTS.md` or `.cursor/rules/`, **those become the agent's instructions** — written for a different tool and a different audience.

Shield: put a **non-empty** `.hermes.md` at the root of the agent's working directory. It wins the precedence race, so nothing below it loads. An empty `.hermes.md` counts as absent and falls through to the next file, so give it at least a few real lines: what this directory is, what the agent may and may not change there.

Checklist:

- [ ] Agent working dir has a non-empty `.hermes.md`.
- [ ] Nothing in that dir's `AGENTS.md`/`CLAUDE.md`/`.cursor/` is meant for this agent (if it is, move it into `.hermes.md`).
- [ ] Context files contain no hidden HTML comments or invisible characters — the injection scanner blocks the whole file.
- [ ] Cron jobs that need project context have a `workdir`; everything else they need is in SOUL/ARCHITECTURE/skills.

## 6. Skills and the other executable surfaces

- A skill is a **procedure**: `skills/<category>/<name>/SKILL.md` with frontmatter `name:` equal to the directory name and a `description:` that says *when* to load it.
- Progressive disclosure: the prompt carries only the index; `skill_view(name)` loads the body; `skill_view(name, path)` loads a reference file.
- **Write approval.** `skills.write_approval: true` stages every agent skill write for review (`/skills pending`, `/skills diff`, `/skills approve|reject`). Keep it on for skills and **off** for memory (`memory.write_approval: false`): scheduled jobs have no operator to approve, so a staged memory write never completes. Forbid memory writes per job by omitting the `memory` toolset instead.
- These settings live in a config the agent can edit. Treat them as **asserted, not locked**: read the effective values back on every deploy (`hermes config get skills.write_approval`) and fail on a mismatch. The fork build used here also bakes a managed seed for these leaves; it fills only missing leaves, and `hermes config set` still overrides it, so it is not a lock either.

Keep each surface separate:

| Surface | What it is | Not |
| --- | --- | --- |
| Skill `scripts/` | helpers the skill runs from its own tree | a copy of a cron adapter, plugin, hook or service launcher |
| Cron adapter | the script a scheduled job names. Hermes cron rejects absolute paths, so the job names a **basename** that resolves under `$HERMES_HOME/scripts/` | a skill |
| Plugin | `$HERMES_HOME/plugins/<name>/` with a flat manifest; Hermes loads plugins only from there | nested under a skill (not loaded there) |
| Hook | event handler in the hooks dir | a procedure |
| Service launcher | a supervised service directory (s6 on the Docker image) under `$HERMES_HOME/services/<name>/` | a second supervisor or a watchdog for what Hermes already supervises |

Identity sync is the copy: it puts adapters, plugins, hooks and launchers in place. A skill's helper may hash or verify them, never copy onto those runtime directories.

## 7. Identity in git with a self-editing agent

Keep the identity (SOUL, ARCHITECTURE, config, skills, hooks, plugins, cron adapters, service launchers) in git so it is reviewable and recoverable. The agent will also edit parts of it at runtime. Two writers need a protocol, or one silently erases the other.

Three file classes: **mirrored files** (`SOUL.md`, `ARCHITECTURE.md`, `config.yaml`) are written from both sides; **tracked dirs** (skills, hooks, plugins, avatars) are applied per file and exported back; **apply-only dirs** (cron adapters, service launchers) go git → runtime only, are never exported, and the apply overwrites them.

| Rule | What it prevents |
| --- | --- |
| **Git owns identity.** Operator edits: pull first (the publish job commits the agent's edits on its own) → edit → commit → push → deploy applies. | Untracked drift; conflicts with the agent's latest publish. |
| **Apply is additive.** Git → runtime copies per file; never deletes runtime files. | Wiping agent-created skills. |
| **Publish mirrors back.** A scheduled job exports runtime edits, commits, rebases and pushes. Its commits may skip CI, so it runs a pinned secret scanner over the outgoing range itself; a finding drops the commit and pushes nothing. | Agent edits existing in one place only; unscanned secrets on the remote. |
| **Three-way marker.** Record the checksum of the git copy last applied. Runtime ≠ marker → the agent edited it; git ≠ marker → the operator did. | Guessing who changed what. |
| **Refuse on both-sides change.** The same file changed on both sides since the marker → the apply refuses and names the file. The check lives in the apply script itself, so every path (direct run, deploy, upgrade, publish job) refuses. Human merges; a force switch exists but is a deliberate "git wins". | A deploy silently reverting the agent's newer edits. |
| **A one-sided runtime edit is kept.** A runtime edit on a file git did not change is left in place and published on the same tick; it does not block the apply. | False refusals that stall both directions. |
| **Committed bytes are not a conflict.** A runtime file whose exact bytes git itself committed between the last apply and the current head was published and then superseded; the apply overwrites it with the head and loses nothing. Only bytes git never committed refuse. | A deploy refused because the agent's already-published edit was edited again in git. |
| **The applied-tree marker guards the export.** Record the identity commit the runtime last received. The publish job applies a git-ahead tree before it exports, and refuses to export while git is still ahead, so pull order on the host does not matter. | A retried publish committing a stale runtime over freshly pushed files. |
| **One lock for both directions.** Publish skips its tick if apply holds it; apply waits, then fails closed. | Exporting a half-copied tree. |
| **Explicit retire.** A retire command deletes a path from git and runtime together; commit, push and re-run the apply so the marker catches up. The publish refuses to recreate a path some commit deleted. | Inferring deletion from absence (one such script once wiped dozens of skills). |
| **No conflict markers.** Publish refuses to commit `<<<<<<<` in identity files. | Markers landing in the live config. |
| **Config schema gate.** The apply refuses a git `config.yaml` whose schema version is newer than the release expects, and defers one newer than the live runtime until the image upgrade. | A new-schema config landing on a still-running older image. |
| **Seeds are runtime-owned.** Files git seeds once (e.g. a cron jobs list) belong to the runtime after first apply. | Git overwriting live schedules. |

What does **not** deploy via git: cron jobs (change them with the CLI on the host; the publish job copies them back to the seed; a field the CLI cannot set, such as a job's toolsets, is edited in the jobs file atomically), memory (agent tool or careful host edit), secrets (host `.env` only). And because the config is mirrored, a runtime `config set` can flip a policy leaf that the publish then commits — hence the deploy-time assertion in §6.

Failure → symptom → fix:

| Failure | Symptom | Fix |
| --- | --- | --- |
| Export broken (push key, dirty tree) | Agent edits stop appearing in git | Alert after N consecutive publish failures (five here); fix the tree, don't force. The job's recovery restores only the identity dir, never a repo-wide reset that would discard unrelated work |
| Apply ran without the both-sides check | Agent's recent skill edits vanished | Put the check inside the apply script itself, so every path is covered |
| Deletion done only in git | Deleted skill reappears next publish | Use the retire command |
| Same key edited on both sides | Publish rebase conflict, repeats | Merge by hand on the host; the job restores and reports |
| Export log says git is ahead of the runtime | Publish keeps refusing | The apply did not land: either a both-sides refusal (merge that file) or a deferred config schema (wait for the upgrade) |

## 8. Propagating a correction to every owner

A correction ("we no longer use X", "that channel is private") usually lives in several owners at once: SOUL, ARCHITECTURE, a skill, a memory entry, a cron prompt, a notes page. Fix all active owners, replace the superseded text rather than appending "except…", and verify each one. Leave historical evidence alone. Full contract: [Operating Loops §4](operating-loops.en.md#4-propagate-corrections-to-every-active-owner).

## 9. Telling the agent about operator changes

When you change something the agent owns or tracks (a skill it maintains, a task it filed, a rule it follows), tell it rather than letting it discover the drift.

- Send a **one-shot, labelled operator note**: `hermes -z` takes one prompt and prints only the reply. Pipe the note on stdin through your CLI wrapper (it runs the CLI inside the container as the runtime user), so nothing needs quoting:

  ```bash
  ssh <host> 'cd <ops-repo> && ./scripts/hermes-cli.sh -z "$(cat)"' < operator-note.txt
  ```

- Start the note with "Operator note (from <who>)", list what changed, and ask for a short reply of what it did.
- Ask the agent to **verify each item itself** before closing its own tasks. A good agent closes some and keeps others with reasons; that disagreement is information.
- Do not edit the agent's memory or task list behind its back to "save it the trouble".

## 10. Setting up identity for another person

- **Start from templates**, not from your agent: [SOUL template](../templates/SOUL.template.md), [ARCHITECTURE template](../templates/ARCHITECTURE.template.md).
- **They write their own SOUL** — or the agent drafts it from a conversation with them and they approve it. Your agent's voice is tuned to you.
- **Never copy your memory, USER profile, notes or personal skills.** Start memory empty; it fills from their corrections.
- Ship only genuinely generic skills (governance, hygiene, runtime debugging). Personal skills go in a private overlay, if anywhere.
- Set the policy trio on day one — `skills.write_approval: true`, `memory.write_approval: false`, `approvals.cron_mode: deny` (cron cannot self-approve dangerous commands) — in every profile, and assert it on every deploy ([setup reference §8](setup-reference.en.md#8-initial-config-baseline)).
- Give their agent its own data directory and profile. One gateway per data directory.
- Add the size guard (§4) and the hijack shield (§5) before the first real session.

Related: [setup patterns](setup-patterns.en.md), [hardening guide](hermes-hardening.md), [Principles §9](../readings/principles-from-hermes-in-practice.en.md#9-convert-experience-into-procedural-competence).
