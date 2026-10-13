# Plan Graph traversal-discovered source admission

**Status:** PINNED / READY FOR PRIME ACTIVATION  
**Owner:** Buddy APP-STATE + SERVER, one jointly reviewed implementation PR  
**Topology:** serial  
**Authority base:** DungeonMindBuddy main `597c69b1ca5449947894311af83756812b2318fe`  
**Prior merge:** MIND #1129 at `597c69b1ca5449947894311af83756812b2318fe`  
**Buddy Core pin:** DungeonMind `d81ed4e126c55ef8df57804c9ab7128b7499c7a1`  
**Schema head:** `20261013_0022_turn_context_trace.py`; next migration follows 0022.  
**Design branch:** `codex/plan-graph-source-admission`

This handoff is pinned on a branch based on current main. PRIME activates the APP and SERVER write leases before implementation. It does not authorize a provider run, World publication, or Graph mutation.

## User outcome and invariant

A Plan Graph Agent can discover a readable source anchor during a parent-validated Graph traversal, open that passage within the same frozen World and revision, include the validated passage in a provider request, and produce an opened citation bound to that exact included read.

The original turn receipt, selected-index commitment, and initial source scope remain immutable. Newly discovered pins enter durable execution history only after the parent validates their exact returned pins against a prior validated Graph operation. No child-supplied scope, anchor, artifact, revision, path, or digest grants authority.

## Current seam

The accepted source read flow keeps an immutable set of initial pins in `GraphExecutionPolicyV2.source_read_scope`. The parent additionally checks that requested anchors exist and are readable in the exact `GraphRetrievalSession`, then validates World/revision and Core read receipts before persisting the read.

A successful Graph operation currently persists its result packet digest and evidence-ref IDs in `ValidatedGraphOperationEventV1`, but not the full source-anchor pin tuples. The current source scope therefore cannot durably prove that a traversal-discovered pin came from that accepted result. Separately, source-read policy caps total reads and anchors at 8, and trace capture has its own cumulative eight-passage cap. Removing only the read-scope membership check would not preserve the passage evidence.

## Durable contract

Add an execution-log V3 for new turns. Preserve V1 and V2 parsing, validation, replay, and saved history byte-for-byte.

A V3 validated Graph operation stores the exact sorted returned source pins: anchor ID, evidence-ref ID, source-artifact ID, and source-revision ID. The parent derives these from the same native response used to build the operation packet digest. The APP validator treats the server-created validated-operation event as the trusted origin record; it does not accept a later self-asserted digest as proof.

Add a V3 source-scope extension event containing its own event ID/sequence and the ID of one earlier validated Graph operation. Its pins must exactly match pins recorded on that operation, and each evidence ref must belong to that operation. Extensions bind to the original receipt's managed/native World, binding version, and Graph revision. An anchor ID cannot be rebound to different pins. Append through the active turn claim/revision fence before returning the operation result to the worker.

For reads, effective pins are the immutable initial pins plus pins from earlier valid extension events. The parent still requires each requested anchor to be present and readable in the exact retrieval session, and checks the complete pin plus frozen World/revision before any Core read. A request batch is all-or-nothing: one invalid, stale, unreadable, or foreign anchor denies the batch before source I/O. Validated read receipts and producing-provider inclusion continue to control whether a citation can say the source was opened.

Do not append a scope extension or perform a source read after an unknown provider outcome. Do not replay an uncertain Graph operation or source read.

## Bounds

Keep the per-request source batch at no more than 8 anchors and each passage at no more than 12,000 characters. Keep the 96,000-character total passage budget and the existing execution/trace JSON byte and event bounds. Remove cumulative per-turn source-read call and anchor-count limits; those counts currently stop authorized traversal despite available character and storage capacity.

Remove the trace store's cumulative eight-passage cap. Keep exact passage-to-read IDs/digests and same-transaction persistence. If actual character or serialized-byte capacity is exhausted, record capture as incomplete, withhold uncaptured passage bytes, and prevent an opened-citation claim for uncaptured content. Do not silently truncate event, pin, read, inclusion, or citation lists.

