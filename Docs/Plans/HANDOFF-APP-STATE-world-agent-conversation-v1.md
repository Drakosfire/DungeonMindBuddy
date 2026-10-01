# APP-STATE — World-scoped Agent conversation continuity

**Status:** BLOCKED — design selected; implementation lease not active
**Owner:** APP-STATE
**Repository:** `Drakosfire/DungeonMindBuddy`
**Design base:** `main@bfa741261e715eadb48d873f87fccc1764417da8`
**Topology:** serial: APP-STATE storage/domain service, then AGENT-INTERACTION runtime adoption, then DEMO surface cutover.
**Decision authority:** `ARCHITECTURE-application-state-layer.md`, `DECISION-agent-context-compilation.md`, and the assigned ARCHITECTURE review.
**Product integration owners:** AGENT-INTERACTION and DEMO.

This handoff records a selected design. It does not authorize schema, runtime,
route, provider, or UI edits. PRIME must activate a separate exact path and
runtime lease after this design reconciliation lands and the implementation
base is re-anchored.

## 1. Evidence and reason for selection

The old assumption that an Agent thread is only a browser-local UI session is
no longer true for the selected managed-World product behavior: one active
conversation per verified World across surfaces, with current surface/work
context and tools recomputed on every turn (Hermes first; Pi later).

Evidence on `main@bfa7412`:

- `agentInteractionHistory.ts` stores visible turns, thread indexes, and
  per-surface/document active-thread pointers in browser `localStorage`; the
  retained history is capped at 20 turns. Index and World Plan use different
  local namespaces, so neither supplies one cross-surface World identity.
- The generic `/api/live/agent/turn` request has client thread and turn IDs but
  does not persist canonical turns or provide a stable server conversation ID.
- Buddy #817 adds a stable Hermes profile root and a structured pointer for the
  exact saved Plan/World/client-thread binding. That restores Hermes-native
  execution history; it is provider state, not canonical conversation or draft
  identity, and it does not unify surfaces.
- Existing Plan edit proposals are stored inside local Agent thread data as
  replacement Markdown plus an `applied` boolean. Applying one changes the
  mounted Plan editor draft; that boolean is not a saved-work receipt.
- Buddy already has a shared PostgreSQL Application State authority with
  domain-owned schemas/services and transaction support. No second database
  or DungeonMind World table is needed.

These facts justify one bounded durable Agent Conversation family. They do not
justify a generic state engine, arbitrary JSON store, semantic Interaction
Memory, or persistence of provider/tool internals.

## 2. Selected product/storage contract

### Identity and lifecycle

- A server-generated opaque `conversation_id` is Buddy product identity. It is
  independent of browser keys, surface IDs, Plan/work IDs, campaign IDs, and
  Hermes/Pi session IDs.
- The owning Agent service verifies the DungeonMind-issued `world_id` on every
  operation. Buddy stores it as an opaque external owner reference with no SQL
  foreign key or copied World truth. In the current single-operator product
  scope, each World has zero or one active conversation; a future account or
  multi-operator model requires a separately approved identity dimension.
- `New conversation` carries a stable caller-generated command ID. Repeating
  that ID with the same World and command returns the same server-generated
  conversation ID; reusing it with a different binding conflicts. Creation,
  activation, command receipt, and archival of the previous active conversation
  commit atomically, so a lost response can be reconciled without creating a
  second conversation. Archive is recoverable. Archiving the active
  conversation clears the active pointer; the next submitted turn creates a
  fresh conversation. Reopening an archived conversation preserves its
  ID/history and atomically archives the former active conversation.
- Archived conversations have no automatic TTL. This slice exposes no delete
  or purge operation; it must not delete data when a World is unavailable or
  removed. Unverified/removed Worlds fail closed while Buddy records remain
  retained. A later explicit deletion/retention policy is a separate contract.

### Turns, provenance, and provider boundary

- Persist the accepted user submission before runtime dispatch. Persist only
  the completed user-visible assistant response/refusal as its paired result.
  An interrupted or failed call retains the user submission and truthful
  lifecycle status without inventing an answer.
