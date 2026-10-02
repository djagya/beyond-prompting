# Cron pitfalls — failure, symptom, fix

Practice, not an official guarantee. Items marked *observed* were seen on recent Hermes builds and are not in the official docs; confirm on your version before relying on them.

| Pitfall | Symptom | Fix |
|---|---|---|
| Interval measured from previous finish (*observed*) | `every 1m` watchdog fires every ~1–2 min, drifts | Use wall-clock cron (`* * * * *`); verify spacing of two natural runs |
| `once` + repeat count (*observed*) | Job fires once and completes | Use an interval schedule with a repeat count; check `next_run_at` advances |
| Missed-run catch-up (*observed: `cron.catch_up_missed`, default true*) | Burst of runs after downtime or upgrade | Set it false where bursts are harmful; named profiles may inherit upstream defaults for missing keys, so set it per profile |
| Unpinned model (documented) | Cron spend or behaviour changes after a chat-model switch; or the drift guard skips runs | Set `cron.model` / `cron.model_provider`, or pin per job |
| Completed one-shot sweep (*observed, ~7 days*) | Registry or audit shows a "missing" job | Treat sweep as normal lifecycle; regenerate registries from the live store |
| Global MCP added to jobs (*observed; `no_mcp` sentinel*) | Cron job calls a write-capable MCP tool it was never given | Add `no_mcp`; verify resolved tool names |
| Toolset cannot be set by CLI on some versions | `cron edit` ignores or lacks a toolset flag | Use the agent tool's update path, or the single-field atomic edit in SKILL.md step 6 |
| Dangerous command in cron | Run ends blocked / `pending_approval` | Report as policy blocker; split compound commands; never wait for an approver |
| Approval-gated memory/skill writes in cron | Writes staged forever; job "succeeds" but nothing persists | Turn the gate off for unattended stores and omit the toolset where writes are forbidden, or review pending queues on a schedule |
| Script outside the scripts directory | Job rejected or script not found | Place a real file inside `$HERMES_HOME/scripts/`; paths escaping it are rejected (documented) |
| Script-only (`no_agent`) failure labelled as provider failure (*observed classifier defect*) | Alert blames the model provider for a script timeout | Check `no_agent` first; read the saved script output before touching provider routing |
| Secrets in script env | Script cannot see provider keys | Documented: cron script env is sanitized; pass only what the script needs through its own secret path |
| Zero-content agent turns | Cost from frequent polls that find nothing | Use the documented `wakeAgent: false` gate or `no_agent` script-only jobs; a frequent tick need not be a frequent model turn |
| Overlapping runs | Two runs of the same job mutate shared state | Hold a non-blocking lock in the script; skip with `WARN` when held |
| Silent loop death | Background sync stops for hours, nobody notices | Consecutive-failure counter + page after N; check the page actually lands |
| Alert target broken | Delivery log shows "chat not found" or no home channel | End-to-end alert test after every channel/token/profile change |

## Monitor-mode pattern

Before adding a reactor daemon, cursor database or poller:

1. write a deterministic script that projects only decision-relevant state (status, current run, bounded failure state) — not timestamps, heartbeats or comments;
2. print `{"wakeAgent": false}` when the projection is unchanged;
3. include a coarse liveness bucket if periodic reasoning is still wanted;
4. fail closed (wake and alert) when an expected input is missing or ambiguous;
5. prove the cycle: baseline → unchanged (no model turn) → relevant change (model turn).

## Temporary verification helpers

Run and remove ad-hoc verifier scripts in separate commands. Remove one literal path per command (no wildcards, recursion, substitution or chaining) and verify absence. Do not generalize this to arbitrary temp-directory deletion.
