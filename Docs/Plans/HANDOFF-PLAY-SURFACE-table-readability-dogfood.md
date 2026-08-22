---
pr_body_template: |
  ## Handoff pointer
  - Workstream: PLAY-SURFACE / Lane A2 table readability + dogfood
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → DOGFOOD → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-SURFACE-table-readability-dogfood.md
  - Branch / PR: agent/play-surface-table-readability / `PLAY-SURFACE: make Play readable at the table`

  ## Verification pointer
  - Design/base anchor: `d4c6fb365b1e8958f6a1989a9f88fcde1b844e73` (merge of PR #625)
  - Predecessor: merged PR #625 / Lane A1 active-Run continuity
  - Base/head: `d4c6fb365b1e8958f6a1989a9f88fcde1b844e73` / <implementation head>
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7 + live continuity/readability dogfood + exact-head screenshots + roadmap review

  The checked-in handoff, cumulative diff, independently rerun evidence,
  dogfood report/screenshots, and exact reviewed-head judgment are the review
  contract. The PR description is transport metadata only.
---

# HANDOFF — make Play readable enough to dogfood at the table

**Created:** 2026-08-20  
**Status:** MERGED / HISTORICAL — PR #626 merged at `a56cf4ab1ea231164db1f5a30fa3d177d8b328a6`; final branch head `f26e6449927d6a509d8cbb71d8798d8a9197015a`; **4 formal review cycles** (Cycles 1–3 REQUEST-CHANGES-equivalent, Cycle 4 PASS-equivalent); readability and same-store active-Run continuity dogfooding PASS (see the Lane A2 report under `Docs/Reports/`); consumed by the current-moment cockpit design gate (`Docs/Plans/HANDOFF-PLAY-SURFACE-current-moment-cockpit-design.md`).  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-SURFACE-table-readability-dogfood.md`  
**Workstream:** `PLAY-SURFACE / Lane A2 table readability + dogfood`  
**Flow / owner:** `PLAY-SURFACE`  
**Direction:** DESIGN → CODE → DOGFOOD → REVIEW  
**Implementation base:** `d4c6fb365b1e8958f6a1989a9f88fcde1b844e73`  
**Suggested branch:** `agent/play-surface-table-readability`  
**PR title:** `PLAY-SURFACE: make Play readable at the table`

> Repository law: `AGENTS.md`.  
> PLAY-SURFACE architecture: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.  
> Play projection: `Docs/Design/DESIGN-play-surface-projection.md`.  
> Parent acceptance roadmap: `Docs/Roadmaps/ROADMAP-con-ready.md`.  
> Living Play sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.  
> C2S27 dogfood evidence: `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`.  
> Predecessor handoff: `Docs/Plans/HANDOFF-PLAY-SURFACE-active-run-continuity.md`.

---

## 0. Re-anchor, predecessor truth, and why this slice exists

Current repository truth at design time:

```text
main:
  d4c6fb365b1e8958f6a1989a9f88fcde1b844e73
  merge of PR #625

PR #625:
  title:                    PLAY-SURFACE: resume the active Run
  final branch head:        54ad6fe916122cc594abb7b63a74f527bbac4f64
  merge commit:             d4c6fb365b1e8958f6a1989a9f88fcde1b844e73
  formal review cycle 1:    REQUEST-CHANGES-equivalent @ 8a054e7e9bc3f1e6d13ec750e3bf68da3a98182d
  formal review cycle 2:    REQUEST-CHANGES-equivalent @ 54ad6fe916122cc594abb7b63a74f527bbac4f64
  passing formal judgment:  none posted before merge
  required U1/U2/U3 dogfood: not run before merge
```

Do not retroactively invent a passing review or a third review cycle. Repository law remains:

```text
one formal reviewer judgment against one distinct head SHA = one review cycle
```

The missing live proof from PR #625 is intentionally **consumed by this PR** rather than waived. This slice therefore has two inseparable outputs:

```text
A. remove the visual/readability blockers that prevent meaningful Play dogfood
B. run the previously-required active-Run dogfood plus a real readability/usability dogfood
```

The styling is not useful without real use, and the real use is not meaningful while the surface is visually unreadable. They are one capability here: **Play is legible and operable enough to evaluate honestly at the table.**

### Source evidence for this pass

The existing C2S27 dogfood report already records a High-severity presentation failure:

```text
READY Table/Runbook + Scene/Beat nav:
  light text on light button backgrounds
  → GM cannot read which control is which
  → Play is unnavigable as a table surface
  → Play must be legible within shared AppChrome, not create a second chrome boundary
```

The follow-up design-agent observation adds:

- the condensed/display-like presentation is too stylized for dense table content;
- body text and controls are too small;
- gray-on-near-black contrast is weak;
- hierarchy and spacing do not support rapid table scanning;
- Play must remain inside shared AppChrome;
- use a plain highly legible body font, larger defaults, stronger contrast, clearer headings, generous line height, and larger controls;
- validate with real Play screenshots at normal viewport size, not only isolated component tests.

### Current CSS facts that explain the observed problem

Current `apps/live-control-ui/src/playSurface/playSurface.css` mixes the dark application shell with light control surfaces without consistently setting foreground colors:

```text
.play-muted                    #5c574e fallback on dark app background
.play-run-list a/button        light #fbf7ef background + color: inherit
.play-mode-toggle button       white background + inherited foreground
.play-nav-list button          white background + inherited foreground
.play-continuity-warning       light #f4eee3 background + inherited foreground
.play-runbook editor           white background
```

The shared application root is dark (`#12141a` / light foreground). That combination is sufficient to create unreadable or weak-contrast states. The Play content also inherits a relatively compact shared wrapper and uses multiple sub-1rem text sizes in high-frequency table UI.

This PR corrects those presentation failures **locally in Play**.

---

## 1. Mission and merge-ready invariant

**Mission:** Remove presentation-level friction so a GM can use the existing Play surface at normal browser zoom long enough to produce trustworthy product dogfood, while preserving the shared AppChrome and all current Play/Run authority semantics.

**Merge-ready invariant:**

> **At the operator's normal table viewport and 100% browser zoom, the existing READY Play surface is plainly legible and operable without squinting, browser zoom, or guessing which control/state is active. Play uses a plain body font, readable body/control sizes, strong foreground/background contrast, clear heading hierarchy, generous line height and spacing, visibly distinct current/selected/focus states, and appropriately sized controls. Table and Runbook views remain inside the existing shared AppChrome and preserve all merged #625 Run/continuity behavior. The exact implementation head is then exercised against real Play state: the full U1/U2/U3 continuity dogfood omitted from #625 is completed, representative table interactions are performed, normal-viewport screenshots are attached and recorded, and the resulting dogfood report truthfully states whether visual readability is now sufficient for continued Play evaluation.**

### What passing this invariant means

If this PR passes, we may say:

```text
true:
  Play presentation is readable enough for continued dogfood
  ordinary /play re-entry has been live-tested against the merged active-Run pointer
  Start New / failed replacement / successful replacement behavior has real-state evidence
  current Play controls can be operated at normal viewport/zoom
  Table and Runbook remain one Play surface inside shared AppChrome
```

### What this PR must NOT claim

Even after a passing readability dogfood, all of these remain separate questions:

```text
native Play's Scene-first information architecture is accepted
Beat/Scene/Decision redesign is complete
Plan → Playable authoring is repaired
Combat is durable
cross-worktree Play/Workspace authority is solved
P3B object sheets are dispatchable
P4 Threat → Combat is dispatchable
Play is product-ready for a full campaign session
```

The C2S27 evidence already rejected the shipped Scene-first table model as the final table instrument. This PR makes that model readable enough to keep learning from it. It does not reverse the structural finding.

---

## 2. Design contract — readability before aesthetics

This is not a visual-brand redesign. It is an explicit **readability and basic usability** pass.

The priority order is:

```text
1. legibility
2. state recognition
3. scan hierarchy
4. control usability
5. density appropriate for a table
6. aesthetic polish
```

Do not sacrifice 1–4 to preserve a stylized visual treatment.

### 2.1 Typography

Play content must explicitly use a plain, highly legible UI/body stack rather than relying on any decorative/display inheritance:

```text
ui-sans-serif / system-ui / platform UI sans fallback
```

No new webfont dependency and no font-file addition in this slice.

Acceptance targets:

- primary authored/body text: **at least 1rem / 16 CSS px** at default browser settings;
- high-frequency button/control labels: **at least 1rem / 16 CSS px**;
- secondary technical metadata may be smaller but should remain comfortably readable; target **>= 0.9rem** and strong contrast;
- body line-height: **>= 1.5**, with a target around 1.55–1.65 for authored prose;
- headings use weight/size/spacing for hierarchy rather than a decorative condensed face;
- technical UUID/revision metadata stays visually subordinate to authored content.

These are steward acceptance targets for this product surface, not a new global design-system contract.

### 2.2 Contrast

All ordinary Play text/control combinations must target at least WCAG-AA-style contrast:

```text
normal text:  >= 4.5:1
large text:   >= 3:1
focus/current/selected boundaries must remain plainly distinguishable from adjacent surfaces
```

Do not rely on gray-on-near-black for essential labels.
Do not combine inherited light text with white/parchment control backgrounds.
Do not encode current/resolved/selected state by subtle color alone.

The worker may choose exact colors, but the palette must remain compatible with the existing dark application shell and shared AppChrome.

### 2.3 Control sizing and focus

High-frequency Play controls must be comfortably clickable at table speed:

- buttons/selectable rows use a minimum block target around **2.5–2.75rem** where practical;
- controls inherit the readable Play font;
- radio/checkbox labels have adequate spacing and a click target that includes the label;
- keyboard `:focus-visible` is obvious;
- disabled state stays legible while still visibly disabled;
- hover/pressed/current states are visually distinct without changing semantics.

No new component library and no new interaction model.

### 2.4 Scan hierarchy and spacing

Improve scanability with CSS and existing semantics:

- page title is immediately identifiable;
- Table/Runbook mode control is visible but subordinate to the title;
- Scenes, Beats, focused authored content, Choices, and Notes are visually separable;
- current/selected Scene and Beat are obvious at a glance;
- authored body has a readable line measure rather than stretching indefinitely;
- Choices/options have enough separation to avoid reading as one undifferentiated block;
- Notes textarea/button read as one action group;
- warnings/errors are high-contrast and do not resemble normal prose;
- vertical rhythm is generous enough for rapid scanning.

Do **not** reinterpret the hierarchy. The current Scene/Beat/Choice DOM remains evidence under test, not accepted future architecture.

### 2.5 Width and responsive behavior inside AppChrome

The current shared `.app-wrap` is narrower than Plan/Ingest at desktop widths. Play may locally request a wider content measure using a Play-scoped selector in `playSurface.css`, including an ancestor selector such as:

```text
.app-wrap:has(.play-surface)
```

This is allowed because it changes only the Play content region **inside the existing AppChrome**.

Requirements:

- do not edit `AppChrome.tsx` or `appChromeConfig.ts`;
- do not create a second header/nav/shell;
- no horizontal page scroll at the operator's normal table viewport;
- if the three-column table becomes cramped, collapse/reflow at a more useful breakpoint rather than shrinking text;
- wide desktop space should benefit authored content instead of leaving it trapped in an unnecessarily narrow center column.

### 2.6 Runbook mode

The read-only Runbook projection must receive the same readability treatment:

- plain font;
- readable size/line-height;
- explicit foreground/background pairing;
- readable headings/lists/tables/callouts inherited through the existing Markdown editor/theme seams;
- no editor chrome is added;
- read-only behavior remains unchanged.

Prefer Play-scoped overrides in `playSurface.css`. Do not modify generic TipTap/Markdown theme authority unless a proven selector/ownership blocker makes local styling impossible; that is a stop-and-report condition for this slice.

---

## 3. Product behavior that must remain unchanged

This is a presentation PR. Preserve merged #625 semantics exactly.

### Play entry grammar

```text
/play?run=<uuid>
  explicit exact Run

/play?choose=1
  explicit chooser / Start New mode

/play
  resolve Play-owned active selection
```

### Active-Run behavior

- bare `/play` resumes only the explicit active Run;
- no latest/first Run inference;
- ordinary re-entry never creates a new Run;
- exact `?run=U` remains authoritative;
- exact READY U may become active;
- blocked/missing/integrity-failed U does not become active;
- active-write failure does not unmount a READY Run;
- Start New is explicit;
- incomplete U2 leaves U1 active;
- successful U3 becomes active only after READY;
- active writes retain the merged serialization fix from #625.

### Runtime mutation behavior

Do not change:

- current Scene/Beat semantics;
- resolved Beat behavior;
- choice selection persistence;
- note persistence;
- `run_revision` CAS;
- manifest admission;
- rebase behavior;
- Start Run UUID allocation.

### Shared shell

There is still exactly one product chrome:

```text
AppChrome
  → Play content
```

No nested/duplicate Play nav bar, no Play-specific chrome contract, no dynamic `?run=` state in shared navigation.

---

## 4. Files in scope — exclusive write lease

### 4.1 Checked-in handoff / predecessor state sync

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-SURFACE-table-readability-dogfood.md` | implementation + dogfood authority |
| Modify | `Docs/Plans/HANDOFF-PLAY-SURFACE-active-run-continuity.md` | mark PR #625 MERGED/HISTORICAL with exact merge/review/dogfood truth |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | consume #625; mark Lane A1 merged, select Lane A2 readability/dogfood as active; add current PR evidence row before final review |
| Modify | `Docs/Roadmaps/ROADMAP-con-ready.md` | consume #625 and current readability/dogfood sequence; keep CR-U17 false overall |
| Modify | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` | re-anchor current Play delivery state |
| Modify | `Docs/Design/INDEX-design-agent-source-set.md` | update repository authority refresh basis only |
| Modify | `Docs/Sources/design-agent/README.md` | update repository export basis only |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | byte-identical mirror |
| Modify | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` | byte-identical mirror |
| Create | `Docs/Reports/REPORT-play-readability-dogfood-2026-08.md` | exact-head continuity + readability dogfood record |

Project Sources snapshot date remains operator-managed. **Do not advance it merely because repository mirrors refresh.**

### 4.2 Frontend implementation

| Action | Path | Purpose |
|---|---|---|
| Modify | `apps/live-control-ui/src/playSurface/playSurface.css` | Play-local typography, contrast, spacing, controls, focus, width, responsive layout, Runbook readability |

### 4.3 Bounded discovery exception

Maximum **two** additional frontend files, only if the existing DOM lacks a styling/accessibility hook required to satisfy §1:

1. `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx`
2. `apps/live-control-ui/src/playSurface/PlaySurfacePage.tsx`

Allowed changes in those files:

- add/rename Play-local `className` hooks;
- add non-controversial semantic wrappers/labels needed for styling or accessibility;
- improve presentation-only copy where the current wording is unreadable/ambiguous in context.

Forbidden through this exception:

- state-machine changes;
- Run/manifest/progress API changes;
- current Scene/Beat behavior changes;
- new view modes;
- new data derivation;
- hiding/reordering semantic content to simulate the Beat-first redesign;
- new toolbar/chrome ownership.

If another production path is required, stop and return to stewardship before editing it.

### 4.4 Test files

Do not edit tests merely to create churn. If §4.3 introduces a semantic/DOM change that requires proof, the only test paths additionally allowed are:

- `apps/live-control-ui/src/App.test.tsx`
- `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx`

A pure CSS implementation should normally need **zero test-file changes**; visual proof comes from the exact-head screenshots and dogfood report.

---

## 5. Explicitly out of scope

Do not modify or claim:

```text
apps/live-control-ui/src/chrome/AppChrome.tsx
apps/live-control-ui/src/chrome/appChromeConfig.ts
apps/live-control-ui/src/styles.css
apps/live-control-ui/src/planSurface/**
apps/live-control-ui/src/buildSurface/**
apps/live-control-ui/src/tiptap/**
apps/live-control-ui/src/surfaceInteraction/** ownership contracts
apps/live-control-ui/src/graphReference/**
apps/live_control_server/**
tests/test_live_play_active_run.py
tests/test_play_active_run.py
Combat runtime/tracker files
WorkspaceDocument authority
Play Run registry/manifest/rebase/progress services
DungeonMind / DungeonMindDnD packages
```

Specifically forbidden:

- a second Play chrome/header/navigation boundary;
- changing shared AppChrome visual/ownership behavior;
- adding a new font dependency or committing font files;
- global application theme redesign;
- dark/light mode implementation;
- Beat/Scene/Decision structural redesign;
- moving Scene/Beat/Choice DOM to approximate future architecture;
- Plan→Playable repair;
- Combat durability;
- P3B graph-object sheets;
- P4 Add to Combat;
- active-Run persistence changes;
- cross-worktree storage migration;
- generic persistence/database work;
- Run cleanup/lifecycle;
- hiding UUID duplicates as a substitute for lifecycle policy.

This pass is allowed to make the current surface **readable**, not to make the rejected structure look finished.

---

## 6. Implementation guidance and critique gates

### 6.1 Preferred implementation shape

The expected implementation is mostly one CSS diff.

A good result should resemble:

```text
playSurface.css
  Play-local font stack
  Play-local text/contrast variables or explicit pairings
  readable heading/body/control sizes
  focus/hover/current/selected treatment
  dark-shell-compatible control surfaces
  wider Play content region within app-wrap
  responsive collapse before columns become cramped
  readable authored content / choices / notes
  readable read-only ProseMirror
```

Do not create a design-token subsystem for one surface.

### 6.2 Do not overfit to screenshots

Screenshots are acceptance evidence, not pixel-perfect golden files.

Do not:

- hard-code one viewport height;
- absolute-position content to match one screenshot;
- truncate authored content to create visual cleanliness;
- reduce information density by hiding important controls/content;
- use extremely large typography that makes table scanning slower;
- tune around one specific Run UUID/title length.

### 6.3 Contrast is a computed-style problem

Before changing markup, inspect the actual computed Play styles in the browser. In particular verify:

- inherited `color` on light control backgrounds;
- `.play-muted` against the actual dark shell;
- button/link text in chooser/nav/mode controls;
- warning text/background;
- read-only ProseMirror text/background;
- current/selected states;
- focus-visible ring/border.

If the observed condensed/stylized face comes from a shared selector, first attempt a Play-local override. Do not edit shared chrome/theme ownership merely because inheritance exists.

### 6.4 Current three-column layout is not sacred

Responsive presentation may change without changing information architecture.

Allowed:

```text
wide viewport:
  Scenes | Beats | Focused content

narrow/cramped viewport:
  Scenes
  Beats
  Focused content
```

Not allowed:

```text
Beat becomes new parent of Scenes
Decisions are re-modeled
new current-moment deck semantics
```

The breakpoint should protect readable text/control sizes rather than preserve three columns at all costs.

### 6.5 Dogfood repairs stay in this PR only when they are presentation defects

The dogfood is expected to find issues.

If the operator finds:

```text
text too small
contrast too weak
control hard to identify/click
spacing/hierarchy unreadable
content clipped/overflowing
responsive layout cramped
```

repair that in this PR, recapture screenshots on the new head, rerun evidence, and re-review the distinct head.

If the operator finds:

```text
wrong hierarchy
missing decision semantics
Plan export loss
missing object sheet
Combat persistence failure
Run authority/storage problem
```

record it in the report and **do not fix it here**. That is product/design evidence for the next re-anchor.

---

## 7. Evidence required to merge

This PR does not pass on unit tests alone.

The required evidence stack is:

```text
A. scoped implementation verification
B. exact-head normal-viewport screenshots
C. carried-forward #625 U1/U2/U3 continuity dogfood
D. representative Play readability/usability dogfood
E. completed dogfood report
F. roadmap review disposition
G. final formal review against the exact evidence head
```

### 7.1 Static / frontend verification

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/App.test.tsx \
  src/playSurface/StartRunPanel.test.tsx \
  src/playSurface/startRunAttempt.test.ts \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx

pnpm run typecheck
pnpm run build
```

If no TS/TSX behavior changed, existing tests are regression evidence only; they do not prove readability.

Repository checks:

```bash
git diff --check

git diff --name-only d4c6fb365b1e8958f6a1989a9f88fcde1b844e73...HEAD
```

Every changed path must be within §4.

Mirror identity:

```bash
diff Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md

diff Docs/Roadmaps/ROADMAP-con-ready.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md

diff Docs/Plans/STEWARDS-ANCHOR-con-ready.md \
  Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md

diff Docs/Design/INDEX-design-agent-source-set.md \
  Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md
```

Every `diff` must produce no output.

### 7.2 Dogfood runtime topology — use real state without moving authority

PR #625's isolated worktree could not run the required dogfood because Play state is checkout-local. This style PR must not solve that by moving storage.

Preferred setup:

```text
backend:
  run merged-main backend from the operator checkout that already owns the real Play state
  (main includes #625 active-Run backend; this PR changes no backend code)

frontend:
  run the PR candidate frontend from the isolated readability worktree
  against that backend

result:
  exact candidate CSS/UI
  + real existing operator Run/manifest/workspace authority
  + no copy/migration of out/runtime/play/**
```

Name the actual ports/checkouts used in the report if they differ from the normal dev setup. Avoid running two backends against the same state store concurrently.

If the normal frontend proxy cannot target the operator-state backend without changing source/config in a forbidden path, stop and report the setup blocker rather than broadening this PR.

### 7.3 Exact-head screenshot evidence

Screenshots must be captured from the same implementation head that will receive final review.

Use:

- the operator's normal table browser;
- the operator's normal table viewport/window size;
- **100% browser zoom**;
- no devtools emulation unless recording an additional responsive check.

Record in the report:

```text
browser + version
OS
viewport CSS width × height
browser zoom
implementation head SHA
Run UUID
Runbook title/revision
```

Attach at least these screenshots to the PR conversation and link/identify them from the checked-in dogfood report:

1. **READY Table — top/primary scan**
   - shared AppChrome visible;
   - title, metadata, Table/Runbook toggle;
   - Scenes/Beats/focused content visible.
2. **READY Table — interaction density**
   - representative authored body plus controls/Choice/option/Notes where available;
   - current/selected states visible.
3. **Runbook mode**
   - representative full-document prose/headings at the same normal viewport.
4. **Chooser / Start New**
   - existing Runs + Start Run state, proving the continuity flow is also legible.

If one screenshot cannot naturally contain Choice/Notes because the real material lacks them, state that rather than manufacturing fake campaign content; use another real Run/material if available.

### 7.4 Carry-forward continuity dogfood from #625 — mandatory

Complete the live proof that #625 required but did not run.

Use a real existing READY Run `U1` in the operator-owned Play store.

```text
1. Open /play?run=U1 and confirm READY.
2. Navigate to Plan or another primary surface.
3. Use shared AppChrome → Play.
   PASS: bare /play resumes exact U1 without chooser and without creating a Run.
4. Hard refresh.
   PASS: U1 remains exact.
5. Close/reopen the browser tab or browser; reopen /play.
   PASS: U1 resumes from server-side active selection.
6. Restart the backend against the same state store; reopen /play.
   PASS: U1 resumes.
7. Click Start New Run.
   PASS: chooser/start UI appears; U1 remains active; no new Run exists merely from entering chooser.
8. Produce one controlled incomplete/blocked replacement attempt U2.
   PASS: U2 never reaches READY and does not replace U1 as active.
9. Return through ordinary /play.
   PASS: U1 resumes.
10. Complete one successful explicit replacement Run U3 through normal StartRunPanel + READY admission.
    PASS: U3 becomes active only after READY.
11. Leave Play and return through shared nav.
    PASS: exact U3 resumes.
12. Compare before/after `out/runtime/play/runs/` filenames.
    PASS: only deliberate explicit Start attempts created Run UUIDs; navigation/reload/chooser entry created none.
```

Record:

```text
U1 UUID
U2 UUID
U2 failure/blocked mechanism and observed state
U3 UUID
before Run filenames
final Run filenames
active-run.json final run_id
backend restart point
```

Do not delete historical Runs to make the evidence cleaner.

### 7.5 Readability/basic-usability dogfood — mandatory

Against READY U1 or U3, perform a short real operator rehearsal using representative session material.

At 100% zoom, without changing browser zoom during the exercise:

```text
A. scan the page and identify the Runbook title, current/selected Scene, current/selected Beat, and focused authored content;
B. navigate to a different Scene and Beat;
C. set the current Scene and current Beat using existing controls;
D. toggle one Beat resolved/unresolved if safe for the dogfood Run;
E. select/change one Choice option if the material contains a Choice;
F. enter and save a short Note, then verify the persisted note remains readable;
G. switch Table → Runbook → Table;
H. use Start New → chooser, then return to the active Run;
I. use at least one keyboard Tab sequence through the primary Play controls and verify focus is obvious;
J. inspect one warning/banner state if naturally available; do not corrupt live data merely to manufacture one.
```

The operator then answers these explicit questions in the report:

| Question | PASS criterion |
|---|---|
| Can body prose be read comfortably at 100% zoom? | no zoom/squinting required |
| Can control labels be read and clicked at table speed? | no tiny targets/ambiguous labels |
| Is current/selected state obvious? | Scene/Beat/mode state recognized without reading implementation metadata |
| Is muted/secondary text still readable? | no low-contrast gray-on-dark loss |
| Are headings enough to scan quickly? | title/section/content hierarchy apparent in a few seconds |
| Does authored content have comfortable line-height/measure? | no dense wall or extreme line length |
| Does the layout avoid horizontal page scroll? | yes at normal viewport |
| Is Runbook mode equally legible? | yes at normal viewport/zoom |
| Is shared AppChrome still the only chrome? | yes; no duplicate shell/nav |
| Did styling hide a structural product problem? | no; structural friction remains recorded explicitly |

If any first-eight readability criteria fail materially, the PR is **not merge-ready**. Repair CSS, recapture exact-head screenshots, and rerun the relevant dogfood portion.

### 7.6 Contrast/computed-style spot check

The dogfood report records computed foreground/background and contrast for at least these representative states using browser devtools or an equivalent local contrast inspector:

- primary authored body text;
- `.play-muted` / secondary metadata;
- normal nav/button text;
- current/selected nav/button state;
- warning/banner text;
- read-only Runbook body text.

The report may record pass/fail rather than dumping excessive decimal precision, but any normal-text pair below the stated target requires repair before passing.

### 7.7 Dogfood report contract

Create and complete:

`Docs/Reports/REPORT-play-readability-dogfood-2026-08.md`

Required structure:

```text
# Report — Play readability + active-Run dogfood

Status
Implementation head
Base / predecessor merge
Environment / viewport / zoom
Exact Run identities U1/U2/U3
Before/after Run-store inventory
Screenshot evidence

## Continuity result
PASS / BLOCKED
step-by-step observations

## Readability result
PASS / BLOCKED
question matrix
contrast spot checks

## Friction found
presentation defects repaired in this PR
structural/product defects deferred

## Roadmap consequence
ROADMAP_REVIEW — UPDATED
or
ROADMAP_REVIEW — NO DESIGN CHANGE

## Recommendation
what is now safe to dogfood next
what remains false
```

Final review must not accept `NOT RUN`, placeholder UUIDs, missing screenshots, or a report captured from an older head.

### 7.8 Roadmap review

Before final passing review, deliberately re-read the living roadmap against the dogfood evidence.

Add the current PR's ledger row with exactly one disposition:

```text
ROADMAP_REVIEW — UPDATED
<evidence changed sequence/assumption/ownership; say how>
```

or:

```text
ROADMAP_REVIEW — NO DESIGN CHANGE
<readability/continuity evidence does not change the existing structural redesign/persistence posture; say why>
```

Do not use the readability pass to declare the Scene-first architecture accepted merely because the styled surface becomes usable.

---

## 8. Review contract

Formal review is against one exact distinct PR head SHA.

A reviewer must independently verify:

1. `main` base was `d4c6fb365b1e8958f6a1989a9f88fcde1b844e73` at dispatch or the handoff was truthfully re-anchored before implementation;
2. every changed path is inside §4;
3. PR #625 is synchronized backward-looking as merged at `d4c6fb365...`, final branch head `54ad6fe...`, **2 formal review cycles**, no passing formal judgment before merge, and live dogfood omitted there;
4. the new PR does not retroactively invent #625 review/dogfood evidence;
5. implementation is genuinely presentation-focused;
6. no backend, active-Run semantics, Run schema, progress, manifest, rebase, StartRun UUID allocation, or storage root changed;
7. no AppChrome component/config change or second Play chrome exists;
8. plain readable Play typography is explicit and does not add a font dependency;
9. light/dark foreground-background pairings are coherent and high-contrast;
10. body/control sizes, line-height, current/selected states, focus, and responsive behavior meet the dogfood intent;
11. Runbook mode is also readable;
12. the screenshots are from the exact reviewed head, normal operator viewport, 100% zoom, and include shared AppChrome;
13. the U1/U2/U3 continuity dogfood is complete with exact identities and Run-store inventory;
14. ordinary navigation/reload created zero Run UUIDs;
15. the readability rehearsal is complete and any material presentation failures found were repaired before review;
16. structural findings were recorded rather than smuggled into this PR;
17. the dogfood report contains a roadmap review disposition;
18. canonical/mirror authorities are byte-identical;
19. frontend tests/typecheck/build and `git diff --check` pass on the exact reviewed head.

A fix commit after formal review creates a new head. Its screenshots/dogfood evidence must still correspond to the repaired head for any presentation change that could affect the observed result, and the distinct head must receive a new formal review cycle before merge.

---

## 9. Predecessor state-authority sync details

This PR consumes PR #625. Synchronize the following facts atomically with implementation:

### `HANDOFF-PLAY-SURFACE-active-run-continuity.md`

Mark:

```text
MERGED / HISTORICAL
PR: #625
final branch head: 54ad6fe916122cc594abb7b63a74f527bbac4f64
merge: d4c6fb365b1e8958f6a1989a9f88fcde1b844e73
formal review cycles: 2
Cycle 1: REQUEST-CHANGES-equivalent @ 8a054e7e...
Cycle 2: REQUEST-CHANGES-equivalent @ 54ad6fe9...
passing review before merge: none
required live U1/U2/U3 dogfood before merge: not run
```

Name this readability/dogfood PR as the consuming slice carrying the missing live proof.

### `ROADMAP-playable-hoist-dungeonmind-kernel.md`

Backward-looking truth at the start of this PR:

```text
Integration tip: d4c6fb365... (#625 merge)
Lane A1 implementation: MERGED
Lane A1 live proof: incomplete at merge; carried into Lane A2
Current active slice: Lane A2 table readability + dogfood
Lane B: still collision-gated on retained Combat-save worktree unless a fresh re-anchor proves otherwise
Beat/Scene/Decision + Plan→Playable redesign: still required before another structural native Play implementation
P3B/P4: still deferred
```

Add a #625 ledger row. Suggested design consequence:

```text
Active-Run continuity landed as a bounded Play-owned pointer and preserved the domain-first persistence posture.
The merge itself did not supply the required real-state dogfood, so the next Play slice must complete that proof before treating Lane A1 as operationally validated.
No generic shared persistence primitive is justified by #625 alone.
```

Before this PR's final review, add this PR's own evidence row as required by §7.8.

### `ROADMAP-con-ready.md` / `STEWARDS-ANCHOR-con-ready.md`

Record:

- #625 implementation merged;
- same-store active-Run continuity is implemented but awaits/receives real proof in this slice;
- CR-U17 remains false overall because cross-worktree Playable/workspace/Combat durability is not solved;
- readability is now an explicit prerequisite to meaningful native Play dogfood;
- structural Beat/Scene/Decision redesign remains a separate reviewed design task.

### source-set/index mirrors

Refresh repository authority basis to `d4c6fb365...` plus the active Lane A2 slice where appropriate.
Do not advance the Project Sources snapshot date unless the operator actually refreshes that user-managed source set.

---

## 10. Post-merge state / successor guidance

If this PR passes dogfood and merges, the next re-anchor should be able to state:

```text
Lane A1 implementation:
  merged

Lane A1 operational validation:
  completed by Lane A2 dogfood

Play presentation:
  readable enough for continued dogfood

Still unresolved:
  Beat/Scene/Decision + Plan→Playable model
  cross-worktree Play/Workspace persistence
  durable Combat / Lane B collision gate
  object-sheet and Threat→Combat deferred work
```

Do **not** pre-authorize a successor in this handoff.

The dogfood may change priority. For example:

- if visual readability was the dominant remaining blocker and the current structural model can now be evaluated, re-anchor on the observed structural/product friction before selecting the Beat/Scene/Decision design task;
- if the operator immediately returns to Combat because Combat remains the useful table instrument, that is evidence for Lane B priority after its worktree collision is resolved;
- if active-Run continuity fails under real state, reopen that specific Play-owned contract rather than masking it with more styling;
- if cross-worktree state remains the dominant issue, design that persistence slice explicitly rather than broadening this PR after the fact.

The purpose of this pass is to make subsequent dogfood **trustworthy**, not to predetermine what the dogfood must conclude.
