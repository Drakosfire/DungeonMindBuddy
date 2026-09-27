# HANDOFF — DEMO: qualify selected first-World edges before sealing

**Created:** 2026-09-27
**Status:** BLOCKED — Buddy #779 must merge and settle before activation
**Execution owner:** DungeonMindBuddy / DEMO first-World preparation
**Design requested by:** MIND, returning the observed blocker to its owning Buddy boundary
**PR topology:** serial; one assigned implementation PR after #779 and DEMO scheduling re-anchor
**Design base:** Buddy `08f0b5e82098782d8990bbf42c002758f58d9f6c`
**Implementation base:** unset until activation; use a fresh accepted `origin/main`
**Suggested implementation branch:** `codex/demo-first-world-edge-qualification`
**Assigned title after activation:** `DEMO: qualify first-World edges before confirmation`

This document is a bounded design. It reserves no write lease and authorizes no
implementation or dispatch while BLOCKED. Its exact committed ref may serve as
design authority; the DEMO steward owns activation and product verification.

## 1. Ownership ruling and current anchors

The defect belongs to Buddy's ordering of preparation checks. There is no
identified missing DungeonMind API and no WorldKeeper change is required.

- DungeonMind main: `4d11686d679029ae4ef0902a13edc0509c0ce476`.
- WorldKeeper main: `662a028fb1882719c4c3e192134a1a6b7a58026c`.
- Buddy's accepted DungeonMind pin: `0f709d76fdc53bac9c9258d1751463ae2c76ca71`.
- Buddy's accepted WorldKeeper pin: `49a8620f066ce7ef8972a699020c012f50af9158`.
- Buddy's GenerationEngine pin remains `9122257f5a8842e4771990a3316130bc1bf7e332`;
  inference is not involved in this repair.
- Serial predecessor #779 is OPEN at inspected head
  `2d5ab6ade1d89ec608c941093819ea36404fd18e`; its report and PostgreSQL
  composition test do not overlap this production repair. Its merge SHA and
  final review are not yet knowable and must be recorded at activation.

DungeonMind's `dungeonmind_dnd` package already owns the versioned
`world-object-v5` vocabulary and exposes each predicate's `subject_kinds` and
`object_kinds` through `load_builtin_world_object_v5_vocabulary()`. Those
package files are unchanged between Buddy's installed pin and DungeonMind main.
Buddy's `assertion_qualification.CURRENT_V5_TARGET` consumes that catalog.
`edge_endpoint_kind_admission_reason()` implements the existing Buddy mapping,
predicate lookup, direction reversal, and endpoint-kind admission check.

The ordinary route currently executes:

```text
prepare_first_world
  → materialize_first_world_plan
  → confirmable = accepted assertion count > 0
confirm_first_world
  → rematerialize and verify sealed plan
  → DungeonMindWorldGraphInitializationAdapter
  → qualify accepted contribution / endpoint admission
  → governed atomic initialization
```

The missing check is before the first confirmable plan is returned. This path
does not call WorldKeeper; moving it into the separately accepted vNext
WorldKeeper composition would be a different capability. Existing confirmation
qualification and DungeonMind publication remain final guards.

Read with this handoff: Buddy `Docs/Roadmaps/ROADMAP-demo.md` and
`Docs/Plans/STEWARDS-HANDOFF-demo.md`; the existing first-World initialization
port/adapter; DungeonMind `Docs/Architecture/AUTHORITY.md` sections 5, 7 and 8;
WorldKeeper `Docs/Architecture/BOUNDARY-dungeonbuddy-worldkeeper-dungeonmind.md`.

## 2. Evidence and an essential diagnosis correction

DEMO observed at Buddy `58c650e8` that child run
`ababe16c-7cd7-5d9a-b602-a8299a038af4` prepared a selected 21-node/8-edge
contribution with `confirmable=true`. Confirmation failed atomically with
`dungeonmind_inexpressible` / `endpoint_kind_not_admitted`. After the operator
rejected three edges, 21 nodes and five location `contains` edges published as
`rev:22ef509825ee1048efc73a1a1aa4a60c`. These are supplied runtime observations;
this design did not reopen the licensed source or mutate that World.

The claim that all three rejected edges are intrinsically inadmissible is not
supported by the current mapping. The helper expects **Buddy kinds**, not raw
CandidateNode types. The actual node mapper normalizes `character → npc` and
`organization → party`. Pure checks against the exact installed DungeonMind
pin and the existing confirmation endpoint guard agree:

```text
serves     character → organization  => npc → party       admitted
belongs_to character → organization  => owns party → npc  endpoint_kind_not_admitted
parent_of  character → character     => npc → npc         admitted
contains   location  → location      => location → location admitted
```

