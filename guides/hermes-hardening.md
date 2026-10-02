# Hardening Hermes Agent

*A practical baseline for personal, friend, and client deployments*

Hermes can read files, browse hostile content, execute code, use credentials, control external systems, and run while nobody is watching. The goal of hardening is not to make the model timid. It is to make useful authority **explicit, bounded, recoverable, and verifiable**.

This guide combines Hermes controls with practices learned from operating a long-running tool-using assistant. It is an independent publication, not official Nous Research documentation. Where it states a key, value or behaviour, that is what the reference deployment behind this collection (a Docker install that tracks a fork; see [Reference Setup](setup-reference.en.md)) runs and asserts; where a behaviour depends on the fork, the text says "on the fork build used here". Hermes changes quickly: on another build, verify version-sensitive commands against that build's `--help` and the [official Hermes documentation](https://hermes-agent.nousresearch.com/docs/) before applying them.

For an agent-executable procedure, install the companion skill:

```bash
hermes skills install djagya/beyond-prompting/skills/hermes-hardening
```

Then invoke:

```text
/hermes-hardening Assess this Hermes deployment. Do not change state.
```

Installation makes the procedure available; it does **not** authorize the agent to modify a deployment.

## 1. The security model

### Capability is not authority

A tool being available does not mean the agent is authorized to use it for every purpose. Keep these separate:

1. **Capability** — the system can perform an action.
2. **Policy** — the action is allowed under stated conditions.
3. **Authorization** — this specific action is permitted now.
4. **Evidence** — the action happened as intended.

A model instruction such as “never send without approval” is useful operating policy, but it is not an enforcement boundary. Whenever consequences matter, move the boundary outside the model: scoped credentials, tool filtering, OS permissions, network policy, approval gates, or a separate service that can refuse the action.

### The dangerous combination

The highest-risk agent has all three:

- access to private or privileged data;
- ingestion of untrusted content such as web pages, email, documents, repositories, or task comments;
- an external communication or action channel.

This is a practical form of Simon Willison's [lethal trifecta](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta). Remove at least one edge where possible. A low-trust research profile should not also hold payment, production, or administrative credentials.

### Hardening is not one switch

Hermes has useful built-in guards, but none of these alone is a sandbox:

- prompt instructions;
- secret redaction;
- command approvals;
- file-write guards;
- profiles;
- MCP trust labels;
- model refusals.

Treat them as layers. For privileged or unattended deployments, add OS/container isolation, resource limits, network restrictions, scoped service identities, backups, and adversarial verification.

## 2. Classify the deployment before changing it

Record these decisions first:

| Question | Why it changes the baseline |
| --- | --- |
| Who can send messages to the agent? | Determines gateway authorization and abuse surface. |
| Does it ingest web, email, documents, repositories, or tickets? | Introduces indirect prompt-injection risk. |
| Which data classes can it read? | Determines profile, credential, filesystem, and retention boundaries. |
| Which external systems can it modify? | Determines approval and transaction controls. |
| Does it run unattended? | Requires fail-closed headless policy, bounded automation, and monitoring. |
| Is it a personal, friend, or company deployment? | Changes identity separation, audit, retention, and offboarding requirements. |
| Is any listener reachable beyond loopback? | Requires host-level exposure verification, authentication, TLS, and rate limiting. |
| What is the recovery objective? | Determines backups, restore tests, and acceptable lockout risk. |

Do not infer isolation from a profile name or a container label. Verify the effective runtime.

## 3. Start with evidence and a recovery point

Before hardening a live system, capture enough state to recover without dumping secret values into the report.

Run the assessment from a separate operator/evidence workspace. Do not use the assessed repository, profile home, or mounted data root as the agent's working directory until you understand where that runtime writes sessions, logs, caches, checkpoints, command-output captures, and temporary files. “Read-only assessment” means no deliberate target mutation; it does not mean the orchestration runtime performs zero filesystem writes. Snapshot the target before and after and classify runtime evidence separately.

Use explicit profile/target arguments and verify the terminal tool's actual working directory. A session's apparent project directory is not evidence that every backend command ran there.

The following diagnostics are useful, but some can expose partial credential fingerprints, user identifiers, paths, integration names, and topology. On live personal or client systems, do not blindly paste raw output into a model or report. Prefer targeted `config get` queries, local field allowlisting, and a human-reviewed metadata summary. Redaction is still required; truncation or masking is not anonymity.

```bash
hermes --version
hermes status
hermes config path
hermes config check
hermes doctor
hermes tools --summary
hermes mcp list
hermes pairing list
hermes cron list
hermes security audit --fail-on high
```

`hermes config check` and `hermes doctor` resolve every secret reference. If secrets come from an external manager with a read budget, check the remaining budget first and do not run them while it is spent (section 6).

Check the target version's backup contents and retention first. Use `--quick` only when its documented critical-state coverage includes every proposed target; it is not a generic backup of skills, plugins, project files or external state. Otherwise use a full backup and separately protect project and external state. Full-backup retention may delete older archives; choose a protected output location and retention policy before running it.

When that coverage is sufficient, create a protected critical-state snapshot before mutation:

```bash
hermes backup --quick --label pre-hardening
```

The reference deployment layers three copies: Hermes' own pre-update quick backup (`updates.pre_update_backup: quick`, a few kept), a verified runtime snapshot taken by the deploy tooling before every image upgrade, and a nightly encrypted off-site backup (section 14). None of them replaces the others.

A full backup may include credentials, sessions, and sensitive state. Protect it like the live profile. A profile export strips keys and is suitable for distribution; it is not a full disaster-recovery backup.

**Do not call backup complete until restore has been exercised** on a disposable profile or machine. Existence of an archive proves only that an archive exists.

For project work, consider opt-in checkpoints:

```bash
hermes config set checkpoints.enabled true
hermes checkpoints status
```

Checkpoints protect project files. They do not replace Hermes-home backups, provider exports, or external-system recovery.

## 4. Run with the least powerful OS identity that works

For an always-on gateway or company deployment:

- use a dedicated unprivileged OS/service account;
- do not run the gateway as root;
- do not grant passwordless `sudo` unless a narrowly scoped operational requirement justifies it;
- set CPU, memory, process, and disk limits for containers/services;
- expose only required mounts, preferably read-only;
- keep the Docker socket, host PID namespace, SSH agent, cloud metadata, and unrelated credential stores out of reach;
- verify the effective UID, capabilities, seccomp/no-new-privileges state, mounts, and listeners from the host—not from a narrative produced inside the container.

Hermes' official security guide recommends a container backend for production gateways. A container with sensitive read-write mounts, ambient credentials, broad egress, or the Docker socket remains highly privileged. The reference deployment makes the opposite trade-off deliberately: the gateway runs inside a hardened container with `terminal.backend: local`, so agent commands run in the gateway's own container, dangerous-command approvals still fire, and the outer container is the boundary.

