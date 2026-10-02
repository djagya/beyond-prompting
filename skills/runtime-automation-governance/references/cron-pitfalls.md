# Cron pitfalls — failure, symptom, fix

Operational practice for recent Hermes builds, stated as the scheduler code behaves. Defaults move between releases; check the scheduler source or CLI help on your build before relying on one.

| Pitfall | Symptom | Fix |
|---|---|---|
| Interval measured from previous finish | `every 1m` watchdog fires every ~1–2 min, drifts | Use wall-clock cron (`* * * * *`); verify spacing of two natural runs |
| `once` + repeat count | Job fires once and completes | Use an interval schedule with a repeat count; check `next_run_at` advances |
| Missed-run catch-up (`cron.catch_up_missed`, default true) | Burst of runs after downtime or upgrade | Set it false where bursts are harmful (this install: false everywhere); sparse named-profile configs inherit upstream defaults for missing keys, so set it per profile and assert it on deploy |
| Unpinned model | Cron spend or behaviour changes after a chat-model switch | Set `cron.model` / `cron.model_provider`, or pin per job |
| Completed one-shot sweep (seven-day retention) | Registry or audit shows a "missing" job | Treat the sweep as normal lifecycle; regenerate registries from the live store |
| Global MCP added to jobs (`no_mcp` sentinel) | Cron job calls a write-capable MCP tool it was never given | Add `no_mcp`; verify resolved tool names |
| Toolsets not settable by `cron edit` (build used here) | Edit ignores or lacks a toolset flag | Use the agent tool's update path, or the single-field atomic edit in SKILL.md step 6 |
| Dangerous command in cron (`approvals.cron_mode: deny`) | Run ends blocked / `pending_approval` | Report as policy blocker; split compound commands; never wait for an approver |
| Approval-gated memory/skill writes in cron | Writes staged forever; job "succeeds" but nothing persists | Keep memory writes ungated and omit the `memory` toolset where writes are forbidden; review the staged skill queue on a schedule |
| Script given as an absolute path or outside the scripts directory | Job rejected or script not found | `script:` is a basename resolved under `$HERMES_HOME/scripts/`; ship a real file there through the apply step |
| Script-only (`no_agent`) failure labelled as provider failure | Alert blames the model provider for a script timeout | Check `no_agent` first; read the saved script output before touching provider routing |
| Secrets in script env | Script cannot see provider keys | Cron script env is sanitized; pass only what the script needs through its own secret path |
| Zero-content agent turns | Cost from frequent polls that find nothing | Monitor mode (`monitor_script`, hash-suppressed) or the `wakeAgent: false` gate, or `no_agent` script-only jobs |
| Overlapping runs | Two runs of the same job mutate shared state | Hold a non-blocking lock in the script; skip with `WARN` when held |
| Silent loop death | Background sync stops for hours, nobody notices | Consecutive-failure counter + page after N; check the page actually lands |
| Supervisor "down" treated as a lock | A watchdog revives the writer mid-maintenance | Hold every restart source, wait for graceful exit, re-prove quiescence just before apply |
| Stored job treated as reboot persistence | Jobs never fire after a host restart | Verify the supervisor that starts the scheduler, not the job file |
| Alert target broken | Delivery log shows "chat not found" or no home channel | End-to-end alert test after every channel/token/profile change |
| Gateway crash in a multiplexed install | Every profile's jobs stop together | Watch the default gateway's memory and PID headroom; alert on it, not per profile |

## Monitor-mode pattern

Before adding a reactor daemon, cursor database or poller:

1. write a deterministic `monitor_script` that projects only decision-relevant state (status, current run, bounded failure state) — no timestamps, heartbeats or comments: the scheduler hashes the **exact** output bytes, so unstable output wakes the agent every tick;
2. unchanged output suppresses the agent run and delivery; a changed output injects a bounded diff into the prompt; a script failure is an error, never a change, and leaves the stored hash alone;
3. include a coarse liveness bucket if periodic reasoning is still wanted;
4. fail closed (wake and alert) when an expected input is missing or ambiguous;
5. prove the cycle: baseline → unchanged (no model turn) → relevant change (model turn).

When a script decides on its own whether to wake the agent, the lighter gate is `{"wakeAgent": false}` on its last stdout line.

## Temporary verification helpers

Run and remove ad-hoc verifier scripts in separate commands. Remove one literal path per command (no wildcards, recursion, substitution or chaining) and verify absence. Do not generalize this to arbitrary temp-directory deletion.
