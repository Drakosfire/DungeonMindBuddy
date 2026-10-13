# Plan Graph traversal-discovered source admission

**Status:** ACTIVE — APP + SERVER implemented and verified; independent review and paired rollout pending (2026-10-13)
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
- `src/application_state/plan_action_dialogue/types.py` (PRIME-approved consultation V3 follow-up)
- `src/application_state/plan_action_dialogue/service.py` (matching owning freeze/append contract)
- `tests/application_state/test_plan_action_consultation.py` (consultation version/persistence evidence)
- new migration after `20261013_0022_turn_context_trace.py`
- `tests/application_state/test_agent_conversation_service.py`
- focused new or existing PostgreSQL execution/trace tests under `tests/application_state/`

APP passage trace bounds:

- `src/application_state/agent_conversation/context_trace.py`
- `src/application_state/agent_conversation/context_trace_store.py`
- owning context-trace tests under `tests/application_state/`

SERVER consumer and parent admission:

- `apps/live_control_server/integrations/dungeonmind/world_graph_reads.py` (PRIME-approved internal same-native-result operation pin seam)

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

APP activation: PRIME dispatch authorizes the exact APP allowlist on this serial branch, pinned handoff `975a98ab09de2fb3ac0be16d4f127da2dfd97f30`, base `597c69b1ca5449947894311af83756812b2318fe`, isolated non-serving checkout `/tmp/app-state-conversation-owner`. SERVER rollout/recovery lease is settled. Integration acceptance and paired rollout remain pending.

## APP phase handback

APP activation commit: `2ed7b6e1`; pinned design remains `975a98ab09de2fb3ac0be16d4f127da2dfd97f30` on base `597c69b1ca5449947894311af83756812b2318fe`. Before PR finalization, fetched remote main `9d32bc3d99e1c39a34434b309ee80c8ee82ad5ac`; its MIND #1130 changes are disjoint. The single branch and non-serving checkout remain the serial integration lane. Relevant open MIND #1130 and older inactive #1014 do not overlap this APP lease. No repository-adapter amendment was necessary.

SERVER interface:

- New turns use `PlanWorldGraphExecutionV3`, `GraphExecutionPolicyV3`, and `graph_execution_policy_digest_v3`. The V3 policy retains immutable initial scope and character budgets, omits cumulative call/anchor counters, and permits initially empty scope with traversal admission. V1/V2 models and serialized fields remain available unchanged. State updates, completion binding, and expired-provider recovery preserve the execution subtype.
- Build `ValidatedGraphOperationEventV3(kind="validated_graph_operation_v3", returned_source_pins=[...])` from the exact validated native operation response. Returned pins are sorted by unique anchor ID and require their evidence refs in the operation's evidence list.
- After the origin append and before returning results to the worker, call `extend_source_scope(... expected_revision, expected_attempt, extension=SourceScopeExtensionEventV3(...))`. It references `origin_graph_event_id` and carries the exact entire origin pin list, receipt/policy SHA, managed/native World, binding version, campaign, Graph revision, and retrieval session. APP validates exact earlier membership, receipt authority, ordering and no rebinding; event ID duplicates are fenced/idempotent. Changed V3 origin content conflicts even when request arguments match.
- `execution.effective_source_pins()` returns immutable initial pins plus validated extensions. Keep session presence/readability checks before source I/O. `authorize_source_read` and `record_validated_source_read` retain their V2 per-batch event contracts (1–8 anchors/receipts); V3 validates against the effective pins. Authorized character reservations still count `max_chars * anchors` against 96,000; consumers must choose request sizes within remaining capacity.
- Use `ProviderAttemptAuthorizedEventV3(kind="provider_attempt_authorized_v3")` for every producing envelope, including all actually included source-read event IDs (up to the execution bound). On an active trace, APP rejects inclusion of any content-bearing receipt without its exact captured event/read/digest tuple. Capture overflow rolls back the read/passage transaction; consumer marks trace incomplete, retries the same receipt without passage, withholds uncaptured bytes, and omits those read events from inclusion. Existing receipt-only behavior when trace capture is disabled remains available.
- Unknown outcomes block operation, extension, and source-read continuation. Duplicate append returns `False`; it is never a fresh dispatch/read grant. Preserve the existing no-replay consumer contract.
- Trace no longer has a cumulative eight-passage limit; historical references may represent up to 2,048 items per material. Same-read references stay capped at the eight-item batch. The 12,000-character passage, 96,000-character turn, 2,048-event/observation and 1 MiB execution/trace bounds remain enforced. Graph trace validation/closure recognize V3 origin events.
- Migration `20261013_0023_graph_source_admission_v3.py` follows 0022, extends the existing JSONB check, preserves legacy checks, and refuses downgrade while V3 records exist. It was run only in disposable PostgreSQL.

