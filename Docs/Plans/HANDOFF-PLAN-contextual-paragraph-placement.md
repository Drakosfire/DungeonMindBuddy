# Ordinary Plan contextual paragraph placement

Status: ACTIVE. The initial inert preparation gate on #4240 is resolved: that PR
merged, and this lane rebased onto current main6f8af81e6dd47ec92b5ef9a0180e2e34ffd104c4
containing its actual 0170 migration. Alan explicitly chose #4240 first, then
0171 after0170. The authorized fence is now allocated as
`20261120_0171_plan_paragraph_placement_reader_fence.py`, down_revision0170.
No production migration execution or deployment. V2 public admission/producer
wiring is in progress in draft #4264; ordinary-model acceptance and exact-source
qualification remain unfinished. Historical inert checkpoints below describe
their recorded heads, not the current working-tree wiring.

## Outcome and delivery

One serial capability: normal Buddy Send nominates a before/after root-paragraph
boundary on a genuinely plain Plan, then uses existing proposal/apply and explicit
Save. No selection required; an incidental caret never wins over the request.
Ambiguity/not-found/discussion must not edit, reserve or Save. Stale/foreign
context refuses; deliberate selection can recover. Preserve unrelated content,
Undo/Redo and real Save/cold reopen. Composed Plan and Build are later separately
qualified slices, not acceptance inferred from this plain-Plan slice.

Branch `codex/plan-contextual-paragraphs`, isolated checkout
`/home/drakosfire/Projects/.codex/bf5b/DungeonMindBuddy`, pinned initial base
`45eb72ab2fa673bfe05bc0effbaa7b7acdd9694d`. Predecessors #4243 and #4248 are
merged as 08d23da86a079121b7b31812e93db1857df17864 and
97c89e93c13a79c1c5e319bf28409b1c78f62b53. Their technical evidence and independent
reviews do not establish ordinary chat or release qualification.

## Authority and write boundary

Alan authorized contextual-targeting/test splits in PlanSurfacePage.tsx,
components/WorldPlanAgentConversation.tsx and agentEdit/planAgentEditProposal.ts,
preserving #3824/#1014/#1188's hosted authorization, rollout and welcome behavior.
Prefer their existing catalog forwarding without edits unless tests expose a gap.
Alan also authorized only paragraph-catalog union/decoder changes in
agent_conversation/native_execution.py and services/plan_jev_driver.py across
#3307/#2462/#2225; preserve retrieval ordering, writer instructions and source status.

Initial exclusive expected writes: this handoff,
`src/application_state/agent_conversation/plan_placement.py` and its owning
`tests/application_state/test_plan_placement.py`. Fresh audit checked 60 returned
open PRs and found no overlap on these implementation/test paths.
The lease includes truthful merged-predecessor settlement in
`HANDOFF-LAYOUT-existing-identity-save-retention.md`.
The lease now includes the single authorized fence migration above, after a
fresh 60-open-PR reservation audit found no0171+ migration collision.
Expand this lease with exact paths and a fresh audit before wiring consumers.
Consumer wiring amendment: a fresh61-open-PR audit found only the already
authorized overlaps with #3307/#2462/#2225. Expected additional writes are
`apps/live-control-ui/src/planSurface/agentEdit/planPlacementCatalog.ts` and its
owning test; `apps/live-control-ui/src/api/planAuthoringReviewApi.ts` and test;
`apps/live_control_server/models/agent_turn.py`;
`src/application_state/agent_conversation/native_execution.py`, `types.py` and
`plan_jev_graph_packet.py`; and `apps/live_control_server/services/plan_jev_driver.py`.
Limit the shared native/driver edits to the authorized catalog union/decoding.
No dispatcher, retrieval ordering or writer-instruction change is included.
Independent review exposed a coupled V2 decision-guidance correction in
`src/application_state/agent_conversation/plan_authoring.py` (fresh open-PR file
audit: no overlap): retain exact historical V1 wording while referring to the
actual opaque V2 alias for after-heading choices. This remains the same paragraph
placement capability; it changes no retrieval or writer contract. Eight dev cases
were frozen before this adjustment in external `plan-ordinary-dev`, alongside
the independently authored, unread 22-case held-out oracle.
The normal-Send activation uses the explicitly authorized targeting-only split
in `apps/live-control-ui/src/planSurface/PlanSurfacePage.tsx`: request V2 for
plain pages while retaining V1 for composed pages. A refreshed open-PR audit
confirmed its only overlapping lanes are #3824/#1014/#1188, covered by that split.
The existing mounted `PlanSurfacePage.test.tsx` ordinary-first-Send cases now
assert that transport includes V2 paragraph choices; its overlaps with
#1014/#1188 fall within the authorized contextual-targeting/test split.
The consumer test lease also includes the existing native caller helper in
`tests/test_plan_jev_authoring.py`: a fresh61-open-PR audit found no overlap.
Limit the helper extension to an optional versioned placement fixture and its
serialized-request checks; preserve existing default test behavior.
The remaining planned owner chain is the frontend catalog/compiler and API
catalog union, backend turn input, retained native action/selection decoders,
actual decision proof and the existing proposal/apply/Save chain. No schema or
public V2 write path is activated by inert classes/tests.

