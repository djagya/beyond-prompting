# From Capability to Authority

## Principles from operating a long-running AI agent

**Independent field note; not official Nous Research or Hermes Agent documentation.**

These principles were refined through sustained work with a customized Hermes-based assistant across software, research, automation, publishing, and external systems. They describe recurring failures that appear when a language model begins to act in a persistent world.

The labels **selection before canonization** and **Semantic Ownership Inversion** name patterns observed in this practice. No claim of first discovery or priority is made. Other methods below adapt established ideas from assurance cases, distributed systems, software architecture, and AI security.

## 1. Capability is not authority

The ability to produce something does not confer authority to decide that it should exist.

Agentic systems tend to collapse this sequence:

```text
capability
→ concrete output
→ implied decision
→ canonical state
```

A system can generate a design, task, message, configuration, publication, or plan. Its output immediately acquires weight because it is concrete and polished. A possibility begins to look like a decision merely because the agent rendered it first.

Use **selection before canonization**:

```text
possibilities
→ explicit comparison
→ human selection or bounded delegated selection
→ accepted operating state
```

A user may delegate bounded selection under explicit criteria; this does not turn every generated proposal into accepted state.

The agent may generate options and make trade-offs visible. Until a choice is accepted, those options remain provisional. The system should support judgment rather than push the user toward its own first concrete answer.

This principle applies to design variants, project plans, scheduled tasks, memory entries, training programs, publications, and external commitments.

## 2. Preserve modality

Agents tend to erase distinctions carried by modality:

- “could” becomes “should”;
- “proposed” becomes “accepted”;
- “prepared” becomes “active”;
- “observed” becomes “ours to act on”;
- “able to execute” becomes “authorized to execute.”

These are not linguistic details. They mark transitions in which human authority and choice must remain intact.

A well-designed system records state explicitly:

```text
observed
suggested
prepared
accepted
authorized
committed
verified
```

The model should not advance an item across those states merely because the next action seems useful.

## 3. Prevent Semantic Ownership Inversion

A recurring architecture failure occurs when a transport or storage mechanism begins to own domain meaning.

Examples:

- cloud storage moves files but should not define when a media delivery is complete;
- a browser submits a form but should not decide when an application is ready to file;
- a scheduler launches a job but should not define what counts as a new event;
- an email client sends a message but should not own the commercial or legal decision behind it.

This is **Semantic Ownership Inversion**.

The corrective rule is:

> Transport may execute; the domain owner decides meaning.

A domain owner should define:

- how the user’s request is recognized;
- what source is authoritative;
- what completion means;
- which invariants must hold;
- when side effects are permitted;
- which adapter should perform them.

Technology-specific adapters remain narrow. The domain owner preserves discoverability from the user’s language and owns verification of the domain outcome.

Alistair Cockburn’s original account of Hexagonal Architecture captures the same boundary: domain behavior should remain independent of interchangeable external adapters.[1]

## 4. Use consequence-driven assurance

Quality labels are too vague to govern consequential work.

Instead of saying that a system should be “secure,” “durable,” or “reliable,” name the failure it must prevent:

- a secret must not enter model-visible context;
- a committed item must not be delivered twice after restart;
- an acknowledged change must survive process death;
- a privileged action must remain bound to the approved target and payload;
- a published artifact must not contain private operational history.

Then construct an assurance case:

```text
Claim
→ Argument
→ Evidence
→ Residual uncertainty
```

Example:

```text
Claim:
The recurring integration does not duplicate committed work after restart.

Argument:
Committed state is durable, items have stable external identifiers,
and repeated execution reconciles before creating new effects.

Evidence:
A controlled restart test, external read-back, and receipts showing
one committed effect per stable identifier.
```

The **Claim–Argument–Evidence** structure follows the CAE notation used in assurance-case practice.[2] Goal Structuring Notation is a related, distinct notation for structuring assurance arguments.[3]

Two useful rules follow:

> No quality requirement without a named failure scenario.

> No material claim without evidence from the real path.

## 5. Distinguish the layers of runtime truth

“The file was fixed” is not a complete operational claim.

A running system has several layers of truth:

1. **Canonical source:** the authoritative source is correct.
2. **Deployed artifact:** the deployed copy matches the canonical source.
3. **Running process:** the live process loaded the deployed artifact.
4. **Mutable state:** cursors, locks, manifests, queues, and receipts satisfy their invariants.
5. **Operational path:** the real workflow functions and remains recoverable.

Each layer requires different evidence. Test only within the authorized scope and claim no more than the tested layer; a source-change task does not silently authorize deployment. Hand off unverified runtime layers explicitly.

A source diff does not prove deployment. Deployment does not prove process freshness. A healthy process does not prove state correctness. An isolated test does not prove scheduler-owned execution. Exit code zero does not prove the intended external consequence.

This distinction is especially important in long-running agents because their behavior persists across time and ownership boundaries.

## 6. Treat external actions as transactions

Any process that changes external state should distinguish at least:

```text
prepared
committed
failed
ambiguous
verified
```

The `ambiguous` state matters. If a request times out after submission, the effect may or may not have happened. Blindly retrying can duplicate a message, payment, upload, import, or resource.

A safer protocol is:

```text
discover
→ prepare exact payload
→ authorize exact payload
→ commit
→ read back
→ reconcile ambiguity
→ record receipt
```

Useful mechanisms include idempotency keys, stable external identifiers, compare-and-swap, snapshots of prior state, immutable receipts, and independent read-back. AWS’s Builders’ Library explains how idempotent API contracts make retries safe when a network failure leaves the caller uncertain about whether an effect occurred.[4]

