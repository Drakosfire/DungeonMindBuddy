---
pr_body_template: |
  ## Handoff pointer
  - Conversation/workstream: UI Presentation Substrate Sidequest
  - Flow: UI
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-UI-canonical-visual-contract.md
  - Branch / PR: none while BLOCKED
  - PR topology: serial

  ## Verification pointer
  - Design authority / head: UI-F3 handoff design head f70985d2d7c82d7bc9ea1954deae5d9505f6c1bd
  - Changed paths: exact §4 allowlist only
  - Verification: Ladle build + opt-in one-worker Chromium Playwright screenshots + ordinary frontend tests/build + diff checks

  The checked-in ACTIVE handoff, cumulative diff, nano-commit story, and independently
  rerun evidence are the review contract. This body is transport metadata.
---

# HANDOFF — UI canonical visual contract

**Created:** 2026-09-25  
**Status:** BLOCKED — UI-F3 ToolHost presentation split must be accepted and merged; steward then re-anchors and activates this handoff  
**Canonical handoff path:** `Docs/Plans/HANDOFF-UI-canonical-visual-contract.md`  
**Conversation/workstream:** `UI Presentation Substrate Sidequest`  
**Flow / owner:** `UI`  
**Direction:** DESIGN → CODE → REVIEW  
**Design authority base:** `f70985d2d7c82d7bc9ea1954deae5d9505f6c1bd` — UI-F3 design head  
**Activation gate:** UI-F3 implementation accepted/merged; re-anchor confirms current Ladle story IDs and ToolHostView/ObjectSheet storyability  
**Dispatch base rule:** fresh current `main` containing this checked-in handoff after activation; exact implementation branch base recorded at dispatch/review  
**PR topology:** `serial`  
**PR authorization:** once ACTIVE, open/update exactly one implementation PR for this capability without asking; no successor/repair PRs  
**PR title:** `UI: add canonical visual contract`

> Repository law: [`AGENTS.md`](../../AGENTS.md). Steward process: [`Docs/Process/STEWARD-CYCLE.md`](../../Docs/Process/STEWARD-CYCLE.md). External PR mechanics: [`.cursor/skills/external-agent-pr-loop/SKILL.md`](../../.cursor/skills/external-agent-pr-loop/SKILL.md).

## §1 Mission and merge-ready invariant

**Mission:** A frontend developer can run one explicit, low-concurrency visual check against a small canonical set of isolated Buddy stories so that large presentation regressions are caught without adding cost to normal UI editing.

**Merge-ready invariant:** A fixed, intentionally small Ladle story set renders deterministically in one Chromium worker at named desktop/narrow viewports, committed visual baselines are generated only for that set, ordinary development/test commands do not launch Playwright, and no backend/product runtime is required.

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | Yes. The capability is one explicit visual contract over already-earned isolated stories; no new product presentation semantics are introduced. |
| Most likely adversarial sequence | “Visual coverage” expands to every story → dozens/hundreds of screenshots + browser workers → weak-laptop workflow becomes slow and brittle. |
| Will §7 actually detect that failure? | Yes. The selected story manifest is fixed and counted, Playwright workers are pinned to 1, and the ordinary test script must remain Playwright-free. |
| Easiest owning boundary to under-test | Baseline determinism across viewport/story loading; a screenshot may race story code-splitting or animations. |
| What PR topology is authorized, and why is it safe? | Serial. Package/lock changes and shared UI stories are collision hotspots; this follows F3 exact presentation state. |
| Fact that forces stop/split | Stable screenshots require app/backend state, more than 12 baseline images, cross-browser coverage, or animation/data mocking infrastructure. |

## §2 Context, authority, lane, and PR topology

