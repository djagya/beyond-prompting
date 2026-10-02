# Running a Long-Lived Hermes: Operations Field Guide

**Operational practice from one always-on Docker deployment, not an official Hermes guarantee.** It describes what that deployment runs and checks; where a behaviour belongs to the fork build it runs, the text says "on the fork build used here". On stock upstream, verify each check once on your version.

You already have Hermes running in Docker (see [setup reference](setup-reference.en.md)). This guide covers keeping it healthy for months: what to check, what the alarming symptoms mean, how to upgrade and roll back, and how to keep state, backups and disk under control. Security controls (exposure, secrets, approvals, tool surface) live in [Hardening Hermes Agent](hermes-hardening.md); this guide links there instead of repeating them.

Placeholders: `<container>` is the Hermes container name, `<profile>` a profile (`default` for the main one), `<data-dir>` the host directory mounted as `$HERMES_HOME`, `<image>@sha256:<digest>` the pinned image. `hermes …` means the CLI run through your wrapper as the runtime user (`docker exec -u hermes <container> …`), never as root.

## 1. Health is not the same as working

A green container and `/health` prove that a process answers HTTP, not that the agent can think, reach its tools or talk on its channels. Each failure below happened with health green.

| Silent-green failure | Why it stays green | Probe |
| --- | --- | --- |
| A new image moved or dropped a binary that an MCP server's `command:` names | The server fails to start and is parked at every boot; the gateway runs without it | On every deploy, resolve each enabled stdio server's `command:` with the gateway's own PATH (`docker exec -u hermes <container> sh -c 'command -v <cmd>'`; a login shell's PATH can differ) and fail the deploy if one is missing; then `hermes mcp test <name>` |
| `config.yaml` failed to parse at boot | The gateway falls back to `.env` and defaults and keeps running, answering nothing useful | Probe this boot's log (after the last startup banner) for the "failed to process config.yaml — falling back" warning; a fresh `config get` cannot see it. Run it on every deploy |
| A secret-manager read budget was spent at boot | Secrets resolve to empty; the messaging token is missing, the platform never connects | Probe this boot's log for secret-resolution failures on messaging tokens; send a real message and watch a turn land. Track the remaining budget in the sweep |
| Provider credits or auth expired | Every turn errors; nothing crashes | Grep the agent log (`$HERMES_HOME/logs/agent.log`) for `401`, `quota`, `rate limit`, `billing`, `insufficient`; run one synthetic turn |
| A configured web search or extract backend no longer exists in the image | Tool calls fail; nothing else does | Assert on deploy that each configured backend name resolves in the running image |
| The gateway's supervised slot is down while the container is Up | Docker sees PID 1 (the supervisor) alive | `docker exec -u hermes <container> s6-svstat /run/service/gateway-<profile>` and `curl -fsS http://127.0.0.1:<api-port>/health` |
| Two gateways poll one bot token | Both processes are healthy; the platform splits updates between them | Count gateway processes (`ps -eo pid,args` in the container) and list every container that mounts `<data-dir>` (`docker inspect` → `.Mounts`). Platform "conflict" errors and dropped messages are the symptom |

Rule: **one gateway per data directory.** A sidecar built from the same image starts a second gateway from the image's service bundle.

## 2. Check cadence

Write the checks as **one sweep script**, not snippets pasted from a doc. Each check prints one row, `PASS|WARN|FAIL <check>: <detail>`; the script exits non-zero only on FAIL. An *expected* failure (a known-broken optional integration, a credential awaiting rotation) is allowlisted and prints WARN with exit 0 — habitual red trains people to ignore exit codes.

```bash
#!/usr/bin/env bash
# sweep.sh — skeleton; add one function per row
fails=0
row() { printf '%s %s: %s\n' "$1" "$2" "$3"; [ "$1" = FAIL ] && fails=$((fails+1)); }
if docker exec -u hermes <container> s6-svstat /run/service/gateway-default | grep -q '^up'
then row PASS gateway/slot up; else row FAIL gateway/slot down; fi
# disk, backup age, memory caps, MCP commands, policy keys, ... one row each
exit $(( fails > 0 ))
```