Passing raw `character`/`organization` directly into the helper falsely rejects
all three. The repair must use the actual mapped node kinds used by publication
and preserve the admissible `serves` and `parent_of` cases. Do not freeze the
historical operator's three-edge rejection as desired product policy. If the
exact observed contribution differs from these stated types, report that
separately from this synthetic parity evidence.

## 3. One merge-ready invariant and behavior

For every selected accepted edge, first-World preparation checks the mapped
predicate and correctly oriented mapped endpoint kinds against the same
mounted vocabulary used by confirmation **before returning a sealed
confirmable plan**. An inadmissible selection returns an actionable preparation
error and changes neither operator decisions nor durable state. A valid
selection retains its existing semantics and can confirm normally.

Implement at `materialize_first_world_plan`, after existing decision/endpoint
resolution and before sealing the effect/digest. Reuse
`edge_endpoint_kind_admission_reason`; derive endpoint kinds from the mapped
accepted node assertions or the exact existing node mapping. Do not duplicate
the catalog, make raw candidate labels into Buddy kinds, or introduce another
predicate map. Load the current catalog once for a materialization invocation.

Use the existing `WorldbuildingWritePlanError → ExtractPromoteError` transport:
HTTP 422, a stable existing qualification reason such as
`endpoint_kind_not_admitted`, and a safe message identifying the offending edge
ID, predicate and endpoint kinds. No response schema or frontend contract change
is needed. Deterministic first-error reporting is sufficient; do not return a
confirmable partial selection. Unsupported mapping and absent catalog predicates
also fail closed through the existing qualification reasons.

Only edges the operator selected `accept` undergo this eligibility gate.
Operator-rejected edges remain explicitly rejected in the sealed contribution;
their presence cannot veto a valid accepted subset. Preserve unresolved-endpoint
errors, decision digests, source/evidence qualification, zero-accepted behavior,
exact confirm rematerialization, retry identity and final adapter qualification.
Never silently convert `accept` to `reject`, omit an accepted edge, swap a
predicate, or broaden the vocabulary.

## 4. Expected write lease after activation

Production and evidence paths:

```text
apps/live_control_server/services/first_world_graph.py
tests/test_first_world_edge_qualification.py                         # new
tests/test_cutover_dungeonmind_first_world_initialization.py
Docs/Reports/REPORT-DEMO-first-world-edge-qualification-v1.md         # new
```

Conditional backward-looking predecessor sync, only if still stale after #779
settlement (the steward resolves this set before activation):

```text
Docs/Plans/HANDOFF-DEMO-J3-PLAY-2-persistent-vnext-postgres-composition.md
Docs/Roadmaps/ROADMAP-demo.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-demo.md
```

That sync may record #779's actual merge/review/evidence and this slice's ACTIVE
status, never pre-mark this slice complete. If the steward has already settled
those authorities, remove these conditional paths from the activated lease.
The roadmap mirror must stay byte-identical. Activation of this handoff itself
belongs to the steward before dispatch. Do not change stable architecture merely
because the predecessor merged.

Read-only dependencies: `assertion_qualification.py`,
`world_graph_initialization_adapter.py`, `world_graph_writes.py`,
`candidate_graph_to_contribution.py`, `worldbuilding_write_plan.py`,
`first_world_graph_publication.py`, existing routes and test fixture helpers.
No changes to those paths are anticipated. Need for another production path is
a stop report with the reason, not automatic lease expansion.

## 5. Activation, collisions and runtime ownership

Before activation the DEMO steward must re-fetch all three repositories; verify
#779 is merged; settle its mutable state; record exact implementation base,
installed pins, final predecessor merge/review, and current PR/worktree leases.
The requested sequencing is serial. Do not create an implementation branch or
PR before this gate. This document's branch is only a design artifact.

At design time DungeonMind and WorldKeeper have no open PRs. Buddy #779 owns
only its new PLAY-2 test/report. Rules #763 owns dependencies and its query
paths; #764/#765 own Rules UI/answer paths. #760/#761 are UI design PRs. All
are disjoint from the proposed repair lease. The ACTIVE
`HANDOFF-DEMO-world-scope-plan-reads-v1.md` also has disjoint code/tests, but
shares the DEMO roadmap and operator runtime. Recheck its actual state at
activation: finish the serial scheduling decision before opening this PR.
Concurrent operation would require a recorded topology amendment by DEMO.

