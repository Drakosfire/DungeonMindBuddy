# Ordinary Plan contextual paragraph placement

Status: ACTIVE for inert catalog/codec and test preparation. Production V2
admission, V2 producer activation and the reader-fence file are gated on #4240
landing its reserved 0170 migration. Alan explicitly chose: wait for #4240,
then add 0171 after 0170. No production migration execution or deployment.

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
Expand this lease with exact paths and a fresh audit before wiring consumers.
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