| Cadence | Checks |
| --- | --- |
| **Daily** (2 min) | Containers Up and not restart-looping (`RunningFor` not resetting); gateway slot up and `/health` answering; no fresh errors in the agent log; provider auth/quota errors; messaging platform connected; background loops (identity publish, notes sync, backup) ran and logged no FATAL; disk below ~80%; supply-chain job not red |
| **Weekly** (10 min) | Identity drift: runtime received the latest identity commit, publish still landing the agent's edits, working tree on the host clean and in sync with the remote; skills list loads without duplicates, agent-authored skills reach git, frontmatter `name:` matches the directory; `hermes cron list` — paused or erroring jobs and stale last errors (autonomous behaviour stopping is the quietest drift); both `.env` files present with the keys the stack needs; named profiles still carry the pinned safety leaves; root-owned files in `<data-dir>`; `user: "0:0"` and the sandbox security options still in compose; reclaimable images; sidecar pin-drift digest; ignore expiries |
| **Monthly** (20 min) | The full sweep script: memory files vs their char limits; `SOUL.md` / `ARCHITECTURE.md` size vs the context-file cap and the prompt budget; install-policy trio read back from the live config (see [hardening](hermes-hardening.md)); web backends resolve; every MCP command resolves; config loaded without fallback; messaging secrets resolved this boot; secret-manager budget; OOM kills in the last 24 h; overlay binaries shadowing image binaries; live hotfix receipts; jobs that must stay paused are paused; ports still bound to loopback; backup freshness and last verified database copy; cgroup PIDs/memory headroom; scratch over budget; more than live + N-1 images; runtime ownership; dirty tree. By hand: admin UIs reachable from another private-network device, OS and Docker updates pending, fork branch protection still in place |
| **Quarterly** | Restore drill into an isolated target (§6); review approval allowlists and ignore lists |

Run the sweep with all rows. A `--quick` mode that skips rows is a different check; do not record its exit 0 as the monthly sweep.

## 3. Red flags → first response

| Symptom | What it means | Do | Don't |
| --- | --- | --- | --- |
| `can't start new thread`, or the gateway died near the PID cap | The cgroup PID limit is full of leftovers; restarting the service does not free them | Recreate the container through your deploy script; then find the leak (usually a browser or a runaway tool child) | `s6-svc -u` the gateway in place |
| Gateway failing database writes (`database disk image is malformed`, `file is not a database`, `disk I/O error`) | Live state store damage in progress | Stop the container, copy the database files, repair the copy ([state-store skill](../skills/live-state-store-maintenance/SKILL.md)) | Bounce the gateway; one bounce during a write storm overwrote the database header |
| Container `Exited` after a Docker or containerd restart | The new daemon did not re-arm the restart policy while the old shutdown was still running | Run your deploy script; check every container | Assume `restart: unless-stopped` covers it |
| Agent silent, `/health` green | Provider auth/credits, missing messaging token, config fallback, or two gateways | Work the §1 table top to bottom | Recreate the container first; you lose the boot log |
| `config.yaml` repaired, agent still silent | The gateway reads config only at boot | Restart the gateway service in place (`s6-svc -r /run/service/gateway-default`) | Recreate the container for it; that empties `/run/service` |
| Kernel OOM-killed a process in the container | Usually one tool child over the memory limit; the gateway survives | Find the tool call at that time and fix the command pattern | Raise the limit as the fix |
| Memory file near or over its char limit | Over the limit every entry still loads but Hermes refuses each new memory add; only a log line says so | Ask the agent to run its memory hygiene and report what moved where ([memory hygiene](../skills/memory-skill-boundary-hygiene/SKILL.md), [identity guide](identity-memory-context.en.md)) | Edit memory behind the agent's back, or raise the limit as the fix |
| Disk filling | Images, snapshots, scratch, logs, or the session store | Classify before deleting (§8) | `rm -rf` anything named `cache` or any worktree |
| Container restart-looping | Ownership/entrypoint-user problem, or a boot check tripping on a file in the data dir | `docker logs --tail 200 <container>`; fix what the boot step names | Strip security options until it boots |
| Background job "succeeds", nothing changes | Stalled behind a dirty tree, a lock, or a refused conflict | Read its log for `refusing`/`conflict`/"git is ahead of the runtime"; resolve by hand | Force one side by default |
| Upgrade postcheck fails on an expired external token after a healthy cutover | A dead credential, not a bad image | Rotate the credential; finish the acceptance checks by hand | Roll back |

## 4. Upgrade runbook (image installs)

`hermes update` refuses on image-managed installs; you upgrade by replacing the image. Batch changes so one window carries one recreate. Record the ops repo commit the host is on before you start: rollback checks it out.

