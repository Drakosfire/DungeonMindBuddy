# Plan authored references

Status: MERGED_AND_DELIVERED; Plan acceptance remains open. Owner/designer: PRIME. Authority: active reference integration goal.
Topology: serial after merged #2092 at
4147f915a9f54793bef9f007a9a7e2e22fc0c7b6. Branch
codex/plan-authored-references; reuse buddy-context-loop and its dependencies.
Implementation lease only; no runtime, primary-data, dependency or provider lease.

## One outcome

An ordinary saved Plan question or editable Plan proposal carries the author's
selected native objects, sources and exact passages through submission, required
reads, the actual writer, citations and retained request recovery. Preserve the
Plan draft, captured placement and existing preparation context. Include means
additional authorized retrieval remains permitted. No Only-selected control or
Play activation is included; both remain full-goal successors.

The current Plan already uses the shared native query/execution/writer. The
remaining gap is the Build-only input/acquisition gate, not a new search system.
The current generic reference union and native readers are already suitable.

## Adoption and demolition

Reuse AuthoredReferencesV2, native object/source discovery controls and readers,
current APP capture/read events, exact input fingerprints, native writer V2 and
claim/citation validation. The human request remains the read authorization; do
not manufacture a Jev selection. Existing native capture events have generic
identity fields despite their historical Build names; retain one owning ledger.

Extract the native host capture/acquisition branches from the Build-only host
module into one shared native owner used by both real Build and Plan callers;
remove the moved branches, rather than leave two executors. The distinct classic
Build recovery reader remains limited to its actually exercised historical callers;
it must not receive the new Plan reference intent. Its full-goal retirement stays
open. Preserve source-only reading without an object Graph.

Introduce only the closed Plan intent variant needed to freeze the new author
input, and the closed semantic-request variant needed to present that input to
Plan's destination decision. Both bind to the real selected references and Plan
work. Historical input decoding remains exact; no source/version substitution,
new ledger, index, endpoint or publication authority. Fence new durable records
with a no-op forward reader revision. Do not rewrite retained rows.

Adopt the existing composer/pending recovery owner with separate Build/Plan draft
keys. Preserve existing Build draft bytes and malformed-copy recovery. A Plan
selection must not leak into another Plan, World, surface or newer composer draft.
Test interrupted work at the owning boundary; do not reinterpret old captured
attempts as new authority or automatically resend an outcome-unknown request.

History inspection is part of this same recovery outcome: project the existing
capture into a read-only authored_references history field instead of borrowing
Build retry authority for Plan. No new store or read grant. Adopt it in active
history and library views, with closed existing reference variants.

The older manual Plan edit/continuation route is a separately selected adoption/
demolition successor. This slice must refuse to silently drop its selected input;
ordinary native Plan messages already support editable proposals. Keep retained
older edit reviews and current author choices intact.

## Expected write lease and review map

Input and retained identity:
- src/application_state/agent_conversation/types.py
- src/application_state/agent_conversation/native_retrieval.py (required-read sequencing gate)
- src/application_state/agent_conversation/plan_jev_decision.py (exact semantic input decoder)
- src/application_state/agent_conversation/native_execution.py
- src/application_state/agent_conversation/native_context.py if actual typed adoption requires it
- src/application_state/agent_conversation/authored_graph_references.py
- src/application_state/agent_conversation/service.py (existing append/admission owner only)
- src/application_state/agent_conversation/library.py (read-only captured-input projection)
- src/application_state/agent_conversation/plan_placement.py
- src/application_state/agent_conversation/plan_authoring.py
- src/application_state/agent_conversation/native_writer.py
- src/application_state/migrations/versions/*0109*

Existing host pipeline:
- apps/live_control_server/models/agent_turn.py
- apps/live_control_server/routes/agent.py (native Plan normalization/query only)
- apps/live_control_server/services/agent_turn_service.py
- apps/live_control_server/services/build_authored_references.py (remove native branches)
- apps/live_control_server/services/native_authored_references.py (moved shared native owner)
- apps/live_control_server/services/build_jev_harness.py (adopt moved owner)
- apps/live_control_server/services/plan_jev_harness.py
- apps/live_control_server/services/plan_jev_dispatch.py
- apps/live_control_server/services/plan_source_turn.py if its actual freeze is coupled

Surface input and recovery:
- apps/live-control-ui/src/api/types.ts and buddyContextTraceTypes.ts
- apps/live-control-ui/src/api/conversationLibraryApi.ts and its owning tests
- apps/live-control-ui/src/agentInteraction/ConversationLibrary.tsx (read-only input display)
- apps/live-control-ui/src/agentInteraction/authoredGraphReferences.ts and tests
- apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx
- apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx
- Existing Plan pending/request validators and their owning tests if concrete callers require them

Tests/authority:
- tests/test_plan_authored_references.py
- tests/test_native_plan_assertions.py, test_native_plan_statements.py,
  test_surface_native_writer.py, test_surface_native_build_ordinary.py and existing
  authored-reference/Plan semantic/recovery tests where actual fixtures require adoption
- .github/workflows/world-ownership-core.yml: query suite test path only
- This handoff and predecessor HANDOFF-REFERENCE-native-writer-projection.md settlement

Shared API-type/CI partitions remain separate from ADVERSARY ingestion changes.
No ingestion, extraction, source admission, publication or benchmark/gold changes.
Inspect concrete callers before editing; checkpoint and split a newly discovered
independent capability rather than absorb it into this PR.

## Owning validation and delivery

Exercise authenticated Plan submission through real APP/native acquisition and
actual SDK writer input with provider-free transports. Cover objects, sources,
sections, mixed references, source-only authority, changed/revoked/foreign versions,
required inclusion, partial reads and tampering. Verify Plan writing retains its
captured placement and page draft; a selection never grants publication or an edit.

Exercise composer drafts, pending/interrupted recovery, changed work/World,
explicit retry where offered and outcome-unknown refusal. Protect newer drafts
and existing Build behavior. Review the exact cumulative diff independently,
commit/push/open this one owning PR, then merge/deliver after gates. Ordinary Plan
dogfood and operator acceptance remain required; tests alone are not completion.

Predecessor #2092 is merged and live in compatible runtime
df915c84fa446216a45a16ada7d24457f61e0145 / APP0108. The ordinary Fellinor retry
71786e11-e5dd-4d6f-92ff-ce66eb5ecaf0 completed with all three requested references,
opened citations and reload/reopening proof. Prior failed attempts remain intact.
This does not establish Plan or Play reference acceptance.


## Delivered predecessor and live failure

Merged #2096 at ee4279013b0d07f5458da237dfa8c87a29845aa8 after exact-head
independent review and all seven CI gates. Delivered compatible live union
6f82cd82662bf861065c3ea9efd9de291d5cd1b0 / APP0109 with API/UI health and
unchanged APP/Core/session state except the no-op migration row. Runtime lease
released. Ordinary Plan selection found Fellinor and filtered C2 Session 29;
its exact selected passage and question were retained, with Retry available.
The resulting turn407c3993-f392-4dd4-915e-67ced8266fc8 failed at the existing
APP ledger size check after successful Core reads. This is not Plan acceptance.
HANDOFF-REFERENCE-assertion-source-locators.md owns the bounded follow-up; original
failure, frozen source/revision and private replay evidence are preserved.