APP proof: 62 focused cases passed (46 deselected) using `/tmp/app_source_admission_final_runner.py`, existing Python environment, owned PostgreSQL 16 with 512 MiB tmpfs/random loopback port/env-only password and unconditional teardown. This comprises 27 new typed/real-PG witnesses and 35 legacy V2/trace regressions. Evidence covers exact fresh-service readback, nine passages/inclusions/opened-citation read binding, forged/late origins and foreign/rebound/mixed pins, fresh/stale/attempt/expired fences, duplicate/changed-origin behavior, unknown no-follow/reclaim, character/batch/event/serialized capacity, capture rollback/incomplete recovery and uncaptured-inclusion denial, V1 migration byte preservation and V3 downgrade refusal. Ruff and cumulative whitespace checks pass. Initial proof harness errors (missing disposable DSN, fixture tokenizer, assertion wording and generated migration quoting) were corrected; final proof is green.

This is APP storage/authority proof. SERVER parent construction, mounted source I/O denial, final completion, consultation and trace collector adoption remain pending in this same draft integration PR. The independent cumulative review and paired migration/runtime release remain gates. PRIME coordinates the serial checkout transfer; APP stops writing after handback.

## APP consultation follow-up activation

PRIME temporarily returned the serial checkout lease to APP to admit V3 in `src/application_state/plan_action_dialogue/types.py` and owning `tests/application_state/test_plan_action_consultation.py`. SERVER is paused; its existing uncommitted `agent_turn_service.py` edit is preserved. This follows exact checkpoint `7c8016519dc2aff3a30d412b69edbe0a158163a6`. PRIME approved the concrete additional scope: `src/application_state/plan_action_dialogue/service.py` plus amendment of the already proposed 0023 migration for nested consultation V3. No new migration/table or V1 consultation acceptance is authorized.

Consultation follow-up VERIFIED: owning consultation union accepts V2/V3; freeze chooses matching execution type and digest; shared validators retain authority binding. Existing 0023 also extends the nested consultation SQL check and refuses downgrade if either Agent or Plan Action V3 exists. V1 consultation rejection is preserved. Ten focused consultation cases passed (31 deselected): V2/V3 JSON round-trip, existing V1 rejection/shared history, V3 owning freeze/append/fresh readback and completed source history, foreign native binding rejection, nested downgrade refusal, V2 completed consultation bytes across downgrade/upgrade, and reused V2 token-fenced/provider/source proofs. Three focused Agent migration/expired V3 recovery cases passed (11 deselected). Both runners used owned disposable 512 MiB tmpfs PostgreSQL and unconditional teardown. Ruff and owning diff checks pass. SERVER dirty `agent_turn_service.py` is excluded from this APP commit; its preserved working-tree blob is `d5dec612bc905e48f110cf2bfc7f2abf755b00ce`. APP releases temporary serial writing after this follow-up handback; consumer integration/final review remain pending.

## SERVER internal pin seam amendment

PRIME authorized this bounded amendment on 2026-10-13 after the mounted real-PG witness exposed that public `WorldGraphSourceAnchor.revision_id` is the Graph revision, not the source revision. Internal resolved wrappers for search/object/neighborhood/support must expose full source pins from the same native operation result. Preserve public result models and distinct frozen Graph/source revision identities. No extra retrieval, anchor resolution, source IO, Core change or public API is authorized. Tests remain in the existing SERVER allowlist; the mounted witness must use real `srcrev` pins and parameterize all four operations. Original redacted failed witness is retained privately at `/tmp/server_source_admission_joined_evidence.txt`.

