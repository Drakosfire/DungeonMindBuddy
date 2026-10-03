# HANDOFF — INTERACTION MAP: one Build projection action

**Status:** ACTIVE — bounded proof authorized by OverMind PR #14 head `1d8dcf7a20dd48fcf2327db8ffc73f277ba16eb7`
**Owner:** INTERACTION MAP, Buddy implementation steward
**Coordination / merge owner:** PRIME task `01a0def6-8fb5-7520-80ff-ef6e67916115`
**Concurrent product owner:** DEMO task `01a0885e-375c-7501-9f6e-a58528b39894`
**Base:** Buddy `main` / `origin/main` at `d5f0ada66ddbebf2ec1dca55ea493ff21da476c3`
**PR topology:** `parallel-independent` of DEMO-J1 Plan world-scope read repair and the open Buddy PRs listed in §5; no behavioral dependency.
**Assigned PR:** one PR titled `INTERACTION MAP: prove shared Build projection action`; PRIME owns merge. Do not merge this slice.

## §1 Mission and invariant

Prove one existing read-side action can be described without its callback and selected by the same semantic ID by Buddy's human ToolHost and a deterministic Agent-side consumer. Both callers must resolve against the current publication and use the existing Tool activation path. The proof is limited to Build's `build-find-existing-object` action (“Find existing object”), whose effect is opening the registered `BuildReferenceSearchProjection`.

This demonstrates one current UI action. It does not establish durable write authorization, a whole-app action map, a model-driven loop, or a new Agent surface.

## §2 Current action path

`buildBuildSurfaceInteractionPublication` publishes the action with a stable ID, label, current availability, and projection activation. Its surface identity and canvas work object are keyed to the exact Build document. An invalid graph lens disables the action with the resolver's reason.

The ToolHost resolves the action by ID from the current effective publication. `activateToolContribution` calls the current projection activator and returns `opened` only when the registered projection actually opens; otherwise it returns an ignored result. The provider binds the activator to the current surface lease. The deterministic consumer will use the same action ID and activation helper after checking that its descriptor still matches the current publication's surface identity and exact document target.

The sanitized descriptor may contain the action ID, label, availability, surface identity, exact work-object target, and bounded effect description. It must contain no callback, projection payload, hidden binding value, document body, or unrelated action catalog.

## §3 DEMO clearance and runtime ownership

DEMO confirmed there is no direct path or runtime collision with its active `HANDOFF-DEMO-world-scope-plan-reads-v1.md` §4 lease and explicitly accepted parallel scheduling for this action. DEMO's unresolved Plan-read mapper failure remains DEMO-owned and is not a prerequisite for this proof.

Focused Vitest fixtures may mount the real Build publication, ToolHost, and projection host with mocked API responses. Do not use DEMO's Of Conks database, API processes, ports, World registry, or corpus. No shared runtime, database, migration source, or generated test output is owned by this slice.

## §4 ACTIVE write lease

- `Docs/Plans/HANDOFF-INTERACTION-MAP-semantic-action.md` — this pinned slice authority and topology record.
- `apps/live-control-ui/src/agentInteraction/semanticActionProjection.ts` — one-action sanitized descriptor and current-context matching.
- `apps/live-control-ui/src/agentInteraction/semanticActionProjection.test.tsx` — owning-boundary UI and deterministic-consumer proof.

No other paths are in scope. The handoff is committed and pushed before implementation work begins.

## §5 Re-anchored concurrent work

Buddy `main` was first re-anchored at `bf67c16fceba09026cef7a6e833a58666fa5855a` before implementation, then advanced to `d5f0ada66ddbebf2ec1dca55ea493ff21da476c3`. After checking its non-overlapping DEMO-J1 handoff update, the implementation branch was rebased onto `d5f0ada` before PR creation.

- Buddy main advanced after the initial re-anchor: `10a7b42` recorded accepted DEMO-J3 PLAY-2 authority, `bf67c16` rebriefed DEMO-J1, and `d5f0ada` added selected-object World-scope reads to the DEMO-J1 lease. The latest handoff explicitly permits this experiment in parallel and confines its code ownership to the two new `agentInteraction/semanticActionProjection*` files; its added Plan/graph-reference paths do not overlap this slice. Fixture runtime remains disjoint.
- DEMO-J1 still has no accepted Plan-read witness. Its rebrief records the blank-campaign Surface Information and selected-object scope gaps; those repairs remain DEMO-owned. The experiment does not depend on them.
- Buddy PRs #763/#764/#765 are the open Rules Lawyer stack; #764 touches the Plan projection catalog, but none of these PRs writes this slice's three leased paths or is a behavioral prerequisite.
- Buddy PRs #760/#761 are blocked documentation-only UI handoffs. #767 is closed; Buddy #779 is merged at `2ccc96f`, before the current base.
- OverMind PR #13 remains an exploratory design seed; it supplies no runtime schema or implementation contract.

If any changed path, shared registry, or runtime use overlaps current work, stop and return to PRIME for serialization or a split.

## §6 Acceptance evidence

The focused test must prove:

1. The human ToolHost and deterministic consumer select `build-find-existing-object` from the same current publication and open the same registered projection through the existing activation helper.
2. The effect is reported as `opened` only after the projection opens; unavailable or failed opens do not report success.
3. The descriptor contains no callback or projection payload and reports current enabled/disabled availability.
4. Removed and disabled actions do not open.
5. A descriptor from an old lease or another exact Build document cannot activate under the new publication.
6. The selected document target in the descriptor matches the current publication's canvas work object exactly.

Run the focused owning-boundary test and `git diff --check`. Do not use helper-only evidence to claim the projection host opened.

## §7 Stop conditions

Stop and report to PRIME if the proof requires a fourth path, changes to Build/ToolHost/Surface Interaction shared runtime contracts, a privileged writer, DEMO-owned paths or live state, a cross-repository contract, or a broader action catalog. If a broader ownership/result contract is necessary, request a bounded ARCHITECTURE ruling; do not expand this PR.

## §8 Return

Return to PRIME with exact base/head and cumulative diff, focused test output, the UI and Agent-side action IDs, current target/availability, stale lease/selection results, actual projection-open result, and explicit DEMO effect (`none`). PRIME reviews and manages merge; this handoff does not authorize merge.
