---
name: contribution-review
description: Check the technical claims in a review, pull request, issue or comment before posting it to a repository you do not own. Scope and evidence for every claim, two independent passes, an adversarial pass on the draft, and a re-check of the head commit right before posting. Use before any forge review, PR, issue or technical comment in someone else's project.
compatibility: Any forge (GitHub, GitLab, Codeberg, etc.) and any agent that can read code and run commands. Sub-agents help but are optional.
metadata:
  author: Danil
  version: "0.1.0"
  category: software-development
  tags: code-review, pull-requests, issues, open-source, evidence, adversarial-review
---

# Contribution Review

Practice-derived procedure, not a forge or project policy.

## When to use

Before posting to a repository you do not own:

- a review of someone else's pull request;
- your own pull request (its body and its code);
- an issue;
- a comment that states how code behaves.

Skip it for comments with no technical claim ("thanks", "rebased").

This skill owns the correctness of what you claim. It does not own privacy, provenance or the publication step: load `public-contribution-integrity` (in this collection) for those, after this skill and before any write.

## Modes and authority

1. **ASSESS** — read the PR, issue or code; run local checks. No forge writes.
2. **PLAN** — produce the draft with every claim scoped and marked, plus the gate result.
3. **APPLY** — post exactly the approved text.
4. **VERIFY** — read the posted item back.

Preparing or reviewing a draft is not approval to post it. Post only with the owner's approval for this exact text, or a standing approval that covers it.

## Rule 1: every claim has a scope and evidence

State each claim's scope: the providers, platforms, configs or code paths it covers. Attach one of:

- a `path:line` at an exact commit SHA, with the SHA in the text;
- a command you ran, with its output;
- a test run, with pass and fail counts.

A claim wider than its evidence is a guess: narrow it or label it "not checked".

Severity and frequency words are claims: "edge case", "rare", "pre-existing", "only when", "never", "all", "does not block". For "only when X", list every way the input reaches the code and show that each one needs X.

For your own PR, "reproduced on main" means a test or command that fails on the default branch and passes with the fix, both runs shown.

## Rule 2: two independent passes

Run two reviewers (sub-agents, or fresh sessions if you have none) on the same commit. Neither sees the other's output. Merge the findings yourself; settle disagreements with a command or a code read, never a vote.

When the code branches by provider, backend, platform or config, each reviewer lists the variants from the code (every resolver, adapter or handler in the dispatch) and checks the claim on each, or limits the claim to the variants checked.

Same-model reviewers are independent contexts, not different models. Say which you used.

## Rule 3: adversarial pass on the draft

A third reviewer reads only the merged draft and the code. Its job is to refute the draft. For each claim it:

1. restates the claim as a testable sentence;
2. finds the strongest counter-case: another provider, a value that is missing rather than wrong, another OS, a newer head, the fallback path, a concurrent caller;
3. runs or reads to settle it;
4. marks it: proven, narrowed, softened to a question, or dropped.

It names at least one counter-case per severity claim. "No counter-case found" lists the cases tried. Apply every mark before going on.

## Rule 4: tone and content

- Lead with what is right.
- Each finding: failure scenario, `path:line`, suggested fix.
- Unproven impact becomes a question.
- Do not ask the author for work you did not show is needed.
- No private names, internal agent names, private paths, hosts or secrets.
- Your own PRs follow the target's contribution guide and test rules (some projects ban tests that read source or config files). Search open and merged issues and PRs first and link the related ones.

## Rule 5: re-verify right before posting

1. Fetch the current head SHA. If it moved, re-run the affected checks or do not post.
2. Read comments and reviews added since the draft; drop points already raised or fixed.
3. Fetch the default branch; check the touched files did not change since your base.
4. Search once more for duplicate issues and PRs.

## Rule 6: final gate

All must be yes, else fix the draft or do not post:

- [ ] Every claim has a scope and evidence.
- [ ] Two independent passes ran; disagreements settled by evidence.
- [ ] The adversarial pass ran; its marks are applied.
- [ ] Each severity word has a counter-case check behind it.
- [ ] Guesses are labelled or phrased as questions.
- [ ] The head SHA is unchanged since the last check; no new comment made a point stale.
- [ ] The owner approved this exact text, or a standing approval covers it.

## Evidence

Keep the drafts, both pass outputs, the adversarial marks and the command logs with the work item (task tracker, ticket or a local evidence folder outside any public repository). Report the final text, the SHA it was checked at, and the gate result.

## After posting

If someone corrects you: thank them, confirm or dispute with evidence, record the miss and its root cause, and add the check this procedure lacked.

## Acceptance scenarios

1. The draft says "edge case" after testing one provider, and the code dispatches over five: block until each variant is checked or the claim names only the one tested.
2. The head commit moved after the draft: re-run the affected checks before posting.
3. A new comment already reports the same bug: drop the point or reference that comment.
4. The adversarial pass softened a claim to a question: the posted text asks the question; it does not assert.
5. The owner approved an earlier version of the text: the changed text needs approval again unless a standing approval covers it.
