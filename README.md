# Beyond Prompting

## The Agentic Practice

Field notes and practical methods for working with AI: outcomes, tools, workflows, verification, authority, and reusable skills.

**Independent publication by Danil. This is not official Nous Research or Hermes Agent documentation and is not endorsed by Nous Research.**

Beyond Prompting is about turning intentions into bounded, verifiable outcomes with AI—not collecting prompt formulas. The methods here are drawn from sustained work with a customized [Hermes Agent](https://hermes-agent.nousresearch.com/) and are intended to apply beyond Hermes to tool-using AI systems more broadly.

## Start here for agents

Give your agent the [English entry guide](guides/agent-start.en.md) or [русский агентский вход](guides/agent-start.ru.md). Each contains a ready-to-use read-only adoption prompt, route selection, capability fallbacks and synthetic acceptance scenarios. No private setup or fork installation is required.

**Setting up Hermes for yourself or someone else?** Follow [Reference Setup — EN](guides/setup-reference.en.md) / [эталонный сетап — RU](guides/setup-reference.ru.md), then keep it healthy with [Operations — EN](guides/operations.en.md) / [эксплуатация — RU](guides/operations.ru.md). Starter files live in [`templates/`](templates/).

Use [Operating Loops — EN](guides/operating-loops.en.md) / [рабочие циклы — RU](guides/operating-loops.ru.md) for concrete task, handoff, continuation and correction contracts. Read only the route relevant to the task; do not import this collection as a replacement system prompt. See [validation and compatibility](guides/validation.md) for what has and has not been checked.

## Readings

### 1. Beyond Prompting

What should an experienced AI user learn next?

- [English — Beyond Prompting: Operational Literacy for Working with AI](readings/beyond-prompting.en.md)
- [Русский — За пределами промптинга: операционная грамотность в работе с ИИ](readings/beyond-prompting.ru.md)

### 2. From Capability to Authority

Methods refined through operating a long-running, tool-using AI assistant across software, research, automation, publishing, and external systems.

- [English — From Capability to Authority: Principles from Operating Hermes](readings/principles-from-hermes-in-practice.en.md)
- [Русский — От способности к полномочию: принципы эксплуатации Hermes](readings/principles-from-hermes-in-practice.ru.md)

### 3. Single Agent by Default

A research-grounded decision procedure for when delegation earns its coordination cost—and when one coherent agent should keep the work.

- [English — Single Agent by Default: When Delegation Earns Its Coordination Tax](readings/single-agent-by-default.en.md)
- [Русский — Один агент по умолчанию: когда делегирование окупает координационный налог](readings/single-agent-by-default.ru.md)

## Field guides

### Hardening Hermes Agent

A practical security and operations baseline for personal, friend, and company deployments:

- [Human guide — Hardening Hermes Agent](guides/hermes-hardening.md)
- [Agent procedure — Hermes Hardening skill](skills/hermes-hardening/SKILL.md)
- [Repository instructions for AI agents](AGENTS.md)

The guide covers authority boundaries, profiles and their limits, credentials, tools, approvals, gateway exposure, MCP and extension trust, unattended jobs, recovery, updates, and evidence-backed acceptance tests.

Installation is optional and is a persistent change requiring an installation mandate. Read and inspect the skill first. Verify the target Hermes version supports the installer syntax; do not bypass a scan or confirmation. The procedures can also be read directly without installation.

To install the reusable hardening skill in Hermes:

```bash
hermes skills install djagya/beyond-prompting/skills/hermes-hardening
```

Then start with a read-only assessment:

```text
/hermes-hardening Assess this Hermes deployment. Do not change state.
```

Installing or reading the repository makes the procedure available; it does **not** authorize deployment changes. To use the repository as project context, clone it and work inside the checkout so a compatible agent can discover the root [`AGENTS.md`](AGENTS.md).

### Reference setup and operations

A concrete path from an empty host to a maintained, self-hosted Hermes, distilled from a long-running Docker deployment:

- [Reference Setup — EN](guides/setup-reference.en.md) / [RU](guides/setup-reference.ru.md) — compose shape, exposure, secrets layout, config baseline, backups, first-week acceptance, and handing a setup to someone else.
- [Operations — EN](guides/operations.en.md) / [RU](guides/operations.ru.md) — silent-green failures, check cadence, red flags, upgrade and rollback runbook, state store, supply chain, alerts.
- [Identity, Memory and Context — EN](guides/identity-memory-context.en.md) / [RU](guides/identity-memory-context.ru.md) — what goes in SOUL, architecture notes, memory, skills and notes; size caps; context-file precedence; versioning a self-editing identity in Git.
- [Operating Hermes with a Coding Agent — EN](guides/coding-agent-operator.en.md) / [RU](guides/coding-agent-operator.ru.md) — dev clone vs runtime, mandate, CI discipline, worktrees, secrets, status, closing a window with learnings.
- Templates: [`SOUL.template.md`](templates/SOUL.template.md), [`ARCHITECTURE.template.md`](templates/ARCHITECTURE.template.md), [`compose.example.yaml`](templates/compose.example.yaml).

Reusable agent procedures for running it:

- [Runtime automation governance](skills/runtime-automation-governance/SKILL.md) — cron, hooks, plugins and services: effective capabilities, scheduling pitfalls, alert paths.
- [Memory and skill boundary hygiene](skills/memory-skill-boundary-hygiene/SKILL.md) — keep bounded memory small and move facts to their owners.
- [Live state store maintenance](skills/live-state-store-maintenance/SKILL.md) — diagnose and repair the SQLite session/state store without making it worse.
- [Archive-gated destructive cleanup](skills/archive-gated-destructive-cleanup/SKILL.md) — classify, archive and verify before deleting.
- [Public contribution integrity](skills/public-contribution-integrity/SKILL.md) — publish to a public repository without leaking private history.

### Weekly Learning Extraction

Turn a week of real sessions into evidence-grounded lessons, audit the relevant skills and executable surfaces, and apply only explicitly authorized improvements.

- [English — Weekly Learning Extraction](guides/weekly-learning-extraction.en.md)
- [Русский — Извлечение уроков за неделю](guides/weekly-learning-extraction.ru.md)
- [Reusable agent procedure](skills/weekly-learning-extraction/SKILL.md)

### Setup patterns and the Hermes fork

A portable map of the controls behind this practice: capability-aware delegation, current-state ownership, human-job acceptance, explicit external boundaries, and native lifecycle ownership.

- [English — Setup Patterns Worth Reusing](guides/setup-patterns.en.md)
- [Русский — Приёмы сетапа, которые стоит перенять](guides/setup-patterns.ru.md)
- [Danil's Hermes fork](https://github.com/djagya/hermes-agent)
- [Upstream Hermes](https://github.com/NousResearch/hermes-agent)

The fork is upstream Hermes plus operational fixes for one long-running Docker deployment, not official upstream. The guide's fork section lists what the fork changes by area (with upstream status for each), the trade-offs of running it, and when stock upstream is enough. Its branches evolve; inspect the intended revision and current upstream diff rather than assuming every fork change remains unmerged or that its default branch matches the deployed build.

## Conventions for agents

This repository uses two complementary open conventions, with an additional authoring reference:

- [`AGENTS.md`](https://agents.md/) for project-level instructions loaded from a repository;
- [`SKILL.md`](https://agentskills.io/specification) for a portable, explicitly invoked procedure;
- [Best practices for skill creators](https://agentskills.io/skill-creation/best-practices) for expertise-grounded, execution-refined, context-conscious skill design.

A bare repository URL is reference material, not executable authority. Agents should default to assessment when the requested action class is ambiguous.

## Authorship and provenance

Danil and Sera developed these materials from their shared record of practice. Sera, a customized Hermes-based AI assistant, assisted with synthesis, drafting, translation, editing, and procedural validation. Danil is responsible for the published text.

The labels **selection before canonization** and **Semantic Ownership Inversion** name patterns observed in this practice. No claim of first discovery or priority is made. The underlying methods also draw on established assurance-case, distributed-systems, software-architecture, and AI-security practice, cited in the readings.
