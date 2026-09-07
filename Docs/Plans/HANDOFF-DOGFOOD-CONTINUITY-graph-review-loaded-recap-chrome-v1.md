---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: DOGFOOD-CONTINUITY / DEMO-R1 chrome
  - Flow: DOGFOOD-CONTINUITY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-graph-review-loaded-recap-chrome-v1.md
  - Branch / PR: dogfood-continuity/graph-review-ingest-chrome / #690

  ## Verification pointer
  - Base/head: 0912ce4010655655b1f7b4966ee071e043b47721 / this PR HEAD
  - Changed paths: Graph Review workbench chrome + predecessor #689 authority sync
  - Verification: §7 vitest command

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — DOGFOOD-CONTINUITY: Graph Review loaded-recap chrome v1

**Created:** 2026-09-07  
**Status:** ACTIVE — one implementation capability  
**Canonical handoff path:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-graph-review-loaded-recap-chrome-v1.md`  
**Conversation/workstream:** DOGFOOD-CONTINUITY / DEMO-R1 assembled-dogfood chrome  
**Flow / owner:** DOGFOOD-CONTINUITY  
**Direction:** DESIGN → CODE → REVIEW  
**Base revision:** `0912ce4010655655b1f7b4966ee071e043b47721` (PR #689 merge)  
**PR title:** `DOGFOOD-CONTINUITY: collapse Graph Review ingest chrome`  
**PR:** #690

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md).

This handoff was missing on Review Cycle 1 head `850c647c81fc942c196f7326f2f11c4c9a380d84`. It is the checked-in review contract for the current head, not a reconstructed “this was always the dispatch copy.”

## §1 Mission and merge-ready invariant

**Mission:** A GM can load a historical recap from Graph Review and read it as a document, with session identity once and ingest/run provenance collapsed behind Advanced details.

**Merge-ready invariant:** Ordinary catalog `Load recap` and exact-run handoff both keep ingest identity available behind Advanced details; they do not delete it. When both are present, exact-run handoff wins presentation identity. Read-only chrome follows inspect-only / non-promotable actions, not `status !== reviewable`. First-world-publish-eligible runs are not labeled Read-only.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes — exact-run handoff wins presentation identity when present; otherwise loaded recap chrome is owned by the applied catalog run. |
| Most likely adversarial sequence | `handleApplyLoad()` clears exact-run handoff; chrome that keys only on `exactRun` vanishes. |
| Will §7 actually detect that failure? | Yes — Load-dialog validated recap must keep `graph-review-historical-recap-meta`, Advanced details, and Read-only. |
| Easiest owning boundary to under-test | Catalog Load vs URL-restored exact-run. |
| Fact that forces stop/split | Changing promotion eligibility, widening `reviewable`, or editing recap prose. |

## §2 Context, authority, and lane

| Field | Required content |
|---|---|
| Parent authority | [`ROADMAP-demo-ready-c1-c2-to-of-conks.md`](../Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md) Stage 1 / STOP 1 dogfood chrome |
| Base revision | `0912ce4010655655b1f7b4966ee071e043b47721` |
| Predecessor contract | PR #689 MERGED (`0912ce4010655655b1f7b4966ee071e043b47721`, 2026-09-07) — historical recap World projection |
| Exact input consumed | Loaded ExtractionRun + optional historical World projection |
| Named successor | Durable APP-STATE / remaining session ingest / STOP 1 close |
| What remains false | STOP 1 complete; promotion; editable recap; C1 14–16 / C2 1–22 catalog coverage |
| Explicit non-goals | No lifecycle change; no prepare/promote change; no corpus restores |
| Branch / isolated checkout | `dogfood-continuity/graph-review-ingest-chrome` on Buddy product checkout |
| Parallel lanes / collision hotspots | Graph Review workbench files were #689’s lease; #689 is merged so this lane may take them |
| Runtime/state ownership | UI-only; no APP-STATE / World writes |
| State-authority sync set after merge | This handoff records predecessor #689 and WR1 completion. Roadmaps/STEWARDS-ANCHOR/projection+inspection handoffs travel in this PR. STOP 1 stays open. |

## §3 Observable paths and adversarial sequences

| Path | Current behavior (Cycle 2 head) | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Catalog Load validated recap | Chrome keyed on applied catalog run | Unchanged | Yes | `GraphReviewWorkbenchModule` + header |
| Exact-run handoff validated recap | Advanced details from `exactRun` | Unchanged, still collapsed | Yes | header |
| Exact handoff + stale persisted catalog | `loadedRun = appliedLiveRun ?? exactRun` can show run A details for run B | Exact handoff wins presentation identity | Yes | `loadedRun = exactRun ?? appliedLiveRun` |
| Worldbuilding reviewable inspect-only | Read-only chip | Unchanged | Yes | header `readOnly` |
| First-world-publish-eligible worldbuilding | Read-only chip while Create World Graph is shown | No Read-only; first-world sheet unchanged | Yes | `loadedReadOnly` excludes first-world |
| Promotable recap | No chip | No chip | Yes | header |

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Load recap → `handleApplyLoad` clears `exactHandoff`/`exactRun` | Applied catalog run still supplies Advanced details + Read-only | Load-dialog validated recap test |
| Persisted catalog run A + `extractionRunId=B` | Advanced details and compact label describe B | Stale-catalog vs exact-handoff test |

## §4 Files in scope — write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-graph-review-loaded-recap-chrome-v1.md` | This review contract |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-recap-projection-v1.md` | Predecessor #689 MERGED |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-recap-inspection-v1.md` | Predecessor successor note |
| Modify | `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-eldyrwild-world-authority-recovery-v1.md` | WR1 / #689 unblocked COMPLETE; STOP 1 stays open |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | #689 no longer “in review” |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | #689 MERGED; #690 active chrome |
| Modify | `Docs/Roadmaps/ROADMAP-demo-ready-c1-c2-to-of-conks.md` | DEMO-R1 predecessor vs current chrome |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewHistoricalRecapProjection.tsx` | Remove duplicate ingest banner from the reader |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchHeader.tsx` | Human session label + Advanced details + Read-only |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchHeader.test.tsx` | Header chrome proof |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.tsx` | Loaded-recap chrome owner |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx` | Catalog Load + URL historical recap proof |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx` | Worldbuilding Read-only proof |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.ts` | Human vs machine labels |
| Modify | `apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts` | Label proof |
| Modify | `apps/live-control-ui/src/planSurface/planSurface.css` | Advanced details / Read-only chip |

## §5 Explicitly out of scope / collision boundary

| Path | Why this slice must not touch or claim it |
|---|---|
| `src/prompts/*.py` | Prompt behavior unchanged |
| `corpus/**` | No restored historical recap filenames |
| `apps/live_control_server/**` | Projection/inspection contracts stay #689 |
| `EXACT_REVIEWABLE_STATUSES` / promote routes | Inspect-only remains inspect-only |
| Stage 1 STOP 1 completion | Assembled dogfood is not closed by chrome |

## §6 Implementation contract

```text
Input:
  applied catalog ExtractionRun and/or exact-run handoff
  optional historical World projection

Output:
  default chrome: human session label, optional Read-only, Load recap
  Advanced details: run id, source, status, machine scope, inspect-only copy

Invariant:
  catalog Load does not delete provenance; exact handoff wins identity when present;
  Read-only follows !promotable except first-world-publish-eligible

Failure behavior:
  missing projection → recap error stays visible; chrome still names the loaded run
```

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| Loaded recap chrome | Session label empty / no chip | Applied run or handoff run | No session loaded | Projection error below header | Identity mismatch error | New Load replaces chrome | Same Load restores chrome |

### D. Predecessor → consumer mapping

**Grounding source:** PR #689 merged historical recap projection

| Predecessor field/outcome | Real shape/optionality | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| Historical projection 200 | `worldId` / `graphId` optional until ready | Advanced details always; World/graph when present | Header meta line | Module tests |
| `validated`/`prepared` recap | inspect-only | Read-only chip | `!promotable` | Load-dialog test |
| Worldbuilding reviewable | inspect-only / optional first-world | Read-only unless first-world eligible | `source_domain === worldbuilding` ⇒ not promotable; first-world suppresses chip | GenericRun test |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command or manual scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Catalog Load keeps collapsed provenance | Graph Review module | regression | §7 command | Advanced details + historical-recap-meta + Read-only | meta missing after Load |
| Exact handoff wins over stale catalog | Graph Review module | regression | §7 command | Advanced details show run B, not persisted A | banner shows catalog A |
| Worldbuilding inspect-only is Read-only | GenericRun + header | regression | §7 command | Read-only chip present | chip absent on reviewable worldbuilding |
| First-world eligible is not Read-only | GenericRun | regression | §7 command | Create World Graph present; Read-only absent | chip on first-world sheet |
| Promotable recap has no Read-only chip | existing reviewable Load tests | regression | §7 command | no Read-only on `er_run_a` | chip on promotable run |
| Predecessor #689 recorded merged | roadmaps + handoffs | authority | diff of Docs/ | no “#689, in review” | leftover in-review claim |
| WR1 no longer blocks #689 | WR1 handoff | authority | diff of Docs/ | WR1 status COMPLETE; #689 MERGED | leftover “ACTIVE — blocks #689” |

Exact verification commands:

```bash
pnpm --dir apps/live-control-ui exec vitest run \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchHeader.test.tsx \
  src/planSurface/graphReviewWorkbench/graphReviewWorkbenchUtils.test.ts \
  src/planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule.test.tsx \
  src/planSurface/graphReviewWorkbench/GraphReviewGenericRun.test.tsx
git diff --check
git diff --name-only origin/main...HEAD
```

### Minimal live / dogfood proof

```text
Existing surface: Graph Review Workbench on /ingest
Smallest realistic scenario: Load recap → C1 Session 17 or C2 Session 23 validated run
Expected observation: Session N · Longmont C# once; Advanced details collapsed; recap readable; pills still open cards
Evidence captured: Cycle 1 screenshot plus this head’s Load-dialog test
```

### Baseline failure handling

Not applicable — no required baseline failure on this UI-only slice.

## §8 Required review handback

Record:

1. Review Cycle 1 on `850c647c81fc942c196f7326f2f11c4c9a380d84` = REQUEST CHANGES (`5134948769`).
2. Review Cycle 2 on `cb0671c8484b1a92e81a6198ba63f45bbce373cb` = REQUEST CHANGES (`5135039869`).
3. §1 disposition after this head: exact handoff wins presentation identity; first-world eligible is not Read-only; WR1 recorded COMPLETE.
4. §7 command rerun on the new head.
5. Nano-commit: Cycle 2 repair (exact-handoff identity + first-world Read-only + WR1 completion sync).
6. Changed paths vs §4.
7. No baseline waiver.
8. Paths outside §4: none.
9. STOP 1 remains open.
10. Successor still false: durable APP-STATE, remaining sessions, STOP 1 close.
11. P1 exact-handoff precedence, P1 WR1 sync, P2 first-world chip.

## §9 Acceptance rubric

- [ ] Exactly one independently useful capability from §1 is delivered and proved by §7.
- [ ] Ordinary Load recap keeps Advanced details.
- [ ] Exact-run handoff wins presentation identity over a stale persisted catalog selection.
- [ ] Read-only follows inspect-only / non-promotable actions; first-world eligible is not Read-only.
- [ ] Predecessor #689 is recorded MERGED; WR1 no longer claims to block #689; STOP 1 is not marked complete.
- [ ] Actual changed paths stay inside §4.
- [ ] Named successor remains unimplemented/unclaimed.

## Stop conditions

Stop and report instead of expanding when any of these appears:

- promotion/`reviewable` widening;
- recap prose editing;
- corpus restores;
- claiming STOP 1 complete from chrome alone.
