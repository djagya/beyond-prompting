# Running a Long-Lived Hermes: Operations Field Guide

**Operational practice from one always-on Docker deployment, not an official Hermes guarantee.** Items marked *confirm on your version* are not in the current Hermes documentation.

You already have Hermes running in Docker (see [setup reference](setup-reference.en.md)). This guide covers keeping it healthy for months: what to check, what the alarming symptoms mean, how to upgrade and roll back, and how to keep state, backups and disk under control. Security controls (exposure, secrets, approvals, tool surface) live in [Hardening Hermes Agent](hermes-hardening.md); this guide links there instead of repeating them.

Placeholders: `<container>` is the Hermes container name, `<profile>` a profile (`default` for the main one), `<data-dir>` the host directory mounted as `$HERMES_HOME`, `<image>@sha256:<digest>` the pinned image.

## 1. Health is not the same as working

A green container and `/health` prove that a process answers HTTP, not that the agent can think, reach its tools or talk on its channels. Each failure below happened with health green.

| Silent-green failure | Why it stays green | Probe |
| --- | --- | --- |
| A new image moved or dropped a binary that an MCP server's `command:` names | The server fails to start and is parked; the gateway runs without it | For each enabled stdio server, resolve `command:` with the gateway's own PATH (`docker exec -u hermes <container> sh -c 'command -v <cmd>'`; a login shell's PATH can differ), then `hermes mcp test <name>` |
| `config.yaml` failed to parse at boot | The gateway falls back to defaults and keeps running | Read this boot's log for config load errors (`hermes logs errors --since 1h`). Keep one deliberate non-default value as a canary and confirm the gateway behaves accordingly after each boot |
| A secret manager read budget was spent at boot | Secrets resolve to empty; the messaging token is missing, the platform never connects | Grep this boot's log for secret-resolution failures; send a real message and watch a turn land. Track the remaining budget in your sweep |
| Provider credits or auth expired | Every turn errors; nothing crashes | `hermes logs errors --since 1h` and grep for `401`, `quota`, `billing`, `insufficient`; run one synthetic turn |
| The gateway's supervised slot is down while the container is Up | Docker sees PID 1 (the supervisor) alive | `docker exec <container> /command/s6-svstat /run/service/gateway-<profile>` and `curl -fsS http://127.0.0.1:<api-port>/health` (API server must be enabled) |
| Two gateways poll one bot token | Both processes are healthy; the platform splits updates between them | Count gateway processes (`ps -eo pid,args` in the container) and list every container that mounts `<data-dir>` (`docker inspect` → `.Mounts`). Platform "conflict" errors and dropped messages are the symptom |

Rule: **one gateway per data directory.** A sidecar built from the same image can start a second gateway from the image's service bundle.

## 2. Check cadence

Write the checks as **one sweep script**, not snippets pasted from a doc. Each check prints one row, `PASS|WARN|FAIL <check>: <detail>`; the script exits non-zero only on FAIL. An *expected* failure (a known-broken optional integration, a credential awaiting rotation) is allowlisted and prints WARN with exit 0 — habitual red trains people to ignore exit codes.

```bash
#!/usr/bin/env bash
# sweep.sh — skeleton; add one function per row
fails=0
row() { printf '%s %s: %s\n' "$1" "$2" "$3"; [ "$1" = FAIL ] && fails=$((fails+1)); }
if docker exec <container> /command/s6-svstat /run/service/gateway-default | grep -q '^up'
then row PASS gateway/slot up; else row FAIL gateway/slot down; fi
# disk, backup age, memory caps, MCP commands, policy keys, ... one row each
exit $(( fails > 0 ))
```

| Cadence | Checks |
| --- | --- |
| **Daily** (2 min, ideally automated) | Containers Up and not restart-looping (`RunningFor` not resetting); gateway slot up; recent errors in `hermes logs errors`; provider auth/quota errors; messaging platform connected; background loops (sync, backup, publish) ran and logged no FATAL; disk below ~80%; supply-chain job not red |
| **Weekly** (10 min) | `hermes cron list` — paused or erroring jobs and stale last errors (autonomous behaviour stopping is the quietest drift); skills list loads without duplicates; canonical source vs runtime drift; root-owned files in `<data-dir>`; reclaimable images; alert-ignore expiries |
| **Monthly** (20 min) | Full sweep: memory files vs their char limits; `SOUL.md` size vs its prompt cap; approval and cron policy keys read back from the live config (see [hardening](hermes-hardening.md)); every MCP command resolves; ports still bound to loopback; backup freshness and last verified canary; cgroup PIDs/memory headroom; OS and Docker updates pending |
| **Quarterly** | Restore drill into an isolated target (§6); review approval allowlists and ignore lists |

Run the sweep with all rows. A `--quick` mode that skips rows is a different check; do not record its exit 0 as the monthly sweep.

## 3. Red flags → first response

| Symptom | What it means | Do | Don't |
| --- | --- | --- | --- |
| `can't start new thread`, or the gateway died near the PID cap | The cgroup PID limit is full of leftovers; restarting the service does not free them | Recreate the container through your deploy script; then find the leak (usually a browser or a runaway tool child) | Restart the s6 service in place |
| Gateway failing database writes (`database disk image is malformed`, `file is not a database`, `disk I/O error`) | Live state store damage in progress | Stop the container, copy the database files, repair the copy ([state-store skill](../skills/live-state-store-maintenance/SKILL.md)) | Bounce the gateway; one bounce during a write storm overwrote the database header |
| Container `Exited` after a Docker or containerd restart | The new daemon did not re-arm the restart policy while the old shutdown was still running | Run your deploy script; check every container | Assume `restart: unless-stopped` covers it |
| Agent silent, `/health` green | Provider auth/credits, missing messaging token, or two gateways | Work the §1 table top to bottom | Recreate the container first; you lose the boot log |
| Memory file near its char limit | Hermes truncates over-cap memory silently | Ask the agent to run its memory hygiene and report what moved where ([memory hygiene](../skills/memory-skill-boundary-hygiene/SKILL.md), [identity guide](identity-memory-context.en.md)) | Edit memory behind the agent's back, or raise the limit as the fix |
| Disk filling | Images, snapshots, scratch, logs, or the session store | Classify before deleting (§8) | `rm -rf` anything named `cache` or any worktree |
| Container restart-looping | Ownership/entrypoint-user problem, or a boot check tripping on a file in the data dir | `docker logs --tail 200 <container>`; fix what the boot step names | Strip security options until it boots |
| Background job "succeeds", nothing changes | Stalled behind a dirty tree, a lock, or a refused conflict | Read its log for `refusing`/`conflict`; resolve by hand | Force one side by default |
| Upgrade postcheck fails on an expired external token after a healthy cutover | A dead credential, not a bad image | Rotate the credential; finish the acceptance checks by hand | Roll back |

## 4. Upgrade runbook (image installs)

`hermes update` refuses on image-managed installs (documented); you upgrade by replacing the image. Batch changes so one window carries one recreate.

1. **Pick the target.** A specific release tag, pinned by digest (`<image>@sha256:<digest>`), never `latest`.
2. **Read the release notes** and diff the shipped default config. Look for **renamed or retired keys**: a renamed key is silently ignored, and an image can rewrite a topology setting to its new default. Decide each retirement deliberately; then confirm which key the running image actually reads (`hermes config get <key>` after boot).
3. **Pin and record evidence.** Commit the new digest together with its SBOM (§7). Write down the digest you are replacing — that is your N-1.
4. **Wait for idle, then freeze.** A live session can run for hours; restarting under it loses the turn. Poll detached for "no agent, tool or cron activity for N minutes" (for example `hermes logs --since 5m`). Then pause host-side loops (sync, backup timers) and chat ingress.
5. **Snapshot as its own step**, after idle so it is fresh. Copy every SQLite file consistently plus the data tree, verify the copies (`quick_check` with the image's SQLite) and read the result. Do **not** chain `snapshot && upgrade`: a chained refusal hides in a long log.
6. **Save the old container's logs** before recreating it: `docker logs <container> > <log-dir>/<container>-$(date -u +%Y%m%dT%H%MZ).log 2>&1`. They are the only record of pre-upgrade crashes and OOMs.
7. **Upgrade** through your deploy script (pull the pinned digest, recreate). If you stopped the gateway with `hermes gateway stop`, it stays stopped across the recreate (documented); start it explicitly.
8. **Re-register externally supervised services.** `/run/service` is runtime state that does not survive a recreate (tmpfs in our deployment; check yours): the boot reconciler rebuilds per-profile gateway slots (documented), but anything you linked there yourself is gone. Have the deploy script re-link and verify it.
9. **Probe** (§1 table, then):

   ```bash
   docker inspect -f '{{.Image}}' <container>          # running image id
   docker image inspect -f '{{.Id}}' <image>@sha256:<digest>   # must match
   hermes --version
   hermes config check
   hermes doctor
   hermes mcp list && hermes mcp test <each-server>
   ```

   Then one real chat turn, one scheduled-job canary, and one MCP read. Record the config schema version the image migrated to (observed as `_config_version` in `config.yaml` on recent builds; confirm on yours) — it decides how rollback works.
10. **Accept** in two stages: a short validation while ingress and background loops are still paused, then an explicit go, then unfreeze.

### Rollback

Re-pinning the old digest is **not** a rollback once the new image has migrated `config.yaml` or the state database: the old image would open new indexes and triggers.

1. Stop the container.
2. Restore the pre-upgrade snapshot: database copies first, **deleting the live `-wal` and `-shm` files** before placing them (a restored database next to a leftover WAL is a torn open), then config, `.env`, skills and memory from the same snapshot.
3. Re-pin the N-1 digest and redeploy. Re-register external services. Probe as above.

Everything after the snapshot is lost. Keep the N-1 image until the new one has survived a day. `docker image prune` (dangling only) keeps a digest-pinned image; `docker image prune -a` removes every image no container uses, including N-1.

### Host OS maintenance window

Anything that restarts Docker (host package upgrades touching `docker`/`containerd`, a reboot) belongs in the same kind of window:

- Run package upgrades **detached as a root systemd unit with a log**, because a VPN or SSH package restart drops your session mid-run:

  ```bash
  sudo systemd-run --unit=host-upgrade -p StandardOutput=append:/var/log/host-upgrade.log \
    -p StandardError=append:/var/log/host-upgrade.log \
    /usr/bin/env DEBIAN_FRONTEND=noninteractive apt-get -y upgrade
  sudo tail -f /var/log/host-upgrade.log
  ```

- **Always run your deploy script afterwards**, then `docker ps -a` for anything `Exited`.
- Host and container clocks or time zones can differ; key wait loops and log searches on UTC.

## 5. State store care

The session store (SQLite with WAL and full-text indexes) is the most fragile state you own. The procedure lives in [live-state-store-maintenance](../skills/live-state-store-maintenance/SKILL.md); the rules:

- **Clean shutdown is a precondition.** The stop grace (compose `stop_grace_period`, s6-overlay `S6_SERVICES_GRACETIME`/`S6_KILL_GRACETIME`) must exceed the gateway's drain time. An unclean exit can mark the search index stale, and the next boot rebuilds it over live writes.
- **No live index rebuild under writers.** A full-text rebuild racing active sessions was the recurring corruption trigger.
- **Never open the live WAL with host `sqlite3`.** Use the image's own SQLite (its Python) in a throwaway container, or work on a copy.
- **Stop → copy → repair.** When the canonical tables still read, salvaging the live file usually keeps more history than restoring the last snapshot.
- **Growth comes from compaction duplicates, not age.** Context compaction re-stores tool output; age-based pruning frees little. Archive first, verify every archived message id resolves, then prune. Built-in auto-prune (`sessions.auto_prune`) is on by default in current docs and has no archive step; turn it off if you need the history.
- **Keep fixtures and experiments out of the data home.** Deliberately corrupt test databases broke a snapshot and crash-looped a new image whose boot check opens every SQLite file there; experimental databases inflated each snapshot by tens of GB.
- **Recurring corruption with clean shutdowns and no live rebuild:** run a memory test overnight before blaming software.
- **Watchdogs:** a restarter that SIGKILLs the gateway or revives a deliberately stopped container is a corruption source. It must honour a deliberate stop and alert, not heal silently.

## 6. Backups that restore

"The backup ran" is not "the backup restores".

- **Stage a verified copy.** Copy each database with SQLite's backup API inside the image, run `PRAGMA quick_check` on the staged copy, and only then mark it good. Never tag an unverified copy as the good one; a tagged copy once turned out corrupt.
- **Canary row in the sweep:** last backup age, last verified database copy, and no FATAL in the backup log.
- **Exclude lists need a test.** Logs, package caches, snapshots, scratch, worktrees and installed dependencies are excluded; credentials, memory, sessions, tokens and the verified database copy are included. A test asserts both lists so a refactor cannot silently drop a path.
- **Keep the backup repository's password and keys on the host**, not mounted into the agent container, so the agent cannot prune its own backups (controls: [hardening](hermes-hardening.md)).
- **Quarterly drill:** restore a known file and the database into an isolated target (never the live home; `hermes import` overwrites its target), open it, and run the acceptance checks. If you cannot, the backup is theatre.

## 7. Supply chain and fork release discipline

Policy and controls are in [hardening](hermes-hardening.md); the operating loop:

- A **digest pin is a review checkpoint, not a vulnerability feed.** Commit an SBOM (for example Syft CycloneDX) per pin and rescan the committed SBOMs daily against the current advisory database (for example Grype or Trivy). Advisories for a fresh image often land hours after publish.
- **Admission:** new images and CI actions must be on an allowlist. Every ignore entry has a reason and an expiry.
- **Enforce, don't just report.** A report-only scanner ran for weeks with critical findings nobody read.
- When choosing a fixed dependency version, respect your registry's minimum release-age rule.

If you run your own fork image:

- Derive the version from the upstream tag; fail the build when the release branch name and version disagree.
- Settle scope before the first build; gate the combined head once; confirm the merged tree equals the gated tree; cancel builds for superseded heads.
- Merge fork `main` into the release branch *before* building, so the tracking PR needs no second build.
- Publish exactly the tested image — no rebuild between test and publish.
- Never rebase or force-push release branches; merge release → `main` with a merge commit.
- Every gate needs a negative control: prove it fails on a known-bad head. A local gate that fed its script over `ssh … bash -s` had stdin swallowed by a child process and reported PASS for months.

## 8. Disk and scratch hygiene

- **Classify before deleting.** A directory named `cache` can hold model weights, unprocessed voice clips, skill state or the only copy of mail. Delete package-manager caches by name; leave the rest until each child is classified.
- **Never `rm -rf` a git worktree** or a directory inside one; it deletes tracked files. Use `git worktree remove` on a clean tree (the branch survives). If the worktree was registered from inside the container, run git there, as the runtime user.
- **Leased scratch:** temporary snapshots, rehearsal copies and scratch trees get an owner, a purpose and an end; close them in the same task. Give the sweep a byte budget per scratch root.
- **Images:** keep live + N-1. Container JSON logs and host cron logs have no cap by default; add rotation.
- **Agent scans need streaming reads and memory caps.** A search that read every file whole hit a multi-GB database and got OOM-killed. Teach the agent (skill text) to stream and skip databases; cap per-command memory where possible.
- Keep browsers out of the gateway's cgroup; size `pids`, `nofile` and `shm` for what remains.

## 9. Alerts

- Route ops and supply-chain alerts to a **channel the agent cannot reach or suppress** (separate bot, separate chat, or email). A compromised agent must not be able to mute its own alarm.
- **Circuit breakers on background loops:** page after N consecutive failures. A publish loop once died silently for hours.
- **Test the alert path end to end.** An alert failed with "chat not found" for days.
- **A lost page is not green.** If sending the alert fails, the job exits non-zero.
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
