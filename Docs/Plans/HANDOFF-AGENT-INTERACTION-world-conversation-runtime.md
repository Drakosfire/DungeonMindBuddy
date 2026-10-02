# HANDOFF — AGENT-INTERACTION: production World conversation runtime

- **Status:** BLOCKED — design contract only; no implementation, provider, database, or runtime lease.
- **Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`.
- **Owner:** PRIME to assign an AGENT-INTERACTION implementation task/owner.
- **Repository:** `Drakosfire/DungeonMindBuddy`.
- **Pinned base:** Buddy `main@672d18b059eaeceff20555374170ec2679f79082`.
- **Topology:** serial — APP-STATE storage/domain service (#822/#827 complete),
  AGENT-INTERACTION runtime adoption, DEMO Plan consumer cutover, then Play
  and remaining surface cutovers.
- **Design authority:** APP-STATE World conversation contract, ARCHITECTURE's
  2026-10-02 ruling, and PRIME's runtime-owner routing decision.

This handoff pins the missing production runtime contract. It does not activate
implementation. PRIME will review this design and assign an owner and exact
implementation lease. The implementation must have one bounded PR after that
activation.

## Mission

Connect Buddy's production generic Agent turn path to the accepted APP-STATE
World conversation service. A verified World has one server-issued active
conversation shared by its surfaces. Every accepted turn is durable, keeps the
surface/work basis under which it was submitted, and completes on that same
historical turn even if the user changes selection before the response returns.

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
- No open Buddy PR or active task currently owns production runtime adoption.
  The suspended `codex/agent-world-conversation-backend` checkout is dirty at
  `0e49c4d7`. Preserve it until PRIME explicitly reconciles its diff and grants
  a new lease. Do not edit, transplant, or infer authority from that checkout.

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
   Play, bind the selected Run/revision or snapshot and its pinned Runbook
   identity/revision/hash. Never treat a client locator as resolved authority.
4. Keep provider continuation separate from the World conversation ID. A Plan
   document or committed revision change starts a fresh provider segment even
   when the bytes happen to match. A Play Run or Runbook revision change also
   starts a fresh segment. Do not replay hidden provider history from a prior
   segment as if it were formed under the current work basis. Recompute current
   context and tools on every turn. Do not add resumable provider sessions if
   the selected adapter has none.
5. Correlate completion to the persisted originating turn and frozen work
   basis. A late Plan A result remains Plan A history; it is not dropped or
   attached to Plan B. A late Run A result remains Run A history; it cannot
   mutate or become the current answer for Run B.
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
- A future Plan consumer may import only allowlisted visible Ask turns whose
  stored `ownerId` exactly matches the independently verified World and whose
  `contentBasis` is preserved. Import must be idempotent by stable source-turn
  identity. Missing/mismatched turns are skipped or quarantined; do not infer
  ownership from a local namespace. Do not import proposal/action rows or
  Hermes handles. Keep local bytes until the owning service confirms import.

This runtime slice does not change Plan or Play UI, Graph retrieval, citations,
tool policy, Run/Runbook persistence, provider/model policy, deployment/auth,
APP-STATE schema, or proposal/Save behavior. The Plan consumer is the first
DEMO surface successor after runtime acceptance; Play follows under its pinned
handoff. Other surfaces remain separately bounded.

## Required owning-boundary evidence

The assigned implementation handoff must name the exact files, database,
provider fixtures, isolated runtime state, and PR topology after re-anchoring.
At minimum, its tests must prove:

- Production route/service calls use the APP-STATE conversation service and
  stable turn receipts, not browser history as authority.
- Plan and Play requests for the same verified World resolve the same active
  server conversation and ordered history across reload/fresh runtime
  instances; `New conversation` uses the durable command/CAS contract.
- User input is persisted before dispatch; retries, concurrent turns,
  interrupted calls, and late completion preserve sequence and originating
  provenance without fabricating an answer.
- Provider pointer/segment selection changes with the exact Plan or Play work
  basis and never leaks hidden history across document/revision/Run/Runbook
  boundaries.
- Invalid World/work/revision or malformed provenance fails closed before
  provider work. A database or receipt failure cannot silently fall back to
  localStorage.
- Verified Ask-history import is idempotent and exact-World scoped. Plan
  proposal/action bytes stay with their owning Plan path.

The later DEMO consumer witness must run a configured-provider Plan multi-turn
conversation, reload it, switch to another Plan and to Play in the same World,
and prove shared visible history, exact provenance, segment isolation, and
late-result placement. It is not operator acceptance of J1–J6.

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

Until activation, this design grants no write, provider, database, service,
port, shared-runtime, or product-state authority. D0 appearance and J1–J6
acceptance remain independent open gates.
