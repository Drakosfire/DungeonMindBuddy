---
pr_body_template: |

  ## Handoff pointer

  * Conversation/workstream: SURFACE-INTEGRATION / SI-3
  * Flow: SURFACE-INTEGRATION
  * Direction: DESIGN → CODE → REVIEW
  * Handoff: `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md`
  * Branch / PR: `agent/surface-information-plan-graph-reference-v1` / `SURFACE-INTEGRATION: make Plan graph information reactive`

  ## Verification pointer

  * Base: `cd6b20ffe151dc43dc21cb71ed77208389059566`
  * Predecessor: PR #676 merged @ `cd6b20ffe151dc43dc21cb71ed77208389059566`
  * Changed paths: HANDOFF §4
  * Verification: HANDOFF §7

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — Plan Graph Surface Information Reference Implementation

**Created:** 2026-09-02
**Status:** COMPLETE — merged PR #677 @ `29932a8ecb74b4bcbf12633f5167470a7f05fb81`
**Canonical handoff path:** `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md`
**Conversation/workstream:** `SURFACE-INTEGRATION / SI-3`
**Flow / owner:** `SURFACE-INTEGRATION`
**Direction:** DESIGN → CODE → REVIEW
**Base revision:** `cd6b20ffe151dc43dc21cb71ed77208389059566`
**Predecessor:** PR #676 / SI-2 merged at `cd6b20ffe151dc43dc21cb71ed77208389059566`; final implementation head `1ced8ea147f8119a424e9f44787cb7246ddb969d`; two formal review cycles
**PR title:** `SURFACE-INTEGRATION: make Plan graph information reactive`

**Completion record (SI-4 predecessor sync, 2026-09-02):**

```text
PR #677 merged
merge SHA            29932a8ecb74b4bcbf12633f5167470a7f05fb81
final implementation 345ee6957dadaa1d9052d60b70396534d7590ac8
formal review cycles 5
successor            SI-4 Ingest application-state authority
```

> Repository law: [`AGENTS.md`](../../AGENTS.md).
> Parent program: [`ROADMAP-surface-integration.md`](../Roadmaps/ROADMAP-surface-integration.md).
> Surface Information authority: [`CONTRACT-surface-information-v1.md`](../Design/CONTRACT-surface-information-v1.md).
> Structural Surface Interaction authority: [`ARCHITECTURE-surface-interaction-layer.md`](../Design/ARCHITECTURE-surface-interaction-layer.md).

---

## §0 Steward design ruling

SI-2 established the neutral Surface Information channel contract.

SI-3 must now prove that contract in the product at the failure boundary that motivated it:

```text
Plan → Edit → World Graph objects
  loading → ready / empty / unavailable / integrity error
```

The Of Conks failure was not that DungeonMind lacked data. The World Graph projection became ready, but the rich Edit panel remained the ReactNode originally published while the projection was loading. That is OC-020.

### Chosen repair

`WorldGraphLensProjectionProvider` remains the fetch owner and additionally publishes `SurfaceInformationChannel<WorldGraphProjection>` for the exact World Graph lens request it already owns. No second World Graph request is introduced.

The Plan World Graph objects panel is a connected component. Structural publication stays on the existing editor-tool path; changing graph information is read with `useSyncExternalStore`. `PlanSurfaceShell` structural dedupe remains intact. `AppChrome` does not compare ReactNode identity. `SurfaceInteractionPublication` does not acquire live graph payloads.

### §0.1 Plan reference, Build witness

Plan is the production Surface Information adoption. Build is an unchanged regression/collision witness. Build Surface Information migration belongs to SI-5 unless a later re-anchor splits it differently.

---

# §1 Mission and merge-ready invariant

## Mission

The GM can open Plan → Edit → World Graph objects and observe the current app-scoped DungeonMind World Graph projection transition truthfully from loading to its terminal state without Plan republishing structural editor tools merely because graph information changed.

## Merge-ready invariant

Given one mounted Plan surface and one exact World Graph lens request:

> **The World Graph objects panel is structurally published once, subscribes to the provider-owned Surface Information channel, and updates in place for each accepted observation generation; a verified DungeonMind projection becomes READY or EMPTY at its exact authority revision, unavailable dependencies become UNAVAILABLE, response-integrity violations become INTEGRITY_ERROR, and neither a late superseded response nor graph-information-only change can require a new AppChrome/editor-tools publication.**

The existing graph projection fetch remains the only authority read for this path. The current `PlanSurfaceShell` structural-publication signature is not the reactivity mechanism.

---

# §2 Context, authority, and lane