1. **Pick the target.** A specific release, pinned by digest (`<image>@sha256:<digest>`), never `latest`.
2. **Read the release notes** and diff the shipped default config. Look for **renamed or retired keys**: a renamed key is silently ignored, and an image can rewrite a topology setting to its new default. Decide each retirement deliberately; then confirm which key the running image actually reads (`hermes config get <key>` after boot). Note the config schema version (`_config_version`) the new image migrates to: it decides how rollback works.
3. **Pin and record evidence.** Commit the new digest and the release manifest together with the image's SBOM (§7). A git config schema bump belongs in the same commit; the apply refuses a newer schema before then.
4. **Do storage maintenance in its own window first.** Full-text index compaction or similar work on the session store has its own rollback and runs with every writer stopped. Never fold it into the upgrade.
5. **Preconditions.** The secret manager's read budget is not spent (the recreated gateway pulls every secret at boot; the deploy script refuses). Wait for idle: a live session can run for hours, and restarting under it loses the turn. Poll detached for "no agent, tool or cron activity for N minutes".
6. **Pre-quiesce.** Run the identity publish once so no agent edit is left unexported. Pause host-side loops (publish job, backup timer). Pause the agent (`hermes pause`), let in-flight turns drain, confirm no task-board work is running, and stop supervised writers you added yourself.
7. **Freeze ingress, then snapshot as its own step.** Stop chat ingress, then copy every SQLite file consistently (main and per-profile session stores, task boards, cron history) plus the data tree, and verify the copies (`quick_check` with the image's SQLite). Check free space first: tree size + 3× the databases + live WAL, plus 2× the new image for the pull. Do **not** chain `snapshot && upgrade`: read the snapshot result first.
8. **Stop the web UI.** It must not run against a half-migrated database.
9. **Clear the pause flag before upgrading.** The image healthcheck fails while it exists, so the container would never turn healthy. Keep the freeze through withheld ingress and paused loops instead.
10. **Upgrade** through your deploy script (pull the pinned digest, recreate). The script saves the old container's logs first (the only record of pre-upgrade crashes and OOMs) and stamps the safety leaves into every profile before the first new boot. First boot can run long index migrations; a long healthcheck `start_period` keeps it `starting`. Do not `compose up` again mid-migration. If you stopped the gateway with `hermes gateway stop`, it stays stopped across the recreate; otherwise the boot reconciler restarts gateways that were running.
11. **Probe** (§1 table, then make one evidence script the done-bar):

    ```bash
    docker inspect -f '{{.Image}}' <container>          # running image id
    docker image inspect -f '{{.Id}}' <image>@sha256:<digest>   # must match
    hermes --version
    grep -m1 '^_config_version' <data-dir>/config.yaml  # equals the image's schema
    hermes config check
    hermes doctor
    hermes mcp list && hermes mcp test <each-server>
    ```

    Also: WAL size stable, `quick_check` ok (skip the live check on a multi-GB database; the snapshot copies cover integrity), no secret-pull failures for messaging tokens in this boot's log, policy and profile shields re-asserted. Then one real chat turn, one scheduled-job canary, and one MCP read.
12. **Resume in order.** Re-link supervised services (`/run/service` does not survive a recreate: the boot reconciler rebuilds the gateway slots, anything you linked yourself is gone) → release the pause → restore the publish job → restore ingress → start the web UI → backup timer, with the first post-upgrade backup after the go.
13. **Accept** in two stages: a short validation while ingress and background loops are still paused, then an explicit go, then unfreeze. Post-migration database writes are not backward-portable.

### Rollback

Re-pinning the old digest is **not** a rollback once the new image has migrated `config.yaml` or the state database: the old image would open new indexes and triggers.

1. Check out the recorded pre-upgrade ops repo commit on the host (compose pin and release manifest revert together; clean tree required), or land a reviewed pin bump back to the previous image.
2. If the new image migrated config or databases, stop the container and restore the pre-upgrade snapshot first: database copies, **deleting the live `-wal` and `-shm` files** before placing them (a restored database next to a leftover WAL is a torn open), then the data tree (skills, profiles, memory) and the timestamped `config.yaml` and `.env` backups.
3. Run the upgrade path from the reverted tree, the gateway alone. Re-link supervised services, start the web UI, probe as above.

Everything after the snapshot is lost. Keep the N-1 image until the new one has survived a full day. `docker image prune` (dangling only) keeps a digest-pinned image; `docker image prune -a` removes every image no container uses, including N-1 — don't run it.

### Host OS maintenance window

Anything that restarts Docker (host package upgrades touching `docker`/`containerd`, a reboot) or recreates Hermes belongs in the same kind of window:

- Check the secret-manager budget and wait for idle first, as above.
- Run package upgrades **detached as a root systemd unit with a log**, because a VPN or SSH package restart drops your session mid-run:

  ```bash
  sudo systemd-run --unit=host-upgrade -p StandardOutput=append:/var/log/host-upgrade.log \
    -p StandardError=append:/var/log/host-upgrade.log \
    /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
  sudo tail -f /var/log/host-upgrade.log
  ```

- **Any Docker restart can leave Hermes stopped.** When containerd and Docker upgrade together, the old daemon can hang on stop and the new one disarms the restart policy while the slow shutdown is still running; the container then stays `Exited` through later reboots. **Always run your deploy script afterwards**, then `docker ps -a` for anything `Exited`.
- Reboot if the host asks for it.
- Run other long steps (snapshot, upgrade) detached too (`nohup … > <log>`), and read the log; never chain them with `&&` behind an SSH session.
- Host and container clocks or time zones can differ; key wait loops and log searches on UTC.

## 5. State store care

The session store (SQLite with WAL and full-text indexes) is the most fragile state you own. The procedure lives in [live-state-store-maintenance](../skills/live-state-store-maintenance/SKILL.md); the rules:

- **Clean shutdown is a precondition.** The stop grace (compose `stop_grace_period`, s6-overlay `S6_SERVICES_GRACETIME`/`S6_KILL_GRACETIME`) must exceed the gateway's drain time. An unclean exit can mark the search index stale, and the next boot rebuilds it over live writes.
- **No live index rebuild under writers.** A full-text rebuild racing active sessions was the recurring corruption trigger. On the fork build used here, the live rebuild path is disabled and index writes fail open.
- **Never open the live WAL with host `sqlite3`.** Use the image's own SQLite (its Python) in a throwaway container, or work on a copy.
- **Stop → copy → repair.** When the canonical tables still read, salvaging the live file usually keeps more history than restoring the last snapshot.
- **Growth comes from compaction duplicates, not age.** Context compaction re-stores tool output; age-based pruning frees little. This deployment turns session auto-prune off (transcripts are the history) and reclaims space in a separate index-compaction window with every writer stopped. If you ever prune, archive first and verify every archived message id resolves.
- **Keep fixtures and experiments out of the data home.** Deliberately corrupt test databases broke a snapshot and crash-looped a new image whose boot check opens every SQLite file there; experimental databases inflated each snapshot by tens of GB.
- **Recurring corruption with clean shutdowns and no live rebuild:** run a memory test overnight before blaming software.
- **No gateway watchdog.** A host-side restarter that SIGKILLed the gateway, silently revived a recurring fault and restarted a deliberately stopped container mid-repair was removed. The accepted trade-off: a gateway left wanted-down inside a running container has nothing acting on it, because Docker's restart policy fires only on container exit. Detection is the daily check and the agent going quiet; recovery is by hand.

## 6. Backups that restore

"The backup ran" is not "the backup restores".

- **Stage a verified copy.** Copy each database with SQLite's backup API inside the image (a one-shot helper container from the same digest, with an explicit entrypoint so it does not start a second gateway), stage it outside the data bind mount, run `PRAGMA quick_check` on the staged copy, and only then mark it good. Never tag an unverified copy as the good one; a tagged copy once turned out corrupt.
- **Canary row in the sweep:** last backup age, last verified database copy, and no FATAL in the backup log. A run that hit unreadable files is a WARN, not a pass.
- **Exclude lists need a test.** Logs, package caches, snapshots, scratch, worktrees and installed dependencies are excluded; credentials, memory, sessions, tokens and the verified database copy are included. A test asserts both lists so a refactor cannot silently drop a path.
- **Keep the backup repository's password and keys on the host**, not mounted into the agent container, so the agent cannot prune its own backups (controls: [hardening](hermes-hardening.md)). The nightly job prints a prune dry-run only; a real prune is an operator act.
- **Weekly structural check** of the repository, and a **quarterly drill:** restore a known file and the database into an isolated target (never the live home), open it, and run the acceptance checks. If you cannot, the backup is theatre.

## 7. Supply chain and fork release discipline

Policy and controls are in [hardening](hermes-hardening.md); the operating loop:

- A **digest pin is a review checkpoint, not a vulnerability feed.** Commit an SBOM (for example Syft or Trivy CycloneDX) per pin, in the same commit as the pin, and rescan the committed SBOMs daily against the current advisory database without pulling images. Advisories for a fresh image often land hours after publish. The deploy refuses a pin that has no SBOM file.
- **Pins move only through one path:** a bump script → human review of the diff → SBOM → one commit → deploy. No automatic image-update PRs; they would fight the release manifest.
- **Drift:** floating sidecar tags are a weekly digest, not a page. For the Hermes image, a newer release, a moved release branch or a moved registry digest fails the watch.
- **Admission:** new images, Dockerfile bases and CI actions must be on an allowlist; actions stay pinned to a full commit SHA.
- **Ignores are rows, not blankets:** one `(advisory, image)` row with a reason and an expiry capped at about a month. A finding that a pin bump fixes is a bump, not an ignore. Unfixable findings count as one warning per image.
- **Enforce, don't just report.** A report-only scanner ran for weeks with critical findings nobody read.
- When choosing a fixed dependency version, respect your registry's minimum release-age rule.

If you run your own fork image:

- Derive the version from the nearest upstream release tag; fail the build when the release branch name names neither that version nor its major.minor. A sync that moves the base cuts a new release branch.
- Settle scope before the first build; gate the combined head once; confirm the merged tree equals the gated tree; cancel builds for superseded heads. The pin must be the release branch head.
- Merge fork `main` into the release branch *before* building, so the tracking PR needs no second build. If `main` moved after the build anyway, open the tracking PR from a side branch (release head plus a merge of `main`, same tree) instead of moving the release branch.
- Publish exactly the tested image — no rebuild between test and publish.
- Never rebase or force-push release branches; merge release → `main` with a merge commit.
- Run the release workflow's own jobs locally, read from the workflow file, before pushing to a release branch. Every gate needs a negative control: prove it fails on a known-bad head. A local gate that fed its script over `ssh … bash -s` had stdin swallowed by a child process and reported PASS for months.

## 8. Disk and scratch hygiene

- **Classify before deleting.** A directory named `cache` can hold model weights, unprocessed voice clips, skill state or the only copy of mail. Delete package-manager caches by name; leave the rest until each child is classified.
- **Never `rm -rf` a git worktree** or a directory inside one; it deletes tracked files. Use `git worktree remove` on a clean tree (the branch survives). If the worktree was registered from inside the container, run git there, as the runtime user.
- **Leased scratch:** temporary snapshots, rehearsal copies and scratch trees get an owner, a purpose and an end; close them in the same task. Give the sweep a byte budget per scratch root.
- **Images:** keep live + N-1 (and the same for any versioned UI source volume). A stopped leftover container blocks `docker rmi`. Container JSON logs and host cron logs have no cap by default; add rotation.
- **Agent scans need streaming reads and memory caps.** A search that read every file whole hit a multi-GB database and got OOM-killed. Teach the agent (skill text) to stream and skip databases; cap per-command memory where possible.
- Keep browsers out of the gateway's cgroup; size `pids`, `nofile` and `shm` for what remains.

## 9. Alerts

- Route ops and supply-chain alerts to a **channel the agent cannot reach or suppress** (separate bot, separate chat, or email). A compromised agent must not be able to mute its own alarm.
- **Circuit breakers on background loops:** page after N consecutive failures. A publish loop once died silently for hours.
- **Test the alert path end to end.** An alert failed with "chat not found" for days.
- **A lost page is not green.** If sending the alert fails, the job keeps its failing exit code, and an otherwise clean run exits non-zero too.
- **Ignores expire.** An ignore without an expiry is a permanent blind spot.

## 10. Failure-state design

For every self-managing component (browser slots, background loops, sync jobs):

- Split failures into **auto-recover** (infrastructure-class: a lost supervisor, a restart, a hang — recover after a short grace window) and **needs-human** (auth, policy, conflicting edits).
- **Page anything stuck longer than ~30 minutes**, whatever the class.
- **Persist failure history** outside the container. Logs die with a recreate; the next investigation needs the timestamps.
- Error text is agent UX: a 403 labelled "permission-blocked" made an agent retry for hours. Say what to do next and when to stop.

Cron and loop rules (scheduling, toolsets, approvals) are in [runtime-automation-governance](../skills/runtime-automation-governance/SKILL.md).

## 11. Learning loop

Close every maintenance window, upgrade or incident with the same four steps:

1. **Encode fixes first** as scripts, sweep rows, tests or config guards. A "remember to…" sentence is the last resort.
2. **Update the canonical doc**, one home per fact. Do not write live state into prose: pins, digests, job ids or "until <date>" go stale in a day; point at the file or command that proves them.
3. **Write a dated, immutable retrospective** — input, not canon — and fold its durable items into their homes in the same change.
4. **Sweep for stale docs** that contradict what you just learned.

For the weekly version of this loop over real sessions, see [Weekly Learning Extraction](weekly-learning-extraction.en.md). If a coding agent operates the deployment for you, its rules are in the [coding-agent operator guide](coding-agent-operator.en.md).
