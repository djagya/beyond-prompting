# Validation and Compatibility

This is an independent reference collection, not a tested universal deployment bundle.

## Repository checks

From a local checkout, with Python and PyYAML already available:

```bash
python scripts/validate.py
```

The validator performs no network calls or target writes. It enumerates documentation, verifies relative links, checks skill frontmatter and self-contained skill references, and scans public text for selected private-identifier patterns. `git diff --check` checks whitespace separately. These checks do not prove semantic correctness, secret absence, safe runtime behavior or production acceptance. Do not install dependencies silently to run a read-only check.

## Adoption checks

Use the synthetic cases in the [English](agent-start.en.md) or [Russian](agent-start.ru.md) entry guide. A fresh-context response is a behavioral canary, not a live security assessment. Preserve the exact package revision, scenario and observed decision privately when judging it. Verify target-specific execution only after the correct mandate, with disposable resources where writes may occur.

## Compatibility boundaries

- The readings and operating contracts are portable practice, not upstream guarantees.
- Hardening CLI/config examples require a supported Hermes target version. Check current [official security documentation](https://hermes-agent.nousresearch.com/docs/user-guide/security) and target `--help` before application.
- `hermes backup --quick` is critical-state only; full backup may have automatic retention deletion. Project and external state require their own protection.
- Supported unattended API/webhook sessions have a separate `approvals.unattended_mode`; unsupported versions need an explicitly verified alternative boundary.
- Skill installation is optional. Read procedures directly when the host lacks a compatible installer. Inspect the exact source and installer behavior before admitting executable extensions.
- Dangerous-command checks are documented as skipped on container/sandbox terminal backends; `approvals.*` settings are evidence of enforcement only for the effective backend actually in use.
- `hermes update` is the Git/source route; image-owned installs are updated by replacing a pinned image (current Docker documentation).
- The linked fork evolves independently; no claim that its default branch matches a deployed build or that all changes remain absent upstream is made.
- The hardening guide is English; the readings, onboarding, setup patterns, reference setup, operations, identity/memory/context, coding-agent operator, operating loops and weekly guide have paired EN/RU versions. Procedural skills and templates are English.
- Several setup and operations statements are practice from one Docker deployment that tracks a fork, marked *practice*, *observed* or *confirm on your version* where the official documentation does not state them (for example implicit MCP attachment to cron jobs, named-profile default inheritance, list-typed `config set` values, the `ARCHITECTURE.md` prompt slot, secret-manager budgets). Treat them as hypotheses to probe on the target.
- `templates/compose.example.yaml` is an annotated example, not a tested deployment bundle; its sizing values come from one host.

## Current evidence limits

The maintenance pass read all originally tracked files. Main research theses were retained; the Gao token-cost statement was made qualitative because its prose ranges do not describe every row of its own Table 3. Selected authoritative documentation and native CLI help were checked. Local fork help is not upstream installation proof. A second review pass (2026-10) re-checked backend approval scope, image-owned updates, `browser.restrict_evaluate`/`browser_exec` and lifecycle-canary isolation against cached official Security, Docker and Browser pages and local CLI help; no live retrieval or runtime test was performed.

A third pass (2026-10) folded operational lessons from a private deployment's maintenance docs, retrospectives and operator sessions into the hardening guide and the new setup, operations, identity and coding-agent guides and skills; incidents were generalized and private identifiers removed. Version-sensitive keys were checked against a cached snapshot of the official documentation; where the snapshot and practice disagreed (for example multiplexed gateways being opt-in), the documented behavior is stated and the observed behavior is labeled.

No foreign agent deployment, skill installation, backup restore, credential rotation, provider write-denial test or production hardening was executed. A link may be structurally valid while retrieval is blocked or its future content changes. Record unresolved checks; never replace them with fabricated PASS.
