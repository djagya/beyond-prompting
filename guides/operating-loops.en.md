# Operating Loops: From Delegation to Delivery

**Operational synthesis from repeated practice, not a universal platform guarantee.**

These contracts complement [setup patterns](setup-patterns.en.md) and [weekly learning extraction](weekly-learning-extraction.en.md). Adopt them in the current owner of the workflow rather than adding another controller or a permanent instruction layer.

## 1. Give one owner a coherent result

By default the controller executes the work directly. Delegate only when a bounded, independent, verifiable branch earns its coordination cost (see [Single Agent by Default](../readings/single-agent-by-default.en.md)); then give one capable worker the whole coherent result, including development and self-verification. Keep architecture, shared state, live external authority and final integration acceptance with the controller. A second reviewer must test a distinct material failure mode, provide specialist competence or justified independence; do not insert a generic reviewer after every task.

A useful task contract:

```text
Outcome and requested form:
Existing source/owner and fixed constraints:
Authorized targets/actions; forbidden targets/actions:
Known material edge cases:
Capabilities required and available:
Acceptance evidence and explicitly untested layers:
Recovery boundary:
Handoff artifact, next owner and next action:
```

State invariants and known edge cases without prescribing every keystroke to a strong worker. A task should be small enough to verify coherently, but not fragmented solely to create more handoffs. Do not prescribe particular model names: choose the least costly route that reliably meets the risk and reasoning demand; cheap scheduling does not imply cheap architectural judgment.

## 2. Check the critical capability before dispatch

Match the task to actual network, storage, tool, authentication, runtime and output limits—not to a role label. Exercise a safe critical-path probe before commissioning a large collection or integration.

If a worker lacks authenticated access, retain that action at the authorized controller and pass a bounded non-secret result. Never transfer credentials or widen permissions for convenience. Before declaring a blocker, inspect existing approved API/helpers, account access and prior successful routes. Preserve security boundaries; one failed browser or RPC path is not proof that the outcome is impossible.

## 3. Continue until the authorized boundary

A process owner continues ready in-scope transitions rather than stopping after an arbitrary one-step wake. Stop when:

- the requested outcome is verified and delivered;
- a genuine blocker requires a named decision or missing capability;
- commissioned external work is pending;
- the bounded runtime budget is exhausted with a durable checkpoint.

Checkpoints name current state, exact candidate, next owner/action and authority boundary. Write a checkpoint only to a destination the mandate authorizes; for read-only work, return findings and source locators in the reply instead of writing into the target. Never place private evidence in a public checkout. For partial or truncated evidence, record the denominator, what was covered and how to recover the remainder. Notifications are wake signals, not current truth: inspect the authoritative target once, discard superseded events and do not replay completed mutations. Do not busy-poll CI or child workers.

Implementation-phase completion is not release acceptance. When CI belongs to the controller, hand off the durable candidate and self-verification; when the worker's own completion contract requires CI, preserve that gate until exact-candidate evidence arrives. A test receipt for another revision does not clear the release barrier.

## 4. Propagate corrections to every active owner

A user correction may affect configuration, task bodies, profile descriptions, controller prompts, skills and project current-state records. Identify the affected active surfaces, replace the superseded requirement and verify agreement. Source, deployed copy and loaded process are separate evidence layers.

Do not rewrite historical evidence into current instructions. Classify paused and retired artifacts separately; correction does not authorize reactivation. Keep one canonical current value per owner. Update private identity only through its own approval path.

## 5. Accept the user's job in the requested form

A document request is not permission to modify the website. A visual timeline is not satisfied by a wall of prose. A layout must show spatial fit, not merely wiring. A dashboard's zero failures is meaningless if the producing pipeline is idle.

Define acceptance across three independent questions: are the facts correct, can the user perform the intended task, and does the form preserve the requested intent? For metrics, expose unavailable measurements and denominators; do not turn missing observations into zeros.

## 6. Keep evidence and delivery connected

A handoff names source/version or retrieval date, tested scope, artifact location, uncertainty and remaining owner. The controller verifies consequential claims and returns the useful synthesis to the originating request. A task-status notification is not the promised result.

An ambiguous result is unknown, not failed. If a non-idempotent action (send, payment, publication, import, resource creation) timed out or lost its response, first inspect the exact target, provider receipt or log. Repeat only after proven non-application or under a documented idempotency key; otherwise report a blocker with the evidence collected.

Avoid unsafe repetition to obtain fresher evidence. Reuse valid evidence for an unchanged exact candidate; refresh mutable facts when the next decision depends on them. No deployment, purchase, send or negative write-test is implied by a request to prove a patch.

## Compact continuation check

```text
What is current, and what evidence binds it to this candidate?
What ready transition remains inside the mandate?
Can I execute it safely now, or is external work actually pending?
If stopped: what precise owner/action reopens progress?
Has the requested artifact and decision-relevant result reached the user?
```

These are practice-derived hypotheses to validate in your own environment. Test one recurring workflow first; retain a new rule only when it improves measured reliability, user intervention, latency or cost.
