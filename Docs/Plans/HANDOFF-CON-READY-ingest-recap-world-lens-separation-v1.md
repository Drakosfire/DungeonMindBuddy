# HANDOFF — CON-READY: separate Ingest recap and World lenses

**Created:** 2026-09-21
**Status:** ACTIVE — blocker repair before PR #742 existing-object dogfood resumes
**Workstream:** `CON-READY / DOGFOOD-CONTINUITY / ingest lens separation`
**Design base:** `main@ce3b86bd560b294a97f6c7bfb7d23dfdacb78b07`
**Branch:** `con-ready/ingest-recap-world-lens-separation-v1`
**PR title:** `CON-READY: separate recap and World lenses`
**Topology:** authorized parallel-independent blocker repair alongside frozen #742; #742 remains open and frozen at `8fcbbc28e6da7c4d9652232a3316d591f1a5504d`. This lane does not depend on or modify #742.
**V2-3:** unauthorized

## §1 Mission and merge-ready invariant

Separate source/recap selection from governed World-lens selection on
`/ingest`. The operator reads one recap and resolves its mentions against an
independently selected governed World projection.

```text
Source decides what gets marked.
World decides what may be bound.
```

Recap campaign/session control only prose, extraction, and the local working
projection. The shared World lens controls durable identity eligibility against
its exact coherent revision. A resolver candidate is an existing governed
target only when the exact canonical bind-target node ID is present in that
World projection. The bind-target rule is
`existing_object_ref.object_id` when present, otherwise `candidate_id`.
Labels, aliases, confidence, party-registry presence, recap-local nodes, and
local staged objects never substitute for exact membership.

Candidate evidence remains visible when it is not durable, but its `Use
existing` / `Add as alias` action is unavailable. Published-recap staging also
rejects absent exact bind-target IDs so stale UI cannot bypass the rule.

The recap remains source-grounded: World nodes outside the selected recap do
not become Markdown annotations merely because they exist in the World lens.

## §2 URL/state authority

On `/ingest`, the two state machines use separate URL vocabulary:

```text
Recap/source selector (RecapGraphModule)
  campaign=longmont-c1
  session=session-1

World lens (shared World-lens provider)
  campaigns=longmont-c1,longmont-c2
  graphFocus=longmont-c2:23   # optional
```

`scopeMode` is legacy on `/ingest` and is ignored for World focus. The old
deep link `/ingest?campaign=longmont-c1&scopeMode=campaign&session=session-1`
must resolve to C1/S1 recap plus the default C1+C2 World union with no focus.
Absent explicit `campaigns`, Ingest defaults to both review campaigns; absent
`graphFocus` means no session focus. Changing either selector preserves the
other, and hard refresh round-trips both independently. Plan/Build URL behavior
remains unchanged.

## §3 Projection contract

Keep three distinct collections:

```text
recapNodeViews             recap annotations and source selection
workingProjectionNodeViews recap plus local, uncommitted proposals
governedWorldNodeViews     exact shared World-lens durable membership
```

Only `governedWorldNodeViews` authorizes an existing target. If the shared
World projection is loading, unavailable, or errored, existing-target actions
fail closed while recap reading and resolver evidence remain available.
Durable object inspection uses the shared World-lens request/revision where the
existing complete-object API supports it; recap campaign/session remains source
provenance.

## §4 Files in scope — write lease

Expected paths:

- `Docs/Plans/HANDOFF-CON-READY-ingest-recap-world-lens-separation-v1.md`
- `apps/live-control-ui/src/graphLens/sessionCampaignContext.ts`
- `apps/live-control-ui/src/graphLens/sessionCampaignContext.test.ts`
- `apps/live-control-ui/src/graphLens/WorldGraphLensContext.tsx` only if needed
- `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.test.tsx`
- `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.tsx`
- `apps/live-control-ui/src/planSurface/graphPreview/RecapGraphModule.test.tsx`
- `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.tsx`
- `apps/live-control-ui/src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.test.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringBindExistingPanel.tsx`
- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphObjectAuthoringPublishedWizard.tsx` only if needed
- its focused test only if the production wizard changes

Bounded exception: one pure helper and one focused test in
`graphReviewWorkbench/` may classify a resolver candidate against the exact
governed node map. It may not query an authority, fuzzy-match, remap aliases,
invent IDs, merge, publish, or cache World membership.

## §5 Explicitly out of scope

Do not reconcile the six Eldyrwild PC IDs, mutate or publish the World, use raw
SQL/JSON repair, change DungeonMind persistence, alter #742's write protocol,
redesign resolver ranking, remove candidates, annotate the whole World into
Markdown, rewrite Plan/Build URL grammar, start V2-3, or complete #742.

## §6 Required implementation behavior

1. `/ingest` defaults to recap campaign/session plus World C1+C2/no-focus.
2. Recap URL synchronization does not write World-lens parameters or
   reinterpret `session` as World focus, and removes legacy `scopeMode`.
3. World-lens synchronization writes `campaigns` and optional qualified
   `graphFocus`, preserving recap `campaign` and unqualified `session`.
4. Resolver candidates remain visible; candidate-only results explain missing
   durable World membership and expose no actionable existing operation.
5. Exact membership of the canonical bind-target node ID in the shared
   governed projection is the sole existing-object eligibility rule. Resolver
   results use `existing_object_ref.object_id` when present and otherwise
   `candidate_id`; no label, alias, or fuzzy remapping is allowed.
6. The published-recap staging callback rejects candidate-only operations and
   leaves proposals unchanged.
7. The working projection remains local and never proves durable membership.

## §7 Evidence required to merge

Run from the exact current head:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/graphLens/sessionCampaignContext.test.ts \
  src/graphLens/useWorldGraphLensProjection.test.tsx \
  src/planSurface/graphPreview/RecapGraphModule.test.tsx \
  src/planSurface/graphPreview/WorldGraphRecapProjection.test.tsx \
  src/planSurface/graphReviewWorkbench/PublishedRecapLocalAuthoring.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphObjectAuthoringSurface.test.tsx \
  src/planSurface/graphReviewWorkbench/graphExistingObjectEligibility.test.ts \
  src/planSurface/graphReviewWorkbench/graphExistingObjectIdentityWorkbench.test.ts \
  src/planSurface/graphReviewWorkbench/useGraphObjectAuthoringDraft.test.ts
pnpm --dir apps/live-control-ui typecheck
pnpm --dir apps/live-control-ui build
git diff --check
```

Record exact pass/fail counts, base/head provenance, diff stat, and changed
paths. Evidence must cover old C1/S1 deep links, independent selector changes,
hard refresh, Plan/Build compatibility, recap/working/governed view separation,
candidate-only `pc:ephanna`, an exact World-present candidate absent from the
recap, projection failure fail-closed behavior, and complete-object reads via
the World lens. Read-only dogfood must cover both selector directions: changing
the recap leaves the World lens fixed, and changing the World lens leaves the
recap fixed. It must also show a World-only existing target as selectable
without adding a recap annotation. No live mutation is allowed.

## §8 Stop conditions

Stop and return to the steward if exact World membership cannot be obtained
from the shared projection, a backend change is required, Plan/Build URL grammar
must change, an out-of-lease path is needed, or the work would mutate live
World state.

## §9 Acceptance

Merge-ready means source/World URL ownership, projection separation,
candidate-only fail-closed behavior, exact durable positive eligibility,
complete-object authority, focused evidence, and read-only dogfood all agree.
PR #742 remains frozen until this slice merges and its separate authorized
identity repair has passed. Do not begin V2-3.
