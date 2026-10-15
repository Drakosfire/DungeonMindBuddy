# AGENT: selected-subject source hydration

Status: DONE for the bounded source-delivery implementation. PR1177 merged
49cb3570fff19504ea46b9db5daeffc83bd9aa6f after two independent review cycles.
Reviewed head adbe38e9069907e30b71389079327cf68f8712a4. No serving adoption
or retained publication implied; full Mirathorn lifecycle remains incomplete.
PRIME owns design/solo implementation. Base d92a916220fe1d800936cfffe25288f9f770aad4.
Serial replacement of the negative policy experiment, not dependent on its
unmerged instructions. PR1176 remains frozen/HOLD. Explicit parallel-independent
exception for DOGFOOD's operator-authorized Build workspace integration: its
surface-context/request/turn-service/UI paths are disjoint from this lease.
No serving runtime or retained database lease. Use isolated disposable clones.

## Invariant and boundary

A fresh ordinary Agent query with ONE explicitly selected native Graph subject
receives bounded exact opened support from that subject's admitted claims before
the model runs. Reads cross existing native source authorization, integrity and
revision checks. Passages remain source statements, not new accepted Graph facts.
No gold-specific IDs/keywords, corpus search, summarization or inferred chronology.

Eligibility: fresh session only; server-resolved selected-object envelope
`excerpt_policy=provenance_context_not_citation`, one matched subject, exact
World/revision/scope/admissibility equality; GM only initially. Derive anchors
only from already admitted claims whose subject OR object is that selected node,
and intersect with the session's readable admitted anchors. Preserve unavailable
support as coverage gaps. No neighborhood expansion as an implicit read seed.
Source observations use the existing selected-observation admission first.

A Build document's saved artifact/revision/digest and native subject selection
are DISTINCT inputs. DOGFOOD owns saved-source binding/admission through shared
surface contracts. This helper must not derive a subject from title, document,
source artifact, editor draft, or surface identity, nor replace that identity.
Without explicit selected native subject this slice does no reads. Supplied
sessions and Player/redacted contexts keep existing behavior (no automatic reads).

## Bounded execution and truthful evidence

Deduplicate anchor IDs; deterministic lexical ordering independent of input order.
At most 16 anchors, batches of at most 8 using existing read_graph_source executor
receipt_version=2. Maximum 24,000 returned characters in total and 3,000 per
anchor; distribute remaining budget across each batch and never truncate copied
content independently of native read results. Character budget is not token or
billing count. Report declared support count, selected/read/opened/unread counts,
truncation/denial/unavailable/budget gaps. Complete means ONLY that declared
selected-subject support set was successfully read without truncation. It never
means complete corpus/World knowledge or established current fictional state.

Each delivered body must have genuine nonempty content, exact matching anchor,
World/Graph revision and receipt, source identity/revision/hash, original outcome
and truncation flags. Existing read receipts remain attached to session state;
pass exact source-qualified bodies and coverage in initial model context for BOTH
harness adapters. Propagate source_reads in existing private session projection;
existing hydrator already validates SourceReadEntry. Do not fake tool events,
claims, citations or opened states. Record reads as server_initial operations.
Missing/malformed/foreign replies yield gaps, never model-visible content. Avoid
partial mutation making unverified content citeable; use the atomic-batch rollback contract below, preserving prior valid batches.

Only existing native admitted source access is permitted. No provider calls in
implementation tests. Later exact-head ordinary diagnostic needs independent
review first and durable invocation/runtime-result/product/transport evidence.
Existing standing operator provider approval applies; no uncertain replay.

## Exclusive prospective write set (only ACTIVE grants lease)

- this handoff
- apps/live_control_server/services/selected_subject_initial_sources.py
- apps/live_control_server/services/agent_context_assembler.py
- apps/live_control_server/services/hermes_graph_agent.py (scope rendering only)
- apps/live_control_server/services/pydantic_ai_agent_runtime.py (scope rendering only)
- src/graph_memory/interaction/session.py (source_reads projection only)
- tests/test_selected_subject_initial_sources.py

DOGFOOD must serialize any need for those paths through PRIME. No edits to
agent_surface_context.py, agent_turn_service.py, source resolvers/requestmodels,
WorldAgentConversation or WorldPlanAgentConversation in this slice.

## Acceptance and completion

