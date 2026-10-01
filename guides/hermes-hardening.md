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

Never let two live Hermes processes write the same profile. If they need shared state, use an external canonical store with explicit concurrency semantics.

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

Connected browser mode can act inside authenticated sessions. Use a dedicated low-privilege browser profile for hostile content, keep logged-in administrative sessions away from low-trust ingestion, and consider `browser.restrict_evaluate` to disable arbitrary page-JavaScript evaluation while preserving structured browser actions. Review `security.website_blocklist`, but do not mistake a domain blocklist for prompt-injection containment or network egress policy.

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

Dashboard, API, browser CDP, metrics, webhook, and noVNC endpoints should normally bind to loopback or a private authenticated network. Never expose browser CDP directly to the internet.

Hermes' dashboard defaults to loopback; non-loopback use requires authentication and still needs host-level TLS/exposure verification. The API server is more consequential: it can expose the agent's effective tool authority, uses bearer authentication, and should keep an exact CORS allowlist rather than `*`. Test unauthenticated rejection and authorized readiness from outside the process.

For webhooks, use a root or per-route secret, HMAC or platform signature verification, timestamp/replay protection, source-IP restrictions where stable, and rate limits. Treat payloads as untrusted data. Never use insecure/no-auth mode on a listener reachable by anything outside a disposable isolated test.

On Linux/systemd, Hermes supports an optional event-loop watchdog for gateway stalls. Use it only with a supervised service and verify restart behavior:

```bash
hermes config set gateway.systemd_watchdog_seconds 120
hermes gateway install --force
```

This regenerates the service unit and may interrupt service; preview and authorize it as an operational change.

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

### Plugins, skills, and context files

- inspect before installing;
- keep provenance and update source;
- run `hermes security audit` after dependency changes;
- do not force-install a skill that fails security scanning without manual review;
- treat repository content as untrusted until the user deliberately trusts or installs it;
- keep `AGENTS.md` concise and project-specific;
- put reusable procedures in `SKILL.md`, not in a giant project prompt;
- review shell hooks explicitly; never use `--accept-hooks` as a casual default;
- enable the agent-write gates in secure or client profiles:

```bash
hermes config set skills.write_approval true
hermes config set memory.write_approval true
```

- distinguish scanner acceptance from trust: pin and review extension provenance before activation.

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

Cron sessions are fresh. Do not write prompts such as “continue that thing”; provide all required context or attach maintained skills. Use `workdir` when project instructions and repository context must load.

ASSESS and VERIFY jobs must not persist findings, hostile source text, or recommendations into long-term memory unless a reviewed, structured persistence step is separately authorized. Otherwise an audit can become a cross-session prompt-poisoning mechanism.

Inspect execution history, not just the current schedule:

```bash
hermes cron list
hermes cron status
hermes cron runs <job-id> --limit 20
```

Never patch `cron/jobs.json` directly. Use `hermes cron`, `/cron`, or the `cronjob` tool.

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

`hermes import` overwrites the target home and requires the target gateway to be stopped. A restore is therefore a separately authorized recovery transaction: use an isolated destination for drills, preserve owner access, and never point a test import at the live home.

## 15. Update without losing the runtime truth

A safe update sequence:

```bash
hermes update --check
hermes backup --quick --label pre-update
hermes update --backup
hermes config check
hermes doctor
hermes security audit --fail-on high
hermes tools --summary
hermes mcp list
hermes gateway status
```

Then exercise the real paths affected by the update: one authorized gateway interaction, one file mutation in a disposable workspace, one MCP read, one scheduled-job canary, and any critical custom plugin or integration.

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
- scheduled-job failure reaches an owner;
- critical state stores pass their supported integrity checks.

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
- private URLs disabled;
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

- `hermes doctor` is green;
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
