# HANDOFF — AGENT-INTERACTION: production World conversation runtime

- **Status:** BLOCKED — design contract only; no implementation, provider, database, or runtime lease.
- **Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`.
- **Owner:** PRIME to assign an AGENT-INTERACTION implementation task/owner.
- **Repository:** `Drakosfire/DungeonMindBuddy`.
- **Design origin:** Buddy `main@672d18b059eaeceff20555374170ec2679f79082`.
- **Prepared re-entry base:** Buddy `main@6a17c852971ad087eca1b8d43450a31f67cf2c3d` (2026-10-02).
- **Topology:** serial — APP-STATE storage/domain service (#822/#827 complete),
  AGENT-INTERACTION runtime adoption, DEMO Plan consumer cutover, then Play
  and remaining surface cutovers.
- **Design authority:** APP-STATE World conversation contract, ARCHITECTURE's
  2026-10-02 ruling, and PRIME's runtime-owner routing decision.

This handoff pins the missing production runtime contract and the prepared
resumed-#865 packet below. It does not activate implementation. The packet is
pending PRIME acceptance; no implementation lease is active.

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

## Activation gates and return contract

This handoff is BLOCKED until PRIME:

1. Names the AGENT-INTERACTION owner/task and exact checkout/head.
2. Reconciles the suspended dirty checkout before choosing files or transplanting
   any work.
3. Pins an exclusive expected-path allowlist, test boundary, provider/DB/runtime
   lease, and one-PR serial topology on a refreshed Buddy base.
4. Confirms no overlapping runtime, schema, or dependency lease and accepts this
   contract's provenance and provider-segment rules.

The owner returns the exact base/head, cumulative diff, owning-boundary test
results and preserved failures, runtime/API contract, retry and migration
behavior, provider-segment behavior, and unresolved acceptance gates. PRIME
reviews and controls merge. Only then may DEMO pin its Plan consumer lease.

## Resumed #865 activation packet — prepared, pending PRIME acceptance

This packet records the bounded successor proposed after APP-STATE #867 and
does not grant a code, provider, database, service, port, or product-state
lease. The frozen #865 source head below is evidence/reference only; it is not
an accepted runtime revision.

- **Re-anchored base:** Buddy `origin/main@6a17c852971ad087eca1b8d43450a31f67cf2c3d`.
- **Frozen #865 reference:** PR #865 head
  `b8aa42c3b4b6b5201d39b19aa62c2bef364cc94c`; five original runtime/test paths.
- **Recovery predecessor:** APP-STATE #867 merged at
  `21af97cdc5fe4d10c10032b35c9b26c9ff23ac2b`, from reviewed head
  `7c8cf2951dd5c47b76297aee1bbdbd34d2c33ce9`. Its four owning suites passed
  34 tests in about 52.96 seconds; architecture accepted. Re-read the merged
  handoff and cumulative main diff before implementation.
- **Open work preserved:** #869 remains open. Its draft control coverage,
  149-test result, inherited typecheck failure, and pending real witness are
  not #865 acceptance evidence. The #869 branch retains its own implementation
  paths; PRIME transferred only the exclusive status-only
  `Docs/Roadmaps/ROADMAP-demo.md` path to the future #865 successor.
- **Owner:** PRIME to assign after accepting this packet.
- **Topology:** one serial implementation PR, resumed from the refreshed base.
  No second runtime capability or PR is included.

### Proposed exclusive expected-path allowlist

Runtime and owning-boundary tests:

~~~text
apps/live_control_server/models/agent_turn.py
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_turn_service.py
tests/application_state/test_agent_conversation_postgres.py
tests/test_agent_turn_route.py
tests/test_agent_turn_service.py
~~~

The final four paths below are restricted to backward-looking status/evidence
settlement after the implementation result is known. They authorize no
behavioral edits and do not authorize edits before the successor lease is
activated:

~~~text
Docs/Plans/HANDOFF-AGENT-INTERACTION-world-conversation-runtime.md
Docs/Plans/HANDOFF-APP-STATE-agent-turn-claim-recovery-v1.md
Docs/Roadmaps/ROADMAP-application-state.md
Docs/Roadmaps/ROADMAP-demo.md
~~~

The #869-to-#865 roadmap transfer is status-only and exclusive for the
successor's settlement. Preserve #869's current evidence and open status; do
not claim #869 merged or full J4 acceptance. APP-STATE's recovery handoff and
roadmap record only the already-merged #867 result. Do not pre-mark the
in-flight runtime slice complete or invent its merge SHA, review count, or
witness.

No other source, schema, migration, MIND/Graph adapter, UI/Plan consumer,
provider deployment/configuration, lockfile, root configuration, or frozen
dirty checkout path is in this lease. In particular, preserve the suspended
`codex/agent-world-conversation-backend` checkout; do not edit or transplant
it.

### Runtime ordering and receipt contract

First independently verify World authority and validate the normalized
request's syntactic scope without resolving today's Plan, Graph, selected-work
authority, or conversation pointer. Construct the canonical submitted intent
from that original normalized request envelope and reconcile the World/key
receipt before any current-work resolution. An exact receipt returns the
original conversation, turn status/result, and frozen typed provenance without
depending on today's Plan, Graph, or active pointer. A changed semantic intent
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

- **Service tests** (`tests/test_agent_turn_service.py`): exact completed
  receipt after Plan/head and active-pointer rotation returns the old result
  without current Plan/Graph/provider lookup or another dispatch; changed
  semantic fields conflict while changed `client_thread_id` does not. A live
  claim returns pending with zero second dispatch; expiry/reclaim advances
  revision and attempt; renew returns the current fence; stale completion and
  failure fail before and after reclaim; persistence retry reuses the same
  provider output.
- **Route tests** (`tests/test_agent_turn_route.py`): prove authorization,
  ordering, request normalization, response/status behavior, and zero provider
  work for invalid World/work scope or an unverifiable receipt.
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

No test result is presumed by this packet. Record exact commands, environments,
failures, and evidence on the successor before requesting review.

Until activation, this design grants no write, provider, database, service,
port, shared-runtime, or product-state authority. D0 appearance and J1–J6
acceptance remain independent open gates.
