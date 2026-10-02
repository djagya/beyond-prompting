# Setup Patterns Worth Reusing

**Practice notes from Danil's customized Hermes setup; not a required deployment template.**

This is a map of portable decisions, not a copy of a private configuration. Adapt the controls to your own account, tools and risk envelope.

Start with the [agent entry guide](agent-start.en.md) for a capability map and fallbacks. One controller is sufficient; private profiles, workers, memory services and deployment paths are not prerequisites. For concrete execution contracts, see [Operating Loops](operating-loops.en.md). For a concrete deployment, see [Reference Setup](setup-reference.en.md), [Operations](operations.en.md), [Identity, Memory and Context](identity-memory-context.en.md) and [Operating Hermes with a Coding Agent](coding-agent-operator.en.md).

## 1. Review experience, then inspect the mechanism

Run [Weekly Learning Extraction](weekly-learning-extraction.en.md): review first, inspect current owners second, implement only after a bounded mandate. A failed outcome may expose an instruction conflict or unavailable capability rather than a missing rule.

## 2. One owner of the final outcome

A controller retains integration, external authority and final verification. Workers receive bounded tasks that match their actual capabilities. Use [Single Agent by Default](../readings/single-agent-by-default.en.md) to decide whether delegation earns its cost. A notification or worker handoff is not final delivery.

## 3. Separate current truth, procedures and history

Maintain one current decision in its proper owner. Procedures live in reusable skills; project state lives in project artifacts; private source evidence remains private. Historical summaries should not compete with later user corrections. Inspect source and deployed state separately.

## 4. Match proof to the requested job

Verify the useful end state, not just tool success: documents must be readable, visual maps must remain visual, access routes require actual safe probes, temporal answers require dated evidence. Record which checks were not executed.

## 5. Keep external boundaries explicit

Capability is not authority. A signed-out browser does not prove that an API route is unavailable. A configured credential does not prove working access. Preserve origin binding, native secret transport, confirmation boundaries and ambiguity-safe retries. See the [hardening guide](hermes-hardening.md).

## 6. Prefer the existing lifecycle owner

Use the system's native job, service and recovery mechanisms before adding another watcher. Make each controller's stop condition explicit: completed result, genuine blocker, pending external work or exhausted bounded budget. Do not busy-poll workers or CI.

## The Hermes fork

