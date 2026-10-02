# Hermes hardening control checklist

Use this checklist as an assessment surface, not as a script. For every control record one status:

- `pass` — current evidence demonstrates the control;
- `partial` — present but incomplete or unverified;
- `fail` — applicable and absent or ineffective;
- `not_applicable` — justified by the deployment model;
- `needs_decision` — owner choice required;
- `unsupported` — the current Hermes/platform version cannot provide it.

Never record secret values. Evidence should identify the command, source, timestamp, and decision-relevant result.

## A. Target and recovery

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-001 | Exact Hermes profile/home, version, install method, host/runtime, and owner are identified. | `hermes --version`, targeted/filtered status, `hermes config path`; runtime observation. |
| HRD-002 | Deployment purpose, users, inputs, data classes, write-capable systems, unattended jobs, and exposure are documented. | Owner-confirmed deployment statement. |
| HRD-003 | A protected pre-change backup exists. | Backup receipt/path without secret contents. |
| HRD-004 | Restore was exercised on an isolated target without touching the live gateway/home. | Restore log plus functional acceptance result; gateway/import preconditions verified. |
| HRD-005 | Rollback and owner access survive proposed changes. | Tested recovery route; no reliance on the agent being repaired. |
| HRD-006 | Assessment runtime writes are separated from the target and explicitly accounted for. | Evidence-workspace path; pre/post target snapshot; session/log/cache/checkpoint/output-capture locations. |

