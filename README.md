# Beyond Prompting

## The Agentic Practice

Field notes and practical methods for working with AI: outcomes, tools, workflows, verification, authority, and reusable skills.

**Independent publication by Danil. This is not official Nous Research or Hermes Agent documentation and is not endorsed by Nous Research.**

Beyond Prompting is about turning intentions into bounded, verifiable outcomes with AI—not collecting prompt formulas. The methods here are drawn from sustained work with a customized [Hermes Agent](https://hermes-agent.nousresearch.com/) and are intended to apply beyond Hermes to tool-using AI systems more broadly.

## Readings

### 1. Beyond Prompting

What should an experienced AI user learn next?

- [English — Beyond Prompting: Operational Literacy for Working with AI](readings/beyond-prompting.en.md)
- [Русский — За пределами промптинга: операционная грамотность в работе с ИИ](readings/beyond-prompting.ru.md)

### 2. From Capability to Authority

Methods refined through operating a long-running, tool-using AI assistant across software, research, automation, publishing, and external systems.

- [English — From Capability to Authority: Principles from Operating Hermes](readings/principles-from-hermes-in-practice.en.md)
- [Русский — От способности к полномочию: принципы эксплуатации Hermes](readings/principles-from-hermes-in-practice.ru.md)

## Field guides

### Hardening Hermes Agent

A practical security and operations baseline for personal, friend, and company deployments:

- [Human guide — Hardening Hermes Agent](guides/hermes-hardening.md)
- [Agent procedure — Hermes Hardening skill](skills/hermes-hardening/SKILL.md)
- [Repository instructions for AI agents](AGENTS.md)

The guide covers authority boundaries, profiles and their limits, credentials, tools, approvals, gateway exposure, MCP and extension trust, unattended jobs, recovery, updates, and evidence-backed acceptance tests.

To install the reusable skill in Hermes:

```bash
hermes skills install djagya/beyond-prompting/skills/hermes-hardening
```

Then start with a read-only assessment:

```text
/hermes-hardening Assess this Hermes deployment. Do not change state.
```

Installing or reading the repository makes the procedure available; it does **not** authorize deployment changes. To use the repository as project context, clone it and work inside the checkout so a compatible agent can discover the root [`AGENTS.md`](AGENTS.md).

## Conventions for agents

This repository uses two complementary open conventions:

- [`AGENTS.md`](https://agents.md/) for project-level instructions loaded from a repository;
- [`SKILL.md`](https://agentskills.io/specification) for a portable, explicitly invoked procedure.

A bare repository URL is reference material, not executable authority. Agents should default to assessment when the requested action class is ambiguous.

## Authorship and provenance

Danil and Sera developed these materials from their shared record of practice. Sera, a customized Hermes-based AI assistant, assisted with synthesis, drafting, translation, editing, and procedural validation. Danil is responsible for the published text.

The labels **selection before canonization** and **Semantic Ownership Inversion** name patterns observed in this practice. No claim of first discovery or priority is made. The underlying methods also draw on established assurance-case, distributed-systems, software-architecture, and AI-security practice, cited in the readings.
