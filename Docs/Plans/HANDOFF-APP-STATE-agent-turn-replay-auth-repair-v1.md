# HANDOFF — APP-STATE: World turn replay and authorization repair

- **Status:** ACTIVE — APP-STATE code/test-only #865 repair lease; no live
  provider, operator, HTTP runtime, or production/cutover database lease.
- **Steward and accountable owner:** APP-STATE.
- **Repository:** `Drakosfire/DungeonMindBuddy`.
- **Design base:** Buddy `main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`.
- **Frozen implementation reference:** Buddy #865 head
  `b8aa42c3b4b6b5201d39b19aa62c2bef364cc94c`.
- **Implementation lane:** isolated branch
  `codex/agent-interaction-world-runtime-repair`, based on current `origin/main`
  at `2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`.
- **Topology:** serial: merged APP-STATE claim/receipt recovery (#867) → one
  auth/replay repair/rebase of #865 → current DEMO #857 canonical World
  conversation plus Plan/action projections, preserving committed-Plan-only
  Ask → separately authorized Plan/Graph auto-context. DEMO owns #857 and the
  Plan consumer.
- **PR topology:** update the existing #865 capability in one cumulative PR
  after PRIME re-anchors and dispatches it. Do not create an Ask/Graph retrieval
  PR or fold retrieval into #865.

This handoff activates only the bounded code/test repair below. It keeps #865
as one World conversation runtime capability and does not authorize live
operator activation, configured-provider calls, database migration, or live
database access. #857 retains #833's committed-Plan-only Ask behavior. Plan or
Graph automatic context is a later, separately authorized capability with
explicit context intent, same-World scope, `focus=none`, and exact per-turn Plan,
Graph, anchor, and omission provenance; it is excluded from both #865 and the
current #857 cutover.

## Re-anchor after #893

- `origin/main` is `2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`, the #893 merge.
  #893 adds only
  `Docs/Plans/HANDOFF-DEMO-plan-world-auto-context.md`; that handoff remains
  BLOCKED and grants no implementation, service, Graph, provider, database, or
  runtime lease. Its complete-provider-request budget and distinct real-runtime
  lease gate apply to that future auto-context capability, not to this #865
  repair.
- #865 remains OPEN, base `main`, head
  `b8aa42c3b4b6b5201d39b19aa62c2bef364cc94c`, with the same five cumulative
  paths listed below. Merging #893 did not update or activate #865.
- ARCHITECTURE's final #893 findings apply only to the later auto-context
  successor: current R.3 anchor reads do not expose `source_revision_id`; a
  future receipt must use verified returned-content digest, pinned Graph
  revision, artifact/span/evidence IDs, read outcome, and completeness. Do not
  invent a missing ID or broaden Graph schema. Derive admissibility from the
  authenticated principal; the current GM adapter does not authorize
  PLAYER-Plan access. If a future implementation selects vNext, its domain
  mapping must explicitly define `wildcard_axes`, `include_unscoped`,
  `audience`, and `standing`. These are future activation decisions and add no
  #865 repair path or behavior.
- Current open PR census includes #865, #887, #886, #869, #844, #826, #798,
  #781, #765, #764, #763, #761, and #760. The other open PR diffs were checked
  against the six proposed repair paths; none overlaps them. APP-STATE-tagged
  worktrees checked at this checkpoint are clean. Repeat the census at
  activation.
- Preserve the frozen #865 remote head. Its existing worktree is clean but
  local head `36db6233c8c6d6ff3d9e362248c88302a8224392` is 27 commits ahead and
  3 behind `origin/codex/agent-interaction-world-runtime-v2` at the frozen PR
  head. Do not transplant that local history. The assigned implementer must
  reconcile the PR's exact cumulative diff onto this base in the released
  isolated implementation checkout.

## Frozen #865 cumulative paths

The current #865 cumulative diff contains exactly these five paths:

```text
apps/live_control_server/models/agent_turn.py
apps/live_control_server/routes/agent.py
apps/live_control_server/services/agent_turn_service.py
tests/application_state/test_agent_conversation_postgres.py
tests/test_agent_turn_route.py
```

These are the complete frozen #865 paths. PRIME has released this repair on an
isolated branch based on current main. Preserve the existing #865 behavior and
resolve only defects needed for this repair.

## Mission and ordering contract

For a World Agent turn, make authorization, durable idempotency, and replay
correct across a Plan save, Graph change, and World conversation-pointer
rotation:

1. Apply Buddy's existing local operator/GM authorization at the start of every
   `/agent/turn` request, including `graph_request.mode == "none"`. A denied
   request must not resolve a World, open/read a receipt or database, resolve
   current Plan/Graph state, inspect provider pointers, construct a runtime, or
   call a provider. Graph `none` skips Graph resolution only; it never skips
   authorization.
2. After authorization, independently verify the submitted World authority.
   Do not reveal whether a receipt exists to a caller who is not authorized for
   that World. Then canonicalize the validated original request envelope and
   look up its durable World/idempotency-key receipt before reading the
   current conversation pointer, Plan, Graph, Hermes pointer, or provider.
3. Persist the existing versioned SHA-256 fingerprint of complete normalized
   semantic intent: verified World, message, surface and instance, submitted
   primary-work pin, client work state, Graph request and selection. The
   idempotency key is derived from World plus `turn_id`; `client_thread_id` is
   routing/display identity and is deliberately excluded from the fingerprint.
   A retry with a different client thread but the same key and semantic intent
   is the same turn; changed semantic fields conflict. Exclude current resolver
   output, active-conversation ID, current CAS revision, provider state, and
   other mutable server state. Do not persist a second raw request copy.
4. An exact matching receipt returns its original turn/result, original
   conversation identity, and frozen typed `TurnProvenance`, without
   re-resolving current Plan/Graph/pointer state or dispatching the provider.
   Do not select or construct the default runtime before reconciliation; a
   completed replay must skip runtime-factory lookup entirely. Preserve the
   existing running/failed/interrupted lifecycle behavior instead of mapping
   those states to a completed answer.
   A same-key fingerprint mismatch conflicts without dispatch. A new key with a
   stale Plan pin follows ordinary current-work validation and fails without
   relabeling it to today's revision.
5. Keep receipt provenance provider-neutral and durable: verified World,
   surface, exact accepted Plan/content basis, and typed source references that
   supported the original answer. Only successful reads may be represented as
   supporting evidence. Never replace missing historical provenance with
   current context.

## Existing APP-STATE receipt API on the re-anchored base

Buddy `main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c` already provides the
required durable mechanism; use it instead of rewriting APP-STATE persistence:

- `SubmittedTurnIntentV1` and its stored fingerprint column preserve the
  normalized semantic intent separately from typed `TurnProvenance`.
- `AgentConversationService.reconcile_turn(world_id, key, intent)` reads the
  World/key receipt before mutable pointer, Plan, Graph, or provider resolution
  and returns the immutable stored `Turn` on a fingerprint match.
- `accept_turn` performs the receipt check before the pointer lock, then checks
  again under the pointer lock before advancing the conversation revision.
- Receipts without the v1 fingerprint fail closed as
  `legacy-receipt-unverifiable`.
- The canonicalizer intentionally excludes `client_thread_id`: the existing
  runtime authority at
  `Docs/Plans/HANDOFF-AGENT-INTERACTION-world-conversation-runtime.md` defines
  it as routing-only, and the APP-STATE owning test asserts changing it does
  not alter the fingerprint. `turn_id` supplies the World-scoped idempotency
  key, so it is not duplicated in the semantic digest.

The #865 runtime must build the v1 intent from the validated original request,
independently verify the World, call `reconcile_turn` before resolving current
work, and include that same intent in the eventual `TurnSubmission`. Do not
reach into repository/unit-of-work internals, encode intent as fake work
provenance, use transcript/local storage as a receipt, or add a migration.
This checkpoint does not authorize edits to APP-STATE persistence, `types.py`,
repository/schema, migrations, Graph, UI, provider configuration, or root
configuration.

## Active narrow #865 repair lease

PRIME accepted this handoff and released the code repair. #865 remains the
single PR; its open state is transport, not authority beyond this exact lease.
The old divergent runtime worktree is preserved, and this new checkout was
created from current `origin/main`.

- **Base:** `origin/main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`.
- **PR:** update #865 in place as one cumulative PR; do not open an Ask/Graph
  retrieval PR.
- **Isolated implementation lane:**
  `codex/agent-interaction-world-runtime-repair`, based on current main. Rebuild
  the exact frozen remote #865 cumulative diff; do not transplant the old
  local `36db6233` history.
- **Maximum write allowlist:** exactly the five frozen #865 paths above plus
  `src/application_state/agent_conversation/service.py`. The existing public
  receipt APIs already satisfy this contract, so leave that sixth path
  untouched unless a concrete defect is proven and reported to PRIME before
  editing. No other source, schema, types, repository, migration, UI, consumer,
  or configuration path.
- **Verification:** fake route/ordering tests in `tests/test_agent_turn_route.py`
  and real disposable-PostgreSQL owning-persistence tests in
  `tests/application_state/test_agent_conversation_postgres.py`. No live
  provider, product runtime, private Session 23, or live Plan mutation.
- **PostgreSQL witness:** confirmed ready: PRIME-owned disposable PostgreSQL
  16.15 container `prime-app-state-pr865-pg-20261003` at `127.0.0.1:55457`,
  using `DMB_APPLICATION_STATE_TEST_DATABASE_URL` from
  `/tmp/prime-app-state-pr865-20261003.dsn`. The test fixture creates unique
  `dungeonbuddy_app_state_test_<uuid>` databases, applies the existing
  migrations, sets the runtime DSN to the generated disposable database, and
  drops it. If that designated service or private environment is unavailable,
  report the witness unrun. Never fall back to a live or cutover database.
- **Held gates:** existing operator activation, configured-provider witness,
  and live DB migration/cutover remain held. A merged PR and fake/disposable
  tests do not release those gates. Any real runtime/provider lease must be a
  separate, explicit PRIME grant.

## Required cases and evidence

### Fake route/ordering proof

Within `tests/test_agent_turn_route.py`, use call-recording sentinels for auth,
World lookup, receipt lookup, Plan/Graph resolution, conversation-pointer
access, runtime construction, and provider invocation. Prove:

- denied local authorization causes zero calls to every later boundary for
  both Graph `none` and Graph-requested turns;
- authorized `none` turns still pass authorization before all lookup/provider
  work;
- matching replay after a Plan revision change and pointer rotation returns
  the frozen receipt before current Plan/Graph/pointer resolution;
- a World verification denial never invokes `reconcile_turn`; an exact replay
  skips runtime-factory lookup as well as provider dispatch; a legacy receipt
  with a null v1 fingerprint conflicts without provider dispatch;
- changed message, Plan pin, surface/instance, or Graph intent under the same
  key conflicts before runtime/provider dispatch; changing routing-only
  `client_thread_id` alone returns the same receipt;
- two deliveries that both miss early reconciliation are resolved by the
  transactional acceptance recheck, returning the same receipt or a semantic
  conflict without a duplicate turn/provider call;
- accepted, running, completed, failed, and interrupted turns retain their
  existing lifecycle behavior; a receipt hit never turns a pending or
  retryable state into a completed answer;
- a missing receipt with a stale Plan pin fails current-state validation and
  does not dispatch; and a World verification denial never reveals a receipt
  or accesses current Plan.

Use fake World/Plan/Graph/provider adapters only. Tests must not make a private
Session 23 call, run a live operator action, or mutate a live Plan.

### Owning PostgreSQL persistence proof

Extend `tests/application_state/test_agent_conversation_postgres.py` to accept
a turn through the production conversation service boundary, then read it from
a fresh `AgentConversationService` instance after pointer/Plan test state has
changed. Assert the committed fingerprint, immutable turn result, original
conversation, typed provenance, and duplicate-key conflict/replay behavior
from PostgreSQL—not an in-memory fake. The route ordering proof remains in the
route suite; it is not a substitute for this owning persistence proof.

The repository fixture in `tests/application_state/conftest.py` creates a
unique `dungeonbuddy_app_state_test_<uuid>` database, sets the runtime DSN to
that database, applies migrations, then drops the database. Run only against
the PRIME-designated disposable PostgreSQL 16 service at `127.0.0.1:55457`,
using `DMB_APPLICATION_STATE_TEST_DATABASE_URL` from the private DSN handoff
environment. PRIME owns that service's lifecycle and credential delivery. Do
not print or commit the DSN. Do not use the fixture's local fallback or
`DUNGEONBUDDY_APPLICATION_STATE_DATABASE_URL`, World Graph DSNs, production DB
`54331`, or cutover rehearsal databases. If the designated service/private
environment is unavailable, report the owning test as unrun; do not substitute
a live database.

## Scope, gates, and dispatch

- No Plan/Graph auto-context or retrieval behavior, citations, new route/schema,
  migration, broad APP-STATE redesign, UI/Plan consumer work, provider
  configuration, or live activation.
- No writes outside the exact six-path maximum lease above. Leave the existing
  APP-STATE service implementation untouched unless a concrete defect is
  proven and reported to PRIME before editing.
- Keep operator authorization, configured-provider acceptance, and live DB
  migration/cutover holds open. Fake route tests and the designated disposable
  PostgreSQL witness are code-level evidence only; they do not lift those
  holds.
- Implementation completion remains one cumulative #865 PR, exact
  `origin/main` base/head and diff review, boundary tests, and truthful report
  of inherited failures or missing witnesses. Merge remains separate
  authority.
