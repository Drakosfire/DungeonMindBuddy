# Explicit Plan controls adopt native reference execution

Status: ACTIVE. Owner: PRIME. Authority: active reference integration goal.
Parent PR: #2102, reviewed head 442f2e827ce09b63906d8bec3504b0ab6ce9e319.
Branch: codex/plan-explicit-native-ui. Serial merge order: merge #2102,
rebase this slice onto its exact remote merge, independently review and verify,
then merge and deliver under an owned runtime lease. Reuse existing checkout.

## Outcome and scope

Fresh explicit question and Plan-change controls use native submit with the exact
operation and authored references. Freeze pending recovery and retained Retry;
new composer preferences cannot reinterpret an old operation. World-context-off
writing fails clearly before dispatch. Preserve automatic requests and the
exercised historical clarification continuation. No model or endpoint changes.

Adopt the existing displayed-target guard for both native writes and historical
continuation instead of duplicating its invariant. Preserve captured selection,
scene, generation and basis checks; no silent caret fallback. Preserve source
versions and normal proposal review/Save ownership.

Write lease: Plan request/history fields only in UI api/types.ts; the Plan
conversation component, owning worldHistory tests and demonstrated affected
PlanSurfacePage integration tests; hosted-validation owning UI selectors; this handoff and the
predecessor handoff's settlement. Add owning proposal-review tests only if the
migration exposes a demonstrated coverage gap. No ingestion or live state writes.

## Adoption/demolition verification

Inventory old fresh manual-producer tests individually. Adopt target capture,
composer preservation, pending and Retry tests into native dispatch. Seed retained
historical Actions/proposals directly for historical-reader and clarification
continuation checks; do not generate them through a retired fresh caller.
Remove superseded producer expectations only after identifying their replacement
owner/coverage. Preserve review/Save, stale-target, reload, history export and
recovery invariants. Current native proposal review is PlanPageProposal, distinct
from the retained historical PlanEditReview. Keep their responsibilities explicit.

Independent review, required CI and protected delivery precede ordinary explicit
question/change reference dogfood. Full Plan/Play/Build acceptance and remaining
legacy continuation retirement remain open; this slice does not complete the goal.

## Review map for superseded producer tests

- Target capture (cursor/scene/selection/missing/stale/late) and six draft-preservation
  cases now exercise native submit; the real PlanSurfacePage scene/selection caller
  checks its exact capture and proves no implicit Save.
- Historical clarification, retained applied/unapplied local proposal readers and
  full-cap history export/reload are seeded from retained records, without invoking
  the removed fresh producer.
- Old fresh Compose/Apply integration cases for inline preview, repeated proposal,
  draft changes, missing scene, stale Before and explicit Save are superseded by
  native submission tests, shared planAgentEditProposal/planPlacementCatalog tests,
  retained PlanEditReview component tests, and current PlanPageProposal tests.
  The latter exercise explicit Save, stale placement/basis, terminal discard/reload
  and exact uncertain-command retry. No old executor is revived for green tests.
- Old in-flight local PlanAction proposal/history cases are superseded by existing
  native pending/history/conversation-fence tests plus original-choice/reference
  Retry against a newer composer. All historical record readers remain.

These deletions are coupled to changing the fresh producer. Splitting their
expectations into an earlier cleanup PR would erase tests of still-live behavior;
retaining them afterward would preserve a retired execution route. Current
ordinary explicit-operation proposal/edit/Save/reload dogfood remains a delivery
acceptance gate, not a claim established by these test substitutions.
