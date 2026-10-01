# Weekly Learning Extraction

**Independent field guide; not official Hermes or Nous Research documentation.**

A persistent assistant accumulates successful work, corrections, failed attempts and unfinished handoffs. A weekly review can turn that record into reusable improvements. The useful output is not a diary of completed tasks: it is a small set of lessons, checked against the procedures and executable surfaces that shape the next run.

## Start with this request

```text
Review our sessions with activity during the last seven days, including
sessions that started earlier and continued within the window.

Extract general, valuable lessons from repeated corrections, failures,
successes and avoidable user intervention. Be initiative-driven, but do
not modify anything: no memory, skills, files, jobs, tasks or settings.

Use primary messages and adjacent responses. Distinguish my decisions
from your proposals and generated notifications. Deduplicate replayed
or compacted history. State the exact window, coverage and limitations.

For each important lesson, provide:
- the observed pattern and supporting source locators;
- the reusable principle, with its applicability and exceptions;
- whether it is already covered by an existing rule;
- the smallest useful improvement and how we could verify it.

Keep private incident evidence out of anything intended for sharing.
Do not turn every observation into a new rule or task.
```

Tool-created caches may still exist even during a read-only review. Distinguish these incidental artifacts from deliberate changes to the user's operating state; do not promise that literally no bytes will be written by the tooling.

## Review activity, not just session creation dates

Fix the time window and timezone before selection. Include old sessions that contain new messages in that window. Where available, separate substantive human messages from scheduled reports, task notifications and transport metadata.

Discovery results and bookends help locate a conversation. They do not prove a decision. Read the original message and the surrounding exchange before attributing acceptance, correction or completion to the user.

Count coverage programmatically when making numerical claims. If the session backend does not expose the necessary activity range, disclose the limitation rather than presenting a partial search as a complete weekly census.

## Extract patterns without inventing consensus

Useful questions include:

- Which correction did the user have to repeat?
- Did a working implementation fail at integration or delivery?
- Was an access blocker declared before an existing route was checked?
- Did the delivered format differ from the requested artifact?
- Did a benchmark prove less than the final claim suggested?
- Which successful method deserves reuse?
- Which accepted user choice closed an obsolete subgoal?

One severe failure can justify a lesson. A repeated pattern strengthens it. Record observation, inference and proposal separately. Do not reinterpret a user's stated emotion or objective merely to make the analysis more interesting.

## Audit the owners before proposing edits

After the review, use a separate request:

```text
Inspect the related skills and executable surfaces read-only.
For each lesson, distinguish:
1. a missing rule;
2. an existing adequate rule that was not applied;
3. conflicting current instructions;
4. a routing, capability, code or configuration defect;
5. a historical issue that has already been fixed.

Propose a minimal ordered plan with exact targets, dependencies,
acceptance tests, rollback and remaining uncertainties. Do not apply it.
Use bounded subagents only for independently verifiable lanes.
```

The relevant surface might be a skill, profile boundary, task specification, controller prompt, helper implementation, project acceptance contract or source/deployment mismatch. A skill edit cannot repair every kind of defect.

Prefer existing owners. Avoid a new universal workflow, watcher or supervisor when a local correction is sufficient. Child reports are leads: the controller verifies consequential findings against current primary sources.

## Apply only after an implementation mandate

An approval such as “implement the reviewed plan” can delegate reversible in-scope work. It does not authorize unrelated publication, purchases, real payments, credential exposure or weakened safety controls. Preview exact targets, scope, recovery and material failure modes; retain any action-specific gates required by the environment.

Re-read targets before editing. Replace superseded current requirements instead of appending contradictory instructions. Reconcile affected source and deployed surfaces without rewriting historical evidence or resuming paused jobs automatically.

## Verify the real outcome

Use the narrowest appropriate proof:

- native readback and exact diff for configuration or contract changes;
- safe read-only API requests for access routes;
- isolated synthetic scenarios for payment boundaries;
- actual retrieval-to-answer cases for memory;
- rendered artifacts and reader tasks for document usability;
- a natural controller wake and final delivery for continuation.

A source-string assertion proves that text exists. A fresh-context LLM canary proves behavior only in that scenario. Neither is production acceptance. Report unexecuted checks and blockers explicitly; never count prepared tests as passed tests.

## Keep the useful lesson, not the whole week

Put reusable procedures in the existing owning skill; project decisions in project state; genuinely cross-session personal facts in bounded memory. Identity changes require their own approval. Preserve private evidence privately and publish only generic examples.

The review succeeds when the next relevant task needs less repeated correction and returns a better verified result—not when the assistant has written more rules.

## Related material

- [Reusable agent procedure](../skills/weekly-learning-extraction/SKILL.md)
- [Setup patterns](setup-patterns.en.md)
- [Single Agent by Default](../readings/single-agent-by-default.en.md)
- [Official Hermes documentation](https://hermes-agent.nousresearch.com/docs/)