Container rules the reference deployment encodes in its compose file:

- **"Not root" means the gateway process, not the container start user.** The image starts as root (`user: "0:0"`) so its entrypoint can remap the runtime UID/GID to match the host data owner and then drop privileges with `gosu`. `no-new-privileges` on the gateway container breaks that setuid remap, so it is omitted; instead use `cap_drop: [ALL]` and re-add only what the remap, `gosu` and service stop need (`CHOWN`, `DAC_OVERRIDE`, `FOWNER`, `FSETID`, `SETUID`, `SETGID`, `KILL`), plus a targeted seccomp profile. If an in-container sandbox (for example bubblewrap) needs user namespaces, extend seccomp narrowly; never use `seccomp=unconfined` or `privileged`. The reference also runs the gateway container AppArmor-unconfined for that reason, an accepted trade-off; its browser containers load a dedicated AppArmor profile that adds only user namespaces. Verify the effective UID of the gateway process from the host. Because the container starts as root, a plain `docker exec <container> hermes …` lands as **root**; the privilege drop applies only to the entrypoint's own process tree. Run every CLI call as the runtime user through a small wrapper (`docker exec -u <runtime-user> …`), never as root, or root-owned files in the data home can be silently ignored or break the gateway and scheduler.
- **Pin the file-write safe root in the container environment.** The image's default write-safe root is the data home only; writes elsewhere are hard-blocked with no approval prompt. Extend it explicitly (for example `HERMES_WRITE_SAFE_ROOT=$HERMES_HOME:<workspace>:/tmp`) in the compose environment, because the image's own environment beats values in the Hermes `.env`.
- **Keep child-process state apart from gateway state.** The reference gives child CLIs (git, gh, MCP helpers) their own HOME under the data directory, separate from `HERMES_HOME` (on the fork build used here, via `HERMES_CHILD_HOME`). Do not point the gateway's own `HOME` at that child path.
- **Know what can shadow image binaries.** If a writable directory inside the data home is on `PATH`, a stale copy of a system tool placed there wins over the image's binary. Keep image directories first, and detect shadows with a check rather than reordering `PATH` for one tool.
- **A read-only Docker socket mount protects nothing.** `:ro` covers the socket file, not the API behind it; anything that can reach the socket is close to host root. Log viewers and dashboards that need it should have actions disabled, bind to loopback, sit behind authentication, or use a read-only socket proxy.
- **Size process and file limits for what the agent actually spawns.** Browsers and stdio MCP servers consume PIDs, file descriptors and shared memory quickly (the reference sets a PID cap in the thousands, `nofile` 8192/65535, 1 GB `shm` and an explicit memory/swap limit). Run Chromium/Playwright-type workloads in their own containers, not inside the gateway's cgroup: a PID-cap hit there kills the gateway. After `can't start new thread` or a PID-cap death, recreate the container; restarting the service inside it does not reclaim leaked processes.
- **Agents can exhaust container memory with ordinary file tools.** Reading every file whole across the data directory (which may contain a multi-gigabyte state database) can trigger the OOM killer. Prefer streaming reads, size checks before reads and per-command memory limits; encode this in the skill that performs scans, and watch kernel OOM kills in the container cgroup as a health signal.
- **Give the stop path enough time.** Set the container stop grace period longer than the supervisor's own service and kill grace times, and keep the gateway's forced-drain timeout well under it. A supervisor that SIGKILLs a gateway a few seconds after SIGTERM is a known cause of state-database corruption.

See [Reference Setup](setup-reference.en.md) for a worked container layout.

## 5. Separate trust zones with profiles—and know their limit

A Hermes profile isolates Hermes state: config, `.env`, memory, sessions, skills, cron jobs, plugins, and gateway state. It does **not** sandbox the filesystem or the host user.

Profile cloning can copy secret state depending on the selected options. Inspect clone/export behavior before using a profile as a client template; a sanitized profile export is not equivalent to cloning a live home.

Create distinct profiles when purpose or trust differs:

```bash
hermes profile create research --description "Low-trust research and document analysis"
hermes profile create operator --description "Bounded privileged operations"
```

Useful separations include:

- low-trust web/email/document ingestion;
- privileged operator;
- software builder;
- independent reviewer;
- one profile per company or client.

Never let two live Hermes processes write the same profile. If they need shared state, use an external canonical store with explicit concurrency semantics. This includes sidecars: a dashboard or helper container started from the same image can bring up its own supervised gateway against the same data directory. Two gateways polling one bot token produce platform `Conflict` errors and dropped messages that look like an unrelated feature failure.

Two further profile facts that change the baseline:

- **A named profile does not inherit the default profile's values.** Leaves missing from a sparse profile `config.yaml` fall back to built-in defaults, which can be more permissive than the policy you set on the default home: `cron.catch_up_missed`, `gateway.auto_multiplex_migration` and `browser.auto_local_for_private_urls` all default to `true`. The reference deployment stamps its required leaves into every named profile and the default home (inserting missing leaves, keeping every other key), and its deploy fails when any live home lacks them. Stamp the live files in place; do not overwrite a live profile's config from a stale copy.
- **The gateway is multiplexed.** One gateway process serves every profile. Upstream has retired `gateway.multiplex_profiles: false` as an opt-out: the gateway rewrites it to `true` at boot, so pinning `false` holds nothing. A profile that must run its own gateway sets `gateway.standalone: true` in its own config. Set `gateway.auto_multiplex_migration: false` (the key the update hook reads; an older `gateway.auto_migrate` leaf is ignored) if you do not want updates to change topology for you. What multiplexing changes: one crash domain (a crash, restart, PID or memory hit on the default gateway takes every profile's chat, cron and task dispatch down together), one cron scheduler for all profiles, and secrets resolved strictly per profile with no fallback to the process environment, so a profile whose secret snapshot is empty fails closed. Verify the effective topology on your build after each upgrade.

Set a deterministic starting directory:

```bash
hermes -p research config set terminal.cwd /absolute/path/to/research-workspace
```

For stronger separation of external CLI state:

```bash
hermes -p research config set terminal.home_mode profile
```

`terminal.home_mode: profile` gives subprocesses a profile-specific `HOME`; initialize only the CLI credentials that profile actually needs. Without it (the default is `auto`), profiles normally share the OS user's Git, SSH, GitHub, cloud-CLI, and similar state. The reference deployment keeps `auto` and separates child-process state from gateway state at the container level (section 4); a profile that needs its own CLI identities uses `profile`.

For real filesystem isolation, use a container, VM, dedicated user, remote worker, or OS sandbox. `SOUL.md`, `AGENTS.md`, `terminal.cwd`, and profile names are not access controls.

## 6. Treat secrets as capabilities

### Baseline

- never put secrets in Git, prompts, skills, `AGENTS.md`, reports, or examples;
- use separate credentials per profile, client, service, and environment;
- prefer read-only or resource-scoped tokens;
- avoid a single general-purpose vault containing personal, financial, administrative, and client credentials;
- remove stale credentials, not merely unused MCP definitions;
- rotate or revoke credentials during offboarding;
- record credential **names, owners, scopes, and expiry**, never values, in audit output.

Keep Hermes secret redaction enabled:

```bash
hermes config set security.redact_secrets true
```

Gateway PII redaction is a trade-off: test that it does not remove context the workflow genuinely needs. The reference deployment runs with it on, even as a personal gateway; for shared or company gateways it should be the default:

```bash
hermes config set privacy.redact_pii true
```

Redaction reduces accidental disclosure in context and logs. It does not stop a compromised process from reading a secret and sending it through an allowed network channel.

Where possible, inject credentials only into the process that needs them. Prefer external secret managers or service-specific identities over a large ambient `.env`. Keep every `.env` file mode `600` and enforce that from host provisioning, not memory. Nothing secret belongs in `config.yaml` itself: secret-bearing leaves such as webhook route secrets are `${ENV}` interpolations, never literals.

### Pitfalls the reference deployment encodes

- **Removing a variable from subprocess environment is not a boundary.** Agent shells run as the same OS user as the gateway; they can read the Hermes `.env`, or start their own `hermes` CLI process that resolves every secret reference itself. With the local terminal backend, child processes also inherit the gateway's process environment, minus a built-in blocklist of infrastructure names, so a provider key in the container environment reaches agent shells whether or not `terminal.env_passthrough` lists it. Probe what an agent shell can actually obtain. The enforceable boundary is the credential's provider-side scope.
- **A credential the agent's shell must use is fully visible to it.** When a tool in the terminal needs a token (for example a Git hosting CLI), anything running in that terminal can read it. Scope it to the minimum resources and treat it as exposed.
- **Custom `config set` keys are not secret storage.** Only recognized credential keys are routed to `.env`; an arbitrary key holding a token lands in plaintext in `config.yaml`, with only a warning. If that file is mirrored to Git or backed up, the token goes with it. Pass a secret a subprocess needs through the environment (for example a container env passthrough from a host-only `.env`). Scan the config for literal credential shapes before every automated commit or push, including bot commits that skip CI; the reference deployment's publish path refuses a config that contains one.
- **External secret managers have budgets.** If secrets are resolved from a manager with a per-account read budget, every home pulls on its own: each profile, each gateway boot, each `hermes` CLI process (including ones the agent starts from its shell), and, on a multiplexed gateway, a re-pull before cron runs once the cache expires. Diagnostics such as `hermes doctor` and `config check` resolve every reference too. With a short default cache TTL this can spend a daily budget in hours. Once the budget is spent every read fails, and a boot or restart comes up without messaging tokens while the health endpoint stays green. The reference deployment's design: a cache TTL of hours set in every home (a rotated secret then needs that home's cache cleared before restart); grouped reads per item that stop at the first rate-limit response and write one account-wide backoff marker; a throttled re-pull that keeps the last good values instead of emptying the scope; agent shells in cache-only mode so a shell `hermes` never calls the manager (on the fork build used here); a budget row in the health sweep; and upgrades and planned restarts refused while the budget is spent. Cache-only mode protects the budget, not the vault: the service account's scope is still the real limit.
- **Keep backup credentials away from the agent.** Store the backup repository password and storage keys together in one host-only, mode-`600` file that is not mounted into the agent's container, so a compromised or confused agent cannot delete or prune backups. Add deny rules for backup-destruction commands (for example `*restic*forget*`) as a second layer.

Use supported secret-entry mechanisms that keep passwords, payment credentials and verification codes outside model context. Do not ask for these values in chat or type them with general-purpose browser inputs. If no supported mechanism exists, hand secret entry to the owner; never invent a private vault integration.

## 7. Minimize the tool surface

Messaging platforms commonly inherit a broad default toolset. Configure tools per platform and profile instead of assuming “the agent will not use them.”

```bash
hermes tools --summary
hermes tools
```

Use `hermes tools disable ...` and `hermes tools enable ...` to build an allowlist appropriate to the role. For one-off CLI work:

```bash
hermes chat --toolsets web,file
```

Patterns:

- **Research profile:** web, read-only document tools, perhaps vision; no terminal, credentials, outbound messaging, or administrative MCPs.
- **Builder profile:** project file and sandboxed terminal access; no personal memory or unrelated SaaS tools.
- **Reviewer profile:** read-only evidence surface; no silent repair path.
- **Operator profile:** only the exact systems it operates, with scoped identities and transaction gates.

Do not use `all` or a full platform toolset merely for convenience on a public or low-trust gateway. Re-check the surface after updates, plugin installs, and MCP changes.

Toolset changes apply to new sessions. Start a fresh session and inspect the effective surface rather than treating a saved setting as immediate enforcement.

## 8. Configure approvals as guardrails, not theatre

A practical baseline:

```bash
hermes config set approvals.mode smart
hermes config set approvals.cron_mode deny
hermes config set approvals.single_query_mode deny
hermes config set approvals.unattended_mode deny
```

`single_query_mode` (one-shot `-q` sessions) and `unattended_mode` (webhook and API-server sessions) default to `deny`; the reference deployment leaves them at that default and asserts `cron_mode: deny` on every deploy (below). On a build without `approvals.unattended_mode`, programmatic sessions need an explicit external execution boundary, not an invented config key.

These settings do not prove fail-closed behavior on every terminal backend. Dangerous-command checks are skipped on container and sandbox terminal backends such as `docker`, `singularity`, `modal`, `daytona` and `vercel_sandbox`, because that backend is treated as the boundary. Keep two questions separate: where the Hermes process itself runs (for example an outer Docker container) and which `terminal.backend` executes agent commands. For each profile, read the effective terminal backend and use `hermes approvals test` where supported to obtain a verdict without execution; then assess the actual isolation of the sandbox backend (mounts, credentials, egress) rather than counting the deny settings as enforcement. Never run a dangerous command to prove that it is denied.

For high-consequence interactive administration, consider `manual` instead of `smart`.

Avoid:

- `approvals.mode: off`;
- `--yolo` on a privileged host;
- `HERMES_YOLO_MODE=1` in aliases or service units;
- `cron_mode: approve` for general autonomous jobs;
- broad permanent allowlist entries such as an interpreter, shell, package manager, or `systemctl`.

Review accumulated permanent approvals:

```bash
hermes config get command_allowlist
hermes approvals suggest
```

To reset them, set `command_allowlist: []` as a YAML list with `hermes config edit` (not a quoted `'[]'` through `config set`; see the list-type warning below), then read it back with `hermes config get command_allowlist`.

Audit each permanent entry for what it pre-approves, not what it was added for. Entries are approval classes, not exact commands: the class `script execution via -e/-c flag` pre-approves every interpreter one-liner (`python`, `perl`, `ruby`, `node` with `-e` or `-c`) in every session. The reference deployment accepts exactly that one class, because unattended jobs that cannot answer prompts depend on it; `bash -c` / `sh -c` is a different class and still prompts, and hardline blocks and `approvals.deny` still run first. Its config guard fails a deploy on any other entry; an empty list also passes. Whether to accept that class is an owner decision, recorded with its reason, not a silent default.

Read back the **type** of any list-valued key you set from the command line. Stock `hermes config set` has stored a JSON list as a YAML string: iterating that string turned a deny list into one glob per character, so `*` matched every command, and a stringified mention-pattern list silenced every group topic while direct messages worked. The fork build used here carries a parser fix; do not rely on it elsewhere. Prefer `hermes config edit` or a YAML list in the file for structured values, then verify with `hermes config get`.

**Policy is asserted, not locked.** The reference deployment's install policy is `skills.write_approval: true`, `memory.write_approval: false` and `approvals.cron_mode: deny` (section 11 explains the memory choice). If `config.yaml` is mirrored to Git or the agent can run `hermes config set`, an export or self-edit can flip those leaves unnoticed; a runtime export once turned `skills.write_approval` off. "Only the owner changes config" is policy, not a filesystem fact when owner and agent share a UID. So a check script reads the effective trio through `hermes config get` (defaults, then any managed seed, then user config — what the gateway sees) after every deploy and fails the deploy on a mismatch; it exits with a distinct, retryable code when the values could not be read at all, so a container still starting is never confused with a policy violation. On the fork build used here, the image bakes those three leaves into a managed config seed that fills them only when user config omits them; the seed is **not a lock**: `hermes config set` wins and `unset` lets the seed show through. Upstream documents managed scope as a lock; verify which behaviour your build has, and do not add managed keys to "lock" behaviour on a build where they are only a seed.

Use `approvals.deny` for deterministic “never through this agent” commands. Quote YAML glob patterns; matching is fnmatch over the normalized command text and applies even when approvals are off or in YOLO mode. The reference denies backup destruction (`*restic*forget*`) and hook bypass (`*--no-verify*`), and its guard requires both. Keep ordinary test runners off the deny list; a guard against live lifecycle tests belongs in the test harness. Deny rules protect against an honest-but-wrong agent; they do not contain an adversarial process with equivalent OS access.

Before using a rule, test its verdict without executing the command:

```bash
hermes approvals test 'the command to evaluate'
```

Remember that file-write guards apply to `write_file` and `patch`; terminal access still runs as the OS user. Hard filesystem boundaries belong outside the model and outside individual tools.

## 9. Keep private-network access closed unless it is required

Leave SSRF/private-URL access disabled for public-facing or low-trust profiles:

```bash
hermes config set security.allow_private_urls false
```

When enabled, web, browser, vision URL fetches, and gateway media downloads may reach loopback, RFC 1918, link-local, CGNAT, and cloud-metadata addresses. That can turn an injected URL into an internal-network probe.

This setting alone does not close the browser path. `browser.auto_local_for_private_urls` defaults to `true` and routes private URLs to a local browser instead of rejecting them; `security.allow_private_urls` does not cover that path. The reference deployment sets both browser leaves false in the default home and in every named profile, because a sparse profile inherits the `true` default, and its health sweep fails a home where either leaf is missing or true:

```bash
hermes config set browser.allow_private_urls false
hermes config set browser.auto_local_for_private_urls false
```

Then probe the deny path from the effective runtime. SSRF blocks in the logs are then expected, not a fault.

If a profile genuinely needs internal URLs:

- isolate that profile from public/untrusted input where possible;
- block cloud metadata at the network layer;
- allowlist destinations with an external proxy/firewall;
- do not rely on DNS names alone;
- verify denied and allowed destinations from the effective runtime.

Enable Tirith command scanning:

```bash
hermes config set security.tirith_enabled true
```

Hermes defaults to fail-open if Tirith is unavailable. The reference deployment runs fail-closed. Choose fail-closed **only after verifying the binary and a safe test path**, otherwise routine commands can be locked out:

```bash
tirith --version
hermes config set security.tirith_fail_open false
```

Tirith is not available as a prebuilt native Windows binary; use WSL if this layer is required.

Runtime dependency installation (`security.allow_lazy_installs`) lets opt-in backends (memory providers, telemetry exporters, plugin dependencies) install their packages on first use. On image installs those land in a dependency area under the data directory, never in the sealed application environment, and are re-resolved against each new image. The reference keeps it on, because turning it off freezes the feature set to what the image shipped and breaks any backend enabled later. The cost is a supply-chain gap: those packages come from the package index at runtime, outside the image SBOM and its rescans, so review a newly enabled backend like an image pin and read what is installed from the package manager's sync receipt. For controlled environments where the feature set is fixed, disable it after provisioning and testing:

```bash
hermes config set security.allow_lazy_installs false
```

Connected browser mode can act inside authenticated sessions. Use a dedicated low-privilege browser profile for hostile content, keep logged-in administrative sessions away from low-trust ingestion, and consider `browser.restrict_evaluate`. That option is a name-based denylist of sensitive JavaScript primitives (cookies, storage, clipboard, network calls, form values) for page evaluation; it does not disable arbitrary JavaScript and is not a sandbox. First establish which browser driver and backend actually apply: the default Browser Use mode exposes `browser_exec`, which runs model-written Python and is offered only to sessions that also have terminal access (verify on your build), so terminal and browser authority must be assessed together. Review `security.website_blocklist`, but do not mistake a domain blocklist for prompt-injection containment or network egress policy.

The reference deployment treats the browser and page content as untrusted and keeps no browser inside the gateway's cgroup:

- browsers are a fixed set of slots in their own containers, leased per task through a controller; `browser.cdp_url` stays empty and the health sweep fails any Chromium process or loopback CDP port inside the gateway container;
- slots never join the network that reaches the gateway API; their only exit is one egress network policed by a host firewall chain, with private-app access granted per task and revoked on recycle;
- the controller accepts the gateway's bearer only from the gateway's own network address, and humans observe or take over a browser only through the private ingress identity, never with that bearer;
- research and QA get a temporary profile on size-capped tmpfs; persistent logged-in profiles are split by organization, not by site, and join the normal encrypted backup;
- Chrome's own sandbox stays on: no `--no-sandbox`, no unconfined seccomp or AppArmor, no `SYS_ADMIN`; the slot refuses to start when the sandbox is missing.

## 10. Secure gateway access and exposed services

Hermes gateway authorization is deny-by-default, but verify the actual configuration.

- use platform allowlists or DM pairing;
- never use `GATEWAY_ALLOW_ALL_USERS=true` for a private or company agent;
- distinguish gateway admins from regular users;
- give separate profiles separate bot tokens;
- revoke stale pairings during offboarding;
- review pending and approved identities:

```bash
hermes pairing list
```

Manage pairing through supported commands, not by editing pairing state directly:

```bash
hermes pairing approve <code>
hermes pairing revoke <platform> <user-id>
```

Before service changes:

```bash
hermes gateway status
```

A service bound to `0.0.0.0` inside a container is a risk signal, not proof of internet exposure. Verify all layers:

1. process bind address;
2. container port publishing;
3. host firewall;
4. reverse proxy;
5. TLS and authentication;
6. rate limits;
7. external reachability from an authorized scanner.

On Linux, ports published by Docker are inserted ahead of host firewall rules such as `ufw`: a published port can be reachable even though the firewall appears to deny it. Bind published ports to `127.0.0.1` and reach them through an authenticated private ingress (a tailnet proxy, VPN, or authenticated reverse proxy), or enforce restrictions at the service itself. The reference deployment publishes every port on loopback only, reaches them through tailnet HTTPS ingress, and its health sweep fails any listed port bound to anything other than loopback or the host's own tailnet addresses.

Inside its container, the reference API server listens on `0.0.0.0` because the port mapping and a sidecar web UI on the compose network need it. The startup warning about a non-loopback bind with the local terminal backend is accepted on purpose: the host publishes loopback only and the API requires its key. The residual is real: any container on that compose network that holds the key can drive the agent with its full tool authority.

A self-hosted CI runner on the agent's host is a listener of a different kind: anyone who can run a workflow on it runs code on the host and reads whatever it mounts. Keep such a runner only for a private repository with no workflow triggered by fork pull requests, and remove it before either condition changes.

Dashboard, API, browser CDP, metrics, webhook, and noVNC endpoints should normally bind to loopback or a private authenticated network. Never expose browser CDP directly to the internet.

Hermes' dashboard defaults to loopback; non-loopback use requires authentication and still needs host-level TLS/exposure verification. The API server is more consequential: it can expose the agent's effective tool authority, uses bearer authentication, and should keep an exact CORS allowlist rather than `*`. Test unauthenticated rejection and authorized readiness from outside the process.

For webhooks, use a root or per-route secret, HMAC or platform signature verification, timestamp/replay protection, source-IP restrictions where stable, and rate limits. Treat payloads as untrusted data. Never use insecure/no-auth mode on a listener reachable by anything outside a disposable isolated test.

On Linux/systemd, Hermes supports an optional event-loop watchdog for gateway stalls. Use it only with a supervised service and verify restart behavior:

```bash
hermes config set gateway.systemd_watchdog_seconds 120
hermes gateway install --force
```

This regenerates the service unit and may interrupt service; preview and authorize it as an operational change.

Any automatic restarter, built-in or home-grown, must:

- stop gracefully with a grace period long enough to drain writes. A forced kill mid-write is a known trigger for state-database corruption and stale search indexes;
- honor a deliberate stop. A watchdog that revives a container the owner stopped for repair can turn a recoverable problem into data loss;
- alert instead of healing silently. Silent revivals hide a recurring fault until it becomes an outage.

A host-level loop that runs `docker restart` on failed health checks usually violates all three. The reference deployment removed exactly such a watchdog and runs none: its `docker restart` SIGKILLed the gateway, its silent revivals hid a recurring fault, and it revived a container stopped for repair. What remains is the in-container supervisor restarting a crashed gateway, Docker's `unless-stopped` policy for a container that exits, and a container healthcheck used for observability only. The accepted trade-off: a gateway that is down inside a still-running container is not revived automatically; the health sweep's gateway-slot row and a silent agent are the detection.

The durable delivery ledger is on by default (the reference deployment leaves it so). Keep it enabled unless a specific privacy or storage analysis rejects it:

```bash
hermes config set gateway.delivery_ledger true
```

At-least-once delivery can produce a labeled duplicate after an ambiguous crash. Downstream actions still need idempotency.

## 11. Constrain MCP servers, plugins, skills, and hooks

Treat each extension as code or authority entering the runtime.

### MCP

- prefer official or reviewed servers;
- pin versions for local command-based servers;
- use TLS verification; do not normalize `ssl_verify: false`;
- reference secrets through environment variables, not literal config values;
- mark servers you do not fully control as `trust: untrusted`;
- use `tools.include` rather than broad exposure;
- disable resources and prompts when unnecessary;
- test the connection and inspect the effective tool list.

Example shape:

```yaml
mcp_servers:
  example:
    url: "https://mcp.example.com/mcp"
    trust: untrusted
    tools:
      include: [list_records, get_record]
      resources: false
      prompts: false
