# HANDOFF — AGENT-INTERACTION: production World conversation runtime

- **Status:** CODE INTEGRATION COMPLETE — PR #865 merged at `1c0320d18c53037308cd7412719fb3e2f0610d99` from reviewed head `097107324e0be5f5e7aa45e9633f70c09c4794e5`. Later consumer/provider and operator activation gates remain held; no live-provider, production-database, or consumer-cutover authority.
- **Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`.
- **Owner:** PRIME owns cross-slice sequencing; the merged #865 implementation lease is released. ARCHITECTURE's accepted mapping decisions below remain the response/provenance contract.
- **Repository:** `Drakosfire/DungeonMindBuddy`.
- **Design origin:** Buddy `main@672d18b059eaeceff20555374170ec2679f79082`.
- **Re-anchored base:** Buddy `main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c` (2026-10-03).
- **Topology:** serial — APP-STATE storage/domain service (#822/#827 complete),
  AGENT-INTERACTION runtime adoption, DEMO Plan consumer cutover, then Play
  and remaining surface cutovers.
- **Design authority:** APP-STATE World conversation contract, ARCHITECTURE's
  2026-10-02 ruling, and PRIME's runtime-owner routing decision.

This handoff preserves the production runtime contract and records the merged
#865 code disposition. The bounded code integration is complete; this does not
authorize a provider/live-production witness, consumer cutover, or operator
acceptance. Later activation work requires its own re-anchor and exact lease.

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

The findings in this section are the design-origin baseline before the #865
repair. The merge disposition and current held gates are recorded below.

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

## #865 code integration and merge settlement

Buddy PR #865 merged on 2026-10-03 at merge commit
`1c0320d18c53037308cd7412719fb3e2f0610d99`, from exact reviewed head
`097107324e0be5f5e7aa45e9633f70c09c4794e5`, based on
`main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`. PRIME reported 58 combined
route, PostgreSQL, Agent-service, and auth cases passing in 41.43 seconds,
plus the full HTTP cardinality case passing in 8.42 seconds (59 total). ARCH's
conditional code-acceptance holds were resolved at that head. No CI or branch
protection contexts were reported.

- **Implemented and merged:** authorization on Graphless and Graph turns;
  receipt-first same-intent reconciliation; bounded completed-answer replay;
  immutable Graph and Plan provenance recovery; accepted-basis fencing when
  concurrent acceptance returns another request's receipt; claim pending,
  expiry/reclaim, renewal and latest-fence completion/failure; and retained
  output retry/error mapping without provider redispatch.
- **Path lease released:** the original five implementation/test paths plus
  the explicitly authorized test-only `tests/test_agent_graph_auth.py` path
  are merged. No new migration or API/schema path was added.
- **Boundary:** the merged code closes the code-level #865 repair. It does not
  claim the later configured-provider consumer witness, human operator
  acceptance, or J1–J6 product acceptance. Those are activation/product gates,
  not prerequisites for merging this code-only PR. No such live witness or
  activation authority was exercised or granted.

The bounded replay mapping and response decision below are the accepted
consumer contract for the merged implementation. The original cross-surface
runtime/product mission remains a separate activation and consumer sequence;
do not reopen or broaden the released #865 code lease.

## Released #865 path lease and owning APIs

The original implementation lease covered five paths, with one explicitly
authorized test-only auth path added before merge. All six cumulative #865
paths are merged and the implementation lease is released:

APP-STATE #867 is the recovery predecessor. #869 remains open and separate;
preserve its evidence and branch. The merged turn route applies authorization
before resolution, including Graph mode `none`; the exact-head evidence below
records the authorization and persistence tests accepted for #865.

~~~text
apps/live_control_server/models/agent_turn.py
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_turn_service.py
tests/application_state/test_agent_conversation_postgres.py
tests/test_agent_turn_route.py
tests/test_agent_graph_auth.py
~~~

`tests/test_agent_turn_service.py` was outside the implementation write lease;
PRIME ran it read-only as part of independent regression verification. The
implementation did not edit `src/application_state/agent_conversation/service.py`,
the database schema/migrations, or introduce a new public API.

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
- Runtime lease: the merged route renews its 120-second claim every 30 seconds,
  carries the latest returned fence, and stops/joins renewal before terminal
  persistence. This does not claim a maximum provider-runtime duration; a
  process loss or renewal failure leaves lifecycle outcome truthful/uncertain.
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
settlement and remain outside the released runtime implementation paths:

~~~text
Docs/Plans/HANDOFF-AGENT-INTERACTION-world-conversation-runtime.md
Docs/Plans/HANDOFF-APP-STATE-agent-turn-claim-recovery-v1.md
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Roadmaps/ROADMAP-demo.md
~~~

The #869-to-#865 roadmap transfer remains status-only. Preserve #869's current
evidence and open status; do not claim #869 merged or full J4 acceptance. This
handoff now records only the actual #865 merge/head and reported code evidence;
it does not invent a consumer witness or operator acceptance.

No other source, schema, migration, MIND/Graph adapter, UI/Plan consumer,
provider deployment/configuration, lockfile, root configuration, or frozen
dirty checkout path is in this lease. In particular, preserve the suspended
`codex/agent-world-conversation-backend` checkout; do not edit or transplant
it.

### Accepted mapping and bounded replay response contract

These decisions bounded the pre-merge code repair. The owning-boundary
evidence disposition is recorded below; the activation gates at the top of
this handoff remain held.

PRIME accepted ARCHITECTURE's mapping and bounded replay-compatibility decision.
These decisions close design questions but do not waive implementation or
evidence gates.

1. **Graph provenance mapping:** persist the actual immutable Graph snapshot
   as a `HistoricalReference` with `kind="world_graph_revision"`,
   `object_id` equal to the actual native World ID, and `revision` equal to the
   actual returned immutable revision. Do not use fake hashes, IDs, or JSON
   metadata. Persist the snapshot even with no selection. If selected,
   `selected_object` names the actual admissible node kind and ID at that same
   revision; otherwise it is absent. Repeated normalized intent verified by
   the durable fingerprint supplies mode, scope, and focus. Revalidate
   server-derived verified World, binding, and role through the owning
   resolver. On replay, derive Graph scope/focus from matching verified intent
   and the stored snapshot. Keep `head_revision_id` and `is_head` unset unless
   that historical observation itself was persisted; never fetch today's head
   to populate them. Report any concrete inability of existing typed
   references to express this mapping; do not add schema fields or duplicate
   context bodies.
2. **Replay response:** a matching HTTP replay returns the stored answer,
   conversation ID, and frozen-reference projection. This is not byte-identical
   whole-response replay and does not authorize retrieval reruns or a fresh
   grounding claim. The existing model path is explicitly authorized to return
   `Graph.status="replayed"`; document consumer compatibility. Completed Plan
   replay may leave `primary_work.content_basis` null because the original
   `has_divergent_working_copy` boolean is not durably stored. Never infer that
   value from today's draft or `client_work_state`. Preserve the immutable full
   typed Plan basis in `TurnProvenance` and the response's primary revision
   fields, so a future exact-basis Ask projection can consume the immutable
   basis without claiming historical draft divergence. This bounded decision
   does not waive frozen stored provenance or historical retry requirements.
3. **Archived history boundary:** no public route, query parameter, provenance
   field, or APP schema/store duplication is authorized. The bounded POST
   replay contract above defines response compatibility for this slice. A
   broader archived-conversation history contract requires explicit contract
   transfer and a named owner.
4. **Claim/runtime bound:** use `claim_turn` directly so a live claim is
   pending and an expired claim can be reclaimed. Renew under the existing
   bounded lease. Serialize renewal and completion/failure so each operation
   uses the latest returned revision as the only valid fence; stop and join
   the renewer before finalizing. No runtime deadline is proven, and the
   default Hermes turn wait (120s) exceeds the 60s APP default; readiness and
   accept waits also count. Test renew and stale-fence outcomes.
5. **Completion persistence:** retry transient `complete_turn` writes with
   the same in-memory provider output and same live fence for a bounded number
   of attempts. The existing completion method recognizes the same result if
   a prior commit succeeded but its acknowledgment was lost. If retries exhaust
   or the fence is lost, return a truthful indeterminate/pending outcome; do
   not redispatch, fabricate success, or mark a stale fence completed.

Keep the five implementation paths, current schema, and current public API
unchanged unless PRIME explicitly transfers a missing contract.

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

### Required owning-boundary evidence — merge disposition

This was the evidence required for the #865 repair. PRIME reports the listed
route, PostgreSQL, Agent-service, auth, and HTTP-cardinality cases passed at
the reviewed head; the source lease has been released. The bullets preserve
the owning-boundary contract for future consumers and do not open an active
implementation lease.

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

### Exact-head evidence and held activation gates

At exact reviewed source head `097107324e0be5f5e7aa45e9633f70c09c4794e5`,
PRIME independently reported 58 combined route, PostgreSQL, Agent-service,
and auth tests passing in 41.43 seconds, plus the full HTTP cardinality test
passing in 8.42 seconds. The PostgreSQL cases used the PRIME-designated
disposable service at `127.0.0.1:55457` and fixture-created test databases.
ARCH's conditional code-acceptance holds were resolved at this head. PR #865
merged at `1c0320d18c53037308cd7412719fb3e2f0610d99`. These are code-level
results; no CI/branch-protection contexts or configured provider were reported.

The merged route/runtime lease is released. The configured-provider Plan
consumer witness, later Play consumer witness, human operator acceptance, and
J1–J6 product acceptance remain separate held activation gates. This document
does not grant those gates, a production database, or a live product-state
mutation. Do not treat the merge or the 59 code tests as product acceptance.
