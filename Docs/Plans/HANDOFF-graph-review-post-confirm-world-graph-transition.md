---
pr_body_template: |
  ## Outcome

  After a terminal extract-promote confirm receipt, Graph Review replaces candidate/preview authority with the exact committed World Graph revision and opens affected objects by exact durable ID. Preview-union, gold, candidate labels, aliases, and head are never used as the committed result.

  ## Merge-ready invariant

  Every post-confirm Graph Review object presentation is addressed by exact durable node ID from an explicit World Graph projection pinned to `receipt.committedRevisionId` and `receipt.worldId`. Candidate/gold/preview-union labels never select, supplement, or substitute for committed identity.

  ## Evidence required to merge

  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Committed request uses receipt.worldId + revisionPin; no campaign remapping after receipt | `worldGraphSurfaceContext` | vitest `worldGraphSurfaceContext.test.ts` | {{RESULT}} |
  | Receipt adoption + response validation + affected-ID normalize | `graphReviewCommittedAuthority` | vitest `graphReviewCommittedAuthority.test.ts` | {{RESULT}} |
  | Conflicting candidate vs durable labels: durable wins by exact ID | Graph Review live/committed panels | vitest committed panel + extract-promote sheet + live projection | {{RESULT}} |
  | Terminal outcomes (committed, already_applied, published_audit_degraded) install committed authority; retries do not re-confirm | Extract promote sheet + live state | vitest ExtractPromoteSheet + WorkbenchModule | {{RESULT}} |
  | Prepare/confirm disabled after terminal receipt for binding | Session toolbar / exact-run chrome | vitest SessionToolbar / WorkbenchModule | {{RESULT}} |
  | Stale in-flight committed loads suppressed via generation counter | Live review state | vitest WorkbenchModule deferred-promise stale | {{RESULT}} |
  | Shared card regressions remain green | graphObjectCard | vitest GraphObjectProjectionCard + GraphObjectCard | {{RESULT}} |
  | Typecheck + build | live-control-ui | `npm run typecheck` / `npm run build` | {{RESULT}} |

  ## Scope and explicit deferrals

  - Base: `caa46f43971fc51f06e8805201c95cbd64ddc638`
  - Head: `{{HEAD_SHA}}`
  - Changed paths: `{{ACTUAL_PATHS}}`
  - Verification: `{{COMMANDS_AND_RESULTS}}`
  - Dogfood: {{DOGFOOD_STATE}}
  - Deferred: exact-run candidate-review projection replacement; preview-union infrastructure retirement; cache/invalidation/telemetry; backend publication changes

  ## Evidence produced

  ### Automated
  {{AUTOMATED}}

  ### Adversarial
  {{ADVERSARIAL}}

  ### Regression
  {{REGRESSION}}

  ### Manual / dogfood
  {{DOGFOOD}}

  ## Gaps, waivers, and stop conditions
  {{GAPS}}
---

# HANDOFF — PR380C Graph Review post-confirm World Graph authority transition

