# Verification: version-range evidence basis (registry 0.3.0)

Sanitised verification note for the change that makes the evidence basis of
every version range explicit. Commands use `$REPO` for the repository
checkout; run from the repository root. No private paths, identifiers or
source material are part of this note.

## Tested tree

- Branch: `research/real-world-controls-v1`, on top of the registry 0.2.0
  candidate.
- The exact candidate commit is recorded in the pull request; every command
  below was run against the working tree of that commit.

## What changed

- `version_range` gains a required `basis` field (`exercised` |
  `documentation` | `illustrative`) declaring how the range was established.
- Every control migrated to its honest basis: seed controls FMR-001..FMR-014
  are `illustrative` (synthetic placeholder examples), practice controls
  FMR-015..FMR-022 are `documentation` (procedures read against builds, as
  their own notes already stated). No range was narrowed or widened; the
  claim attached to each range is what changed.
- Report results carry `version_basis` and, for statuses whose reading
  depends on in-range membership on a non-exercised basis, an explicit
  `hermes_version.basis` disclosure reason. No applicability status changed;
  `unsupported` on out-of-range versions and `needs_decision` on missing
  versions behave exactly as before. The report document tag is now
  `beyond-prompting/report@2`.
- CLI: `evaluate --format markdown` exports a deterministic, fully escaped
  Markdown rendering of the report; `compare a.json b.json` diffs two
  reports against their recorded input context (registry version and digest,
  inventory digest, profiles, as-of, freshness policy), marks
  `same_context: false` with an explicit warning when they differ, and lists
  per-control status/version-basis transitions with reason deltas. All JSON
  inputs load under explicit limits: 4 MiB size cap, duplicate object keys
  rejected as contradictory facts (previously accepted silently,
  last-wins), malformed or pathologically nested documents rejected.
- Registry manifest bumped to 0.3.0 with `as_of 2026-10-23`; the example
  report was regenerated deterministically.
- Minimal CI workflow `.github/workflows/registry-checks.yml` runs the unit
  suite, the registry validator and the repository structural validator on
  pushes and pull requests.
- This resolves review question 3 from the 0.2.0 note: the wide ranges stay
  as documentation/illustrative records and no longer imply exercised
  platform compatibility, instead of being narrowed to a claim that would
  itself be unverified.

## Commands and results

All of the following were run against the candidate tree; exit code 0 unless
noted.

```sh
cd $REPO
python3 scripts/applicability.py validate-registry
python3 -m unittest discover -s registry/tests   # 90 tests, OK
python3 scripts/validate.py                      # repository structural checks, PASS
python3 scripts/applicability.py evaluate \
    --profile public-surface \
    --inventory registry/tests/fixtures/inventories/public-gateway.json \
    --as-of 2026-10-17
python3 scripts/applicability.py evaluate \
    --profile public-surface \
    --inventory registry/tests/fixtures/inventories/public-gateway.json \
    --as-of 2026-10-17 --format markdown
git diff --check
```

Determinism: both `evaluate` commands above were run twice; each pair
produced byte-identical output (also covered by the test suite). `compare`
of a report against itself yields `same_context: true` with zero changes;
`compare` of reports evaluated at different as-of dates yields
`same_context: false` plus the explicit warning. Duplicate-key, oversized
and pathologically nested inputs exit 1 with stable error codes.

## Honest limits

- The disclosure is about evidence, not new verification: no control was
  exercised against any Hermes build for this change, and no range claims
  otherwise.
- Verification here is local: unit tests, the registry validator, the
  repository structural validator, CLI determinism and failure-path exits.
  No control was applied to a live deployment.
- The CI workflow was checked as YAML and mirrors the commands above; its
  first hosted run happens on push and is not part of this local evidence.
- The 4 MiB input cap and the duplicate-key/nesting limits are defaults
  sized for this registry; they live in one constant and one loader function
  and can be revisited deliberately if a legitimate input ever hits them.

# Verification: operational-practice controls (registry 0.2.0)

Sanitised verification note for the change that adds the operational-practice
controls FMR-015 through FMR-022 on top of the ported registry scaffold.
Commands use `$REPO` for the repository checkout; run from the repository root.
No private paths, identifiers or source material are part of this note.

## Tested tree

- Base: the public `main` history (merge of the speech-to-text guide series).
- Branch: `research/real-world-controls-v1`.
- The exact candidate commit is recorded in the pull request; every command
  below was run against the working tree of that commit.

## What changed

- Ported the previously reviewed registry scaffold (`registry/`,
  `scripts/applicability.py`, `guides/control-registry.en.md` and its Russian
  twin) onto the current public base. The port is byte-identical to the
  reviewed source for those paths; the base's own newer content
  (speech-to-text guide, later controller-guide revisions) is untouched.
- Added eight operational-practice synthesis controls, FMR-015..FMR-022,
  each marked `provenance.origin: synthesis`, and referenced them from the
  relevant profiles (`private-server`, `messaging-gateway`,
  `low-trust-ingestion`, `privileged-operator`).
- Bumped the registry manifest to `registry_version 0.2.0` and
  `as_of 2026-10-22`, and extended its description to separate synthetic seed
  content from synthesis content.
- Added a positive inventory fixture
  (`registry/tests/fixtures/inventories/operator-console-unattended.json`),
  evaluator tests for the new controls (positive, negative and
  missing-fact cases), and updated existing count/expectation assertions.
- Regenerated `registry/examples/report-public-surface.json` with the CLI.
- Added a "seed vs synthesis" provenance section to both registry guide
  translations (same heading structure).

## Commands and results

All of the following were run against the candidate tree; exit code 0 unless
noted.

```sh
cd $REPO
python3 scripts/applicability.py validate-registry
python3 -m unittest discover -s registry/tests   # 72 tests, OK
python3 scripts/validate.py                      # repository structural checks, PASS
python3 scripts/applicability.py evaluate \
    --profile public-surface \
    --inventory registry/tests/fixtures/inventories/public-gateway.json \
    --as-of 2026-10-17
git diff --check
```

Determinism: the `evaluate` command above was run twice; both runs produced
byte-identical reports (also covered by the test suite).

## Honest limits

- All inventories and fixtures are synthetic and labelled as such; they
  exercise the controls, they do not prove any historical incident.
- The synthesis controls are operational practice generalised from recorded
  use with private detail removed; where a claim would be product-specific,
  the control text says so instead of citing an incident.
- Verification here is local: unit tests, the registry validator, the
  repository structural validator and CLI determinism. No control was applied
  to a live deployment, and no external CI was run for this change.
- The verified version ranges on the practice controls are deliberately wide
  (0.6.0–1.2.0); they record the builds the surrounding procedures were read
  against, not a versioned platform feature.

## Questions for review

1. Are the profile assignments and baseline choices for FMR-015..FMR-022 the
   ones you want (in particular FMR-018 as non-baseline in `private-server`)?
2. Should the universal practice controls (FMR-017, FMR-019) also be
   referenced from `workstation`, accepting that they then appear in every
   workstation report?
3. Is the wide verified range on practice controls acceptable, or should
   practice controls carry a different freshness convention?
