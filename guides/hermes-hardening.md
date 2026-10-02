# Hardening Hermes Agent

*A practical baseline for personal, friend, and client deployments*

Hermes can read files, browse hostile content, execute code, use credentials, control external systems, and run while nobody is watching. The goal of hardening is not to make the model timid. It is to make useful authority **explicit, bounded, recoverable, and verifiable**.

This guide combines current Hermes controls with practices learned from operating a long-running tool-using assistant. It is an independent publication, not official Nous Research documentation. Hermes changes quickly: verify version-sensitive commands against the [current Hermes documentation](https://hermes-agent.nousresearch.com/docs/) before applying them.

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

Check the target version's backup contents and retention first. Use `--quick` only when its documented critical-state coverage includes every proposed target; it is not a generic backup of skills, plugins, project files or external state. Otherwise use a full backup and separately protect project and external state. Full-backup retention may delete older archives; choose a protected output location and retention policy before running it.

When that coverage is sufficient, create a protected critical-state snapshot before mutation:

```bash
hermes backup --quick --label pre-hardening
```

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

Hermes' official security guide recommends a container backend for production gateways. A container with sensitive read-write mounts, ambient credentials, broad egress, or the Docker socket remains highly privileged.

Container nuances observed in practice:

- **"Not root" means the gateway process, not the container start user.** The official image starts as root so its entrypoint can remap the runtime UID/GID to match the host data owner and then drop privileges (documented as `gosu` to an unprivileged user). `no-new-privileges` on the *gateway* container can break that setuid step; prefer `cap_drop: [ALL]` with only the capabilities the entrypoint needs and a targeted seccomp profile. Verify the effective UID of the gateway process from the host. Run interactive CLI calls as the runtime user (`docker exec -u <runtime-user>`), never as root, or root-owned files can be silently ignored by the gateway.
- **A read-only Docker socket mount protects nothing.** `:ro` covers the socket file, not the API behind it; anything that can reach the socket is close to host root. Log viewers and dashboards that need it should have actions disabled, bind to loopback, sit behind authentication, or use a read-only socket proxy.
- **Size process and file limits for what the agent actually spawns.** Browsers and stdio MCP servers consume PIDs, file descriptors and shared memory quickly. Run Chromium/Playwright-type workloads in their own container, not inside the gateway's cgroup: a PID-cap hit there kills the gateway. After `can't start new thread` or a PID-cap death, recreate the container; restarting the service inside it does not reclaim leaked processes.
- **Agents can exhaust container memory with ordinary file tools.** Reading every file whole across the data directory (which may contain a multi-gigabyte state database) can trigger the OOM killer. Prefer streaming reads, size checks before reads and per-command memory limits; encode this in the skill that performs scans.

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

- **A named profile does not inherit the default profile's values.** Leaves missing from a sparse profile `config.yaml` fall back to upstream defaults, which may be more permissive than the policy you set on the default home. Stamp the required policy keys into every profile and assert them per profile, not only for the default.
- **Know whether your gateway is multiplexed.** Hermes can run one gateway process per profile or a single multiplexing gateway that serves every profile (`gateway.multiplex_profiles`). Official documentation describes multiplexing as opt-in; some recent builds have been observed migrating to it on upgrade. A multiplexed gateway is one crash domain and one cron scheduler for all profiles: a resource-limit hit or bad config takes every profile down. Check the effective mode after each upgrade and decide it deliberately.

Set a deterministic starting directory:

```bash
hermes -p research config set terminal.cwd /absolute/path/to/research-workspace
```

For stronger separation of external CLI state:

```bash
hermes -p research config set terminal.home_mode profile
```

`terminal.home_mode: profile` gives subprocesses a profile-specific `HOME`; initialize only the CLI credentials that profile actually needs. Without it, profiles normally share the OS user's Git, SSH, GitHub, cloud-CLI, and similar state.

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

For shared or company gateways, consider gateway PII redaction after testing that it does not remove context the workflow genuinely needs:

```bash
hermes config set privacy.redact_pii true
```

Redaction reduces accidental disclosure in context and logs. It does not stop a compromised process from reading a secret and sending it through an allowed network channel.

Where possible, inject credentials only into the process that needs them. Prefer external secret managers or service-specific identities over a large ambient `.env`. Protect any local secret file with restrictive ownership and permissions.

### Pitfalls observed in practice

- **Removing a variable from subprocess environment is not a boundary.** Agent shells usually run as the same OS user as the gateway; they can read the Hermes `.env`, or start their own `hermes` CLI process that resolves every secret reference itself. Probe what an agent shell can actually obtain rather than trusting documentation that says it cannot. The enforceable boundary is the credential's provider-side scope.
- **Custom `config set` keys are not secret storage.** Only recognized credential keys are routed to `.env`; an arbitrary key holding a token lands in plaintext in `config.yaml`, which may be mirrored to Git or included in backups. Pass secrets a subprocess needs through the environment (for example a container env passthrough) and secret-scan every automated commit or push, including bot commits that skip CI.
- **External secret managers have budgets.** If secrets are resolved from a manager with a per-read rate limit, cost multiplies by profile × process start × refresh interval, and diagnostics such as `hermes doctor` or `config check` also resolve references. A spent budget can make a throttled refresh return "success" with empty values and overwrite working secrets: long-running chat (loaded at boot) keeps working while cron delivery and MCP servers fail. Use a long cache TTL, grouped reads, one shared backoff marker, a per-reference last-good fallback that is never used after an authentication failure and never resurrects a rotated or removed reference, cache-only mode for agent shells, and a budget check in health monitoring. Refuse a planned restart while the budget is spent.
- **Keep backup credentials away from the agent.** Store the backup repository password and keys in a host-only file that is not mounted into the agent's container, so a compromised or confused agent cannot delete or prune backups. Add deny rules for backup-destruction commands as a second layer.

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

On versions supporting `approvals.unattended_mode`, include webhook/API programmatic sessions in the fail-closed check. Verify support on the target before applying; unsupported versions need an explicit external execution boundary, not an invented config key.

These settings do not prove fail-closed behavior on every terminal backend. Current official documentation states that dangerous-command checks are skipped on container and sandbox terminal backends such as `docker`, `singularity`, `modal`, `daytona` and `vercel_sandbox`, because that backend is treated as the boundary. Keep two questions separate: where the Hermes process itself runs (for example an outer Docker container) and which `terminal.backend` executes agent commands. For each profile, read the effective terminal backend and use `hermes approvals test` where supported to obtain a verdict without execution; then assess the actual isolation of the sandbox backend (mounts, credentials, egress) rather than counting the deny settings as enforcement. Never run a dangerous command to prove that it is denied.

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

To reset them:

```bash
hermes config set command_allowlist '[]'
```

Audit each permanent entry for what it pre-approves, not what it was added for. An entry admitted for one routine job can pre-approve inline interpreter execution (`-c`/`-e` script bodies) for every session. Removing it may break unattended jobs that cannot answer prompts; that trade-off is an owner decision, recorded with its reason, not a silent default.

Read back the **type** of any list-valued key you set from the command line. In practice a JSON list passed to `config set` has been stored as a YAML string: a deny list became a pattern matching everything, and a mention-pattern list silenced a group channel. Prefer `hermes config edit` or a YAML list in the file for structured values, then verify with `hermes config get`.

**Policy is asserted, not locked.** If `config.yaml` is mirrored to Git or the agent can run `hermes config set`, an export or self-edit can flip approval leaves unnoticed; in practice a runtime export once turned `skills.write_approval` off. "Only the owner changes config" is policy, not a filesystem fact when owner and agent share a UID. Read the effective values with `hermes config get` after every deploy and fail the deploy on mismatch. Some forks bake a managed config seed; check whether it is a lock or only a default on your build rather than assuming either.

Use `approvals.deny` for deterministic “never through this agent” commands. Quote YAML glob patterns. Deny rules protect against an honest-but-wrong agent; they do not contain an adversarial process with equivalent OS access.

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

This setting alone does not close the browser path. When a cloud browser provider is configured, `browser.auto_local_for_private_urls` (on by default in current documentation) routes private URLs to a local browser instead of rejecting them. For profiles that must not reach the private network, also set:

```bash
hermes config set browser.auto_local_for_private_urls false
```

Then probe the deny path from the effective runtime.

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

Hermes defaults to fail-open if Tirith is unavailable. High-security Linux/macOS deployments may choose fail-closed **only after verifying the binary and a safe test path**, otherwise routine commands can be locked out:

```bash
tirith --version
hermes config set security.tirith_fail_open false
```

Tirith is not available as a prebuilt native Windows binary; use WSL if this layer is required.

For controlled environments, disable runtime dependency installation after required features have been provisioned and tested:

```bash
hermes config set security.allow_lazy_installs false
```

Connected browser mode can act inside authenticated sessions. Use a dedicated low-privilege browser profile for hostile content, keep logged-in administrative sessions away from low-trust ingestion, and consider `browser.restrict_evaluate`. That option is a name-based denylist of sensitive JavaScript primitives (cookies, storage, clipboard, network calls, form values) for page evaluation; it does not disable arbitrary JavaScript and is not a sandbox. First establish which browser driver and backend actually apply: in current documentation the default Browser Use mode exposes `browser_exec`, which runs model-written Python and is offered only to sessions that also have terminal access, so terminal and browser authority must be assessed together. Review `security.website_blocklist`, but do not mistake a domain blocklist for prompt-injection containment or network egress policy.

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

On Linux, ports published by Docker are inserted ahead of host firewall rules such as `ufw`: a published port can be reachable even though the firewall appears to deny it. Bind published ports to `127.0.0.1` and reach them through an authenticated private ingress (a tailnet proxy, VPN, or authenticated reverse proxy), or enforce restrictions at the service itself.

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

A host-level loop that runs `docker restart` on failed health checks usually violates all three.

Keep the durable delivery ledger enabled unless a specific privacy or storage analysis rejects it:

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

For command-based (stdio) servers, verify after every image or dependency update that each enabled server's `command` still resolves, using the gateway's own environment and `PATH` rather than your shell's. An update that drops or moves a binary leaves the server failing on every boot while the gateway's health endpoint stays green.

### Plugins, skills, and context files

- inspect before installing;
- keep provenance and update source;
- run `hermes security audit` after dependency changes;
- do not force-install a skill that fails security scanning without manual review;
- treat repository content as untrusted until the user deliberately trusts or installs it;
- keep `AGENTS.md` concise and project-specific;
- put reusable procedures in `SKILL.md`, not in a giant project prompt;
- review shell hooks explicitly; never use `--accept-hooks` as a casual default;
- shield the agent's working directory: project context files load first-match-wins from the working directory (`.hermes.md`, then `AGENTS.md`, `CLAUDE.md`, Cursor rules). If the agent works inside a repository whose `AGENTS.md` or editor rules were written for another tool, those become its instructions. A **non-empty** `.hermes.md` at that root takes precedence; an empty one falls through. See [Identity, Memory and Context](identity-memory-context.en.md);
- decide the agent-write gates per profile:

```bash
hermes config set skills.write_approval true
hermes config set memory.write_approval false   # see below
```

- distinguish scanner acceptance from trust: pin and review extension provenance before activation.

With `write_approval: true`, writes outside the interactive CLI are staged for an operator to approve. That is a sound default for skills, which are executable procedure. For memory it is a trade-off: in any profile that runs cron or other unattended work, nobody is present to approve, so staged writes accumulate and the job silently loses what it meant to remember. Practice has been `memory.write_approval: false` plus, for jobs that must not write memory at all, omitting the `memory` toolset from that job. Set `memory.write_approval: true` only where every writer is interactive, or where someone reviews `/memory pending` on a schedule.

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

The stored toolset list is not necessarily the effective surface. Recent builds have been observed adding every globally enabled MCP server to a cron job unless the job's toolsets include the literal sentinel `no_mcp`; confirm on your version. Resolve the effective surface through the scheduler's own rule and test one allowed and one denied cross-lane action; a check that merely forbids the string `mcp` in the list is not enough.

A dangerous command in a deny-mode cron job produces a pending approval that no one can answer. Treat it as a policy blocker to report, not a request to wait on; split compound commands so the safe part can proceed.

Scheduling details that surprised practice (verify on your version):

- interval schedules such as `every 1m` may be measured from the end of the previous run, so they drift; use a wall-clock cron expression when timing matters;
- missed runs can be caught up after downtime (`catch_up_missed`), producing a burst of executions on restart;
- unpinned jobs follow changes to the default model; pin the job model when cost or behavior matters;
- completed one-shot jobs may be swept automatically after a retention period;
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

Change jobs through `hermes cron`, `/cron`, or the `cronjob` tool; do not hand-edit `cron/jobs.json` as a normal configuration path. One narrow exception has been needed in practice: where the CLI cannot set a job's `enabled_toolsets`, edit only that field, atomically (write a temporary file, then rename it into place), with the scheduler's file lock respected where one exists, then read the job back through `hermes cron list`. Re-check this on each version; prefer the CLI as soon as it supports the field.

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

- **Verify the staged copy, not the job's exit code.** Copy SQLite state through a consistent method (the engine's backup API or the image's own `sqlite3`), run an integrity check on the staged copy, and never tag an unverified copy as known-good. In practice a tagged snapshot turned out to be corrupt when it was needed.
- **Keep scratch out of the data home.** Test fixtures (including deliberately corrupt databases) and experimental stores inside the Hermes home inflate every snapshot, can fail the backup's own checks, and can crash-loop a new image's boot-time disk check. Exclude them, and keep a test proving the exclusions still match.
- **Keep backup credentials host-only** (see section 6).
- **Know how the session store grows.** Context compaction can re-insert carried-forward messages, so a store can hold the same tool output several times over; growth tracks compaction, not age, and age-based pruning frees little. Archive before pruning, verify that archived message IDs resolve, and keep built-in automatic pruning off where it offers no archive step. The [live state store maintenance skill](../skills/live-state-store-maintenance/SKILL.md) covers repair: never open a live write-ahead log from the host, never rebuild indexes under live writers, never restart a gateway that is already failing writes. Stop, copy and repair the copy.

`hermes import` overwrites the target home and requires the target gateway to be stopped. A restore is therefore a separately authorized recovery transaction: use an isolated destination for drills, preserve owner access, and never point a test import at the live home.

## 15. Update without losing the runtime truth

First identify who owns the application code. The update route differs:

- **Git/source install:** the Hermes CLI updates the checkout. Where supported, inspect `hermes update --check` (and `--plan` if your version offers it), then follow the backup guidance above and `hermes update --backup` where `--help` confirms it.
- **Image-owned install (for example the official Docker image):** current documentation states that `hermes update` refuses image-owned code changes; the application is updated by replacing the image. Pin an exact version or digest, record the digest being replaced so it can be restored, back up the mounted data directory, then pull and recreate the container. The new image may migrate the mounted config on start; that migration is part of the change.

**Rollback is not just re-pinning the old image.** A new image can migrate `config.yaml` and the state database forward, and older code may not read the result. A real rollback restores the pre-upgrade data snapshot (removing any leftover write-ahead/shared-memory files beside the database first) and then re-pins the previous digest. Keep the previous image locally: image prune modes treat digest-pinned images differently, and a pruned rollback target is a download you may not be able to make during an incident.
- **Other packaging (Nix, managed services):** follow that owner's documented route.

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

A digest pin is a review checkpoint, not a vulnerability feed. Record an SBOM with each pin, rescan committed SBOMs against the current advisory database on a schedule (advisories can land hours after an image is published), give every ignore entry an expiry, run scanners in enforcing rather than report-only mode, and send supply-chain alerts to a channel the agent itself cannot reach or suppress.

Then exercise the real paths affected by the update: one authorized gateway interaction, one file mutation in a disposable workspace, one MCP read, one scheduled-job canary, and any critical custom plugin or integration.

A green health endpoint is not a working gateway. Each of these has been observed with health returning OK: a stdio MCP server whose command an update removed; `config.yaml` failing to parse, so the gateway ran on fallback defaults; a secret-manager budget exhausted at boot, so the messaging token was empty; exhausted provider credit or revoked provider auth; and the gateway's supervised service down while the container showed as running. Probe each explicitly.

Upgrades can also rename or retire config keys. A renamed key may be ignored without a warning, and a migration may rewrite a setting you chose deliberately (gateway topology is one example). Read the release notes for removed and renamed keys, guard intentional settings with a post-deploy assertion, and confirm which key the running build actually reads. Retiring a feature or setting is an owner decision, not a side effect of the upgrade.

Upgrade only when the agent is idle; a long-running session can take hours to finish, so wait in a detached job and re-check that the pre-upgrade snapshot is still fresh before proceeding. Run the snapshot and the upgrade as separate steps (a chained `snapshot && upgrade` can hide a refusal), and save the old container's logs before recreating it: they are the only crash or OOM evidence. The [operations guide](operations.en.md) has the full runbook, including host maintenance windows and supply-chain checks.

Hermes updates may follow a moving branch. For exposed or client gateways, record the version/source being replaced, inspect or stage the update, and bind acceptance evidence to the version actually deployed—not merely to “latest.”

Do not infer that a config change is active merely because the file changed. Some controls are read at process or session startup. Restart only when required, and verify the new process and behavior afterward.

## 16. Acceptance tests

A hardened deployment should demonstrate, not merely claim, the following:

### Access

- an unauthorized gateway identity is denied;
- an authorized identity works;
- stale pairings and former staff/client access are gone;
- dashboard/API/CDP listeners are not publicly reachable unless intentionally protected.

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

- private/cloud-metadata URLs are blocked where required;
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
- a rollback has a restorable pre-upgrade data snapshot and a locally retained previous image.

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
- supervised gateway and failure alerts;
- cron deny mode;
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