```

A server-supplied `readOnlyHint` is a hint, not proof. Prefer credentials and APIs that are technically read-only.

For command-based (stdio) servers, verify after every image or dependency update that each enabled server's `command` still resolves, using the gateway's own environment and `PATH` rather than your shell's. An update that drops or moves a binary leaves the server failing on every boot while the gateway's health endpoint stays green. The reference deployment probes every enabled stdio command with the gateway's own resolver on each deploy and in its health sweep; a missing command is an image regression to fix in the image, not a config tweak. Prefer URL-based MCP servers with native OAuth over local bridge processes where the provider offers one.

### Plugins, skills, and context files

- inspect before installing;
- keep provenance and update source;
- run `hermes security audit` after dependency changes;
- do not force-install a skill that fails security scanning without manual review;
- treat repository content as untrusted until the user deliberately trusts or installs it;
- keep `AGENTS.md` concise and project-specific;
- put reusable procedures in `SKILL.md`, not in a giant project prompt;
- review shell hooks explicitly; keep `hooks_auto_accept: false` and never use `--accept-hooks` or `HERMES_ACCEPT_HOOKS` as a casual default;
- shield the agent's working directory: project context files load first-match-wins from the working directory (`.hermes.md`, then `AGENTS.md`, `CLAUDE.md`, Cursor rules). If the agent works inside a repository whose `AGENTS.md` or editor rules were written for another tool, those become its instructions. A **non-empty** `.hermes.md` at that root takes precedence; an empty one falls through. See [Identity, Memory and Context](identity-memory-context.en.md);
- decide the agent-write gates per profile:

```bash
hermes config set skills.write_approval true
hermes config set memory.write_approval false   # see below
```

- distinguish scanner acceptance from trust: pin and review extension provenance before activation.

With `write_approval: true`, writes outside the interactive CLI are staged for an operator to approve. That is a sound default for skills, which are executable procedure. For memory it is a trade-off: in any profile that runs cron or other unattended work, nobody is present to approve, so staged writes accumulate and the job silently loses what it meant to remember. The reference deployment's install policy is `skills.write_approval: true` and `memory.write_approval: false`, asserted after every deploy (section 8); jobs that must not write memory at all omit the `memory` toolset. Its upgrade rehearsal proves all three behaviours on a sanitized copy: a cron-shaped memory write persists, an agent skill write stages for approval, and a job without the `memory` toolset cannot write memory. Do not turn memory approval on to be "safe"; set `memory.write_approval: true` only where every writer is interactive, or where someone reviews `/memory pending` on a schedule.

A memory plugin or memory sidecar is a new process holding the agent's most sensitive data. The reference deployment keeps its memory control surface as a guarded opt-in outside the default compose set: the sidecar has a read-only root filesystem, shares only the web UI's network namespace (no new port or ingress route), and gets no Hermes home, gateway token, task database or Docker socket. Its access token is minted after operator consent and mounted read-only, and is not a boundary against compromised code running as the same UID in the web UI. Activating such a component does not by itself enable any caller policy or MCP server.

Project instructions, skills, comments, tickets, web pages, and documents do not inherit authority merely because the agent can read them.

## 12. Design autonomous jobs as standing mandates

A cron job is not a reminder to “use judgment somehow.” It is a standing delegation that wakes with no user present.

For each job define:

- bounded purpose;
- input sources;
- enabled toolsets;
- skill(s) and self-contained prompt;
- work directory where needed;
- model/provider policy and cost boundary;
- external delivery target;
- mutable state and idempotency key;
- timeout, retry, and ambiguous-outcome behavior;
- success evidence;
- failure alert and owner;
- pause, rollback, and retirement procedure.

Keep:

```bash
hermes config set approvals.cron_mode deny
```

Use script-only jobs when a deterministic script can produce the exact alert. Use an agent only when interpretation is required. For agent jobs, explicitly restrict toolsets instead of inheriting the full gateway surface.

The stored toolset list is not the effective surface. The scheduler adds every globally enabled MCP server to an agent cron job unless the job's toolsets include the literal sentinel `no_mcp`. Resolve the effective surface through the scheduler's own rule and test one allowed and one denied cross-lane action; a check that merely forbids the string `mcp` in the list is not enough.

A dangerous command in a deny-mode cron job produces a pending approval that no one can answer. Treat it as a policy blocker to report, not a request to wait on; split compound commands so the safe part can proceed.

Scheduling behaviour to design for (one caveat for the whole list: verify on your build):

- interval schedules such as `every 1m` are measured from the end of the previous run, so they drift; use a wall-clock cron expression when timing matters;
- `cron.catch_up_missed` defaults to `true`, so missed runs fire after downtime as a burst on restart; the reference deployment pins it `false` in the default home and every named profile;
- unpinned jobs follow changes to the default model; the reference sets a cron-wide `cron.model`, and a job pins its own model when cost or behaviour matters;
- a one-shot schedule with `repeat` greater than one is not recurrence: it completes after its first fire; use an interval or cron schedule for bounded repeats and check that the next run time advances;
- completed one-shot jobs are swept from the job store after seven days; a registry or drift check that mirrors the job list must expect that removal;
- script jobs name a script by basename under `$HERMES_HOME/scripts/`; the scheduler rejects absolute paths, so keep one canonical copy of each script in version control and deploy it to that directory under the exact name the job uses;
- jobs that are paused on purpose should stay paused through deploys and self-edits; the reference health sweep fails when one of them is found enabled;
- a deterministic monitor script whose unchanged output suppresses the agent turn is cheaper and more reliable than adding another poller.

Test the failure-alert path end to end with a real message to the real destination. An alert that fails with a delivery error, or a scan left in report-only mode, can stay silent for weeks while the job looks configured. Background loops need a circuit breaker that pages after N consecutive failures. See the [runtime automation governance skill](../skills/runtime-automation-governance/SKILL.md) for the procedure.

Cron sessions are fresh. Do not write prompts such as “continue that thing”; provide all required context or attach maintained skills. Use `workdir` when project instructions and repository context must load.

ASSESS and VERIFY jobs must not persist findings, hostile source text, or recommendations into long-term memory unless a reviewed, structured persistence step is separately authorized. Otherwise an audit can become a cross-session prompt-poisoning mechanism.

Inspect execution history, not just the current schedule:

```bash
hermes cron list
hermes cron status
hermes cron runs <job-id> --limit 20
```

Change jobs through `hermes cron`, `/cron`, or the `cronjob` tool; do not hand-edit `cron/jobs.json` as a normal configuration path. Jobs are runtime state: a copy in version control is a seed, not the deploy path, so changing it does not change a live job. One narrow exception exists: `hermes cron edit` cannot set a job's `enabled_toolsets`, so edit only that field, atomically (write a temporary file, then rename it into place), with the scheduler's file lock respected where one exists, as the runtime user (a root-written job file breaks the scheduler), then read the job back through `hermes cron list`. Prefer the CLI as soon as your build supports the field.

## 13. Define outward-action boundaries

Use an explicit operating contract:

- research is not implementation;
- drafting is not sending;
- preparing a form is not submitting it;
- producing a migration plan is not moving data;
- creating an invoice artifact is not issuing or paying it;
- having a credential is not permission to use it for a new purpose.

A useful state-changing protocol:

```text
inspect → preview → execute → read back → record
```

The preview should name:

- exact action and target;
- scope/count;
- expected effect;
- reversibility and recovery boundary;
- material failure modes.

A successful write response is not evidence that the intended state exists. Read it back through the closest independent surface.

Require fresh action-specific confirmation for irreversible outward communication or commitment, credential revocation/rotation, destructive no-rollback changes, access-policy changes that can lock out the owner, restore/import operations, and service interruptions unless a bounded standing mandate already covers them.

## 14. Make recovery an exercised capability

A recovery design should cover:

- Hermes config, skills, memory, sessions, cron, plugins, and state;
- project repositories and uncommitted work;
- external providers and canonical SaaS data;
- credential re-issuance;
- gateway/service reconstruction;
- client offboarding and data deletion;
- corrupted or ambiguous state.

Practices:

- use versioned canonical source for scripts and configuration templates;
- separate canonical source, deployed copy, mutable state, and evidence;
- make writes atomic where possible;
- use idempotency keys for external actions;
- never automatically repeat an action whose outcome is ambiguous;
- give deletion authority to a separate, deliberate path;
- periodically restore into an isolated target and exercise the real acceptance checks.

Backups that restore:

- **Verify the staged copy, not the job's exit code.** Copy SQLite state through a consistent method (the engine's backup API), run an integrity check on the staged copy, and never tag an unverified copy as known-good. A tagged snapshot once turned out to be corrupt when it was needed. The reference deployment's nightly job copies the state database inside a one-shot helper container started from the same image as the gateway, never with host SQLite (the host library can be a different version, and opening a live write-ahead log from the host is a corruption risk). The staging file lives outside the data mount, so it is not charged to the gateway's memory cgroup. A failed copy or integrity check is a warning: the file tree still uploads, but no new known-good database tag is created.
- **Make the off-site copy encrypted, incremental and bounded.** The reference uses a client-side-encrypted, deduplicating backup tool to object storage, nightly, with a short daily/weekly/monthly retention. Directories marked as caches are excluded, and separately mounted filesystems (such as persistent browser profiles) are listed as their own backup roots, because a one-filesystem backup does not descend into them. The health sweep fails when the last successful run is older than about 30 hours or the staged database failed its check.
- **Drill the restore.** At least quarterly, restore a known file from the latest snapshot into a scratch directory without touching the live runtime. If that fails, the backup is theatre.
- **Keep scratch out of the data home.** Test fixtures (including deliberately corrupt databases) and experimental stores inside the Hermes home inflate every snapshot, can fail the backup's own checks, and can crash-loop a new image's boot-time disk check. Exclude them, and keep a test proving the exclusions still match.
- **Keep backup credentials host-only** (see section 6).
- **Know how the session store grows.** Context compaction can re-insert carried-forward messages, so a store can hold the same tool output several times over; growth tracks compaction, not age, and age-based pruning frees little. Archive before pruning, verify that archived message IDs resolve, and keep built-in automatic pruning off where it offers no archive step (the reference sets `sessions.auto_prune: false` with a long retention, in every profile). The [live state store maintenance skill](../skills/live-state-store-maintenance/SKILL.md) covers repair: never open a live write-ahead log from the host, never rebuild indexes under live writers, never restart a gateway that is already failing writes. Stop, copy and repair the copy.

`hermes import` overwrites the target home and requires the target gateway to be stopped. A restore is therefore a separately authorized recovery transaction: use an isolated destination for drills, preserve owner access, and never point a test import at the live home.

## 15. Update without losing the runtime truth

First identify who owns the application code. The update route differs:

- **Git/source install:** the Hermes CLI updates the checkout. Where supported, inspect `hermes update --check` (and `--plan` if your version offers it), then follow the backup guidance above and `hermes update --backup` where `--help` confirms it.
- **Image-owned install (the Docker image, including the fork build used here):** `hermes update` refuses image-owned code; the application is updated by replacing the image. Pin an exact digest, record the digest being replaced so it can be restored, back up the mounted data directory, then pull and recreate the container. Never copy fixes into the image's code directory; a durable fix is a new image. The new image may migrate the mounted config and state database on start; that migration is part of the change.
- **Other packaging (Nix, managed services):** follow that owner's documented route.

The reference deployment separates two operations. A **deploy** applies configuration and identity and recreates containers, but freezes the Hermes image to the one already running. Only an explicit **upgrade** moves the image to the reviewed pin. Its upgrade refuses while the secret manager's budget is spent, when the pre-upgrade snapshot failed, or when free disk does not cover the snapshot plus the new image. Before the new image first boots, it stamps the required policy leaves into every home, so that first boot cannot pick up permissive built-in defaults. A healthy container is not the done-bar. The postchecks require: the live config schema matches the image, this boot's log shows no secret-read failure for a messaging token, `hermes config check` and `hermes doctor` pass, and the running digest matches the reviewed pin. Acceptance has two stages: frozen read-only validation, then an explicit go, then unfreezing ingress and jobs. A `doctor` failure caused by a dead external credential after an otherwise healthy upgrade means rotate the credential, not roll back.

**Rollback is not just re-pinning the old image.** A new image can migrate `config.yaml` and the state database forward, and older code may not read the result; post-migration writes are not backward-portable. A real rollback re-deploys the previous release as a whole (the recorded pre-upgrade revision of your deployment repository, so pin and config revert together), not a hand-edited pin. If the schema changed, first restore the pre-upgrade data snapshot, deleting any leftover write-ahead/shared-memory files beside the database first. Keep the previous image locally: `docker image prune` does not see digest pins the way you expect, so keep the live image plus the previous one by explicit cleanup, and never remove the previous release until the new one has run for a full day. A pruned rollback target is a download you may not be able to make during an incident.

After either route, re-check the effective state:

```bash
hermes --version
hermes config check
hermes doctor
hermes security audit --fail-on high
hermes tools --summary
hermes mcp list
hermes gateway status
```

Distinguish upstream base, a fork's default branch, the chosen release source, the built image digest and the build actually observed running. A checked-out branch or a tag name is not proof of what is deployed; bind evidence to source SHA, image digest/provenance and exact-head CI where these exist, and do not invent receipts where they do not.

A digest pin is a review checkpoint, not a vulnerability feed. The reference deployment moves pins only through a bump script, a human review of the diff, and an SBOM committed with the pin; its deploy refuses a pinned image without an SBOM on disk. It rescans the committed SBOMs daily against the current advisory database (advisories can land hours after an image is published). It refuses any new image or CI action that is not on a named allowlist, keeps CI actions pinned to full commit SHAs, and gives every ignore entry a reason and an expiry of at most a month. Scanners run in enforcing rather than report-only mode, and supply-chain alerts go to a channel the agent itself cannot reach or suppress. A failed alert send is not a green run: the watch still exits non-zero.

Then exercise the real paths affected by the update: one authorized gateway interaction, one file mutation in a disposable workspace, one MCP read, one scheduled-job canary, and any critical custom plugin or integration.

A green health endpoint is not a working gateway. Each of these has been observed with health returning OK: a stdio MCP server whose command an update removed; `config.yaml` failing to parse, so the gateway ran on fallback defaults; a secret-manager budget exhausted at boot, so the messaging token was empty; exhausted provider credit or revoked provider auth; and the gateway's supervised service down while the container showed as running. Probe each explicitly; the reference health sweep has a row for every one of them.

Upgrades can also rename or retire config keys. A renamed key may be ignored without a warning (an older `gateway.auto_migrate` leaf is one example), and a migration may rewrite a setting you chose deliberately (`gateway.multiplex_profiles: false` is rewritten to `true` at boot). Read the release notes for removed and renamed keys, guard intentional settings with a post-deploy assertion, and confirm which key the running build actually reads. Retiring a feature or setting is an owner decision, not a side effect of the upgrade.

Upgrade only when the agent is idle; a long-running session can take hours to finish, so wait in a detached job and re-check that the pre-upgrade snapshot is still fresh before proceeding. Run the snapshot and the upgrade as separate steps (a chained `snapshot && upgrade` can hide a refusal), and save the old container's logs before recreating it: they are the only crash or OOM evidence. The [operations guide](operations.en.md) has the full runbook, including host maintenance windows and supply-chain checks.

Hermes updates may follow a moving branch. For exposed or client gateways, record the version/source being replaced, inspect or stage the update, and bind acceptance evidence to the version actually deployed—not merely to “latest.”

Do not infer that a config change is active merely because the file changed. The gateway reads `config.yaml` only at boot, and some controls are read at session startup. When a restart is required after a config change or repair, restart the gateway service in place through the in-container supervisor (run as the runtime user), not by recreating the container; a recreate loses supervisor state that the deploy tooling must rebuild. The exception is a gateway that died on a PID or thread limit: recreate through your deploy script, because an in-place restart does not reclaim leaked processes. Verify the new process and behavior afterward.

## 16. Acceptance tests

A hardened deployment should demonstrate, not merely claim, the following:

### Access

- an unauthorized gateway identity is denied;
- an authorized identity works;
- stale pairings and former staff/client access are gone;
- dashboard/API/CDP listeners are not publicly reachable unless intentionally protected;
- every published port is bound to loopback or the private ingress address, checked from the host.

### Secrets and data

- reports and logs contain no secret values;
- a low-trust profile cannot reach unrelated credential stores or client data;
- a deliberately planted non-secret canary is not exfiltrated when hostile content asks for it;
- backup handling and retention are documented.

### Tools and actions

Write-denial tests are write attempts: if enforcement fails they can mutate data. Run them only when the exact test is authorized on disposable resources, or use a provider-supported non-mutating validation endpoint. Otherwise inspect permission metadata and report denial behavior as unverified. Existing precise authorization need not be requested twice.

- excluded tools and MCP operations are absent;
- read-only credentials reject a write attempt at the provider boundary;
- dangerous commands are denied in cron and one-shot modes;
- changing the target, normalized parameters, or final payload invalidates a high-consequence approval;
- ASSESS/VERIFY creates no unapproved memory or skill persistence;
- `--yolo` is absent from service units and launch aliases;
- external writes are independently read back.

### Network and prompt injection

- private/cloud-metadata URLs are blocked where required, with `security.allow_private_urls`, `browser.allow_private_urls` and `browser.auto_local_for_private_urls` explicitly `false` in every home (a missing leaf counts as a failure);
- untrusted content cannot authorize tool calls or reveal secrets;
- egress restrictions block a destination outside policy;
- MCP/plugin/skill provenance and effective versions are recorded.

### Recovery and operations

- a backup restores into an isolated target;
- an import drill uses an isolated home with its target gateway stopped;
- a failed or interrupted external action produces an honest ambiguous state rather than an automatic duplicate;
- gateway restart recovery is observed;
- scheduled-job failure reaches an owner, proven by a real test message;
- critical state stores pass their supported integrity checks;
- the effective approval and write-gate policy matches the intended values in every profile;
- each enabled MCP server starts after the latest update, not only at initial setup;
- a rollback has a restorable pre-upgrade data snapshot and a locally retained previous image;
- the gateway booted from the parsed config, not from fallback defaults, and this boot loaded every messaging token;
- the latest backup is recent and its staged state database passed its integrity check;
- identity prompt files are under the context-file cap (past it the middle is dropped) and memory stores under their limits (over it, new adds are refused);
- runtime files are owned by the runtime user, and jobs paused on purpose are still paused.

The reference deployment runs the machine-checkable state items (policy per home, bound ports, MCP commands, config load, messaging tokens, backup freshness, caps, ownership, paused jobs) as one monthly health-sweep script that prints `PASS`, `WARN` or `FAIL` per check and exits non-zero on any `FAIL`. An expected, allowlisted failure prints `WARN` and does not change the exit code, so a red exit always means something real. Pasted snippets rot; a script is diffable and testable.

Lifecycle tests (restart, import, update, supervisor behavior) belong on a disposable deployment or external CI that reproduces the real supervisor and container layout. A temporary profile or Git worktree on the live host shares its process supervisor, PID 1, host Docker and live state; it is not an isolated lifecycle canary. Never exercise those tests against the active supervised gateway. A restore path that has not been exercised remains unverified.

## 17. Recommended deployment profiles

### Personal workstation

- normal user, not root;
- no public listeners;
- explicit tool review;
- secret redaction on;
- approvals smart/manual;
- checkpoints for project work;
- protected backup and tested restore.

### Private always-on server

- dedicated service account or hardened container/VM;
- explicit gateway allowlist/pairing;
- loopback/private listeners behind authenticated ingress;
- resource limits and external egress policy;
- supervised gateway and failure alerts, with no host-level restart loop;
- cron deny mode and the install policy asserted on every deploy;
- scheduled backups and restore drills.

### Low-trust ingestion profile

- no personal memory or privileged credentials;
- web/document/email inputs treated as hostile;
- read-only tools only;
- no terminal or external communication unless a narrow workflow requires it;
- private URLs disabled, including the browser's local fallback;
- outputs reviewed before entering canonical state.

### Privileged operator profile

- minimal untrusted input;
- per-system scoped credentials;
- exact tool/MCP allowlists;
- consequential action previews and transaction gates;
- independent read-back;
- strong audit and recovery.

### Company or consultancy deployment

- one client/company boundary per profile and preferably per service identity;
- no personal memory, personal credentials, or cross-client browser sessions;
- documented data classes, retention, subprocessors, and owners;
- joiner/mover/leaver process;
- change records and acceptance evidence;
- provider-native read-only roles where possible;
- incident response, credential rotation, and offboarding tested before handover.

## 18. What not to claim

Do not call a deployment secure merely because:

- `hermes doctor` or the health endpoint is green;
- the model says it cannot access something;
- a profile exists;
- the process runs in Docker;
- secret redaction is enabled;
- the dashboard is not visible from inside the container;
- one happy-path test passed;
- the guide was “applied.”

A defensible conclusion states scope and residual risk:

> The assessed controls reduce accidental misuse and several prompt-injection paths. They do not prove containment against a malicious process with the same OS identity and network access. Host isolation, provider-side scope, and tested recovery remain the authoritative boundaries.

## Sources

### Hermes Agent

- [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)
- [Profiles](https://hermes-agent.nousresearch.com/docs/user-guide/profiles)
- [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/)
- [MCP Config Reference](https://hermes-agent.nousresearch.com/docs/reference/mcp-config-reference)
- [Toolsets Reference](https://hermes-agent.nousresearch.com/docs/reference/toolsets-reference)
- [Scheduled Tasks](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
- [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)
- [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)
- [Checkpoints and Rollback](https://hermes-agent.nousresearch.com/docs/user-guide/checkpoints-and-rollback)
- [CLI Commands](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)
- [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)
- [Browser](https://hermes-agent.nousresearch.com/docs/user-guide/features/browser)
- [Web Dashboard](https://hermes-agent.nousresearch.com/docs/user-guide/features/web-dashboard)
- [API Server](https://hermes-agent.nousresearch.com/docs/user-guide/features/api-server)
- [Webhooks](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/webhooks)

### Security references

- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [NIST — Strengthening AI Agent Hijacking Evaluations](https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations)
- [Simon Willison — The lethal trifecta for AI agents](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta)
