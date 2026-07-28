---
slice_id: PR380C
title: Graph Review post-confirm World Graph authority transition
status: ACTIVE
canonical_path: Docs/Plans/HANDOFF-graph-review-post-confirm-world-graph-transition.md
implementation_base: caa46f43971fc51f06e8805201c95cbd64ddc638
suggested_branch: agent/graph-review-post-confirm-world-graph-transition
pr_body_template: |
  ## Outcome

  A GM who confirms a prepared Graph Review proposal sees Graph Review replace candidate review authority with the exact committed World Graph revision and can open the affected durable objects by exact ID.

  ## Merge-ready invariant

  Once Graph Review receives a terminal commit receipt for the current review binding, that receipt and its exact committed World Graph revision are the only post-confirm authority: the surface must either render objects from a campaign-scoped projection whose world, campaign, and revision exactly match the receipt, or preserve the receipt in a durable-read-unavailable state with an exact-revision retry; it must never present preview-union, gold-fixture, exact-run candidate, label-derived, alias-derived, or current-head data as the committed result.

  ## Evidence required to merge

  | Guarantee | Owning boundary | Required evidence | Result |
  |---|---|---|---|
  | Terminal confirm receipt replaces candidate authority for the same review binding | Graph Review workflow/provider | Catalog-run and exact-run integration tests | {{RESULT}} |
  | The committed projection request is pinned to the receipt revision and exact campaign/world scope | World Graph request adapter + provider | Request-shape contract tests | {{RESULT}} |
  | Affected objects and relationships resolve only from the committed projection by exact ID | Committed projection panel | Adversarial card/navigation tests using conflicting candidate and durable labels | {{RESULT}} |
  | Post-commit read failure preserves the receipt and never falls back to candidate state | Provider + committed panel | Failure/retry tests | {{RESULT}} |
  | Run switches suppress stale committed-projection completions while same-binding refreshes preserve the transition | Provider binding lifecycle | Deferred-promise interleaving tests | {{RESULT}} |
  | Existing pre-confirm preview review remains usable and no backend/publication contract changes | Existing Graph Review surfaces + diff boundary | Regression suite and allowlist inspection | {{RESULT}} |

  ## Scope and explicit deferrals

  - Base: `caa46f43971fc51f06e8805201c95cbd64ddc638`
  - Head: `{{HEAD_SHA}}`
  - Current slice ID: PR380C (roadmap/content ID, not a predicted GitHub PR number)
  - Changed paths: `{{ACTUAL_PATHS}}`
  - Paths outside the handoff allowlist: `{{NONE_OR_STOP_REPORT}}`
  - Confirmation, Kernel publication, contribution persistence, and receipt schemas are reused unchanged.
  - Preview-union remains the pre-confirm candidate-review source until the exact-run candidate-review successor replaces it.
  - Deferred: committed recap-prose overlay, browser-reload receipt rehydration, preview-union retirement, cache/telemetry, Ingest redesign, worldbuilding authority elevation, agent continuity, Build/Plan/Play changes.

  ## Evidence produced

  ### Automated
  {{COMMANDS_AND_RESULTS}}

  ### Adversarial
  {{INTERLEAVING_AND_MISMATCH_RESULTS}}

  ### Regression
  {{PRE_CONFIRM_AND_SHARED_CARD_RESULTS}}

  ### Manual / dogfood
  {{DOGFOOD_RESULT}}

  ## Gaps and stop conditions
  {{NONE_OR_EXACT_GAP_REPORT}}
---

# HANDOFF — PR380C Graph Review post-confirm World Graph authority transition

