# Control Registry: Which Hardening Applies to This Deployment

**Reference material. The registry classifies and recommends; it never changes your system. Applying a control is a separate, authorized act.**

The [registry](../registry/README.md) holds atomic hardening controls for Hermes Agent deployments and a deterministic evaluator that answers one question: given facts about a deployment, which controls apply, which do not, and which cannot be decided from the facts at hand.

## What it gives you

- A stable vocabulary: each control is one file with an id, a predicate stating when it applies, variants, verification, rollback and failure modes.
- Deployment profiles (workstation, private server, messaging gateway, public surface, team runtime, privileged operator) that compose by reference instead of copying.
- A report that separates decided outcomes from decisions a human must make, and never hides a missing fact behind a clean pass.

## Documents and layout

`registry/` contains the manifest (`registry.json`), JSON Schemas, one control per file under `controls/`, profiles under `profiles/`, examples, and a unittest suite. The manifest pins the registry version, the reference date (`as_of`) and the maximum verification age in days; freshness is judged against the supplied as-of date, never against your clock.

## Seed content and synthesis provenance

Two kinds of controls live side by side, marked by `provenance.origin`. The seed controls (FMR-001 through FMR-014) and all test inventories are synthetic examples: their version ranges, dates and scenarios are illustrative placeholders, not claims about any specific Hermes release or incident. Controls from FMR-015 onward are operational-practice synthesis (`origin: synthesis`): practices generalised from recorded operational use with all private detail removed. A synthesis control describes a practice that proved itself in operation; it does not cite a publicly verifiable incident, and it says so in its own references. Synthetic fixtures exercise both kinds; they never prove that a historical incident occurred.

## Applicability statuses

Every control in the resolved set receives exactly one status:

- `required` — applies and is baseline for the selected profile(s).
- `recommended` — applies, but the profile marks it optional.
- `not_applicable` — the predicate is false for this deployment.
- `unsupported` — the Hermes version is outside every verified range.
- `needs_decision` — a fact is missing, verification is stale, or the control conflicts with another applicable control; the reasons name the exact facts or ids involved.

## Missing facts are never a silent no

Predicates use three-valued logic. An absent or mismatched inventory fact is unknown, not false. Any control that cannot decide becomes `needs_decision` listing the fact path it needed. An incomplete inventory therefore reads as an explicit question list, which is exactly what you want before hardening a real system.

## Version ranges carry an evidence basis

Every range in `hermes_versions.verified` states how it was established in a required `basis` field. `exercised` means the control's behaviour was actually exercised on builds inside the range. `documentation` means the surrounding procedures or official documentation were read against those builds — no behavioural verification is claimed. `illustrative` marks a synthetic placeholder on a synthetic seed control — no compatibility claim at all. The report shows the strongest basis covering your Hermes version as `version_basis` on each control, and adds a disclosure reason whenever an applicable control is in range only on documentation or illustrative evidence. Outside every range the control stays `unsupported`, exactly as before: the basis changes what a pass claims, never whether a gap is hidden. Today no control in this registry carries an exercised range — seed controls are illustrative and the practice controls are documentation-reviewed — so no report asserts exercised platform compatibility for any Hermes version.

## Determinism contract

Evaluation is a pure function of the registry bytes, the profile ids, the inventory bytes and the as-of date. Reports carry digests of both inputs; the same inputs always yield byte-identical output. Evaluation itself reads no clock, inspects no host state and writes nothing; the CLI writes a report file only when you explicitly pass `--out`.

## Running the evaluator

```sh
python3 scripts/applicability.py validate-registry
python3 scripts/applicability.py evaluate \
    --profile messaging-gateway \
    --inventory my-inventory.json \
    --as-of 2026-10-17
```

Repeat `--profile` to union several profiles. Exit code 0 means a report was produced; 1 means the registry or inventory failed validation; 2 is a usage error. Validate the registry itself before trusting any report from it.

## Reading a report

Start with the summary counts, then read `needs_decision` entries first — they carry the facts you must supply or confirm. Check `resolution` when a profile references a deprecated control: the entry names the successor that was evaluated instead. `registry_digest` and `inventory_digest` let you pin a report to the exact inputs it was made from.

## Recording evidence

When you verify a control on a real deployment, record what you did under the evidence schema: control, variant, status, date, method, result summary, redaction statement, artifacts with digests. Keep values and secrets out; the record states what was checked and what was redacted, nothing more. See `registry/examples/evidence-example.json`.

## Extending the registry

Add one control per file with the next free id, reference it from the relevant profiles with a baseline choice, declare conflicts on both sides, and use supersession (deprecated plus `superseded_by`) instead of editing a control in place. Profiles keep referencing the old id; resolution is transparent and recorded. Run `validate-registry` and the test suite before committing. The full workflow lives in [the registry README](../registry/README.md).

## What this registry never does

It never executes a control, never contacts your deployment, never reads your clock or host, and never treats a missing fact as compliance. Recommendation and application stay separate acts with separate owners.
