# HANDOFF — APP-STATE: Buddy selected-source bootstrap v1

**Status:** ACTIVE contract preparation — PRIME authorized this docs-only consumer contract; implementation requires its independent review/merge and explicit source lease activation. No code/dependency/runtime adoption occurs in this PR.
**Repository / base:** Drakosfire/DungeonMindBuddy, freshly fetched `99fe172e08194abb89fe9f5d3a65a4d506e78d7a`.
**Owners:** SERVER owns admitted bootstrap ordering, integration and source authorization; APP-STATE owns immutable typed scope/receipt validation; Core owns native selection, provenance and public-safe coverage. PRIME coordinates, ARCH reviews the contract.
**Topology:** serial: published Core #102 → this Buddy authority PR → one bounded Buddy implementation PR on refreshed main. No unmerged behavioral dependency.
**Docs lane:** `codex/selected-source-bootstrap-contract`, `/tmp/dmb-plan-ask-history`; writes only this handoff.
**One observable outcome:** a World with 513 unrelated eligible anchors does not block a conversation whose admitted selected targets have a bounded eligible index.

## Publication and evidence anchors

Core #102 is verified MERGED: reviewed head `9a33fcf316507777fedac0441e1a36ecdb468a78`, published merge `870e879ac8226ae34b064d6846dc018b39db06aa`. Its ratified predecessor is `Docs/Handoffs/HANDOFF-AHEAD-selected-source-anchor-index.md` in Drakosfire/DungeonMind. Use the exact published source, not an unpublished existence-rebind successor.

The approved application API is `SelectedSourceAnchorIndexRequest` / `SelectedSourceAnchorIndexResult` and `WorldGraphRetrievalService.list_selected_source_anchor_index`. One request has an immutable tuple of 1–8 distinct `EvidenceTarget` values, kind object/relationship/assertion, and cap 512. Selection is nontransitive own support only. Complete/overflow/unavailable describes eligible selected metadata, never complete World knowledge; hidden and absent share public-safe not_visible. No source body or raw locator is returned.

Source dependency adoption is exact and separate: after this authority lands, the implementation may pin only published Core `870e879ac8226ae34b064d6846dc018b39db06aa` in pyproject/uv.lock and qualify that owning consumer environment. A later existence-rebind publication requires its own accepted exact pin and compatibility evidence; do not follow Core main, an unpublished head or a live environment implicitly.

The retained recovery composition `d87e9745` is qualified against Core `5d4e98963991995bdc280e57df52b8d0fe8de79e` only. Durable Graph reconstruction uses Core schema 0014 / the separately pinned a501-based environment, while the preserved old runtime has Core schema 0013. Neither the old recovery packet nor availability of selected-index Core 870 authorizes an environment/schema switch or proves full-World compatibility. A later paired rollout must name exact Buddy source, installed Core consumer SHA, Buddy/Core schemas, World binding/revision and source proof. Before any full-World/operator QA it must qualify the **actual Buddy/Agent native Graph connection** on those paired pins, including native admitted reads, selected-index access, product source opening, and old global/no-index receipt byte/hash/replay compatibility. Standalone Core or one-target synthetic success does not substitute for that consumer-boundary proof.

Characterization authority: `/tmp/rake-retrieval-limit-qualification/proposed-lease.json` and the ratified Core handoff. The 513 global-index failure was reproduced synthetically. The retained 44 recap cohort alone is not proven to overflow; source/corpus/identity gaps remain separate. This capability does not recover a World or manufacture missing Session 28/statblock/combat data.

## Consumer ordering and immutable authority

For a brand-new eligible auto-Plan/World turn:

1. Authorize the managed/native World mapping, exact revision, scope/focus and admissibility using existing owner/Core primitives. Perform the existing bounded admitted initial search before provider dispatch.
2. Construct at most eight distinct native target kind/ID pairs from that actual admitted read. Use existing result rank/order with a deterministic documented tie-break; no new reranker, paging or provider-selected IDs. Never guess native kinds from Buddy claim-ID strings. Reuse the exact read context and revision for the selected index.
3. Validate selected result context against the search: native World, campaign, scope mode, full typed focus, admissibility/access and exact revision. Verify canonical requested/admitted/not_visible partitions, count/status consistency, selector digest and index digest against the published Core serializer. Reject malformed, duplicate, stale, foreign-scope or widened authority before provider work.
4. Commit the immutable selected selector/context/result and authoritative anchor/evidence/artifact/source-revision tuples, then freeze the parent request and execution scope before any provider attempt. No whole-World global-index preflight is performed for the new selected policy.

With no admitted native target, do not call Core's 1–8-target API with an invented or empty selector. Preserve the existing omitted/Plan-only no-index path, with no source-read authority or selected-completeness claim. Selected overflow is explicit and empty, refused before provider dispatch; never freeze a partial-complete authority. Selected unavailable/provenance gaps remain explicit. An unavailable index grants no anchors and no source calls; zero openable anchors alone does not strip independently valid admitted Graph claim/evidence membership, while unsupported facts or no admitted evidence retain the existing Plan-only omission path. Source-body readability is not a new Graph fact-admission predicate, and no policy loosening or invented source support is permitted.

