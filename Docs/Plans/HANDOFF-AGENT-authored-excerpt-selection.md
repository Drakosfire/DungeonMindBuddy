# AGENT — select authored blocks; materialize exact text in the host

## Settlement at successor design

Implementation #1617 merged `df98f6a5a554ac7ef234b1196b4f8dd3377d178a` after
Bugbot approved exact head `ebb61c13ee520eeddbbad5e64f086ce06c4c9302` in cycle2.
The P2 historical Play policy collision was fixed by current-submission binding;
independent89 backend/22 unchanged UI checks passed. Guarded API/UI adoption on
8000/5202/APP0048 preserved1757 pre-migration APP rows, native rows,79 mechanics
files and17 frozen components. Implementation write lease is released.

Original swamp/Edge, notes/reflections rendered acceptance and post-answer
protected restart remain pending under the active goal. No successful new
benchmark reply or full journey is claimed by migration health. The operator
selected connected scene/encounter/revision design as the next milestone; the
roadmap retains these residuals. Historical activation below is not a live lease.

## Authority and topology

PRIME owns this bounded successor under the operator's active local Buddy goal.
Base: `319e45fac00b4ae2152e5a0d895ac60e5e2f0866` (#1615), live8000/5202,
APP0047/native0017. Existing checkout `buddy-context-loop/DungeonMindBuddy`,
branch `codex/agent-authored-excerpt-selection`; no new worktree/environment.
Fresh remote/open-PR census found no overlapping implementation.

Topology **serial**: one design-contract PR, then one dependent implementation PR.
The original #1616 PR was design-only. The design gate was satisfied by #1616; implementation was **ACTIVE** under the
exact activation below after exact-head Bugbot review and PRIME adoption. That is a technical gate, not a new
operator-permission request. Activation records the reviewed contract/head and
exact implementation base before runtime edits. Location alone grants no authority.

Architecture critique from authorized chat `01a086f2-c457-7b10-b753-df6063cab1ce`,
turn `01a165ce-9d5f-79e1-b14e-fd3c15273cfc`, is adopted below. No compatibility
live route, private adventure fixture, additional model/judge/retry, arbitrary new
character/token limit, or Core/OverMind runtime dependency is authorized.

## Reproduced failure

After #1615 delivery, the original swamp/Edge question admitted five exact retained
passages with zero fresh source reads. All three model responses were acknowledged;
accepted-to-terminal time was9.042s. Final delivery was interrupted. Pure read-only
reconstruction from the saved exact producing request/output reproduces
`Authored claim must be a literal frozen excerpt`: the model regenerated a799-char
Plan quote that was not a literal raw substring. Validation correctly rejected it;
no Plan edit occurred. Private original bytes and traces remain local.

The current wire `authored_quote` requires source_handle plus generated text.
Asking the writer to copy formatting is avoidable work and a delivery failure
point. The repair is explicit selection of host-owned exact blocks. Do not loosen
substring checks or normalize the model's output into an alleged quotation.

## Contract

1. **Version current execution.** Introduce a new shared evidence-answer wire
   policy for Plan and Play. An authored segment selects only an opaque block
   handle. Reject model-supplied quote text, unknown/duplicate selectors and
   unexposed handles. Existing source-passage claims remain paraphrasable with
   exact selected citations; proposals stay hypothetical. Preserve historical V1
   readers, but current dispatch must not accept the prior quote-generation shape.
2. **Deterministic exact partition.** A versioned host partition of the frozen
   authored body uses source spans from the existing Markdown parser. Preserve
   top-level paragraphs, lists, tables, blockquotes and fenced code intact;
   preserve supported authored callout containers as complete blocks. Keep every
   raw byte, Unicode character, CRLF, indentation and inter-block separator.
   No trimming, whitespace folding, Markdown reserialization or ellipses. A
   partition is ordered, nonoverlapping and reconstructs the original body exactly.
   Heading paths are display context, never identity. No new parser dependency.
3. **Unambiguous identity.** Bind each block handle to partition version, parent
   source kind/identity/revision, frozen owner/body digest, exact raw byte span and
   block digest. Repeated identical blocks/headings remain distinct by location.
   Session sources include their specific frozen entry identity (kind, element
   selector and/or exact frozen entry ordinal); same text in different entries
   must not alias. Notes/reflections remain supplemental recollections, not recaps
   or Graph facts. Plan and Play retain their original authority distinctions.
4. **Body once in actual input.** Supply ordered handle+literal-block projections
   without duplicating entire authored bodies, reprinting provenance hashes or
   exposing host bookkeeping to the writer unnecessarily. Any versioned Plan
   frame/native Play carrier change must reconstruct and verify the exact original
   frozen owner body/manifest before provider authorization. Selecting a handle
   grants authority only if its exact block was in the actual acknowledged final
   producing envelope. The partition is not a new publication or evidence source.
5. **Host materialization.** Resolve one selected handle to exactly one exposed
   block and produce its literal raw text in the completion. Multiple selections
   produce separate host-materialized excerpts, not concatenated/reformatted model
   text. Add an explicit stored segment/completion version preserving parent source
   handle, block handle, partition version, span and block hash; do not redefine
   `SurfaceAuthoredQuoteV1.source_handle` (whole body/Play manifest source ID).
6. **Persistence and readers.** Revalidate source owner, exact producing inclusion,
   partition and selected span at atomic completion. Introduce one append-only
   migration if closed SQL completion constraints need the new version; do not
   rewrite old rows/migrations. Refuse unsafe downgrade while new retained records
   exist. Shared Plan/Play UI renders useful source names and exact excerpts;
   historical V1 completions and citations still reopen after restart.
7. **Preserve reuse and execution boundaries.** #1615 source-reuse semantics,
   current-request bounds, actual provider lifecycle, Rules composition/final-writer
   fence, reset/claim/replay and existing exposure/completion budgets remain intact.
   This slice does not redesign retrieval decisions, Graph-object reuse, history
   pruning, semantic entailment or inference/model allocation.

## Expected implementation lease

Activation may write this handoff, `HANDOFF-AGENT-retained-passage-reuse.md` and
`../Roadmaps/ROADMAP-demo.md`; shared APP agent-conversation owners
`surface_evidence_answer.py`, new `authored_excerpt_blocks.py`, `types.py`,
`service.py`, `native_answer_output.py`, `native_rules_output.py`,
`plan_jev_graph_packet.py`, `plan_jev_writer_packet.py`, `play_graph_input.py`,
`play_graph_context.py`, `native_graph_input.py`, `rules_authority_completion.py`,
`rules_authority_reads.py`, `surface_source_answer.py`;
new `src/application_state/migrations/versions/20261022_0048_authored_excerpt_blocks.py`;
server services `agent_turn_service.py`, `plan_jev_writer.py`,
`native_rules_runtime.py`, `plan_jev_rules_runtime.py`, `agent_context_trace_collector.py`;
UI `src/api/types.ts`, shared `SurfaceEvidenceAnswer.tsx`/test and
`WorldPlanAgentConversation.tsx`/world-history test under their existing paths;
focused new partition/selection tests and owning existing Plan writer/native Play,
source-reuse, Rules composition, APP completion/history and UI test files.
The activating steward enumerates exact test paths and amends before additional
writes. Lockfiles, old migrations, primary runtime checkout and unrelated lanes
are excluded. The original design PR wrote only the three Markdown files named above.

Runtime lease for reviewed merged delivery: existing owned8000/5202, APP54331,
native54330, current persistent artifact root/Core overlay and immutable rollout
artifacts. No live mutation outside ordinary UI, no direct SQL/API repair, no
restart during design. Preserve all sources, Worlds, drafts, notes, scene/fight
position, mechanics and historical saves.

## Acceptance

- Synthetic exact-span tests cover duplicate blocks/headings/session entries,
  Unicode/CRLF/soft wraps, lists/tables/quotes/code and supported callouts; assert
  byte-for-byte reconstruction and host materialization.
- Reject stale revision, other entry, unexposed/modified block, changed envelope,
  changed partition/span/digest, supplied model text and cross-owner handles.
- Actual Plan and native Play prepared-input-to-APP completion tests cover new
  policy, host text, exact final inclusion, Rules composition and retained history.
  Preserve #1615 hit/miss/bounds/accounting, reset/claim/replay and source-opening
  regressions; historical readers are exercised without a live fallback.
- Verify SQL new-version acceptance/downgrade protection and shared UI; no extra
  provider response or body duplication in the actual prepared input.
- Inspect cumulative diff, commit/push assigned PR, exact-head Bugbot, PRIME merge,
  guarded delivery and protected restart. Ordinary original swamp/Edge query must
  produce a useful cited answer and selected literal Plan excerpt with no source
  rereads when eligible; inspect Debug exact prompt and per-call usage. Exercise
  Play scene notes and supplemental session reflections separately. Measure real
  repeated timings; a near-nine-second failed answer is not latency acceptance.
- Full two-adventure J1–J6 twice, image follow-through, original repeated~10s,
  older-laptop/8GB evidence and operator acceptance remain goal gates, not claims
  established by this contract or its isolated tests.


## Implementation activation — 2026-10-22

PRIME adopts Bugbot-approved design head `538c193f625184c5cee53d00aeb761ba4a581a57`,
merged #1616 at `df4cebf3cebae6e8cc94a5cb7b7dbc3703017e43`. ACTIVE serial dependent
implementation branch `codex/agent-authored-excerpt-blocks` starts at that exact
remote main. Same checkout/runtime lease; open-PR census has no competing owner.
One implementation PR, exact-head Bugbot, PRIME merge and guarded delivery.

The exact source/UI/migration write set is the expected lease above, with these
explicit consumer paths added before editing:
`apps/live_control_server/services/native_play_graph_owner.py`,
`apps/live_control_server/models/agent_turn.py`,
`apps/live-control-ui/src/shared/surfaceEvidenceProtocol.ts` and its test,
`apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`.
UI paths above resolve under `apps/live-control-ui/`; server services resolve
under `apps/live_control_server/services/`; APP modules resolve under
`src/application_state/agent_conversation/`.

Exact test writes: new `tests/test_authored_excerpt_blocks.py`,
`tests/test_surface_evidence_answers.py`, `tests/test_surface_source_answers.py`,
`tests/test_surface_source_play_binding.py`, `tests/test_source_passage_reuse.py`,
`tests/test_plan_jev_writer.py`, `tests/test_plan_jev_driver.py`,
`tests/test_native_play_source_acquisition.py`,
`tests/application_state/test_plan_jev_writer_packet.py`,
`tests/application_state/test_native_play_input_postgres.py`,
`tests/application_state/test_agent_conversation_historical_trace_postgres.py`,
`tests/test_play_graph_context.py`, `tests/test_native_answer_output.py` and
existing named shared UI tests above. Amend before any additional file.
No old migration or retained state may be rewritten.

Lease amendment: `apps/live-control-ui/src/planSurface/components/BuildSourcePassageEvidence.tsx`
accepts the explicit new shared completion union; citation rendering remains unchanged.

Lease amendment: `src/application_state/agent_conversation/repository.py` selects
versioned Plan evidence history attribution from the actual completion type;
retained V1 attributions keep their exact schema and validators.

Lease amendment: `tests/test_agent_turn_route.py` updates only the native Play
HTTP no-Rules fixture to the current V2 answer contract; independent owner-pin,
retry and Rules admission assertions remain the boundary under test.