V3 provider inclusion must represent every source-read event actually present in that provider envelope within the execution record's storage bound. Preserve per-batch lists capped at 8. Preserve the event-array ceiling of 2,048 and 1 MiB JSON execution bound; a bounded-storage failure must settle honestly without fabricated completion. Trace material/source-reference list changes are limited to fields that currently impose a cumulative or per-envelope ceiling on this exact path.

## Core compatibility

Buddy's pinned Core is `d81ed4e126c55ef8df57804c9ab7128b7499c7a1`. Its selected-source index is metadata-only and remains bounded (up to 512 entries); its selected-target request is specifically 1–8 explicit targets and supplies the initial selection commitment. It is not the proof source for anchors returned by a later traversal.

The existing Buddy read request accepts 1–8 anchor IDs and one per-read character limit, then converts them to individual Core reads using the retrieval session's frozen projection. Core verifies exact World/campaign/revision and exact source artifact/revision receipts. Repeating these per-call reads has no cumulative Core call-count gate. Keep that request-to-Core conversion unchanged; apply new admission only in the Buddy parent and durable APP execution history.

No DungeonMind/Core change or pin update is part of this slice.

## Exact write lease

One serial PR contains only these paths:

APP durable execution contract and migration:

- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/service.py`
- new migration after `20261013_0022_turn_context_trace.py`
- `tests/application_state/test_agent_conversation_service.py`
- focused new or existing PostgreSQL execution/trace tests under `tests/application_state/`

APP passage trace bounds:

- `src/application_state/agent_conversation/context_trace.py`
- `src/application_state/agent_conversation/context_trace_store.py`
- owning context-trace tests under `tests/application_state/`

SERVER consumer and parent admission:

- `apps/live_control_server/services/agent_turn_service.py`
- `apps/live_control_server/services/plan_action_consultation.py`
- `apps/live_control_server/services/hermes_graph_interaction_tools.py` only for the matching tool contract wording
- `apps/live_control_server/services/agent_context_trace_collector.py` only for the matching trace-capacity behavior
- `tests/test_agent_turn_service.py`
- `tests/test_plan_action_consultation.py`
- `tests/test_agent_context_trace_collector.py`

The repository adapter is excluded unless implementation proves its generic fenced execution update cannot append the new typed event. Any required path outside this lease returns to PRIME before editing. WorldKeeper, DungeonMind, provider integrations, UI, deployment files, and private ingestion artifacts are outside the lease.

## Commit and review order

1. PRIME re-fetches current main, confirms the SERVER delivery/rollout lease has settled, and activates this one serial lease.
2. Implementation lands the APP V3 event, validator, fenced append, migration, and APP tests first on the single branch.
3. On that same isolated branch, SERVER adds parent pin capture/extension, effective-pin source authorization, consultation projection, trace changes, and integrated tests. No second PR is opened.
4. Independent review covers the cumulative APP + SERVER diff and the final mounted flow before any paired rollout.
5. Only after the integrated review accepts the path may PRIME coordinate APP/SERVER rollout. Until then there is no complete source-admission claim.

## Merge-blocking witness

The integrated test begins with anchor X absent from the initial selected packet and source scope. A parent-validated neighborhood operation at the frozen revision returns X with its full pin tuple. The parent appends a fenced extension linked to that exact operation. The same turn reads X, persists the passage, includes its read event in the producing provider authorization, and accepts a final citation whose opened state maps to that exact included read.

The focused adversarial matrix also proves:

- foreign World/revision, stale session, unreadable or unreturned anchor, altered evidence/artifact/source-revision pin, forged extension, missing/late origin event, and anchor rebinding are denied before source I/O;
- mixed valid + invalid batches deny wholly before source I/O;
- more than 8 successful passages are retained and accurately included while within character/byte limits;
- genuine character/serialized-byte exhaustion records incomplete capture, withholds unavailable passage text, and cannot produce an opened citation for it;
- current V1/V2 durable history still decodes and validates unchanged;
- no extension/read follows outcome-unknown and no operation is automatically replayed.

Offline typed/service tests and a real PostgreSQL fenced-append test are required. No provider QA or World-knowledge publication is authorized by this handoff.