| Field | Required content |
|---|---|
| Parent authority | UI Presentation Substrate plan |
| Design authority base | `f70985d2d7c82d7bc9ea1954deae5d9505f6c1bd` |
| Activation gate | UI-F3 implementation merge + re-anchor |
| Dispatch base rule | fresh current main containing this handoff after activation |
| Predecessor contract | Ladle workshop; ObjectSheet stories; ToolHostView presentation boundary |
| Exact input consumed | selected static Ladle story IDs only |
| Named successor | UI-F5 — Canvas Page/Print convergence experiment |
| What remains false | no whole-app screenshot suite; no production E2E; no Firefox/WebKit matrix; no per-story auto-snapshotting |
| Explicit non-goals | visual pixel perfection; every component/story; backend flows; accessibility audit expansion; screenshot CI across multiple OS/browser variants |
| PR topology | serial |
| Authorized PR action | open/update exactly this assigned PR only |
| Open implementation PRs in workstream at dispatch | none required; steward re-checks |
| Stack parent + merge/rebase order | not applicable |
| Branch / isolated checkout | fresh isolated implementation branch/worktree after activation |
| Parallel lanes / collision hotspots | package.json/lockfile; `src/ui/*.stories.tsx`; any F3 ToolHostView story path |
| Runtime/state ownership | local Ladle preview process + one Playwright Chromium worker; no application runtime state |
| State-authority sync set after merge | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` records UI-F3 completed predecessor / UI-F4 current |

Read before implementation:

1. active UI-F1/F2/F3 results;
2. `apps/live-control-ui/package.json`;
3. current Ladle stories/meta output;
4. Ladle visual-snapshot guidance / current `meta.json` story IDs;
5. Playwright screenshot comparison contract;
6. current repo ignore/output conventions.

## §3 Observable paths and adversarial sequences

| Path | Current behavior | Required behavior | Same §1 invariant? | Owning boundary |
|---|---|---|---:|---|
| Ordinary `npm test` | Vitest only | remains Vitest only; no browser launch | Yes | package scripts |
| Ordinary `npm run ui` | Ladle dev workshop | unchanged; no screenshot watcher | Yes | package scripts |
| Explicit visual check | absent | builds/previews Ladle and runs one-worker Chromium on fixed story manifest | Yes | Playwright config/test |
| Baseline creation/update | absent | explicit developer action only | Yes | Playwright snapshot workflow |
| Story loading | code-split | wait for Ladle `data-storyloaded` before screenshot | Yes | visual test |
| Desktop/narrow | manual only | named viewport per selected case | Yes | visual test matrix |

Adversarial sequences:

| Sequence | Required safe outcome | Owning §7 proof |
|---|---|---|
| Run ordinary unit tests after Playwright install | No Chromium starts; no visual snapshots update | package-script inspection + unit test run |
| Run visual check on cold Ladle preview | Test waits for loaded story before screenshot | visual test |
| Reorder/add unrelated stories | Canonical selected set unchanged; no automatic snapshot fan-out | fixed manifest test/source review |
| Run on weak laptop | one worker only; no parallel browser matrix | config assertion/review |
| Visual diff occurs | test fails and emits diff; baseline is not silently rewritten | Playwright contract/manual proof |

## §4 Files in scope — write lease

Exact snapshot names/story IDs are re-anchored at activation from real F1–F3 stories, but the count and categories may not expand.

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/package.json` | Add opt-in visual scripts + Playwright dev dependency |
| Modify | `apps/live-control-ui/package-lock.json` | Exact dependency lock |
| Create | `apps/live-control-ui/playwright.ui.config.ts` | Chromium-only, workers=1, ignored output, Ladle preview web server |
| Create | `apps/live-control-ui/tests/ui-visual.spec.ts` | Fixed canonical story/viewport manifest and screenshot assertions |
| Create | `apps/live-control-ui/src/ui/VisualContract.stories.tsx` | Only if required to expose static ToolHostView canonical states; no new product behavior |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/object-rich-desktop.webp` | Canonical baseline |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/object-rich-narrow.webp` | Canonical baseline |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/object-faction-desktop.webp` | Canonical baseline |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/object-faction-narrow.webp` | Canonical baseline |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/object-relationships-desktop.webp` | Canonical baseline |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/object-relationships-narrow.webp` | Canonical baseline |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/toolhost-overlay-desktop.webp` | Canonical baseline |
| Create | `apps/live-control-ui/tests/ui-visual-snapshots/toolhost-peek-desktop.webp` | Canonical baseline |
| Modify | `Docs/Plans/PLAN-ui-presentation-substrate-sidequest-v1.md` | Backward-looking predecessor sync |

**Bounded discovery exception:**
```text
Directory: apps/live-control-ui/tests/ui-visual-snapshots/
Maximum additional paths: 2
Allowed path kinds: .webp baselines only
Decision rule: only if activation-time story structure makes one narrow ToolHost state and/or one sparse-object state materially necessary; total baselines must remain <= 10
```

## §5 Explicitly out of scope / collision boundary

| Path/capability | Why this slice must not touch or claim it |
|---|---|
| production surface components | Visual infrastructure consumes isolated stories only |
| API/backend tests | Not an E2E product suite |
| browser matrix beyond Chromium | Performance/cost intentionally deferred |
| automatic snapshot of all Ladle stories | Prevents unbounded weak-laptop/CI cost |
| CI workflow files | Add only if repository already has an obvious low-cost UI job and steward separately authorizes; otherwise handback can recommend later |
| Base UI/a11y tooling | Separate capability |
| Canvas | UI-F5 |

## §6 Implementation contract

```text
Input:
  fixed list of existing static Ladle story IDs + named viewport

Output:
  explicit Chromium screenshot comparison against committed WebP baseline

Invariant:
  same as §1

Failure behavior:
  story missing → fail loudly
  story render error → fail loudly
  screenshot difference → fail with diff; never auto-update
  Ladle preview unavailable → fail setup

Replay / idempotency:
  unchanged story/environment → same baseline comparison
  intentional visual change → explicit baseline update reviewed in diff
  unrelated new story → no new screenshot unless manifest deliberately changes

Trust boundary:
  Verifies: selected presentation pixels in one controlled Chromium environment
  Records/trusts without proving: semantic correctness, accessibility, all browsers/OS rendering