These mechanisms make repeated execution safer while keeping uncertainty visible.

## 7. Gate destructive cleanup on recoverability and authority

For valuable or non-reproducible data, destructive cleanup requires two independent gates:

1. evidence that the intended deletion set is recoverable;
2. authority to delete that exact set.

A sound procedure is:

1. inventory the source;
2. build an identity-aware expected set;
3. compare it with an authoritative archive;
4. classify exclusions explicitly;
5. supplement missing archive items;
6. verify the archive from a second source of evidence;
7. freeze an immutable deletion manifest;
8. perform a dry run against that manifest;
9. establish explicit authorization bound to the frozen manifest, including a valid standing mandate when host policy permits;
10. delete only the frozen set;
11. verify both source absence and archive presence.

Counts alone are weak evidence. The archive may contain the right number of files and still be missing the only irreplaceable one.

Evidence establishes recoverability; it does not itself authorize deletion. Confirm that the exact frozen set is covered by an explicit mandate before deleting it. Reproducible caches can use a proportionate recovery/rebuild path rather than this full archival protocol; preserve required authority and irreplaceable evidence.

## 8. Put security boundaries outside the model

A useful minimum assumption for tool-using agents is:

> Assume the model can be steered. Put the real boundary outside the model.

Prompts are not an authorization system. A capable model can still be manipulated by hostile documents, websites, messages, tool descriptions, or retrieved text.

Real controls include:

- least-privilege credentials;
- narrow, parameter-bound tools;
- separation of low-trust ingestion from privileged execution;
- exact approval binding for consequential actions;
- deterministic validation around model decisions;
- immutable or append-only evidence;
- synthetic adversarial testing.

NIST’s work on agent hijacking shows why adaptive and repeated evaluation matters: one failed attack does not establish a reliable boundary.[5]

Simon Willison’s “lethal trifecta” provides a compact threat model: private data, untrusted content, and external communication become dangerous when combined in one agentic system.[6] OWASP’s AI Agent Security Cheat Sheet addresses related risks including prompt injection, tool abuse, excessive autonomy, sensitive-data exposure, and inadequate human oversight.[7]

For mutable sources, attach the checked version or retrieval date, authority and applicability. Top-k retrieval absence does not prove absence from the corpus or establish the latest event; refresh decision-relevant current facts.

## 9. Convert experience into procedural competence

A long-running assistant should improve through skills, not through uncontrolled prompt accumulation.

Use the appropriate store:

- memory for compact durable facts;
- skills for reusable procedures;
- documents for rich domain knowledge;
- session history for chronology and raw evidence;
- runtime state for locks, cursors, manifests, and receipts.

The always-loaded stores are the scarcest and the least forgiving. Identity, topology, and memory files each have a character cap, and overflow fails quietly: an identity file past its cap loses its middle, and a memory store past its limit keeps loading but refuses every new fact, with nothing louder than a log line; memory is also frozen at session start. Layer accordingly: identity and voice in the persona file, channel and ownership invariants in a compact topology file, only pre-lookup facts in memory, procedures in skills, and rich material in notes. A fact promoted into an always-loaded store displaces another one, so promotion should pass an explicit retention test and every store should be measured against its cap mechanically: identity and topology files before each deploy, which refuses on overflow, and memory in a regular health sweep. The practical layering, size guards, and sync rules are in [Identity, Memory and Context](../guides/identity-memory-context.en.md).

A strong skill-development loop is:

```text
real task
→ observed failure modes
→ successful procedure
→ reusable skill
→ fresh-context test
→ later correction
→ skill update
```

The skill should preserve the method’s essence rather than every historical incident. Its description must explain when to load it. Its verification should reflect the real outcome. If later work exposes a missing step or false assumption, patch the skill instead of merely remembering the embarrassment.

Hermes documents skills as progressively disclosed procedural packages.[8] Anthropic’s authoring guidance similarly emphasizes concise triggering descriptions, supporting resources loaded on demand, appropriate degrees of freedom, and iterative testing.[9]

## A compact operating protocol

Before trusting a tool-using agent with consequential work:

1. Identify the canonical source and semantic owner.
2. Define the intended consequence and named failure scenarios.
3. Separate preparation from commitment.
4. Bind authorization to the exact target, payload, and scope.
5. Exercise the authorized path; name any unverified layers.
6. Read the resulting state back independently.
7. Preserve evidence and unresolved ambiguity.
8. Convert repeated successful procedures into maintained skills.
9. Keep human or explicitly delegated selection before canonization.

This deliberately unglamorous protocol is what keeps an agent useful after the demo.

## Sources

[1] https://alistair.cockburn.us/hexagonal-architecture — Hexagonal Architecture
[2] https://www.adelard.com/asce/cae — Claims, Arguments and Evidence
[3] https://scsc.uk/gsn-standard — Goal Structuring Notation Standard
[4] https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs — Making retries safe with idempotent APIs
[5] https://www.nist.gov/news-events/news/2025/01/technical-blog-strengthening-ai-agent-hijacking-evaluations — Strengthening AI Agent Hijacking Evaluations
[6] https://simonwillison.net/2025/Jun/16/the-lethal-trifecta — The lethal trifecta for AI agents
[7] https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html — AI Agent Security Cheat Sheet
[8] https://hermes-agent.nousresearch.com/docs/guides/work-with-skills — Working with Skills
[9] https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices — Skill authoring best practices
