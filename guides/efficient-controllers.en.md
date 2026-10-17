# Efficient Controllers: Events, State and Prompt Cache

A design method for reducing unnecessary model work without reducing a controller's responsibility for a delegated outcome.

**Independent operational synthesis, not official Hermes documentation or a verified deployment recipe.** The architecture and acceptance scenarios below are a proposed engineering contract. They do not establish measured savings or authorize changing a running system.

## 1. Preserve the job before optimizing its cost

A controller may own an outcome, not merely process task-status notifications. It must notice stalled progress, incomplete acceptance and work that no longer serves the agreed goal. Replacing it with a status-change handler can make inference cheaper while quietly removing that responsibility.

Separate three kinds of work:

- **Event response:** an executor finishes, a requirement changes, an expected check completes or a specific deadline arrives.
- **Semantic review:** assess whether an active project is making useful progress, including problems that produce no formal event.
- **Useful execution:** carry an available integration or acceptance action to a verifiable stopping point.

An illustrative policy is to start processing material events within five minutes and detect signal-free stagnation within an hour. These are owner-selected targets, not universal defaults or platform guarantees. Record overload, source failures, scheduling delay and a controller busy with its own useful run as degradation rather than removing them from the measurements. Integration may legitimately take longer than the event-response target.

Useful work should end at a logical boundary. Waiting for a worker, CI, access or a human decision should generally happen outside a model run. A small fixed call budget is not a substitute for this distinction; retain a separate runaway safeguard.

## 2. Cache is not controller memory

Provider prompt caching reuses computation for eligible repeated input. It does not decide which project facts are current or maintain a durable record of handled events.

Keep these concepts distinct:

- **Authoritative sources:** accepted requirements, native task state, exact candidate identities and evidence.
- **Compact decision state:** the current interpretation, pending work and references needed for the next decision.
- **Conversation history:** a record of prior interactions, including explanations that may no longer be current.
- **Provider cache:** an execution optimization whose coverage and billing rules depend on the provider.

Summed input tokens count repeated context on successive calls. They are not the size of one continuously growing history. Measure total input, cache-read input, uncached input, cache write and output separately. Neither a high cache-hit ratio nor a silent final response establishes that a run was worthwhile. Subscription quota consumption is a separate question.

Keep stable instructions and tool definitions deterministic within a configuration version. Put changing observations after the stable material where the platform supports that arrangement. Check where the platform actually assembles per-run material: when injected observations precede the job text inside a volatile instruction, standing rules written into the job text are themselves volatile, and cacheable standing material belongs in the platform's stable prefix facility. Do not retain obsolete instructions to preserve cache hits, mutate past messages mid-run or make keep-warm requests without a demonstrated need.

## 3. Put a cheap gate before inference

The simplest architecture is often an existing scheduler, an inexpensive observation step and one controller run when a decision is due:

1. Read explicitly allowed sources.
2. Detect a material change, due wait check, semantic-review deadline or permitted recovery attempt.
3. If none applies, exit before inference.
4. Otherwise supply the wake reason, compact state and relevant changes to one controller.
5. Perform a bounded action or record an explicit wait.
6. Persist the considered source revision and decision result.

A frequent scheduler tick need not mean frequent inference. A model-generated “nothing changed” response has already paid the model cost.

Prefer native claims, execution history, monitor suppression and incident handling before adding a daemon, scheduler or cursor database. Native facilities must be inspected for their exact semantics, not treated as proof of an application-level delivery protocol.

For Hermes, consult the current [Scheduled Tasks documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron/). Fresh scheduled sessions, available monitor features, continuity injection and durable per-job facilities depend on the target build. Confirm the installed interface and source before using version-sensitive behaviour. No commands in this guide install or modify them.

### Material signals, not directory churn

Define a source manifest with a locator, authoritative owner, material revision rule, read capability and failure behaviour for each source.

Include only what the delegated outcome needs:

- active requirements and accepted corrections;
- relevant task ownership, dependencies, handoffs and terminal outcomes;
- selected acceptance records and exact candidate or artifact identities;
- specific external operations already being awaited;
- named wait deadlines and resumption conditions.

