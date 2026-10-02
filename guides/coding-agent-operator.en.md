# Operating Hermes with a Coding Agent

**Independent field guide; practice from one long-running deployment, not official Hermes or Nous Research documentation.**

Many operators keep their Hermes setup in a private ops repository (compose file, identity, scripts, docs) and maintain it with a coding agent such as Claude Code, Codex or Cursor. That puts two agents on one system. This guide is the working contract that kept that arrangement safe and fast: what the coding agent may do, how it proves its work, and how it stays out of the runtime agent's way.

Placeholders: `<box>` is the host that runs Hermes, `<ops-repo>` its checkout of the ops repository, `./scripts/deploy.sh` your deploy script. Adapt the names; keep the rules.

## 1. Two agents, one system

| | Coding agent | Hermes (runtime agent) |
|---|---|---|
| Role | The operator's hands on the repo and the host | A long-running agent with its own identity, memory and jobs |
| Writes | Repo files, commits, PRs, deploys run by the operator's mandate | Its own memory, skills, cron jobs and notes inside its data home |
| Session | Bounded: one task, then it exits | Continuous: chats, cron runs, background work |

Rules that follow from this:

- **Neither edits behind the other's back.** The coding agent does not rewrite Hermes' memory or skills on the host to "fix" behaviour; it asks Hermes to do it, or changes the git-owned source and deploys. Hermes does not edit the ops repo's scripts; its self-edits come back through the publish path you built for them (see [Identity, Memory and Context](identity-memory-context.en.md)).
- **Coordinate through durable channels.** A fix that belongs to another session goes to that session. A shared branch gets a heads-up before you push to it. If Hermes publishes into the same repo, tell it to rebase rather than resolving its conflict yourself.
- **Hermes is a user of your work.** Error messages, skills and scripts you ship are read by an agent. Write them for that reader ([Operating Loops §2](operating-loops.en.md#2-check-the-critical-capability-before-dispatch)).

## 2. The checkout is a dev clone, not the runtime

The laptop checkout is the source of truth for *code*. The live container, its data directory and its logs exist only on `<box>`. The most common coding-agent mistake is to read local state as runtime state.

- `docker ps` empty on the laptop means "Docker is not running here", not "the stack is down".
- A local `data/` directory (often left over from testing a sync script) is stale. Never read it for runtime facts and never edit it expecting Hermes to see the change.
- "Restart / update / deploy Hermes" means running the deploy script **on the box**, not `docker compose up` on the laptop. Local compose is only for compose-syntax or image-build debugging.
- Reach the box only over your private network (for example Tailscale), never a public IP or LAN address.
- Run the Hermes CLI through a wrapper that execs as the runtime user. The container starts as root, so a plain `docker exec` writes root-owned files that break the host's publish and backup jobs.

Paste this into the ops repo's root `AGENTS.md` (or `CLAUDE.md`) and adjust:

```markdown
## Orientation: this checkout is dev, not runtime

- The live Hermes runs on <box>. This checkout never runs it.
- Empty `docker ps` or a failing `docker info` here says nothing about the stack.
- Treat ./data/ as nonexistent: gitignored and stale. Never read it for runtime
  state, never edit it, never deploy from it. The live data dir is on <box>.
- "Deploy / restart / update Hermes" means `./scripts/deploy.sh` run on <box>
  over SSH. Never `docker compose pull/up/restart` hermes by hand, here or
  there: that skips the deploy guards and drops supervised service links.
- Box access: private network only (`ssh <box>` via the tailnet). Never the
  public or LAN address. If the host name is ambiguous, ask. If SSH prints an
  approval URL (check mode), wait for the owner to approve it, then reuse the
  connection (ControlMaster) so later commands do not re-prompt.
- A quoted remote command does not receive a local heredoc. Use
  `ssh <box> "docker exec -i <container> bash -s" <<'EOF' ... EOF`; a pipe or
  command after the closing quote runs locally. `ssh -t` keeps remote output
  in order.
- Hermes CLI only via `./scripts/hermes-cli.sh` (runs as the runtime user);
  never `docker exec` as root.
- Runtime memory, cron jobs and live config change on <box>, not via git.

## Working on the repo

- Done means committed and pushed: run the test battery, `git pull`, commit
  (Conventional Commits, task scope only; never secrets, data/ or scratch),
  push, and state the branch and commit. Ask first only when a change is
  irreversible or destructive beyond the task.
- Before editing hermes/identity/, `git pull` first: the box's publish job
  commits Hermes' own edits there.
- Helper scripts stay inside this checkout: .scratch/ (gitignored) for
  one-offs, scripts/ for keepers. Never /tmp, on the laptop or the box.
- Bash orchestrates (docker, git, ssh); structured-data logic is a tested
  Python module. A one-line `python3 -c` is fine; a heredoc program is not.
- A change to compose, scripts or host config updates its doc in the same
  commit.
```

Why: an agent that believes the stack is down "fixes" it locally, or deploys stale data over live state.

## 3. Mandate: what the agent finishes alone

Write the mandate down once, in the repo or the agent's memory, so it does not ask at every gate.

**Delegate end to end** (practice that worked): review, merge, build/publish the image, pin it and deploy, when tests and CI are green. "Done" means committed and pushed (after running the test battery and a `git pull`), deployed where the task requires it, and verified, with the branch and commit reported. Uncommitted or unpushed work is not done. Ask first only when a step is irreversible or destructive beyond the task.

**Keep with the owner**: policy and security posture (approval modes, allowlists, exposure), network topology, credential creation and rotation, anything public or outward-facing, irreversible deletion, and retiring an upstream setting the owner chose.

**Permission brakes are features.** When the coding agent's permission system blocks a destructive command, the agent stops and reports; it does not rephrase the command to slip past the check.

**Review before merge, even for your own fork.** Parallel read-only reviewers once found real bugs in an image that was already built and pinned; it did not ship. A pin is a review checkpoint, not proof of review.

## 4. CI discipline

CI is the last gate, not the bug finder.

1. **Run CI's exact commands locally.** Copy them from the workflow file. `ruff check` passing while CI runs `ruff format --check` left `main` red; "similar" commands are different commands.
2. **Keep a local pre-push gate** that runs the workflow's own jobs (or their commands) against the head you are about to push. A fork that pushed to CI to discover failures burned most of its CI minutes on one PR with dozens of pushes.
3. **Prove the gate can fail (negative control).** Run it once on a known-bad head and see a non-zero exit. A local gate reported PASS for months because a child process in `ssh <box> bash -s` read the rest of the script from stdin; bash hit EOF and exited 0 before the check ran. Redirect such children from `/dev/null`.
4. **Watch CI after every push** until it is green or you know why it is red. Do not stack further pushes on an unknown result.
5. **Disable irrelevant workflows in a fork** (upstream release, docs deploy, issue bots) so red signals mean something.
6. **Know the traps** (GitHub Actions shown; check your CI):

| Trap | Symptom | Fix |
|---|---|---|
| A skip-CI token (`[skip ci]`) quoted anywhere in the commit message | The fix itself never ran CI | Never write the token in a subject or body unless you mean it |
| Empty commit to retrigger a path-filtered workflow | Nothing runs: no files changed | Re-run the workflow, or change a file in the filtered path |
| Bot publish commits use skip-CI | Secrets in automated commits go unscanned | Run a secret scan (for example gitleaks) on every push, including skip-CI ones |
| Deploy from a red `main` | Broken scripts reach the box | Deploy script refuses unless the deployed commit has green CI, allowing skip-CI only for known bot prefixes |
| A bot that publishes agent-written *code* uses skip-CI | `main` looks untested and the deploy gate refuses the next deploy | Skip-CI only for bot commits whose content the deploy already gates (identity, evidence files); code publishes run CI |
| Many CI jobs per push on a private repo | Each job bills at least a minute; frequent bot pushes exhaust the quota | One job with in-job lanes keyed on the diff, `paths-ignore` for bot-only files, cancel-in-progress, a job timeout |

The deploy gate that refuses red CI caught real issues, including bot commits outside the allowlisted prefixes that had never been tested.

## 5. One worktree per session

Shared checkouts collide: another editor's uncommitted edits end up in your commit, or another agent session switches the branch and your commit lands on the wrong one.

- Give each coding-agent session its own `git worktree` (inside the repo's ignored scratch area, not `/tmp`). The same goes for one-off helper scripts and logs: keep them in that scratch area, keepers in `scripts/`.
- Before editing files Hermes also publishes (its identity tree), `git pull` first.
- Before committing, check `git branch --show-current` and `git status`; stage paths explicitly.
- Remove a finished worktree with `git worktree remove` on a clean tree, never `rm -rf`.
- On the box, leave no uncommitted work: a dirty tree stalls Hermes' own publish job and the deploy. To persist one identity change on the box without racing the publish job, commit only the identity path and push.
- On the box, never `git stash pop` after a pathspec `stash push` that printed "No local changes to save": it pops the *top* stash, possibly someone else's, and can drop conflict markers into live config. Check `git stash list` first.

## 6. Secrets never travel through chat

- Never paste passwords, tokens or recovery codes into the agent conversation. If one was pasted, treat it as leaked: the owner rotates it.
- Pass a secret to a command through stdin or an env var loaded from a file, never as an argument (arguments show up in process lists and shell history).
- Prefer device-flow / browser logins that the owner completes, so the agent never sees the credential.
- Never `hermes config set` a custom key holding a secret: unrecognised keys land plaintext in `config.yaml`, which the publish job mirrors into git. A secret a subprocess needs goes into the host's compose `.env` and an `environment:` passthrough.
- Do not trust regex redaction of command output. A `sed` substitution without the global flag replaced only the first match on a line and leaked a token printed later. Better: never print the value.

## 7. Background watchers

Long waits (an idle gate, a build, a reboot) belong in background watchers. They need hygiene.

- Give each watcher an exit condition and a timeout; stop stale watchers before starting new ones.
- `pgrep -f deploy` matches its own wrapper's command line, so "wait until deploy is gone" never ends (one loop ran for 40 hours). Use a PID file, `pgrep -x`, or the `[d]eploy` bracket trick.
- Compare times in one clock. Host and container may log in different time zones.
- Run anything that may cut your SSH session (host package upgrades that restart Docker or the VPN) detached on the host, as a supervised unit with a log file, then re-run the deploy afterwards.

## 8. Report status in one stable shape

End every status update with the same three blocks:

```text
Done:      <item> — evidence (commit, run, check output)
Running:   <item> — what it waits on, how you will know
Needs you: <decision or action> — why only you, what unblocks
```

Carry the *Needs you* list forward in every update until each item is cleared. A decision request buried in prose is a decision nobody makes.

## 9. Batch restarts; fix what the user sees

- **One restart per window.** Merge every pending change first, then run one upgrade or deploy. Each restart of a busy agent costs a wait for idle (one to ten hours in practice) and a fresh pre-upgrade snapshot.
- **Fix the visible surface, not just the metadata.** A version was corrected in the build metadata while the branch name still carried the old one; every report kept showing the wrong version and the owner had to ask twice. Check what the user reads: names, titles, messages, dashboards.

## 10. Tell the runtime agent what changed

After a change that affects Hermes (a fixed bug it reported, a new skill, a retired job), send it a labelled one-shot note instead of editing its records:

```bash
ssh <box> 'cd <ops-repo> && ./scripts/hermes-cli.sh -z "$(cat)"' < note.txt
```

`hermes -z` is the scripted one-shot mode: one prompt in, only the reply out. `hermes-cli.sh` stands for your wrapper that runs the CLI inside the container as the runtime user. The prompt travels on stdin, so no quoting problems.

Start the note with `Operator note (from the coding agent):`, list the changes, and ask Hermes to verify each one itself before closing its own tasks and to reply with what it closed and what it kept. In one run it closed four items and kept five, with reasons; a note alone would have closed all nine.

## 11. Audits: fan out read-only, rank once

A periodic audit is one of the cases where parallel agents earn their cost ([Single Agent by Default](../readings/single-agent-by-default.en.md)): the branches are independent, read-only and breadth-first.

- Split by surface, for example: repo, box, CI and supply chain, the runtime agent's identity (SOUL, memory, skills).
- Each auditor is read-only and reports findings as *confirmed* (with evidence) or *plausible* (with the check that would confirm it).
- The controller dedupes and produces **one ranked list**. Fixes then happen in the single main session, not in the auditors.

## 12. Mine the runtime agent's own history

The runtime agent's sessions are the best bug report you have: real tool calls, real errors, real retries.

1. Export a window of sessions (`hermes sessions export <file>`; verify on your version) or query the session store read-only from a copy.
2. **Dedupe compaction copies first.** Context compaction can store the same tool rows several times; counting them raw inflates every rate.
3. Count outcomes per tool: calls, successes, error classes, retry loops.
4. Split the fixes: **agent-behaviour fixes** (skill text, error messages) go to the agent's skills; **code fixes** go to the repo. A misleading error message is both.

A sweep like this found a lease cache that ignored identity (sensitive calls ran in a research browser), leases never released at session end, and an error message that caused hours of retries.

## 13. Close every window with learnings

A maintenance window is not done when the deploy is green. Before closing it:

- Encode each fix as a script guard, test or check first; prose only for what cannot be encoded. An *expected* failure is allowlisted and prints WARN; it never exits non-zero.
- Update the canonical doc that owns each fact (setup rationale, operator manual, health checks). One home per fact; the others link to it.
- No live state in canonical docs: no pins, digests, commit SHAs, job ids, "N-1 is…" or "until <date>". Point at the file or command that proves it. Never cite a gitignored scratch path from a tracked doc, and avoid version or stage names that expire.
- Write a short dated retrospective (what bit, what was fixed, what was left), immutable after the session, and fold its durable items into canon in the same commit.
- Sweep for docs the change made stale.

The weekly version of this loop is [Weekly Learning Extraction](weekly-learning-extraction.en.md); the health-check side is in [Operations](operations.en.md).

## Session contract (paste into your coding agent)

```text
You operate a Hermes deployment through this repo. Rules for this session:
- This checkout is dev. Runtime lives on <box>; reach it only via `ssh <box>`
  over the private network. Never trust ./data/ or local docker state.
- Deploy = ./scripts/deploy.sh on <box>. Never compose up/restart by hand.
  Hermes CLI only through the wrapper that runs as the runtime user.
- git pull before editing the identity tree (Hermes publishes into it).
  Helper scripts stay in the repo's ignored scratch dir, never /tmp.
  Infra changes update their doc in the same commit.
- Mandate: you may review, merge, publish, pin and deploy when tests and CI are
  green. Ask me for policy, security posture, topology, credential rotation,
  public posts and irreversible deletion. If a permission check blocks you,
  stop and report; do not work around it.
- Before push: run CI's exact commands locally; watch CI after push. Never
  write a skip-CI token in a commit message you want tested.
- Use your own worktree. Check branch and status before each commit.
- Never ask me to paste secrets. Pass secrets via stdin; never print them.
- Do not edit Hermes' memory, skills or jobs behind its back. Change git-owned
  source and deploy, or send it a labelled one-shot operator note and ask it
  to verify before closing its own items.
- Batch changes into one restart; wait for the agent to be idle first.
- Report as Done / Running / Needs you. Carry Needs-you until cleared.
- Done = tests run, pulled, committed, pushed, deployed if required, verified,
  branch+commit stated. Uncommitted or unpushed is not done.
- Close the window: encode fixes, update canonical docs (one home per fact,
  no live pins or ids in prose), write a dated retro.
```

These are practice-derived rules from one deployment. Keep the ones that prevent a failure you can name in your own setup.
