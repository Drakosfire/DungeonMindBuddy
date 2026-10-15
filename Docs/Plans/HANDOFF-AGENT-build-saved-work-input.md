# AGENT: carry admitted Build source through the harness input boundary

Status ACTIVE after ARCHITECTURE design PASS on117e110d006390720b5b576d20015702de302cf6. PRIME designs and
implements solo. Base13a4d89a05758c45547690e6b9c2e40f97216d9a. Branch
codex/build-saved-work-harness-input, isolated non-serving checkout
/tmp/buddy-advisory-review-design. Serial: one implementation PR.

## Outcome and evidence

An admitted saved Build source larger than8000 characters must reach the actual
Agent Harness worker seam intact, without being misclassified as a public user
question or a Plan continuity turn. No provider call is needed for the code proof.

The frozen Mirathorn revision2 SHA70444f40b9f16976f55620a72f802b1201efe56014a61343bb45811a33570342
has22272 UTF8bytes; BuildSavedSourceBasis.invocation_message assembled23246chars.
The actual host serializer rejects this with question exceeds max length8000 when
plan_continuity_turn=False. Private offline proof /tmp/build-source-host-limit-reproduction.json.
This proves a reproducible contract mismatch. It does NOT identify the exact stage
or provider outcome of original failed live turn4d843106-39d7-4c84-a74a-0462fd85beb5:
its durable protocol error/absent trace cannot prove whether inference occurred.
No retry of that turn is authorized by this handoff.

## Contract

Add internal input_kind discriminator: ordinary_question default and
server_assembled_saved_work. Only trusted server assembly after saved source
owner/revision/hash/visibility admission sets the alternative for Build. Public
AgentTurnRequest cannot set it. Never infer authority from message JSON or size.
Propagate neutral invocation -> Hermes request -> strict serializer/deserializer.
Reject unknown/wrong types in both directions; absent/default preserves ordinary
behavior. This discriminator changes only assembled-input size admission.

Keep public questions and ordinary internal questions limited to8000chars. Keep
Build source UTF8cap, actual TOTAL encoded MAX_WIRE_BYTES and final provider-envelope
budget independently enforced. No truncation or treating source allowance as total
wire allowance. Preserve exact admitted source/question/document/revision/hash.

Build stays plan_continuity_turn=False; do not select persistent Plan profile or
change capability, provider authorization, Graph scope, model, history, persistence
or write permissions. Existing Plan size exception and continuity behavior remain
unchanged; no Plan refactor in this repair. PydanticAI consumes invocation.message
without this host cap; trace and verify its unchanged behavior rather than adding
an unused flag consumer. No new source basis/ownership authority/body duplication.

## Exclusive prospective paths

- this handoff
- apps/live_control_server/services/agent_runtime.py (input kind only)
- apps/live_control_server/services/agent_turn_service.py (admitted Build producer only)
- apps/live_control_server/services/hermes_agent_runtime.py (adapter mapping only)
- apps/live_control_server/services/hermes_graph_agent_contract.py (strict symmetric IPC)
- tests/test_build_saved_work_harness_input.py (new owning pipeline/adapter/host tests)
- tests/test_hermes_graph_agent_contract.py (changed contract cases only, if required)

Current1180/1181 are merged and settled. Historical MIND PRs remain frozen;
DOGFOOD UI lease released. SERVER owns current runtime diagnosis/rollout; no
product-path overlap. No ports, serving processes, retained native DB, schema,
provider calls, credentials or source edits leased here. Unique disposable APP
fixtures may exercise real saved-source admission; fixture DBs drop finally.

## Owning proof and completion

Exercise actual saved-source admission -> service assembly -> actual Hermes
adapter/host serialization with synthetic Unicode Build source >8000chars, saved
pins/content intact at worker seam and Plan continuity false. A roundtrip/helper
alone is insufficient. Test wrong source pins remain rejected and no public field
can widen input; ordinary/public >8000 reject; malformed discriminator rejects
both directions; absent/default and existing Plan behave unchanged. Total encoded
wire overflow and final provider-envelope budget reject before provider execution.
No provider/model fixture may dispatch real inference. Preserve controlled errors
without source-body logging. Confirm PydanticAI needs no matching change.

Implement/test/cumulative diff/commit/push/PR, independent exact-head review before
merge. Only after accepted code and separately coordinated matched rollout may a
NEW ordinary live question use existing standing Agent approval. Preserve the
original failed turn and its unknown execution outcome. Live success is a separate
gate; do not claim full graph ingestion/publication or operator acceptance.

Activation: current main13a4d89a re-anchored, open relevant product work1178/1180/1181
merged; no active overlapping seven-path lease. SERVER/DOGFOOD serving ownership
remains disjoint. Independent implementation review required before merge.