**Created:** 2026-07-27, America/Denver.
**Status:** ACTIVE — dispatch exactly one product authority migration.
**Canonical handoff path:** `Docs/Plans/HANDOFF-graph-review-post-confirm-world-graph-transition.md`
**Repository:** `Drakosfire/DungeonMindBuddy`
**Implementation base:** `caa46f43971fc51f06e8805201c95cbd64ddc638` — `main` after PR380B (#437) merge.
**Suggested branch:** `agent/graph-review-post-confirm-world-graph-transition`
**Slice ID:** PR380C (roadmap/content ID, not a predicted GitHub PR number)
**Predecessor:** PR380B / GitHub PR #437 (shared `GraphObjectProjectionCard` + World Graph surface context) and extract-promote confirm receipt `dmb_extract_promote_confirm_v2`.
**Product anchors:** Graph Review post-confirm must read durable World Graph identity, not candidate/preview labels; successor named from the PR380B deferred list.
**Operating rule:** reconstruct from current main; implement only §4 allowlist paths.

> **Dispatch gate:** Dispatch is prohibited until the worker has read the authorities in §2, confirmed that `caa46f43971fc51f06e8805201c95cbd64ddc638` is an ancestor of current main, inspected any base movement in the allowlisted Graph Review files, and verified that the existing confirm receipt still exposes the exact world, parent revision, committed revision, outcome, and affected durable object IDs required below.
>
> This checked-in handoff is the complete implementation authority. The worker must not compress it into “load the graph after merge,” reconstruct the abandoned 101-file PR #380 branch wholesale, or silently add adjacent cleanup. The PR body is a truthful evidence summary, not a replacement for this document. A compressed rewrite that drops binding, retry, persistence, or adversarial matrices is a merge blocker even if the code is directionally sound.

## Shared vocabulary

| Term | Definition |
| --- | --- |
| **Terminal confirm receipt** | `ExtractPromoteConfirmReceipt` (`schema: dmb_extract_promote_confirm_v2`) whose `outcome` is one of `committed`, `already_applied`, or `published_audit_degraded`. |
| **Committed authority** | The only post-confirm object authority: an exact campaign-scoped World Graph projection pinned to `receipt.committedRevisionId` for `receipt.worldId`, with affected objects opened by exact `affectedObjectIds`. |
| **Candidate authority** | Pre-confirm review lens: preview-union / gold fixture / exact-run candidate presentation used until a terminal receipt is adopted for the current binding. |
| **Review binding** | The typed identity that owns committed-transition state: either `catalog_run` (run + campaign + session) or `exact_run` (run + source artifact + campaign/session scope). |
| **Binding key** | Stable string produced by `catalogRunBindingKey` / `exactRunBindingKey`; equality of bindings is key+kind, never partial field match. |
| **Committed phase** | Provider-owned vocabulary: `candidate` \| `loading` \| `ready` \| `error` for the active binding. |
| **Durable-read-unavailable** | Post-confirm error state that preserves the adopted receipt and offers exact-revision retry of the committed projection only — never re-confirm, never candidate fallback. |
| **Partially durable failure** | Publication already produced a terminal receipt, but the subsequent committed projection read failed; UI must keep the receipt and retry the read, not the confirm. |
| **Generation counter** | Monotonic token used to suppress stale in-flight committed-projection completions after binding change or superseded adopt. |
| **Exact ID** | Durable World Graph node ID string; never a label, alias, gold object key reinterpretation, or fabricated live selection. |
| **Prepared identity** | The prepare response fields (`proposalId`, `proposalDigest`, `parentRevisionId`, `worldId`, `runId`, `campaignId`, `sessionId`) checked against the receipt and active binding on adoption. |

## §0 Capability decomposition decision

PR380C is a Graph Review post-confirm **read-authority transition**, not a publication rewrite, not preview-union retirement, not an exact-run candidate-review redesign, and not a Recap/Build/Ingest migration.

| Candidate outcome | Independently useful? | Public/durable contract changed? | User or operator surface changed? | Failure model changed? | Independently testable or revertible? | Decision |
| --- | --- | --- | --- | --- | --- | --- |
| After terminal receipt, Graph Review loads the exact committed World Graph revision and presents affected objects by exact ID | Yes | Frontend consumes existing generic projection + existing confirm receipt; no backend contract change | Yes | Yes | Yes | Include |
| Auto-load committed authority for `published_audit_degraded` the same as `committed` / `already_applied` | No alone; required so audit degradation cannot leave candidate authority in place | No | Yes | Yes | Yes | Include under the same invariant |
| Hide/disable prepare/confirm chrome after a terminal receipt for the current binding | No alone; required to prevent accidental re-confirm | No | Yes | Yes | Yes | Include under the same invariant |
| Exact-ID navigation on the committed panel via shared `GraphObjectProjectionCard` | No alone; required to prevent a second post-confirm object model | Shared UI seam only | Yes | Yes | Yes | Include under the same invariant |
| Stale suppression for overlapping committed loads via generation counter | No alone; required for truthful binding lifecycle | No | Yes | Yes | Yes | Include under the same invariant |
| Typed catalog_run / exact_run bindings with scope in the key; clear on binding change; preserve on same-binding refresh | No alone; required so receipts cannot leak across runs or scopes | No | Yes | Yes | Yes | Include under the same invariant |
| Post-commit read failure preserves receipt and retries exact committed read only | No alone; required for partially durable failure honesty | No | Yes | Yes | Yes | Include under the same invariant |
| Demolish post-confirm `selectDurableObjectIds` / gold/preview authority path | No alone; demolition required by the migration | No | Yes | Yes | Yes | Include under the same invariant |
| Relationship traversal on committed cards uses exact target IDs within the committed projection only | No alone; required to keep navigation coherent with authority | Shared UI seam only | Yes | Yes | Yes | Include under the same invariant |
| Replace Graph Review live lane with a direct exact-ExtractionRun candidate-review projection | Yes | Yes | Yes | Yes | Yes | Successor: exact-run-candidate-review-projection |
| Delete preview-union infrastructure, Graph Preview routes, or run-registry requirements | Yes | Yes | Yes/operational | Yes | Yes | Successor: retire-preview-union-review-materialization |
| Backend confirm/audit/Kernel publication contract changes | Yes | Yes — durable publication authority | Yes | Yes | Yes | Reject / STOP if needed |
| Committed recap-prose overlay in Graph Review | Yes | Frontend presentation expansion | Yes | Minor | Yes | Deferred successor |
| Browser-reload receipt rehydration / durable UI persistence of receipts | Yes | Persistence contract | Yes | Yes | Yes | Deferred successor |
| Projection cache, request coalescing, revision invalidation, telemetry | Yes | Yes | Indirectly | Yes | Yes | Successor PR380D |
| Ingest wizard redesign or extraction-control removal | Yes | Product workflow | Yes | Yes | Yes | Successor PR380E |
| Worldbuilding authority elevation / Build/Plan/Play changes | Yes | Cross-surface | Yes | Yes | Yes | Explicitly deferred |
| Agent Interaction continuity / cross-route ledger | Yes | Thread/context contract | Yes | Yes | Yes | Reject; hoisted-agent successor |
| Fabricate live selection when an affected ID is missing from the committed projection | Yes — but false | Invents hybrid identity | Yes | Yes | Yes | Reject from this slice |
| Remap `worldId` from campaign after a receipt that already carries `worldId` | Yes — but false | Invents second world authority | Yes | Yes | Yes | Reject from this slice |
| Fall back to current head when pinned revision read fails | Yes — but false | Breaks exact-revision invariant | Yes | Yes | Yes | Reject from this slice |
| Keep exact-run candidate prose/assertions as primary chrome after commit | Yes — but false | Leaves candidate authority visible | Yes | Yes | Yes | Reject from this slice |
| Overlay candidate nodes onto the committed projection response | Yes — but false | Invents hybrid authority | Yes | Yes | Yes | Reject from this slice |

**Selected capability:** A GM who confirms a prepared Graph Review proposal sees Graph Review replace candidate review authority with the exact committed World Graph revision for the current review binding and can open the affected durable objects by exact ID, with partially durable read failure preserving the receipt and offering exact-revision retry only.

**Why the included rows share one invariant:** every changed seam establishes the same authority claim — once a terminal confirm receipt is adopted for the current binding, that receipt and its exact committed revision are the only post-confirm authority. Candidate, gold, preview-union, label, alias, and head sources may remain available for pre-confirm review or diagnostics, but they can never select, supplement, or substitute for committed identity.

**Named successors still false after this slice:**

- exact-run-candidate-review-projection — replace Graph Review’s preview-union / gold candidate lane with a direct exact-ExtractionRun review lens.
- retire-preview-union-review-materialization — remove preview-union lifecycle requirements after all consumers move.
- PR380D — cache, coalescing, invalidation, telemetry.
- Committed recap-prose overlay.
- Browser-reload receipt rehydration.
- PR380E / PR380F / agent-continuity / Build-Plan-Play authority changes.

## §1 Mission and merge-ready invariant

### Mission

A GM who confirms a prepared Graph Review proposal sees Graph Review replace candidate review authority with the exact committed World Graph revision and can open the affected durable objects by exact ID.

### Merge-ready invariant

> Once Graph Review receives a terminal commit receipt for the current review binding, that receipt and its exact committed World Graph revision are the only post-confirm authority: the surface must either render objects from a campaign-scoped projection whose world, campaign, and revision exactly match the receipt, or preserve the receipt in a durable-read-unavailable state with an exact-revision retry; it must never present preview-union, gold-fixture, exact-run candidate, label-derived, alias-derived, or current-head data as the committed result.

### Mission falsification test

```text
This is not one slice if implementation must also:
- change backend confirm, audit, Kernel publication, or contribution-persistence contracts;
- delete or retire preview-union storage/routes/Graph Preview infrastructure;
- replace the live candidate lane with a new exact-run candidate-review projection;
- invent live selection when an affected ID is missing from the committed projection;
- remap worldId from campaign after a receipt that already carries worldId;
- fall back to current head, gold, preview-union, or candidate labels on committed-read failure;
- re-confirm when only the committed projection read failed;
- persist or rehydrate receipts across browser reload;
- add committed recap-prose overlay, cache/telemetry, Ingest redesign, or Build/Plan/Play changes;
- elevate worldbuilding write authority or Agent Interaction continuity.
```

### Pre-dispatch critique table

| Critique | Answer | Disposition |
| --- | --- | --- |
| Is this just “reload World Graph after confirm”? | No — current code reloads then discards authority into gold/preview `selectDurableObjectIds`. The slice installs receipt-pinned committed authority. | Keep |
| Can published_audit_degraded stay manual-only? | No — leaving candidate authority after a terminal degraded receipt falsifies the invariant. | Include auto-load |
| Is binding identity only runId? | No — catalog needs campaign+session; exact_run needs sourceArtifactId plus campaign/session scope so scope changes clear stale receipts. | Include typed bindings |
| Can retry mean “Retry exact confirm”? | No — after terminal receipt, retry is exact committed projection read only. | Include partially durable failure matrix |
| Do we need backend changes for revisionPin? | No — gate already true on main. | STOP if false |
| Is exact-run candidate chrome allowed under the committed panel? | No — candidate presentation must disappear once phase ∈ {loading, ready, error}. | Include panel switch |
| Is browser-reload persistence required? | Useful later, not required for one truthful in-session transition. | Defer |
| Can adoption happen after catalog refresh? | No — refresh can change/remove the binding; freeze binding and adopt first. | Include ordering rule |
| Is characterization optional? | No — conflicting candidate vs durable labels must prove the authority bug before/with the fix. | Include §8.2 |

## §2 Context, authority, and boundaries

### Parent authority — read order

Read in this order before editing:

1. This checked-in handoff (complete authority)
2. `Docs/Plans/HANDOFF-pr380b-world-graph-recap-ui-migration.md` — predecessor split naming PR380C; shared card + World Graph surface context patterns
3. `Docs/Design/DECISION-graph-lens-projection-boundary.md`
4. `apps/live-control-ui/src/api/types.ts` — `ExtractPromoteConfirmReceipt`, prepare/confirm types, `WorldGraphProjection` / request shapes
5. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts` — `reloadCommittedWorldProjection`, `selectDurableObjectIds` (post-confirm misuse to demolish)
6. `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx` — sheet-local `applyCommittedRevision` + audit-degraded skip
7. `apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx` — generation stale guard + shared card consumption pattern
8. `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts` — neutral request builders
9. `apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx` — shared exact-ID card renderer
10. Current base `caa46f43971fc51f06e8805201c95cbd64ddc638` implementation and owning tests

### Repository rules

- `AGENTS.md`
- `.cursor/rules/external-agent-pr-loop.mdc`
- `.cursor/skills/external-agent-pr-loop/SKILL.md`
- `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`
- Existing frontend TypeScript, Vitest, and projection-boundary conventions
- Python backend remains out of scope; if touched, STOP

### Authority precedence

1. This checked-in handoff
2. Existing extract-promote confirm v2 receipt contract on main
3. Existing generic World Graph projection + `revisionPin` contract on main
4. PR380B shared card / surface-context patterns (consume, do not rewrite)
5. Current main implementation and tests on base
6. Chat summaries and compressed task prompts (non-authoritative)

Compressed worker prompts, PR bodies, and “summary” rewrites are never higher authority than this document.

### Preconditions already true on main

- Confirm receipt schema includes `worldId`, `parentRevisionId`, `committedRevisionId`, `outcome`, `affectedObjectIds`.
- Terminal outcomes are `committed`, `already_applied`, `published_audit_degraded`.
- Generic `POST /api/live/world-graph/projection` accepts `revisionPin`.
- Shared `GraphObjectProjectionCard` + `adaptWorldGraphNodeView` / neutral World Graph adapter exist (PR380B).
- `worldGraphSurfaceContext` provides campaign→world mapping helpers for other surfaces.
- Graph Review prepare/confirm publication path already works; this slice does not change it.
- Preview-union / gold candidate review remains the pre-confirm lens until a successor replaces it.
- BuildGraphObjectContext already demonstrates generation-counter stale suppression for exact World Graph reads.

### Correctness gap on base

| Gap | Current false behavior | Required true behavior |
| --- | --- | --- |
| Post-confirm authority | Reload World Graph, then select durable IDs via gold/preview | Adopt receipt → pin committed projection → open exact IDs from that projection |
| `published_audit_degraded` | Skip auto-reload; manual path only | Auto-load committed authority like other terminal outcomes |
| Missing affected ID | Fabricate live selection via `selectDurableObjectIds` | Fail closed / unresolved; never fabricate |
| Conflicting labels | Candidate/gold label can win | Durable committed label wins by exact ID |
| Post-commit read failure | Can surface “Retry exact confirm” / unknown_result | Preserve receipt; retry committed read only |
| Exact-run after commit | Candidate prose/assertions remain primary; committed appended | Candidate chrome replaced by committed panel |
| Binding scope | Weak/partial identity risk | Typed keys including campaign/session (and exact source artifact) |
| Adopt vs refresh ordering | Refresh can precede freeze | Freeze binding and adopt before catalog refresh side effects |

### Architectural decision

Install a Graph-Review-owned **committed authority** state machine bound to a typed review binding. Confirmation remains the existing publication action. The UI transition is: terminal receipt adoption → pinned World Graph read → exact-ID presentation, with fail-closed validation and stale suppression. Do not invent a hybrid candidate+committed authority.

Reference patterns already on main (consume, do not copy blindly):

- `BuildGraphObjectContext.tsx` for committed card + generation stale guard
- `reloadCommittedWorldProjection` currently at `graphReviewLiveReviewState.ts` — replace with full authority install
- `selectDurableObjectIds` — MUST NOT be post-confirm authority
- Sheet `applyCommittedRevision` + audit-degraded skip in `GraphReviewExtractPromoteSheet.tsx` — demolish

### Exact inputs consumed

| Input | Shape | Consumer rule |
| --- | --- | --- |
| Terminal confirm receipt | `ExtractPromoteConfirmReceipt` | Required fields must be present and terminal; becomes frozen authority token for the binding |
| Prepared response (optional but required when available) | prepare fields listed in vocabulary | Must match receipt proposal/world/parent and binding run/campaign/session |
| Active review binding | `catalog_run` or `exact_run` | Owns phase/receipt/projection; change clears; same-binding refresh preserves |
| Campaign→world map | Existing shared helper | Used only to fail closed if map missing/disagrees with `receipt.worldId`; never remaps after receipt |
| Committed projection response | `WorldGraphProjection` | Must match receipt world, request campaign, pinned revision, admissibility, focus, scopeMode |
| Affected object IDs | `receipt.affectedObjectIds` | Normalize trim+dedupe preserve order; open only exact keys present in committed nodes |

### What remains false after this slice

- Exact-run candidate-review projection redesign
- Preview-union retirement
- Backend publication/audit changes
- Browser-reload receipt rehydration
- Committed recap-prose overlay
- Cache/telemetry (PR380D)
- Ingest redesign; worldbuilding elevation; agent continuity; Build/Plan/Play production changes
- Gold authoring commit path
- Cross-surface Recap automatic refresh onto the new revision as a Graph Review obligation

### Base movement rule

Base `caa46f43971fc51f06e8805201c95cbd64ddc638` must remain an ancestor of HEAD. Do not rebase onto unrelated worktrees. Do not cherry-pick old integration branches wholesale. Reconstruct from current main.

## §3 Observable-path inventory

| # | Observable path | Current behavior on base | Required behavior | Owning boundary | Proof |
| --- | --- | --- | --- | --- | --- |
| 1 | Confirm → `committed` | Reload WG; select IDs via gold/preview | Adopt receipt; load pinned projection; open exact IDs | live review state + sheet | Workbench + ExtractPromote tests |
| 2 | Confirm → `already_applied` | Same family as committed | Same committed-authority install | sheet + live state | ExtractPromote tests |
| 3 | Confirm → `published_audit_degraded` | Skip auto-reload | Auto-load committed authority | sheet + live state | Characterization then fix |
| 4 | Affected ID missing in committed projection | Fabricate via `selectDurableObjectIds` | Unresolved/missing; keep other exact hits; no fabricate | committed panel / authority | Panel + authority tests |
| 5 | Conflicting labels (`Candidate Hesta` vs `Hesta Ironroot`) | Gold/preview can win | Durable committed label by exact ID | characterization + panel | Committed panel + sheet tests |
| 6 | Catalog binding change (run/campaign/session) | Leak risk | Clear committed state | workbench + live state | WorkbenchModule tests |
| 7 | Exact-run binding change (run/source/campaign/session) | Leak risk | Clear committed state | workbench + live state | WorkbenchModule tests |
| 8 | Same-binding refresh | Unspecified | Preserve committed authority | workbench | WorkbenchModule tests |
| 9 | Retry after terminal receipt | May re-confirm | Reload committed projection only | sheet / toolbar / provider | Failure/retry tests |
| 10 | Stale overlapping committed loads | Partial | Generation counter suppresses stale | live review state | Deferred-promise tests |
| 11 | Exact-run primary chrome after commit | Candidate remains visible | Committed panel replaces candidate when phase ≠ candidate | LiveProjectionPanel + Workbench | Panel switch tests |
| 12 | Prepare/confirm chrome after terminal receipt | May remain enabled | Hide/disable for current binding | SessionToolbar / exact-run chrome | Toolbar / Workbench tests |
| 13 | Relationship navigation on committed card | Risk of label/alias | Exact target ID within committed projection only | CommittedProjectionPanel | Adversarial nav tests |
| 14 | Pre-confirm candidate review | Works via preview/gold | Remains usable until terminal receipt for binding | existing Graph Review | Regression suite |
| 15 | Shared card regressions | Green on main | Remain green | graphObjectCard | GraphObject* tests |
| 16 | Request construction after receipt | May remap world via campaign | `receipt.worldId` + fail closed on map disagree | worldGraphSurfaceContext | Request-shape tests |
| 17 | Response integrity | Weak/absent | Validate world/campaign/revision/admissibility/focus/scopeMode | authority module | Unit + provider tests |
| 18 | headRevisionId / isHead metadata | May be misread as authority | Metadata only; isHead=false allowed | committed panel | Panel tests |

### Ordered adversarial sequences

| Seq | Steps | Forbidden outcome | Required outcome | Owning proof |
| --- | --- | --- | --- | --- |
| A1 | Confirm run A → deferred committed projection pending → switch binding to run B → resolve A | A receipt/phase/object appears under B | B remains candidate or B-only; A discarded | WorkbenchModule deferred stale |
| A2 | Confirm → install receipt → committed read fails | UI offers “Retry exact confirm” / re-enters confirm | Receipt preserved; phase error; retry reloads pinned projection only | ExtractPromoteSheet + live state |
| A3 | Confirm object-1 where candidate label is `Candidate Hesta` and durable is `Hesta Ironroot` | UI shows `Candidate Hesta` as committed | UI shows `Hesta Ironroot` by exact ID | Characterization + panel |
| A4 | Confirm → refresh catalog that removes/changes active binding before adopt freezes | Receipt adopted onto wrong/missing binding | Adopt only against frozen current binding; otherwise fail closed / clear | Sheet + provider ordering test |
| A5 | Exact-run commit while candidate prose/assertions visible | Candidate remains primary with committed appended | Candidate chrome replaced once phase ∈ {loading,ready,error} | Workbench exact-run + LiveProjectionPanel |
| A6 | Same exact runId/sourceArtifactId with campaign/session scope change | Old receipt/projection preserved under new lens | Binding key differs; committed state cleared | Binding key + Workbench tests |
| A7 | Relationship click to target absent from committed projection but present under same label in candidate | Alias/label opens wrong object | Unresolved exact target; source card remains | CommittedProjectionPanel |
| A8 | Double-adopt / same-binding refresh while generation advances | Stale completion overwrites newer state | Only latest generation installs | Generation counter tests |
| A9 | `published_audit_degraded` without manual reload | Candidate authority remains | Auto committed load | Sheet characterization/fix |
| A10 | Missing affected ID with gold object present under same label | Fabricated selection from gold | Missing/unresolved; no gold authority | Authority + panel |
| A11 | Map disagrees with `receipt.worldId` | Silent remap to mapped world | scope_unavailable; receipt preserved; no candidate fallback | surface context + provider |
| A12 | Confirm catch wraps adopt+read; read fails | Phase collapses to unknown_result with re-confirm CTA | Separate confirm success from read failure | ExtractPromoteSheet |

## §4 Files in scope — allowlist

| Action | Path | Purpose |
| --- | --- | --- |
| Create / overwrite | `Docs/Plans/HANDOFF-graph-review-post-confirm-world-graph-transition.md` | Canonical dispatch authority (this document) |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts` | Add pure `buildGraphReviewCommittedProjectionRequest` |
| Modify | `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.test.ts` | Prove `receipt.worldId`, `revisionPin`, fail-closed mapping disagreement |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewCommittedAuthority.ts` | Binding types/keys, adoption/response validation, ID normalize, phase vocabulary |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewCommittedAuthority.test.ts` | Unit proofs for authority helpers |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts` | Own committed transition; exact read/retry; generation stale guard; remove post-confirm gold/preview authority path |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveStateContext.tsx` | Expose committed APIs via existing provider spread |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.tsx` | Committed panel: shared card + exact ID nav + receipt metadata + loading/error/retry |
| Create | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.test.tsx` | Label conflict + exact ID + unresolved relationship proofs |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx` | Delegate `adoptCommittedReceipt`; remove sheet-local gold/preview apply; auto-load degraded; no re-confirm on retry; freeze binding before catalog refresh side effects |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx` | Characterization + terminal flows + partially durable failure |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx` | Show committed panel when phase ≠ `candidate` for binding; hide candidate authority |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx` | Committed vs candidate switching |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewSessionToolbar.tsx` | Hide/disable prepare/confirm after terminal receipt for binding |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Typed catalog/exact bindings; clear on change; preserve on refresh; committed primary in exact-run |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | Binding clear/preserve + deferred stale + exact-run replacement |
| Modify | `apps/live-control-ui/src/styles.css` | Minimal committed panel styling only if required (allowlisted). Do **not** add PR380C styles to `planSurface.css`. |
| Modify as needed | Colocated test harness files under graphReviewWorkbench (e.g. `graphReviewLiveStateTestHarness.tsx`) | Keep harnesses aligned with binding/authority types |

### Bounded discovery exception

Maximum **3** additional paths under:

- `apps/live-control-ui/src/planSurface/graphReviewWorkbench/`, or
- `apps/live-control-ui/src/worldGraph/`

for colocated fixtures/helpers required by owning tests.

**Stop and report** if backend paths, Recap/Build/Ingest production paths, `planSurface.css` PR380C styling, or any other out-of-tree production path is required.

Allowed diff classes only:

- TypeScript/TSX production modules listed above
- Matching Vitest files listed above
- This handoff markdown
- Optional minimal `styles.css` rules for the committed panel

Forbidden without STOP report:

- `apps/live_control_server/**`
- `src/graph_memory/**`
- Recap/Build/Ingest production modules
- `apps/live-control-ui/src/planSurface/planSurface.css` PR380C hunks
- New persistence schemas / localStorage keys for receipts

## §5 Out of scope

| Capability / path class | Why out of scope |
| --- | --- |
| Backend extract-promote / World Graph / Kernel routes | Dispatch gate already satisfied; STOP if changes needed |
| Recap / Build / Ingest production changes | Owned by PR380B / other slices |
| Preview-union deletion or Graph Preview route retirement | Successor |
| Exact-run candidate-review projection redesign | Successor |
| Gold authoring commit path | Separate authority |
| Fabricating selection when ID missing | Forbidden by invariant |
| Browser-reload receipt rehydration | Deferred persistence successor |
| Committed recap-prose overlay | Deferred presentation successor |
| Cache / coalescing / telemetry | PR380D |
| Agent Interaction continuity | Hoisted-agent successor |
| Worldbuilding write elevation; Plan/Play production edits | Explicitly deferred |
| Changing confirm receipt schema | Out of scope; consume as-is |
| Auto-publishing or widening publication authority | Rejected |
| Hybrid candidate+committed projection overlays | Rejected |

## §6 Implementation contract

### §6.1 Review binding contract

Graph Review owns a typed binding for committed-transition state:

```ts
type GraphReviewCommittedBinding =
  | {
      kind: "catalog_run";
      key: string; // catalogRunBindingKey(...)
      runId: string;
      campaignId: string;
      sessionId: string;
    }
  | {
      kind: "exact_run";
      key: string; // exactRunBindingKey(...)
      runId: string;
      sourceArtifactId: string;
      campaignId: string | null;
      sessionId: string | null;
    };
```

**Key rules:**

- `catalogRunBindingKey({ runId, campaignId, sessionId })` → `catalog_run:${runId}:${campaignId}:${sessionId}`
- `exactRunBindingKey({ runId, sourceArtifactId, campaignId, sessionId })` → `exact_run:${runId}:${sourceArtifactId}:${campaignId ?? ""}:${sessionId ?? ""}`
- Binding equality is `kind` + `key` only (`committedBindingsEqual`).
- Changing any key constituent clears committed state.
- Same-binding refresh (identical key) preserves committed transition.
- Exact-run must include campaign/session scope in the key even when null, so a later non-null scope is a different binding.
- Receipt adoption that receives prepared identity must verify prepared `runId` / `campaignId` / `sessionId` against the active binding (null-normalized).
- Workbench must construct catalog bindings from the live catalog selection and exact bindings from exact handoff/run identity including `sourceArtifactId`.

### §6.2 Committed authority state

Provider-owned state per active binding:

| Field | Meaning |
| --- | --- |
| `phase` | `candidate` \| `loading` \| `ready` \| `error` |
| `receipt` | Adopted terminal receipt or null |
| `affectedObjectIds` | Normalized exact IDs from receipt |
| `request` | Frozen committed projection request used for load/retry |
| `projection` | Validated committed `WorldGraphProjection` or null |
| `errorKind` | `scope_unavailable` \| `request_failed` \| `integrity_mismatch` (when error) |
| `generation` | Monotonic counter for stale suppression |

Phase meanings:

| Phase | Meaning | Candidate chrome | Committed chrome |
| --- | --- | --- | --- |
| `candidate` | No adopted receipt for binding | Visible / primary | Hidden |
| `loading` | Receipt adopted; projection in flight | Hidden / replaced | Loading + receipt metadata |
| `ready` | Validated projection installed | Hidden / replaced | Exact-ID cards |
| `error` | Durable-read-unavailable | Hidden / replaced | Error + exact-revision retry |

Expose via `GraphReviewLiveStateContext` using the existing provider spread pattern. Consumers must not invent a second committed store.

### §6.3 Receipt adoption

`validateCommittedReceiptAdoption(receipt, prepared?, binding?)`:

**Accept only when:**

- receipt present;
- `outcome` ∈ {`committed`, `already_applied`, `published_audit_degraded`};
- `worldId`, `parentRevisionId`, `committedRevisionId` non-empty after trim;
- if `prepared` provided: proposalId, proposalDigest, parentRevisionId, worldId match;
- if `prepared` + `binding` provided: prepared run/campaign/session match binding (null-normalized).

**On success:** return receipt + `normalizeAffectedObjectIds(receipt.affectedObjectIds)`.

**On failure:** do not install committed authority; surface integrity error without candidate fallback masquerading as success.

**Ordering rule:** freeze the active binding and adopt the receipt against that binding **before** any catalog refresh that can change/remove the binding. Catalog refresh must not race ahead of adoption.

`adoptCommittedReceipt` in live review state must:

1. validate adoption;
2. bump generation;
3. store receipt + normalized IDs;
4. build and freeze request (or enter scope_unavailable error with receipt preserved);
5. set phase `loading` and kick exact read;
6. never call `selectDurableObjectIds` for authority.

Sheet must pass `prepared` into adoption when available.

### §6.4 Committed projection request

Pure helper `buildGraphReviewCommittedProjectionRequest` in `worldGraphSurfaceContext.ts`:

```json
{
  "schema": "dmb_world_graph_projection_request_v1",
  "worldId": "<receipt.worldId>",
  "campaignId": "<binding.campaignId or explicit campaign scope>",
  "focus": { "kind": "session", "sessionId": "<S>", "campaignId": "<C>" }
           // or { "kind": "none", "sessionId": null } when no session
  "admissibility": "gm",
  "scopeMode": "campaign",
  "revisionPin": "<receipt.committedRevisionId>"
}
```

**Rules:**

- Use `receipt.worldId` directly — no remapping after receipt.
- If campaign→world map is missing or disagrees with `receipt.worldId`, fail closed (`scope_unavailable`).
- Never send queryText, preview paths, gold fixtures, extraction IDs as authority, or omit `revisionPin`.
- Store the frozen request on the committed state for retry.
- Focus uses session when sessionId present; otherwise `{ kind: "none", sessionId: null }`.

### §6.5 Response validation

`validateCommittedProjectionResponse({ projection, receipt, request })` must verify at least:

| Check | Rule |
| --- | --- |
| world | projection world identity matches `receipt.worldId` |
| campaign | response campaign matches request campaign scope |
| revision | snapshot `revisionId` equals `receipt.committedRevisionId` and request `revisionPin` |
| admissibility | matches request (`gm`) |
| focus | matches request focus kind/session |
| scopeMode | matches `campaign` |

`headRevisionId` / `isHead` may be shown as metadata only; `isHead=false` is acceptable and must not trigger head fallback.

Integrity/scope failures preserve the receipt, set phase `error`, and keep the frozen request for retry. Pass the frozen `request` into validation — do not rebuild a divergent request at validate time.

### §6.6 Exact object/relationship presentation

`GraphReviewCommittedProjectionPanel`:

- Renders receipt metadata (world, parent revision, committed revision, outcome, auditStatus as truthful secondary copy).
- Opens affected objects by exact ID from the committed projection node map only.
- Uses `GraphObjectProjectionCard` + `adaptWorldGraphNodeView` (or equivalent PR380B neutral adapter path).
- Relationship navigation emits exact target IDs; resolve only within the loaded committed projection.
- On relationship target miss: keep source card visible; show unresolved exact-target message; **no** alias/label/candidate fallback.
- Labels displayed are committed projection labels only.
- Loading and error states remain receipt-aware (show that commit happened; read is unavailable).

Characterization fixture requirement:

- candidate/gold `object-1` label = `Candidate Hesta`
- durable committed `object-1` label = `Hesta Ironroot`
- post-confirm UI must show `Hesta Ironroot` and must not show `Candidate Hesta` as authority.

### §6.7 Commit point and partially durable failure

**Commit point (already on main):** Kernel/publication confirm returns a terminal `ExtractPromoteConfirmReceipt`. That receipt is the durable publication fact this slice consumes.

**UI commit point for authority transition:** successful `validateCommittedReceiptAdoption` for the current binding. From that moment, candidate authority is no longer primary for the binding even if the subsequent projection read has not completed.

**Partially durable failure:**

| Stage | Durable? | UI rule |
| --- | --- | --- |
| Confirm HTTP succeeds with terminal receipt | Yes (publication) | Adopt receipt; enter loading |
| Committed projection read fails / integrity mismatch | Receipt still yes; projection no | phase `error`; preserve receipt+request; CTA = retry committed read |
| Retry | Read-only replay of frozen request | Must **not** call confirm again |
| Catch/error handling around confirm+adopt | Must not collapse post-receipt read failure into `unknown_result` that offers “Retry exact confirm” | Separate confirm failure from post-commit read failure |

Implementation note: awaiting committed-authority adoption inside the same try/catch as `confirmExtractPromote` is a known false pattern. Confirm success must be recognized before read failure handling. Footer CTAs after terminal receipt must not render “Retry exact confirm.”

### §6.8 State and fallback matrix

| Observable path | Loading | Exact success | Ordinary miss | Dependency unavailable | Integrity/contract failure | Stale/superseded | Retry/replay |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Pre-confirm candidate review | Existing | Existing preview/gold/exact-run candidate | Existing | Existing | Existing | Existing run semantics | Existing |
| Receipt adoption | N/A | Freeze binding; install receipt; phase→loading | Non-terminal outcome: remain candidate | N/A | Fail closed; no fake ready | Binding change cancels | Not applicable |
| Committed projection request build | N/A | Frozen request with revisionPin | N/A | Map missing/disagree: scope_unavailable error w/ receipt | Fail closed | N/A | Rebuild only from same receipt/binding |
| Committed projection read | Show loading + receipt meta | Validate; phase ready; exact cards | Affected ID absent: unresolved slot | Network/world/revision missing: error w/ receipt | Schema/mismatch: error w/ receipt | Generation mismatch: ignore completion | Retry exact frozen request |
| Exact object open | Exact map lookup | Shared card from committed node | Missing ID unresolved | N/A | No label/alias | Projection replace resets selection | Deterministic |
| Relationship traversal | Exact target lookup | Open target in same projection | Unresolved message; keep source | Follow committed loading/error | No candidate rebind | Stay on loaded snapshot | Safe |
| Prepare/confirm chrome | Existing until terminal | Disabled/hidden after terminal for binding | N/A | N/A | N/A | Re-enable only if binding cleared to candidate | Must not re-confirm from error retry |
| Exact-run candidate chrome | Existing pre-confirm | Replaced when phase≠candidate | N/A | N/A | N/A | Restored only if binding returns to candidate | N/A |
| Catalog refresh after confirm | May run for diagnostics | Must not change binding under an in-flight adopt | Binding disappeared: fail closed | Refresh failure ≠ candidate fallback | N/A | N/A | Safe if binding frozen first |
| Session toolbar after terminal | N/A | Prepare/confirm suppressed for binding | N/A | N/A | N/A | Cleared with binding | N/A |
| Shared card open | Exact ID | GraphObjectProjectionCard | Missing unresolved | Host error bounded | No gold path | Reset on new projection | Safe |

**Permitted fallback sources for committed authority: none.**

Committed authority must not consult:

- preview-union store;
- gold fixtures as identity;
- exact-run candidate nodes/labels;
- `selectDurableObjectIds` against gold/preview;
- label/alias search;
- unpinned current head;
- fabricated live selection;
- Recap/Build document prose;
- ThreatDraft/statblock labels;
- party registry or corpus-index supplementation.

### §6.9 Identity matrix

| Situation | Required matching rule | Ambiguity behavior | Fallback permitted? | Persistence consequence |
| --- | --- | --- | --- | --- |
| Catalog binding | Exact runId+campaignId+sessionId key | Any constituent change is a new binding | No partial match | Transient provider state only |
| Exact-run binding | Exact runId+sourceArtifactId+campaign+session key | Scope change clears old receipt | No | Transient |
| Binding equality | kind + key only | Missing either side → unequal/clear | No fuzzy equality | Transient |
| Receipt world | Exact `receipt.worldId` | Empty/mismatch rejects adoption | No remap | None beyond receipt token in memory |
| Committed revision | Exact `committedRevisionId` pin | Head metadata ignored for authority | No head float | None |
| Prepared vs receipt | Exact proposalId/digest/parent/world | Mismatch rejects | No | None |
| Prepared vs binding | Exact run/campaign/session (null-normalized) | Mismatch rejects | No | None |
| Affected object open | Exact node ID in committed projection | Missing unresolved | No gold/label | None |
| Relationship target | Exact durable target ID in committed projection | Missing unresolved | No alias | None |
| Labels | Display only after exact ID resolve | Never choose identity | No | None |
| Rename later head | Not in this slice; pin remains exact | N/A | No | No new persistence |
| Deletion in later unpinned head | Out of scope for pinned read | Missing remains unresolved | No recreation | No new persistence |

First-win label matching is prohibited for committed object opens.

### §6.10 Binding lifecycle matrix

| Event | Phase before | Required phase after | Receipt | Projection | Candidate chrome | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Initial mount / no confirm | candidate | candidate | null | null | Primary | Pre-confirm review unchanged |
| Terminal confirm adopt OK | candidate | loading | frozen | null | Replaced | Generation++ |
| Projection validate OK | loading | ready | preserved | installed | Replaced | Exact IDs openable |
| Projection fail / integrity | loading | error | preserved | null | Replaced | Retry = read only |
| Retry committed read | error | loading | preserved | cleared pending | Replaced | Same frozen request |
| Same-binding refresh | ready/error/loading | preserved | preserved | preserved or reload policy without clear | Replaced | Must not wipe transition |
| Binding change (catalog or exact) | any | candidate | cleared | cleared | Primary for new binding | Generation++; ignore in-flight |
| Stale generation completion | any | unchanged | unchanged | unchanged | unchanged | Drop late promise |
| Non-terminal confirm outcome | candidate | candidate | not adopted | null | Primary | Existing error UX |
| Manual clear / leave review | any | candidate | cleared | cleared | N/A | Existing navigation rules |
| Catalog refresh after successful adopt | loading/ready/error | unchanged for frozen binding | preserved | preserved | Replaced | Refresh must not rebind under adopt |
| Scope-only exact-run change | any | candidate | cleared | cleared | Primary | Key includes campaign/session |

### §6.11 Persistence and replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay behavior | Compatibility/migration | Rollback |
| --- | --- | --- | --- | --- | --- |
| Confirm publication | Existing backend receipt/event | Backend already durable | Confirm replay is backend concern; UI must not re-confirm from committed-read retry | No schema change | Outside slice |
| Adopted receipt in Graph Review UI | In-memory provider state only | Lost on full browser reload (explicitly deferred) | Re-adopt only from a new confirm response in-session | No localStorage/IndexedDB schema | Clear binding / revert frontend |
| Frozen committed request | In-memory | Reconstructable from receipt+binding while session live | Retry idempotent read | No migration | Revert frontend |
| Committed projection response | Transient HTTP | Deterministic adapt for same bytes | Duplicate read safe | Consumes existing v1 | Revert frontend |
| Active card selection | React state | No reload guarantee | Duplicate click reopens exact ID | None | Close card |
| Candidate preview/gold state | Existing | Unchanged pre-confirm | Existing | No migration | Outside scope |
| Browser-reload rehydration | Not in this slice | N/A | N/A | Deferred successor | N/A |
| Generation counter | In-memory | Session only | New adopts increment | None | Clear on unmount |

No new persisted format, durable identifier, migration, or compatibility adapter is allowed in PR380C.

### §6.12 Predecessor-to-consumer mapping

#### Grounding sources

- `apps/live-control-ui/src/api/types.ts` — `ExtractPromoteConfirmReceipt`, prepare/confirm, `WorldGraphProjection`
- Existing extract-promote confirm route/client (unchanged)
- Existing generic World Graph projection route/client (unchanged)
- `apps/live-control-ui/src/worldGraph/worldGraphSurfaceContext.ts`
- `apps/live-control-ui/src/graphObjectCard/GraphObjectProjectionCard.tsx`
- `apps/live-control-ui/src/buildSurface/BuildGraphObjectContext.tsx` (pattern reference only)
- `graphReviewLiveReviewState.ts` demolition targets: `reloadCommittedWorldProjection`, `selectDurableObjectIds` post-confirm misuse
- `GraphReviewExtractPromoteSheet.tsx` demolition targets: sheet-local `applyCommittedRevision`, degraded skip

| Predecessor field/outcome | Real shape | Consumer field/behavior | Transformation | Proof |
| --- | --- | --- | --- | --- |
| `receipt.schema` | `dmb_extract_promote_confirm_v2` | Adoption discriminant | Preserve | authority unit test |
| `receipt.outcome` | terminal enum | Adoption gate + chrome | Preserve; non-terminal rejected | authority + sheet |
| `receipt.worldId` | required string | Request worldId; response match | Trim; no remap | surface context + validation |
| `receipt.parentRevisionId` | required string | Metadata + prepared match | Trim | adoption test |
| `receipt.committedRevisionId` | required string | `revisionPin` + response match | Trim | request + validation |
| `receipt.affectedObjectIds` | string[] | Exact open list | trim+dedupe preserve order | normalize unit test |
| `receipt.proposalId` / `proposalDigest` | strings | Prepared match | Trim compare | adoption test |
| `receipt.auditStatus` | `ok` \| `degraded` | Secondary copy only | Preserve; does not block auto-load | sheet degraded test |
| `receipt.headAdvanced` / counts / warnings | present | Optional secondary copy | Preserve; not identity | panel optional |
| Prepared `runId/campaignId/sessionId` | optional/nullable | Binding match | null-normalized | adoption+binding tests |
| Catalog binding fields | run/campaign/session | key + state owner | `catalogRunBindingKey` | Workbench tests |
| Exact binding fields | run/source/campaign/session | key + state owner | `exactRunBindingKey` | Workbench tests |
| `WorldGraphProjection.snapshot.revisionId` | required | Must equal committedRevisionId | Exact equality | validation test |
| `snapshot.headRevisionId` / `isHead` | required-ish metadata | Display only | Never authority | panel tests |
| Projection nodes by ID | exact map/list | Card model | Neutral adapter; exact ID | panel tests |
| Node adjacency targets | exact IDs | Relationship nav | Exact-map only | panel adversarial |
| `published_audit_degraded` | terminal outcome | Auto adopt+load | Same path as committed | sheet characterization |
| 404/network projection errors | existing client errors | phase error w/ receipt | No candidate fallback | failure/retry tests |
| Shared GraphObjectProjectionCard | PR380B | Committed panel renderer | Reuse; no fork | shared card regression |

### §6.13 Trust boundary

**Verifies:**

- terminal receipt adoption fields and prepared/binding alignment;
- committed request uses `receipt.worldId` + `revisionPin` without remap;
- response world/campaign/revision/admissibility/focus/scopeMode match;
- affected objects and relationships resolve by exact ID inside the committed projection;
- phase ≠ candidate replaces candidate chrome for catalog and exact-run;
- post-commit read failure preserves receipt and retries read only;
- binding change clears state; same-binding refresh preserves; stale generations ignored;
- prepare/confirm disabled after terminal receipt for the binding;
- no backend publication contract edits;
- allowlist-only production paths.

**Records or trusts without proving:**

- semantic completeness of Kernel publication;
- whether every affected ID ought to exist (backend truth);
- cross-reload UI rehydration;
- long-term preview-union retirement readiness;
- cache correctness;
- Recap immediately reflecting the new revision (Recap has its own consumers).

**Rejects:**

- gold/preview/`selectDurableObjectIds` as post-confirm authority;
- candidate labels/aliases as committed identity;
- head fallback on pinned miss;
- re-confirm from durable-read-unavailable retry;
- fabricating missing IDs;
- world remap after receipt;
- keeping exact-run candidate as primary after commit;
- silent allowlist expansion / backend edits;
- compressed handoff substitutes as dispatch authority.

## §7 Required demolition

Remove or neutralize these false authorities:

1. **Post-confirm gold/preview selection path** — stop using `reloadCommittedWorldProjection` only to verify-then-discard into `selectDurableObjectIds` against gold/preview as the object authority.
2. **Sheet-local `applyCommittedRevision`** that selects from gold/preview after confirm.
3. **`published_audit_degraded` skip** that leaves candidate authority in place without auto-load.
4. **Fabricated live selection** when an affected ID is missing from the committed projection.
5. **“Retry exact confirm” after terminal receipt** when only the committed projection read failed — replace with exact-revision committed-read retry.
6. **Exact-run candidate-primary chrome after commit** — candidate presentation must not remain the primary authority under/above a merely appended committed panel once phase ∈ {loading, ready, error}.
7. **Weak exact-run binding identity** that omits campaign/session scope from the key/equality — scope changes must clear stale committed state.
8. **Adopt-after-refresh races** that can move/remove the active binding before the receipt is frozen to it.
9. **Shared try/catch collapsing confirm success + post-commit read failure** into `unknown_result` / re-confirm CTAs.
10. **Any post-confirm path that treats `headRevisionId` / `isHead` as authority** rather than metadata.

Do not delete preview-union infrastructure in this slice; only stop using it as post-confirm authority.

## §8 Evidence required

### §8.1 Proof ledger

| Guarantee | Owning boundary | Required evidence | Result slot |
| --- | --- | --- | --- |
| Terminal confirm receipt replaces candidate authority for the same review binding | Graph Review workflow/provider | Catalog-run and exact-run integration tests | {{RESULT}} |
| Committed projection request pinned to receipt revision and exact campaign/world scope | World Graph request adapter + provider | Request-shape contract tests | {{RESULT}} |
| Affected objects/relationships resolve only from committed projection by exact ID | Committed projection panel | Adversarial card/navigation tests with conflicting labels | {{RESULT}} |
| Post-commit read failure preserves receipt; never falls back to candidate; retry does not re-confirm | Provider + committed panel + sheet | Failure/retry tests | {{RESULT}} |
| Run switches suppress stale completions; same-binding refresh preserves transition | Provider binding lifecycle | Deferred-promise interleaving tests | {{RESULT}} |
| Pre-confirm preview review remains usable; no backend/publication contract changes | Existing Graph Review + diff boundary | Regression suite + allowlist inspection | {{RESULT}} |

### §8.2 Characterization-first

Before or as the first implementation commit after docs:

1. Add a failing/documenting test with conflicting candidate vs durable labels for `object-1`:
   - candidate/gold: `Candidate Hesta`
   - durable committed: `Hesta Ironroot`
2. Document that base/`published_audit_degraded` currently skips auto-load (characterization), then turn green.
3. Prefer a separate characterization commit before production fixes when feasible.

Characterization must fail for the right reason (authority misuse), not because of unrelated harness breakage.

Minimum characterization assertions:

- post-confirm authority path currently consults gold/preview labels OR would display `Candidate Hesta` if that path remains;
- after the fix, durable `Hesta Ironroot` is shown and `Candidate Hesta` is not presented as committed authority;
- degraded outcome no longer depends on a manual-only reload to leave candidate mode.

### §8.3 Commands

Run from repository root unless noted:

```bash
cd apps/live-control-ui

npx vitest run \
  src/worldGraph/worldGraphSurfaceContext.test.ts \
  src/planSurface/graphReviewWorkbench/graphReviewCommittedAuthority.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewCommittedProjectionPanel.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx

npx vitest run \
  src/graphObjectCard/GraphObjectProjectionCard.test.tsx \
  src/graphObjectCard/GraphObjectCard.test.tsx

# Optional but recommended Graph Review regressions (pre-confirm must remain usable)
npx vitest run \
  src/planSurface/graphReviewWorkbench/GraphReviewLoadSurface.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx \
  || true

npm run typecheck
npm run build

cd ../..

git diff --check
git diff --name-only caa46f43971fc51f06e8805201c95cbd64ddc638...HEAD

# Allowlist inspection — planSurface.css must not gain PR380C styling hunks.
# styles.css may contain minimal committed-panel rules if needed.
rg -n "CommittedProjection|committed-projection|graph-review-committed" \
  apps/live-control-ui/src/styles.css \
  apps/live-control-ui/src/planSurface/planSurface.css || true

# Post-confirm authority must not reintroduce gold/preview selection as committed truth.
rg -n "selectDurableObjectIds" \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewExtractPromoteSheet.tsx

# Binding helpers must exist for both catalog and exact_run.
rg -n "catalogRunBindingKey|exactRunBindingKey|catalog_run|exact_run" \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewCommittedAuthority.ts \
  apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx
```

Record command outputs truthfully. Baseline-identical typecheck/build failures outside the allowlist are informational and must be reported accurately; they do not waive §1 invariant failures.

### §8.4 Dogfood

Manual dogfood is optional for merge if automated adversarial proofs cover A1–A12. If performed, record:

- campaign/session or exact-run identity used;
- confirm outcome observed;
- whether committed panel replaced candidate;
- whether exact IDs opened durable labels;
- whether a forced projection failure offered read-retry rather than re-confirm.

If not run: PR body must say `not run` (not “passed”).

### §8.5 Baseline failure protocol

If `npm run typecheck` or `npm run build` fails:

1. Reproduce on clean base `caa46f43971fc51f06e8805201c95cbd64ddc638` with the same command.
2. If failures are identical and outside §4 allowlist paths: report as baseline-identical; do not expand scope to fix unrelated debt.
3. If failures are new in allowlisted files: fix before merge.
4. Never claim green without the command output.
5. Do not use baseline failure as cover for invariant regressions.

## §9 Required PR description and handback

### PR description

Use the YAML `pr_body_template` exactly as the PR body skeleton. Fill every `{{RESULT}}` / placeholder with real evidence. Do not invent dogfood. Do not replace the Outcome/Invariant wording.

Suggested title:

`PR380C: Graph Review post-confirm World Graph authority transition`

Base: `caa46f43971fc51f06e8805201c95cbd64ddc638`

The PR body is a merge contract, not a substitute for this handoff. Reviewers must still read this document for matrices and adversarial sequences.

### Implementation handback (return to dispatcher)

Return:

- HEAD SHA
- commit list (docs → characterization → helpers → provider/state → panel/wiring → fixes)
- test command results (pass/fail counts)
- actual changed paths vs §4 allowlist
- PR URL (after push + `gh pr create` when evidence is green)
- gaps / stop conditions / baseline-identical failures
- explicit confirmation that binding/retry/persistence/adversarial matrices in this handoff were not compressed away

### Commits expected

Logical commits:

1. docs (this handoff)
2. characterization (may be red)
3. helpers (`worldGraphSurfaceContext`, `graphReviewCommittedAuthority`)
4. provider/state (`graphReviewLiveReviewState`, context)
5. panel/wiring (committed panel, sheet, live panel, toolbar, workbench)
6. fixes from review/gaps

Do not push until evidence for the invariant is honest; then `git push -u origin HEAD` and open/update the PR.

## §10 Acceptance rubric

Merge only when all are true:

### Authority transition

1. Docs handoff committed and is this full artifact (not a compressed substitute).
2. Terminal receipt adoption replaces candidate authority for the binding.
3. Committed objects open by exact ID from a projection pinned to `committedRevisionId` / `receipt.worldId`.
4. Conflicting candidate vs durable labels: durable wins.
5. `published_audit_degraded` auto-loads committed authority.

### Failure and retry

6. Post-commit read failure preserves receipt; retry does not re-confirm.
7. No “Retry exact confirm” CTA after a terminal receipt when only the read failed.

### Binding lifecycle

8. Catalog and exact_run bindings include required scope in keys.
9. Binding change clears committed state; same-binding refresh preserves it.
10. Deferred stale completions from prior bindings are ignored.

### Presentation

11. Exact-run candidate chrome is replaced when phase ≠ candidate.
12. Prepare/confirm disabled/hidden after terminal receipt for the binding.
13. Relationship misses stay unresolved without alias fallback.

### Scope and evidence

14. Characterization proves label conflict / authority misuse, then turns green.
15. All §8.3 primary commands recorded; shared card regressions green.
16. No production paths outside §4 / bounded exception (`planSurface.css` PR380C hunks forbidden).
17. PR body uses frontmatter skeleton with real results.
18. Base remains ancestor of HEAD.
19. No backend/publication contract changes.
20. §6.8–§6.11 matrices and §3 adversarial sequences remain present in the checked-in handoff.

## §11 Stop conditions

STOP and report without silently expanding scope if:

- backend confirm/audit/World Graph contract changes are required;
- generic projection lacks usable `revisionPin` on base (gate regression);
- receipt fields required by §6.3 are absent on base;
- more than the bounded discovery exception is required;
- Recap/Build/Ingest production edits seem necessary for the invariant;
- preview-union retirement or exact-run candidate redesign is required to make tests pass;
- the worker is tempted to compress this handoff or omit matrices to “save tokens”;
- base is no longer an ancestor after attempted history rewrite;
- `planSurface.css` appears to be the only workable styling surface (report; prefer `styles.css` or STOP).

## §12 Reviewer focus

Review against §1 invariant first.

**Reject immediately if:**

1. The checked-in handoff is a compressed rewrite missing §6.8–§6.11 matrices or §3 adversarial sequences.
2. Any post-confirm path reopens gold/preview/`selectDurableObjectIds` as committed authority.
3. Post-commit read failure offers re-confirm.
4. Exact-run keeps candidate as primary after commit.
5. Exact-run binding omits campaign/session scope from identity/equality.
6. Receipt adoption can land on a binding changed by intervening catalog refresh.
7. Stale deferred projection from run A can install under run B.
8. Allowlist breached (backend, Recap/Build, `planSurface.css` PR380C styles, etc.).
9. Characterization for `Candidate Hesta` / `Hesta Ironroot` is absent or greenwashed.
10. Frontmatter Outcome/Invariant were rewritten away from this handoff’s wording.

**Primary review surfaces:**

- `graphReviewCommittedAuthority.ts` + tests
- `graphReviewLiveReviewState.ts` generation/retry/adopt ordering
- `GraphReviewExtractPromoteSheet.tsx` confirm vs read failure separation
- `GraphReviewCommittedProjectionPanel.tsx` exact-ID + unresolved targets
- `GraphReviewLiveProjectionPanel.tsx` / `GraphReviewWorkbenchModule.tsx` chrome replacement
- `worldGraphSurfaceContext.ts` request builder
- Diff path list vs §4
- This handoff file’s continued completeness

**Secondary:** shared card regressions remain green; pre-confirm Graph Review still works.


## Annex A — Binding key worked examples

These examples are normative for key construction tests.

### Catalog run

Inputs:

- runId = `live-run-77`
- campaignId = `c2`
- sessionId = `s25`

Key:

```text
catalog_run:live-run-77:c2:s25
```

Changing only `sessionId` to `s26` yields a different binding and must clear committed state.

### Exact run with null scope

Inputs:

- runId = `er-1`
- sourceArtifactId = `art-1`
- campaignId = `null`
- sessionId = `null`

Key:

```text
exact_run:er-1:art-1::
```

Later setting campaignId=`c2` and sessionId=`s25` yields:

```text
exact_run:er-1:art-1:c2:s25
```

That is a **different** binding. Preserving the prior receipt under the new key falsifies §6.1 / §6.10 / adversarial A6.

### Exact run with scope

Inputs:

- runId = `er-9`
- sourceArtifactId = `src-markdown-22`
- campaignId = `hermes`
- sessionId = `session-4`

Key:

```text
exact_run:er-9:src-markdown-22:hermes:session-4
```

## Annex B — Partially durable failure sequence (normative)

1. User confirms a prepared proposal.
2. `confirmExtractPromote` returns terminal receipt (`committed` / `already_applied` / `published_audit_degraded`).
3. UI freezes current binding and adopts receipt → phase `loading`; candidate chrome replaced.
4. Committed projection request is built with `receipt.worldId` + `revisionPin=committedRevisionId`.
5. Projection read fails (network, 404, integrity mismatch, or scope_unavailable).
6. UI retains receipt + frozen request; phase `error`; CTA labeled for exact-revision retry / reload committed projection.
7. CTA must **not** call confirm again.
8. Retry reuses the frozen request; on success → phase `ready` and exact-ID presentation.

Forbidden collapses:

- wrapping steps 3–5 in the same catch as step 2 such that step 5 becomes `unknown_result`;
- showing “Retry exact confirm”;
- reverting to candidate/gold labels while the receipt remains adopted;
- floating to current head because the pin failed.

## Annex C — Adversarial fixture notes

### A3 label conflict

| Source | object ID | Label |
| --- | --- | --- |
| Candidate / gold / preview | `object-1` | `Candidate Hesta` |
| Committed World Graph projection at pinned revision | `object-1` | `Hesta Ironroot` |

Post-confirm cards, lists, and navigation chrome for `object-1` must render `Hesta Ironroot`.

### A1 stale generation

Use deferred promises:

1. Adopt on binding A; start projection fetch; hold the promise.
2. Switch to binding B (different key).
3. Resolve A’s promise with a valid A projection.
4. Assert B shows no A receipt, no A phase ready, and no A object card.

### A5 exact-run chrome

In exact-run mode after terminal adopt:

- source prose / assertion candidate panels are not the primary authority surface;
- committed panel is the primary object authority surface whenever phase ∈ {loading, ready, error}.

## Annex D — Allowlist path checklist for PR authors

Before opening/updating the PR, paste `git diff --name-only caa46f43971fc51f06e8805201c95cbd64ddc638...HEAD` and classify every path:

| Path | In §4? | In discovery exception? | Action |
| --- | --- | --- | --- |
| (fill per path) | yes/no | yes/no/n/a | keep / STOP report |

If any production path is neither allowlisted nor an admitted exception, STOP.

## Annex E — Evidence ledger fill guide

When filling the frontmatter evidence table:

| Guarantee | What “PASS” requires |
| --- | --- |
| Terminal receipt replaces candidate authority | Catalog + exact-run tests show phase transition and chrome replacement |
| Request pinned to receipt revision/scope | Unit test asserts worldId from receipt, revisionPin, fail-closed map disagree |
| Exact ID resolution under label conflict | A3 fixture green |
| Post-commit read failure preserves receipt | A2/A12 green; no re-confirm CTA |
| Stale suppression + same-binding preserve | A1 + same-binding refresh green |
| Pre-confirm usable + no backend changes | Regression suite + empty backend diff |

## Annex F — Non-goals restated for reviewers

PR380C does **not**:

- redesign candidate review;
- delete preview-union;
- change confirm schemas;
- rehydrate receipts after browser reload;
- migrate Recap onto the new revision as part of Graph Review;
- add cache/telemetry;
- grant Build/Plan/Play new write authority.

If a diff does any of the above, it is out of slice.

## Annex G — Mapping from compressed 294-line rewrite defects

The rejected compressed rewrite omitted or under-specified:

| Defect in compressed rewrite | Restored here |
| --- | --- |
| Thin binding section without key rules | §6.1 + Annex A |
| No ordered adversarial sequences | §3 Ordered adversarial sequences A1–A12 |
| No binding lifecycle matrix | §6.10 |
| No persistence/replay matrix | §6.11 |
| Characterization treated as optional aside | §8.2 |
| Partially durable failure under-specified | §6.7 + Annex B |
| Exact Outcome/Invariant drifted | Frontmatter + §1 restored to dispatch wording |
| Reviewer focus lacked compression reject rule | §12 item 1 |


## Final dispatch check

- [ ] Capability decomposition selected one invariant
- [ ] Mission falsification test written
- [ ] Observable paths + ordered adversarial sequences complete
- [ ] Allowlist + discovery exception explicit
- [ ] §6.1–§6.13 matrices present (binding, state, adoption, request, validation, presentation, commit/partial failure, fallback, identity, lifecycle, persistence, predecessor mapping, trust)
- [ ] Demolition list explicit
- [ ] Evidence ledger + characterization-first + commands + dogfood + baseline protocol present
- [ ] Acceptance, stop conditions, reviewer focus present
- [ ] Frontmatter Outcome/Invariant/evidence match this document body
- [ ] Document is not a compressed rewrite of itself

## Dispatch summary for the coding agent

Implement only the Graph Review post-confirm World Graph authority transition on base `caa46f43971fc51f06e8805201c95cbd64ddc638`, branch `agent/graph-review-post-confirm-world-graph-transition`, allowlist §4.

Characterization first with `Candidate Hesta` vs `Hesta Ironroot`.

Install typed bindings (`catalog_run` / `exact_run`), receipt adoption, pinned committed projection, exact-ID panel, partially durable failure retry, and binding lifecycle stale suppression.

Demolish gold/preview post-confirm authority and degraded skip.

Do not compress this handoff. Do not change backend contracts. Record §8 evidence and open/update the PR with the frontmatter skeleton.
