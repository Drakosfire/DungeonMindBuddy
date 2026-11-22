# DOGFOOD: retain full long-chat context without searching again

ACTIVE, directly authorized by Alan to continue #4459, fix its remaining gaps and
deploy. DOGFOOD designs/owns this bounded Buddy runtime slice. No Core changes.

Topology: stacked implementation, serial delivery. Parent serving source a5c7599c3c32731785de4562ced073cadf392e07 (APP0192),
which includes #4472@40c51d4f and the Plan author focus fence; then this
retained-context slice with APP0193 reader fence. Branch
codex/dogfood-long-chat-context in the existing managed dogfood-lore-review
checkout. Review against an owned frozen copy of that parent; merge/deploy only
after its dependency settles and current serving integrations are preserved.
Current observed serving is a5c7599c3, APP0192. No runtime write lease yet.
#4471 owns image/guest build configuration, #4464/#4469 own activation tooling,
#4466 owns variant portraits; preserve their actual delivered successors.
ADVERSARY and ONBOARDING were notified to flag contemporary overlapping leases.
Parent4472 does not edit this context admission/projection region. Its placement test regions remain read-only here. The shared ordinary HTTP fake
writer and carried-citation expectations are explicitly included only to adopt
the V2 protocol; new long-chat cases use a separate owning test module.

One indivisible capability: frozen conversation closure -> typed APP admission ->
semantic writer projection -> exact producing-request/citation replay -> reader
fence. Splitting these would leave unverifiable bytes or an unreadable receipt.

Problem established from owning source: list_build_dialogue takes6 rows; prior
body admission uses only that window's cited native passages, dropping earlier
saved-page reads/drafts and uncited source material. Prompt instructions cannot
recover omitted text. Reuse is not a new source search or a model summary.

Invariants and review map:
- One transaction-owned, chronological snapshot of this exact World/conversation,
  strictly before current turn, joined to active pointer, revision and attempt.
  No6/50-row semantic cutoff or silent truncation. Current/future/in-flight turns
  and retry self/successor leakage are forbidden.
- Preserve terminal failed-turn USER constraints as intent only. Failed assistant output supplies no evidence. A completed mixed reply retains
  its accepted visible Rules composition and any owner-validated object-only
  review as dialogue. Material requires its explicitly approved base projection. Invalid acquisitions never carry.
- Retain actual successful authorized read/catalog closures and exact earlier
  authored snapshots. Preserve original producing IDs/attempt and source revision;
  the new admission sequence owns current inclusion. Do not fabricate a new read
  or a prior-completion citation. Source/World/access checks stay with owners.
- Saved/draft/related authored text remains historical author context, not current
  page state or played truth. Preserve revisions, corrections, retractions and
  every chronological occurrence even when exact payloads share storage.
- V2 admission is a closed extension of V1, with frozen full dialogue and retained
  material. V1 producing-input/citation/reopening bytes remain reconstructible.
  V2 actual request verifies full dialogue as well as native/work frames.
- Model projection contains text, meaningful source qualifiers and local aliases;
  all IDs/hashes, pointer/revision/attempt and accounting stay host-side. No new
  provenance authority, cross-chat memory, ranking or lossy summary.
- Existing writer capacity checks account for the complete request. Over-capacity
  refuses explicitly before dispatch, never triggers search or drops old facts.

Expected exclusive writes: this handoff; predecessor authored-context-coverage
and world-page-context handoffs for backward-looking settlement; new
src/application_state/agent_conversation/retained_conversation.py; types.py,
repository.py, service.py, native_execution.py, native_corpus.py, native_writer.py,
native_build_work_view.py and context_trace_store.py in that package;
apps/live_control_server/services/build_jev_harness.py and plan_jev_writer.py only
for Build retained-context projection; agent_native_source_sections.py only for
current-principal reopening through a retained read's original catalog authority; new migration0193 with parent0192;
new tests/test_build_retained_conversation.py, the ordinary HTTP fake writer and
carried-citation expectations, and focused codec tests as needed.
CI inventory is included only for the one new backend module: its world-and-content
contract argv entry and domain-integration classification entry. This is a logical
path split from ONBOARD guest-release entries, with no overlapping behavior or
line ownership; ONBOARD was notified. Do not alter placement, Plan retrieval, Rules,
provider/model, lockfiles or unrelated activation code.

Validation: ordinary HTTP >6 and >50 turns; early uncited source read, no editor
snapshot and changed current document; saved revision changes and retracted ideas;
failed/retried/mixed turns; foreign World/chat/principal and stale pointer/attempt;
exact dedup with chronological occurrences; tampered unused context/prefix denial;
V1 replay and old-reader fence refusal. Count new source/provider acquisition
separately from APP receipt loading. Run exact-SHA owning backend contracts and
required frontend verifier, independently review cumulative diff, commit/push/PR.
Then real-provider long-chat replays, explicit latency/failure-rate evidence,
compatible recovery rehearsal and actual signed-in page/save/reopen/idempotence.
Keep inherited test failures red and all unsuccessful replays retained.

Successors remain serial and undispatched until this scope is settled: align
no-search discussion routing and natural page-title witnesses; diagnose long-chat
output-limit failure with actual provider evidence. Preserve the complete #4459
objective; completion requires deployed actual-app proof, not this first PR.

Implementation checkpoint (working-tree diagnostics, not exact-SHA qualification):
- Full context, repeated reuse and existing carried-page save/reopen: 30 passed,
  180 deselected; retained log /tmp/dogfood-retained-integrated.log. The 60-turn
  admission measured301.0ms initially and73.9–79.4ms on repeated synthesis, decoding
  one completed prefix owner thereafter. These are host admission times, not
  provider or end-to-end latency, and precede the final anchor/reset refinements.
- Late earlier HTTP completion: PASS. A running sequence2 was absent from the
  sequence3 closure; after it completed, the next reuse loaded1,2,3 and preserved
  its constraint. Anchor optimization requires every prior row completed and
  present at its exact attempt/sequence. Otherwise use the full row set, without
  implicit seeding. Completed mixed Rules dialogue and validated object-only
  review remain visible; only an approved base supplies reusable material.
- Actual reset before capture and before writer dispatch: both PASS with no
  physical writer call. The writer rechecks the exact captured pointer revision.
- Mixed APP/HTTP output and codec/scope/overlap/reset focused checks:19 passed,
  2 deselected. CI inventory guards:17 passed with Node22.23.0. An earlier guard
  run failed because Node was absent from PATH; retain that failed diagnostic.
- Exact-source contracts, hosted verifier, independent exact-head review and live
  provider/app acceptance remain pending. No release-qualified or deployed claim.
