# HANDOFF — DEMO: project typed Plan action dialogue

**Status:** BLOCKED — design only; the AGENT-INTERACTION runtime is the serial predecessor. No implementation, provider, database, service, or runtime lease is active.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Repository:** `Drakosfire/DungeonMindBuddy`

**Design base:** Buddy `main@13dbf3a42b0b040a482c0ced1ec0fe5d7b314c37` (PR #858 merge; #857 is its parent).

**Topology:** serial — APP-STATE World conversation storage/receipts (#822/#827 complete) → AGENT-INTERACTION production runtime adoption → this Plan-owned action-dialogue projection capability → DEMO Plan World-conversation cutover in [HANDOFF-DEMO-plan-world-conversation-cutover.md](HANDOFF-DEMO-plan-world-conversation-cutover.md). The action projection is a separate capability and PR, not an expansion of the consumer lease.

**Future implementation PR title:** `DEMO: persist Plan action dialogue projection`.

## One bounded capability

Compose/Revise on a saved managed-World Plan can use the last six eligible
visible Plan dialogue turns through an authoritative Plan-owned projection.
The projection includes Ask turns from the exact APP-STATE World conversation
and prior Plan action dialogue from this capability. It binds every action to
the verified World, exact Plan document, and committed content basis; when a
submitted mounted draft differs from that basis, it records a separate input
witness. It exposes the user instruction and assistant-visible summary only,
not the proposal or draft bytes.

This capability supplies a typed Plan action-history source for the later
consumer cutover. It does not replace the APP-STATE World transcript, move Plan
actions into generic conversation storage, change Plan review/Apply/Save
ownership, or implement the cutover itself. The visible Plan proposal remains
reviewable under existing behavior; only the narrow dialogue projection is
eligible for future bounded context.

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

After successful generation and owner validation, persist a bounded typed
dialogue record with:

- a server-assigned action ID, server order/sequence, and accepted timestamp;
- verified World, Plan document, and full committed-basis tuple above;
- the user's instruction text;
- the assistant-visible proposal summary text;
- an input witness separate from the committed basis.

The input witness records whether the submitted mounted draft matched the
committed basis, a server-computed SHA-256 of the exact submitted draft, and
the selection target kind plus selected-text digest (or equivalent stable
selection range witness) when selection affected the proposal. If the mounted
draft is dirty, preserve that fact truthfully; never label its digest or bytes
as committed Plan content. The projection stores no draft bytes, selected text,
replacement Markdown, proposal payload, Apply/Save receipts, traces, provider
session IDs, or hidden provider state.

Only a successful, validated proposal result may contribute an assistant
summary. Failure, timeout, rejected/stale basis, malformed response, or
uncertain provider outcome must not fabricate a completed dialogue row. The
Plan owner defines an idempotent action command/receipt: retrying the same
request returns or reconciles its original record; reusing its stable key with
a different request/basis conflicts. If the owner cannot atomically make a
valid result and its narrow projection available, report the persistence
failure explicitly and keep the action ineligible for later context until
reconciled. Never silently fall back to client history as authority.

The record is a Plan-owned action dialogue, not an APP-STATE generic Agent
turn, tool result, or proposal receipt. Its user-visible fields are exactly the
instruction and assistant summary; provenance/input witnesses are metadata
used for filtering and truthful disclosure.

## Read and ordering contract

The Plan owner provides an authoritative server-side read/projection for the
consumer. It accepts a server-verified World, Plan document, and committed
basis and returns only completed visible action dialogue that matches all
three. It orders records by server accepted time/sequence with a stable tie
break, and returns a bounded page of at most six action turns. Each action turn
is one user instruction paired with its assistant summary. The consumer later
merges this source with eligible APP-STATE Ask turns, applies the overall
six-turn cap after ordering, and never supplies an authoritative client
`conversation_history` array.

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
3. Only a validated user instruction and assistant summary are returned by
   the projection. Replacement Markdown, draft bytes, Apply/Save receipts,
   traces, provider IDs, and hidden history are absent from persistence and
   projection output.
4. Idempotent retries do not duplicate action turns; conflicting key reuse,
   proposal failure, malformed response, uncertain completion, and projection
   persistence failure remain explicit and do not fabricate dialogue.
5. Projection queries reject another World, Plan, or committed basis; preserve
   stable order; return at most six action turns; and isolate Plan A from B.
6. A late response remains bound to the originating action ID and basis after
   Plan/World switch. Existing proposal review, Apply-to-editor, and ordinary
   Save behavior still pass.

Use isolated fake provider/runtime and only a disposable persistence fixture
explicitly named by PRIME's implementation lease. No configured provider,
production database, shared service, port, or live product state is leased by
this BLOCKED design. A configured-provider witness, if needed, requires a
separate exact PRIME approval.

## Activation gates and future lease

This handoff stays BLOCKED until PRIME:

1. Accepts the AGENT-INTERACTION runtime PR/base/head and its owning-boundary
   evidence.
2. Confirms Content can provide the exact committed basis tuple to the Plan
   owner. Any new Content resolver is a separate owner contract.
3. Pins the Plan proposal/action service as owner and approves its exact typed
   record, idempotency, ordering, projection filter, dirty-draft witness, and
   failure semantics with ARCHITECTURE.
4. Re-anchors Buddy main, inspects open PRs/active leases, and grants an exact
   exclusive file/path allowlist, disposable persistence/provider fixtures,
   verification boundary, and one serial implementation PR.

Candidate source paths for future investigation only: the World Plan proposal
model/service/route and their owning tests, plus the minimum Plan UI request
correlation needed to carry a stable action key. `routes/live.py` is a shared
collision hotspot and must not be changed while the runtime lease is active.
These hints grant no write authority. If implementation needs another owner,
path, schema, or API, stop and return the exact contract gap to PRIME.

The implementation PR for this capability must merge and its read/write
contract be reviewed before the DEMO Plan consumer cutover can activate. The
two changes remain separate capabilities and separate PRs. Human visual and
connected J1–J6 acceptance stay open.

## Design review and merge settlement

Buddy PR #859 merged at main `43c4c4daa8e1c17b22953681fe817e6881242b36`
from reviewed head `c78feb94f37f7612200e2d0962d26d0f5a1326cf` after PRIME's
exact-diff review. This accepts the bounded projection contract only. The
implementation remains BLOCKED until the AGENT-INTERACTION runtime is
accepted, Content confirms the exact committed-basis resolver, and PRIME grants
the Plan proposal/action owner an exclusive path and verification lease. No
provider, database, service, runtime, or product-state authority was granted
by #859.