| Field | Required content |
| --- | --- |
| Parent authority | `ROADMAP-surface-integration.md`; `CONTRACT-surface-information-v1.md`; `ARCHITECTURE-surface-interaction-layer.md`; Of Conks OC-020 |
| Base revision | `cd6b20ffe151dc43dc21cb71ed77208389059566` |
| Predecessor | SI-2 / PR #676 merged; final implementation head `1ced8ea147f8119a424e9f44787cb7246ddb969d`; two formal review cycles |
| Named successor | **SI-4 — Ingest information-provider disposition** |
| Branch | `agent/surface-information-plan-graph-reference-v1` |
| Parallel lane | PR #674 remains OPEN / PARKED and read-only |
| Feature freeze | Unchanged through SI-6 |

### Backward-looking predecessor sync

This PR records:

```text
PR #676 merged
merge SHA            cd6b20ffe151dc43dc21cb71ed77208389059566
final implementation 1ced8ea147f8119a424e9f44787cb7246ddb969d
formal review cycles 2
successor             SI-3 Plan graph information reference implementation
```

Update SI-2 HANDOFF → COMPLETE; SURFACE-INTEGRATION roadmap → SI-2 DONE, SI-3 CURRENT; clarify SI-3 as Plan reference implementation with Build compatibility witness. Do not mark SI-3 complete. Do not churn `CONTRACT-surface-information-v1.md` or `ARCHITECTURE-surface-interaction-layer.md` unless a semantic contradiction is discovered.

---

# §3 Normative implementation design

See the dispatch body. Summary:

- Existing `WorldGraphLensProjectionProvider` owns `postWorldGraphProjection`.
- Narrow channel-handle context value is `SurfaceInformationChannel<WorldGraphProjection> | null` and changes only when the exact channel descriptor changes.
- One channel per exact desired World Graph request. Revision is observation metadata, never descriptor identity.
- Same-request refresh uses the same channel and a new observation ticket.
- Request identity change disposes the old channel and creates a new one.
- Mapping: LOADING / READY / EMPTY / UNAVAILABLE / INTEGRITY_ERROR. No `unrevisioned`. STALE is supported by the panel but this provider does not emit it in SI-3.
- Connected `PlanWorldGraphObjectsPanel` uses `useSyncExternalStore`. Graph information is not toolbar/editorTools props.
- Insert remains Plan-editor-owned and fails closed for STALE / unlocked-unsafe cases.
- Do not change `appChromeToolsPublicationSignature`.
- Do not modify Build production code.

---

# §4 Files in scope — exclusive write lease

