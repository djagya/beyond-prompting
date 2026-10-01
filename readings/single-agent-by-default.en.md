# Single Agent by Default

## When delegation earns its coordination tax

**Independent field note; not official Nous Research or Hermes Agent documentation.**

Delegation is not evidence of sophistication. It is an architectural trade: the system exchanges unified context for parallel capacity, independent exploration, or specialist attention.

That exchange is sometimes excellent. It is never free.

> Start with one capable agent. Add agents only when the structure of the task—not its apparent size—pays for coordination.

## 1. What delegation actually optimizes

A child agent gets a fresh context and can investigate without filling the controller's working memory with every search result, tool trace, and abandoned hypothesis. Several children can also work simultaneously.

These are real advantages:

- **parallelism:** independent work finishes concurrently;
- **context isolation:** large intermediate traces stay outside the controller context;
- **specialization:** a bounded question receives a distinct procedure or review lens;
- **independence:** an auditor can inspect a frozen result without inheriting the implementer's reasoning.

But context isolation is not compute efficiency. Every child receives its own instructions, reconstructs relevant state, invokes tools, and returns a summary that the controller must interpret and verify. Delegation can reduce wall-clock time while increasing total tokens, tool calls, latency variance, and integration work.

## 2. What the evidence says

### Architecture must match task structure

*Towards a Science of Scaling Agent Systems* evaluated single-agent and four multi-agent architectures across controlled agentic benchmarks.[1] Its central result is not that one architecture always wins, but that coordination succeeds only when it matches the task.

In the reported experiments:

- centralized coordination improved performance by about 81% on decomposable financial reasoning;
- every tested multi-agent architecture degraded sequential planning performance by 39–70%;
- tool-heavy workflows incurred a growing coordination penalty;
- independent aggregation amplified trace-level errors far more than centralized verification;
- the benefit of additional agents diminished when the single-agent baseline was already strong.

These are benchmark results, not universal constants. The durable lesson is structural: parallel exploration and sequential stateful reasoning are different computational shapes.

### Stronger models shrink the default case for swarms

*Single-agent or Multi-agent Systems? Why Not Both?* compared SAS and MAS designs across code generation, software engineering, mathematical reasoning, travel planning, financial analysis, retrieval, and scientific experimentation.[2]

The authors found that multi-agent gains often narrowed as base models improved, while coordination remained expensive. Their evaluated systems showed substantial additional token consumption for MAS. The prose ranges in §3.2 do not match every row of Table 3, so those ranges are not treated here as a uniform summary of the table. They identified three recurring defect locations:

- **node defects:** one critical agent still bottlenecks the whole system;
- **edge defects:** downstream agents are harmed by excessive or distracting upstream output;
- **path defects:** summarization and handoffs lose decisive information.

Their practical answer is not a permanent choice between SAS and MAS. It is routing and cascade: try the efficient single-agent path where appropriate, verify the result, and escalate only the requests that need a more expensive architecture.

### Breadth-first research is a genuine multi-agent case

Anthropic's production account of its Research system provides the important counterexample.[3] Multi-agent research substantially outperformed a single agent on an internal breadth-first research evaluation, especially when many independent directions had to be searched simultaneously.

The cost was equally explicit: Anthropic reported that agents used about four times the tokens of ordinary chats, while multi-agent systems used about fifteen times as many. It also noted that most coding tasks contain fewer truly parallel subtasks than open-ended research.

The useful conclusion is not “never delegate.” It is:

> Spend the coordination budget where independent search breadth, context scale, or task value makes the additional compute worthwhile.

## 3. The delegation gate

Delegate only when all five conditions hold:

1. **Reasoning-heavy** — the work requires sustained investigation, implementation, or critique rather than one deterministic operation.
2. **Bounded** — the child can own one explicit outcome, corpus, module, or read-only review surface.
3. **Low coupling** — its progress does not depend on continuous access to another agent's changing state.
4. **Verifiable** — the controller can inspect artifacts, rerun tests, or check cited evidence.
5. **Net-positive** — parallelism, specialization, context isolation, or independent review is worth the duplicated prompt, discovery, synthesis, and verification cost.

If one condition fails, keep the work with the controller.

### Keep local

- one or two tool calls;
- deterministic enumeration, transformation, filtering, hashing, or validation;
- sequential debugging where each observation changes the next step;
- edits to shared files or one mutable external target;
- work requiring live clarification from the user;
- authorization, publication, payment, deletion, deployment ownership, or final integration.

### Delegate

- independent literature or market searches;
- separate jurisdictions, repositories, products, or evidence families;
- disjoint implementation modules with explicit ownership;
- a specialist analysis whose intermediate trace is large;
- a read-only adversarial review after implementation is frozen.

## 4. Use the smallest useful topology

Prefer architectures in this order:

1. **Single controller** — one reasoning locus, direct tools, unified state.
2. **Controller + specialist** — one isolated investigation or critique.
3. **Small parallel batch** — several disjoint workers, one central synthesizer.
4. **Separate audit wave** — read-only reviewers after a frozen implementation barrier.