**Created:** 2026-07-27, America/Denver.
**Status:** ACTIVE — dispatch exactly one product authority migration.
**Canonical handoff path:** `Docs/Plans/HANDOFF-graph-review-post-confirm-world-graph-transition.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Implementation base:** `caa46f43971fc51f06e8805201c95cbd64ddc638` — `main` after PR380B (#437) merge.
**Suggested branch:** `agent/graph-review-post-confirm-world-graph-transition`
**Predecessor:** PR380B / GitHub PR #437 (shared `GraphObjectProjectionCard` + World Graph surface context) and extract-promote confirm receipt `dmb_extract_promote_confirm_v2`.
**Product anchors:** Graph Review post-confirm must read durable World Graph identity, not candidate/preview labels; successor named from PR380B deferred list.
**Operating rule:** reconstruct from current main; implement only §4 allowlist paths.

> **Dispatch gate:** PASSED — receipt has `worldId`, `parentRevisionId`, `committedRevisionId`, `outcome`, `affectedObjectIds`. Generic projection route supports `revisionPin`.
>
> This checked-in handoff is the complete authority. The worker must not compress, omit, replace, or rewrite it before implementation. The PR description must use the frontmatter skeleton and remain a truthful merge contract; it cannot substitute for the handoff.

## Shared vocabulary

| Term | Definition |
|---|---|
| **Terminal confirm receipt** | `ExtractPromoteConfirmReceipt` with outcome `committed`, `already_applied`, or `published_audit_degraded`. |
| **Committed authority** | Exact World Graph projection pinned to `committedRevisionId` for `receipt.worldId`, opened by exact `affectedObjectIds`. |
| **Candidate authority** | Preview-union / gold / live candidate projection used before terminal confirm. |
| **Binding** | Catalog (campaign/session/live-run) or exact-run identity that owns the committed transition state. |

## §0 Capability decomposition decision

PR380C is a Graph Review post-confirm **read-authority transition**, not a publication rewrite, not preview-union retirement, and not a candidate-review projection redesign.

| Candidate outcome | Independently useful? | Decision |
|---|---|---|
| After terminal receipt, load exact committed World Graph revision and present affected objects by ID | Yes | Include |
| Auto-load for `published_audit_degraded` (same as committed/already_applied) | Required for one authority | Include |
| Hide/disable prepare/confirm after terminal receipt for current binding | Required | Include |
| Exact ID navigation on committed panel via shared card | Required | Include |
| Stale suppression for overlapping committed loads | Required | Include |
| Replace Graph Review live lane with exact-run candidate projection | Yes alone | Successor |
| Delete preview-union infrastructure | Yes alone | Successor |
| Backend confirm/audit changes | Yes alone | Out of scope — STOP if needed |

## §1 Mission

After a terminal extract-promote confirm receipt, Graph Review replaces candidate authority with the exact committed World Graph revision and opens affected objects by exact durable ID.

**Invariant:** Every post-confirm Graph Review object presentation is addressed by exact durable node ID from an explicit World Graph projection pinned to `receipt.committedRevisionId` and `receipt.worldId`. Preview-union, gold, candidate labels, aliases, and head never select, supplement, or substitute for committed identity.

### Mission falsification test

This is not one slice if implementation must also:

- change backend confirm/audit contracts;
- delete or retire preview-union storage/routes;
- replace the live candidate lane with a new exact-run candidate-review projection;
- invent live selection when an affected ID is missing from the committed projection;
- remapping `worldId` from campaign after a receipt that already carries `worldId`.

## §2 Context, authority, and boundaries

| Field | Content |
|---|---|
| Parent authority | PR380B successor split; extract-promote confirm v2 receipt; World Graph generic projection + `revisionPin` |
| Base revision | `caa46f43971fc51f06e8805201c95cbd64ddc638` |
| Exact input consumed | `ExtractPromoteConfirmReceipt` (`worldId`, `parentRevisionId`, `committedRevisionId`, `outcome`, `affectedObjectIds`) |
| Named successors | Exact-run candidate-review projection; preview-union retirement; PR380D cache/telemetry |
| Explicit non-goals | Backend edits; gold authoring; Recap/Build changes; inventing missing IDs |

Read in order before editing:

1. This handoff
2. `apps/live-control-ui/src/api/types.ts` — `ExtractPromoteConfirmReceipt`
3. `graphReviewLiveReviewState.ts` — `reloadCommittedWorldProjection`, `selectDurableObjectIds`
4. `GraphReviewExtractPromoteSheet.tsx` — sheet-local `applyCommittedRevision` + audit-degraded skip
5. `BuildGraphObjectContext.tsx` — generation stale guard + shared card pattern
6. `worldGraphSurfaceContext.ts` — neutral request builders

## §3 Observable-path inventory

| Path | Current behavior | Required behavior | Owning boundary |
|---|---|---|---|
| Confirm → `committed` / `already_applied` | Reload World Graph then `selectDurableObjectIds` against gold/preview | Adopt receipt → load pinned committed projection → open exact IDs from that projection | live review state + sheet |
| Confirm → `published_audit_degraded` | Skip auto-reload; manual reload CTA only | Auto-load committed authority same as other terminal outcomes | sheet + live state |
| Missing affected ID in committed projection | Fabricate live selection via `selectDurableObjectIds` | Fail closed / show missing; never fabricate from gold/preview | committed panel / authority |
| Conflicting labels (Candidate Hesta vs Hesta Ironroot) | Gold/preview label can win | Durable committed label wins by exact ID | characterization + panel |
| Binding change (catalog/exact) | N/A / leak risk | Clear committed state | workbench + live state |
| Same-binding refresh | N/A | Preserve committed authority | workbench |
| Retry after terminal receipt | Must not re-confirm | Reload committed projection only | sheet / toolbar |
| Stale overlapping loads | Partial | Generation counter suppresses stale | live review state |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-graph-review-post-confirm-world-graph-transition.md` | Canonical dispatch authority |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts` | Add `buildGraphReviewCommittedProjectionRequest` |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.test.ts` | Prove receipt.worldId, revisionPin, fail-closed mapping |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewCommittedAuthority.ts` | Binding types, adoption/response validation, ID normalize, phase vocabulary |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewCommittedAuthority.test.ts` | Unit proofs for authority helpers |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts` | Own committed transition; exact read/retry; generation stale guard; remove post-confirm gold/preview authority path |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveStateContext.tsx` | Expose committed APIs via existing provider spread |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.tsx` | Committed panel: shared card + exact ID nav + receipt metadata + loading/error/retry |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.test.tsx` | Label conflict + exact ID proofs |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx` | Delegate `adoptCommittedReceipt`; remove sheet-local gold/preview apply; auto-load degraded; no re-confirm on retry |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx` | Characterization + updated terminal flows |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx` | Show committed panel when phase ≠ candidate for binding |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx` | Committed vs candidate switching |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewSessionToolbar.tsx` | Hide/disable prepare/confirm after terminal receipt |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Typed catalog/exact bindings; clear on change; preserve on refresh; committed primary in exact-run |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | Binding clear/preserve + deferred stale |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Minimal committed panel styling only if required |

**Bounded discovery exception:** Maximum 3 additional paths under `apps/live-control-ui/src/planSurface/graphReviewWorkbench/` or `apps/live-control-ui/src/worldGraph/` for colocated fixtures/helpers required by owning tests. Stop and report if backend or out-of-tree production paths are required.

## §5 Explicitly out of scope

| Capability | Why |
|---|---|
| Backend extract-promote / World Graph routes | Dispatch gate already satisfied |
| Recap / Build / Ingest production changes | Owned by PR380B / other slices |
| Preview-union deletion | Successor |
| Exact-run candidate-review projection redesign | Successor |
| Gold authoring commit path | Separate authority |
| Fabricating selection when ID missing | Forbidden by invariant |

## §6 Implementation contract

### Request builder (`worldGraphSurfaceContext.ts`)

`buildGraphReviewCommittedProjectionRequest`:

- Pure helper.
- Uses `receipt.worldId` as `worldId` (no remapping after receipt).
- Fail closed if campaign→world map is missing or disagrees with `receipt.worldId`.
- `scopeMode: "campaign"`.
- Focus: session when `sessionId` present, else `{ kind: "none", sessionId: null }`.
- `revisionPin = receipt.committedRevisionId`.

### Authority module (`graphReviewCommittedAuthority.ts`)

- Binding types for catalog vs exact.
- Receipt adoption validation (required fields, terminal outcomes).
- Response validation (revision match, world match).
- Affected ID normalize: trim + dedupe preserving order.
- State vocabulary: `candidate | loading | ready | error`.

### Live review state

- Own committed transition state for current binding.
- Exact read + retry of committed projection.
- Stale suppression via generation counter (Build pattern).
- Remove post-confirm use of `selectDurableObjectIds` against gold/preview as authority.
- Keep `selectDurableObjectIds` out of post-confirm flow (or gut post-confirm misuse).

### Sheet

- On terminal outcomes (`committed`, `already_applied`, `published_audit_degraded`) call provider `adoptCommittedReceipt`.
- Remove sheet-local `applyCommittedRevision` that selects from gold/preview.
- Retries reload committed authority only — must not re-confirm.
- Auto-load for `published_audit_degraded`.

### Panels / chrome

- `GraphReviewCommittedProjectionPanel`: `GraphObjectProjectionCard` + `adaptWorldGraphNodeView`; exact ID nav; receipt metadata; loading/error/retry.
- `GraphReviewLiveProjectionPanel`: when committed phase ≠ `candidate` for current binding, show committed panel instead of candidate.
- `GraphReviewSessionToolbar`: hide/disable prepare/confirm after terminal receipt for binding.
- `GraphReviewWorkbenchModule`: typed bindings; clear on binding change; preserve on same-binding refresh; committed primary in exact-run mode; deferred-promise stale tests.

### Demolition

- Stop using `reloadCommittedWorldProjection` result only for verify-then-discard + `selectDurableObjectIds` against gold/preview.
- Auto-load for `published_audit_degraded`.
- No fabricate live selection when ID missing.

## §6A State matrix

| Phase | Meaning | UI |
|---|---|---|
| `candidate` | Pre-confirm / no adopted receipt for binding | Live/gold candidate panels |
| `loading` | Committed projection in flight | Loading + receipt metadata if known |
| `ready` | Pinned projection installed | Committed panel + exact IDs |
| `error` | Load/validation failed | Error + retry (no re-confirm) |

## §6B Identity matrix

| Field | Source of truth post-confirm |
|---|---|
| worldId | `receipt.worldId` |
| revision | `receipt.committedRevisionId` (must match projection snapshot) |
| object open | exact `affectedObjectIds` present in committed projection nodes |
| labels | committed projection node labels only |

## §7 Verification ownership map and commands

Characterization gate (first implementation commit after docs may be red):

- Conflicting labels: candidate/gold `object-1` = `Candidate Hesta`, committed = `Hesta Ironroot` → post-confirm UI must show durable label.
- `published_audit_degraded` currently skips auto-load (document then fix).

Evidence commands (must run and record):

```bash
cd apps/live-control-ui
npx vitest run src/worldGraph/worldGraphSurfaceContext.test.ts \
  src/planSurface/graphReviewWorkbench/graphReviewCommittedAuthority.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx
