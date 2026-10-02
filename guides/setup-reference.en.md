# Reference Setup: Bringing Up a Self-Hosted Hermes

A concrete bring-up path for one person's Hermes Agent on a home server or small VPS, using the official Docker image. It is the setup behind this collection, with the private parts removed. It is written for an operator who has not done this before and for the coding agent helping them.

**Official** below means the current Hermes documentation says it; **practice** means a long-running deployment learned it, with no upstream guarantee. Commands and keys change between releases: check each against the [official docs](https://hermes-agent.nousresearch.com/docs/) for your version. This guide assumes you have read the [hardening guide](hermes-hardening.md) or will read it next.

## 1. What you are building

```text
phone / laptop --(private network, e.g. a tailnet)--> host
host:
  private ingress (e.g. Tailscale Serve, HTTPS + identity) --> 127.0.0.1:<port>
  SSH: private network only
  ops repo (git): compose.yaml, scripts/, hermes/identity/ --apply--> data dir
  docker: hermes container (official image, s6) = gateway + cron
          bind mount: ./data/hermes (gitignored) --> $HERMES_HOME
  optional sidecars (loopback only): web UI, log viewer, browser containers
  host cron: encrypted backup --> off-site repository (keys host-only)
```

One container, one data directory, one gateway (official: all mutable state lives in the mounted directory; two gateways must never share it). Chat is the main interface; nothing listens on a public port. Git holds the definition; the data directory holds what the agent changes at runtime.

**Source (git) install instead of Docker.** Official: `hermes setup`, then `hermes gateway install` registers a systemd user service (launchd on macOS), and state lives in `~/.hermes`. The uid remap, capability and cgroup rows below do not apply; a dedicated unprivileged OS user, a stop timeout long enough to drain, and the exposure, secrets and backup rules still do. Source installs upgrade with `hermes update`; image installs by moving the pin.

## 2. Prerequisites

- [ ] A Linux host that stays on. 4+ GB RAM for chat-only use; plan 16+ GB if the agent will drive browsers.
- [ ] Docker Engine with the compose plugin, installed from Docker's own packages.
- [ ] A private network for admin access, such as Tailscale, WireGuard, or a VPN you already run.
- [ ] A model provider account. Cap its spending on the provider's side.
- [ ] A chat platform bot (Telegram, Discord, Slack…) and **your own** user ID, which goes on its allowlist.
- [ ] A private git remote for the ops repo.
- [ ] Off-site storage for encrypted backups, plus a password manager for the backup passphrase.
- [ ] Host basics: automatic security updates, SSH key-only login, firewall default-deny inbound.

## 3. Repository layout

Keep a **private ops repo** that describes the box:

```text
ops-repo/
├── compose.yaml            # from templates/compose.example.yaml
├── .env.example            # variable names only; the real .env stays on the host
├── scripts/                # deploy, backup, health-check (one script per job)
├── hermes/identity/        # git-tracked identity: SOUL.md, ARCHITECTURE.md,
│                           #   config.yaml baseline, skills/, hooks/, plugins/
├── docs/                   # why each decision was made; maintenance checklist
└── data/                   # gitignored: data/hermes is the live $HERMES_HOME
```

Rules that prevent most confusion:

- **Your laptop checkout is a dev clone, not the runtime.** An empty `docker ps` on the laptop says nothing about the box. "Deploy" means running the deploy script **on the host** over the private SSH path.
- **A laptop `data/` is stale.** Never read it as live state and never deploy from it.
- **Deploy through a script**, not `docker compose up` by hand. The script pulls git, applies identity, recreates the container if needed, checks the policy, and probes the result.

## 4. Compose essentials

Start from [`templates/compose.example.yaml`](../templates/compose.example.yaml). Every non-obvious line in it has a one-line reason. The ones that matter most:

| Setting | Why |
| --- | --- |
| `image: nousresearch/hermes-agent:<version>@sha256:<digest>` | A digest is a review checkpoint. Without one, `docker compose pull` can silently move you onto a new release. Move the pin in a commit after reading the changelog. |
| `user: "0:0"`, no `entrypoint` override, `HERMES_UID/GID` = host owner of the data dir | Official: the image's init runs as root to remap the `hermes` user and fix ownership, then drops privileges. Matching the host uid keeps agent and host-script (backup, git) files under one owner. |
| No `no-new-privileges`; `cap_drop: ALL` + seven re-adds | Practice: `no-new-privileges` breaks the setuid remap. Dropping every capability and re-adding what the remap needs is the safer trade. |
| `command: ["gateway", "run"]` | Official: runs the supervised gateway. |
| Ports `127.0.0.1:…` only | Docker-published ports bypass ufw (see §5). |
| `shm_size`, `ulimits.nofile`, `deploy…pids` | Practice: browsers and MCP servers exhaust the defaults. A pids cap stops a fork storm without starving normal work. |
| `stop_grace_period` > s6 grace times | Practice: a SIGKILL during shutdown is how the SQLite session store gets corrupted. |
| One gateway per data directory | Official. Practice: a second container from the same image (e.g. a dashboard sidecar) can start a second gateway on the same bot token; dropped messages then look like "voice is broken". |
| Docker-socket tools | A `:ro` socket mount protects nothing: the API behind it is read-write, i.e. host root. Actions off, auth, loopback, or a read-only socket proxy. |

Run browsers in separate containers, not in the gateway's cgroup. A leaked tab should not be able to kill the gateway.

## 5. Network exposure

1. **Bind every published port to `127.0.0.1`.** Docker inserts its NAT rules before ufw sees the packet, so `ufw deny` does not protect a port published on `0.0.0.0`.
2. **Expose admin UIs through authenticated private ingress.** Tailscale Serve is one example: HTTPS, reachable only from your private network, with identity attached. Add the app's own password as a second layer.
3. **SSH only over the private network**, keys only, no root login. sshd is first-match-wins: a cloud-init drop-in with `PasswordAuthentication yes` beats a later file.
4. **The API server stays off** unless a client needs it. If one does, require a key (official) and keep the port on loopback plus private ingress.
5. Verify from **outside**: run a port scan of the host's public and LAN addresses from another machine. A bind address in compose is not evidence ([hardening §10](hermes-hardening.md#10-secure-gateway-access-and-exposed-services)).

## 6. Secrets layout

| Secret | Where it lives | Never |
| --- | --- | --- |
| Provider keys, bot tokens | `$HERMES_HOME/.env` on the host, mode 600 | in git, chat, or `config.yaml` |
| Secrets a subprocess or skill needs | ops-repo `.env` on the host → compose environment passthrough, or a skill's declared env vars | `hermes config set my.custom_key <secret>`: practice shows custom keys land **plaintext** in `config.yaml` (only recognised keys are routed to `.env`) |
| Backup repository password and keys | a host-only file, mode 600, **not mounted into any container** | readable by the agent: an agent that can read the keys can also prune your backups |

Practice notes:

- **Stripping env vars is not a boundary.** The agent runs as the same OS user that can read `.env`. Treat provider-side scoping (read-only, per-resource tokens, spending caps) as the real limit, and test any claim that "the agent can't reach X".
- **If you use a secret manager**, budget its read rate: every profile, refresh and CLI process pulls. A throttled pull once returned "ok" with empty values and overwrote working secrets; cron and MCP broke while chat kept working. Use a long cache TTL, keep the last good value on throttling (never after an auth failure), and put the remaining budget in your health check.
- Run a secret scanner such as gitleaks on **every** push, including automated commits that skip CI.
- Never paste a secret into a chat with any agent. If one gets pasted, rotate it.

## 7. Bring-up, step by step

```bash
# On the host, inside the ops repo checkout
mkdir -p data/hermes && chmod 700 data/hermes
cp .env.example .env && chmod 600 .env          # fill in compose-level values
# Copy identity BEFORE first start, so the seeded defaults don't win
cp hermes/identity/SOUL.md hermes/identity/ARCHITECTURE.md data/hermes/
docker compose run --rm hermes setup             # wizard: provider, keys, chat platform
docker compose up -d hermes                      # first start; later: your deploy script
docker exec hermes hermes config get approvals.cron_mode
```

Official: `docker exec hermes hermes …` drops to the `hermes` user automatically, so file ownership stays correct. Run the wizard while no gateway is running.

## 8. Initial config baseline

Apply the approval baseline from [hardening §8](hermes-hardening.md#8-configure-approvals-as-guardrails-not-theatre), then the **install-policy trio**:

```bash
# In Docker, prefix each command with: docker exec hermes
hermes config set skills.write_approval true     # skill edits stage for your review
hermes config set memory.write_approval false    # memory writes apply directly
hermes config set approvals.cron_mode deny       # cron never self-approves dangerous shell
hermes config set browser.auto_local_for_private_urls false
hermes config set security.allow_private_urls false
```

The gateway reads `config.yaml` only at boot, so after changing config restart the gateway service (official: `hermes gateway restart`, which runs through s6 inside the container).

Why each one:

- **`memory.write_approval: false`**: when it is `true`, writes outside the interactive CLI are *staged* for approval (official). A cron job has no operator, so its memory writes wait forever in practice. To keep a particular job from writing memory, leave the `memory` toolset off **that job**.
- **`skills.write_approval: true`**: skills are procedures that run later with authority, so they get the slower, reviewed path.
- **`approvals.cron_mode: deny`**: a dangerous command in an unattended job is blocked and reported. It is not auto-approved.
- **`browser.auto_local_for_private_urls: false`**: official: with a cloud browser configured, this is on by default and routes private URLs to a local browser. Practice: that route bypasses the `allow_private_urls` deny.

**Named profiles** (`hermes profile create <name>`) are sparse. In practice, missing leaves fill from **upstream defaults, not from your default profile**. Set the trio and any other safety leaf in every profile, and assert all of them on each deploy:

```bash
for p in default work; do
  for k in skills.write_approval memory.write_approval approvals.cron_mode \
           browser.auto_local_for_private_urls; do
    printf '%s %s = ' "$p" "$k"; hermes -p "$p" config get "$k"
  done
done
```

The policy is **asserted, not locked**: the agent's uid can write `config.yaml`, so a self-edit can flip a leaf. Make the deploy script fail on a mismatch. Read list-typed keys back after `config set`: one build stored a JSON list as a string and a deny list became deny-all.

Fork note: some builds ship a managed config seed. Upstream documents it as a lock; one fork deliberately lets `config set` override it. Check which behaviour your build has.

## 9. Identity in git

Write `SOUL.md` and `ARCHITECTURE.md` from [`templates/SOUL.template.md`](../templates/SOUL.template.md) and [`templates/ARCHITECTURE.template.md`](../templates/ARCHITECTURE.template.md). Keep them in `hermes/identity/` and apply them additively to the data directory. `SOUL.md` is an official slot; an `ARCHITECTURE.md` slot may be build-specific, so verify your version loads it. Slot order, size caps, two-way sync with a self-editing agent and the project-context hijack: [Identity, Memory and Context](identity-memory-context.en.md). Cron jobs and memory are runtime state, so they do **not** deploy through git.

## 10. Backups

1. Run the backup from **host cron**, not Hermes cron, so it still runs while Hermes is down.
2. Use an encrypted, deduplicating tool such as restic. Keep its keys host-only (§6), and deny prune commands to the agent (`approvals.deny` such as `*restic*forget*`).
3. **Never copy a live SQLite file directly.** Stage a consistent copy with the image's own SQLite (a one-shot container from the same digest), run `PRAGMA quick_check` on the **staged** copy, and tag it good only if that passes (an unchecked tagged snapshot once turned out corrupt). Never open the live WAL with the host's `sqlite3`.
4. Exclude caches, logs, worktrees and scratch databases. Keep test fixtures and experimental databases **out of** the data directory entirely.
5. Before each upgrade, take a quick snapshot. The official CLI has `hermes backup --quick --label pre-upgrade`; verify it on your version.
6. **"Backup ran" is not "restorable".** Restore into a scratch directory once a quarter and open the restored database. Day-to-day cadence is in [Operations](operations.en.md).

## 11. First-week acceptance checklist

Probe behaviour, not status. A green `/health` has coexisted with a dead MCP server, a config file that failed to parse and fell back to defaults, a missing bot token and an exhausted provider balance.

- [ ] **Authorized chat**: you message the bot and get a sensible reply.
- [ ] **Unauthorized chat**: a second account messages the bot and gets nothing or a pairing refusal, and the attempt appears in the logs.
- [ ] **Exposure**: an external port scan shows nothing new, and admin UIs answer only over the private network.
- [ ] **Cron canary**: one harmless job (e.g. "reply with the date") fires on schedule, delivers to the right chat, and shows the expected toolset. Recent builds were observed attaching every global MCP server to cron jobs unless the job opts out (a `no_mcp` field; confirm on your version).
- [ ] **Policy**: the loop in §8 prints the expected values for every profile.
- [ ] **MCP**: `hermes mcp list` / `hermes mcp test <name>` succeeds for each enabled server, run inside the container.
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
| SIGKILL on stop | DB "malformed" errors, long full-text index rebuild on next boot | Longer grace; stop, copy, repair the **copy** |
| Process cap hit | "can't start new thread" | Recreate the container (restarting the service is not enough); move browsers out |

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
