---
name: weekly-learning-extraction
description: Extract evidence-grounded lessons from a week of sessions, audit their owners, and propose minimal improvements without silent mutation.
metadata:
  hermes:
    tags: [sessions, retrospective, learning, evidence]
---

# Weekly Learning Extraction

Human guides: [English](https://github.com/djagya/beyond-prompting/blob/main/guides/weekly-learning-extraction.en.md) and [Russian](https://github.com/djagya/beyond-prompting/blob/main/guides/weekly-learning-extraction.ru.md). Human guides are optional rationale; this procedure is self-contained when installed alone.

## Authority and modes

Default to REVIEW: read-only analysis. AUDIT inspects relevant procedures and surfaces; PLAN proposes changes. APPLY requires a separate implementation mandate and exact scoped targets. A review does not authorize memory capture, skill edits, task creation, job changes or publication. Tool-generated caches are incidental artifacts, not intentional target changes.

## Procedure

1. Fix the seven-day activity window, timezone and corpus; compute the boundaries with code, not mentally, and use an exclusive end. Later outcomes may verify a fact dated inside the window but do not enter the review as new events. Apply the bounds to each message timestamp, not the session creation date; include old sessions with in-window activity. Check actual history/provenance capabilities before choosing tools. With only selected exports review that bounded corpus; without history report readiness, not invented lessons. Unknown timestamps or authorship are coverage uncertainty. Count coverage programmatically against a stated denominator; a top-k search result is not a census. Do not invent universal Hermes export commands.
2. A `user` role does not prove human authorship: exclude generated jobs, task notices, quoted material and compaction summaries as consent evidence. Collapse only copies with demonstrated transport identity/lineage; matching text or timestamps alone do not prove replay. Preserve independently sent identical corrections. Mark unresolved provenance instead of silently removing it. Bookends and search hits locate evidence; inspect primary authored messages and adjacent responses.
3. Select recurring corrections, major failures, successful reusable methods and avoidable user intervention. Keep observation, inference and proposal separate. Do not convert every incident into a rule or obligation.
4. For each significant lesson, identify the existing semantic owner. Distinguish missing rule, adequate-but-unapplied rule, conflicting contract, routing/capability/code/config defect, and already repaired history. Inspect current primary surfaces before claiming a live defect.
5. Default to one controller with task-relevant context; no workers, profiles or private integrations are required. Use bounded independent children only where their evidence surfaces are separable and available. Give read-only scope, evidence budget, forbidden actions and handoff format. Root verifies decision-relevant claims and synthesizes the plan; child confidence is not proof.
6. Propose exact targets, minimal changes, ordering, dependencies, acceptance checks, gates and recovery. Encode before you write prose: a "remember to / never do X" lesson becomes a script guard, test, config assertion or repository setting first; only what cannot be encoded becomes an instruction. Give each lesson one canonical home and link to it elsewhere. Prefer replacing superseded current requirements to duplicating prose, and include a sweep of stale current-state statements the lesson touches. Preserve historical evidence and paused state.
7. If implementation is subsequently authorized, preview the envelope, apply on supported surfaces and read back exact targets. Preserve action-specific external gates and security controls. Never publish private incident evidence.
8. Test actual outcomes at the appropriate boundary. Distinguish static assertions, fixtures, fresh-context behavioral canaries, live access probes and production evidence. Prepared/unexecuted tests are not PASS.
9. Report applied changes separately from proposals and open acceptance. Persist lessons only in their proper owner within the authorized envelope: a repeatable procedure in the owning skill (where agent skill writes are approval-gated, a staged edit is a proposal until reviewed), a project decision in project state, a bounded cross-session personal fact in memory; do not silently rewrite identity. A dated retrospective narrative may record the review, but it is input, not canon: it is immutable after the session, and the change that adds it also folds every durable item into its canonical owner. Never write live values (versions, digests, ids, counts) into canonical prose; point to where they are read.

## Output

The evidence report and its locators are private by default. If sharing is authorized, prepare a separate generic summary without session IDs, internal paths, account identifiers or topology; do not publish or persist it without a mandate. If the environment lacks skills or persistent memory, propose changes to its existing procedural owner rather than auto-installing a new store.

- exact window, coverage, exclusions and limitations;
- selected findings: primary locator, pattern, reusable principle, applicability;
- disposition: already covered/fixed, application failure, or genuine gap;
- minimal plan: target, owner, dependencies, acceptance and rollback;
- if APPLY was authorized: exact changed targets, observed checks and unresolved gates.

## Negative controls

- Assistant recommendations and generated completion notices are not user consent.
- Top-k absence does not prove corpus-wide absence or the latest event.
- Profile names do not prove capabilities or permission.
- A requested document cannot be replaced by code changes.
- A successful benchmark cannot be promoted into an unsupported business claim.
- Pleasure and the user's stated emotion are not defects to optimize away.
- More rules, children or closed tasks do not themselves prove improvement.
- A retrospective that is not folded into its owners has not changed the next run.
