# PLAY: retained source and passage references

Status: MERGED and DELIVERED; operator acceptance remains open. PR2153 merged
at `351ca4327d12b773d039ff7877a7440856ff7f42`; independently reviewed runtime
`051ac464e1cdc2c00177c05c8990be4f5dd43811` is live on5202. Exact source
filtering/selection and same-tab composer reload passed ordinary Play checks.
Live answer/citation dogfood awaits the pending C2 provider-transfer question.
The implementation write lease is released. Play objects and broader References
acceptance remain subsequent scope.

Base: `63587a57d2f949715ea8552e8041cc635931a9cd` (merged #2151).
Branch: `codex/play-retained-source-references` in the existing
`/home/drakosfire/.codex/worktrees/buddy-context-loop/DungeonMindBuddy` checkout.
Topology: serial. #2151 is merged and delivered before this lane. Retained-source
and passage context is one independently useful outcome; Play object context is
a subsequent serial slice if its acquisition differs. #2104 remains held. No
INGEST lane or provider-role change is authorized by this slice.

## Outcome and invariant

A GM in an exact saved Play Run can choose an admitted retained source or source
section through ordinary References, retain that selection across composer
reload, submit it with an ordinary question, and inspect the answer citation.
The same World/native binding, immutable source revision, content hash and extent
must survive selection, admission, actual source opening, provider input,
completion and inspection. Missing, foreign, changed or unadmitted selections
fail accurately and remain recoverable; they cannot silently select newer text.

The existing Run/edition/Beat/Scene/current-moment/scene-note join remains exact.
Corpus passages do not acquire Run ownership. A no-provider reclaim may reuse
its original human capture from an earlier claim of the same immutable turn and
intent after fresh Core access checks; it retains the original capture attempt
and appends no duplicate reads. It cannot borrow another turn or a future attempt. A reference is human input, not a
published fact, source-admission decision or model-issued read grant. Saved Plan,
Run progress, mechanics, notes, Graph and source rows must remain unchanged.

## Current evidence and chosen owners

Current Build and Plan selections use `AuthoredReferencesV2`,
`AuthoredSourceReferenceV1`, native discovery/inspection and Core's
`read_authored_source`. Plan ordinary passage selection, unsent reload, submit,
completed reload and native citation opening passed on runtime
`beb93d88d1c2412746de1ccb84d241b5ec675f8f`, turn
`0a2905df-3a0b-47a9-96e6-ff230dc2fc1f`; the disposable saved Plan and retained
Graph/Run/source state stayed unchanged. This does not prove Play support.

Play has no composer reference entrypoint. Its request rejects authored input;
`native_play_graph_owner`, `PlayGraphIntentV1`, `PlayWorldGraphContextReceiptV1`,
`PlayWorldGraphExecutionV1` and `NativePlayInputV6` own the actual Run-bound,
single-provider path. Build/Plan's Jev executor is not that path.

Adopt shared source identities, discovery, exact Core opening, native catalog /
excerpt validation and citation primitives. Integrate their author-selected
reads and actual producing-envelope proof at the existing Play owner. Factor
reusable pure validation from Build/Plan-specific execution assumptions when
needed. Do not call the controller/writer body-acquisition state machine with a
fabricated Play controller role, or mint a fake model response to admit a human
selection. Keep one retained execution ledger and one source-admission owner.
The existing Play moment/note frame remains distinct from corpus ownership.

Extend current contracts with explicit reference capability where sufficient;
keep absent optional fields absent from historical digests. A new discriminator
is justified only when the existing schema cannot express the invariant
unambiguously. Retain necessary readers for existing immutable history, without
a second fresh submission executor or a legacy fallback. Fence newly persisted reader semantics with a forward schema revision. Real APP
admission exposed a closed SQL Play policy/event constraint; extend its exact
storage shapes alongside receipt and completion shapes. Preserve historical
branches and rewrite no user documents, turns or source rows.

## Exclusive expected write set and review map

- This handoff; consuming predecessor settlement in
  `HANDOFF-BUILD-native-writer-token-accounting.md`.
- Request and history transport:
  `apps/live_control_server/models/agent_turn.py`,
  `apps/live_control_server/routes/agent.py`.
- Existing Play runtime and source ownership:
  `apps/live_control_server/services/native_play_graph_owner.py`,
  `apps/live_control_server/services/agent_turn_service.py`,
  `apps/live_control_server/services/agent_native_source_sections.py` (adopt the native citation reader).
- APP intent, frozen receipt, ledger, source/provider and citation joins:
  `src/application_state/agent_conversation/types.py`,
  `service.py`, `authored_graph_references.py`, `native_corpus.py`,
  `play_graph_authority.py`, `play_graph_context.py`, `play_graph_input.py`,
  `surface_evidence_answer.py`, `native_answer_output.py`,
  `native_source_answer.py` (validate autonomous section citations only when present),
  `play_authored_sources.py` (new focused owner if needed).
- Shared Core source adapter only if an exercised caller needs an owner-neutral
  extraction: `apps/live_control_server/integrations/dungeonmind/native_corpus_source.py`.
- UI selection, exact Run-scoped draft/request recovery and source inspection:
  `apps/live-control-ui/src/api/types.ts`,
  `apps/live-control-ui/src/agentInteraction/authoredGraphReferences.ts`,
  `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`,
  `apps/live-control-ui/src/surface/SurfaceGraphReferenceInput.tsx`,
  `apps/live-control-ui/src/graphLens/NativeSourceInspection.tsx`,
  `apps/live-control-ui/src/rulesLookup/playContextProtocol.ts`,
  `apps/live-control-ui/src/shared/surfaceEvidenceProtocol.ts` and their owning tests
  (adopt shared authority validation and exact Play body-citation transport).
- Necessary forward reader fence and exact Play storage constraint extension under
  `src/application_state/migrations/versions/`.
- Owning tests: `tests/test_play_authored_source_references.py` (new),
  `tests/test_play_graph_input.py`, `tests/test_native_authored_source_references.py`,
  `tests/application_state/test_native_play_input_postgres.py`,
  `apps/live-control-ui/src/agentInteraction/WorldAgentConversation.planPlay.integration.test.tsx`,
  `tests/test_surface_native_authored_references.py` (settle its main-inherited V2/V3 expectation),
  shared reference input/retention tests adjacent to their owners. Add only the
  owning selector in `.github/workflows/world-ownership-core.yml` if needed.

No runtime activation during implementation. Local 8000/5202 and APP/Core/Run
resources remain the delivered candidate; preserve its ingestion extras.
Existing dependencies are reused. No new environment, checkout, corpus ingest,
publication, manual Graph editing or independent provider experiment.

Backend admission, producing-input proof and UI submission belong together in
this capability: shipping an accepted but unproved reference or an attaching
picker before its executor would be misleading. Review in the map's order;
split adjacent object support and retrieval optimization rather than growing
this source slice. Reassess before any additional public capability or write
ownership is needed.

## Verification and delivery

1. Real request/intent/fingerprint/receipt/APP round-trip for the exact saved Run;
   authored-source read uses the existing native admission and exact selector.
2. Reject foreign World/binding/revision, changed extent/hash, absent admission,
   mismatched intent, substituted Run/edition/scene, missing actual input,
   altered producer, another attempt's source and unsupported object attachment.
3. Provider-free owning Play execution with original moment/note/session sources
   preserved; actual producing request contains the selected corpus bytes and
   citations resolve only to its included exact read. No invented model grant.
4. Existing no-reference Play, source-navigation, Rules, source/Graph mixed
   answers and retained history still validate; no alternate fresh executor.
5. UI discover/filter/inspect/select/remove, Run-scoped composer reload and
   pending-request retention; no nonfunctional object or only-selected option.
6. Cumulative diff inspection, independent Bugbot review and required CI before
   merge. Deliver under standing PRIME authority after fresh resource checks.
7. Ordinary source and passage questions on an existing Elderwyld rehearsal Run,
   reload and citation inspection. Retain latency/call/read measurements and
   unchanged saved Run/Plan/Graph/source/session proof. Operator acceptance is
   separate; tests and this handoff do not establish it.

## Adoption and demolition closure

Adopt the shared picker / source browser and reference identities; remove the
Play composer exclusion for this supported source capability. Replace any
Build/Plan-only source validator assumption with an exercised shared owner,
without copying its provenance decisions. Keep native autonomous Play source
navigation for its distinct model caller, not as a human-selection workaround.
Inventory any remaining caller before deleting shared code. No unexercised
compatibility branch, duplicate source registry, read ledger or search index.

The full goal remains open: other reference cases and operator acceptance,
original-request efficiency, repeat runs and independent contrast assessment.
