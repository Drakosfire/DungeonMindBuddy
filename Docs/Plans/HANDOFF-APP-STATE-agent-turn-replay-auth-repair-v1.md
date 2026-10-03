# HANDOFF — APP-STATE: World turn replay and authorization repair

- **Status:** COMPLETE — Buddy PR #865 merged at
  `1c0320d18c53037308cd7412719fb3e2f0610d99` from reviewed head
  `097107324e0be5f5e7aa45e9633f70c09c4794e5`. Its code/test lease is released;
  later consumer/provider/operator activation remains separately held.
- **Steward and accountable owner:** APP-STATE.
- **Repository:** `Drakosfire/DungeonMindBuddy`.
- **Design base:** Buddy `main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`.
- **Reviewed implementation head:** Buddy #865 `097107324e0be5f5e7aa45e9633f70c09c4794e5`.
- **Merge base:** `main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`.
- **Topology:** serial code path completed: APP-STATE claim/receipt recovery
  (#867) → AGENT-INTERACTION World runtime (#865) → DEMO Plan action-dialogue
  design (#859) → later Plan consumer/cutover. The later stages remain separate.
- **PR topology:** the existing #865 was updated in place and merged. No
  Ask/Graph retrieval PR was created or folded into #865.

This handoff records the completed bounded code/test repair. It kept #865 as
one World conversation runtime capability and did not authorize live operator
activation, configured-provider calls, database migration, or live database
access. #857 retains #833's committed-Plan-only Ask behavior. Plan or Graph
automatic context is a later, separately authorized capability with explicit
context intent, same-World scope, `focus=none`, and exact per-turn Plan, Graph,
anchor, and omission provenance; it was excluded from #865 and the current #857
cutover.

## Historical re-anchor before #865 repair

This records the 2026-10-03 pre-merge activation checkpoint. Its frozen-head
and open-PR statements are superseded by the merge settlement at the end of
this handoff.

- At this checkpoint, `origin/main` was
  `2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`, the #893 merge.
  #893 adds only
  `Docs/Plans/HANDOFF-DEMO-plan-world-auto-context.md`; that handoff remains
  BLOCKED and grants no implementation, service, Graph, provider, database, or
  runtime lease. Its complete-provider-request budget and distinct real-runtime
  lease gate apply to that future auto-context capability, not to this #865
  repair.
- At that checkpoint, #865 was OPEN, base `main`, head
  `b8aa42c3b4b6b5201d39b19aa62c2bef364cc94c`, with the five cumulative paths
  listed below. Merging #893 did not update or activate #865.
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

## Historical narrow #865 repair lease

At dispatch, PRIME accepted this handoff and released the code repair. #865 was
the single PR; its open state was transport, not authority beyond the exact
lease. The old divergent runtime worktree remains preserved, and the repair
checkout was created from that checkpoint's `origin/main`.

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

## Scope, gates, and dispatch at implementation start

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

## Settlement — Buddy #865 merge

The bounded APP-STATE repair is complete. Buddy PR #865 merged on 2026-10-03
at `1c0320d18c53037308cd7412719fb3e2f0610d99` from reviewed head
`097107324e0be5f5e7aa45e9633f70c09c4794e5`, based on
`main@2e1a8184ac63ad3bfdd3af428c4ea6df907a7c0c`. PRIME reported 58 combined
route, PostgreSQL, Agent-service, and auth tests passing in 41.43 seconds,
plus the HTTP cardinality case passing in 8.42 seconds. ARCH's conditional
code-acceptance holds were resolved. The original five-path lease and its
explicitly authorized test-only `tests/test_agent_graph_auth.py` addition are
released. These code checks do not activate a configured provider, live World,
production database, consumer cutover, or operator acceptance.

The merged runtime contract and later held activation gates are recorded in
[the AGENT-INTERACTION runtime handoff](HANDOFF-AGENT-INTERACTION-world-conversation-runtime.md).

## Next contract checkpoint — APP-STATE review of #859

Buddy PR #859 merged the design-only Plan action-dialogue projection at
`43c4c4daa8e1c17b22953681fe817e6881242b36`. Its implementation remains
blocked. The current contract is
[`HANDOFF-DEMO-plan-action-dialogue-projection.md`](HANDOFF-DEMO-plan-action-dialogue-projection.md).

APP-STATE's preliminary boundary review finds the ownership split compatible
with this repository: Plan/DEMO owns action semantics, lifecycle, idempotency,
repository/service, and safe projections; APP-STATE owns only the shared
Alembic runner, unit-of-work, DSN, and database infrastructure. The design
keeps these rows outside `agent.turn` and Content's committed-revision tables.
The current merged `main@1c0320d1` migration chain has one head,
`20261002_0013`, descending from `20261002_0012`. The inspected open PR paths
do not overlap the Alembic versions directory.

This review does not grant an implementation lease. The #859 handoff did not
pin an exact migration filename, schema signature, or exclusive path allowlist;
APP-STATE proposes the following exact persistence paths for PRIME to pin in a
future ACTIVE handoff:

```text
src/application_state/plan_action_dialogue/__init__.py
src/application_state/plan_action_dialogue/types.py
src/application_state/plan_action_dialogue/repository.py
src/application_state/plan_action_dialogue/service.py
src/application_state/migrations/versions/20261003_0014_plan_action_dialogue.py
tests/application_state/test_plan_action_dialogue_postgres.py
```

After PRIME's design amendment, APP-STATE accepts these as the proposed exact
APP-owned persistence paths, subject to PRIME pinning them in an ACTIVE
handoff. The migration is additive and linear, with `down_revision =
"20261002_0013"`. Do not edit `migrations/env.py`, the shared runner, DSN,
Content tables/APIs, or `agent.*`. PRIME must re-anchor and pin these paths,
the Plan route/model/UI correlation paths, verification fixture, and one serial
PR before any implementation begins.

### Proposed minimal persistence contract for review

Use one Plan-owned `plan.action_dialogue` table. The minimum durable fields are:

- `action_id UUID` primary key; `world_id TEXT`; `plan_document_id UUID`;
  stable client `idempotency_key UUID`; canonical `request_fingerprint` as a
  checked SHA-256; server `sequence BIGINT` and `accepted_at TIMESTAMPTZ`;
- frozen basis: `object_revision`, `work_revision_id UUID`, `revision_n`, and
  `content_sha256`; all required, server-resolved, and kept with the action;
- request witness: action type, instruction, draft-matches-basis boolean,
  draft SHA-256, and nullable selection kind plus selected-text digest or
  stable range witness. Never store submitted draft bytes or selected text;
- lifecycle: `status` constrained to `pending|completed|failed|indeterminate`,
  nullable active `dispatch_token UUID`, monotonic `fence BIGINT`,
  database-evaluated `lease_expires_at TIMESTAMPTZ`, `updated_at`, nullable
  `failure_code`, and nullable `assistant_summary`/`completed_at`. A nullable
  `dispatch_started_at TIMESTAMPTZ` may record observability, but it does not
  permit reclaim or redispatch after expiry.

Enforce unique `(world_id, idempotency_key)` so reusing a key for another Plan
or basis is detected; compare the full fingerprint and return the existing row
only for an exact match. Enforce unique `(world_id, plan_document_id,
sequence)` ordering and positive sequence/fence values. Constrain `pending`
rows to have a dispatch token and lease expiry; terminal rows revoke/null the
active dispatch token. Require a completed row to have a nonempty safe summary
and `completed_at`; non-completed rows have neither. Require `failure_code`
for `failed`/`indeterminate` and keep it null for `pending`/`completed`. Add
indexes for exact-basis completed projection/order and bounded status reads.
Do not add foreign ownership or transcript fields to `agent.*` or `content.*`.

Amended process-death contract: reserve a `pending` action and persist its
dispatch token, fence, and bounded lease expiry before provider dispatch. Use
database time for expiry comparisons and updates. A same-key/same-fingerprint
retry reads the existing action and never dispatches again; changed
fingerprints conflict. A live `pending` action remains `pending`. On a read or
attempted transition, lazily lock and reconcile an expired `pending` row once
to `indeterminate`, monotonically advance its fence, and return the resulting
state. Do not add a sweeper or background worker, reclaim the reservation, or
automatically redispatch. Completion and definite-failure writes are
compare-and-set operations requiring `status = pending`, the same dispatch
token and fence, and an unexpired lease according to database time. Expiry
reconciliation advances the fence and revokes the active token. A stale/late
worker cannot commit a summary or terminal result after
expiry/reconciliation. The configured provider deadline must be demonstrably
bounded below the lease duration; this does not eliminate process-death
uncertainty. Reconciliation beyond
`indeterminate` requires provider operation correlation explicitly supported
by the selected runtime, or a new user intent. APP-STATE World-turn claims and
recovery APIs do not authorize reuse for Plan actions.

The owning PostgreSQL tests must exercise concurrent reservation for one key,
same-key exact retry and changed-fingerprint conflict, live-pending reads,
one-time expiry reconciliation and fence advancement, completion/failure CAS
before expiry, and stale/late writes after expiry with no summary leakage.
Implementation evidence must also show the selected runtime's actual provider
deadline is bounded below the configured database lease.

### Existing Content basis boundary

The current `get_committed_playable_revision(document_id, revision_n,
expected_sha256, kind="plan", expected_world_id=...)` read returns the resolved
WorkObject and immutable WorkRevision tuple, including object revision,
WorkRevision UUID/number, SHA-256, and Markdown. The Plan owner must verify the
World/document/kind/active binding and fingerprint the resulting exact tuple.
The read selects an immutable basis; if the Plan advances before the action
row is inserted, persist the captured reference rather than requiring it to
remain today's head. Historical retries use that exact Content revision read.
`get_current_world_plan_revision` is available when the caller has the full
expected object/revision-number/digest tuple and requires a currently matching
Plan; it must not be used to add a second current-at-insert validation after
the accepted basis was captured.

APP approves this existing Content boundary for reference resolution only.
Plan/DEMO remains the owner of its action schema, action lifecycle, and safe
projection. No migration, provider, route, UI, or product-state work is
authorized until PRIME pins the implementation lease.