Exclude heartbeats, read timestamps, incidental logs and the controller's own administrative updates as independent wake reasons. Do not exclude a changed requirement or substantive handoff merely because task status is unchanged. Hashing every comment is noisy; ignoring all comment content can miss authoritative changes. Select the actual requirement-bearing sources.

An unavailable source is unknown or error, not unchanged. Hold the action that depends on it; do not automatically freeze unrelated authorized work. Represent each source's availability as a stable part of the gate output that changes only when availability changes, so one dead source neither storms the model with repeated wakes nor silently freezes every independent stream. Retry or escalate through a bounded existing operational path, not a model storm.

### Separate event and review clocks

Coalesce accumulated events for the same project. Preserve arrivals during an active run without starting a competing writer.

A semantic-review deadline is separate from event polling. A small event pass must not postpone it unless that pass performed the review. Leave time for queueing and analysis when setting the deadline. Validate natural scheduler cadence; an interval setting alone is not proof of wall-clock timing.

A completed finite mandate should not restart because a timer expired. A known human hold does not justify repeatedly asking the same question. Explicit ongoing maintenance responsibilities retain their own conditions.

## 4. Keep a small current-state contract

The compact state is an index of the current decision, not a second source of truth or a prose archive.

Useful fields include:

- format version and controller identity;
- mandate revision and authoritative source references;
- explicit mode: active, waiting or finite-complete;
- the last source revisions considered;
- accepted results with exact evidence references;
- active owners and dependencies;
- named waits, their targets, next checks and resumption conditions;
- pending wake or recovery ticket;
- last completed semantic review;
- next permitted action, or its precise absence.

Reuse an existing durable per-job facility where its semantics fit. Keep evidence payloads elsewhere. Moving a large previous report into a scratchpad that is automatically injected on every run is not an optimization.

An atomic write to one record prevents mixed fields, but does not establish compare-and-set, fencing or exclusive ownership. Prove the actual single-writer path, including recovery and late processes, before depending on it. If the available facility cannot provide a required property, choose a supported alternative or explicitly commission a narrow platform change.

Missing, corrupt, incompatible or silently omitted state requires reconstruction from authoritative sources before dependent mutation. It is not evidence of an empty or completed project. Terminal modes are reconstructed from authoritative records — an acceptance receipt or a mandate revision — never from the absence of state: if the mode cannot be determined, treat it as unknown, do not revive finished work, do not re-ask a known human hold, and escalate once.

A previous-run answer may help continuity but is not a current-state record. Remove that input only after demonstrating equivalent continuity and recovery with the replacement.

## 5. Observed does not mean handled

A monitor can remember a changed payload before the model successfully processes it. That can be a deliberate platform policy to avoid endless re-alerts. It does not acknowledge the controller's business decision.

Distinguish:

- **Observed revision:** what the cheap checker saw.
- **Pending ticket:** what still needs a decision or reconciliation.
- **Handled revision:** the specific snapshot for which a durable decision exists.

A required protocol is:

1. Capture the source revision and wake reason without marking them handled.
2. Let native observation bookkeeping advance without clearing application-level pending work.
3. Process the captured revision under valid ownership and authority.
4. After a durable result, acknowledge that revision. An explicit justified wait is a result; it need not mean project completion.
5. Keep later arrivals pending rather than acknowledging an uncaptured future snapshot.
6. On failure before acknowledgment, retain the pending work and allow a bounded retry when eligible. An unchanged monitor hash must not suppress recovery forever.
7. Before repeating an ambiguous external action, reconcile its exact target and existing receipt. Missing acknowledgment does not prove the action did not happen. Record the intended target and an idempotency key before issuing a non-idempotent effect, so a successor can reconcile an effect whose identifier was not knowable in advance.

Retry eligibility, deadlines and limits must be durable and integrated with the execution lifecycle. Do not change an attempt number on every idle tick just to force a new hash. Pending must survive a crash before the model's first write. One candidate derives it by comparing observed source revisions with the handled checkpoint; another uses a compatible observer-owned delivery journal persisted before native observation commit. A lost or corrupt delivery journal must not mean handled: reconstruct pending from authoritative sources and the checkpoint. Key retry eligibility on lifecycle events such as a failed execution, which change once per failure and never per idle tick. The physical carrier remains a proof obligation, not a reason to invent another storage service. A pending/handled protocol needs crash, concurrency and recovery proof; naming these fields is not that proof.