A cascade is an escalation policy, not a fifth larger topology: start with one agent and escalate only when a failed or incomplete verification justifies it. A separate audit wave is optional: use it for a distinct material risk, specialist expertise or justified independence; otherwise controller verification suffices.

Agent count is not a quality metric. A five-agent system with duplicated discovery and overlapping ownership may be worse than one strong agent with a disciplined tool loop.

## 5. Keep shared state centralized

The controller should retain:

- architecture and decomposition;
- authoritative source discovery;
- authorization boundaries;
- shared files, queues, databases, and external state;
- conflict resolution and final synthesis;
- final verification and the completion claim.

Children should receive bounded scopes and return evidence. Their summaries are claims, not proof. Read back consequential written artifacts and inspect external state at the controller. Repeat tests only when safe and authorized; reuse valid evidence bound to the exact unchanged candidate. A patch mandate does not authorize deployment, real payments or other external tests. Completion claims must name the tested layer and any unverified handoff.

When independent audit is warranted, use an explicit temporal barrier:

```text
snapshot
→ implementation
→ frozen state
→ independent review
→ remediation
→ final verification
```

An auditor started before the implementation barrier reports on a historical state. Its conclusions must not be merged into the current state without revalidation.

## 6. Quarantine context without losing evidence

Context isolation is strongest when large child outputs become durable artifacts rather than long conversational summaries.

Prefer:

```text
child explores a large corpus
→ writes a cited report or structured dataset
→ returns a path, source/version, retrieval date, scope and compact findings
→ controller reads only the decision-relevant sections
```

This reduces the “game of telephone” described by Anthropic: specialist output survives without being repeatedly summarized through coordinators.[3]

A summary cap should be treated as a handoff limit, not as a substitute for durable evidence. If omitted detail matters, store it and return a reference.

## 7. Keep the hot path short

The cited studies measure coordination among agents, not the length of skill files or policies.[1][2] Extending the result to instruction surfaces is an engineering inference: any rule loaded on every routine run consumes context, adds conditions to reconcile, and can turn one coherent agent into an internal communication graph.

Rigor is not proportional to prose volume. Use a complexity budget:

- keep only rules needed on every run in the hot path;
- move branch-specific rationale and edge cases behind optional references;
- add a rule only when it changes a decision or prevents a demonstrated reusable failure;
- before appending, replace, consolidate, or delete equivalent prose.

An incident can justify learning without justifying permanent ceremony. Extract the smallest durable invariant, discard incident residue, and remeasure the routine path. A skill that only grows will eventually reproduce the coordination cost it was meant to control.

## 8. Hermes mapping

Hermes provides three different execution surfaces:[4][5]

- call a normal tool directly for one operation;
- use `execute_code` for mechanical multi-call logic, loops, and reduction;
- use `delegate_task` for reasoning-heavy isolated work or independent parallel branches.

Delegation configuration controls capacity, not policy. Model choice and reasoning effort determine child capability. `max_iterations` is a safety ceiling, not a target number of turns. Raising it helps genuinely long work finish; it does not make a weak delegation decision better.

A useful configuration posture is:

- a capable child model;
- enough iterations for long research or implementation;
- bounded concurrency;
- shallow or disabled nesting;
- no wall-clock timeout unless operationally necessary;
- artifact-backed handoffs when summaries may truncate.

The controller should still decide whether a child should exist at all.

## 9. Measure the architecture, not the spectacle

After a delegated run, record:

- wall-clock time and longest critical path;
- total child calls or token use;
- duplicated discovery and verification;
- stale findings caused by moving state;
- merge or integration conflicts;
- defects found that a controller-only pass likely would have missed;
- controller context protected;
- verified outcome quality.

Parallelism can be worth higher compute for urgent or valuable research. Higher compute without reduced critical-path time, specialist gain, context protection, or better verified quality is simply overdelegation.

## Operational rule

```text
one agent by default
→ keep the routine instruction path short
→ delegate only bounded independent work
→ centralize shared state and authority
→ freeze if independent review is warranted
→ verify child claims at the root
→ escalate architecture only when evidence justifies it
```

The aim is not to minimize agent count. It is to spend coordination only where coordination produces something one coherent agent could not produce as reliably, quickly, or context-efficiently.

## Sources

[1] [Kim et al. — Towards a Science of Scaling Agent Systems (arXiv:2512.08296)](https://arxiv.org/abs/2512.08296)

[2] [Gao et al. — Single-agent or Multi-agent Systems? Why Not Both? (arXiv:2505.18286)](https://arxiv.org/abs/2505.18286)

[3] [Anthropic — How we built our multi-agent research system](https://www.anthropic.com/engineering/built-multi-agent-research-system)

[4] [Hermes Agent — Subagent Delegation](https://hermes-agent.nousresearch.com/docs/user-guide/features/delegation)

[5] [Hermes Agent — Delegation & Parallel Work](https://hermes-agent.nousresearch.com/docs/guides/delegation-patterns)
