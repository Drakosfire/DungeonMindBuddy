# HANDOFF — AGENT-INTERACTION: production World conversation runtime

- **Status:** HOLD — PR #865 is open at `5674cf6f792c3516c4b99fdd2a2a6ac3eeab6991`; the original runtime acceptance remains incomplete. No merge, live-provider, production-database, or consumer-cutover authority.
- **Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`.
- **Owner:** PRIME owns the bounded #865 runtime repair; ARCHITECTURE must resolve the mapping decisions below before the remaining five-path implementation proceeds.
- **Repository:** `Drakosfire/DungeonMindBuddy`.
- **Design origin:** Buddy `main@672d18b059eaeceff20555374170ec2679f79082`.
- **Re-anchored base:** Buddy `main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c` (2026-10-03).
- **Topology:** serial — APP-STATE storage/domain service (#822/#827 complete),
  AGENT-INTERACTION runtime adoption, DEMO Plan consumer cutover, then Play
  and remaining surface cutovers.
- **Design authority:** APP-STATE World conversation contract, ARCHITECTURE's
  2026-10-02 ruling, and PRIME's runtime-owner routing decision.

This handoff pins the original production runtime contract and the current
acceptance disposition for resumed #865. The five-path implementation lease
was authorized and used to publish a partial repair. That publication does not
close the original acceptance or authorize a sixth path, schema/API change,
provider/live-production witness, consumer cutover, or merge.

## Mission

Connect Buddy's production generic Agent turn path to the accepted APP-STATE
World conversation service. A verified World has one server-issued active
conversation that later surface consumers share. Every accepted turn is
durable, keeps the surface/work basis under which it was submitted, and
completes on that same historical turn even if the user changes selection
before the response returns.

The World conversation ID is visible conversation identity. Provider
continuation is a separate, narrower context segment keyed from the
server-resolved work revision. Browser thread IDs and Hermes/Pi session IDs are
not conversation authority.

## Re-anchored evidence

- APP-STATE storage and domain service merged in #822 at
  `0e49c4d708d3e16c8068384549adb50e863bf64a`; World-wide turn receipts merged
  in #827 at `c48abb9fa5857df90af0b086ab78294445fd252a`. Their assigned
  service/PostgreSQL tests passed. See
  [the APP-STATE contract](HANDOFF-APP-STATE-world-agent-conversation-v1.md).
- Play's cross-surface contract merged in #842 at `672d18b059eaeceff20555374170ec2679f79082`.
  It requires exact per-turn Run/Runbook provenance and revision-scoped
  provider continuation. Its consumer handoff remains BLOCKED pending this
  runtime gate: [Play adoption](HANDOFF-DEMO-play-agent-adoption.md).
- RAKE's read-only audit of the exact pinned tree found that the production
  `agent_turn_service.py` path does not call `AgentConversationService`.
  Plan Ask still stores history in browser `localStorage`, namespaced by World
  and Plan document, and passes `client_thread_id` without a canonical server
  conversation ID. `startNewConversation` is local-only.
- The same audit found that a valid deferred Plan Ask is discarded when its
  document or revision changes before completion. The result is not persisted
  on its originating turn. Existing tests encode both per-document history
  separation and the dropped late response.
- At this pinned base, no implementation PR or assigned task owns production
  runtime adoption. The suspended
  `codex/agent-world-conversation-backend` checkout is dirty at `0e49c4d7`.
  Preserve it until PRIME explicitly reconciles its diff and grants a new
  lease. Do not edit, transplant, or infer authority from that checkout.

## Required runtime contract

1. Resolve and verify the managed World and current surface/work on every
   request. Use the APP-STATE server `conversation_id` and ordered visible
   history. A client thread ID may remain correlation metadata; it must not
   select World ownership, canonical history, or provider authority. Resolve
   an unset active pointer only through APP-STATE lifecycle rules; an
   ambiguous legacy import requires an explicit selection, never a local
   thread or route-based guess.
2. Persist the accepted user submission and stable idempotency binding before
   provider dispatch. Persist the completed visible answer/refusal or a
   truthful pending/failed/interrupted state on that same turn. A retry with
   the same key and request must reconcile the existing receipt; reusing the
   key with a different request/basis must conflict.
3. Record server-resolved per-turn provenance: verified World, exact surface
   and instance, primary work, supporting references, and selection where
   present. For Plan, bind the saved document ID, object revision,
   Content/WorkRevision ID and number, and full committed-content SHA-256. For
   a later Play consumer, preserve the selected Run/revision or snapshot and
   pinned Runbook identity/revision/hash that its server resolver supplies.
   This handoff does not implement that Run resolver. Never treat a client
   locator as resolved authority.
4. Keep provider continuation separate from the World conversation ID. A Plan
   document or committed revision change starts a fresh provider segment even
   when the bytes happen to match. When a later Play resolver supplies its
   Run/Runbook basis, either revision change also starts a fresh segment. Do not
   replay hidden provider history from an earlier segment as if it were formed
   under the current work basis. Recompute current context and tools on every
   turn. Do not add resumable provider sessions if the selected adapter has
   none.
5. Correlate completion to the persisted originating turn and frozen work
   basis. A late Plan A result remains Plan A history; it is not dropped or
   attached to Plan B. Apply the same invariant when the later Play consumer
   adopts this runtime; this slice does not implement Play selection behavior.
6. Preserve provider-neutral transcript boundaries: store visible user and
   assistant text plus typed provenance and lifecycle only. Do not store
   hidden prompts, model reasoning, compiled Plan content, graph/tool packets,
   tool results, credentials, or provider session IDs as conversation authority.

## Ownership and exclusions

- **APP-STATE** owns canonical World conversation identity/lifecycle, durable
  turn receipts, typed provenance, and the idempotent legacy-import service.
- **AGENT-INTERACTION** owns production turn orchestration, fresh context and
  tool resolution, bounded history replay, provider-segment selection, and
  completion/retry correlation.
- **DEMO** owns Plan/Play consumer cutover, presentation of historical results,
  and its configured-provider acceptance witness.
- **Plan/Content** retains Compose/Revise proposal bytes, review state, Apply
  receipts, and ordinary Save results as Plan-owned actions. They are not
  generic conversation turns; a non-authoritative link/summary is optional.
- The later DEMO Plan consumer cutover owns invoking the legacy importer. It
  may import only allowlisted visible Ask turns whose
  stored `ownerId` exactly matches the independently verified World and whose
  `contentBasis` is preserved. Import must be idempotent by stable source-turn
  identity. Missing/mismatched turns are skipped or quarantined; do not infer
  ownership from a local namespace. Do not import proposal/action rows or
  Hermes handles. Keep local bytes until the owning service confirms import.

This runtime slice does not change Plan or Play UI, legacy browser-history
import, Graph retrieval, citations, tool policy, Run/Runbook persistence,
provider/model policy, deployment/auth, APP-STATE schema, or proposal/Save
behavior. The Plan consumer is the first DEMO surface successor after runtime
acceptance; Play follows under its pinned handoff. Other surfaces remain
separately bounded.

## Required owning-boundary evidence

The assigned implementation handoff must name the exact files, database,
provider fixtures, isolated runtime state, and PR topology after re-anchoring.
At minimum, its tests must prove:

- Production route/service calls use the APP-STATE conversation service and
  stable turn receipts, not browser history as authority.
- Two currently supported, server-resolved Agent contexts for the same World
  (for example Index and saved Plan) use the same active server conversation
  and ordered history, but distinct provider segments; each turn keeps its own
  exact surface/work basis. A changed Plan document/revision also selects a
  fresh segment. `New conversation` uses the durable command/CAS contract. Do
  not require a real Play route or Run resolver in this runtime PR.
- User input is persisted before dispatch; retries, concurrent turns,
  interrupted calls, and late Plan completion preserve sequence and originating
  provenance without fabricating an answer.
- Provider pointer/segment selection changes with the exact Plan document and
  committed revision/digest and never leaks hidden history across those
  boundaries. Preserve the typed contract for future Play Run/Runbook bases;
  test their resolver and UI in the later Play consumer slice.
- Invalid World/work/revision or malformed provenance fails closed before
  provider work. A database or receipt failure cannot silently fall back to
  localStorage.
- Plan proposal/action bytes stay with their owning Plan path; legacy history
  import is not part of this runtime slice.

The later DEMO consumer witness must run a configured-provider Plan multi-turn
conversation, reload it, and switch to another Plan in the same World. Prove
shared visible history, exact provenance, segment isolation, and late-result
placement. A separate later Play consumer witness will prove Run/Runbook
selection, cross-surface history, and late-result placement. Neither is
operator acceptance of J1–J6.

## Resumed #865 implementation and current disposition

PR #865 remains open and is **HOLD / not merge-ready** against this handoff.
PRIME authorized a bounded repair on the existing five implementation/test
paths. The repair was published on `codex/agent-interaction-world-runtime-v2`
at `5674cf6f792c3516c4b99fdd2a2a6ac3eeab6991`, based on the re-anchored main
above. The frozen pre-repair source head was
`b8aa42c3b4b6b5201d39b19aa62c2bef364cc94c`.

- **Implemented subset:** route authorization for every turn, normalized World
  receipt reconciliation before mutable work/runtime resolution, completed
  answer replay, and concurrent acceptance fencing.
- **Observed verification:** the implementation checkout passed 25 Agent
  route/PostgreSQL tests, Ruff, and `git diff --check`. DEMO independently
  reports 19 `tests/test_agent_turn_service.py` tests passed at the same head.
  Its expired cases exercise Hermes pointer TTL, not APP claim expiry/reclaim.
  These results do not prove the outstanding historical-pin, APP lease, or
  retained-output gates below.
- **Remaining acceptance:** Graph typed-provenance mapping, exact historical
  replay basis, archived-history consumer contract, APP claim renewal/reclaim,
  and bounded same-output persistence retry remain open. Do not call the 44
  reported passing tests full runtime acceptance.
- **No merge or live witness:** PRIME review, the DEMO consumer witness, human
  operator acceptance, and later cutover gates remain separate. No configured
  provider, production database, or product state was used by this repair.

## Five-path repair lease and owning APIs

The current implementation lease is exactly these five paths; tests for the
remaining boundary behavior must stay in the two leased test files:

APP-STATE #867 remains the recovery predecessor. Its storage-boundary evidence
does not substitute for the HTTP ordering, historical-pin, claim, or provider
retry witnesses listed here. #869 remains open and separate; preserve its
evidence and branch. PRIME owns the serial #865 repair. The turn route now
applies the existing authorization before resolution, including Graph mode
`none`; the remaining authorization-order tests must prove this on all route
shapes within the two leased test files.

~~~text
apps/live_control_server/models/agent_turn.py
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_turn_service.py
tests/application_state/test_agent_conversation_postgres.py
tests/test_agent_turn_route.py
~~~

`tests/test_agent_turn_service.py` is not part of this five-path lease; the
specified service/claim evidence must be exercised through the two leased
route and PostgreSQL test files. The implementation may call existing owning
APIs but must not edit `src/application_state/agent_conversation/service.py`,
the database schema/migrations, or current public API models/routes beyond the
existing five-path boundary.

Existing primitives available to that lease:

- Exact Plan recovery: `workspace_document_registry.get_committed_playable_revision`
  accepts `revision_n`, `expected_sha256`, `kind="plan"`, and
  `expected_world_id`; it delegates to
  `application_state.content.service.exact_committed_revision` and returns the
  retained Markdown, WorkRevision UUID, revision number, digest, and object
  revision. Retry must compare the stored WorkRevision UUID/number/SHA and must
  not require the old object revision to still be today's pointer.
- Exact Graph recovery: `WorldGraphAuthority.read_revision(world_id,
  revision_id)` loads an immutable World Graph revision. The existing Agent
  Graph query/projection path accepts `revision_pin`; selected-object projection
  also carries that pin. Resolve the actual envelope/identity/selection before
  first acceptance, persist its resolved revision, and restore that pin on a
  retry rather than substituting the current head.
- Claim and fence: `AgentConversationService.claim_turn` distinguishes
  `claimed`, `pending`, and `completed`; it can reclaim expired `running`
  claims and advances revision/attempt. `renew_turn_claim` is bounded to a
  1–300 second lease and advances revision; `complete_turn` and `fail_turn`
  require the current revision fence and unexpired claim. `begin_turn` is a
  convenience wrapper that throws for pending/completed and therefore cannot
  be the route's only running-receipt decision.
- Runtime bound: the APP default lease is 60 seconds and maximum is 300
  seconds. The current Hermes host default turn wait is 120 seconds, with
  readiness and accept waits in addition. The route must renew and carry the
  latest fence through completion/failure, or prove the full selected runtime
  bound is below the chosen lease. No such proof or renewal currently exists.
- Same-output completion retry: `complete_turn` is idempotent when the same
  assistant text has already committed at the same fence. The runtime can
  retry a bounded transient completion write using the retained in-process
  `final_text` without provider redispatch while the fence remains valid; a
  stale/nontransient failure must return a truthful indeterminate/pending
  result and must not be rewritten as a second provider attempt.
- Archived transcript read: APP-STATE `list_turns(world_id,
  conversation_id)` supports an explicit conversation ID, while the existing
  public history route only resolves the active conversation. Do not add a
  public archived-history query/route without an explicit contract transfer.

The final four paths below are restricted to backward-looking status/evidence
settlement and remain outside the five implementation paths:

~~~text
Docs/Plans/HANDOFF-AGENT-INTERACTION-world-conversation-runtime.md
Docs/Plans/HANDOFF-APP-STATE-agent-turn-claim-recovery-v1.md
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Roadmaps/ROADMAP-demo.md
~~~

The #869-to-#865 roadmap transfer remains status-only. Preserve #869's current
evidence and open status; do not claim #869 merged or full J4 acceptance. Do
not pre-mark this runtime slice complete or invent a merge SHA, review count,
consumer witness, or operator acceptance.

No other source, schema, migration, MIND/Graph adapter, UI/Plan consumer,
provider deployment/configuration, lockfile, root configuration, or frozen
dirty checkout path is in this lease. In particular, preserve the suspended
`codex/agent-world-conversation-backend` checkout; do not edit or transplant
it.

### Open mapping and response-contract decisions

The following decisions block completion and must be resolved before more
behavioral edits:

1. **Graph provenance mapping:** `HistoricalReference` is generic enough to
   name a real immutable Graph revision and a real selected Graph object, but
   there is no accepted mapping for Graph mode, campaign/world scope, focus,
   and optional head/freshness identity across `supporting_work` and
   `selected_object`. The submitted-intent fingerprint is one-way and cannot
   substitute for stored provenance. ARCHITECTURE must ratify the exact
   `kind`/`object_id`/`revision` meaning and which absence/presence denotes
   mode, scope, focus, selection, and head. Do not invent pseudo-work refs or
   serialize context options into identity fields. If the existing typed
   references cannot express the truthful mapping, return that concrete
   insufficiency for owner/contract transfer; do not add a schema field here.

   **Candidate mapping for ARCHITECTURE review, not yet accepted:** Graph
   mode `none` stores no Graph reference and an absent selection. A Graph
   request stores one `supporting_work` reference to the real World Graph
   snapshot (`kind="world_graph_snapshot_world"` or
   `kind="world_graph_snapshot_campaign"` to identify the query lens,
   `object_id=world_id`, `revision=resolved_snapshot_revision_id`). If a
   campaign lens/focus is present, store references to the actual campaign and
   session objects at that same snapshot revision; if a head/freshness pin is
   needed, store the actual World Graph head revision separately. Set
   `selected_object` to the actual selected Graph node's kind and ID at the
   resolved snapshot revision, or absent when no node was selected. The
   original caller mode/scope/revision-pin/focus/selected-node remain in the
   submitted-intent fingerprint for retry equality. ARCHITECTURE must confirm
   that these kind values and snapshot-scoped campaign/session references are
   truthful `HistoricalReference` semantics; do not implement this candidate
   until ratified.
2. **Replay divergence:** the existing response's
   `AgentTurnContentBasis.has_divergent_working_copy` is not present in the
   durable `HistoricalReference`; it is not equivalent to the client's
   `client_work_state`. A replay cannot fabricate it or consult today's
   working copy and still claim to return the original exact basis. ARCH and
   DEMO must decide whether exact-basis successor compatibility requires this
   original boolean. If yes, the current durable type/lease is insufficient
   without an explicitly authorized persistence contract change. Do not
   silently return a current value or map client state into it. The existing
   `object_revision`, WorkRevision UUID/number, and content SHA can reconstruct
   the immutable content identity, but not this original divergence value.
3. **Archived history:** `AgentConversationService.list_turns` can read a
   specified conversation, but the existing public history route only reads
   the active pointer. After New Conversation, the old transcript is not
   accessible through that route. Decide whether the existing POST replay's
   response fields suffice for the successor or whether an authenticated
   archived-conversation history contract is required. Any new query parameter,
   route, or response field needs explicit public API authority and a named
   owner; it is not part of the five-path lease.
4. **Claim/runtime bound:** use `claim_turn` directly so a live claim is
   pending and an expired claim can be reclaimed. Renew under the existing
   bounded lease, tracking each renewed revision as the only valid fence for
   completion/failure, or provide an owning-boundary proof that the full
   configured runtime is shorter than the chosen lease. The default Hermes
   turn wait (120s) already exceeds the 60s default lease; readiness and accept
   waits also count. Test both renew and stale-fence outcomes.
5. **Completion persistence:** retry transient `complete_turn` writes with
   the same in-memory provider output and same live fence for a bounded number
   of attempts. The existing completion method recognizes the same result if
   a prior commit succeeded but its acknowledgment was lost. If retries exhaust
   or the fence is lost, return a truthful indeterminate/pending outcome; do
   not redispatch, fabricate success, or mark a stale fence completed.

These are exact acceptance gates, not a request to narrow the original runtime
mission. Keep the five implementation paths, current schema, and current
public API unchanged unless PRIME explicitly transfers the missing contract.

### Runtime ordering and receipt contract

First apply the existing local operator/GM authorization to conversation and
turn routes, including Graph mode `none`, before any World lookup, receipt or
database access, or provider work. Graph mode `none` skips Graph resolution;
it does not skip authorization. Then independently verify World authority and
validate the normalized request's syntactic scope without resolving today's
Plan, Graph, selected-work authority, or conversation pointer. Construct the
canonical submitted intent from that original normalized request envelope and
reconcile the World/key receipt before any current-work resolution. An exact
receipt returns the original conversation, turn status/result, and frozen
typed provenance without depending on today's Plan, Graph, or active pointer.
A changed semantic intent
conflicts; a different `client_thread_id` alone does not. Only the no-receipt
path resolves today's work basis and selected-work authority, then calls
APP-STATE acceptance with the required v1 submitted-intent fingerprint. A
legacy receipt without that fingerprint fails closed as
`legacy-receipt-unverifiable`, including for callers that do not supply v1.
Draft/import contracts remain separate.

The semantic fingerprint includes visible message, surface/instance, client
work state, original primary Plan revision/number/content SHA, and Graph
mode/scope/revision pin/focus/selected-node intent. Routing-only
`client_thread_id` is excluded. These are request-intent inputs; resolved
historical references remain typed provenance stored separately.

Store typed provenance references separately from the submitted-intent
fingerprint. Do not duplicate context bodies or add context IDs, context
digests, or schema fields. Preserve the exact immutable Plan revision and
Markdown used for the turn. For Graph, preserve graph identity and the resolved
immutable snapshot revision even when no node is selected; validate any
selected node against that snapshot and retain a separate head/freshness
reference when needed. Preserve the original Plan WorkRevision UUID and
content hash, plus Graph mode/scope and resolved snapshot identity. A valid
historical pin remains usable after the current Plan or Graph head advances.
Fail closed before provider dispatch only when the original pin is missing,
its identity/digest cannot be verified, or it is inadmissible in its own
resolved snapshot; a difference from today's head alone does not invalidate
it. Candidate binding is needed only for an actual selected-candidate
capability; ordinary Plan Ask does not require it.

For a new turn, use the bounded APP-STATE claim and revision fence. A live
claim is pending and cannot dispatch twice. Expiry blocks the old fence; a
successful reclaim advances the fence and attempt. Renew, complete, and fail
with the current fence. Retry a transient persistence write using the retained
provider output, without another dispatch while that fence is valid. Provider
execution and PostgreSQL commit are not atomic: preserve at-least-once
semantics and truthful pending/indeterminate outcomes; never fabricate an
answer or claim exactly-once provider calls.

### Required owning-boundary evidence

- **Service/claim behavior, within this five-path lease:** exercise these
  owning-boundary cases in `tests/test_agent_turn_route.py` and
  `tests/application_state/test_agent_conversation_postgres.py`: exact completed
  receipt after Plan/head and active-pointer rotation; semantic conflict versus
  routing-only `client_thread_id`; live claim pending without a second dispatch;
  expiry/reclaim advancing revision and attempt; renew returning the current
  fence; stale completion/failure before and after reclaim; and bounded
  same-output persistence retry with no provider redispatch. Do not add the
  unleased `tests/test_agent_turn_service.py` path.
- **Route tests** (`tests/test_agent_turn_route.py`): prove authorization,
  ordering, request normalization, response/status behavior, and zero provider
  work for invalid World/work scope or an unverifiable receipt. Prove existing
  local operator/GM authorization runs before World lookup/receipt/DB/provider
  access on each existing conversation-history, New Conversation, and turn
  route shape, including graph-backed, Graph mode `none`, and turn-only
  requests. Missing or invalid authorization returns without those accesses;
  Graph mode `none` skips Graph resolution only. Do not add an auth system or
  UI.
- **PostgreSQL tests**
  (`tests/application_state/test_agent_conversation_postgres.py`): exercise
  durable restart/recovery, transaction and lock boundaries, exact historical
  receipt resolution, claim expiry/reclaim/fencing, and only the authorized
  unique fixture databases.
- **Historical pins:** expired Plan recovery loads the original immutable
  revision bytes and verifies its WorkRevision ID. Expired Graph recovery
  loads the original immutable revision, including graph identity, without
  requiring a selection. Selected nodes are checked against that snapshot.
  Missing pins, unverifiable original identity/digests, or pins inadmissible in
  their own resolved snapshot cause zero provider calls. A changed current head
  alone does not invalidate a valid historical pin.
- **#833 semantic phase:** keep the saved-Plan fact plus dirty-draft decoy as a
  distinct phase inside this one canonical runtime acceptance. Include
  graph-mode-none/zero-Graph-resolution behavior and an exact-basis receipt
  after reload. Coordinate a real configured-provider runtime witness later;
  the existing #833 witness remains historically complete but is not full J4
  or J1–J6 acceptance.

### Exact-head evidence and known limits

At PR head `5674cf6f792c3516c4b99fdd2a2a6ac3eeab6991`:

- The implementation checkout ran the route and PostgreSQL suites with the
  provisioned disposable PostgreSQL 16 fixture using the mode-0600
  `/tmp/prime-app-state-pr865-20261003.dsn` file:
  `set -a; . /tmp/prime-app-state-pr865-20261003.dsn; set +a; timeout 240s /home/drakosfire/.codex/worktrees/agent-world-conversation-backend/DungeonMindBuddy/.venv/bin/pytest -p no:cacheprovider -q tests/test_agent_turn_route.py tests/application_state/test_agent_conversation_postgres.py`
  — **25 passed in 24.28s**. Ruff and `git diff --check` passed on the five
  changed paths. The run used uniquely named `dungeonbuddy_app_state_test_*`
  databases; it did not use a configured provider, production database, or
  live product state. Eleven existing Pydantic `schema`-shadow warnings were
  emitted.
- DEMO independently reports **19 passed** in
  `tests/test_agent_turn_service.py` at the same head. Its “expired” cases are
  Hermes pointer TTL cases, not APP claim expiry/reclaim evidence; this file is
  not part of the current five-path lease.
- These results verify the implemented subset only. Historical Graph/Plan
  recovery, claim expiry/reclaim/renewal/fencing, maximum-runtime versus lease,
  retained-output persistence retry, replay divergence semantics, and archived
  conversation consumer compatibility remain open. The PR description records
  HOLD; no merge, DEMO cutover, operator acceptance, or live-provider witness
  is claimed.

Do not treat the 44 reported test passes as full acceptance. Record new exact
commands, environment, failures, and owning-boundary evidence on this handoff
before requesting another review.

The bounded five-path repair lease does not grant live-provider, production
database, shared-runtime, or product-state authority. D0 appearance, the DEMO
consumer witness, operator acceptance, and J1–J6 acceptance remain independent
open gates. No merge is authorized.