- Each turn has a stable idempotency key, request fingerprint, sequence, and
  lifecycle state. Repeating the same key and same request returns or resumes
  the recorded turn; key reuse with different content/binding conflicts. A
  conversation revision/sequence CAS rejects stale concurrent writers instead
  of reordering them. Exactly-once provider invocation across crashes is not
  promised; durable turn recording and honest pending/failed/retry states are.
- Store typed server-resolved historical provenance only: `world_id`,
  `surface_id`/instance, work kind/ID and exact work/source revision when
  applicable, and selected-object ID when applicable. Explicit absence is
  distinguishable from unavailable/unresolved. These IDs explain the old turn;
  they are not a context snapshot, permission, or input to later resolution.
- Canonical history is provider-neutral visible user/assistant text. The Agent
  owner chooses a bounded recent-history window for Hermes/Pi replay. Each new
  turn independently verifies the World, resolves the current surface/work,
  re-reads current revisions, and rebuilds graph scope, context, and tools.
  Earlier turns may resolve conversational references; they never assert
  World truth.
- Do not store model reasoning, system prompts, compiled context/retrieval
  packets, tool arguments/results/state, credentials, or provider-native
  history as conversation authority. Hermes/Pi session IDs are not required
  to recover a conversation. #817's Hermes profile/pointer is transitional
  adapter state and must not be imported as a conversation or draft.

### Composer drafts

- A composer draft is a separate typed durable record, not an ordered turn.
  It has a stable draft ID and CAS revision and is bound to the verified World,
  conversation, and typed source context (surface plus work/source IDs and exact
  revision when present; absence is explicit).
- Recover it only under that same binding after reload, process/host restart,
  or returning to its World. Switching World/source never transfers it. A
  changed or unavailable source leaves the text recoverable but stale; it must
  not be submitted under the new context without explicit revalidation.
- Saving a draft does not send it to the Agent. Explicit submit atomically
  accepts the user turn and retires the exact draft revision. If the response
  is uncertain, the caller retries/reconciles with the same turn key; it does
  not clear the draft or create a duplicate visible user message until commit
  is confirmed.
- Current unsent text is component state, not a persisted predecessor, so
  there is no legacy unsent-draft backfill. The new UI must save it before
  relying on restart recovery.

### Pending domain actions

- No generic Agent action or receipt table is selected. Each action's owning
  domain records its own pending/uncertain/committed/failed outcome and
  idempotency. Conversation may retain a typed operation reference and safe
  user-visible summary only.
- Plan edit proposals, replacement Markdown, editor-application state, and
  saved Plan commit receipts remain Plan/Content-owned. “Applied to editor
  draft” is not “saved/committed.” A stale proposal may be displayed as
  historical but must not auto-apply or rebase.
- The current local Plan proposal payload is not an eligible conversation
  turn and is not imported by this family. Keep that local data until the
  Plan/Content owner provides its own adoption or stale-proposal disposition.

## 3. Predecessor import and cutover

- Legacy localStorage keys, thread IDs, active pointers, campaign-like
  namespace strings, and Hermes handles are import metadata, never server
  identity or World authority.
- Import only allowlisted visible user/assistant turns whose per-turn stored
  verified World ID exactly matches the World independently resolved by the
  server. Preserve order and typed historical provenance. Do not infer World
  from the currently selected route, a Plan/campaign/local namespace, or a
  Hermes profile. Import requests are bounded and idempotent by a stable
  source-import key; the new conversation ID remains server-assigned.
- Do not merge surface/document-local threads. If exactly one eligible legacy
  active thread exists for a World it may be imported active. If there are
  multiple or contradictory active candidates, import eligible histories as
  archived and leave the World active pointer unset until the user chooses.
  Unbound/malformed histories are quarantined or left local, never attached to
  another World.
- Keep local transcript bytes until the server confirms that exact import.
  Then the owning UI may remove or demote the imported transcript to a cache;
  do not dual-write. Preserve local Plan action payloads until their owner
  handles them. Import only bounded safe summaries; traces remain separately
  typed and never become conversation text. The existing 20-turn browser cap
  means older discarded turns cannot be reconstructed. Hidden Hermes profile
  messages are never imported.
