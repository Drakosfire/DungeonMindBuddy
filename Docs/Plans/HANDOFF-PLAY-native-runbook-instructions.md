---
pr_body_template: |
  ## Handoff pointer
  - Workstream: PLAY-SURFACE / Playable Architecture Graduation / dogfood bridge D2
  - Flow: PLAY-SURFACE
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md
  - Branch / PR: agent/play-native-runbook-instructions / `PLAY: expose exact Runbook instructions`

  ## Verification pointer
  - Design/base anchor: `a0e03bed359dce094a18a5a5824d07487fe4b490`
  - Predecessor: merged PR #621 / Start Run dogfood bridge
  - Base/head: `a0e03bed359dce094a18a5a5824d07487fe4b490` / <implementation head>
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7 + roadmap review disposition

  The checked-in handoff, cumulative diff, nano-commit story, and independently
  rerun verification are the review contract. The PR description is transport
  metadata only.
---

# HANDOFF — expose the exact admitted Runbook beside the native Play table deck

> **MERGED / HISTORICAL (2026-08-20 sync):** PR **#622** merged as
> `62f7f9e856327247b8677b4c951801e4c58a826c` after **1 formal review cycle**.
> Implementation/evidence head `b923117bd7767884053bbe32f25043c7cfe8dcab`;
> final reviewed head `c549611a889bc132d385e536ccc675ca695b356c`.
> D2 proved a full read-only exact Runbook view beside the native `/play` Table deck.
> The C2 Session 27 real-table dogfood that followed accepted that exact
> lifecycle/admission/runtime wiring and rejected the native three-column Table
> presentation as the table instrument (**BLOCKED / PLAY NOT READY** —
> `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`).
> The D4 current-Beat table-stage successor (PR #623) was closed unmerged.
> Current sequence lives in `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`:
> Lane A (active-Run continuity) and Lane B (durable Combat state), then the
> Beat/Scene/Decision + Plan→Playable design task. P3B remains designed but deferred.

**Created:** 2026-08-19  
**Status:** MERGED / HISTORICAL — PR #622 / `main` `62f7f9e856327247b8677b4c951801e4c58a826c` after **1 formal review cycle**. Implementation/evidence head `b923117bd7767884053bbe32f25043c7cfe8dcab`; final reviewed head `c549611a889bc132d385e536ccc675ca695b356c`. This file is not current dispatch authority.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md`  
**Workstream:** `PLAY-SURFACE / Playable Architecture Graduation / dogfood bridge D2`
**Flow / owner:** `PLAY-SURFACE`
**Direction:** DESIGN → CODE → REVIEW  
**Implementation base:** `a0e03bed359dce094a18a5a5824d07487fe4b490`  
**Suggested branch:** `agent/play-native-runbook-instructions`  
**PR title:** `PLAY: expose exact Runbook instructions`

> Repository law: `AGENTS.md`.
> Playable authority: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.
> Play product design: `Docs/Design/DESIGN-play-surface-projection.md`.
> P3A projection predecessor: `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`.
> D1 lifecycle predecessor: `Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md`.
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.

---

## 0. Re-anchor, predecessor sync, and design decision

Current repository truth at design time:

```text
main:
  a0e03bed359dce094a18a5a5824d07487fe4b490

D1 / PR #621:
  merged:                  a0e03bed359dce094a18a5a5824d07487fe4b490
  implementation/evidence 8dc1bad2ac4d85906975a6936861e52a3f043e70
  final reviewed head:    11f5724f5ec7ce7158906cfdcce249c532cbd38e
  formal review cycles:   2

native /play now has:
  explicit existing Run chooser
  explicit Start Run from one chosen committed Runbook
  exact Run + sealed manifest + committed Runbook admission
  Scene / Beat / Choice / Option table deck
  existing P2 Runtime mutations under run_revision CAS

remaining dogfood gap:
  Play shows the focused Scene/Beat projection but does not let the GM read the
  rest of the exact committed Runbook without leaving the table surface.
```

### Backward-looking atomic state-authority sync carried by this PR

This implementation consumes merged D1 / PR #621. Per `AGENTS.md`, the PR must atomically reconcile mutable authorities that still describe D1 as in flight.

Update together in this implementation PR:

1. `Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md`
   - mark D1 / PR #621 **MERGED / HISTORICAL**;
   - record merge SHA `a0e03bed359dce094a18a5a5824d07487fe4b490`;
   - record implementation/evidence head `8dc1bad2ac4d85906975a6936861e52a3f043e70`;
   - record final reviewed head `11f5724f5ec7ce7158906cfdcce249c532cbd38e`;
   - record **2 formal review cycles**;
   - name this D2 Runbook-view capability as the consuming successor.
2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - replace the D1 `this PR` row with merged PR #621 truth;
   - mark D1 complete without changing its accepted design consequence;
   - move the mutable integration tip to `a0e03bed...`;
   - select this D2 capability as current next;
   - add the D2 review row only when implementation evidence is truthfully known;
   - do **not** pre-mark D2 complete.
3. `Docs/Plans/HANDOFF-PLAY-SURFACE-native-graph-object-sheet.md`
   - keep P3B **NON-DISPATCHABLE**;
   - update the sequencing precondition so Start Run is now complete, D2 is current, and live dogfood/re-anchor still precede P3B.

Do **not** edit stable architecture/design authorities merely to record that #621 merged. Their ownership claims did not change.

### Product/design decision for D2

Do **not** create a `briefing` schema or classify planning prose by heading text.

The first dogfoodable contract is deliberately simpler:

```text
native Play
├── Table      ← existing Scene / Beat / Choice / Option projection; default
└── Runbook    ← full exact committed Runbook, rich and read-only
```

The Runbook view is the same exact admitted document already used to build the table deck. It is not a second fetch, a copied document, or a separately persisted briefing.

This choice intentionally allows authored material such as:

- Session intent;
- current play state;
- memory/context;
- pressures;
- GM decisions/reminders;
- NPC notes;
- decision forks;
- exit ramps;
- open questions;
- reference material;
- planning principles;

without teaching Play that any of those labels are durable element kinds.

The focused Table view remains the default so Play does not dump a long prep document into the GM's primary table stage.

---

## §1 Mission and merge-ready invariant

**Mission:** While running one exact admitted Run in native `/play`, the GM can switch between the focused table deck and a rich read-only view of that same exact committed Runbook, then return without the mode switch mutating Runtime or replacing the admitted document.

**Merge-ready invariant:**

> **Table mode and Runbook mode are two Play-owned projections of one P3A-admitted Run binding: the Runbook view renders only the TipTap document imported from the exact committed workspace snapshot already admitted against the Run + sealed manifest; it never fetches or substitutes a newer/default document, never creates a second persisted briefing/instruction authority, never makes ordinary Runbook prose Runtime-addressable, and never writes Run/Runbook/World/Mechanics state. Table remains the default. Switching modes alone preserves the component's current table focus and produces zero Runtime writes; any authoritative Run update continues to follow existing P3A/P2 overlay behavior. Ordinary unmarked Runbook-level H1/H2 sections terminate a preceding playable body slice so global instructions after a Scene/Beat are not silently projected as that element's body, while the existing Scene/Beat/Choice/Option marker grammar and identities remain unchanged.**

### Pre-dispatch critique

| Question | Answer |
|---|---|
| Can one invariant govern every claimed observable path? | **Yes.** Exact-document derivation, read-only rendering, mode switching, and the Runbook-level ownership boundary all exist so one admitted Runbook can be used both as focused table structure and as full instructions without creating competing authority. |
| Most dangerous adversarial sequence | Run U is admitted to Runbook R@7/SHA-A → workspace advances to R@8/SHA-B → GM opens Runbook mode. D2 must show only admitted R@7/A or remain blocked under existing P3A admission; it must never fetch/render R@8/B beside the old Runtime binding. |
| Second dangerous sequence | GM focuses Beat B2 locally → opens Runbook → returns to Table. The mode switch must not call Runtime APIs or reset focus to preview/current merely because the full-document view mounted. |
| Third dangerous sequence | Last playable Beat is followed by ordinary `## Open questions`. Existing flat body slicing would treat that H2 section as Beat body. D2 must recognize ordinary root H1/H2 as Runbook-level boundaries so those instructions remain outside the Beat projection. |
| Would §7 detect those failures? | **Yes.** Projection tests prove exact imported document reuse and H2 ownership boundaries; component tests prove rich Runbook visibility, zero writes on switch, and return-to-focus. |
| Easiest owning boundary to under-test | The boundary between full-document rendering and P3A's flattened playable body slices. Both views must come from one admitted import without redefining durable structure. |
| Stop/split trigger | If useful instructions require durable semantic IDs, a heading-name ontology, a new backend parser/API, editable Play document state, or reference-opening behavior, stop. Those are separate Plan/P3B/editing capabilities. |

---

## §2 Context, authority, and boundaries

### Read authoritative inputs in this order

1. `AGENTS.md`
2. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
3. `Docs/Design/DESIGN-play-surface-projection.md`
4. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
5. `Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md`
6. `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`
7. `Docs/Plans/HANDOFF-PLAY-SURFACE-native-graph-object-sheet.md`
8. `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts`
9. `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts`
10. `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx`
11. `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx`
12. `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx` — **read/reuse; expected no modification**
13. `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts` — **read only**

### Existing predecessor contract — do not redesign it

P3A already admits one exact Runbook by requiring:

```text
PlayRunRecord
+ sealed PlayRunReferenceManifest
+ active committed workspace Runbook snapshot
+ exact revision equality
+ exact content SHA equality
+ P1 Markdown import validity
+ client P1 structure == sealed manifest membership
```

Only after those checks does `admitNativeRunbook(...)` return `status: "ready"`.

D2 consumes that READY projection.

The existing admission already imports the exact snapshot Markdown with `markdownToTiptapDoc(...)` before building the Scene/Beat deck. D2 should carry that admitted imported document forward as Play-local derived projection data rather than importing/fetching a different source later.

`MarkdownEditorCore` already supports `editable={false}` with the same extension family used by workspace documents. Reuse it; do not create a second Markdown renderer.

### Boundary table

| Field | Required content |
|---|---|
| Parent authority | `ARCHITECTURE-playable-material-and-runtime.md` + `DESIGN-play-surface-projection.md` |
| Base revision | `a0e03bed359dce094a18a5a5824d07487fe4b490` |
| Predecessor | merged #621 Start Run + merged P3A exact native Runbook admission |
| Exact input consumed | one `NativeRunbookReadyDeck` produced from exact Run + manifest + committed snapshot |
| Durable writes | **none added**; existing Runtime writes remain Table-only behavior |
| New durable representation | **none** |
| New semantic vocabulary | **none** |
| Named successor | **occurred:** D3 C2 Session 27 real-session dogfood (verdict BLOCKED / PLAY NOT READY) → post-dogfood re-anchor. The D4 current-Beat table-stage PR #623 was closed unmerged. Re-anchor before selecting any new Play table, P3B, or Plan-authoring work |
| What remains false | Play does not semantically extract “pressure”, “GM decision”, “open question”, etc.; Runbook mode is read-only; graph references do not open natively; no interactive planning review UI |

### Lane / collision review

Open PR #578 remains a historical/mining Play branch and is not implementation authority for this slice.

Rules:

- branch from exact `a0e03bed...` in an isolated checkout/worktree;
- do not cherry-pick/merge #578;
- do not borrow #578 Runbook/prep rendering paths as authority;
- re-anchor if another active PR begins modifying the D2 code paths below;
- central docs in §4 are this lane's expected write lease while active.

---

## §3 Observable paths and adversarial sequences

### Product shape

At READY, the existing Runbook header gains a small explicit mode control:

```text
[ Table ] [ Runbook ]
```

Rules:

- `Table` is selected by default on initial READY/reload;
- `Runbook` is deliberate and read-only;
- switching modes is local projection state, not Runtime state;
- do not persist mode selection in Run JSON or localStorage in this slice;
- do not add a third “Briefing” document or sidebar authority;
- do not auto-open Runbook mode because unmarked prose exists.

### Table mode

Table mode remains the current P3A behavior:

- Scenes navigation;
- Beats navigation;
- focused authored Scene/Beat bodies;
- Choices/Options;
- Runtime notes;
- Runtime mutation controls.

D2 must not alter Scene/Beat/Choice/Option identity, manifest membership, CAS, or navigation semantics except for the specific ordinary root H1/H2 body-boundary correction described below.

### Runbook mode

Runbook mode renders the **entire exact admitted Runbook document** using the existing TipTap read-only stack.

Required:

- headings remain headings;
- lists remain lists;
- blockquotes/callouts/tables/references use existing admitted editor rendering where supported;
- Playable marker comments themselves are not shown as user-facing prose;
- no toolbar;
- no editable state;
- no Save action;
- no Runtime controls inside the document;
- no re-fetch of workspace document content;
- no parsing/classification based on display heading labels;
- graph/source/reference nodes may render according to existing read-only editor behavior, but D2 adds **no open/resolution action**.

### Runbook-level instruction boundary

D2 needs one structural correction so ordinary Runbook instructions can safely occur after playable material.

Current `slicePlayableBodies(...)` starts a body at a Playable heading and ends only at the next Playable heading. That can incorrectly absorb later Runbook-level sections into the final Scene/Beat/Choice/Option body.

Required rule:

```text
A Playable body slice ends at:
  1. the next canonical Playable heading; OR
  2. an ordinary unmarked document-root H1/H2 heading.
```

The unmarked H1/H2 and following ordinary content are not given a durable identity and are not added to the sealed manifest. They remain ordinary Runbook prose visible in Runbook mode.

Unmarked H3/H4+ content may remain inside the current Playable body as today; this preserves useful authored subheadings such as GM Note / Read aloud / Consequences without creating new element kinds.

Do not change marker syntax or server manifest derivation.

### Required adversarial proofs

#### A. Workspace advances after Run binding

```text
Run U admitted against R@7 / SHA-A
→ workspace becomes R@8 / SHA-B
→ GM opens / reloads Play
```

Existing P3A behavior remains authority: no READY deck against the mismatched workspace, therefore no Runbook view of R@8 appears beside U@7.

D2 must not add a second fetch that bypasses this block.

#### B. Mode switch cannot mutate Runtime

```text
focus Beat B2 locally
→ click Runbook
→ inspect full document
→ click Table
```

Required:

- zero `putPlayRunProgress` calls from either mode switch;
- focused B2 returns when no authoritative Run change occurred;
- runtime current/resolved/selection/note state is unchanged.

#### C. Global instructions after a Beat

```text
### Beat: Breach   [canonical Beat marker]
Beat-specific prose

## Open questions   [ordinary unmarked H2]
- Does Tealeaf answer?
- How much wall falls?
```

Required:

- `Beat: Breach` body contains Beat-specific prose only;
- `Open questions` is visible in full Runbook mode;
- no new Playable element or Runtime-referenceable ID is created.

#### D. Full Runbook includes playable and ordinary prose from one import

Required:

- the read-only document contains Session Intent / pressures / open questions and the authored Scene/Beat headings from the same admitted snapshot;
- Table mode still derives its Scene/Beat list from the existing P1 structure + manifest contract;
- no second Markdown parser or alternate serialization path is introduced.

---

## §4 Files in scope — exclusive write lease

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md` | checked-in D2 implementation authority |
| Modify | `Docs/Plans/HANDOFF-PLAY-start-run-from-runbook.md` | atomic backward-looking D1/#621 merged/historical sync |
| Modify | `Docs/Plans/HANDOFF-PLAY-SURFACE-native-graph-object-sheet.md` | keep P3B non-dispatchable; advance sequencing facts through completed D1/current D2 |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | record D1 complete + current `a0e03bed...` integration tip + select D2; do not pre-mark D2 complete |
| Modify | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts` | carry exact admitted imported document forward and enforce ordinary root H1/H2 body boundary |
| Modify | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | prove exact-document projection + body-boundary semantics + unchanged admission |
| Modify | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx` | add explicit Table/Runbook local projection mode and read-only full-document rendering |
| Modify | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx` | owning UI proofs: rich instructions, zero mode-switch writes, focus return, Table regression |
| Modify | `apps/live-control-ui/src/playSurface/playSurface.css` | minimal mode-control/read-only Runbook presentation |

### Bounded discovery exception

Not applicable by default.

If implementation proves that `MarkdownEditorCore` cannot render the already-imported document read-only without a Play-local wrapper, stop and report the exact seam. Do not silently modify shared TipTap/editor infrastructure or add a new renderer.

---

## §5 Explicitly out of scope

Do not modify or claim:

```text
apps/live_control_server/**
apps/live-control-ui/src/api/**
apps/live-control-ui/src/planSurface/**
apps/live-control-ui/src/buildSurface/**
apps/live-control-ui/src/workspaceDocument/**
apps/live-control-ui/src/tiptap/markdown/**
apps/live-control-ui/src/tiptap/playable/** marker grammar / identity
apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx
apps/live-control-ui/src/graphReference/**
apps/live-control-ui/src/agentInteraction/**
apps/live-control-ui/src/surfaceInteraction/**
Combat runtime/mutation
World Graph persistence
DungeonMind / DungeonMindDnD packages
```

Specifically forbidden:

- new `briefing`, `pressure`, `gm-decision`, `npc-cue`, `exit-ramp`, `open-question`, or similar durable element kind;
- heading-text classifiers such as `if title === "Session intent"`;
- extracting/copying ordinary Runbook prose into a second JSON structure for persistence;
- a new backend Runbook projection endpoint;
- a second Markdown parser/renderer;
- Play editing/unlock/save;
- Plan Keep/Edit/Remove/Decide workflow;
- agent-authored planning interview;
- Run creation/rebase/delete changes;
- graph/source reference opening;
- P3B object sheets;
- Add to Combat;
- mode persistence across reload;
- auto-scroll/jump-to-current inside the full Runbook;
- restructuring all existing Scene/Beat presentation vocabulary.

If dogfood later shows that the full Runbook is too broad and the GM needs a curated briefing, that is evidence for a later **projection** slice, not permission to invent semantics here.

---

## §6 Implementation contract and matrices

```text
Input:
  NativeRunbookReadyDeck from existing P3A admission
  including one exact imported TipTap document derived from the admitted snapshot

Output:
  Table mode: existing focused native deck
  Runbook mode: full exact imported document rendered read-only

Invariant:
  §1 merge-ready invariant

Durable writes:
  none added

Local state:
  table | runbook mode only
  existing viewSceneId / viewBeatId remain component-local

Trust boundary:
  P3A admission proves exact Run + manifest + committed snapshot binding.
  D2 trusts only that READY result and never fetches replacement document content.

Failure behavior:
  non-READY P3A admission → existing blocked/rebase/integrity UI; neither mode is exposed
  read-only editor initialization → truthful local loading shell; no fallback to raw/latest Markdown fetch

Replay / reload:
  reload exact READY Run → Table mode by default
  mode switch → no persistence/no write
  authoritative Run update → existing P3A overlay behavior
```

### A. State / fallback matrix

| Observable path | Exact success | Dependency unavailable / invalid | Stale binding | Retry / reload |
|---|---|---|---|---|
| P3A admission | existing READY deck | existing fail-closed state | existing rebase_required | existing behavior |
| Table mode | existing deck + Runtime controls | not exposed without READY | never overlays newer prose | reload defaults Table |
| Runbook mode | exact admitted rich document | local renderer loading/error only; no alternate document fetch | never fetch/render latest workspace | switch locally; reload defaults Table |
| Mode switch | preserve local focus; zero Runtime writes | n/a | authoritative Run update follows existing overlay | repeatable/local |

### B. Identity matrix

| Situation | Required rule | Fallback permitted? |
|---|---|---|
| Run identity | existing exact canonical Run UUID | No |
| Runbook identity | existing exact `playable_artifact_id` | No title/label fallback |
| Runbook revision | existing exact revision + SHA | No latest fallback |
| Playable identity | existing Scene/Beat/Choice/Option IDs only | No new instruction IDs |
| Ordinary H1/H2 instruction section | presentation-only Runbook prose | No durable ID; no Runtime reference |
| Mode identity | local `table` / `runbook` presentation state | Not persisted |

### C. Persistence / replay matrix

| Operation | Durable representation | Behavior |
|---|---|---|
| Switch Table ↔ Runbook | none | local only; zero Runtime writes |
| Render full Runbook | none added | reconstruct from exact admitted imported document |
| Existing Runtime mutation | existing Run JSON / `run_revision` CAS | unchanged; Table-owned controls only |
| Reload | existing Run + manifest + workspace admission | default Table; Runbook can be reopened locally |

### D. Predecessor-to-consumer mapping

| Predecessor field/outcome | D2 use | Transformation |
|---|---|---|
| admitted `run` | header/runtime context | unchanged |
| admitted `snapshot.markdown` | imported once during P3A admission | existing `markdownToTiptapDoc` only |
| imported TipTap `doc` | full Runbook view | carry forward as Play-local derived projection; no persistence |
| indexed P1 structure | Table Scene/Beat/Choice/Option projection | unchanged |
| sealed manifest | membership integrity | unchanged |
| Runtime progress | Table overlay | unchanged |
| ordinary root H1/H2 | terminates current playable body slice; remains full-document prose | no identity creation |

---

## §7 Evidence required to merge

Evidence should prove the product invariant and atomic predecessor sync; do not create ceremony-only work.

### Focused UI/projection proof

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx \
  src/App.test.tsx

pnpm run typecheck
pnpm run build
```

`App.test.tsx` is regression-only unless implementation discovers a real route/composition change; it is **not** in the write lease.

### Required owning proofs

| Guarantee | Owning boundary | Required proof |
|---|---|---|
| full Runbook uses the same exact admitted import | `nativeRunbookProjection` | READY carries the imported doc produced from the admitted snapshot; no second content fetch/parser |
| global H1/H2 instructions do not leak into prior Beat/Scene body | `slicePlayableBodies` | fixture with Beat followed by ordinary `## Open questions`; body excludes it |
| ordinary instructions remain visible | `RunbookTableDeck` | full Runbook mode shows ordinary planning headings/list text plus playable headings |
| Table remains default | `RunbookTableDeck` | initial render is existing Table UI; full document not primary stage until explicit click |
| mode switch writes nothing | `RunbookTableDeck` | Table → Runbook → Table produces zero `putPlayRunProgress` calls |
| local table focus survives mode switch | `RunbookTableDeck` | focus non-default Beat, switch modes, return to same focused Beat absent authoritative Run change |
| Runbook view is read-only | `RunbookTableDeck` / `MarkdownEditorCore` use | editor is non-editable; no toolbar/save/update persistence callback |
| P3A exact admission remains gate | projection regression | stale revision/SHA still returns non-READY; no Runbook view bypass |
| D1 predecessor truth is atomically synchronized | docs diff | #621 merge/evidence/review facts agree in predecessor handoff, roadmap, and P3B sequencing state |
| no new durable/public contract | cumulative diff | no backend/API/schema/marker-grammar persistence changes |

### Repository hygiene

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md

git diff --check
git diff --name-only a0e03bed359dce094a18a5a5824d07487fe4b490...HEAD
```

Every changed path must be in §4.

### Dogfood posture

Do **not** require a whole live session before merging D2; D2 exists to make that session dogfood possible.

A lightweight local smoke is useful when available:

```text
Start one exact Run from a Runbook containing:
  Session intent
  Pressures
  at least one marked Scene/Beat
  Open questions after playable material

Confirm:
  /play starts in Table
  Runbook mode shows all of the authored document
  Open questions do not appear inside the preceding Beat body
  switching back returns to the same focused table moment
```

The real-session dogfood was the named successor after merge. It ran as D3 (C2 Session 27); the verdict and re-anchor are recorded in `Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md` and `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.

---

## §8 Required review handback

Keep the handback operational rather than ceremonial:

1. exact PR URL, base SHA, reviewed head SHA;
2. actual changed paths and confirmation they remain inside §4;
3. focused test/typecheck/build results;
4. explicit result for the H1/H2 body-boundary proof;
5. explicit result for Table → Runbook → Table zero-write/focus proof;
6. atomic predecessor-sync result for #621 across all three mutable authorities;
7. roadmap design disposition / hoist observation;
8. stop conditions or scope amendments, if any.

Formal review cycles follow `AGENTS.md`:

```text
one formal reviewer judgment against one distinct head SHA = one review cycle
```

---

## §9 Acceptance rubric

Reviewer accepts only when every item is true:

- [ ] `/play` READY defaults to the existing focused Table deck.
- [ ] GM can explicitly open a full rich Runbook view and return to Table.
- [ ] Full Runbook is rendered from the same exact admitted imported document; no second fetch/latest/default substitution exists.
- [ ] Runbook mode is read-only and introduces no Save/edit/Runtime action.
- [ ] Mode switches alone generate zero Runtime writes.
- [ ] Local focused Scene/Beat survives Table → Runbook → Table when no authoritative Run change occurs.
- [ ] Ordinary unmarked root H1/H2 sections terminate preceding playable body ownership.
- [ ] Those ordinary sections remain ordinary Runbook prose with no stable Playable ID or manifest membership.
- [ ] Existing Scene/Beat/Choice/Option identity, manifest admission, and Runtime CAS remain unchanged.
- [ ] No heading-name ontology or `briefing` persistence/schema was created.
- [ ] No backend/API/Plan/Build/graph-reference/Combat scope entered.
- [ ] #621 / D1 is atomically recorded as merged/historical across predecessor handoff, living roadmap, and P3B sequencing state.
- [ ] P3B remains non-dispatchable until real-session dogfood and re-anchor.

---

## Stop conditions

Stop and report rather than expanding if implementation discovers:

- the full admitted Runbook cannot be rendered with existing `MarkdownEditorCore` without modifying shared TipTap infrastructure;
- ordinary Runbook instructions require durable IDs or semantic block persistence to be useful;
- heading-name recognition is required to distinguish “briefing” content;
- fixing body ownership requires changing P1 marker grammar or server manifest derivation;
- full Runbook mode needs a new workspace/API fetch to render accurately;
- Play editing/save is required;
- reference opening is required to make D2 usable;
- a path outside §4 must change;
- another active lane begins modifying the same runbook projection/deck paths;
- `main` moves and the P3A/D1 predecessor seams materially change.

Use the standard report:

```text
Stop condition:
Why D2 cannot absorb it:
Invariant clause affected:
New public/durable contract discovered:
Owning boundary affected:
Proposed successor:
Authority/roadmap update needed:
```

---

## Named successor — real-session dogfood, then re-anchor (occurred)

After D2 merged, the D3 C2 Session 27 real-session dogfood ran. Verdict: **BLOCKED / PLAY NOT READY** — exact Run admission accepted, native Table rejected as the table instrument (`Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`). The D4 current-Beat table-stage successor (PR #623) was closed unmerged. Do not automatically dispatch P3B; the post-C2S27 sequence (Lane A Run continuity, Lane B durable Combat, then the Beat/Scene/Decision + Plan→Playable design task) is owned by `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.

Historical dispatch instruction, preserved for the record:

Use the product for a real session with a Runbook shaped like the current Session 27 planning scaffold:

```text
prepare / edit Runbook
→ commit exact revision
→ Start Run
→ Table mode for current Scene/Beat
→ Runbook mode for intent, pressures, forks, open questions, references
→ Runtime notes / Beat resolution where already supported
→ return to Table repeatedly without leaving Play
```

Capture product evidence, not implementation ceremony:

- what information was still hard to reach;
- what parts of the Runbook were repeatedly consulted;
- where the GM left Play;
- whether full-document mode was too broad or exactly sufficient;
- whether a curated briefing projection is justified;
- which references wanted to be clickable;
- what had to be written somewhere else;
- what the GM avoided because it felt unsafe or cumbersome.

Then re-anchor the roadmap and choose the next independently useful capability from dogfood evidence. P3B exact graph-reference opening remains designed but **NON-DISPATCHABLE until that re-anchor names it next**.