| Action | Path | Purpose |
| --- | --- | --- |
| Create | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md` | This implementation/review contract |
| Modify | `Docs/Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md` | Backward-looking SI-2 completion sync |
| Modify | `Docs/Roadmaps/ROADMAP-surface-integration.md` | SI-2 DONE; SI-3 CURRENT; Plan reference / Build witness; freeze preserved |
| Create | `apps/live-control-ui/src/graphLens/worldGraphLensSurfaceInformation.ts` | Pure DungeonMind graph-lens descriptor + observation-state mapping |
| Create | `apps/live-control-ui/src/graphLens/worldGraphLensSurfaceInformation.test.ts` | Mapping, exact revision, empty/unavailable/integrity evidence |
| Modify | `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.ts` | Existing fetch owner publishes/disposes exact Surface Information channels |
| Modify | `apps/live-control-ui/src/graphLens/useWorldGraphLensProjection.test.tsx` | Provider/channel lifecycle, refresh ordering, descriptor replacement |
| Modify | `apps/live-control-ui/src/graphLens/index.ts` | Narrow channel-handle hook/type export |
| Create | `apps/live-control-ui/src/planSurface/components/PlanWorldGraphObjectsPanel.tsx` | Connected Edit rich panel consuming Surface Information |
| Create | `apps/live-control-ui/src/planSurface/components/PlanWorldGraphObjectsPanel.test.tsx` | State mapping, exact View, insert gates, channel subscription |
| Modify | `apps/live-control-ui/src/planSurface/components/PlanSurfaceCanvas.tsx` | Publish stable connected panel instead of projection-materialized ReactNode |
| Create | `apps/live-control-ui/src/planSurface/PlanSurfaceGraphInformation.integration.test.tsx` | Actual Plan → AppChrome/EditHost OC-020 regression witness |

Maximum additional write paths: **0**. No package or lockfile change is expected.

---

# §5 Explicitly out of scope / collision boundary

Do not modify:

```text
apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx
apps/live-control-ui/src/chrome/AppChrome.tsx
apps/live-control-ui/src/surfaceInteraction/**
apps/live-control-ui/src/surfaceInformation/**
apps/live-control-ui/src/buildSurface/**
apps/live-control-ui/src/agentInteraction/**
apps/live-control-ui/src/playSurface/**
apps/live-control-ui/src/api/**
apps/live_control_server/**
package.json / package-lock.json / root dependency config
Docs/Sources/design-agent/**
Docs/Roadmaps/ROADMAP-con-ready.md
```

PR #674 remains parked. SI-3 does not dispose or rebase #674.

---

# §6 Required adversarial and product witnesses

A. OC-020 owning-boundary: loading panel → verified node appears → zero new `onEditorToolsChange` after structural tools stabilize.
B. EMPTY: verified `nodes = []` at exact revision; not unavailable or integrity error.
C. UNAVAILABLE: dependency/request failure; no silent prior READY value.
D. INTEGRITY_ERROR: verification/revision failure; not EMPTY.
E. Same-scope revision refresh / late response: B accepted, late A rejected, visible revision remains B.
F. Descriptor replacement: old channel disposed; in-flight work cannot mutate the new channel.
G. Equivalent accepted observation: new generation, no semantic dedupe, no editorTools republication.
H. Panel mount continuity across same-descriptor refresh.
I. Build graph-reference regression remains green; Build is not migrated.

---

# §7 Evidence required to merge

From `apps/live-control-ui`:

```bash
npm test -- src/surfaceInformation/channel.test.tsx src/surfaceInformation/boundaries.test.ts
npm test -- src/graphLens/worldGraphLensSurfaceInformation.test.ts src/graphLens/useWorldGraphLensProjection.test.tsx
npm test -- src/planSurface/components/PlanWorldGraphObjectsPanel.test.tsx src/planSurface/PlanSurfaceGraphInformation.integration.test.tsx
npm test -- src/planSurface/PlanSurfaceShell.test.tsx src/planSurface/PlanSurfaceInsertChip.test.tsx
npm test -- src/buildSurface/reference/BuildReferenceCapability.test.tsx src/buildSurface/reference/buildBuildSurfaceInteractionPublication.test.ts
npm test -- src/agentInteraction/surfaceInteractionCompat.test.ts
npm test
npm run typecheck
npm run build
```

From repository root:

```bash
git diff --check
git diff --name-only cd6b20ffe151dc43dc21cb71ed77208389059566...HEAD
git diff cd6b20ffe151dc43dc21cb71ed77208389059566...HEAD -- \
  apps/live-control-ui/src/planSurface/PlanSurfaceShell.tsx \
  apps/live-control-ui/src/chrome/AppChrome.tsx \
  apps/live-control-ui/src/surfaceInteraction \
  apps/live-control-ui/src/surfaceInformation \
  apps/live-control-ui/src/buildSurface \
  apps/live-control-ui/src/agentInteraction \
  apps/live_control_server
```

Expected structural non-change: empty. Actual changed paths must reconcile exactly with §4.

Full-suite baseline rule: run the full suite on this head. If failures remain, rerun the same failure on base `cd6b20f…`, prove this head adds no failure, and record exact head/base results. New failures in surfaceInformation, graphLens, Plan, AppChrome/EditHost, Agent/Surface Interaction compatibility, or Build graph-reference regression are blockers.

---

# §8 Required review handback

Record identity, predecessor sync, provider contract, observation semantics, OC-020 witness, panel continuity, collision/boundary evidence, Build regression, and what remains false (Build adoption, Ingest disposition, cross-surface adoption, SI-6, freeze).

---

# §9 Acceptance rubric

See dispatch acceptance checklist. SI-4 remains the named successor. Feature freeze remains in force through SI-6.

---

# Stop conditions

Stop and rebrief if implementation requires modifying `PlanSurfaceShell.tsx`, `AppChrome.tsx`, `SurfaceInteractionPublication`, the SI-2 public contract, a second World Graph request, Build production, #674-owned paths, backend/API, lockfiles, `unrevisioned` for a missing DungeonMind revision, silent integrity→EMPTY/UNAVAILABLE mapping, or any path outside §4.

---

# Dispatch summary

```text
Flow: SURFACE-INTEGRATION
Slice: SI-3 — Plan Graph Surface Information reference implementation
Base: cd6b20ffe151dc43dc21cb71ed77208389059566
Branch: agent/surface-information-plan-graph-reference-v1
PR: SURFACE-INTEGRATION: make Plan graph information reactive
Successor: SI-4 — Ingest information-provider disposition
Feature freeze: remains in force through SI-6
```
