# HANDOFF — DEMO: project typed Plan action dialogue

**Status:** PREPARED — design-only amendment to merged PR #859. Implementation remains BLOCKED until the AGENT-INTERACTION runtime is accepted and PRIME activates the exact lease below. No lease for this Plan-action capability is active.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Repository:** `Drakosfire/DungeonMindBuddy`

**Preparation base:** Buddy `main@327bdb5a899178eef2c16f3e9198219eb8e79773` (PR #863 merge).

**Accepted design:** PR #859 merged at `43c4c4daa8e1c17b22953681fe817e6881242b36` from reviewed head `c78feb94f37f7612200e2d0962d26d0f5a1326cf`. This amendment narrows the action-record scope and records the shared-migration ownership ruling; it does not activate implementation.

**Topology:** serial — APP-STATE World conversation storage/receipts (#822/#827 complete) → AGENT-INTERACTION production runtime adoption → this Plan-owned action-dialogue projection capability → DEMO Plan World-conversation cutover in [HANDOFF-DEMO-plan-world-conversation-cutover.md](HANDOFF-DEMO-plan-world-conversation-cutover.md). The action projection is a separate capability and PR, not an expansion of the consumer lease.

**Future implementation PR title:** `DEMO: persist Plan action dialogue projection`.

## One bounded capability

Compose/Revise on a saved managed-World Plan can later use the last six eligible
visible Plan dialogue turns. This capability supplies only the Plan-owned
action-dialogue record and its safe typed read projection. The later consumer
composes that source with eligible Ask turns from the exact APP-STATE World
conversation. Each action is bound to the verified World, exact Plan document,
and committed content basis; when a submitted mounted draft differs from that
basis, the record carries a separate input witness. The safe projection
contains the action type, exact basis references, truthful status, user
instruction, and an assistant-visible summary only for completed actions. It
does not expose proposal or draft bytes.

This capability supplies a typed Plan action-history source for the later
consumer cutover. It does not read or merge APP-STATE Ask turns, replace the
APP-STATE World transcript, move Plan actions into generic conversation
storage, change proposal review/Apply/Save behavior, or implement the consumer
cutover itself. Proposal content and Apply/Save receipts are outside this
capability and require a separate design and lease if later persistence is
needed. Only completed instruction/summary exchanges enter future bounded
conversational context; pending, failed, and indeterminate records remain
truthful status items and are not replayed as assistant turns.

## Storage and ownership boundary

Use the existing Buddy Application State PostgreSQL database and its single
Alembic migration authority under `src/application_state/migrations/versions`.
Do not create another database, add a generic APP-STATE transcript/action
table, or require a cross-database transaction. Plan/DEMO owns this distinct
action schema's semantics, repository/service, idempotency, lifecycle, and safe
projection. APP-STATE owns the shared migration runner, unit-of-work, DSN, and
database infrastructure and must explicitly review and authorize the
Plan-owned migration path before implementation activation. A Plan-owned
package alongside the existing `content`, `play`, and `agent_conversation`
packages is the expected fit; PRIME must pin its exact path in the lease.

## Current evidence and gap

- `POST /api/live/world-plan-edit/propose` accepts the World ID, Plan document
  ID, base object revision and content hash, mounted draft and digest, target
  kind, selected text, instruction, and a client-supplied
  `conversation_history`. The server verifies the managed World and Plan and
  rejects a stale base, then passes the supplied history into proposal
  generation. This request history is not an authoritative Plan dialogue
  store.
- `WorldPlanAgentConversation.tsx` currently builds that history from the six
  most recent `currentThread.turns`, regardless of `backend`. It stores both
  generic Ask and `plan_edit` turns in browser `localStorage`.
- Buddy #858 repaired the separate `PlanAgentInteractionBar.test.tsx` fixture
  against the current selected-World document API. It changed no Plan proposal
  or World Plan Agent production code, so this boundary audit is unchanged.
- A local `plan_edit` turn contains the instruction, visible response summary,
  replacement Markdown, and an `applied` flag, but no exact committed
  WorkRevision/content basis. It cannot safely be attached to the selected
  Plan's current basis after reload or import by inferring from route state.
- PRIME's ruling is to preserve the existing six-item Compose/Revise dialogue
  behavior. The consumer must combine eligible APP-STATE Ask turns and this
  Plan-owned projection, ordered by accepted time/sequence and filtered to the
  exact same Plan and committed basis. Ask-only narrowing is not authorized.
- ARCHITECTURE assigned Plan/Content ownership as follows: the Plan proposal/
  action owner owns this typed read model; Content remains the authority for
  resolving the committed Plan basis; APP-STATE continues to own generic
  World conversation turns. Do not store Plan action rows in APP-STATE or make
  Content own the action dialogue.

This is a design contract only. The current proposal service does not expose
the typed projection or persist Plan action dialogue. Re-anchor and obtain an
exact, exclusive implementation lease after the runtime predecessor is
accepted. Current runtime routes and services remain outside this handoff.

## Write-time record contract

On each successful World Plan Compose/Revise command, the Plan proposal/action
owner resolves and validates the managed World, active Plan, and exact
committed basis before generation. The basis is server-resolved and contains:

- managed World ID and Plan document ID;
- committed object revision;
- immutable WorkRevision ID and revision number;
- committed content SHA-256.

The proposal request's base revision/hash must match that basis. If the basis
is missing, stale, foreign, or ambiguous, fail closed before provider work and
do not create a projected dialogue entry. Content remains the source of the
committed-basis truth; the Plan owner stores a typed reference to it.

Before provider dispatch, reserve a durable Plan-owned action row in a
transaction. Each row contains:

- a server-assigned durable action ID;
- the client-generated idempotency key for this user intent, which the client
  must reuse with an identical request and basis on uncertain network retry;
- a canonical request fingerprint covering the verified basis and all
  generation inputs whose identity affects the result;
- server order/sequence, accepted timestamp, and truthful request outcome;
- verified World, Plan document, and full committed-basis tuple above;
- the user's instruction text;
- the assistant-visible proposal summary text only after a validated result is
  durably recorded as completed;
- an input witness separate from the committed basis.

The input witness records whether the submitted mounted draft matched the
committed basis, a server-computed SHA-256 of the exact submitted draft, and
the selection target kind plus selected-text digest (or equivalent stable
selection range witness) when selection affected the proposal. If the mounted
draft is dirty, preserve that fact truthfully; never label its digest or bytes
as committed Plan content. Neither the durable action record nor its projection
stores draft bytes, selected text, replacement Markdown, proposal payload,
Apply/Save receipts, traces, provider session IDs, or hidden provider state.

The client creates one stable idempotency key per user intent and resends that
key with the identical request and basis on every uncertain network retry. The
server assigns a separate action ID when it reserves the row. Same-key,
same-fingerprint retries return or reconcile that row; same-key reuse with a
changed instruction, basis, draft witness, or other fingerprinted input
conflicts. Stale or invalid basis fails before provider work. Persist the
truthful state as `pending`, `completed`, `failed`, or `indeterminate`. A
completed row includes the safe assistant summary; other states do not.

Provider dispatch and database commit cannot be one exactly-once transaction.
If a provider result is uncertain, retain `indeterminate` and reconcile by a
known provider correlation only when the runtime supports it; otherwise require
an explicit new user intent instead of blindly redispatching. A persistence
failure after dispatch must not fabricate a completed action. Never silently
fall back to client history as authority.

The record is a Plan-owned action dialogue, not an APP-STATE generic Agent
turn, tool result, or proposal receipt. Its visible dialogue text is the
instruction and, only when completed, the assistant summary. Action type,
basis references, and status are safe typed metadata; input witnesses remain
private filtering metadata.

## Read and ordering contract

The Plan owner provides an authoritative server-side read/projection for the
consumer. It accepts a server-verified World, Plan document, and committed
basis and returns only records matching all three, ordered by server accepted
time/sequence with a stable tie break. It includes truthful `pending`,
`failed`, and `indeterminate` status items for UI recovery. A completed item
contains one user instruction paired with its assistant summary; other states
have no fabricated assistant response. The projection is bounded to at most
six action records. Only completed instruction/summary pairs are eligible for
the later conversational context. The consumer merges those with eligible
APP-STATE Ask turns, applies the overall six-turn cap after ordering, and never
supplies an authoritative client `conversation_history` array.

A new object revision, WorkRevision ID/number, or content hash starts a
different eligible basis. Old action dialogue may remain historical in the
Plan owner but is not returned as current context for the new basis. Plan A
and Plan B queries cannot cross. A late proposal response is correlated with
its originating action command/basis and cannot be attached to the currently
selected Plan after a switch.

The projection read should remain internal to the Plan proposal/action owner
unless a reviewed consumer contract requires a public API. It does not expose
replacement text, draft bytes, selection bytes, provider history, or the whole
World transcript. The later Plan consumer is responsible for merging this
source with exact-basis APP-STATE Ask turns and rendering World transcript
provenance.

## Legacy rows and exclusions

Existing browser `plan_edit` rows do not include the required committed-basis
tuple or a server action receipt. Treat them as basis-unknown and ineligible
for this projection. They may remain in their Plan-owned legacy view or be
quarantined under a later exact lease; never assign the currently selected
basis, import them as APP-STATE Ask turns, or infer ownership from a local
namespace. Preserve existing local bytes until a separately approved
disposition is implemented.

This capability does not change:

- APP-STATE conversation schema or generic turn lifecycle;
- Content's committed Plan records or revision authority;
- the visible World transcript or Plan Ask #833 committed-content disclosure;
- Plan proposal review, Apply-to-editor behavior, ordinary Save, or the
  browser's current unsent draft while this design is blocked;
- Agent provider-segment ownership, Graph scope, citations, retrieval, or
  J1–J6 acceptance.

## Failure cases and future owning-boundary witness

After activation, tests at the Plan proposal/action service boundary must
prove:

1. Exact managed World, Plan, object revision, WorkRevision ID/number, and
   content digest are resolved server-side; foreign, missing, stale, or
   mismatched values fail before provider work.
2. Clean and dirty mounted drafts record the same correct committed basis but
   distinct server-computed working-input witnesses. Selection identity is
   captured without persisting selected text or draft bytes.
3. The projection returns only allowlisted instruction, safe assistant
   summary, action type, exact basis references, and truthful status;
   non-completed states have no assistant summary. Replacement Markdown,
   draft bytes, Apply/Save receipts, traces, provider IDs, and hidden history
   are absent from projection output.
4. Same-key/same-fingerprint retries do not duplicate rows; reuse of the same
   idempotency key with a changed fingerprint conflicts. A `pending` row is
   reconciled without blind redispatch; a definite failure or indeterminate
   result remains visible and requires a deliberate new user intent if it
   cannot be reconciled. Projection persistence failure retains explicit
   truthful state and does not fabricate dialogue.
5. Projection queries reject another World, Plan, or committed basis; preserve
   stable order; return at most six action turns; and isolate Plan A from B.
6. A late response remains bound to the originating action ID and basis after
   Plan/World switch. Existing proposal review, Apply-to-editor, and ordinary
   Save behavior still pass.

Use an isolated fake provider/runtime and only a disposable persistence
fixture explicitly named by PRIME's implementation lease. No production
database, shared service, port, or live product state is leased by this
PREPARED design. A bounded configured-provider acceptance witness, if later
useful, is covered by the standing DEMO authorization; it must use the
configured provider/model, finite retries, and honest unknown cost receipts.

## Activation gates and future lease

This handoff is PREPARED and stays BLOCKED until PRIME:

1. Accepts the AGENT-INTERACTION runtime PR/base/head and its owning-boundary
   evidence.
2. Confirms `apps/live_control_server/services/workspace_document_registry.py`
   `get_committed_playable_revision(document_id, kind="plan",
   expected_world_id=...)` supplies the exact committed-basis tuple needed by
   this owner. Any new Content resolver is a separate owner contract.
3. Obtains APP-STATE's explicit review/authorization of the Plan-owned
   migration using the shared Alembic authority.
4. Re-anchors Buddy main, inspects open PRs/active leases, and grants an exact
   exclusive file/path allowlist, disposable persistence/provider fixtures,
   verification boundary, and one serial implementation PR.

Candidate source paths for future investigation only: the World Plan proposal
model/service/route and their owning tests; a Plan-owned package under
`src/application_state`; one additive migration under
`src/application_state/migrations/versions`; and the minimum Plan UI request
correlation needed to create and reuse a stable idempotency key. The fixture
candidate is the unique-database `application_state_dsn` test helper against
the PRIME-owned disposable PostgreSQL 16 service, subject to PRIME's exact
lease. `routes/live.py` is a shared collision hotspot and must not be changed
while another lease owns it. These are candidates, not an allowlist or write
authority. If implementation needs another owner, path, schema, or API, stop
and return the exact contract gap to PRIME.

The implementation PR for this capability must merge and its read/write
contract be reviewed before the DEMO Plan consumer cutover can activate. The
two changes remain separate capabilities and separate PRs. Human visual and
connected J1–J6 acceptance stay open.

## Design review and merge settlement

Buddy PR #859 merged at main `43c4c4daa8e1c17b22953681fe817e6881242b36`
from reviewed head `c78feb94f37f7612200e2d0962d26d0f5a1326cf` after PRIME's
exact-diff review. It accepts this bounded capability's design only. The
present amendment records ARCHITECTURE's clarified private action-record state
machine and shared-migration boundary, plus PRIME's decision to exclude
proposal bytes and Apply/Save lifecycle from this slice. Implementation remains
BLOCKED until the AGENT-INTERACTION runtime is accepted, Content confirms the
exact committed-basis resolver, APP-STATE reviews the Plan-owned migration, and
PRIME grants an exclusive path and verification lease. No provider, database,
service, runtime, or product-state authority was granted by #859.
