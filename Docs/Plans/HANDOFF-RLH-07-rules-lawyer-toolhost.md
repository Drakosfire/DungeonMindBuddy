# HANDOFF — RLH-07 Rules Lawyer ToolHost

**Status:** ACTIVE — implementation candidate, pending review  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**Authority:** `Drakosfire/DungeonOverMind/Docs/Plans/PLAN-rules-lawyer-graph-experiment.md`  
**Predecessor:** `RLH_06_RULES_QUERY_PACKET_ACCEPTED` and the accepted shared presentation/UI-foundation stack  
**Primary question:** Can the shared ToolHost/presentation substrate support a useful Rules Lawyer evidence experience without one-off shell behavior?  
**Unlocks:** RLH-08

## Re-anchor before coding

This handoff was planted while the UI presentation-foundation stack was still active. At activation, read the accepted post-substrate re-entry decision and use the final ToolHost/publication contracts. If the host contract changed, amend this handoff rather than coding against this historical sketch.

The current Plan surface publishes tools through `createPlanSurfaceConfig` and the shared surface-interaction adapter. The shared ToolHost launches projection contributions; the Plan projection catalog owns render registration. This slice registers one tool and one catalog renderer through those contracts. The UI substrate documentation stack is still open, so this PR remains stacked on RLH-06 and must be reviewed against any accepted host changes before merge.

## User experience

Add one Rules Lawyer tool contribution:

```text
ask rules question
→ loading / explicit failure state
→ evidence results
→ citation chips
→ inspect source/evidence details
→ optional related rule/entity relationships
```

This PR intentionally stops **before generated answer prose**. The user can already get value by seeing highly relevant, exact, citable rules evidence inside Buddy.

The tool must make three states visibly different:

- no evidence found;
- partial/insufficient evidence;
- service unavailable.

## Reuse requirement

Exercise the shared UI foundation.

Prefer existing:

- ToolHost contribution/publication;
- shared cards/list primitives;
- Peek/Projection/source-navigation surfaces where they fit;
- shared loading/error/empty patterns from the accepted UI substrate.

If a missing generic primitive is discovered, keep the smallest reusable fix in the owning shared layer. Do not fork a Rules-Lawyer-specific host.

## Suggested lease

After re-anchor, expect a bounded new module plus smallest host registration:

```text
apps/live-control-ui/src/rulesLawyer/
apps/live-control-ui/src/api/        # query client
apps/live-control-ui/src/surfaceInteraction/... # registration only if required
focused tests
```

Do not take a broad lease on `App.tsx`, global CSS, ToolHost internals, or source navigation unless current contracts require a tiny integration edit.

## Citation behavior

Each rendered citation must preserve the durable identity returned by RLH-06. Clicking/inspecting it must never reconstruct source identity from display text.

## Do not

- generate an LLM ruling;
- add graph-reasoning UX;
- add Jev;
- redesign the whole Buddy shell;
- duplicate source-reader behavior.

## Acceptance proof

Focused UI tests prove:

- query submission;
- successful evidence rendering;
- exact citation identity survives API → UI;
- source/evidence inspection path works;
- no/partial/unavailable states render truthfully;
- ToolHost close/grouping behavior remains unchanged.

Acceptance token:

```text
RLH_07_RULES_LAWYER_TOOLHOST_ACCEPTED
```