Owning initial-invocation tests: direct subject plus incoming/outgoing support,
dedup shared paragraph, permutation-invariant selection, critical synthetic
support beyond first batch, counts/budgets, unreadable/denied/truncated/malformed/
wrong-revision/source-integrity failures, Player exclusion, supplied-session
no-replay, no selected subject no read, no alteration of admitted claims/source
bytes/surface context. Verify both model-context renderers and private session
projection/hydration preserve genuine receipts. Do not add a new public schema.

Real registered disposable clone + fresh spawned ordinary runtime must prove
actual initial delivery, openable citations and frozen semantic gold separately;
all original objects unchanged, clone dropped. Negative outcomes stay immutable.
Review exact cumulative diff and independent tests; commit/push/PR; PRIME merge
only after applicable gates. No retained publication, full Mirathorn lifecycle,
restart/history or operator acceptance is pre-marked complete.

## Activation clarifications (binding implementation contract)

- Re-anchored remote main remains d92a916. ARCH reviewed40d266a5 and requested
  these clarifications; ARCH subsequently accepted exact9403d3f9; PRIME activates this portable
  pinned handoff under ecosystem core rule3. Main merge is not an activation gate.
- Declare deduplicated support IDs BEFORE session readability intersection or
  cap. Missing/unreadable IDs remain coverage denominator/gaps. Cap overflow is
  explicitly unread, never source/corpus completeness. Only selected subject
  claim support is included; irrelevant anchors never become implicit scope.
- Per-anchor maxChars=min(3000, remainingCharacters//remainingSelectedAnchors),
  recomputed between batches with the same cap for every member of that batch.
  Existing executor maxChars is PER ANCHOR. Subtract actual returned characters
  only after validated batches. This reserves a fair share for later anchors.
- Use ATOMIC BATCH rollback: snapshot entire session before each executor batch;
  if response count/uniqueness/identity/receipt/snapshot/budget checks fail or an
  exception escapes, restore that snapshot and store the replacement session.
  Deliver no bodies/receipts from that batch; mark every attempted anchor a gap.
  Earlier validated batches survive; valid siblings in rejected batch are
  intentionally lost and disclosed. No local body slicing or automatic retry.
- Authentic partial/truncated bodies may be delivered with original flags and
  receipts, count as opened but not complete. Denied/unavailable are disclosed
  non-content outcomes, not malformed successful reads. Batch integrity failures
  cannot leave newly opened/citeable state. Declared/eligible/selected/attempted/
  opened/truncated/unread counts remain distinct.
- Helper returns exact genuine read result+receipt+sourceReadId in private
  initial_opened_source_reads, plus initial_source_read_coverage. Assembler adds
  these to the existing flexible private AgentRetrievalSession.packet; BOTH
  scope renderers expose them as openedSourceReads/sourceReadCoverage. No new
  accepted claims/public request schema. SourceReadEntry metadata+operations
  are separately projected through private session IPC so hydrator and final
  citations retain real reads; bodies need not persist in returned session.
- Validate expected anchor and claim evidence refs; result/receipt source IDs,
  source revision/digest, readID/sessionID, and snapshot World/campaign/scope/
  admissibility/focus/Graph revision must agree. Native v2 remains source-body
  integrity authority. Its contentSha256/read_content_sha256 denote SOURCE
  revision digest, not returned snippet hash; preserve that meaning, never
  require a paragraph hash to equal a whole-document hash. Exact returned body
  hashes can be supplementary diagnostics without changing native receipts.
- Predecessor1175 is merged d92a916;1176 is frozen negative experimental policy,
  not an accepted dependency. This successor starts on accepted main policy.

## Settlement

Cycle1 held5c3d5481 for contradictory non-content replies preserving citeable
successful read state. Corrected adbe38e9 passed independent36tests and cycle2.
Exact corrected-head ordinary disposable-clone trial delivered9/9 source bodies
(including the previously unread realization) in first provider request; useful
cross-source explanation independently accepted with attribution qualifications.
Three provider calls;126234 reported inputtokens,1432outputtokens; estimated API
costUSD0.00689891, actual billing unknown. Fourteen genuine source citation
entries are receipt-backed; UI clicking/fresh-process/restart not proved by that
trial. All525 original objects unchanged; disposable clone dropped.

Private evidence: thalia-ordinary-hydrated-support-1 under owned experiment root.
No full three-case gold acceptance, selected-World completeness or retained
worldbuilding publication claim. PR1176 negative policy experiment is superseded;
its instructions are not part of this implementation. Implementation write lease
is released; downstream work must re-anchor and name its own bounded lease.
