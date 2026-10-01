# Setup Patterns Worth Reusing

**Practice notes from Danil's customized Hermes setup; not a required deployment template.**

This is a map of portable decisions, not a copy of a private configuration. Adapt the controls to your own account, tools and risk envelope.

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

[Danil's Hermes fork](https://github.com/djagya/hermes-agent) is the customization and integration surface used alongside these methods. [Upstream Hermes](https://github.com/NousResearch/hermes-agent) remains the reference for the base project.

Branch contents and upstream inclusion change over time. This guide does not claim that every fork change is absent upstream, required for these methods or suitable for another deployment. Before adopting a build, inspect the intended branch, compare it with current upstream, read its tests and release notes, and choose a known revision. Do not assume the fork's default branch is the build currently used by its owner.

- [Official Hermes documentation](https://hermes-agent.nousresearch.com/docs/)
- [Operational literacy](../readings/beyond-prompting.en.md)
- [Capability and authority](../readings/principles-from-hermes-in-practice.en.md)
