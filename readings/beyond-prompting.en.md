# Beyond Prompting

## Operational literacy for working with AI

**Independent field note; not official Nous Research or Hermes Agent documentation.**

Experienced AI users have little to gain from another collection of clever prompts. Prompting is only the conversational surface of a broader discipline: **operational literacy**.

> Operational literacy is the ability to turn an intention into a bounded, verifiable change in reality with the help of AI.

Generative literacy asks whether a model can produce a convincing answer, image, plan, or program. Operational literacy asks harder questions:

- What outcome are we trying to produce?
- What sources and tools does the system need?
- What may it change, and what remains forbidden?
- How will failure appear?
- What evidence will prove that the work succeeded?

This distinction matters as soon as AI touches files, code, browsers, email, cloud services, schedules, money, or other persistent state.

## 1. Specify outcomes, not vibes

A useful instruction establishes a work contract:

```text
Outcome
Relevant context and sources
Constraints and non-goals
Permitted actions
Definition of done
Required evidence
```

Compare:

> Improve the deployment.

with:

> Assuming deployment is explicitly authorized and a rollback path is available, deploy the change through the real runtime path, preserve the existing service, exercise the changed behavior, and show that the running process loaded it.

The second instruction does not micromanage implementation. It states what must become true.

## 2. Learn verification, not just generation

A plausible result is not necessarily a real result.

- A file can be correct while the running process still uses an older copy.
- An API can return success while the external state remains unchanged.
- A test can pass while exercising a mock instead of the real path.
- A citation can exist without supporting the sentence beside it.

Ask the agent to distinguish observation, inference, hypothesis, external claim, and direct evidence.

For consequential work, require it to execute the real path and independently read the result back. “The command exited successfully” is evidence about the command, not automatically about the intended consequence.

## 3. Develop taste and editorial judgment

As AI lowers production costs, selection becomes the scarce skill: deciding what is generic, which detail carries the work, what should be removed, when completeness has become clutter, and when a polished answer rests on the wrong frame.

A technically valid artifact can still be aesthetically or strategically dead. Taste governs what deserves to exist.

## 4. Acquire basic tool literacy

Using agents well requires enough technical literacy to inspect their work, not a career in software engineering.

The most useful basics are files and directories, Markdown, Git and GitHub, terminal fundamentals, JSON, spreadsheets, basic SQL, HTTP APIs, and a little Python or JavaScript.

The point is not memorizing syntax. It is understanding the shape of the system: where information lives, what an operation changes, and how to inspect the result.

## 5. Design workflows before pursuing autonomy

A repeatable AI workflow often has a simple shape:

```text
input → inspect → decide → act → verify → record
```

Use deterministic software for deterministic responsibilities: enumeration, schema validation, hashes, locks, cursors, retries, state transitions, exact allowlists, and health checks.

Use the model where interpretation is required: classification, synthesis, editorial judgment, ambiguity resolution, and context-dependent choice.

A strong arrangement is:

```text
deterministic preflight
→ bounded model judgment
→ deterministic commit and verification
```

Anthropic’s account of effective agents reaches a similar conclusion: successful systems often use simple, composable workflows instead of beginning with elaborate autonomous frameworks.[1]

## 6. Understand authority and blast radius

Do not give one model unrestricted access to private data, hostile external content, credentials, and outward communication merely because its prompt asks it to behave.

Separate:

- **preparation:** research, drafting, calculation, staging;
- **commitment:** sending, publishing, paying, deleting, deploying, signing.

Preparation can often be broad and reversible. Commitment should be narrow, parameter-bound, explicitly authorized, and independently verifiable.

Simon Willison’s “lethal trifecta” describes the danger of combining private-data access, exposure to untrusted content, and external communication in one agentic system.[2] The practical response is architectural: remove or constrain at least one leg rather than trusting probabilistic prompt obedience.

## 7. Turn repeated experience into skills

A long-running assistant should not accumulate one enormous prompt containing everything that has ever happened.

Use different stores for different kinds of continuity:

- **memory:** compact durable facts;
- **skills:** reusable procedures;
- **documents:** rich domain knowledge;
- **session history:** chronology and raw evidence;
- **runtime state:** cursors, locks, manifests, and receipts.

A skill should emerge from real work:

```text
difficult task
→ observed failure modes
→ successful procedure
→ reusable skill
→ fresh-context test
→ later correction
→ skill update
```

Hermes implements skills through progressive disclosure: the system first sees compact metadata, loads the main procedure only when relevant, and opens supporting references only when needed.[3] Anthropic’s skill-authoring guidance emphasizes the same economy: concise instructions, explicit triggering conditions, appropriate degrees of freedom, and testing against real usage.[4]

## A practical progression

For someone already comfortable with AI:

1. Choose one recurring real problem.
2. Complete it interactively several times.
3. Record where the model lacked context or produced false confidence.
4. Give it stable source material and explicit acceptance criteria.
5. Add tools only where they enable the real outcome.
6. Require execution and independent verification.
7. Automate only the portions that have become stable.
8. Preserve human judgment where errors are expensive or meaning is still being chosen.
9. Extract the successful method into a reusable skill.
10. Update the skill when reality disproves it.

## What not to learn first

Postpone these until a concrete problem demands them:

- libraries of magical prompt phrases;
- multi-agent swarms;
- vector databases for every project;
- fine-tuning without a dataset and evaluation;
- elaborate autonomy before one workflow works reliably;
- model rankings that will be stale next month.

The durable AI skill is not knowing how to make a model sound intelligent. It is knowing how to arrange context, tools, authority, and evidence so that intelligence can answer to reality.

## Sources

[1] [Anthropic — Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
[2] [Simon Willison — The lethal trifecta for AI agents](https://simonwillison.net/2025/Jun/16/the-lethal-trifecta)
[3] [Hermes Agent — Working with Skills](https://hermes-agent.nousresearch.com/docs/guides/work-with-skills)
[4] [Anthropic — Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