Acknowledgment, review timestamps and intent writes must not create new wake events. Checkpoint content belongs in the decision context, not in the wake fingerprint. If the native monitor hashes the entire gate output, do not serialize a controller-written checkpoint revision there; keep state-read failures distinguishable through stable health classes instead. Prove both the wake and no-extra-wake paths on the target build.

## 6. Bound runs by progress, not arbitrary smallness

Normal stopping points include a verified completed action, a worker handoff, an external wait, a real authority or capability gate, and exhaustion of the permitted recovery path.

A controller may continue a related useful integration without restarting only to satisfy a tiny budget. Long runs are diagnostic signals, not proof of waste.

A runaway safeguard should notice repeated actions against unchanged inputs and targets without new demonstrated progress. Keep a platform-level call budget as a high last-resort ceiling rather than a normal pass boundary, and detect loops by progress signatures recorded in the controller's own state. New source evidence invalidates the relevant prior decision, not every safety limit.

Before repeating a verification suite, identify what invalidated the old evidence and whether its candidate and environment still match. An administrative “unverified” label alone is not proof that code changed. Investigate a reproducible evidence/feedback mismatch at its owner; do not silently disable verification gates.

## 7. Define proof before rollout

The following are acceptance obligations, not reported test results:

- Unchanged observations suppress inference until a real deadline.
- Heartbeats do not wake the model, but a changed handoff or requirement at the same task status does.
- A specific external check can wake the waiting controller without a task-board change.
- Source failures remain visible without creating endless inference.
- A crash after observation commit but before model completion leaves recoverable pending work.
- A crash after an external effect but before acknowledgment does not duplicate that effect.
- Arrivals during processing survive acknowledgment of the earlier snapshot.
- Coalescing and recovery preserve one active writer, including protection from late stale writers.
- Missing or invalid compact state cannot unlock dependent actions.
- Restarts, clock boundaries and queues do not hide overdue reviews.
- Constant real events cannot indefinitely starve semantic review.
- Completed work and known human holds do not turn into automatic new work.
- Unchanged compatible evidence is not re-created solely for an administrative marker.

First use synthetic fixtures and saved observations, including a deliberately broken ordering as a negative control. Then compare a read-only shadow gate with manually classified material events. A shadow gate must not become a second controller with write authority.

A live pilot needs an explicit mutation mandate, one selected controller, source coverage, a preserved rollback and an observed no-change-to-real-change cycle. Observe natural fires and actual continuation, not only a successful configuration write. Roll out further only after acceptance.

Measure wake reasons, useful actions, avoidable repeats, per-event time from material change to detection and to processing start, pending-event age, review age, the time until blocked dependent actions are actually unblocked, recovery outcomes and tokens by category. Do not predict a savings percentage from a previous high-volume window without comparable project activity and a classified baseline.

Use null with a reason when authoritative event timestamps are unavailable, and report arrivals during a busy run separately. Inter-start intervals cannot substitute for event or unblock latency. Do not claim preserved latency targets when the required measurements are missing.

## 8. Rollback and evidence boundaries

Preserve the prior behavioural configuration, exact executable source and compatible state before a pilot. Do not overwrite newer scheduler bookkeeping with an old whole-file snapshot.

Quiesce or fence the active owner, retain pending external-effect handles, reconcile actual outcomes and restore compatible configuration and state. Decide the disposition of the new compact state explicitly — archive it out of band and remove it, or retain it with a translation the restored controller understands — and convert still-pending work into an input the restored configuration will actually see. Returning to an old monitor with an incompatible hash or checkpoint can swallow work rather than recover it.

Keep canonical source, deployed runtime, mutable state and proof artifacts distinct. Do not present a local candidate as a live deployment or a simulation as runtime acceptance.

This method is developed within the same practice described in [Operating Loops](operating-loops.en.md), [Setup Patterns](setup-patterns.en.md) and [Runtime Automation Governance](../skills/runtime-automation-governance/SKILL.md). It adds no authority beyond the owner's explicit mandate.