One forward-only reader-fence allocation is authorized, subject to the explicit
#4240 → 0170 → 0171 chain. Do not create an independent Alembic head, invent
another compatibility owner, merge #4240 under this assignment, or run migrations
against operator/live data. Inspect actual SQL admission in owned disposable
PostgreSQL before deciding whether the fence alone suffices.

## Contract critique and review map

V1 explicitly admits caret/heading/section/end choices and validates real root
headings. Do not smuggle paragraphs into those kinds or forge the original caret.
V2 uses opaque local selectors and explicit before/after paragraph kinds; exact
indices, offsets, World/document/revision hashes and capture receipts stay host-side.
Model context contains semantic section/passage labels only. Keep V1 serialization
and hashes unchanged and derive the existing boundary-capture format only from
an admitted frozen choice and matching original capture. Explicit replacement
selection must not broaden into insertion. Reject malformed/foreign/stale roots,
unsupported/composed targets and mutated labels/digests. No page-top fallback.

The catalog is durable in native actions and retained selection/proof replay.
Old readers therefore require the existing application-schema fence before new
records. Independent contract review by /root/plan_contract_review confirmed this
and recommended reusing the existing root-boundary proposal/apply/Save machinery.

Validation progresses from pure codec/compiler controls to actual ordinary model
dispatch and real persistence. Positive: clear semantic target plus duplicate
elsewhere, no selection; exact boundary and untouched neighbors; Undo/Redo; Save
and fresh reopen. Negative: genuine ambiguity clarifies before reservation, plus
missing/discussion/stale/foreign and deliberate-selection recovery. Never count
scripted nomination, helper tests or mocked readback as ordinary routing proof.
Retain frozen dev and independently authored held-out sets before tuning. The
prior standalone Jev baseline consumed its held-out set and failed ambiguity;
do not reuse it as fresh held-out acceptance or tune on its answers.

Use owned disposable fixtures and per-test clones, external Projects evidence,
the global frontend resource lock, exact-SHA owning contracts, hosted verifier
and meaningful discovered diagnostic. Review cumulative base-to-head diffs and
independent exact-head judgments before authorized merge. Preserve baseline red
results and required human acceptance; do not claim release/deployment readiness.

## Inert preparation checkpoint

Added separate V2 option/catalog classes without changing V1 wire values or
hashes. V2 selectors are local opaque aliases; host-only source indices bind
explicit before/after paragraph kinds to actual nonempty root prose. Semantic
labels are checked against the captured text/heading context. Existing boundary
captures retain the real selection, and explicit replacements cannot broaden.
Composed roots and unrelated object targets refuse in this first plain scope.
No public request/retained-action decoder or default producer accepts V2 yet.

All 48 owning placement tests pass as working-tree diagnostics in the existing
locked environment and a task-owned disposable PostgreSQL template/per-test
clone setup (container buddy-layout-save-a0jv7t, current loopback33132).
Evidence: `/home/drakosfire/Projects/.codex/buddy-check.A0jV7T/plan-catalog-working.log`.
Ruff reports two pre-existing E701 lines in the owning test file; no new lint
diagnostics. Whitespace checks pass. Exact-source qualification, frontend
compiler, consumer integration, reader fence and actual ordinary-path/model/
persistence evidence remain unfinished. This checkpoint is not feature delivery.

