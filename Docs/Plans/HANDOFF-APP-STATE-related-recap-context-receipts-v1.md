# HANDOFF — APP-STATE: related recap context execution receipts

**Status:** ACTIVE — PRIME approved this bounded slice on 2026-10-12.
**Base:** freshly fetched Buddy `origin/main@8fce46de7e33bc352300abdf3ece0369a3ac1e68` (SOURCE #1089 merged).
**Branch:** `codex/app-state-related-recap-context`.
**Owner/topology:** APP-STATE; one serial implementation PR. SERVER owns the parent tool broker and remains the only owner of `apps/live_control_server/services/agent_turn_service.py`; the broker successor follows the active source-open projector lease. This slice does not edit SERVER paths.

## Mission and invariant

Add a bounded, typed, durable APP-STATE execution receipt for Agent `read_related_recap_context`. The receipt records a parent-authorized, same-pin provenance-to-context join and the verified read/inclusion outcome. Recap text may inform prose; it is never evidence source text, `source_read_ids`, `source_opened`, graph-grounded claim support, or a citation substitute.

Preserve legacy Graph execution V1 and existing V2 payload serialization/replay. Add only discriminated additive events inside the existing V2 `graph_context_execution` JSONB value. Do not add a database column, migration, repository write path, provider configuration, runtime/corpus work, or source authority. Do not persist paths, continuation tokens, raw metadata catalogs, or passage text.

## Admission and authority boundary

SERVER is the trusted parent for Core and Buddy authority. Under the turn's exact frozen native GM `WORLD_CROSS_CAMPAIGN` graph projection, it:

1. Takes the exact assertion/relationship target and evidence references actually admitted to this turn. Admission must be from the initial dispatched Graph input, a prior validated Graph operation, or the explicitly committed selected-index admission. The target and each evidence reference must be present in the same admission source. Merely existing in Core or a broad catalog is insufficient.
2. Calls Core `WorldGraphRetrievalService.get_evidence()` for that exact target and evidence-ref set. It requires matching snapshot/World/scope/revision, complete evidence-ref coverage, nonblank source revisions, and zero provenance gaps. It retains exact `(evidence_ref_id, source_artifact_id, source_revision_id)` metadata even when Core marks the old source anchor unreadable.
3. Calls Core `list_source_context_index()` at the identical frozen projection, requires a complete, non-overflow index, and joins the exact artifact/revision pair to an authorized context descriptor. It never infers a source tuple from labels, slugs, model text, or a neighboring session. Zero match or unresolved ambiguity fails closed.
4. Re-runs the same-pin metadata/context join and resolves the opaque context ID again before each Buddy read. Buddy verifies the exact descriptor, source URI containment, full revision-byte digest, UTF-8, unique canonical Session heading, and bounded section/continuation.

The APP-STATE admission receipt contains only the exact turn-admitted target/ref set, Core metadata pairs and result commitment, selected descriptor and selector, and frozen authority pins. APP-STATE validates structural consistency and membership in the turn; it does not claim that it called or authenticated Core. The frozen readable `source_read_scope.admitted_anchors` is not an admission prerequisite for this context-only capability. This is required for opaque legacy S22/S23 evidence metadata that is provenance but not source-readable.

The durable receipt names exactly one admission origin and APP-STATE validates it against the stored turn: (a) `initial_graph_input`, where target ID and all exact evidence-ref IDs are in the same frozen `assembled_input` dispatched target/ref sets; (b) `validated_graph_operation`, where an earlier validated operation event contains that target and all exact refs; or (c) `selected_index_admission`, where the frozen selected-index commitment admits the target and its frozen admitted-anchor set includes the refs. The origin and event/commitment identity are persisted. A target or ref merely present in Core's wider snapshot, receipt candidate set, or unrelated prior event does not authorize this read. This membership gate precedes and is independent from the Core provenance-pair/context-descriptor join above.

## Typed execution contract

In `src/application_state/agent_conversation/types.py`, add strict discriminated V2 events and nested models for:

- Parent authorization, with frozen turn/policy digests; managed/native World, binding, exact graph revision, GM cross-campaign scope; admission origin and source event/commitment; exact target kind/ID and evidence-ref IDs; complete zero-gap Core provenance pairs and a canonical metadata-result digest; complete context-index digest; and the selected `dm-context-anchor:v1` ID, matching source tuple, selector schema/policy/session/heading, and source-content digest.
- Validated read result, referencing its prior authorization and exact descriptor commitment; outcome, full source-byte SHA-256, full section SHA-256, Buddy heading/line range, page character offset and returned length under an explicit range-semantics version, per-page UTF-8 content digest, truncation, and continuation input/output commitments. Do not store raw continuation or content.
- Provider-context inclusion, persisted immediately before the ordinary provider-attempt authorization. It binds the included validated context-result event IDs and digests plus total characters to the exact provider attempt ID and envelope SHA-256. Require the following provider authorization to match both before dispatch.

Set bounded limits in this new receipt family without adding fields/defaults to the existing frozen Graph policy: at most 8 context-read calls, 12,000 requested/returned characters per call, and 96,000 total authorized/returned characters per turn. Enforce same-descriptor/same-section continuation, prior cursor commitment, contiguous character offsets, and size limits. No opaque context ID or read-result ID may be inserted into evidence or source-read fields.

Implement a receipt-aware validator that checks admission target/ref membership against the frozen initial receipt, prior validated Graph event ordering, or committed selected-index target/anchor set, as appropriate. Invoke it on APP-STATE append and durable Turn readback boundaries so tampered JSONB fails closed. Keep `PlanWorldGraphExecutionV1`, current `ProviderAttemptAuthorizedEventV2`, and all old event/model dumps unchanged. The V2 state machine must allow the new authorization/read events only under V2; inclusion must be followed by the matching provider authorization, while a durable inclusion without that authorization remains undispatched and recoverable.

## Exclusive write set

```text
Docs/Plans/HANDOFF-APP-STATE-related-recap-context-receipts-v1.md
src/application_state/agent_conversation/types.py
src/application_state/agent_conversation/service.py
tests/application_state/test_agent_conversation_service.py
tests/application_state/test_agent_conversation_postgres.py
```

Change `service.py` only for narrow typed append wrappers and receipt-aware append validation needed by the typed contract. No repository, migration, SERVER, UI, provider, source, Graph, or runtime path is leased. Publish the exact DTO/event contract through this handoff/PR early; SERVER integration remains under its separate lease.

## Required focused evidence

- Service/model tests accept a synthetic complete parent scope including `can_open_source=false` provenance without a readable source anchor; reject target/ref absent from all three turn-admission paths, mismatched target/ref membership, incomplete/gapped provenance, pair/descriptor mismatch, stale or foreign World/scope/revision, overflowing context index, ambiguity, duplicate IDs, out-of-order events, and over-budget/oversized data.
- Read tests reject changed full-source/section/page digests, selector/range mismatch, invalid continuation, discontinuous offsets, and result lengths above the authorization. Provider-inclusion tests reject unknown/later result IDs, changed envelope/attempt, wrong ordering, and context IDs offered as source-read/claim-support IDs.
- PostgreSQL test proves auth → read → inclusion persistence and fresh-service/history reload of the exact typed receipt with no body/path/token; a dangling inclusion is recorded as not dispatched and cannot be mistaken for provider authorization.
- Round-trip representative pre-change V1 and current V2 payloads and assert byte-identical canonical serialized JSON and existing idempotent replay behavior.
- Use synthetic/public fixtures only. No private S23 provider export or live provider call. PostgreSQL owning-boundary tests must use the repository's unique disposable `dungeonbuddy_app_state_test_*` database fixture, never the operator/runtime database. No schema migration is expected or authorized.

Run only the focused APP-STATE service and PostgreSQL tests plus changed-path lint/diff checks. Preserve inherited failures and report exact base/head, checks, limitations, and the untouched SERVER/runtime boundaries in the implementation PR.
