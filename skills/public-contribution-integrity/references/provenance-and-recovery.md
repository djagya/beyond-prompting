# Provenance and recovery

Load when outgoing material has contested, mixed, generated, copied or uncertain origin; when a prerequisite must be rebuilt; when takeover or salvage is proposed; or during a public integrity incident.

## Three provenance dimensions

Classify each outgoing commit and substantive block on all three.

### Human intellectual source

- `OWNER` — independently attributable to the requesting owner's direction, design and adopted work;
- `JOINT` — substantive design or implementation with another human;
- `FOREIGN` — produced by another person;
- `UNCERTAIN` — not established.

Routine review or a typo fix does not create co-authorship; an accepted replacement algorithm does.

### Material origin

- `ORIGINAL` — produced without reproducing third-party implementation;
- `AI_TOOL_ASSISTED` — generated under the owner's substantive direction;
- `MECHANICALLY_GENERATED` — lockfiles, schemas, snapshots, formatter output;
- `COPIED_OR_VENDORED` — from external material;
- `UNCERTAIN`.

AI-assisted output may ship as `OWNER_ONLY` only when the owner supplied or adopted the intent, the result was inspected and understood, the owner accepts responsibility, repository policy permits it, required disclosure is made, and no third-party material is reproduced. Retyping, translating, porting or paraphrasing someone else's implementation does not create independent authorship.

### Permission and disclosure

For external or generated substantive material: source and license, compatibility, notices to keep, attribution, AI disclosure, DCO/CLA. Credit is not permission; permission is not authorship. Uncertain or incompatible status blocks publication.

### Metadata vs provenance

Author, Committer, trailers, branch names and squash containers are metadata. Changing them never changes provenance. A matching patch ID is evidence of matching normalized content, not of derivation or authorship — corroborate with lineage, range-diff and public PR heads.

## Full outgoing publication graph

Inspect: commit messages, trailers, signatures, author/committer emails, blobs; branch/tag/ref names and the refspec; PR/issue title, body, comments, suggestions, rendered and hidden link targets; filenames, fixtures, snapshots, binaries, screenshots and EXIF, logs, source maps, build paths, generated docs, releases, attachments; CI logs and annotations; bot-generated text.

Search for: private tracker/chat/document URLs and ids; credentials, authenticated URLs, tokens, keys; personal addresses and unnecessary PII; internal hostnames and paths; hidden foreign provenance.

## Relationship claims

- `Fixes/Closes` — fully resolves the issue as written (beware automatic closing);
- `Related to` — narrower overlap;
- `Complementary` — distinct layer or failure mode;
- `Alternative to` — independently produced competing design;
- `Follow-up` — independent delta on merged work;
- `Supersedes` — complete replacement, with maintainer acknowledgement or established norm.

Audit closing keywords across commit messages, PR text and comments. Never close another contributor's PR without authority.

## Unmerged prerequisites

1. keep the follow-up local; 2. identify the exact owner delta; 3. wait for the prerequisite to merge; 4. fetch the fresh base; 5. new branch from it; 6. apply only the owner delta; 7. compare old/new with range-diff; 8. rerun provenance, privacy, tests, authorization; 9. publish only if still useful.

## Incident recovery

### Private identifier or unnecessary PII published

Stop publication. Redact mutable surfaces within an authorized envelope, read back, then assess notifications, caches, forks, mirrors and history separately. Report residual exposure honestly.

### Credential or equivalent secret published

Treat as compromised: stop and avoid repeating the value; notify its owner; revoke or rotate under an incident mandate; keep a private incident record; redact mutable surfaces; assess historical objects, forks and downstream use. History rewriting or branch deletion needs its own authorized envelope.

### Foreign work in an owner-only PR

Stop updates; classify; do not repair by changing authors, stripping trailers, squashing or retyping; withdraw the PR if it cannot be made honest in place; credit existing work; keep only the genuinely independent delta locally and rebuild after the prerequisite merges.