- After all current consumers cut over, ordinary transcript and draft reads/
  writes use Buddy PostgreSQL and fail closed when unavailable. No fallback to
  localStorage as current authority. Retire the Plan-only native Hermes
  continuity dependency after its consumer is migrated; do not remove it early
  from unrelated legacy paths.

## 4. Ownership boundaries

```text
Buddy PostgreSQL agent domain service
  ├── conversation identity/lifecycle and one-active-per-World constraint
  ├── visible turn lifecycle, idempotency, ordering/CAS, typed provenance
  ├── typed source-bound composer drafts and submit reconciliation
  └── bounded, verified, idempotent legacy transcript import

AGENT-INTERACTION
  ├── conversation lifecycle and request semantics at AgentRuntime
  ├── fresh per-turn context/tool policy and bounded history replay
  └── Hermes now; Pi adapter later

DEMO / surface and owning domains
  ├── active conversation and draft UI across surfaces
  ├── localStorage import/cutover and user-visible recovery
  └── Plan edit proposals and action receipts in their owning services

DungeonMind
  └── World identity/truth and WorldGraph authority
```

Buddy stores no World facts and creates no cross-database foreign keys. Play
surface/runtime semantics and the current DEMO #820 work are outside this
family.

## 5. Reviewable implementation sequence

1. **APP-STATE storage/domain-service PR (serial, first).** Extend the existing
   Buddy Application State PostgreSQL database with only the typed Agent
   Conversation, Turn, and ComposerDraft records. Implement one-active-per-
   World, stable IDs, turn and draft CAS/idempotency, typed provenance, and the
   verified legacy transcript import. Use the existing UoW/DSN/migration
   authority. Prove the contract at real PostgreSQL through the owning service:
   World isolation, active switching/archive/reactivation, concurrent writes,
   duplicate/uncertain turn and draft submission, import conflicts, restart
   recovery through a fresh service instance, and DB-unavailable fail-closed
   behavior. No UI, Play, provider-profile, WorldGraph, or live provider work.
2. **AGENT-INTERACTION backend adoption (successor lease).** Connect the actual
   generic Agent turn path to canonical history: persist the user submission
   before dispatch, replay only the bounded visible turns, resolve fresh
   context/tools each turn, and persist final response/status. Keep provider
   metadata outside conversation identity. Add exact boundary evidence for
   interrupted/retried turns. This does not change tool policy or surface
   semantics without their owner's authority.
3. **DEMO product cutover (successor lease).** Adapt current Agent surfaces to
   World-global active conversation and source-bound draft APIs; import legacy
   histories idempotently and retain local bytes until confirmation. Mounted
   UI/DEMO acceptance must prove cross-surface continuity and honest recovery.
   Plan edit/action artifacts are migrated only by their owning domain. APP-STATE
   evidence does not claim this user journey complete.

Keep these serial unless PRIME later verifies independent path/runtime
ownership. Do not dispatch steps 2–3 before the predecessor gate and explicit
owner leases resolve.

## 6. Proposed APP-STATE implementation write set — not yet leased

The following exact candidate paths are for PRIME's later lease decision only.
They are **not** an ACTIVE write lease:

- `src/application_state/migrations/versions/20261001_0010_agent_conversation.py`
- `src/application_state/agent_conversation/__init__.py`
- `src/application_state/agent_conversation/types.py`
- `src/application_state/agent_conversation/repository.py`
- `src/application_state/agent_conversation/service.py`
- `tests/application_state/test_agent_conversation_service.py`
- `tests/application_state/test_agent_conversation_postgres.py`

If actual persistence cannot be proven at these owning-service paths, return to
PRIME with the exact boundary/path gap. Do not silently expand into Agent
runtime, routes, shared API types, migrations owned by another lane, or UI.

## 7. Explicitly unresolved successor decisions

- The owning product UI must choose how an active-pointer-unset World prompts
  the user to select/import one of several archived legacy conversations.
- Plan/Content must define durable proposal adoption and action-operation
  receipts, including exact target revision and uncertain-save reconciliation.
- AGENT-INTERACTION must choose bounded history size/compaction and failure
  retry presentation without changing the stored canonical transcript.

These are integration gates, not reasons to broaden this storage family.
