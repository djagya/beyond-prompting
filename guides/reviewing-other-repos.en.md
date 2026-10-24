# Reviewing and Contributing to Other People's Repositories with Agents

**Practice notes from one owner's agents. The procedure is our own; it is not a GitHub, forge or project policy.**

An agent can read a pull request, run its tests and draft a review in minutes. That speed is the risk: a confident, wrong review costs more than no review. It misleads the author, it can be merged as a "reviewed" fix, and it spends the trust you have with the maintainers. The same holds for your own pull requests, issues and technical comments in a repository you do not own.

This guide covers one procedure for anything an agent posts to another project: two independent passes, an adversarial pass on your own draft, a scope and a piece of evidence for every claim, and a re-check right before posting. The agent version is the [contribution review skill](../skills/contribution-review/SKILL.md). Privacy, provenance and the exact publication step are a separate gate: [public contribution integrity](../skills/public-contribution-integrity/SKILL.md).

## 1. The case that prompted it

Observed in practice, details removed.

An agent reviewed a pull request in a multi-provider LLM tool. It found a real bug: a background worker dropped a corrected endpoint URL that the main process had repaired. The agent checked the bug on one provider, saw that it only showed up when the stored URL was stale, and wrote: "mostly pre-existing, an edge case, does not block this PR". The owner's session reworded the draft and posted it.

A day later another contributor showed that the bug broke every job on a different provider. That provider never stores an endpoint URL at all; the tool builds it at runtime from a region. The worker received an empty value and fell back to a default region. The finding was right; the rating was wrong.

What went wrong was not the code reading:

- **Scope.** One provider was probed; the claim covered all providers.
- **A severity word without evidence.** "Edge case" and "does not block" were claims, and nothing checked them.
- **One pass.** The same agent wrote the draft and judged it. Nobody tried to prove it wrong.
- **The last step only edited style.** The human-facing session polished the text and did not re-test it.

## 2. Every claim has a scope and evidence

Write each claim with its scope: which providers, platforms, configs or code paths it covers. Attach one piece of evidence:

- a `path:line` at an exact commit SHA, with the SHA in the text, because a force-push can make links point at a commit that is no longer on the PR;
- a command that was run, with its output;
- a test run, with the pass and fail counts.

A claim wider than its evidence is a guess. Narrow it, or say "not checked".

Severity and frequency words are claims too: "edge case", "rare", "pre-existing", "only when", "never", "all", "does not block". For "only when X", list every way the input reaches that code and show that each one needs X.

For your own pull request, "reproduced on main" means a test or command that fails on the target's default branch and passes with the fix, with both runs shown.

## 3. Two independent passes

Run two reviewer agents on the same commit. Do not show either one the other's draft. Merge the findings yourself, and settle each disagreement with a command or a code read, not a vote.

When the code branches by provider, backend, platform or config, each reviewer lists the variants from the code itself (every resolver, adapter or handler in the dispatch) and checks the claim on each one, or limits the claim to the variants it checked. This is the step that would have caught the case above.

Two agents on the same model are two contexts, not two opinions from different models. That is still useful: each reads the code without the other's framing. If you want model diversity as well, use a different model for one pass and say so in your notes.

## 4. An adversarial pass on your own draft

A third agent reads only the merged draft and the code, not the reviewers' notes. Its job is to refute you. For each claim it:

1. restates the claim as a testable sentence;
2. finds the strongest counter-case: another provider, a value that is missing rather than wrong, another operating system, a newer head commit, the fallback path, a concurrent caller;
3. runs or reads the code to settle it;
4. marks the claim: proven, narrowed, softened to a question, or dropped.

It names at least one counter-case for each severity claim. "No counter-case found" lists the cases it tried. Apply every mark before going on.

The "missing rather than wrong" case deserves its own line. Reviewers test bad values; bugs often live where a value was never set.

## 5. Tone and content

- Lead with what the pull request gets right.
- For each finding: the failure scenario, the `path:line`, and a suggested fix.
- Ask about impact you did not prove: "Does this also affect providers that build their endpoint at runtime?"
- Do not ask the author for work you did not show is needed.
- Keep private names, internal agent names, private paths, hosts and secrets out of the text.
- For your own pull requests, follow the target's contribution guide and test rules. Some projects ban tests that read source or config files; read the rules before writing tests. Search open and merged issues and pull requests first, and link the related ones.

## 6. Re-verify right before posting

Drafts go stale while you work on them.

1. Fetch the current head commit. If it moved, re-run the affected checks or do not post.
2. Read the comments and reviews added since the draft. Drop the points someone already raised or fixed.
3. Fetch the default branch and check that the touched files did not change since your base.
4. Run one more search for duplicate issues and pull requests.

## 7. The final gate

Post only when every answer is yes:

- Every claim has a scope and evidence.
- Two independent passes ran, and their disagreements were settled by evidence.
- The adversarial pass ran, and its marks were applied.
- Each severity word has a counter-case check behind it.
- Guesses are labelled, or phrased as questions.
- The head commit is unchanged since the last check, and no new comment made a point stale.
- The owner approved posting this exact text, or a standing approval covers it.

Keep the drafts, both pass outputs, the adversarial marks and the command logs with the work item. When someone corrects you, thank them, confirm or dispute with evidence, and add the check your procedure missed.

## 8. Adapting it

- **One agent only.** Run the passes in fresh sessions, and give the adversarial session only the draft and the code. It is weaker than separate agents, but far better than one pass.
- **No test environment.** Code reading still settles many claims. Label the rest "not checked" or turn them into questions.
- **Small comments.** A "thanks" or "rebased" comment needs none of this. Any comment that states how code behaves does.
- **Cost.** The passes take a few minutes of agent time. One wrong review posted in the owner's name costs much more.
