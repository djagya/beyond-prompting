# Danil's Hermes Fork, in Plain Words

**Practice notes about one maintained fork of Hermes Agent. This is not official Nous Research or Hermes Agent documentation.**

[Danil's fork](https://github.com/djagya/hermes-agent) is [upstream Hermes](https://github.com/NousResearch/hermes-agent) plus several hundred changes made while running one assistant, Sera, around the clock in Docker. Sera talks over Telegram, runs many scheduled jobs, edits its own skills under approval, logs into websites, and pays at checkouts with the owner's approval. Each change in the fork came from something that broke, leaked or went quiet in that setup.

This page explains what the fork changes, why, and what it costs you. It was checked against the fork's release branch on 2026-11-20. Branches move, so treat every "fork-only" claim as dated and re-check it before you rely on it.

## The short version

- **It keeps working when things go wrong.** A message that a restart interrupted is picked up again afterwards. The container refuses to start broken instead of running half-working. The session database is never rebuilt while it is in use.
- **Approvals mean exactly what you approved.** An approved skill edit cannot be swapped for a different one, or applied over a newer version of the file. Command deny rules also look inside `eval` and `env -S`. An old or forwarded Telegram approval button does nothing.
- **It handles logins and cards without seeing them.** The fork extends Hermes's credential vault: card payments at checkout with one approval tap per purchase, new-account passwords, recovery codes, and logins from a photographed letter. Every filled value is masked in everything the model and the logs see.
- **Scheduled jobs fail honestly and quietly.** You get one alert after the third failure, not one per job per network blip. A job that ran out of provider credits counts as failed, not "ok".
- **Memory stays tidy.** The automatic memory review cannot fill memory to the limit, and its stale proposals expire.
- **A tighter image.** Tools that open untrusted files run in a sandbox without network access. The image is scanned before release and carries a signed record of the commit and workflow that built it.

None of this makes the fork better than upstream in general. It is better for one kind of deployment: an always-on gateway in Docker with real credentials, many cron jobs and an assistant that changes itself. For a laptop install or a light setup, stock upstream is simpler and gets fixes first.

## Who it is for

The fork fits you if most of these are true:

- Hermes runs in Docker on an always-on amd64 machine, not on your laptop.
- You talk to it through a messaging gateway, usually Telegram.
- It runs many scheduled jobs, and you need to trust their alerts.
- It holds real credentials: a password manager, card details, logins.
- It edits its own skills or memory, and you approve those edits.
- You want to pin an exact image and verify how it was built.

Stay on upstream if you use Hermes on a desktop or laptop, run on ARM (the fork image is amd64 only), want the official docs to match what you run, or need only one of the fixes below. For a single fix, carrying that one patch on upstream costs less than adopting the whole fork.

## What changes, area by area

Each item says what you notice, why it exists, and whether it works on its own or needs Danil's private services.

### 1. It keeps running through restarts and outages

- **Interrupted requests resume.** If a deploy or crash restarts the gateway mid-answer, the request is picked up again afterwards, in the same order. Upstream marks the cut-off turn as unknown and waits for you to clear it, so a deploy quietly drops what you asked. Setting `gateway.resume_interrupted: ask` restores upstream's behaviour.
- **The container fails loudly instead of running broken.** It refuses to start with less than 2 GiB of free disk, with a database it cannot open, or after a failed config migration. A Docker health check covers the gateway, the disk, the database and the migrations. Upstream warns and carries on after a failed migration.
- **The session database is never rebuilt live.** On a store of several GB with many writers, a live search-index rebuild was what kept corrupting it. The fork never runs one on an open database. If the index goes stale, search falls back to a slower query, and the repair waits for an offline maintenance window.
- **The password manager does not lock you out.** With 1Password, all references in one item are read in one call. A rate-limit stops reading and backs off, and the last good value fills in for a value lost to throttling or a network error, but never after an authentication failure. Without this, a 1Password service account runs out of reads, and the next restart comes up without its messaging tokens.
- **MCP connections that use OAuth stay connected.** Tokens refresh a minute before they expire and once more when a server rejects one, and a failed early refresh keeps the token that still works. Without this, a long-running gateway lost its MCP tools in the middle of the day. Proposed upstream (open PRs).

### 2. Approvals mean exactly what you approved

- **Skill and memory edits are bound to what you reviewed.** An approval applies once, to the exact text you saw. If the skill changed after you reviewed it, the edit is refused and staged again. A batch of skill edits rolls back as a whole when one fails.
- **Deny rules look inside wrapped commands.** A deny rule also matches a command hidden inside `eval "…"` or `env -S "…"`. The smart-approval model returns typed outcomes, and the approval log records whether a model or a person decided.
- **Telegram approval buttons work once.** Each button carries a random single-use token bound to its request, chat and message. A replayed tap, a button from before a restart, or someone else's tap does nothing. Upstream numbers the buttons with a counter that starts again at every restart, so an old button could match a new request.
- **Scheduled jobs cannot approve themselves.** By default, a cron run refuses anything that needs approval instead of waiting for an answer nobody will give.

### 3. Logins and cards, without the model seeing them

Upstream already has a credential vault that fills saved passwords and two-factor codes without the model seeing them. The fork extends it:

- **Card payments with one approval per purchase.** The agent can fill a saved card into a checkout, including card fields inside a payment provider's frame. Before each fill, you get a Telegram card showing the shop, the cart, the total and the card label, and you tap Approve. If the total matches the page, that same tap also allows exactly one press of "Pay". The fill never presses Pay on its own. It notices when an order has gone through, so the same purchase cannot be paid twice.
- **Payment forms nobody has reviewed yet.** A built-in list covers reviewed payment providers. With destination consent turned on, a card can also go into an unknown payment form, but the approval card marks it, and the approval covers that one purchase only.
- **Masking.** Every value that went through a fill is masked in tool output, browser output, pop-up text and logs. Groups of digits that look like a card number are masked whole, so the model cannot learn the number by noticing which digits were hidden.
- **Harder login cases.** The vault can fill a new-account password and its confirmation box, type one stored recovery code per approval (never the same code twice), and turn a photographed letter with a one-time login into a single sign-in. The model never sees the letter's credentials. Each fill reports which field it wrote and why a fill was refused, so the agent does not retry and burn a one-time code.

**Limit:** card payments need a Telegram owner set in `approvals.payment_approver`. Without one, every card fill is refused, including in the CLI and desktop app, where upstream would just ask.

### 4. Scheduled jobs that fail honestly

- **Alert thresholds per job:** for example, alert on the third failure in a row, or after 45 minutes of failing.
- **Network outages, once.** When the host goes offline, an opt-in switch sends one shared alert instead of one from every job. If the outage lasts too long, the per-job alerts come back.
- **A run whose tool provider ran out of credits counts as failed.** Before, it was recorded as a success that did nothing.
- **Fallback models per job, and a longer run history.**

### 5. Memory, skills and identity

- **The automatic memory review has a ceiling.** It can add to memory but never remove, so it used to fill memory to the hard limit, and after that every save you asked for failed. Now it stops below a set ceiling, its unapproved proposals expire after 14 days (moved aside, never deleted), and a newer proposal replaces older ones it fully covers.
- **Loaded skills survive context compression.** A skill the model just loaded is kept based on how much text came after it, not on a message count, so a burst of short turns no longer drops a skill the model is still following.
- **An `ARCHITECTURE.md` slot.** Next to `SOUL.md`, the fork loads `ARCHITECTURE.md` from the profile, including in scheduled runs. Facts about the setup and its privacy rules live there instead of in limited memory. See [Identity, Memory and Context](identity-memory-context.en.md).
- **Image config is a default, not a lock.** Settings shipped with the image fill in only what your config leaves out, and `hermes config set` still wins. Upstream treats them as locked.

### 6. Telegram polish

- **Every answer has a link.** The platform message ids of each answer are stored with it, so you can link back to that exact Telegram message later.
- **The first answer arrives before a queued voice note is transcribed.**
- **Pictures attached to progress messages are kept,** long replies go out as rich messages instead of failing on Telegram's length limit, and scheduled jobs send photos as albums.

### 7. A browser run by a separate service (needs Danil's private service)

With a browser-control service configured, every browser tool gets its browser from that service. Each task and identity has its own slot, for example research or a sensitive login. On top of that:

- The agent can **hand the live browser to your phone** to solve a captcha or log in. It continues on its own when you tap "return".
- **Pop-ups on consequential pages,** such as "Confirm purchase?" or "Delete account?", wait for an explicit answer instead of an automatic OK.
- After a card fill, **the slot is locked down** (no screenshots, no second connection) until the shop's confirmation page has been read.

The service itself lives in Danil's private deployment repository, so this whole area is off in your install unless you build your own service. Without it, the browser behaves like upstream.

### 8. A tighter image

- **Tools that open untrusted files run in a sandbox.** PDF, OCR, office, image, archive and media tools run inside bubblewrap with no network and limits on CPU, processes and output. CI attacks the sandbox with 16 hostile files: archives that write outside their folder, decompression bombs, office macros and a fork bomb among them.
- **Nothing is downloaded at runtime.** Plugin installs at startup are turned off, and the tools the image needs (`gh`, the 1Password CLI, a guarded mail client, two MCP servers, the Home Assistant plugin) are built in.
- **Release checks.** Each image is scanned with Trivy and blocked on fixable high or critical vulnerabilities. The image that passed the tests is the image that gets published. It carries a signed GitHub build attestation, and its version shows the upstream release it is based on plus the number of commits on top.

## What it costs you

- **One maintainer, one deployment.** Changes are chosen and reviewed for one setup, and some defaults show it. Skills the agent creates locally must name Sera as their author (hard-coded). The image includes MCP servers for Danil's services. The defaults assume a Telegram owner.
- **It lags upstream.** A release follows an upstream release tag, a full test run and a review. Upstream fixes that land after a cut, security fixes included, reach the fork only with the next cut or a carried patch.
- **You trust a second publisher.** The image is built by the fork's workflows and published from Danil's registry account. Pin it by digest and verify the attestation.
- **The docs differ.** The official docs are wrong about fork-only behaviour: they describe image config as a lock and do not mention `ARCHITECTURE.md`.
- **Switching back is not free.** The fork adds a column to the session database and holds back one upstream migration. Going back to upstream may run that migration and a live index rebuild the first time it opens the database, so try a switch on a copy.

## Before you run the image

1. **Where it is.** `ghcr.io/djagya/hermes-agent`. Each release is tagged with the full commit SHA and with the branch name without `release/`. There is no `latest` tag. Pin by digest.
2. **How releases are named.** Release branches are `release/vX.Y.Z-dlz`, cut from upstream tag `vX.Y.Z`. The fork's default branch is not the build Danil runs. Read the version on your own install rather than trusting this page.
3. **amd64 only.** There is no ARM image.
4. **Check how it was built:**

   ```bash
   gh attestation verify oci://ghcr.io/djagya/hermes-agent@sha256:<digest> --repo djagya/hermes-agent
   ```

5. **SBOMs are short-lived.** The SPDX and CycloneDX files are kept for 7 days as workflow-run artifacts and are not attached to the image. Save your own copy if you need one.
6. **The scan has exceptions.** The vulnerability gate skips the bundled `op`, `gh` and `uv` binaries and pip's vendored code, and honours dated ignore rows.
7. **Host settings for the sandbox.** The sandboxed tools need user namespaces. Run the container with the shipped seccomp profile and `apparmor=unconfined`, and on Ubuntu 24.04 allow unprivileged user namespaces. Without that, those tools refuse to run. There is no unsandboxed fallback.
8. **Startup is strict.** You need at least 2 GiB free disk, an openable database and a clean config migration. With `HERMES_REQUIRE_DATA_MOUNT=1`, the data directory must also be a real mount.
9. **Defaults to review.** Skill edits need approval, memory edits do not, and scheduled jobs refuse anything that needs approval. All three can be changed with `hermes config set`. Interrupted requests resume after a restart. Card payments are off until you name a Telegram approver.

## What went back to upstream

Fixes are proposed upstream as separate pull requests, so the fork can shrink over time. As of 2026-11-20:

- Five upstream PRs have merged with parts of this work in them, as salvages or with co-author credit. They cover Telegram image albums, a reply to a voice note still reaching speech-to-text, a terminal guard that blocked harmless commands, `eval` payloads reaching the hard command floor, and a CI cache fix.
- Nine more PRs are open. They cover MCP OAuth recovery, deny rules inside `eval` and `env -S`, card expiry dates, kanban notices, cron monitoring, browser error output and a package-manager cache.
- Some fork changes stopped being differences because upstream fixed the same problem itself. Examples are `hermes config set` with lists and mappings, a repository-config code-execution fix, cron script timeouts and catch-up of missed runs.

Each release cut drops what upstream has taken.

## Detailed reference

For an engineer comparing builds. Status is relative to upstream `main` on 2026-11-20.

| Area | What the fork changes | Upstream status |
|---|---|---|
| `ARCHITECTURE.md` prompt slot | Loads `$HERMES_HOME/ARCHITECTURE.md` after `SOUL.md`. It belongs to the profile, does not depend on the working directory, and loads in cron runs that carry identity. | Fork-only. |
| Managed config scope | The image's managed config is a seed: it fills only values your config leaves out. `config set` wins, `config unset` lets the seed show through, and managed `.env` secrets stay refused. | Fork-only. Upstream rejects `set` and `unset` on a managed key. |
| Session store full-text index | No live `rebuild` or drop-and-recreate on an open database. A stale index is detached and search falls back to `LIKE`. The startup lease around index DDL is one hour. | Fork-only. Upstream rebuilds live behind an admission lock. |
| 1Password secret source | One `op item get` per item. A rate limit sets a per-account backoff. A per-reference last-good cache fills values lost to throttling, network errors or timeouts, never after an auth failure. A `hermes` started from the agent's own shell reads only the cache. | Fork-only. Upstream's last-good cache covers Bitwarden only. |
| Skill and memory write approval | Durable staged writes, approval bound to the payload digest, a base-state digest check under a cross-process lock, batch rollback, and quarantine for an ambiguous outcome. Background-review proposals have a ceiling, expire and are superseded. | Fork-only. A payload-binding PR was closed upstream. |
| Command approval | Deny rules match inside `eval` and inside `env -S` with unresolved `${…}`. Typed smart-approval outcomes. Bounded provenance of helpers defined in earlier code cells. Typed "could not scan" outcome. | Partly upstream: `eval` reaches the hardline floor. Deny rules inside `eval` and `env -S` are in an open PR. |
| Gateway | Interrupted turns resume after a restart (`gateway.resume_interrupted`). Single-use, request-bound tokens on Telegram approval buttons. | Fork-only. |
| Telegram | Delivery receipts and message links, the first answer before queued voice transcription, interim-message media, long replies as rich messages, native cron albums. | Partly upstream: standalone albums and replied voice notes landed upstream. |
| Credential vault | Card fill across reviewed payment providers with a per-purchase Telegram approval that also covers one Pay press, order detection, per-purchase destination consent, post-fill slot lockdown, confirmation-page handover, masking of filled values, signup passwords, single-use recovery codes, one-time letter logins, typed fill outcomes. | Fork-only. A card-expiry fix is in an open PR. |
| Cron | Per-job alert thresholds, opt-in grouping of network outages, credit exhaustion counted as failure, per-job fallback models, longer output retention. | Fork-only. A monitoring PR is open. Script timeouts and catch-up are upstream. |
| Kanban | A stable `blocker_key` for repeated blockers, snapshot-guarded operator recovery from the CLI, typed PR-acceptance failures, a typed exit when a mandatory skill is missing, retry of failed deliveries. | Fork-only. Parts are in open PRs. |
| Providers | xAI subscription routing (a port of an open community PR), Claude subscription sign-in from inside a container, MCP OAuth refresh and recovery. | Fork-only. MCP OAuth is in open PRs. |
| Browser (managed) | A client for an external browser-control service: slots leased per task and identity, file transfer, pop-up policy, phone handoff with automatic wake-up, operator-installed site bridges, UX capture. | Fork-only. Needs a private service. Off unless configured. |
| Container image | No compilers at runtime, Debian packages from a dated snapshot, a bubblewrap toolbox tested against hostile files, baked CLIs and MCP servers, the Home Assistant plugin bundled with a cold-boot grace period, `HEALTHCHECK`, strict boot gates, runtime plugin installs turned off. | Fork-only. Both images pin the Debian base by digest. Process supervision with s6 is upstream. |
| Release and supply chain | Version taken from the nearest upstream tag plus commit distance. The build fails on a mismatched branch or `pyproject.toml`. amd64 image published to GHCR after a Trivy gate, the tested image is the published image, build-provenance attestation, SBOMs as short-lived run artifacts. | Fork-only pipeline. Upstream publishes multi-arch images to Docker Hub. |

## Check it yourself

A read-only request you can give your own agent before adopting anything:

```text
Inventory my Hermes installation without changing it: install ownership
(Git checkout, container image, other packaging), terminal and browser
backends, running version and its source revision or image digest.
Compare the fork revision I name with my upstream base and list, per area,
which fork changes my setup would actually use. Propose an incremental
change set with acceptance checks and rollback (previous digest or
revision). Do not install, update, restart or switch builds.
```

See also [Setup Patterns Worth Reusing](setup-patterns.en.md), [Reference Setup](setup-reference.en.md) and [Operations](operations.en.md).
