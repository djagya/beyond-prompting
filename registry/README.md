# Hardening Control Registry

An atomic registry of hardening controls for Hermes Agent deployments, plus a
deterministic evaluator that decides which controls apply to a given
deployment. The registry describes and classifies; it never executes
anything. Applying a control is always a separate, authorized act.

## Layout

```text
registry/
  registry.json              manifest: registry version, reference date, freshness policy
  schemas/                   JSON Schemas (Draft 2020-12) for every document kind
  controls/                  one atomic control per file, file stem == id lowercased
  profiles/                  named deployment profiles, composed by reference
  examples/                  example evidence record and generated report
  tests/                     unittest suite, fixtures, negative fixtures
```

## Document kinds

| Kind | Schema | Purpose |
| --- | --- | --- |
| Control | `schemas/control.schema.json` | One hardening measure: what it protects, when it applies (predicate), variants, verification, rollback, failure modes, version ranges with an explicit evidence basis, conflict and supersession links. |
| Profile | `schemas/profile.schema.json` | A named set of control references with a baseline disposition per reference. Profiles extend other profiles; they never copy control bodies. |
| Inventory | `schemas/inventory.json` | Closed-world facts about one deployment. No free text, no secrets, no identifiers beyond the schema. |
| Report | `schemas/report.schema.json` | Output of the evaluator: per-control status, reasons, digests, resolution trail. |
| Evidence | `schemas/evidence.json` | A verification artifact for one control variant, with an explicit redaction statement. |
| Registry | `schemas/registry.schema.json` | The manifest itself. |

The manifest pins `registry_version`, `as_of` (the reference date all
freshness decisions are made against) and `max_verification_age_days`. There
is no wall-clock reading anywhere in the evaluator.

## Applicability statuses

For each control the evaluator produces exactly one status:

- `required` — the predicate is true and the profile marks the control baseline.
- `recommended` — the predicate is true and the profile marks it non-baseline.
- `not_applicable` — the predicate is false for this inventory.
- `unsupported` — the deployment's Hermes version falls outside every
  verified range for the control.
- `needs_decision` — a fact is missing, verification is stale, or the control
  conflicts with another applicable control. The reasons name the exact
  undecidable facts.

Precedence (first match wins): `not_applicable` > `unsupported` >
`needs_decision` (missing fact) > `needs_decision` (stale verification) >
`needs_decision` (live conflict) > `required`/`recommended`.

## Missing facts are never a silent no

Predicates evaluate under three-valued logic: true, false, or unknown. A
missing or type-mismatched inventory fact is unknown, never false. Any
control whose predicate cannot decide yields `needs_decision` and names the
facts it needed. A deployment that omits facts therefore surfaces as an
explicit decision list, not as an accidentally clean report.

## Version range evidence basis

Every range in a control's `hermes_versions.verified` carries a required
`basis` declaring how the range was established:

- `exercised` — the control's behaviour was actually exercised on builds
  inside the range.
- `documentation` — the surrounding procedures or official documentation
  were read against those builds; no behavioural verification is claimed.
- `illustrative` — a synthetic placeholder on a synthetic seed control; no
  compatibility claim at all.

Each report result records `version_basis`: the strongest basis among the
ranges containing the inventory's Hermes version (`out_of_range` outside
every range, `unknown` when the inventory omits the version). A result whose
applicability reading depends on in-range membership on a documentation or
illustrative basis carries an explicit `hermes_version.basis` disclosure
reason; the disclosure never changes a status, and `unsupported` on an
out-of-range version behaves exactly as before. At registry 0.3.0 no control
carries an exercised range — seed controls are illustrative, practice
controls are documentation-reviewed — so no report from this registry
asserts exercised platform compatibility for any Hermes version.

## Determinism contract

Evaluation is a pure function of four inputs: the registry bytes, the
selected profile ids, the inventory bytes, and the supplied `--as-of` date.
The report records a digest of the registry and of the inventory; identical
inputs always produce byte-identical reports. Evaluation itself writes
nothing, reads no clock, and inspects no host state; the CLI writes a report
file only when `--out` is explicitly given.

## Running the evaluator

```sh
python3 scripts/applicability.py validate-registry
python3 scripts/applicability.py evaluate \
    --profile public-surface \
    --inventory registry/tests/fixtures/inventories/public-gateway.json \
    --as-of 2026-10-17
```

`--profile` may repeat; results are the union of the resolved control sets
with baselines OR-ed together. `--format markdown` renders the same report
as deterministic, escaped Markdown instead of JSON. `--out FILE` writes the
report instead of stdout. `--registry DIR` evaluates another registry copy.
Exit codes: 0 success, 1 validation or evaluation failure, 2 usage error.

Two reports can be compared with their input context bound:

```sh
python3 scripts/applicability.py compare report-a.json report-b.json [--format markdown]
```

Both inputs are validated against the report schema. The comparison records,
per context field (registry version and digest, inventory digest, profiles,
as-of, freshness policy), whether the two reports agree, and lists
per-control status and version-basis transitions with reason additions and
removals in deterministic order. When any context field differs the result
carries `same_context: false` and an explicit warning: status differences
between mismatched inputs reflect changed inputs and are not, by themselves,
evidence of a security regression.

All JSON inputs (inventories and reports) are read under explicit limits: a
4 MiB size cap, rejection of duplicate object keys (contradictory facts are
an input error, never a silent last-wins choice), and rejection of malformed
or pathologically nested documents, all with exit code 1 and a stable error
code.

Run the suite with:

```sh
python3 -m unittest discover -s registry/tests
```

The unit suite, `validate-registry` and the repository structural checks
also run on every push and pull request via
`.github/workflows/registry-checks.yml`.

## Validation checks

`validate-registry` enforces, beyond JSON Schema conformance: symmetric
conflicts, no self-conflicts, conflict targets exist; supersession links are
consistent, acyclic, and never point at retired controls; verification dates
are neither stale nor in the future relative to the manifest `as_of`;
verified version ranges are ordered and every range declares its evidence
basis; profiles form an extends DAG — shared
ancestors reached through different children compose once (first-visit
order) and are not cycles, while a profile reaching itself through extends
is rejected — with no control declared more than once inside one
composition (same control with opposing baselines in independent parents is
rejected, never silently merged) and no references to retired controls;
file stems match document ids.

## Extending the registry

1. Add `controls/fmr-0NN.json` (next free id; stem must match the id).
2. Add the control to the relevant profiles by reference, with a baseline.
3. If it replaces an old control, mark the old one `deprecated` with
   `supersession.superseded_by` pointing to the new id; profiles keep
   referencing the old id and are resolved transparently.
4. If it conflicts with another control, add the link on both sides.
5. Run `validate-registry` and the test suite before committing.

See `guides/control-registry.en.md` / `guides/control-registry.ru.md` for the
operator walkthrough.
