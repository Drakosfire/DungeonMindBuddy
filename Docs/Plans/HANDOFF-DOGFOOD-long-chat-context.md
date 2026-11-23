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
  or a prior-completion citation. Historical authored snapshots follow the existing
  agent_saved_sections contract: typed original ownership and current World/turn
  authorization, without a current-page lookup. Discarding or changing the old
  page does not erase authorized conversation context. Native citation reopening
  retains fresh Core principal checks.
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
model_markdown.py only for the new retained-source presentation helper,
native_build_work_view.py and context_trace_store.py in that package;
apps/live_control_server/services/build_jev_harness.py and plan_jev_writer.py only
for Build retained-context projection; agent_native_source_sections.py only for
current-principal reopening through a retained read's original catalog authority; new migration0193 with parent0192;
new tests/test_build_retained_conversation.py, the ordinary HTTP fake writer and
carried-citation expectations, and focused codec tests as needed.
CI inventory is included only for the one new backend module: its world-and-content
contract argv entry, domain-integration classification entry, and corresponding
selector expectation in tests/test_ownership_ci_partition.py. This is a logical
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

Exact80c checkpoint and scoped corrections:
- Hosted verifier and retained-evidence validation PASS:1474 passed,0 failed,
  154 pending; build/parity/cleanup PASS. Ingestion/review913 passed,9 skipped.
- World/content511 passed,2 failed,2 skipped; saved readers562 passed,31 failed.
  All32 non-inventory failures reproduced on exact parenta5c in the same locked
  environment. Full IDs/traces are retained in the80c verification evidence and
  parent-failure-comparison.json. These contracts remain red, not release-qualified.
- The one new inventory guard failure identified its missing selector expectation;
  correct that expectation with the new module registration.20 CI guards now pass.
- Exact80c real-provider unmounted onboarding replay PASS:5548ms first draft,
  49ms save/reopen, one page, identical repeated receipt, zero synthesis acquisition.
- The frozen Maelthor replay exposed an excessive current-page metadata gate on
  historical authored snapshots. Align with agent_saved_sections.open_saved_section:
  typed original read ownership and current World/turn authorization; no current
  page lookup. Changed-current-page plus discarded-original-page HTTP regression
  and remaining focused cases now pass20/20 (60-turn case excluded in that check).
- A later diagnostic briefly edited CI/documentation files in the verification
  clone after its contract runs completed; it was restored clean. Treat that
  Maelthor diagnostic as nonqualifying and repeat on the final isolated commit.
  Earlier exact-source frontend/backend results are retained at their own SHA.

Projection checkpoint: actual frozen context contains generated Buddy navigation
URLs and a PDF provenance fingerprint embedded in old Markdown. V2's current model
presentation must project these structural fields before dispatch, preserving raw
read/citation bytes. Keep the earlier experimental V2 full presentation as an
explicit historical codec only, and refuse new dispatch using that old policy.
This is required by the existing model-prompt boundary, not a new retrieval grant.
No current exclusive overlap: ONBOARD4489 changes surface_evidence_answer.py and
native completion tests, not this retained-source projection.

Exact0bb checkpoint:
- Hosted retained evidence validates. World/content512 passed,1 inherited failure,
  2 skipped; ingestion/review913 passed,9 skipped; saved readers562 passed,
  31 inherited failures. All32 failure IDs match the exacta5c comparison.
- A real interrupted-turn60-history diagnostic passed. Repeated full fallback
  admission took286–312ms with zero new native acquisitions; no speed waiver or
  silent truncation is needed for the conservative failed-turn fallback.
- Frozen12-turn Maelthor: HTTP200, all context retained; draft16953ms and
  save/reopen4330ms. An independent local semantic audit confirms both cited
  original reads support the dream/password claims and preserve authored premises,
  corrected directions and open questions. The older last-citation-SHA assertion
  remains visibly false: V2 selected an earlier valid Session6 extent12–29 from
  frozen turn7 rather than the later full1–29 extent. Revised acceptance requires
  exact original read/source identity, exact reopened bytes AND claim-specific
  support, never source-tuple equality alone. Latency remains a successor gap.
- Final prompt audit found one generated navigation UUID and one PDF fingerprint
  inside old source text. The new current presentation uses structural Markdown
  projection for owned links and the standalone provenance field. Raw source bytes
  and historical producing requests remain available. The earlier full V2 policy
  is replay-only; new dispatch requires the semantic policy.16 pure checks and
  23 focused cases pass; the real retained material projects to zero UUID/hash
  values. A completed earlier V2 record still decodes under its full policy.
- Diagnostic lower lore effort plus existing immutable Source cache preserved
  fresh access contexts and reduced draft to13266ms/save to530ms, with0cached
  provider tokens. These runtime monkeypatches are not product changes or final
  latency acceptance. Provider/model identity is unchanged; successors need review.

Review cycle3 HOLD at ae784: owned-link projection flattened mixed paragraphs,
losing external destinations/formatting, and an owned autolink retained its UUID
as visible text. Replace whole-block rendering with parser-owned source spans;
project only owned controls and managed images, including nested image labels,
reference definitions, source line endings and human link-title qualifiers.
Ten focused projection/presentation regressions pass. The initial broader command
without the disposable DB environment failed fixture setup (12 passed,1 error);
repeat through the isolated DB helper, retaining that diagnostic as a setup error.
No merge/deployment or exact-current-source pass is claimed at this checkpoint.