Automated witnesses use synthetic source/candidate fixtures, temporary registry
and corpus roots, and a lane-owned disposable database pair. Existing native
first-World fixtures TRUNCATE the configured DungeonMind test DB: provision a
fresh, uniquely named `dmb_firstworld_test_<random>` database, migrate it from
the exact installed DungeonMind source, and set `DMB_CUTOVER_TEST_DATABASE_URL`
only to that verified disposable target. APP-STATE's fixture creates its own
unique database through `DMB_APPLICATION_STATE_TEST_DATABASE_URL` admin access.
Neither fixture may target a DEMO, C1/C2, shared developer or PLAY-2 database.
Do not launch or replace shared servers. No model calls or licensed bytes are
needed for implementation or automated proof.

## 6. Required witnesses and verification commands

1. Synthetic `character serves organization` and `character parent_of character`
   remain accepted after the real kind normalization. `location contains location`
   succeeds. Include an admissible inverse mapping such as `item belongs_to
   character` to prove reversal, not blanket rejection of `belongs_to`.
2. `character belongs_to organization` fails prepare with its edge ID and stable
   reason. Also cover an invalid direct endpoint pair, unmapped predicate and a
   mapped predicate absent from an injected catalog. Missing/rejected endpoints
   retain their current error. Check at least one catalog-driven negative so a
   hardcoded special case cannot pass the suite.
3. A mixed valid/invalid accepted set fails as a whole. Decisions, candidate bytes,
   run status, source and registry digests remain unchanged; no accepted subset
   is silently sealed. Explicitly rejecting the bad edge then preparing preserves
   the valid edges, their direction, and the recorded rejection.
4. Through the ordinary HTTP prepare route with the real first-World service,
   an invalid selection returns 422 and no confirmable plan. Assert no call to
   initialization and unchanged PostgreSQL World/head/revision/source/contribution/
   review/initialization-receipt counts. Helper-only tests cannot close this gate.
5. Through the native PostgreSQL route fixture, the corrected synthetic selection
   prepares, explicitly confirms and reads back exactly its accepted edges/kinds.
   Retry preserves existing receipt/idempotency behavior. Rejected edges are absent
   from published graph truth and remain review evidence as currently contracted.
6. Exercise the existing confirmation adapter directly with an invalid synthetic
   contribution that bypasses preparation. It still refuses with
   `endpoint_kind_not_admitted` and publishes nothing. Retain current tampered-plan,
   source-drift and concurrency regressions; no new concurrency mechanism is added.

After provisioning the isolated test dependencies above:

```bash
uv sync --locked
uv run pytest -q tests/test_first_world_edge_qualification.py
uv run pytest -q tests/test_cutover_dungeonmind_first_world_initialization.py
uv run pytest -q tests/test_candidate_graph_admission_contract.py tests/test_cutover_worldbuilding_authority_port.py
uv run ruff check apps/live_control_server/services/first_world_graph.py tests/test_first_world_edge_qualification.py
git diff --check
```

Run relevant witnesses with zero skips. Record exact commands/counts and inherited
failures against the actual activation base; no broad suite or unrelated baseline
repair is required by this narrow design. If an existing large test file has a
Ruff baseline, inspect newly changed lines and report the baseline separately.
No production test was run or claimed by the design author; the design-time
execution evidence is the pure helper/confirmation-guard parity check in §2.

## 7. Stop conditions, handback and DEMO return

Stop for any proposed vocabulary widening, node-kind policy change, new generic
DungeonMind API, WorldKeeper migration, pin/lock change, UI redesign, inference
repair, source revision reconstruction, additional production path or live-data
write. If actual installed authority disagrees with the re-anchored catalog,
return a minimal synthetic reproduction with the exact package provenance before
designing a separately owned prerequisite. Never solve that discrepancy by
guessing a new admitted kind or predicate.

Handback: exact design ref, implementation base/head, PR URL, changed paths,
installed dependency provenance, normalized qualification cases, route and
PostgreSQL evidence, no-mutation/retry/final-guard results, and predecessor state
sync disposition. Obtain an independent review of that exact implementation
head before the DEMO steward uses its existing merge authority.

Minimal DEMO return contract after merge: record the accepted SHA and prove in
an isolated synthetic first-World journey that a selected bad edge is rejected
at Prepare with a useful message, the operator's selection remains intact,
explicit rejection permits a new plan, and one Confirm publishes the exact
valid subset. Record World/head and counts before/after. Preserve admissible
`serves`/`parent_of` examples; do not claim that rejecting all three historical
edges was necessary. The already published Of Conks World and original child
run remain untouched. DEMO owns any later licensed replay or human usability
assessment and serializes its runtime independently.

Successor: return to DEMO's current J1/J3 frontier and re-anchor. This closes
preparation/confirmation endpoint parity only; it neither accepts extraction
quality nor advances Kernel V7, PLAY-3, ontology expansion or full DEMO acceptance.
