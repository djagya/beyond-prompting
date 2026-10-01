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
- The linked fork evolves independently; no claim that its default branch matches a deployed build or that all changes remain absent upstream is made.
- The hardening guide is English; the readings, onboarding, setup, operating loops and weekly guide have paired EN/RU versions. Procedural skills are English.

## Current evidence limits

The maintenance pass read all originally tracked files. Main research theses were retained; the Gao token-cost statement was made qualitative because its prose ranges do not describe every row of its own Table 3. Selected authoritative documentation and native CLI help were checked. Local fork help is not upstream installation proof.

No foreign agent deployment, skill installation, backup restore, credential rotation, provider write-denial test or production hardening was executed. A link may be structurally valid while retrieval is blocked or its future content changes. Record unresolved checks; never replace them with fabricated PASS.
