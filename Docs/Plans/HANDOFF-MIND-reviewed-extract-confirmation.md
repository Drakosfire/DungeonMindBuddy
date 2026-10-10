# MIND — truthful pinned semantic-review confirmation

Status: IMPLEMENTED_AWAITING_PRIME_REVIEW

Base: Buddy `main` at `6d27238820fdb0647694fcb9ee580680a88f8da3`

Authority: PRIME's bounded implementation lease on PR #1063, issue comment `6096969018`

## Outcome and boundary

An internal trusted GM caller may confirm a selected subset of an existing sealed extract-promote proposal only when an independently reviewed, byte-pinned artifact explicitly accepts every selected assertion. The artifact carries the agent steward's actual UTC review time. Buddy uses the fixed server service principal `service:buddy:reviewed-extract` for Core confirmation and retains the separate semantic reviewer attribution in the hashed candidate diagnostics.

This does not expose a new HTTP request, file path, reviewer, target override, or Core contract. The public extract-promote confirm model and legacy call path remain as they were. The root C1S1 review (`22 accept / 4 reject / 8 defer`, private SHA-256 `156179d9e5ee56f092fde8037725eca9fd232956e28931180632687e654bfa9d`) is local semantic authority only; it is not an execution input for this PR. The isolated probe's current head differs from the sealed old parent. No real C1 source, probe, or production graph was confirmed here.

## Exact path

1. Check the existing `CONFIRM_COMMIT` capability and GM graph scope for the selected native World, campaign, parent, and Core finalize tool before source or Core reads.
2. Verify the artifact byte digest, complete decisions over the proposal's accepted assertions, exact sorted selection, prepared package bytes, proposal seal, selected managed World binding, and run-owned source/candidate/span component bytes and digests.
3. Reuse Buddy's candidate admission, source, semantic, identity, and parent checks. Build Core's V2 candidate with the frozen review time and the semantic artifact/source pins in its diagnostics. Preserve the original proposal ID as the Core plan identity.
4. Check Core `get_for_plan` before rebuilding. An exact stored review supplies the original candidate, actor, time, verdicts, and review ID. Publish or recover that review. Any change in selection, artifact, actor, time, source/candidate pins, or parent is an idempotency conflict.
5. Recheck the publication against the stored review and exact accepted assertion IDs before returning its receipt.

## Evidence and limits

Focused synthetic tests cover denied capability with zero source/Core access, rejected/deferred selection, run byte closure, actual review time different from parent creation time, first publication, lost finalize and publication responses, exact in-memory concurrent retry, and conflict on selection/artifact/actor/time/source drift. Existing managed-target and reviewed-relation tests were also run. A disposable pgvector PostgreSQL test covers stored-review recovery, concurrent publication retry, repository recreation, and exact replay.

These tests use synthetic source and graph facts. They do not authorize or prove the separate real C1S1 rehearsal, current-probe reanchoring, operator dogfood, public transport redesign, or any production publication. PRIME independent review is required before merge and before a separately bounded real-data attempt.