[Danil's Hermes fork](https://github.com/djagya/hermes-agent) is upstream Hermes plus operational fixes for one long-running Docker deployment: an always-on messaging gateway, several profiles, many cron jobs, a secret manager and an agent that edits its own skills. Release branches are cut from upstream release tags and named for the upstream version they ship; each release is published as a digest-pinned container image. [Upstream Hermes](https://github.com/NousResearch/hermes-agent) remains the reference for the base project.

Branch contents and upstream inclusion change over time. This guide does not claim that every fork change is absent upstream, required for these methods or suitable for another deployment. Before adopting a build, inspect the intended branch, compare it with current upstream, read its tests and release notes, and choose a known revision. Do not assume the fork's default branch is the build currently used by its owner.

### What the fork changes

The table compares a fork release branch with upstream `main` by area. CI plumbing that does not change what a user gets is left out. "Fork-only" means upstream `main` had no equivalent code when this was written. Re-check before you rely on any row.

| Area | What the fork changes | Why it matters | Upstream status |
|---|---|---|---|
| Prompt slot for `ARCHITECTURE.md` | Loads `$HERMES_HOME/ARCHITECTURE.md` right after `SOUL.md`. It is profile-scoped, independent of the working directory, and also loads in cron runs that carry identity. | Runtime topology and channel/privacy invariants do not depend on bounded memory or on which directory a run starts in. Scheduled runs see them too. See [Identity, Memory and Context](identity-memory-context.en.md). | Fork-only. |
| Managed config scope | The image's managed config is a **seed**: it fills only leaves the user config omits. `hermes config set` writes the user config and wins; `config unset` lets the seed show through. Managed `.env` secrets stay refused. | Policy defaults (write approval, cron approval mode) ship with the image, while the operator or agent can still change a leaf and export it through git. The deployment asserts the values on every deploy instead of trusting a lock. | Fork-only. Upstream treats managed scope as a lock: `config set` and `unset` on a managed key are rejected. |
| Session store full-text index | Never runs a live FTS `rebuild` or drop-and-recreate on an open session database. A stale or misaligned index is detached and search falls back to `LIKE`; repair runs in an offline maintenance window. The startup lease around index DDL is long enough for a multi-GB store. | On a large store with concurrent writers, a live rebuild was the recurring corruption trigger. A startup killed mid-DDL by its watchdog restarted into the same DDL. See [Operations](operations.en.md). | Partially. Upstream serializes live rebuilds behind an admission lock and defers them while other processes hold the database, but it still rebuilds live. |
| 1Password secret source | References in one item resolve with one `op item get`. A rate-limit response stops the pull and writes a per-account backoff marker. Last-good values are kept per reference and fill only names lost to throttling, network errors or timeouts, never after an auth failure. A `hermes` started from the agent's own shell reads the cache only; an explicit sync stays live. | A service-account read budget runs out when every restart, cron re-pull and shell call re-reads every reference. Once it is spent, a restart comes up without messaging tokens. | Fork-only. Upstream has an opt-in last-good cache for Bitwarden, not for 1Password. |
| Skill and memory write approval | Staged writes are durable and read back. An approval applies once and is bound to the digest of the reviewed payload. Each apply checks the target's base-state digest under a cross-process lock, so a target that changed since review refuses and restages. Batch skill writes roll back on an exception; an ambiguous outcome is quarantined for an operator to resolve. | An approved change cannot overwrite a skill edited after review, and a different payload cannot ride on an earlier approval. | Fork hardening of an upstream feature. Payload binding is proposed upstream (open PR). |
| Command approval | Deny rules also match inside `eval` payloads and `env -S` payloads with unresolved `${…}`. The smart-approval guardian returns typed outcomes, and every decision records whether a model or a human decided. The guardian sees bounded provenance of helpers defined in earlier code cells. The lifecycle guard tells "dangerous operation seen" apart from "could not scan". | Fewer silent auto-approvals and fewer misleading denial reasons. After an incident, the log shows who approved what. | Fork-only. |
| Kanban | A stable `blocker_key` counts repeated blockers by cause, not by wording. Operator recovery (attested gate closure, exact-blocker resolution) is a snapshot-guarded CLI, not an agent tool. A configured notification target applies from task creation. PR-acceptance failures are typed (auth, rate limit, network), and `gh` authenticates through the profile's secret scope. A worker missing a mandatory skill blocks with a typed exit. | Long-running boards stop looping on reworded blockers, and stuck triage gets an audited way out without force flags. | Fork-only. Parts are proposed upstream (open PRs). |
| Gateway and Telegram | A delivery receipt (platform, chat, message ids) is stored on the exact assistant row and yields a Telegram message link. The first answer is delivered before a queued voice note is transcribed. Media from interim messages is kept. Replies that would exceed Telegram's limit after escaping go out as rich messages. Cron media results stay native albums. | On an always-on messaging gateway, replies stay ordered and can be linked later. | Fork-only. Several parts are proposed upstream (open PRs). |
| Browser | An optional client for an external, self-hosted browser-control service: when configured, every browser entry point gets a gated CDP URL from it. Leases are keyed by task and identity, dead leases are dropped, and leases are released when a session closes. | Research and sensitive browsing identities stay apart, and finished cron runs and sessions do not keep browser slots. | Fork-only. Specific to the owner's browser service and off unless configured. |
| Container image | A runtime stage without compilers, with Debian packages from a dated snapshot. A baked toolbox of document, archive and media CLIs that run in a bubblewrap sandbox with no network and caps on CPU, processes and output. A guarded mail CLI and baked MCP server binaries. A Docker `HEALTHCHECK` (gateway `/health`, service slot, free disk, read-only database open, migration markers). Boot refuses tight disk, an unopenable database, a failed config migration and, with `HERMES_REQUIRE_DATA_MOUNT=1`, a data directory that is not a mount. The image sets `HERMES_CHILD_HOME` to the child-process home that upstream already derives from `$HERMES_HOME`, and an image doctor checks that layout. | The container fails loudly at boot instead of running degraded, and parsers of untrusted files are contained. | Fork-only. Both images pin the Debian base by digest, but the upstream image has no `HEALTHCHECK` and continues with a warning after a failed config migration. |
| Release and supply chain | The version is derived from the nearest upstream release tag plus the commit distance and stamped into image labels. The build fails when the branch name or `pyproject.toml` disagrees with that base. A single-arch (amd64) image goes to GHCR only after Trivy passes (fixable HIGH/CRITICAL) and is the same image that was tested. It ships SPDX and CycloneDX SBOMs and a GitHub build-provenance attestation (`gh attestation verify`). | A deployment pins by digest and can verify which commit and workflow built the image. | Fork-only pipeline. Upstream publishes multi-arch images to Docker Hub by digest; its workflows have no SBOM or attestation step. |

Some earlier fork changes are **no longer differences**, because upstream fixed the same problem: `hermes config set` parsing of list and mapping literals (upstream "fix(config): parse list/mapping literals in hermes config set" and "config set refuses a wrong-shaped value for a list/mapping key"), the GitSpawn repository-config RCE fix, which the fork carried before its base release included it, the terminal snapshot leaking delegation markers, and the explicit admin for `/goal gate add`. Older fork changes to delegation fallback chains, checkpoint store limits, terminal lineage and Home Assistant write bounds no longer differ from upstream in the fork tree either. Verify current upstream before assuming either way.

### Trade-offs of running the fork

- **One maintainer, one deployment.** Changes are chosen, reviewed and released by one person for one deployment profile. Some are specific to it: the image requires the owner's agent name as the author of locally created skills, bakes MCP servers for the owner's services and carries the browser-control client.
- **It lags upstream between release cuts.** A release follows an upstream tag, a full test pass and a local CI gate. Upstream `main` moves quickly, so fixes that land upstream after a cut, security fixes included, reach the fork only with the next cut or a carried patch.
- **You trust a second publisher.** The image is built by the fork owner's workflows and published from the fork owner's registry account, in addition to Nous Research's source. Pin by digest and verify the attestation; the image is amd64 only.
- **Docs and data differ.** The official docs are wrong for fork-only behaviour (managed scope is documented as a lock; the `ARCHITECTURE.md` slot is undocumented). The fork adds a column to the session database and holds back one upstream index migration, so switching back to upstream may run that migration and a live index rebuild on first open. Test a switch on a copy.
- **Contribution PRs go upstream, so the delta should shrink, but only when upstream accepts or replaces a change.** Fixes are proposed as separate PRs ported onto current upstream `main`; several are open and none had merged when this was written. Overlap so far has come from upstream fixing the same problem itself. Each release drops carryovers that landed upstream.

### Choosing between the fork and upstream

Stock upstream is enough for a laptop or desktop install, a short-lived or single-profile gateway, light cron use, no secret manager, or any machine that is not amd64. It also gets fixes first and matches the official docs. The fork's changes matter for the profile it was built for: an always-on Docker gateway with several profiles and many cron jobs, a multi-GB session store, a rate-limited secret manager, an agent that edits its own skills under write approval, and an operator who wants digest pins with SBOMs and provenance. That makes the fork better for this deployment profile, not better in general. For a single fix, carrying that patch on upstream can cost less than adopting the whole fork.

A read-only adoption request for your agent:

```text
Inventory my Hermes installation without changing it: install ownership
(Git checkout, container image, other packaging), terminal and browser
backends, running version and its source revision or image digest.
Map capability -> authority -> tested access for each consequential tool.
Compare the fork revision I name with my upstream base. Propose an
incremental change set with acceptance checks and rollback (previous
digest or revision). Do not install, update, restart or switch builds.
```

- [Official Hermes documentation](https://hermes-agent.nousresearch.com/docs/)
- [Operational literacy](../readings/beyond-prompting.en.md)
- [Capability and authority](../readings/principles-from-hermes-in-practice.en.md)