A complete selected index can still have not_visible/provenance/unavailable-binding gaps. Preserve all coverage facts; selected completeness only means eligible metadata was enumerated. Product body availability is tested separately by the existing opener. Bounded search truncation remains explicit, not pagination or exhaustive-history coverage.

## Exact policy and receipt commitment

New selection policy: `parent_initial_retrieval_with_selected_source_index_v1`. New execution policy: `plan_world_graph_execution_selected_scope_v1`. New nested commitment: `dmb_selected_source_anchor_index_commitment_v1`. The existing context receipt v1 and execution-v2 envelopes remain; policy identities distinguish the new meaning.

The commitment records the exact public Core context (world_id, campaign_id, scope_mode, full typed focus, admissibility, revision_id), a canonical access-context hash, requested/admitted/not_visible native kind/ID arrays, counts, provenance_gap_count, unavailable_binding_count, eligible_count, status, max_entries 512, index_scope selected_targets, selector_sha256 and index_sha256. Recompute hashes using published Core canonical serialization; pin golden vectors rather than approximate or partial-ID hashing. No credentials, raw locator, source body or hidden identities are stored.

Persist source tuples once in existing scope.admitted_anchors. Reconstruct the Core index hash from these exact tuples and commitment metadata; do not duplicate a 512-pin body inside the commitment or provider request. Freeze the context receipt's retrieval_packet_sha256 from a distinct selected composite containing the admitted initial claim packet, selected commitment and source tuples. Execution-policy digest separately commits the full scope and commitment. Enforce cross-receipt World/revision/access/policy/selector/hash/pin equality, including same-pin/different-selector tampering.

Public-safe not_visible echoes only caller-provided target IDs/kinds or admitted identities. No hidden-versus-absent distinction or excluded source/locator leak. A selected index is authority to use its committed metadata under that exact context, not authority derived solely from selector membership.

## Concrete APP-STATE storage seam; no migration inferred

Inspected current surfaces: GraphSourceReadScopeV2 persists retrieval session, managed World/campaign, graph revision and at most 512 sorted unique pins. GraphExecutionPolicyV2 embeds that typed scope. Repository already serializes/reads the complete execution JSONB; no separate selected-index column is needed. The 0018 execution constraint requires the existing scope-v2 discriminator and required fields but permits additive scope fields, preserves 512 anchors, 8 calls/anchors and a 1 MiB record cap. Current source head is 0019; this contract activates no migration.

Candidate representation: strict `GraphSelectedSourceReadScopeV2` subtype retaining scope schema `dmb_graph_source_read_scope_v2`, with a **required** versioned selected_index_commitment. GraphExecutionPolicyV2 accepts an explicit selected/legacy typed union. Only the selected policy may use the selected subtype; it must carry a valid commitment even when unavailable/zero-source authority. The legacy subtype remains unchanged, without nullable new defaults, custom rewriting or newly serialized fields. Selected metadata is part of persisted policy/digest, not merely transient bootstrap state.

This design must prove exact JSON/hash compatibility and actual PostgreSQL round-trip under current constraints before implementation claims migration-free completion. If a different outer schema, repository mapping, new migration or UI projection is genuinely required, stop and return the concrete failing boundary to PRIME before editing an unleased path.

The history/API projection exposes claimability/authorization state, not full private execution scope. Packet selection_policy_version is already a nonblank string. Therefore no UI/model wire expansion is inferred. Do not silently strip selected commitment during policy.model_dump or fresh-service decode; typed union serialization needs owning evidence.

## Replay, source opens and budgets

Known legacy policies `parent_initial_retrieval_v1` and `parent_initial_retrieval_with_bounded_source_index_v1` retain their exact global/no-index canonical bytes, hashes, coverage and replay semantics. Default new policy is only for a genuinely new turn with admitted targets; existing unknown/unverifiable policy is a conflict, not permission to reinterpret it.

Completed replay returns its frozen receipt before current Plan/Graph/index/provider reads. Safe pending reclaim selects the **stored** policy/selector/commitment before reconstruction; do not rerank today's search or silently substitute the new default. Re-establish the exact authorized snapshot/context and compare complete commitment plus pins to the frozen execution. Existing sent/unknown outcomes remain nonredispatchable. Preserve revision/access/selector/index tamper rejection and immutable attribution after head advances.

Existing source broker authorizes only the frozen exact anchor/evidence/artifact/source-revision pool. Later graph expansions may find other targets but cannot append pins, rebuild the selection or silently grant source opens. Outside-pool opens are denied before product body resolution, even if a later lookup supplies a plausible ID or shared artifact. Exact shared pins already committed through selected own provenance remain that same permission; this is not paragraph redaction or transitive target authority. New separately authorized turn is required for a wider source selection.

