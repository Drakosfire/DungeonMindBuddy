# HANDOFF — DEMO: cut over Plan conversation to World history

**Status:** BLOCKED — design only; AGENT-INTERACTION runtime, Plan-owned action projections, and a separate APP-STATE exact-basis Ask projection are predecessors; no Plan consumer implementation, provider, database, service, or runtime lease.

**Steward:** DEMO task `01a0efc8-f3a8-7be2-a556-33eb338338e8`

**Repository:** `Drakosfire/DungeonMindBuddy`

**Design base:** Buddy `main@c0c1247ecc4fdb76553ba81d62abfeaf9f156e2c`.

**Current amendment base:** Buddy `main@e4d02ca03003877064f7a323a20b8230325d11cf`.

**Topology:** serial by default — APP-STATE World conversation storage/receipts (#822/#827 complete) → AGENT-INTERACTION production runtime adoption (#865) → separate Plan-owned action-dialogue projection capability (#859) → separate APP-STATE exact-basis Ask projection → this DEMO Plan consumer cutover. PRIME owns activation and each exact implementation lease. Session 29 Graph retrieval and Play adoption remain later, separately bounded work.

**Future implementation PR title:** `DEMO: cut over Plan conversation to World history`.

## One user-visible capability

From a saved Plan in a verified managed World, the operator continues the
World's canonical Agent conversation. Plan Ask turns have durable, exact
committed-content provenance and remain visible after reload, Plan switching,
or returning from another World surface. Each new turn resolves the selected
World, saved Plan, committed WorkRevision, and content digest again. A Plan
switch or committed content change starts the provider segment required by the
accepted runtime contract. A delayed result remains attached to its originating
turn and Plan basis.

This cutover preserves current Plan behavior: Ask sends the question and exact
committed Plan content through the configured provider, never the mounted editor
draft; Compose/Revise still uses the mounted draft and captured selection and
produces a reviewable Plan-owned proposal; Apply remains an editor-draft action,
and ordinary Save remains the commit boundary. Ask explicitly requests
`graph_request.mode="none"`. This slice does not add Graph retrieval,
citations, proposal auto-apply, a new conversation engine, or J1–J6 acceptance.

## Current evidence and boundary

- Buddy #822/#827 completed APP-STATE World conversation storage, durable
  ordered turn receipts, typed per-turn provenance, and idempotency. The
  accepted contract has one server-generated conversation per verified World;
  browser keys and client thread IDs are not conversation authority.
- The current APP-STATE `AgentConversationService.list_turns` read filters by
  World, conversation, and sequence paging only; it does not filter by exact
  Plan/basis. PRIME assigned a separate APP-STATE eligible-Ask projection that
  must filter completed visible Ask pairs by the full server-resolved basis
  before limiting. It follows #865 and precedes this cutover; it is excluded
  from #865 and is not an active implementation lease here.
- The AGENT-INTERACTION runtime adoption (#865) is an immediate serial
  predecessor and is currently blocked pending direct operator authorization.
  Its production route, service, assembler, runtime, models, and tests remain
  outside this DEMO handoff's write lease. The consumer must use the exact
  accepted runtime API; this amendment grants no runtime implementation
  authority.
- Buddy #805 introduced the saved managed-World Plan Ask surface. Buddy #833
  moved Ask to exact committed Plan content: the server pins the WorkObject
  revision, WorkRevision ID/number, and SHA-256, reads current World-owned Plan
  content atomically, excludes the editor draft, returns a compact receipt,
  and requests no Graph. Its configured-provider witness proved one saved
  content turn and reload only; it did not prove World-wide conversation
  continuity.
- Buddy #828/#829 own the current Compose/Revise/Apply path. The Plan editor
  review and ordinary Save remain Plan/Content-owned. Buddy #847 corrected a
  witness assertion; it did not move proposal/action state into conversation
  storage.
- At this design base, `WorldPlanAgentConversation.tsx` stores Plan threads in
  browser `localStorage`. Compose/Revise builds `conversation_history` from up
  to six `currentThread.turns`, including `plan_edit` entries, and sends that
  client-supplied array to the proposal endpoint. The same browser turn model
  can contain proposal replacement bytes and an `applied` flag. Those action
  records are not eligible APP-STATE conversation turns and the client array
  cannot be authoritative context after cutover.
- PRIME's contract ruling preserves the existing six-item Compose/Revise
  dialogue behavior. A separate Plan-owned typed visible action-dialogue read/
  projection must expose only the instruction and user-visible assistant
  summary, with exact World/Plan/committed-basis provenance and stable order.
  It excludes proposal bytes, Apply/Save receipts, and hidden provider state.
  The consumer must combine this projection with eligible APP-STATE Ask turns;
  it may not silently narrow to Ask-only.

The existing Plan Ask/edit flows remain the user-visible surfaces. A successful
cutover uses one World conversation identity and visible transcript, not a
Plan-private provider history. Each visible turn retains its original surface
and exact historical work/content basis. The runtime alone decides bounded
provider replay under the accepted segment rules; visible World history is not
permission to reuse unrelated turns as current Plan context.

## Ownership and request contract

- **APP-STATE** owns canonical conversation identity/lifecycle, visible
  user/assistant turns, ordering, idempotency receipts, typed historical
  provenance, and its stable-key legacy import contract.
- **AGENT-INTERACTION** owns production turn orchestration, fresh World/Plan
  resolution, bounded provider replay, exact provider-segment selection, and
  completion/retry correlation.
- **DEMO** owns the Plan UI cutover, invoking the approved legacy importer,
  presentation of visible historical turns, and the configured-provider Plan
  acceptance witness.
- **Plan/Content** owns mounted drafts, selection/caret snapshots, Compose/
  Revise proposals, replacement Markdown, review state, Apply-to-editor state,
  ordinary Save, and committed-work receipts. None is a generic conversation
  turn or APP-STATE action receipt.

For every new Plan Ask turn, the server independently verifies the managed
World and saved Plan, resolves the exact committed content basis, and rejects
foreign, removed, unavailable, stale, or contradictory bindings before
provider work. The basis includes the World ID, document ID, object revision,
WorkRevision ID and number, and content SHA-256. The question and this exact
committed Plan content go to the configured provider under the existing #833
disclosure. Editor draft bytes are excluded even when the UI reports
`saved_dirty`. Keep `graph_request.mode="none"` and no graph selection.

Use the server-assigned APP-STATE conversation ID as canonical identity. A
client thread ID may be retained only as a request/import correlation value if
the merged runtime contract still requires it; it cannot select a conversation
or provider segment. On Plan document or committed basis change, the runtime
uses a fresh segment bound to the verified World, Plan surface/instance,
document, and exact basis. It must not replay hidden provider state or treat
older Plan content as the current basis. Use the exact landed runtime request
and response schema; this design does not freeze a new public API.

The visible transcript may include turns from other surfaces in the same World
conversation. Render their historical provenance clearly. Compose/Revise must
not inherit the whole World transcript as context. Its bounded context may
contain only eligible visible turns whose server-resolved World, Plan document,
and committed content basis/segment exactly match the current Plan action.
Enforce the six-turn cap at the authoritative server boundary, not by trusting
client `conversation_history`.

### Compose/Revise context requirement

Preserve the existing six-item dialogue behavior. Before this consumer can
activate, both source capabilities must be delivered under separate reviewed
PRs:

- The Plan-owned capability in
  [HANDOFF-DEMO-plan-action-dialogue-projection.md](HANDOFF-DEMO-plan-action-dialogue-projection.md)
  supplies two reads. Its status/recovery projection exposes bounded truthful
  statuses for the UI. Its completed-context projection filters to completed
  instruction/summary pairs on the exact World, Plan document, object revision,
  WorkRevision ID/number, and content SHA-256 **before** applying its own
  maximum-six eligible-pair limit. Newer unresolved actions cannot crowd older
  eligible pairs out of model context.
- APP-STATE supplies a separate eligible-Ask projection, outside #865. It
  returns only completed visible Ask pairs matching that same full
  server-resolved basis, filtered before its limit. Existing
  `AgentConversationService.list_turns` is chronological paging and does not
  provide this exact-basis behavior.

The authoritative Plan proposal boundary obtains both context projections,
merges their eligible pairs in stable accepted-time/sequence order, and applies
the total six-turn cap after the merge. The status/recovery projection is not a
model-context source. No client `conversation_history` can add, remove, or
reorder authoritative context. If either owner projection needs another API,
storage, or runtime capability, that owner delivers it under its own reviewed
capability/PR before this consumer cutover; do not expand this consumer lease.

When the mounted draft is dirty, the Plan action record keeps a separate
request-input witness (dirty/clean status and server-computed draft digest,
plus selection identity/range or digest when it affected the proposal); it
must not label that draft as committed Plan content or expose its bytes. The
projection excludes replacement Markdown, proposal bytes, Apply/Save receipts,
and provider state. Existing `plan_edit` localStorage rows lack exact
committed-basis provenance and are not safe input by themselves.

For each submitted Ask, preserve the original idempotency key and normalized
intent, including its originating Plan/basis request snapshot, through an
uncertain response and reload. Never silently create a fresh key for an
automatic retry; reusing the key with changed intent conflicts. APP-STATE PR
#867 guarantees durable turn identity and honest recovery, but explicitly does
not promise exactly-once provider invocation across crashes:

- Replaying a completed durable receipt returns the original result without a
  provider dispatch.
- Replaying while a claim is still valid does not start a second provider
  dispatch; return or resume the pending state according to the accepted
  runtime contract.
- Retrying persistence after the provider output is known reuses that output
  and does not dispatch the provider again.
- If the provider outcome was lost or remains indeterminate, or an expired /
  fenced claim is reclaimed, follow the accepted runtime recovery contract.
  Provider re-dispatch may occur and must be reported honestly; never describe
  it as impossible or exactly-once. A new key is reserved for a deliberate new
  user intent, not an automatic retry.

If the World or committed Plan basis changes while the request is pending,
keep its eventual response tied to the originating turn and out of the newly
selected context. Compose/Revise retains its current user-entered instruction,
mounted draft, selection/caret, proposal validation, review, Apply-to-editor,
and ordinary Save behavior.

## Legacy Plan history cutover

The consumer may invoke the APP-STATE legacy importer only for visible Ask
turns with complete, unambiguous per-turn evidence: stored `ownerId` exactly
matches the independently verified World, and the complete `contentBasis`
matches that turn's saved Plan document and committed WorkRevision/revision/hash
basis. Preserve visible order, source-turn identity, and historical
provenance. Import is idempotent by the accepted stable source-turn key.

Skip or quarantine missing, malformed, ambiguous, mismatched, unbound, or
legacy campaign rows. A browser namespace, currently selected route, Plan
name, local thread ID, provider pointer, or Hermes handle cannot establish
ownership. Import no `plan_edit` question/answer rows, proposal replacement
Markdown, `applied` flag, draft text, review state, traces, provider internals,
or action/Apply/Save receipt. Keep local bytes until APP-STATE confirms the
exact import; after confirmation use the server transcript as authority and do
not dual-write or silently fall back to localStorage when the service is
unavailable.

## Failure cases to preserve

- Foreign, removed, unavailable, malformed, or changed World/Plan/basis fails
  closed before provider dispatch. A pending save or unresolved WorkRevision
  cannot be presented as committed.
- Ask never includes mounted draft text, even when dirty. A changed committed
  basis is shown truthfully and uses a fresh provider segment.
- Plan A → Plan B and back never crosses the exact Plan context filter. The
  World transcript may remain visible, with provenance, but unrelated turns
  are not fed into Plan Ask replay or Compose/Revise context.
- Duplicate import/retry returns the original durable receipt; conflicting
  stable source keys do not duplicate or relabel a turn. Incomplete history is
  skipped/quarantined without deleting local bytes.
- A late Ask result remains on its originating durable turn and frozen Plan
  basis. It cannot populate a newly selected Plan's current response or
  proposal review.
- A deferred Ask response after a managed-World switch or same-Plan
  committed-basis advance remains tied to the originating turn and never
  enters the new World/basis context or current response.
- An uncertain Ask retry after reload retains the original idempotency key
  and normalized intent; changed intent with that key conflicts. Completed
  receipt replay, a still-valid pending claim, and persistence retry with known
  output do not dispatch again. Lost/indeterminate provider outcome or
  expired/fenced claim recovery follows APP-STATE #867's at-least-once contract
  and may re-dispatch; report that possibility honestly rather than promising
  exactly-once invocation.
- APP-STATE/runtime unavailability produces an explicit error. No browser
  localStorage fallback can create a second authority or an unreceipted turn.
- Compose/Revise still requires review before Apply; Apply changes only the
  editor draft, and ordinary Save is still required to commit.
- Graph remains `not_requested`; no citation, retrieval, graph-grounding, or
  J3 claim appears.

## Future owning-boundary witness

After runtime merge and a new exact PRIME lease, exercise the real Plan page,
Ask plugin, Agent transport, and approved proposal boundary against the landed
runtime/API. Use isolated tests/fakes for UI cases and only the provider/DB
fixtures explicitly named by that lease. Prove:

1. Two Plan Ask turns use the server World conversation and stable durable
   receipts; each turn records exact Plan document and committed content
   basis. Reload restores visible turns from APP-STATE, not localStorage.
2. Index/Plan or another already-supported surface can observe the same
   World-global visible history with per-turn provenance, while Plan Ask
   replay starts a fresh provider segment when Plan document or committed
   basis changes.
3. Plan A → B → A preserves only exact historical provenance and never sends
   B's context as A's current basis. Deferred Ask responses after a managed-
   World switch or same-Plan committed-basis advance remain attached to their
   originating turns and out of the newly selected context.
4. Legacy Ask import accepts only complete matching `ownerId` plus
   `contentBasis`, preserves order, is idempotent, quarantines invalid rows,
   and leaves local bytes until confirmed. Exercise the actual importer path
   through its owner boundary and prove retry returns the original import
   receipt, invalid rows are quarantined/skipped, and local bytes are retained
   until confirmed; documentation or a client-only filtering test is not this
   witness. `plan_edit`, proposal payload, editor draft, trace, and provider
   state are not imported.
5. Compose/Revise tests combine eligible APP-STATE Ask turns and the Plan-owned
   completed-context projection in stable order, filter each source before its
   per-source limit, and enforce the total six-item cap after merge at the
   authoritative boundary. Six newer unresolved actions remain visible in the
   separate status/recovery read without hiding older completed context.
6. Ask retry evidence preserves the same key and original normalized intent
   across uncertain response and reload, and conflicts if that key is reused
   with changed intent. Distinguish (a) completed durable receipt replay, (b)
   a still-valid pending claim, and (c) persistence retry with known provider
   output, each of which avoids another provider dispatch, from lost or
   indeterminate provider output and expired/fenced claim recovery. For the
   latter, exercise the accepted APP-STATE #867 recovery behavior and report
   possible provider re-dispatch; do not assert exactly-once invocation or
   silently mint a new key. World-switch and basis-advance deferred responses
   remain fenced to their originating turn.
7. Preserve the #828/#829 proposal, review, Apply-to-draft, ordinary Save, and
   stale-thread fences. Service/runtime failures, protocol mismatch, pending
   save, and changed Plan/World/basis fail safely without duplicate durable
   turn records, mislabeled results, or cross-Plan results.

A configured-provider witness is required for the Plan consumer acceptance
only under PRIME's exact provider/model/spend authorization. No production
database, shared service, provider, port, real Graph, or product state is
leased by this BLOCKED design. Mocked tests alone do not establish a live
provider result or operator acceptance.

## Activation gates and future lease

This handoff stays BLOCKED until PRIME:

1. Accepts the exact runtime PR/base/head and its owning-boundary evidence.
2. Completes the separate Plan-owned action-dialogue projection capability
   and its own reviewed PR, with status/recovery and completed-context reads;
   completed exact-basis pairs are filtered before the context limit.
3. Completes the separate APP-STATE exact-basis Ask projection after #865 and
   before this consumer, with completed visible Ask pairs filtered by full
   server-resolved basis before limiting. This capability is not part of #865.
   Do not activate this consumer while either source projection is missing.
4. Re-anchors current Buddy main and inspects open PRs and active leases for
   collisions. Do not edit AGENT-INTERACTION routes/services/models/tests
   without a separate exact owner lease or explicit transfer.
5. Pins one exact exclusive Plan UI/consumer allowlist, proposal boundary,
   isolated test/provider/database/runtime fixtures, verification evidence,
   and one serial PR. Candidate source files are investigation hints only and
   are not an implementation lease.

The future consumer must stop and return to PRIME before editing any path or
contract outside the pinned lease. No Plan implementation, runtime/service,
provider, database, Graph, port, shared external state, or product mutation is
authorized by this design. Visual acceptance and the connected J1–J6 journey
remain separate open gates.

## Design review and merge settlement

Buddy PR #857 merged at main `41fe2944468327da852a987685992fc50f91f059`
from reviewed head `de08a3cc2f24406d1440b771f047ba0b8398a6e8` after PRIME's
exact-diff review. This accepts the BLOCKED design only. The
AGENT-INTERACTION runtime, separate Plan action-dialogue projection, and
separate APP-STATE exact-basis Ask projection remain predecessors. No Plan
consumer implementation/provider/database lease is active.