## Preparation review corrections

Independent review of inert head164c3248 found two V2 contract gaps: named-table
captions were treated as semantic headings, and after-section accepted a later
boundary short of/beyond the actual section end. V2 now mirrors the frontend's
exact plain/unmarked caption predicate, including meaningful marks/extra attrs,
computes the next equal-or-higher-level semantic heading/end, and validates
canonical heading/section/end labels. Captured caret/selection labels are also
canonical, so they cannot claim an unrelated semantic destination.

All 58 owning tests pass after these corrections, including caption variants,
rehashed wrong section ends, wrong semantic labels and a mislabelled incidental
caret. The changed backend module passes Ruff; the owning test file retains its
two previously recorded E701 errors. Evidence: `plan-catalog-label-fix.log` under
the existing external task. This is still inert preparation, not ordinary-path
or migration qualification. V1 definitions and current public consumers remain
unchanged. Independent reinspection is requested before relying on the V2 shape.

## Reader-fence prerequisite settlement

#4240 is merged and current main contains its0170. The new0171 is chained directly
to that revision; no independent Alembic head or competing-slot reassignment.
The fence uses the existing forward-only schema-version mechanism, with a
disposable-database test for an older170 application's refusal and failed
downgrade preserving the171 schema version. SQL admission of actual retained V2
native records remains a required integration proof; a fence-only test does not
establish it. Default/public V2 production paths are still not wired.

All 59 owning placement/fence tests pass after chaining0171 onto the merged0170.
The initial fence-test diagnostic queried the wrong version table and failed;
the corrected test uses `application_state.schema_migrations`. Both attempts
are retained separately as `plan-fence-working.log` and
`plan-fence-corrected.log`. Backend module and new fence pass Ruff. These are
working-tree diagnostics and do not qualify the unfinished ordinary path.

## Consumer and ordinary-producer checkpoint

V2 now passes through public turn input, requested-work preparation, retained
native actions and selection/proof decoders. Shared explicit version dispatch
preserves omitted-schema V1 compatibility and requires an explicit V2 tag.
Plain Plan ordinary Send captures real root-paragraph aliases; composed pages
retain V1. V2 after-heading decision guidance uses the actual opaque alias;
historical V1 guidance is unchanged. No retrieval ordering/writer change.

Working-tree diagnostics under `/home/drakosfire/Projects/.codex/buddy-check.A0jV7T`:

- `plan-producer-composed-control.json`: 14 compiler tests pass, including actual
  editor offsets, Undo/Redo, async stale capture and composed V1 fallback.
- `plan-mounted-producer-activation.json`: nine mounted ordinary-first-Send cases
  pass with V2 choices; 131 unrelated cases skipped by this focused command.
- `plan-producer-typecheck.log`: TypeScript check passes under the global lock.
- `plan-cross-language-witness.json`: actual TS producer catalog validates in
  Python and prepares model state without the inspected host metadata. Synthetic.
- `plan-decoder-owner-parity-corrected.log`: 67 placement/fence/consumer tests pass,
  including public/requested-work/current retained-action raw version controls,
  scripted native proposal plus actual explicit Save/cold read, and no-reservation
  clarify/discuss. Its preceding failed attempt used an older action class in the
  test; preserved separately. This is not real-model targeting evidence.
- `plan-v2-authority-controls.log`: all70 tests pass after adding actual native
  reservation/proof controls for changed capture, page and conversation.
- `plan-owner-consumer-regression.log`: 132 pass, two mixed Rules replay failures.
  Exact base6f8af81e reproduces both same test IDs and owning pinned-evidence error
  in `plan-owner-base-mixed.log` (four other parameter cases pass).
- `plan-consumer-lint-comparison.json`: current/base both42 diagnostics with equal
  path/code/message multiset; full JSON retained. Lint remains red.

Disposable task PostgreSQL is currently loopback33133; fixtures own their session
template/per-test clones. No operator data or providers used by these diagnostics.
Exact-SHA verifier/review, broader discovery comparison and a joined ordinary
real-model/browser/Save/reopen witness remain required before merge. The fresh
held-out oracle is unread. No release, cross-surface or full-goal completion claim.
