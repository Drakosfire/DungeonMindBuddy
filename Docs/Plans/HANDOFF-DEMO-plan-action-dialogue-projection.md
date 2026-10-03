# HANDOFF — DEMO: project typed Plan action dialogue

**Status:** PREPARED — design-only amendment to merged PR #859. The AGENT-INTERACTION runtime predecessor, PR #865, is accepted and merged at `1c0320d18c53037308cd7412719fb3e2f0610d99`; this does not activate Plan-action implementation. Implementation remains BLOCKED pending APP-STATE's explicit migration review and PRIME's exact lease below. No lease for this Plan-action capability is active.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Repository:** `Drakosfire/DungeonMindBuddy`

**Preparation base:** Buddy `main@327bdb5a899178eef2c16f3e9198219eb8e79773` (PR #863 merge).

**Amendment base:** Buddy `main@1c0320d18c53037308cd7412719fb3e2f0610d99` (PR #865 merge).

**Accepted design:** PR #859 merged at `43c4c4daa8e1c17b22953681fe817e6881242b36` from reviewed head `c78feb94f37f7612200e2d0962d26d0f5a1326cf`. This amendment narrows the action-record scope and records the shared-migration ownership ruling; it does not activate implementation.

**Topology:** serial — APP-STATE World conversation storage/receipts (#822/#827 complete) → AGENT-INTERACTION production runtime adoption (#865) → this Plan-owned action-dialogue projection capability (#859) → separate APP-STATE exact-basis Ask projection → DEMO Plan World-conversation cutover in [HANDOFF-DEMO-plan-world-conversation-cutover.md](HANDOFF-DEMO-plan-world-conversation-cutover.md). The two projections are separate capabilities and PRs, not an expansion of either implementation lease.

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
- Buddy PR #865 merged at `1c0320d18c53037308cd7412719fb3e2f0610d99` from
  reviewed head `097107324e0be5f5e7aa45e9633f70c09c4794e5`. Its runtime
  acceptance does not establish a live consumer/provider/operator witness or
  J1–J6 acceptance, and does not grant this Plan-action implementation lease.
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

The existing Content read selects one coherent committed snapshot as the
action's basis-selection point. Persist that exact basis tuple with the action
before provider dispatch. If the Plan advances after this read, including
before the action row is inserted, keep the action pinned to the captured
snapshot; do not reject it or rebind it to the new head. The action remains
historical and is excluded from projections for a newer Plan basis. Apply
retains its captured-basis guard, and ordinary Save retains its existing
expected-object-revision CAS, which rejects stale changes. No shared unit of
work, current-at-insert check, Content-specific transaction, or new Content
resolver is required.

Before provider dispatch, reserve a durable Plan-owned action row in a
transaction. Each row contains:

- a server-assigned durable action ID;
- the client-generated idempotency key for this user intent, which the client
  must reuse with an identical request and basis on uncertain network retry;
- a canonical request fingerprint covering the verified basis and all
  generation inputs whose identity affects the result;
- a Plan-owned dispatch owner/token, monotonically advancing fence/version, and
  database-time lease expiry for the pending reservation;
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
same-fingerprint retries return or reconcile that row but never dispatch the
provider again. Only the request that atomically creates the reservation may
dispatch, using the recorded owner/token and fence; every idempotency hit is a
read/reconciliation path. Same-key reuse with a changed instruction, basis,
draft witness, or other fingerprinted input conflicts. Stale or invalid basis
fails before provider work. Persist the truthful state as `pending`,
`completed`, `failed`, or `indeterminate`. A completed row includes the safe
assistant summary; other states do not.

Provider dispatch and database commit cannot be one exactly-once transaction.
While a `pending` reservation's database-time lease is live, same-key retries
and status reads return `pending`. On a same-key retry or status read after
expiry, lock the row and atomically transition it to `indeterminate`, advancing
its fence/version exactly once. No sweeper or background worker is used. An
expired reservation is never reclaimed or redispatched automatically; an
unknown provider outcome requires a fresh explicit user intent. Terminal
success and definite-failure writes are compare-and-set operations that require
the row still be `pending`, the same dispatch token and fence, and an unexpired
lease according to database time. A late worker that loses this check cannot
write a terminal state or expose a completed summary. If its failed compare-
and-set observes an expired pending row, it uses the same atomic expiry
reconciliation and returns `indeterminate`; if another caller already
reconciled the row, it returns that state. A persistence failure after
dispatch must not fabricate a completed action. Never silently fall back to
client history as authority.

Before activation, inspect the current provider request deadline and its
configuration, then prove it is bounded and strictly shorter than the selected
database lease duration. Do not invent a deadline or lease duration. If the
provider deadline cannot be established or is not shorter, this remains an
activation gate. Provider correlation does not authorize automatic reclaim or
redispatch in this capability.

The record is a Plan-owned action dialogue, not an APP-STATE generic Agent
turn, tool result, or proposal receipt. Its visible dialogue text is the
instruction and, only when completed, the assistant summary. Action type,
basis references, and status are safe typed metadata; input witnesses remain
private filtering metadata.

## Read and ordering contract

The Plan owner provides two distinct authoritative server-side projections,
both scoped by the server-verified World, Plan document, and complete committed
basis:

1. The **status/recovery projection** returns a bounded, stably ordered set of
   matching action records with truthful `pending`, `completed`, `failed`, and
   `indeterminate` status for the UI. A completed record pairs one user
   instruction with its assistant summary; other states have no fabricated
   assistant response. This read serves status and recovery display only. The
   proposed route is `GET /api/live/world-plan-edit/actions`; it resolves the
   World, Plan, and committed basis server-side and reconciles expired pending
   rows using the atomic rule above.
2. The **completed-context projection** first filters to `status=completed`, a
   safe assistant summary, and the exact World ID, Plan document ID, object
   revision, WorkRevision ID and number, and content SHA-256; only then does it
   apply its maximum-six eligible-pair limit. It returns the instruction and
   assistant summary with safe typed metadata and stable ordering. Newer
   pending, failed, or indeterminate actions never consume this context limit
   or hide older eligible completed pairs.

The later Plan consumer merges the completed-context projection with the
separate APP-STATE exact-basis Ask projection, orders both sources stably, and
applies the overall six-turn cap after that merge. The status/recovery read is
not a context source. The consumer never treats client `conversation_history`
as authoritative.

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
4. Same-key/same-fingerprint retries do not duplicate rows or dispatch again;
   reuse of the same idempotency key with a changed fingerprint conflicts. A
   live `pending` row remains pending. An expired pending row becomes
   `indeterminate` atomically on retry/status read, advances its fence exactly
   once under concurrency, and is never automatically reclaimed or
   redispatched. A definite failure or indeterminate result remains visible
   and requires a deliberate new user intent. Projection persistence failure
   retains explicit truthful state and does not fabricate dialogue.
5. Projection queries reject another World, Plan, or committed basis; preserve
   stable order; return at most six action turns; and isolate Plan A from B.
6. A late response remains bound to the originating action ID and basis after
   Plan/World switch. Existing proposal review, Apply-to-editor, and ordinary
   Save behavior still pass.
7. Six newer matching actions in `pending`, `failed`, or `indeterminate`
   states remain visible through the status/recovery projection but do not
   hide older completed exact-basis pairs from the completed-context
   projection; filtering to completed exact-basis pairs happens before its
   six-item limit.
8. Concurrent expiry reads transition one pending row to `indeterminate` and
   advance its fence/version once; a live-lease read leaves it pending. A stale
   completion or definite-failure write after expiry reconciles it to
   `indeterminate` and cannot expose a summary. A terminal write with the
   matching token/fence and an unexpired lease can win only once.
9. Provider invocation is strictly bounded by the observed configured request
   deadline, which is shorter than the chosen lease duration.

Use an isolated fake provider/runtime and only a disposable persistence
fixture explicitly named by PRIME's implementation lease. No production
database, shared service, port, or live product state is leased by this
PREPARED design. A bounded configured-provider acceptance witness, if later
useful, is covered by the standing DEMO authorization; it must use the
configured provider/model, finite retries, and honest unknown cost receipts.

## Activation gates and future lease

This handoff is PREPARED and stays BLOCKED until PRIME:

1. ~~Accepts the AGENT-INTERACTION runtime PR/base/head and its
   owning-boundary evidence.~~ **Satisfied:** PR #865 merged at
   `1c0320d18c53037308cd7412719fb3e2f0610d99` from reviewed head
   `097107324e0be5f5e7aa45e9633f70c09c4794e5`.
2. Uses the existing Content read
   `get_committed_playable_revision(document_id, kind="plan",
   expected_world_id=...)` to select the coherent committed-basis snapshot
   described above. The Plan action persists that captured tuple. No new
   Content resolver, shared unit of work, or current-at-insert validation is
   required.
3. Obtains APP-STATE's explicit review/authorization of the Plan-owned
   migration using the shared Alembic authority, including shared migration
   and unit-of-work integration boundaries.
4. Proves the current provider request deadline is strictly shorter than the
   proposed database lease; select no duration until this is evidenced.
5. Re-anchors Buddy main, inspects open PRs/active leases, and grants an exact
   exclusive file/path allowlist, disposable persistence/provider fixtures,
   verification boundary, and one serial implementation PR.

The following is the proposed exact implementation file set for PRIME's future
lease, not current write authority:

- `apps/live_control_server/models/plan_document_edit_proposal.py`
- `apps/live_control_server/routes/live.py`, limited to
  `post_world_plan_document_edit_proposal` for
  `POST /api/live/world-plan-edit/propose` and the new status handler for
  `GET /api/live/world-plan-edit/actions`; leave campaign proposal handlers
  untouched.
- `apps/live_control_server/services/plan_document_edit_proposal.py`, limited
  to the World-owned proposal/action flow; leave the legacy campaign flow
  untouched.
- `src/application_state/plan_action_dialogue/__init__.py`
- `src/application_state/plan_action_dialogue/types.py`
- `src/application_state/plan_action_dialogue/repository.py`
- `src/application_state/plan_action_dialogue/service.py`
- `src/application_state/migrations/versions/20261003_0014_plan_action_dialogue.py`,
  only if the migration head is still `20261002_0013` at activation.
- `apps/live-control-ui/src/api/liveApi.ts`
- `apps/live-control-ui/src/api/liveApi.test.ts`
- `apps/live-control-ui/src/api/types.ts`
- `apps/live-control-ui/src/planSurface/components/WorldPlanAgentConversation.tsx`
- `apps/live-control-ui/src/planSurface/WorldPlanAgentReviewedEdit.integration.test.tsx`
- `tests/test_world_plan_edit_proposal.py`
- `tests/application_state/test_plan_action_dialogue_postgres.py`

Use the existing unique-database `application_state_dsn` fixture with the
PRIME-assigned disposable PostgreSQL service; do not edit
`tests/application_state/conftest.py`. This proposed set excludes shared
`unit_of_work.py`, migration runner/environment, global fixtures, configuration,
lockfiles, roadmap, provider/runtime infrastructure, and unrelated routes. APP
must review how the new Plan-owned store is wired through its shared unit of
work; if implementation requires any excluded path or another contract, stop
and return the exact expansion to PRIME before editing. The above paths are
not an allowlist or write authority until PRIME grants the exclusive lease.

The implementation PR for this capability must merge and its read/write
contract be reviewed before the DEMO Plan consumer cutover can activate. The
two changes remain separate capabilities and separate PRs. Human visual and
connected J1–J6 acceptance stay open.

## Design review and merge settlement

Buddy PR #859 merged at main `43c4c4daa8e1c17b22953681fe817e6881242b36`
from reviewed head `c78feb94f37f7612200e2d0962d26d0f5a1326cf` after PRIME's
exact-diff review. It accepts this bounded capability's design only. The
2026-10-03 amendment records PRIME's accepted Plan-owned expiry/fence rule,
ARCHITECTURE's review of that state machine, and the exact proposed
implementation package and tests. PR #865 is accepted and merged at
`1c0320d18c53037308cd7412719fb3e2f0610d99`; it does not provide live
consumer/provider/operator evidence or J1–J6 acceptance. APP-STATE's explicit
review of the Plan-owned migration and shared unit-of-work boundary and PRIME's
exclusive implementation lease remain open. The existing Content snapshot
read selects each action's committed basis; no separate Content resolver or
Content-specific transaction is required. No provider, database, service,
runtime, or product-state authority is granted by this amendment.
