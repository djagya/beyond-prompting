# Reference Setup: Bringing Up a Self-Hosted Hermes

A concrete bring-up path for one person's Hermes Agent on a home server or small VPS, using a digest-pinned Docker image. It is the setup behind this collection, with the private parts removed. It is written for an operator who has not done this before and for the coding agent helping them.

What follows is what that deployment runs and enforces in its scripts. It runs a fork build of Hermes; where a behaviour is specific to that build, the text says "on the fork build used here". On stock upstream, check each section once against the [official docs](https://hermes-agent.nousresearch.com/docs/) for your version. This guide assumes you have read the [hardening guide](hermes-hardening.md) or will read it next.

## 1. What you are building

```text
phone / laptop --(private network, e.g. a tailnet)--> host
host:
  private ingress (e.g. Tailscale Serve, HTTPS + identity) --> 127.0.0.1:<port>
  SSH: private network only
  ops repo (git): compose.yaml, scripts/, hermes/identity/ --apply--> data dir
  docker: hermes container (pinned image, s6) = gateway + cron for every profile
          bind mount: ./data/hermes (gitignored) --> $HERMES_HOME
  optional sidecars (loopback only): web UI (chat proxied through the gateway),
          log viewer, isolated browser containers
  host cron: identity publish (runtime -> git), encrypted backup --> off-site
          repository (keys host-only)
```

One container, one data directory, one gateway: all mutable state lives in the mounted directory, and two gateways must never share it. On current builds that one gateway serves every profile (multiplexed, §8). Chat is the main interface; nothing listens on a public port. Git holds the definition; the data directory holds what the agent changes at runtime.

**Source (git) install instead of Docker.** `hermes setup`, then `hermes gateway install` registers a systemd user service (launchd on macOS), and state lives in `~/.hermes`. The uid remap, capability and cgroup rows below do not apply; a dedicated unprivileged OS user, a stop timeout long enough to drain, and the exposure, secrets and backup rules still do. Source installs upgrade with `hermes update`; image installs refuse it and upgrade by moving the pin.

## 2. Prerequisites

- [ ] A Linux host that stays on. 4+ GB RAM for chat-only use; plan 16+ GB if the agent will drive browsers.
- [ ] Docker Engine with the compose plugin, installed from Docker's own packages.
- [ ] A private network for admin access, such as Tailscale, WireGuard, or a VPN you already run.
- [ ] A model provider account. Cap its spending on the provider's side.
- [ ] A chat platform bot (Telegram, Discord, Slack…) and **your own** user ID, which goes on its allowlist.
- [ ] A private git remote for the ops repo, and a dedicated deploy key for the host (a read-write one only for the job that publishes the agent's edits).
- [ ] Off-site storage for encrypted backups, plus a password manager for the backup passphrase.
- [ ] Host basics: automatic security updates, SSH key-only login, firewall default-deny inbound.

## 3. Repository layout

Keep a **private ops repo** that describes the box:

```text
ops-repo/
├── compose.yaml            # from templates/compose.example.yaml
├── .env.example            # variable names only; the real .env stays on the host
├── scripts/                # deploy, apply/publish identity, backup, health sweep
├── hermes/identity/        # git-tracked identity: SOUL.md, ARCHITECTURE.md,
│                           #   config.yaml, skills/, hooks/, plugins/,
│                           #   scripts/ (cron adapters), services/ (launchers),
│                           #   cron/jobs.json (seed only)
├── hermes/release.yaml     # operator-only release manifest (tag, digest)
├── supply-chain/           # watch policy and one SBOM per pinned image
├── docs/                   # why each decision was made; maintenance checklist
├── .scratch/               # gitignored: one-off helpers, worktrees, logs
└── data/                   # gitignored: data/hermes is the live $HERMES_HOME
```

Rules that prevent most confusion:

- **Your laptop checkout is a dev clone, not the runtime.** An empty `docker ps` on the laptop says nothing about the box. "Deploy" means running the deploy script **on the host** over the private SSH path.
- **A laptop `data/` is stale.** Never read it as live state and never deploy from it.
- **Deploy through a script**, never `docker compose up` / `restart` of the gateway by hand. The script applies identity, pulls git, recreates the container if needed, re-links supervised services, checks the policy, and probes the result. It also refuses to deploy a commit whose CI is red or unfinished (skip-CI commits from the host's own publish job excepted).

## 4. Compose essentials

Start from [`templates/compose.example.yaml`](../templates/compose.example.yaml). Every non-obvious line in it has a one-line reason. The ones that matter most:

| Setting | Why |
| --- | --- |
| `image: <registry>/hermes-agent:<tag>@sha256:<digest>` | A digest is a review checkpoint. Without one, `docker compose pull` can silently move you onto a new release. Move the pin in a reviewed commit together with its SBOM. |
| `user: "0:0"`, no `entrypoint` override, `HERMES_UID/GID` = host owner of the data dir | The image's init runs as root to remap the `hermes` user and fix ownership, then drops privileges. Recent images default to uid 10000; matching the host uid keeps agent and host-script (backup, git) files under one owner. |
| No `no-new-privileges`; `cap_drop: ALL` + seven re-adds | `no-new-privileges` breaks the setuid remap. Dropping every capability and re-adding the seven the remap and service stop need is the safer trade. If the container stops booting after an image bump, suspect this block first. |
| `command: ["gateway", "run"]` | Runs the supervised gateway. Because of it, a one-off `docker compose run hermes` needs the explicit binary (`/opt/hermes/.venv/bin/hermes …`). |
| `working_dir` | Relative paths and project-context discovery resolve here. If it is a vault or repo with its own agent rules, shield it with a non-empty `.hermes.md` ([identity guide §5](identity-memory-context.en.md#5-project-context-precedence-and-the-hijack-shield)). |
| `HERMES_WRITE_SAFE_ROOT` | The file-write tools are confined to `$HERMES_HOME` by default. List every root the agent may write (workspace, `/tmp`). Set it in compose: the image's own ENV beats `$HERMES_HOME/.env`. |
| `PATH` | Image binaries first, then an overlay `bin` dir under the data home for tools the image lacks, then system paths, matching the image's login-shell profile. An overlay copy of a system tool still wins; detect shadows with a check rather than reordering. |
| Ports `127.0.0.1:…` only | Docker-published ports bypass ufw (see §5). |
| `shm_size`, `ulimits.nofile`, `deploy…pids`, memory + `memswap_limit` | Browsers and MCP servers exhaust the defaults. A pids cap stops a fork storm without starving normal work. A running container keeps the limits it was created with until the next recreate. |
| `S6_*_GRACETIME` and `stop_grace_period` | The gateways run as dynamic s6 services, and s6-overlay SIGKILLs leftovers 3 s after SIGTERM by default. 150 s each covers drain plus slack; the grace period (360 s here) must exceed both. A SIGKILL mid-write is how the SQLite session store gets corrupted. |
| Seccomp + AppArmor for the sandbox | With `cap_drop: ALL`, Bubblewrap needs a seccomp profile that adds only the namespace syscalls; on Ubuntu 24.04 also `apparmor:unconfined` plus the host's unprivileged-userns sysctl. Never `seccomp=unconfined` or `privileged`. |
| `healthcheck` | Observability only: Docker never restarts an unhealthy container. Give it a long `start_period` (30 min here) so first-boot migrations stay `starting`. |
| No volume on `/opt/hermes` | The image owns its code. Durable fixes ship as a new image digest, not as files copied into a running container. |
| One gateway per data directory | A second container from the same image (e.g. a dashboard sidecar) starts a second gateway on the same bot token; dropped messages then look like "voice is broken". |
| Web UI sidecar without `depends_on` | `depends_on: hermes` made every `compose up webui` recreate the gateway as a side effect. The UI proxies chat through the gateway and just errors until it answers. |
| Docker-socket tools | A `:ro` socket mount protects nothing: the API behind it is read-write, i.e. host root. Actions off, auth, loopback, or a read-only socket proxy. |

Run browsers in separate containers, not in the gateway's cgroup, on a network the browser containers share only with their controller. A leaked tab should not be able to kill the gateway, and a renderer breakout should have no route to the gateway API.

## 5. Network exposure

1. **Bind every published port to `127.0.0.1`.** Docker inserts its NAT rules before ufw sees the packet, so `ufw deny` does not protect a port published on `0.0.0.0`.
2. **Expose admin UIs through authenticated private ingress.** Tailscale Serve is one example: HTTPS, reachable only from your private network, with identity attached. Add the app's own password as a second layer.
3. **SSH only over the private network**, keys only, no root login. sshd is first-match-wins: a cloud-init drop-in with `PasswordAuthentication yes` beats a later file, so name yours `00-…`. A socket-activated sshd keeps its old config until `ssh.service` restarts.
4. **The API server** stays off unless a client needs it. A web UI sidecar does: then it listens on `0.0.0.0` inside the container (so the compose network and the published port reach it), requires a key, and the host publishes it on loopback only. Residual risk: any container on that compose network holding the key can drive the agent.
5. Verify from **outside**: run a port scan of the host's public and LAN addresses from another machine. A bind address in compose is not evidence ([hardening §10](hermes-hardening.md#10-secure-gateway-access-and-exposed-services)).

## 6. Secrets layout

| Secret | Where it lives | Never |
| --- | --- | --- |
| Provider keys, bot tokens | `$HERMES_HOME/.env` on the host, mode 600 | in git, chat, or `config.yaml` |
| Secrets a subprocess or skill needs | ops-repo `.env` on the host → compose `environment:` passthrough | `hermes config set my.custom_key <secret>`: only recognised keys are routed to `.env`; a custom key lands **plaintext** in `config.yaml`, and the identity publish then mirrors that file into git |
| Webhook secrets in config | `${ENV}` interpolation in the config leaf | a literal value |
| Backup repository password and keys | a host-only file, mode 600, **not mounted into any container** | readable by the agent: an agent that can read the keys can also prune your backups |

Notes:

- **Stripping env vars is not a boundary.** The agent's shells run as the same OS user that can read `.env`. Treat provider-side scoping (read-only, per-resource tokens, spending caps) as the real limit, and test any claim that "the agent can't reach X".
- **If you use a secret manager, budget its read rate.** Every pull reads each mapped secret, and every home pulls on its own: the default home, each named profile, each CLI process (including ones the agent starts from its terminal). Once the budget is spent, every read fails and a boot comes up with no messaging tokens while health stays green. The design that holds: a long cache TTL (6 h here, in every home); keep the last good values on a throttled re-pull and back off, never empty the scope; one account-wide backoff marker at the first rate-limit response; child shells read the gateway's cache only; the upgrade refuses while the budget is spent; the health sweep reports the remaining budget. A rotated secret then needs the cache file removed before the restart.
- Run a secret scanner such as gitleaks on **every** push, including automated commits that skip CI (scan them on the host before they push).
- Never paste a secret into a chat with any agent. If one gets pasted, rotate it.

## 7. Bring-up, step by step

```bash
# On the host, inside the ops repo checkout
mkdir -p data/hermes && chmod 700 data/hermes
cp .env.example .env && chmod 600 .env           # fill in compose-level values
./scripts/apply-identity.sh                      # SOUL, ARCHITECTURE, config, skills… BEFORE first start
docker compose run --rm hermes \
  /opt/hermes/.venv/bin/hermes setup             # wizard: provider, keys, chat platform
./scripts/deploy.sh                              # first start and every later one
./scripts/hermes-cli.sh config get approvals.cron_mode
```

- Apply the identity first so the image's seeded defaults don't win.
- The wizard is needed only while `$HERMES_HOME/.env` is missing; run it while no gateway is running. It needs the explicit binary because the service command is `gateway run`.
- The service starts as root, so a plain `docker exec hermes …` runs as **root** and leaves root-owned files in the data dir that break host jobs (publish, backup). Use a small wrapper (`hermes-cli.sh` above) that runs `docker exec -u hermes <container> /opt/hermes/.venv/bin/hermes "$@"`.

## 8. Initial config baseline

Apply the approval baseline from [hardening §8](hermes-hardening.md#8-configure-approvals-as-guardrails-not-theatre), then the **install-policy trio** and the leaves this deployment pins next to it:

```bash
# hermes = your CLI wrapper (runs as the runtime user)
hermes config set skills.write_approval true     # skill edits stage for your review
hermes config set memory.write_approval false    # memory writes apply directly
hermes config set approvals.cron_mode deny       # cron never self-approves dangerous shell
hermes config set browser.auto_local_for_private_urls false
hermes config set security.allow_private_urls false
hermes config set cron.catch_up_missed false     # a gateway that was down does not replay missed runs
```

The gateway reads `config.yaml` only at boot. After a change, restart the gateway service in place (`docker exec <container> s6-svc -r /run/service/gateway-default`). Do not recreate the container for it: a recreate empties `/run/service` and needs the service re-link.

Why each one:

- **`memory.write_approval: false`**: `true` stages every write under `pending/` for an operator. A cron job has no operator, so its memory writes never complete. To keep a particular job from writing memory, leave the `memory` toolset off **that job**.
- **`skills.write_approval: true`**: skills are procedures that run later with authority, so they get the slower, reviewed path.
- **`approvals.cron_mode: deny`**: a dangerous command in an unattended job is blocked and reported, not auto-approved. A different switch from the staging queue.
- **`browser.auto_local_for_private_urls: false`**: with `true` (the image seed's default), a private URL is *routed* to a local browser instead of rejected, and `security.allow_private_urls` does not cover that path.

**Named profiles** (`hermes profile create <name>`) are sparse: a missing leaf fills from **upstream defaults, not from your default profile**. Upstream defaults `cron.catch_up_missed` and `gateway.auto_multiplex_migration` to true and the seed sets the browser fallback to true. Pin every safety leaf in every profile (a "seed shield"), insert them with a script that stamps the live files rather than hand edits, and assert all of them on each deploy and upgrade:

```bash
for p in default work; do
  for k in skills.write_approval memory.write_approval approvals.cron_mode \
           browser.auto_local_for_private_urls cron.catch_up_missed \
           gateway.auto_multiplex_migration; do
    printf '%s %s = ' "$p" "$k"; hermes -p "$p" config get "$k"
  done
done
```

**One gateway serves every profile.** Current builds retired `gateway.multiplex_profiles: false`: the gateway rewrites it to `true` at boot, the per-profile gateway slots stay down, and pinning `false` in git only makes the mirrored config disagree. What changes: each profile's secrets resolve strictly in its own scope, with no fallback to the process environment; one cron scheduler runs every profile's jobs; and a crash, restart or cgroup limit on the default gateway takes every profile's cron down together. A profile that must run its own gateway sets `gateway.standalone: true` in its own config.

The policy is **asserted, not locked**: the agent's uid can write `config.yaml`, and the publish job mirrors it into git, so a self-edit can flip a leaf. Make the deploy script read the effective values back after every start and fail on a mismatch. List-typed keys: stock `hermes config set` stored a JSON list as a YAML string, and a deny list read as a string matched every command (deny-all). Use `hermes config edit` or a YAML list for list keys, and read them back.

On the fork build used here, the image bakes a managed config seed for the trio. It fills only leaves the user config omits: `config set` wins, `config unset` lets the seed show through. Upstream documents its managed scope as a lock; check which your build has, and keep the deploy assertion either way.

## 9. Identity in git

Write `SOUL.md` and `ARCHITECTURE.md` from [`templates/SOUL.template.md`](../templates/SOUL.template.md) and [`templates/ARCHITECTURE.template.md`](../templates/ARCHITECTURE.template.md). Keep them in `hermes/identity/` and apply them additively to the data directory. `SOUL.md` loads from `$HERMES_HOME` on every build; the `ARCHITECTURE.md` slot is a feature of the fork build used here, so verify your version loads it. Slot order, size caps, two-way sync with a self-editing agent and the project-context hijack: [Identity, Memory and Context](identity-memory-context.en.md). Cron jobs and memory are runtime state, so they do **not** deploy through git.

## 10. Backups

1. Run the backup from **host cron**, not Hermes cron, so it still runs while Hermes is down.
2. Use an encrypted, deduplicating tool such as restic. Keep its keys host-only (§6). Let the nightly job print `forget --prune --dry-run` only; a real prune waits for an operator. Deny prune commands to the agent (`approvals.deny` such as `*restic*forget*`). Set the bucket lifecycle to keep only the latest object version.
3. **Never copy a live SQLite file directly, and never open the live WAL with the host's `sqlite3`** (a host SQLite inside the WAL-reset bug window can corrupt it; fixed in 3.51.3+, backports 3.50.7 / 3.44.6). Copy the database with the image's own SQLite in a one-shot helper container from the same digest: `--network none`, read-only, `--cap-drop ALL`, and an explicit `--entrypoint` (the image's default entrypoint is the supervisor, which would start a second gateway). Stage the copy outside the data bind mount, run `PRAGMA quick_check` on it, and only then promote it as the good copy. A failed check still uploads the rest of the tree but never adds a new "good database" tag.
4. Exclude what is redownloadable or rebuildable (package caches, logs, snapshots, scratch, worktrees, installed dependencies); keep what holds history or secrets. Mark disposable cache dirs with a `CACHEDIR.TAG` and back up with `--exclude-caches`; an excluded directory named `cache` can still hold the only copy of something, so exclusion is not a licence to delete. Keep test fixtures and experimental databases **out of** the data directory entirely. Loop-mounted volumes (such as persistent browser profiles) need to be listed as their own backup roots.
5. Before each upgrade, take a full consistent snapshot as its own step ([Operations §4](operations.en.md#4-upgrade-runbook-image-installs)).
6. **"Backup ran" is not "restorable".** Run a structural repository check weekly and restore into a scratch directory once a quarter. Day-to-day cadence is in [Operations](operations.en.md).

## 11. First-week acceptance checklist

Probe behaviour, not status. A green `/health` has coexisted with a dead MCP server, a config file that failed to parse and fell back to defaults, a missing bot token and an exhausted provider balance.

- [ ] **Authorized chat**: you message the bot and get a sensible reply.
- [ ] **Unauthorized chat**: a second account messages the bot and gets nothing or a pairing refusal, and the attempt appears in the logs.
- [ ] **Exposure**: an external port scan shows nothing new, and admin UIs answer only over the private network.
- [ ] **Cron canary**: one harmless job (e.g. "reply with the date") fires on schedule, delivers to the right chat, and shows the expected toolset. The scheduler adds every globally enabled MCP server to a job unless the job carries the literal `no_mcp` sentinel; check the effective tool list, not the stored one.
- [ ] **Policy**: the loop in §8 prints the expected values for every profile.
- [ ] **Config load**: this boot's log shows no "failed to process config.yaml, falling back" warning.
- [ ] **MCP**: `hermes mcp list` / `hermes mcp test <name>` succeeds for each enabled server, run through the wrapper.
- [ ] **Secrets**: `git log -p` and the image contain no secret, and `.env` files are mode 600.
- [ ] **Clean stop**: `docker compose stop hermes` finishes within the grace period, with no SIGKILL in the logs.
- [ ] **Backup restore**: the first snapshot restores to scratch and its database passes `quick_check`.
- [ ] **Alert path**: one deliberate failure reaches you end to end. An alert channel that has never fired is unproven.

Record results in the ops repo. The broader acceptance list is [hardening §16](hermes-hardening.md#16-acceptance-tests).

## 12. Failure → symptom → fix

| Failure | Symptom | Fix |
| --- | --- | --- |
| Port published on `0.0.0.0` | UI reachable from the LAN or internet despite ufw | Bind `127.0.0.1`, use private ingress |
| Second gateway on the same token | Polling "Conflict" errors, dropped audio or messages | One gateway per data dir; remove the sidecar |
| `no-new-privileges` or non-root `user:` | Container fails at init, ownership errors | Start as root, rely on the image's drop |
| `docker exec` as root | Root-owned files in the data dir; host publish or backup fails | `chown` back to the runtime uid; use the wrapper |
| `config.yaml` repaired while running | Agent still silent or still on fallback values | Restart the gateway service in place; don't recreate |
| SIGKILL on stop | DB "malformed" errors, long full-text index rebuild on next boot | Longer grace; stop, copy, repair the **copy** |
| Process cap hit | "can't start new thread" | Recreate the container through the deploy script (restarting the service does not free leftover processes); move browsers out |

## 13. Handing a setup to someone else

To set this up for a family member or friend:

**Give them:** the ops-repo *structure*, the compose example, scripts, the generic templates, this guide, and the [coding-agent operator guide](coding-agent-operator.en.md) for the agent that will maintain it.

**They must own:**

- their own host, private network, provider account and spending cap;
- their own bot and allowlist, plus every secret, created fresh by them and never sent through your chat;
- their own `SOUL.md`, written about *their* assistant, not a copy of yours;
- their own backup repository and passphrase;
- the decisions: what the agent may do unattended and what it must ask about.

**Never copy across:** your `memories/`, sessions or `state.db`, `.env`, auth or OAuth token files, cron jobs that mention your accounts, or skills that encode your private workflows. Copy generic skills only after reading them. Their agent starts empty and learns *them*.

Operating it day to day (updates, health checks, cron discipline, incidents) is covered in [Operations](operations.en.md).