## B. Identity and isolation

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-010 | Gateway/service does not run as root. | Effective UID of the gateway process from host/runtime (an image entrypoint may start as root to remap UID, then drop); CLI access goes through a wrapper that runs as the runtime user, because a plain `docker exec` lands as root; no root-owned files in the data home. |
| HRD-011 | Privileged and low-trust workloads use separate profiles and, where needed, separate OS/container identities. | Profile inventory and runtime mapping. |
| HRD-012 | No two live agent processes write the same Hermes home. | Process/service inventory. |
| HRD-013 | `terminal.cwd` is explicit for bounded profiles. | Resolved config plus real tool cwd. |
| HRD-014 | External CLI credentials are separated where needed (`terminal.home_mode: profile` or stronger isolation). | Resolved config and credential-surface inventory by name only. |
| HRD-015 | Filesystem and process isolation match the threat model. | Mounts, permissions, `cap_drop: [ALL]` plus only the capabilities the UID remap needs, targeted seccomp (never `unconfined` or `privileged`; `no-new-privileges` breaks the image's setuid remap), write-safe root set explicitly in the container environment, PID/file/shm/memory limits sized for browsers and MCP servers, browsers outside the gateway cgroup, Docker socket not reachable (`:ro` does not count), no writable `PATH` directory shadowing image binaries. |
| HRD-016 | Profile policy is stamped per profile and gateway topology is deliberate. | Effective policy per named profile (sparse profiles inherit `true` built-in defaults for `cron.catch_up_missed`, `gateway.auto_multiplex_migration` and `browser.auto_local_for_private_urls`); multiplexed gateway accepted as one crash domain, or `gateway.standalone: true` where a profile needs its own; no sidecar starting a second gateway on the same data. |

## C. Secrets and data

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-020 | Secret redaction is enabled. | `hermes config get security.redact_secrets`. |
| HRD-021 | Credentials are per-purpose, scoped, revocable, and not stored in public/config prose. | Provider-side scope metadata; repository/history scan. |
| HRD-022 | The agent-accessible secret store excludes unrelated personal/client/admin secrets. | Secret inventory names/counts only. |
| HRD-023 | PII redaction/retention are decided for shared gateways. | Config and documented decision. |
| HRD-024 | Offboarding removes credentials, pairing, service identities, and retained data. | Tested checklist or completed offboarding evidence. |
| HRD-025 | Assessment does not persist hostile or unreviewed content into long-term memory. | `memory.write_approval` decision (with its unattended-job consequence) or `memory` toolset omitted, plus before/after evidence. |
| HRD-026 | Agent shells cannot obtain secrets beyond their purpose; no secret sits in a custom config key. | Probe from an agent shell (names only), remembering that local-backend children inherit the gateway's environment minus a built-in blocklist; `config.yaml` scan for literal credential shapes before any mirror/publish; webhook secrets as `${ENV}` interpolations; `.env` files mode `600`; provider-side scope. |
| HRD-027 | External secret-manager budget, caching and failure fallback are designed; backup credentials are not mounted into the agent. | Cache TTL of hours in every home, grouped reads with one shared backoff marker, last-good values kept on a throttled re-pull, cache-only mode for agent shells where the build supports it, budget health row, restarts/upgrades refused while the budget is spent; mount inventory. |

## D. Tools, approvals, and write boundaries

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-030 | Effective tools are minimized per profile and platform. | `hermes tools --summary`; effective tool list. |
| HRD-031 | Interactive approval mode is `smart` or `manual`. | `hermes config get approvals.mode`. |
| HRD-032 | Cron, one-shot and supported unattended API/webhook sessions fail closed. | `approvals.cron_mode=deny`; `approvals.single_query_mode` and `approvals.unattended_mode` read back as `deny` (their default); effective `terminal.backend` per profile (container/sandbox backends skip dangerous-command checks); non-mutating `hermes approvals test` verdicts. Never execute a dangerous command to test denial. |
| HRD-033 | YOLO is absent from services, aliases, and privileged automation. | Service unit/launcher inspection. |
| HRD-034 | Permanent command allowlist is reviewed and narrow. | `command_allowlist` inspection; entries are approval classes, so record what each pre-approves in every session (the class `script execution via -e/-c flag` covers every interpreter one-liner); owner decision recorded for any class kept; approval-history review. |
| HRD-039 | Effective approval and write-gate policy is asserted after every deploy; list-valued keys have list type. | `hermes config get` per profile for `skills.write_approval=true`, `memory.write_approval=false`, `approvals.cron_mode=deny`, compared to intended values with the deploy failing on mismatch (an unreadable value is a retryable state, not a pass); whether any managed config seed is a lock or only a default on this build; type read-back. |
| HRD-035 | Deterministic deny rules exist for prohibited actions when useful. | Config plus `hermes approvals test`; note that this is not a sandbox. |
| HRD-036 | File-write safe roots and OS permissions match the workspace boundary. | Effective environment, deny tests, and terminal boundary analysis. |
| HRD-037 | Consequential external actions require bounded authority and independent read-back. | Operating policy plus canary transaction test. |
| HRD-038 | High-consequence approvals bind the exact target and final normalized payload, and reject drift/replay. | Approval receipt or broker test; changed-parameter and replay canaries. |

## E. Network and gateway

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-040 | Private URL access is disabled unless explicitly required. | `security.allow_private_urls`, `browser.allow_private_urls` and `browser.auto_local_for_private_urls` explicitly `false` in every home (a missing leaf inherits `true` for the local fallback) plus deny/allow probes. |
| HRD-041 | Cloud metadata and disallowed egress are blocked outside the model. | Proxy/firewall policy and runtime probe. |
| HRD-042 | Tirith is enabled; fail-open/fail-closed choice is tested and documented. | Config, binary/platform availability, safe test. |
| HRD-043 | Gateway access uses explicit allowlists or approved pairing; allow-all is off. | Config names and `hermes pairing list`, no secret tokens. |
| HRD-044 | Admin roles are narrower than ordinary chat access. | Effective authorization test. |
| HRD-045 | Dashboard, API, CDP, webhook, metrics, and noVNC exposure is verified from the host and an authorized external vantage point. | Bind/publish/firewall/proxy/TLS/auth/external scan evidence; Docker-published ports bound to loopback (Docker bypasses host firewalls such as ufw); residual access from other containers on the same compose network to a non-loopback in-container API bind recorded; self-hosted CI runners on the host limited to private repositories without fork-PR triggers. |
| HRD-046 | Gateway supervision, delivery ledger, and failure notifications are tested. | Service status, restart canary, delivery ledger on (the default), delivery recovery evidence; container stop grace longer than the supervisor's own grace times and the forced-drain timeout; any restarter stops gracefully, honors a deliberate stop and alerts rather than healing silently (no host loop running `docker restart`). |
| HRD-047 | Dashboard, API, and webhook authentication, CORS/signature, replay, source, and rate-limit controls match exposure. | Unauthenticated rejection, exact-origin/signature tests, replay/rate-limit canaries. |

## F. MCP, plugins, skills, and supply chain

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-050 | Every MCP/plugin/skill has an owner, source, version/update policy, and purpose. | Extension inventory. |
| HRD-051 | MCP tools use explicit includes; resources/prompts are disabled unless needed. | Resolved MCP config and effective tool list. |
| HRD-052 | Uncontrolled MCP servers are marked untrusted; real write restrictions exist at the credential/provider layer. | Permission metadata; denied write canary only on explicitly authorized disposable resources or non-mutating validation endpoints. Otherwise denial behavior is unverified. |
| HRD-053 | TLS verification is enabled for remote MCPs. | Resolved config and connection test. |
| HRD-054 | Shell hooks are explicitly reviewed and authorized. | Hook inventory and consent state. |
| HRD-055 | Supply-chain audit runs after install/update/extension changes. | `hermes security audit` result and disposition. |
| HRD-056 | Runtime dependency installation policy is explicit. | `security.allow_lazy_installs` plus provisioned dependency test. |
| HRD-057 | Connected-browser authority is separated from hostile ingestion; arbitrary evaluation and website policy are decided. | Effective browser driver/backend (including `browser_exec`, which runs model-written Python and requires terminal access), no browser process or loopback CDP inside the gateway container, browser containers without a route to the gateway API and with policed egress, Chrome sandbox kept on, browser-profile inventory, `browser.restrict_evaluate` (a primitive-name denylist, not a sandbox), website policy, authenticated-session test. |
| HRD-058 | Agent-created persistent skill writes require an explicit owner policy/gate. | `skills.write_approval` decision and denied-write canary. |
| HRD-059 | Command-based MCP servers resolve after every update; image pins carry an SBOM, scheduled rescans and expiring ignores. | Command resolution with the gateway's own PATH; SBOM per pin; rescan and alert evidence. |

## G. Automation and state

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-060 | Every autonomous job has a self-contained prompt or attached maintained skill. | Job read-back. |
| HRD-061 | Every agent job has explicit minimal toolsets and delivery target. | Job read-back and effective run context, including every globally enabled MCP server the scheduler adds unless the job's toolsets include the literal `no_mcp`. |
| HRD-062 | Model/provider policy, cost boundary, timeout, retries, and ambiguous outcomes are defined. | Job config and failure-path test. |
| HRD-063 | Stateful jobs use atomic state, overlap control, idempotency, and bounded retention. | State design plus repeated/interrupted canary. |
| HRD-064 | Jobs are managed through supported Hermes commands/tools, not direct store edits. | Canonical owner and mutation path; `enabled_toolsets` (which `hermes cron edit` cannot set) edited atomically, alone, as the runtime user, with read-back; script jobs reference a basename under `$HERMES_HOME/scripts/` with one canonical source copy. |
| HRD-065 | Execution history is monitored and failures reach an owner. | Recent `hermes cron runs`; end-to-end alert test to the real destination; circuit breaker on background loops; `cron.catch_up_missed` decided per home; jobs paused on purpose still paused. |
| HRD-066 | State-store backups are verified copies and scratch stays out of the data home. | Database copied with the image's own engine, not host SQLite; integrity check of the staged copy, with no known-good tag on failure; encrypted off-site copy with bounded retention and freshness alert; separately mounted roots listed; exclusion list plus test; archive-before-prune for session history. |

## H. Verification and maintenance

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-070 | Config and install diagnostics pass or findings are dispositioned. | Locally filtered `hermes config check` / `hermes doctor` evidence; no raw identifiers or credential fingerprints retained. |
| HRD-071 | Unauthorized-user, prompt-injection, secret-canary, private-URL, excluded-tool, and write-denial tests pass. | Dated canary report. |
| HRD-072 | Real critical paths are exercised after update/restart. | Gateway, file, MCP, cron, and custom integration canaries; health-endpoint green is not accepted as evidence. |
| HRD-075 | Rollback is restorable. | Pre-upgrade data snapshot (config and state database) plus locally retained previous image; previous release re-deployable as a whole (pin and config together); policy leaves stamped into every home before a new image's first boot; renamed/retired keys reviewed. |
| HRD-076 | Machine-checkable state is swept by one script, not pasted snippets. | `PASS`/`WARN`/`FAIL` rows with non-zero exit on `FAIL`; expected failures allowlisted as `WARN`; rows for policy per home, bound ports, MCP commands, config load, messaging tokens, secret budget, backup freshness, prompt-file and memory caps, ownership and paused jobs. |
| HRD-073 | Canonical source, deployed runtime, mutable state, and evidence are distinct and reconciled. | Source/deploy map and drift check. |
| HRD-074 | Residual risk is stated without claiming model-level controls are containment. | Final assurance statement. |

## Stop conditions

Stop and return control to the owner when:

- the target profile or host is ambiguous;
- the only owner access path may be removed;
- backup or rollback cannot be demonstrated;
- a command would reveal secret values;
- a service restart, credential rotation/revocation, restore/import, firewall change, or destructive mutation is not explicitly authorized;
- an external action has an ambiguous outcome;
- the target's CLI or resolved config contradicts the proposed command;
- recovery ceases to be credible.
