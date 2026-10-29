---
name: simplify-system
description: Read-only architecture review of one behaviour that grew too many mechanisms, aiming at a single source of truth, one decision path and explicit state machines, with measured efficiency, a switch-guarded migration plan and owner decisions.
metadata:
  hermes:
    tags: [architecture, simplification, single-source-of-truth, review, state-machine]
---

# Simplify a System

Use this procedure for one *behaviour*, not one file. A behaviour is the question the system answers, for example "what is this item worth now, and may we use it?". The caller names it; if they don't, ask for it in one line.

Use it when the owner asks to simplify, consolidate or harden a system, or says "single source of truth", "too many rules" or "why so many states". Don't use it for cleaning up a diff; a code-simplifier pass does that better.

This is a review. Nothing is edited, committed, deployed or sent, and no production host or paid API is touched. Run it at the highest reasoning effort available.

## 0. Frame

- Write the behaviour as one question, and list the incidents that motivate the review with their numbers: money lost, blind time, churn, pages.
- Read the intent: the design or experiment notes that built each mechanism, the owner's standing rules (repository instructions, policy files, memory) and the release history. Quote every owner rule the system must keep. Those rules are constraints, not candidates for deletion.
- Pin the code: the branch and head, plus every open branch that touches the system. Work still in flight has to fold into the plan.

## 1. Map, then verify

Split the mapping into at most three read-only workers, one per axis. Skip the split when one reader is enough.

- **Values:** where the answer is computed and cached (quotes, models, ledgers, local estimators).
- **Lifecycle:** every hold, ban, probation, timer and persistence, and what happens after a restart.
- **Decisions and blame:** every path that adjusts the answer after new evidence: who is blamed, on what basis, and which consumer acts on it.

Each worker returns its findings as text in one table:

| # | State | Written (file:line) | Read (file:line) | Lifetime / expiry | Persisted? | After restart |
|---|---|---|---|---|---|---|

Then check every claim that a later fix depends on yourself:

- Confirm the code says what the worker reported.
- Confirm the production path actually reaches that code: who calls it, with what arguments, and whether a flag or a builder makes it dead.
- Write a small probe for any claim a fix depends on.

## 2. Find duplicated and conflicting truths

Run this checklist against the map and cite file:line for each hit.

1. **One fact stored N times.** Look for several caches of the same value, or mirrors on two threads or processes, that disagree after a restart.
2. **Two bases for one comparison.** For example, a figure from moment A set against a figure from moment B, or a model value set against a signed or committed value.
3. **One word, several meanings.** "Held", "near", "fresh" or "stale" defined in several places with different thresholds.
4. **Two paths blaming the same evidence.** This shows up as double counting, or as one rule running before the rule that should have explained the evidence.
5. **Derived values cached instead of recomputed,** and constants defined more than once.
6. **Information leakage.** The same design decision is visible in several modules. Also look for:
   - pass-through layers;
   - temporal decomposition: code split by *when* something happens rather than by *what* it does;
   - shallow modules whose interface is as complex as their body.
7. **States with no exit.** A ban with no retest, a probation with no timeout, a permanent lockout, or a circular dependency where X is needed to learn X.
8. **Memory-only state** that matters across a restart.
9. **Dead or unreachable branches** that tests still pass, because the test hands in arguments production never sends.
10. **Repeated work.** The same decode, walk, scan or publish runs several times per event, especially on a hot thread.
11. **The thrown-away measurement.** Ask what the system already observes exactly but then guesses at anyway: for example, logs in a simulation answer, a receipt, or a response field the code ignores. This is often the biggest simplification available. Measure; don't infer.

## 3. Measure efficiency

- Profile the existing replays or tests that exercise the hot path (for example `python -m cProfile -o out.prof`, then `pstats` sorted by cumulative time). Report calls per event and each function's share of the hot turn.
- Time micro-operations at realistic and pessimistic sizes. Name every size you don't know, such as the production row count.
- Count external cost per event and per day against its budget: RPC or API calls, metered units, database scans.
- Label everything you didn't measure as an estimate.

## 4. Design the simpler system

- **One owner per fact.** Name the single store for the answer: its key, its sources, their order of precedence, and the one read function that replaces all the others.
- **One attribution path.** Evidence becomes verdicts, and verdicts go to exactly the consumers that need them. Each is computed once, on one basis.
- **One explicit state machine for availability.** Give a table of states, with whether each state is listed or used, the transitions and their triggers, the timers (first gap, backoff, cap), persistence, and what happens at a restart. Every exclusion has a retest and a cap. Only exclusions seeded in code are permanent.
- **Self-healing.** When a value is disputed, re-read the evidence behind it, bounded and rate-limited, instead of waiting for a restart.
- **Robustness.** Say what fails closed (money, sending, irreversible actions) and what fails open (holds based on inferred evidence). Keep hot-thread work bounded and push heavy work to a cold side.
- **A deletion table** with three columns: deleted, merged into, kept. Restate the owner rules that stay unchanged, quoted.

## 5. Attack your own design

List what could get worse:

- a transient state recorded as truth;
- new parsing risk;
- a single point of failure;
- a shared endpoint starved by the new work;
- changed test expectations that hide a regression.

Give each a mitigation: a per-consumer switch, a shadow comparator, or a fallback to today's path on any error.

## 6. Migration plan

Break the change into small, separately releasable steps. Each step sits behind a switch whose "off" setting reproduces today's behaviour, and the steps are ordered by value against risk. For each step, give:

- what it does;
- its switch;
- the tests or replays that pin behaviour (bit for bit where possible; otherwise list each expected change with its reason);
- what it depends on.

A typical order:

1. Record-only measurement plus a shadow comparator.
2. The cheap efficiency fixes.
3. The state machine in shadow.
4. The state machine live.
5. Deletion of the old paths after two weeks green.

Fold in each open branch so that steps don't conflict.

## 7. Report

Lead with what is blocked or undecided, then give the short answer. Then:

- **Fix now:** bugs and costs verified along the way, each with its proof (a probe, a profile, a log line), shippable before any redesign.
- The map (sections 1–2), the measurements (3), the design (4–5) and the plan (6).
- **Owner decisions:** short lettered options with a recommendation and the real effect of each, in money, risk or time, restated in plain words.
- **Method:** the workers used, the probes, the profiles, and what was estimated rather than measured.

Write the full report to a durable path inside the project, not only to a temporary scratch area, and return a summary.

## Sources this procedure draws on

- Behaviour-preserving refactoring, pinned by tests before anything changes: [code-simplification](https://claudeskills.info/skills/addyosmani/agent-skills/code-simplification/).
- Redundant state and cached derived values as explicit review targets: [code-simplifier](https://skills.sh/paulirish/dotfiles/code-simplifier).
- Module depth and information leakage as the lens: John Ousterhout, *A Philosophy of Software Design* ([summary](https://danlebrero.com/2021/02/24/philosophy-of-software-design-summary/)).
- Scope discipline, deciding what one system is before mapping it: [skills architecture](https://hatchworks.com/blog/claude/skills-architecture/).

The rest is practice from a production review: the three-axis map, live-path verification, the thrown-away-measurement question, and the switch-guarded migration. It is practice, not an official method.
