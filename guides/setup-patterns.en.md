# Setup Patterns Worth Reusing

**Practice notes from Danil's customized Hermes setup; not a required deployment template.**

This is a map of portable decisions, not a copy of a private configuration. Adapt the controls to your own account, tools and risk envelope.

Start with the [agent entry guide](agent-start.en.md) for a capability map and fallbacks. One controller is sufficient; private profiles, workers, memory services and deployment paths are not prerequisites. For concrete execution contracts, see [Operating Loops](operating-loops.en.md). For a concrete deployment, see [Reference Setup](setup-reference.en.md), [Operations](operations.en.md), [Identity, Memory and Context](identity-memory-context.en.md) and [Operating Hermes with a Coding Agent](coding-agent-operator.en.md).

## 1. Review experience, then inspect the mechanism

Run [Weekly Learning Extraction](weekly-learning-extraction.en.md): review first, inspect current owners second, implement only after a bounded mandate. A failed outcome may expose an instruction conflict or unavailable capability rather than a missing rule.

## 2. One owner of the final outcome

A controller retains integration, external authority and final verification. Workers receive bounded tasks that match their actual capabilities. Use [Single Agent by Default](../readings/single-agent-by-default.en.md) to decide whether delegation earns its cost. A notification or worker handoff is not final delivery.

## 3. Separate current truth, procedures and history

Maintain one current decision in its proper owner. Procedures live in reusable skills; project state lives in project artifacts; private source evidence remains private. Historical summaries should not compete with later user corrections. Inspect source and deployed state separately.

## 4. Match proof to the requested job

Verify the useful end state, not just tool success: documents must be readable, visual maps must remain visual, access routes require actual safe probes, temporal answers require dated evidence. Record which checks were not executed.

## 5. Keep external boundaries explicit

Capability is not authority. A signed-out browser does not prove that an API route is unavailable. A configured credential does not prove working access. Preserve origin binding, native secret transport, confirmation boundaries and ambiguity-safe retries. See the [hardening guide](hermes-hardening.md).

## 6. Prefer the existing lifecycle owner

Use the system's native job, service and recovery mechanisms before adding another watcher. Make each controller's stop condition explicit: completed result, genuine blocker, pending external work or exhausted bounded budget. Do not busy-poll workers or CI.

## The Hermes fork

[Danil's Hermes fork](https://github.com/djagya/hermes-agent) is upstream Hermes plus operational fixes for one long-running Docker deployment: an always-on messaging gateway, many cron jobs, a secret manager, card payments under owner approval and an agent that edits its own skills. Release branches are cut from upstream release tags and published as digest-pinned, attested container images. [Upstream Hermes](https://github.com/NousResearch/hermes-agent) remains the reference for the base project.

[Danil's Hermes Fork, in Plain Words](hermes-fork.en.md) explains what the fork changes by area, why, which parts went upstream, what running it costs and what to check before you run the image. It also has a detailed per-area table for comparing builds. Branch contents and upstream inclusion change over time, so inspect the revision you intend to run and compare it with current upstream; do not assume the fork's default branch is the build its owner runs.
