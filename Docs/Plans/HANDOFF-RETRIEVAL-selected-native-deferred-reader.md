# RETRIEVAL: deferred Graph reader for selected native sources

Status: ACTIVE design and reader compatibility under the user's over-retrieval
objective. Root owns the serial lane. Base: serving branch
`codex/coverage-capability-serving-base` at `32a446fc221dd60c2fc68cc8f0f69f47bf3a59a0`;
checkout `Projects/.codex/copy-revision-serving/DungeonMindBuddy`, branch
`codex/retrieval-selected-native-reader`. Reader precedes any producer; merge and
production rollout must follow the actual serving lineage and reader-first order.

## Problem and boundary

Case 496 supplied an exact native source and produced a correct cited answer,
but the legacy Surface-native Build route prepared a Graph query and an App page
catalog before it knew whether additional sources were requested. Its probes are
partial and it is development, not held-out, evidence. A selected source is not
proof that the request excludes other sources. Graph objects, mixed requests,
stale or foreign references, incomplete selected evidence and retries must not be
silently treated as selected-source-only.

The first reader slice may add a distinct, versioned deferred Graph commitment for
ordinary Build with nonempty, exact native source selections only; it must bind
the immutable selected manifest and existing World/source/revision authority.
The commitment expresses pending Graph work, not an empty or unavailable result,
and supplies no evidence authority. Historical receipts retain their existing
meaning. New producer behavior, controller questions, lookup decisions and
catalog acquisition are out of scope. The current eager App catalog is retained
for the Graph-only producer; a separate successor will defer it. No new record may be emitted in production
until the reader is reviewed, deployed and verified.

Before implementation, prove how the existing captured-reference and exact
source-read events join to the pending commitment and how the writer distinguishes
successful selected-source evidence from missing, rejected or unattempted reads.
Graph work must require the existing authorized settlement and preserve mixed
requests. A deferred App catalog needs an explicit later discovery boundary; an
empty frozen catalog cannot mean unobserved. Keep source and prompt metadata
bound to host-owned validation, not provider-visible identifiers.

## Expected write lease and validation

Reader owners as needed: `src/application_state/agent_conversation/native_context.py`,
`native_execution.py`, `native_corpus.py`, `native_reads.py`, `native_writer.py`,
`native_replay.py`, `authored_graph_references.py`, `writer_evidence_selection.py`
(selected-source terminal reader), `service.py` and
`apps/live_control_server/services/agent_turn_service.py`,
`apps/live_control_server/services/native_authored_references.py` and
`apps/live_control_server/services/build_jev_harness.py` (existing-record
opening, resume and citation projection readers only), and corresponding strict API
codec or frontend reader files if a real recorded state reaches them; focused
boundary tests and this handoff. Do not edit runtime producer routing in this
slice. If the invariant requires another owner, revise the boundary before edits.

Focused tests must cover old frozen records, exact new commitment and source
manifest, source-only successful evidence and citation reconstruction, changed
World/revision/section, Graph object and mixed-reference rejection, unattempted or
unavailable source, provider and read ordering, Graph settlement, interruption
and replay. Inspect the entire base-to-head diff and obtain independent exact-head
review. Record any missing evidence honestly; no goal completion is implied.

The Graph-only producer successor is serial and not yet assigned: it must adopt a
reviewed source-only versus mixed-request contract, retain current App catalog
behavior, replay negative and required-source controls, and deploy after this
reader. A separate serial App-catalog reader and producer must then establish
post-decision discovery rather than treating an unobserved catalog as empty.
Both require signed-in verification. The full objective spans all these slices.

## Local checkpoint

The reader-only candidate recognizes a distinct source-manifest-bound pending
query and does not create it for fresh requests. Focused model tests cover a
real in-memory Core source and citation reopen, incomplete/duplicate reads,
changed manifests, revision and binding mismatches, mixed object selections,
old and new Graph settlement proofs, and pending/settled replay projection.
The focused UI protocol test and a targeted TypeScript check passed. Tests do
not yet prove an ordinary HTTP turn, full persisted-Turn recovery, a revoked
access boundary, or reader rollback in a deployed app. Obtain independent
review and those missing boundary proofs before claiming compatibility.

Independent review of initial head `bde25e92b0842cfae2571a9ffa892615c00531bf`
held the slice because selected source reads had no completion terminal and a
resume would enter Graph retrieval. The follow-up adds an exact selected-source
terminal, refuses an incomplete pending selection before constructing a Graph
driver, and exercises the actual Build completion branch with an independently
constructed source execution and provider-free writer. It does not establish a
full persisted-Turn interruption/recovery or revoked-access boundary; those are
still required before reader activation.

The first real App reclaim attempt (case 517) failed: the existing claim owner
increments the attempt after a pre-provider crash, but native authored-capture
validation required the capture's original attempt to equal the new one. For
this new codec only, recovery may retain an earlier capture from the same turn,
conversation and fingerprint. The existing claim owner forbids reclaim once
any provider authorization exists; this is essential to that allowance. Verify
both sides at the real App boundary before accepting the change.
