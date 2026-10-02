# HANDOFF — APP-STATE: Agent turn claim and receipt recovery v1

**Status:** PREPARED / BLOCKED — design authority only; no implementation lease.
**Repository:** Drakosfire/DungeonMindBuddy
**Steward:** DEMO
**Owning flow/domain:** APP-STATE
**Design base:** Buddy main at 0f9b79961ddef1f8cf52e0fcc89f2feca741f107, freshly fetched and verified by PRIME on 2026-10-02.
**Topology:** serial — APP-STATE claim/receipt recovery → AGENT-INTERACTION World runtime (#865) → DEMO Plan action-dialogue projection (#859) → DEMO Plan conversation cutover (#857).
**PRIME re-anchor:** #865 is frozen at head `b8aa42c3b4b6b5201d39b19aa62c2bef364cc94c` pending this prerequisite; it is a reference, not an accepted runtime revision. PRIME's 2026-10-02 census found no recovery/schema lane. Recheck refs, open PRs, and ownership before activation.

This handoff defines one bounded durable-turn recovery capability. It does not grant a code, database, provider, HTTP-route, or runtime lease. The current APP-STATE service stores durable turns and World-wide idempotency receipts, but a worker crash can leave a turn permanently running; the production runtime also needs receipt reconciliation before it resolves today's work or provider continuation.

## Mission and invariant

Make accepted World Agent turns recoverable without duplicating visible turns, losing a completed answer, attaching it to a newer conversation, or letting an obsolete worker overwrite a newer attempt.

For an independently verified World and a stable idempotency key:

1. An exact retry reconciles the existing durable receipt before current active-conversation, Plan/Graph, or provider-segment resolution. A completed result remains bound to its original conversation and immutable provenance after Plan v1 advances to v2 or the World active pointer changes.
2. Reusing the key with different submitted intent or basis conflicts. A new key with a stale Plan basis follows normal current-work validation and fails; it is never relabeled to the current revision.
3. A turn has a bounded worker claim. A live claim is not dispatched twice. An expired claim can be recovered with a newer fence; only the current fence may complete or fail the turn.
4. Provider execution and PostgreSQL commit are not one atomic transaction. The system makes no exactly-once provider-call promise. It records honest pending/indeterminate outcomes and never fabricates an assistant response.

## Re-anchored code facts

- APP-STATE conversation storage/service merged in Buddy #822 and World-wide turn receipts in #827. The current migration chain at this base is 20261001_0010 → 20261001_0011 → 20261002_0012; 0012 adds typed surface and Content revision provenance.
- Migration 20261001_0011 already installs the unique key index on agent.turn(world_id, idempotency_key), rejects pre-existing duplicate keys, and backfills idempotency_fingerprint from World, visible user text, and typed provenance. Do not request a second uniqueness migration unless re-anchoring proves that invariant changed.
- agent_conversation.repository.get_turn_by_world_key already reads a receipt by World and idempotency key, independent of active conversation. AgentConversationService.accept_turn already rechecks a key inside its transaction, but it locks the active pointer first and its stable fingerprint is computed from the provenance supplied to it. Runtime code currently resolves current context before reaching that service. The new public domain operation must make receipt-first retry possible before that resolution.
- The current turn model has accepted/running/completed/failed/interrupted status, a lifecycle revision, and an attempt counter. begin_turn increments attempt and revision for accepted/retryable turns; complete_turn and fail_turn compare the expected revision. There is no claim-expiry field or expired-running reclaim path. A running row can therefore remain stuck after worker/process loss.
- The generic request_fingerprint includes routing/CAS fields and is not the stable retry identity. Existing idempotency_fingerprint is World-wide and independent of conversation routing/CAS, but represents the server-resolved provenance. Preserve its historical meaning.
- Docs/Roadmaps/ROADMAP-application-state.md still reports the Agent Conversation storage/service slice as in progress although #822/#827 are complete. The eventual recovery implementation PR must include this roadmap for truthful state settlement. Do not edit it in this prepared-handoff change.

## Required service contract

### Receipt reconciliation before current-context resolution

APP-STATE exposes a narrowly scoped domain operation that reconciles a submitted turn by verified World, idempotency key, and a versioned submitted-intent fingerprint. It returns the matching durable receipt (including its original conversation ID, status, user-visible result if completed, and frozen provenance), reports a fingerprint conflict for a reused key with different intent, or reports no receipt so the caller can proceed as a new turn.

The runtime order is:

~~~text
independently verify World authority
→ reconcile World-wide receipt by idempotency key + submitted-intent fingerprint
→ if matched, return/present that historical receipt without current Plan/Graph/pointer/provider lookup
→ if absent, resolve current active conversation and current surface/work/selection
→ accept through APP-STATE and dispatch under a durable claim
~~~

Receipt lookup is not an authorization mechanism. The caller first resolves/validates the World using the owning World boundary. APP-STATE then scopes the read to that verified World. The existing unique (world_id, idempotency_key) index is the identity/race authority across active and archived conversations.

SubmittedTurnIntentV1 is canonical, versioned, and reproducible from the normalized original `AgentTurnRequest` envelope. Its fingerprint covers verified World scope, exact visible user text, surface/instance, `client_work_state`, and the original caller-supplied semantic fields. For Plan work these are the submitted `primary_work` document ID, expected object revision, expected committed revision number, and expected content SHA. For Graph they are the submitted graph mode/scope, caller-supplied revision pin, focus, and selected node IDs. Include any other original user options that change request meaning. Do not include resolver outputs absent from that original envelope, such as the server-resolved WorkRevision ID; store those in the accepted turn's separate typed provenance. The consumer must preserve and resend the original normalized envelope for an exact retry after reload. The fingerprint excludes the idempotency key, mutable active-conversation pointer, conversation CAS revision, provider segment/session IDs, and context discovered only by re-resolving current state. Never reconstruct a missing original basis from today's Plan or Graph head, and do not persist duplicate raw prompts merely to support the digest.

The submit/accept path repeats the idempotency check atomically before pointer/CAS mutation and insertion. The early receipt read is an optimization and retry behavior, not the uniqueness gate. If two first deliveries race, the database uniqueness constraint plus the in-transaction recheck must produce one accepted turn; an identical request receives that receipt and a different fingerprint conflicts.

### Existing receipt compatibility

Add a nullable submitted_intent_fingerprint_v1 for turns accepted after this contract is enabled. Do not backfill it by resolving current Plan/Graph state, and do not rewrite the existing idempotency_fingerprint.

For a pre-existing receipt with no v1 digest, default to fail-closed with an explicit `legacy-receipt-unverifiable` conflict. No lossless mapping from the current stored resolved provenance to the complete original submitted intent has been proven at this base. A future implementation may permit a specific legacy replay only if it proves that the caller's original intent exactly reconstructs the stored World, user text, and typed provenance, allowing comparison with the legacy idempotency fingerprint without current-context resolution. Do not guess, relabel, or dispatch a second turn under that key. Direct the consumer to the already stored historical transcript rather than claim a replay.

Do not compare a replay with current content or a new active conversation. Conversely, if no receipt exists, current-basis and active-pointer validation remain mandatory before accepting a new turn.

### Expiring claim and fencing contract

- Persist a bounded lease expiry when a worker claims an accepted/retryable turn. Return the claimed turn revision as the fencing token; the existing monotonic turn revision is the fence, and the existing attempt counter is the attempt number. Do not add a redundant generation field unless owning-boundary tests show these fields cannot fence stale workers.
- An unexpired running claim is returned as pending and is not dispatched again. A running claim whose lease has expired is recoverable on the same turn/key. Reclaim atomically advances attempt and turn revision and sets a new expiry. A history/read result must not present an expired running claim as healthy indefinitely; expose it truthfully as recovery-needed/indeterminate until reclaimed.
- Re-dispatch after reclaim must rebuild provider context from the turn's original immutable basis, never today's Plan, Graph head, or active pointer. For a Plan, call Content's existing `get_committed_playable_revision` with the pinned document ID, World ID, revision number, and content SHA to load the exact WorkRevision, then verify its WorkRevision ID matches the stored pin; do not use a current-revision lookup. For Graph, load the original immutable snapshot by its exact resolved `revision_id` and validate that each selected node is admissible there. If the pinned bytes/snapshot are unavailable or inadmissible, fail closed as indeterminate with zero provider dispatch. A new request on today's basis is a new key.
- Completion, failure, and lease renewal require both the current fencing revision and an unexpired lease, checked atomically against database time. Expiry itself revokes claim authority even if no replacement worker has reclaimed the turn; the old claim cannot complete, fail, or renew. Reclaim is allowed only after expiry and atomically advances attempt and turn revision. Renewal returns the resulting turn revision; if renewal advances the fence, the worker must use that returned revision for later completion/failure. A late stale result cannot replace the current result or append another visible turn.
- A live worker that has provider output but encounters a transient complete_turn persistence failure retries persisting that same output under its still-current, unexpired fence; it must not redispatch the provider. If the lease expires first, that fence cannot commit. A still-live worker may reclaim the turn only if its atomic reclaim wins, then persist the retained output under the new fence without another provider call.
- A same-result completion retry is idempotent only when it presents the fence that actually committed the terminal transition; matching answer text or failure code alone never authorizes a stale worker. The implementation may derive that winning fence from the terminal turn revision only if owning-boundary tests prove the invariant that completion/failure advances the revision exactly once and terminal rows receive no later revision change. Otherwise, stop and ask PRIME to amend the lease for the minimum persisted terminal-fence field before adding schema. A stale fence must conflict even when its result matches.
- If a process disappears after provider success but before the result is durable, the outcome is indeterminate. After lease expiry, the runtime may use provider idempotency/result lookup if the provider supports it; otherwise it may make another provider attempt (at-least-once), but only the newest fence can commit. Do not claim exactly-once provider calls, silently mark success, or fabricate an assistant answer. A provider attempt that cannot be recovered remains observable as uncertain through truthful lifecycle/error state and attempt telemetry where known.
- Lease duration/renewal must be bounded and compatible with the runtime's request deadline. The APP-STATE service validates lease values; AGENT-INTERACTION owns dispatch, renewal timing, provider retry policy, and provider-attempt observation.

The migration must preserve existing turn IDs, sequence, text, provenance, status, result, failure code, attempt, and World-wide idempotency uniqueness. Existing running rows receive no invented answer or failure; activation/recovery must treat their missing prior lease as expired/recovery-needed. Any migration backfill must be deterministic, reviewed, and safe for a stale worker: a newer claim revision fences its old completion.

## Ownership boundary

- APP-STATE owns the durable turn schema, submitted-intent fingerprint version/storage and comparison, World-wide receipt reconciliation, claim lease/reclaim CAS, and fenced completion/failure APIs.
- AGENT-INTERACTION owns constructing the submitted intent from the original request, calling receipt reconciliation before current-context/provider work, resolving current World/Plan/Graph context only for a new receipt, dispatching/renewing claims, and retrying a live completion write without a second provider call.
- The verified World owner remains the authorization source. Content remains the authority for current and historical Plan WorkRevision resolution. Graph/MIND remains the authority for immutable graph snapshots.
- DEMO owns UI recovery/presentation and configured-provider runtime proof in the later consumer/runtime slices. This handoff changes no route, UI, provider, retrieval, or Plan action behavior.

## Graph provenance fit — separate #865 runtime gate

The fresh MIND main review at `619329c2c8586572ffd04558a79b3555c2ca3764` confirms that a resolved revision ID loads an immutable World graph revision while the current head is reported separately. Existing APP-STATE HistoricalReference fields can represent a selected node as object ID + revision equal to the exact resolved graph revision, plus a supporting graph/head reference. No per-node revision, MIND API, or APP-STATE graph schema expansion is required on this evidence.

This is not work in the recovery PR. #865 must still prove that each selected node was resolved/admissible in the pinned immutable snapshot, store the selected node and resolved snapshot in turn provenance, keep a distinct head/freshness reference when it differs, and include graph identity + resolved revision + selected IDs in provider-segment identity. An unresolved selected graph reference fails closed before provider dispatch; an unresolved client locator must never be used to derive or reuse a segment.

## Candidate implementation write set

The following is a proposed closed write set, not an active lease. Re-anchor and confirm the Alembic head and all overlapping paths before activation.

~~~text
src/application_state/migrations/versions/20261002_0013_agent_turn_claim_recovery.py
src/application_state/agent_conversation/types.py
src/application_state/agent_conversation/repository.py
src/application_state/agent_conversation/service.py
tests/application_state/test_agent_conversation_service.py
tests/application_state/test_agent_conversation_postgres.py
Docs/Roadmaps/ROADMAP-application-state.md
~~~

The candidate migration follows 20261002_0012 (down-revision `20261002_0012`). It adds only the lease/recovery fields and a nullable versioned submitted-intent fingerprint needed for new turns; the existing World-wide key index is retained. If the migration head or required shared paths change, return to PRIME before editing. Do not modify apps/live_control_server runtime routes, #865 leased files, UI code, MIND, Graph adapters, provider code, Docker/runtime configuration, or production data.

The roadmap is included only so the implementation PR can correct its stale #822/#827 status and truthfully record this recovery capability as active. The subsequent #865 successor lease must include the DEMO roadmap and this handoff/runtime authority for backward-looking recovery merge/evidence sync. Do not create a separate routine state-sync PR.

## Owning-boundary verification

Use the existing isolated Application State PostgreSQL test fixtures and disposable test DSNs only. No production database, persistent demo data, live provider, MIND service, shared port, or output directory is part of this lane. Unit/service tests may inject a deterministic clock; PostgreSQL tests must exercise real row locks, unique constraints, transaction rollback, and process/service restart behavior.

Required evidence:

- Exact completed v1 receipt after Plan v2 is current and the World active conversation has rotated: same verified World/key/submitted-intent digest returns the original v1 turn and original conversation/provenance without current-pointer/Content/provider resolution.
- Exact retry after the current Graph head advances matches using the preserved original request envelope and returns the receipt's original resolved revision without a current Graph lookup; a changed submitted revision pin, focus, or selected node conflicts.
- Same key with changed text, submitted basis, surface, or user-selected semantic input conflicts. A new key cannot use stale v1 as a new current turn.
- Legacy rows without a v1 digest fail closed as unverifiable unless an exact, reviewed compatibility mapping is proven; all such handling avoids current-context resolution and provider work.
- Concurrent first delivery with same World/key/fingerprint yields one durable turn/sequence; one with different fingerprint conflicts. The early lookup and in-transaction acceptance race are both covered.
- An unexpired claim retry is pending with no second claim/dispatch. Expiry alone prevents the old fence from completing, failing, or renewing even before reclaim. After expiry, one worker claims with higher attempt/fence; the former worker cannot complete or fail the turn even when its result text matches. A successful renewal returns any advanced fence, which the worker must use next.
- A fresh service instance can recover an expired running row. Existing completed rows and transcript order survive migration unchanged.
- An exact completion retry returns the original receipt only when it presents the fence that committed the terminal transition and the result matches. For a running row, expired-fence completion, failure, and renewal fail before reclaim; stale completion/failure fails after reclaim even when result text or failure code matches. Owning-boundary tests prove the terminal-fence derivation invariant or stop for PRIME to amend the lease before adding a field. Live output-write retry reuses the same provider result while the fence remains valid; after expiry, a retained result can be committed only under a newly acquired fence. The APP-STATE suite makes no provider-dispatch claim.
- Migration upgrade/backfill preserves existing receipts and enforces its nullable digest/lease constraints without guessing historical intent or outcome.

AGENT-INTERACTION #865 must separately prove the HTTP/runtime ordering with a fake provider: exact completed receipt retry makes zero provider/current-basis calls; unexpired running retry makes zero additional provider calls; a live worker's transient completion-write retry reuses the already generated result; after current content advances, expired Plan recovery sends the provider the exact original v1 Markdown, and after the Graph head advances, expired Graph recovery sends the provider context resolved from the original pinned snapshot; expired recovery makes zero provider calls if its pin is unavailable or inadmissible; recovery may be at-least-once only where provider idempotency cannot reconcile the unknown result; stale worker result is rejected; and the route returns truthful pending/indeterminate state without duplicate visible turns.

Suggested APP-STATE verification commands after activation:

~~~bash
uv run pytest -q tests/application_state/test_agent_conversation_service.py tests/application_state/test_agent_conversation_postgres.py
git diff --check
~~~

Record exact Python/PostgreSQL environment and all failures; do not convert a pre-existing suite failure into a pass by narrowing the command.

## Serial topology and activation gates

~~~
APP-STATE turn claim/receipt recovery (this handoff)
        ↓ merge, then re-anchor and sync
AGENT-INTERACTION #865 production World runtime
        ↓ accept and sync
DEMO #859 Plan action-dialogue projection
        ↓ accept and sync
DEMO #857 Plan World-conversation cutover
~~~

PR #865 remains frozen at the cited head until the recovery prerequisite lands. It must then be rebased/reviewed on the recovered Buddy main; the cited #865 head is not accepted authority. No #859 or #857 implementation lane is active. There is one serial implementation PR per step and no parallel migration/runtime lease.

This handoff remains BLOCKED until PRIME:

1. Reviews and accepts this design and the exact receipt/legacy-compatibility and claim/fencing semantics.
2. Re-anchors to freshly fetched Buddy main, checks PRs and worktrees again, confirms the Alembic head/path lease, and assigns the APP-STATE implementation owner and isolated branch/worktree.
3. Confirms no overlapping APP-STATE schema or service lane and grants the exact candidate write set.
4. Preserves #865 as frozen until this prerequisite merges; after merge, re-anchors and activates/rebases #865 with its own exact route/provider/test lease.
5. Keeps the Graph snapshot requirement as a separate #865 runtime acceptance gate; no MIND or Graph schema change is authorized here.

The implementation return must provide exact base/head and cumulative diff, migration upgrade evidence, real-PostgreSQL results, receipt/fingerprint compatibility behavior, lease-expiry and fencing witnesses, preserved failures, and remaining runtime gates. A green unit-only test is not evidence for PostgreSQL recovery.

### State settlement

The recovery implementation PR owns `ROADMAP-application-state.md`: it records the already-true #822/#827 completion and accurately identifies recovery as in progress, without pre-marking recovery complete or inventing its merge SHA/review count. After recovery merges, PRIME's #865 reactivation gate explicitly transfers the APP-STATE roadmap's status-only settlement path to the resumed #865 implementation lease, alongside its existing DEMO roadmap ownership. This is a narrow documentation transfer, not APP-STATE schema or service ownership. The #865 successor records the actual recovery merge/head/review/test evidence in both roadmaps; no separate routine status-sync PR is created. No dependent dispatch occurs until the mutable authority claims agree with re-read repository state.