## SERVER integration handback

Implementation head: `6e8015cbbc8cf3f219d8a567020cb1bfbc3072e6`; adapter amendment pinned first at `cc82293fd7927b97995d36aa506e66800f48f3c0`. Refreshed main is `2dcd5b40f28757f8b398ad0a3ffcaf248db51bf0`; intervening #1131 UI/history confirmation changes are disjoint. Cumulative comparison merge base is `9d32bc3d99e1c39a34434b309ee80c8ee82ad5ac`. The existing draft #1132 remains the single integration PR.

New ordinary turns and saved Plan consultations use V3; parent operation origins and fenced extensions use exact source pins from the same native result. All four internal resolved adapters preserve public results and distinct Graph/source revisions without extra authority/source reads. Source reads use effective pins, retain session/readability/World/revision and character/storage bounds, and omit only V3 cumulative call/anchor counters. Producing inclusion, final completion and saved Plan source projections recognize V3. Saved Plan adapters initialize shared denial tracking and receipt-only capture state. Capability preflight requires the V3/source persistence methods before dispatch. Safe parent failure diagnostics expose only an allowlisted stage/category.

Final focused evidence: **60 passed, 1 deselected** (the PostgreSQL collector case runs in the next gate), including nine source passages/inclusions, final opened citation and saved Plan projection, foreign/stale/unreadable/mixed batch denial before I/O in both consumers, five incompatible-producer preflight cases, provider lifecycle/no-replay, legacy source receipt and direct retrieval contract regressions. Final disposable PG16 gate: **7 passed**, comprising the mounted authenticated server route for search/object/neighborhood/support, real trace terminal-failure persistence and two saved Plan V3 owning persistence/history cases. The mounted cases use actual SERVER/APP/Core paths with an in-memory native World fixture and provider-free runtime stub. They prove absent initial pins → origin exact source pins → fenced extension → Core source IO → exact producing envelope inclusion → opened citation → fresh-service and fresh-process durable history readback. Support keeps its selected initial claim while its source pin is absent initially; other cases discover the cited claim in the operation. Ruff and cumulative whitespace checks pass.

Private proof: `/tmp/server_source_admission_joined_runner.py`, `/tmp/server_source_admission_joined_final_evidence.txt`, `/tmp/server_source_admission_focused_final.txt`; beginning regression retained at `/tmp/server_source_admission_joined_initial_failure.txt`. The approved 512 MiB tmpfs PG16 launcher used random loopback ports, environment-only disposable credentials and unconditional teardown; removal confirmed. Python/dependencies: `/tmp/buddy-c1s16-ge-deepseek-prep-20261012/.venv/bin/python`; APP imported from this checkout's `src/application_state`. That venv contains an older Core wheel (`aa344e...`), so final gates overlay exact locked Core `d81ed4e126c55ef8df57804c9ab7128b7499c7a1` source archived from the existing local Git object to `/tmp/server-source-admission-core-d81ed4e/src`. GE dependency is `38d77f33d0e45b3be02459f43add560c2ca2ff8a`; Hermes is 0.18.2. No network installation or lockfile change. The preliminary older-Core `GraphContributionAssertionV3` import failure clears with the exact pin. Default locked sync cannot run here because local `out/hermes-agent` is absent; this reuse is explicitly permitted by PRIME. No whole slow suite is represented as green.

Q04 original tool arguments are absent from retained artifacts; no retrospective cause, replay or model request is claimed. The joined proof exposed and fixed a source/Graph revision substitution defect but does not establish that it caused Q04. Integration acceptance remains for PRIME's independent exact-head review. Paired release requires APP migration 0023 plus compatible SERVER runtime together; DOGFOOD owns runtime adoption and any subsequent authorized benchmark. No merge, retained database mutation, provider call, deployment or World publication performed.