```

### A. State / fallback matrix

| Observable path | Loading/init | Exact success | Ordinary miss | Dependency unavailable | Integrity failure | Stale/superseded | Retry/replay |
|---|---|---|---|---|---|---|---|
| visual story | wait for Ladle storyloaded | compare screenshot | missing story = fail | preview/browser unavailable = fail | render/screenshot failure | removed/renamed story = fail until manifest reviewed | safe rerun |

### B. Identity matrix

| Situation | Required rule | Ambiguity behavior | Fallback permitted? |
|---|---|---|---|
| Story ID | exact activation-time Ladle ID | missing/duplicate = fail | No fuzzy title lookup |
| Snapshot name | fixed semantic filename | duplicate = config/test failure | No generated index names |
| Viewport | exact named width/height | n/a | No responsive auto-detection |

### C. Persistence / replay matrix

| Operation | Durable representation | Round-trip guarantee | Duplicate/replay | Compatibility/migration | Rollback/reversion |
|---|---|---|---|---|---|
| visual baseline | committed lossless WebP | same selected story/viewport compares to reviewed baseline | deterministic rerun | baseline changes require explicit review | revert baseline commit |
| test artifacts | ignored `out/` / Playwright temp | not durable authority | replace freely | none | delete |

### D. Predecessor → consumer mapping

**Grounding source:** Ladle `meta.json` from activation-time F1–F3 build.

| Predecessor field/outcome | Real shape | Consumer behavior | Transformation | Proof |
|---|---|---|---|---|
| story ID | exact `meta.json.stories` key | URL `?story=<id>&mode=preview` | none | visual test startup |
| story loaded | `data-storyloaded` marker | wait before screenshot | none | test |
| canonical story category | existing F2/F3 story | map to fixed screenshot filename + viewport | explicit manifest | source review |

## §7 Evidence required to merge

| Guarantee / invariant clause | Owning boundary | Evidence class | Command/scenario | Expected evidence | Stop condition |
|---|---|---|---|---|---|
| Visual suite is opt-in | package scripts | contract | inspect scripts + run ordinary test | no Playwright/browser launch | ordinary test starts browser |
| Selected set bounded | visual spec | contract | count manifest/baselines | <= 10 screenshots | automatic all-story crawl or >10 |
| Single-worker Chromium | Playwright config | performance contract | config + run output | 1 worker, Chromium only | parallel/multi-browser default |
| Ladle stories load deterministically | visual spec | regression | `npm --prefix apps/live-control-ui run ui:visual` | selected stories PASS against baselines | flaky/missing story |
| Visual diff fails closed | Playwright | adversarial/manual | intentionally perturb one token locally without updating baseline, run one case, restore | test reports diff | silent pass/update |
| Production/unit workflow unaffected | frontend | regression | unit test + typecheck + build | no new failures | new failure |
| Exact lease | Git | contract | diff checks | only §4/bounded snapshot paths | unexpected path |

Expected scripts after implementation:

```bash
npm --prefix apps/live-control-ui run ui:build
npm --prefix apps/live-control-ui run ui:visual
npm --prefix apps/live-control-ui run test
npm --prefix apps/live-control-ui run typecheck
npm --prefix apps/live-control-ui run build
git diff --check
git diff --name-only <dispatch-base>...HEAD
```

### Minimal live / dogfood proof

```text
Existing surface: isolated Ladle preview
Smallest realistic scenario: run the visual suite on the target laptop with backend services stopped
Expected observation: one Chromium worker checks <=10 images; ordinary editor/Ladle workflow remains separate
Evidence captured: total cases, elapsed observation, failures/diffs, worker/browser count
```

### Baseline failure handling

Browser binary installation is environment setup, not a product failure. Any story/test/build failure must use exact base/head comparison. Screenshot baselines are generated/reviewed on one declared environment; cross-OS equality is not claimed.

## §8 Required review handback

Record exact selected story IDs, viewport sizes, snapshot count, browser/worker config, commands/results, whether ordinary unit/UI dev scripts remain browser-free, baseline environment, changed snapshot names, and any flakiness observed.

## §9 Acceptance rubric

- [ ] UI-F3 predecessor merged and story IDs re-anchored.
- [ ] Visual run is explicit/opt-in.
- [ ] Chromium only; workers=1.
- [ ] Total committed baselines <=10.
- [ ] Only fixed canonical stories are checked.
- [ ] Ladle storyloaded synchronization is used.
- [ ] Visual diffs fail rather than auto-update.
- [ ] Ordinary unit/UI dev workflow does not start Playwright.
- [ ] No backend/product runtime required.
- [ ] UI-F5 remains false.

## Stop conditions

Stop if:

- stable screenshots require backend/API data;
- F1–F3 stories are not static/deterministic enough;
- test count grows above 10 to feel “complete”;
- multi-browser/CI matrix becomes necessary for the slice;
- Playwright must become part of ordinary `npm test`;
- a second visual-regression framework is proposed;
- screenshot stability requires broad animation/global CSS rewrites.
