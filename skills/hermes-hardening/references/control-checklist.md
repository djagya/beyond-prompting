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
| HRD-010 | Gateway/service does not run as root. | Effective UID from host/runtime. |
| HRD-011 | Privileged and low-trust workloads use separate profiles and, where needed, separate OS/container identities. | Profile inventory and runtime mapping. |
| HRD-012 | No two live agent processes write the same Hermes home. | Process/service inventory. |
| HRD-013 | `terminal.cwd` is explicit for bounded profiles. | Resolved config plus real tool cwd. |
| HRD-014 | External CLI credentials are separated where needed (`terminal.home_mode: profile` or stronger isolation). | Resolved config and credential-surface inventory by name only. |
| HRD-015 | Filesystem and process isolation match the threat model. | Mounts, permissions, capabilities, seccomp/no-new-privileges, resource limits. |

## C. Secrets and data

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-020 | Secret redaction is enabled. | `hermes config get security.redact_secrets`. |
| HRD-021 | Credentials are per-purpose, scoped, revocable, and not stored in public/config prose. | Provider-side scope metadata; repository/history scan. |
| HRD-022 | The agent-accessible secret store excludes unrelated personal/client/admin secrets. | Secret inventory names/counts only. |
| HRD-023 | PII redaction/retention are decided for shared gateways. | Config and documented decision. |
| HRD-024 | Offboarding removes credentials, pairing, service identities, and retained data. | Tested checklist or completed offboarding evidence. |
| HRD-025 | Assessment does not persist hostile or unreviewed content into long-term memory. | `memory.write_approval` decision plus before/after evidence. |

## D. Tools, approvals, and write boundaries

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-030 | Effective tools are minimized per profile and platform. | `hermes tools --summary`; effective tool list. |
| HRD-031 | Interactive approval mode is `smart` or `manual`. | `hermes config get approvals.mode`. |
| HRD-032 | Cron and one-shot dangerous commands fail closed. | `approvals.cron_mode=deny`, `approvals.single_query_mode=deny`; dry-run verdict. |
| HRD-033 | YOLO is absent from services, aliases, and privileged automation. | Service unit/launcher inspection. |
| HRD-034 | Permanent command allowlist is reviewed and narrow. | `command_allowlist` inspection; approval-history review. |
| HRD-035 | Deterministic deny rules exist for prohibited actions when useful. | Config plus `hermes approvals test`; note that this is not a sandbox. |
| HRD-036 | File-write safe roots and OS permissions match the workspace boundary. | Effective environment, deny tests, and terminal boundary analysis. |
| HRD-037 | Consequential external actions require bounded authority and independent read-back. | Operating policy plus canary transaction test. |
| HRD-038 | High-consequence approvals bind the exact target and final normalized payload, and reject drift/replay. | Approval receipt or broker test; changed-parameter and replay canaries. |

## E. Network and gateway

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-040 | Private URL access is disabled unless explicitly required. | `security.allow_private_urls` plus deny/allow probes. |
| HRD-041 | Cloud metadata and disallowed egress are blocked outside the model. | Proxy/firewall policy and runtime probe. |
| HRD-042 | Tirith is enabled; fail-open/fail-closed choice is tested and documented. | Config, binary/platform availability, safe test. |
| HRD-043 | Gateway access uses explicit allowlists or approved pairing; allow-all is off. | Config names and `hermes pairing list`, no secret tokens. |
| HRD-044 | Admin roles are narrower than ordinary chat access. | Effective authorization test. |
| HRD-045 | Dashboard, API, CDP, webhook, metrics, and noVNC exposure is verified from the host and an authorized external vantage point. | Bind/publish/firewall/proxy/TLS/auth/external scan evidence. |
| HRD-046 | Gateway supervision, delivery ledger, and failure notifications are tested. | Service status, restart canary, delivery recovery evidence. |
| HRD-047 | Dashboard, API, and webhook authentication, CORS/signature, replay, source, and rate-limit controls match exposure. | Unauthenticated rejection, exact-origin/signature tests, replay/rate-limit canaries. |

## F. MCP, plugins, skills, and supply chain

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-050 | Every MCP/plugin/skill has an owner, source, version/update policy, and purpose. | Extension inventory. |
| HRD-051 | MCP tools use explicit includes; resources/prompts are disabled unless needed. | Resolved MCP config and effective tool list. |
| HRD-052 | Uncontrolled MCP servers are marked untrusted; real write restrictions exist at the credential/provider layer. | Config plus denied provider-side write canary. |
| HRD-053 | TLS verification is enabled for remote MCPs. | Resolved config and connection test. |
| HRD-054 | Shell hooks are explicitly reviewed and authorized. | Hook inventory and consent state. |
| HRD-055 | Supply-chain audit runs after install/update/extension changes. | `hermes security audit` result and disposition. |
| HRD-056 | Runtime dependency installation policy is explicit. | `security.allow_lazy_installs` plus provisioned dependency test. |
| HRD-057 | Connected-browser authority is separated from hostile ingestion; arbitrary evaluation and website policy are decided. | Browser-profile inventory, `browser.restrict_evaluate`, website policy, authenticated-session test. |
| HRD-058 | Agent-created persistent skill writes require an explicit owner policy/gate. | `skills.write_approval` decision and denied-write canary. |

## G. Automation and state

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-060 | Every autonomous job has a self-contained prompt or attached maintained skill. | Job read-back. |
| HRD-061 | Every agent job has explicit minimal toolsets and delivery target. | Job read-back/effective run context. |
| HRD-062 | Model/provider policy, cost boundary, timeout, retries, and ambiguous outcomes are defined. | Job config and failure-path test. |
| HRD-063 | Stateful jobs use atomic state, overlap control, idempotency, and bounded retention. | State design plus repeated/interrupted canary. |
| HRD-064 | Jobs are managed through supported Hermes commands/tools, not direct store edits. | Canonical owner and mutation path. |
| HRD-065 | Execution history is monitored and failures reach an owner. | Recent `hermes cron runs`, alert canary. |

## H. Verification and maintenance

| ID | Control | Minimum evidence |
| --- | --- | --- |
| HRD-070 | Config and install diagnostics pass or findings are dispositioned. | Locally filtered `hermes config check` / `hermes doctor` evidence; no raw identifiers or credential fingerprints retained. |
| HRD-071 | Unauthorized-user, prompt-injection, secret-canary, private-URL, excluded-tool, and write-denial tests pass. | Dated canary report. |
| HRD-072 | Real critical paths are exercised after update/restart. | Gateway, file, MCP, cron, and custom integration canaries. |
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
- official docs/current CLI contradict the proposed command;
- recovery ceases to be credible.