npx vitest run src/graphObjectCard/GraphObjectProjectionCard.test.tsx \
  src/graphObjectCard/GraphObjectCard.test.tsx
npm run typecheck
npm run build
cd ../..
git diff --check
git diff --name-only caa46f43971fc51f06e8805201c95cbd64ddc638...HEAD
```

## §8 Required implementation handback

Return: HEAD SHA, commit list, test command results, PR URL, gaps/stop conditions, actual changed paths.

## §9 Acceptance rubric

Merge only when:

1. Docs handoff committed.
2. Characterization proves label conflict / authority misuse on base behavior (or documents it then turns green).
3. All §7 commands green (or baseline-identical failures reported accurately).
4. No production paths outside §4 / bounded exception.
5. PR body uses frontmatter skeleton with real `{{RESULT}}` fills.
6. Base remains ancestor of HEAD.

## §10 Reviewer protocol

Review against §1 invariant first. Reject any path that reopens gold/preview/`selectDurableObjectIds` as post-confirm authority.

## §11 Re-review protocol

If allowlist is insufficient or backend changes are required: STOP, report, do not expand scope silently.

## Commits expected

Logical commits: docs → characterization → helpers → provider/state → panel/wiring → fixes.

Do not push until evidence is green; then `git push -u origin HEAD` and `gh pr create` against base `caa46f43`.