Preserve the existing multi-hop Graph crawl under the same authorized World/revision/context and eight-operation budget. Do not restrict admitted Graph reads/results to the frozen target list merely because source permission is selected. Owning comparison fixture: initial search selects A; neighborhood discovers admitted B; a committed A anchor opens within budgets, while B's distinct outside-pool source anchor returns an explicit source-scope gap/deny before body resolution. The neighborhood itself remains available. Under the legacy global policy, the same B source remains openable when its pin was in the frozen global pool.

**Residual limitation:** the new selected turn cannot open an outside-pool source discovered during later multi-hop exploration. It must report that gap or use a separately authorized turn with a new frozen selection; no hidden widening occurs. A one-target bootstrap pass does not prove complete source-backed multi-hop exploration, full-World coverage or co-GM/operator readiness.

Retain all existing provider context/accounting limits and result caps: eight graph operations, eight source-read calls, eight anchors, 12,000 characters per anchor, 96,000 total, and 512 selected metadata entries. No source bodies open at bootstrap; no provider/policy budget increase, full-World metadata/body dump or new search pagination. The selected commitment never becomes a provider-wide evidence-context dump.

## Exclusive candidate implementation lease

After authority merge and PRIME activation, re-fetch main/open leases and start one isolated codex branch. Core dependency source adoption is limited to the published `870e879ac8226ae34b064d6846dc018b39db06aa`; publication gate is met, but this docs PR changes no pin or installed environment. Candidate closed write set:

- `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py`
- `apps/live_control_server/routes/agent.py`
- `apps/live_control_server/services/agent_turn_service.py`
- `src/application_state/agent_conversation/types.py` — required selected subtype/commitment, legacy-preserving union/digest/cross-receipt validation
- `tests/test_agent_turn_route.py`
- `tests/test_agent_turn_service.py`
- `tests/test_world_graph_retrieval_contract.py`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py` — actual JSONB/fresh-service/constraint compatibility
- `pyproject.toml` and `uv.lock` — exact accepted Core publication only, no unrelated dependency upgrade
- This handoff for truthful activation/predecessor settlement only

No APP-STATE repository/service/schema/migration, UI, new framework, broader config or live pin is leased. Source tests use synthetic/disposable fixtures only. Return to PRIME for an actual necessary path extension, not an assumed schema expansion.

Ownership checked: DEMO S28 uses extract_promote/recap correction/ingest-basis paths; RAKE owns Core existence rebind; MIND owns replay driver. None is absorbed into this slice. Keep the accepted recovery composition `d87e9745` and its executable rollout packet untouched. Current open Play #1030 and rollout #1014 are separate lanes; recheck any future shared pin/path lease before dispatch.

## Required owning evidence and completion gates

- Actual Buddy adapter/route bootstrap fixture over real synthetic Core reads: 513+ unrelated World anchors, admitted one-target search → selected complete index → frozen source authority before any provider callback. Global legacy index still overflows; selected own scope over 512 returns explicit empty overflow. No provider/DB/runtime call in this fixture.
- Selector creation only from admitted native kind/ID results; deterministic 1–8 bound, empty-search no invented selector, missing/hidden/unsupported provenance coverage public-safe and distinct from product body unavailability. Wrong World/revision/access/focus/kind never opens a body or leaks hidden metadata.
- Multi-hop owning fixture explicitly proves initial search → admitted neighbor/new target → within-pool source open succeeds and outside-pool open reports gap/deny, without disabling Graph crawl or claiming completeness; legacy global-source behavior remains unchanged.
- Selector/access/index/anchor/revision tampering rejected at adapter, freeze and safe reclaim; same pins under different selector cannot be substituted. Later outside-scope graph target source open denied before product resolver; eight-operation/eight-call/eight-anchor/character limits remain unchanged.
- Golden old no-index and global-index receipt/execution bytes, policy digests and replay paths remain exact. Completed replay invokes no current Plan/Graph/index/provider resolver. Unknown policy fails closed.
- Owning native-read/source-open consumer proof against the exact published Core pin, plus legacy receipt compatibility, is required before later paired runtime adoption; actual Buddy/Agent connection on the final paired pins is a distinct live-release gate, not performed in this source slice.
- Fresh APP-STATE service readback of selected subtype/commitment and exact full execution JSONB under existing SQL constraint; legacy rows decode/serialize identically. An owning zero-eligible/unavailable fixture retains independently valid typed Graph claims with admitted evidence membership, grants zero source-read permission and invokes no source resolver; a distinct unsupported/no-admitted-evidence fixture retains the existing Plan-only omission. Record/input byte budgets remain enforced without metadata duplication.

Run only owning checks/lint, inspect exact cumulative base→head and contract/serialization boundaries, commit/push/open one implementation PR after activation. Independent review and merge remain separate authority. No corpus repair/replay/admission, provider/model calls, operator DB reads/writes, source/body probes, runtime rollout, World rebind, cleanup or live dependency sync. Full-World operator readiness and migration/runtime/provider QA holds remain; synthetic index success is not evidence that a World is complete or user-ready.
