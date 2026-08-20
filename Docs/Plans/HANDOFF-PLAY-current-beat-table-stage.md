---
pr_body_template: |
  ## Handoff pointer
  - Workstream: Playable Architecture Graduation / dogfood UX repair D4
  - Flow: PLAY
  - Direction: DESIGN → CODE → REVIEW
  - Handoff: Docs/Plans/HANDOFF-PLAY-current-beat-table-stage.md
  - Branch / PR: agent/play-current-beat-table-stage / `PLAY: make current Beat the table stage`

  ## Verification pointer
  - Design/base anchor: `62f7f9e856327247b8677b4c951801e4c58a826c`
  - Predecessor: merged PR #622 / exact admitted Runbook view
  - Dogfood decision: C2 Session 27 native Play READY wiring accepted; shipped three-column Table UX rejected as the table instrument
  - Base/head: `62f7f9e856327247b8677b4c951801e4c58a826c` / <implementation head>
  - Changed paths: HANDOFF §4 only
  - Verification: HANDOFF §7 + visual table-stage review

  The checked-in handoff, cumulative diff, owning-boundary tests, and visual
  inspection against the current-moment contract are the review contract.
  The PR description is transport metadata only.
---

# HANDOFF — make the current Beat the native Play table stage

**Created:** 2026-08-19  
**Status:** ACTIVE — dispatch exactly one native Play projection/interaction capability while `main` remains anchored at `62f7f9e856327247b8677b4c951801e4c58a826c`; re-anchor and amend before dispatch if `main` moves.  
**Canonical handoff path:** `Docs/Plans/HANDOFF-PLAY-current-beat-table-stage.md`  
**Workstream:** `Playable Architecture Graduation / dogfood UX repair D4`  
**Flow / owner:** `PLAY`  
**Direction:** DESIGN → CODE → REVIEW  
**Implementation base:** `62f7f9e856327247b8677b4c951801e4c58a826c`  
**Suggested branch:** `agent/play-current-beat-table-stage`  
**PR title:** `PLAY: make current Beat the table stage`

> Repository operating law: `AGENTS.md`.  
> Play product design authority: `Docs/Design/DESIGN-play-surface-projection.md`.  
> Current-moment Table redesign: `Docs/Design/DESIGN-play-native-current-moment-deck.md`.  
> Playable/Runtime authority: `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`.  
> Prototype evidence only: `Docs/Reports/REPORT-pr578-play-dogfood-mining.md`.  
> D2 predecessor: `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md`.  
> P3A admission/runtime projection predecessor: `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`.  
> Deferred reference successor: `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`.  
> Living sequence: `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`.

---

## §0 Re-anchor, completed predecessor, dogfood decision, and state-authority sync

### Repository truth at dispatch design time

```text
main:
  62f7f9e856327247b8677b4c951801e4c58a826c

D2 / PR #622:
  title:                   PLAY: expose exact Runbook instructions
  merged:                  62f7f9e856327247b8677b4c951801e4c58a826c
  implementation/evidence b923117bd7767884053bbe32f25043c7cfe8dcab
  final reviewed head:     c549611a889bc132d385e536ccc675ca695b356c
  formal review cycles:    1

native /play now truthfully has:
  explicit durable Run chooser
  explicit Start Run from one committed Runbook
  exact Run + sealed manifest + committed snapshot admission
  stable Scene / Beat / Choice / Option projection
  P2 Runtime progress under run_revision CAS
  Table / full exact Runbook projection switch
  ordinary unmarked root H1/H2 outside prior Playable body slices
```

### C2 Session 27 dogfood decision

After D2, the steward dogfooded shipped native `/play` against the real Campaign 2 Session 27 Mireward Runbook.

Dogfood identity is evidence, **not design authority**:

```text
Run:
  07225b19-7df3-4335-ae14-22e4b133eac4

Runbook:
  C2 Session 27 — Mireward Climax
  document 8235ce04-5023-485c-92f0-2d8d81d64f50
  revision 3
```

Accepted result:

```text
committed Runbook
  → Start Run
  → exact Run + sealed manifest
  → P1 admitted TipTap document
  → Table + Runbook projections
  → Runtime CAS
```

That wiring is good enough to keep.

Rejected result:

```text
Scene list | Beat list | focused body dump
```

The GM refused to use the shipped native Table navigation as the table instrument. The layout answers “which identity is selected?” rather than “what is happening right now?” Contrast was patched as an emergency exception, but the problem is hierarchy, not one color token.

The already-accepted Play product thesis remains authority:

> **Play is the surface for the next few minutes at the table.**

and the target hierarchy remains:

```text
Run title
Scene deck / position
Beat strip
Focused Beat detail
```

This PR implements that hierarchy over the already-shipped native authorities. It does **not** invent a new Play philosophy.

### Source-gap note

The dogfood brief refers to:

`Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md`

That path is **not present on `main` at `62f7f9e...`**. Do not fabricate or create that report inside this implementation slice. If the report already exists in the executing worktree from D3 dogfood, leave it untouched. The exact dogfood facts above and the locked product authorities are sufficient dispatch input. If that report or any competing Play state authority lands before dispatch, re-anchor and reconcile deliberately.

### Backward-looking atomic state-authority sync carried by this PR

This implementation consumes merged D2 / #622 and the completed D3 dogfood decision. Per `AGENTS.md`, synchronize the mutable authorities that still describe D2/dogfood as in flight.

Update atomically in this PR:

1. `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md`
   - mark D2 / #622 **MERGED / HISTORICAL**;
   - record merge SHA `62f7f9e856327247b8677b4c951801e4c58a826c`;
   - record implementation/evidence `b923117bd7767884053bbe32f25043c7cfe8dcab`;
   - record final reviewed head `c549611a889bc132d385e536ccc675ca695b356c`;
   - record **1 formal review cycle**;
   - record that real C2S27 dogfood accepted exact lifecycle wiring but rejected the native three-column Table presentation;
   - name this current-Beat table-stage slice as the consuming implementation successor.

2. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
   - replace D2 `this PR` truth with merged PR #622 truth;
   - mark D2 complete;
   - advance integration tip to `62f7f9e...`;
   - record the C2S27 dogfood conclusion: lifecycle/admission/runtime wiring accepted, default Table UX rejected;
   - select **current Beat table stage** as the current next implementation slice;
   - add the current PR review/evidence row only when implementation evidence is truthfully known;
   - do **not** pre-mark this slice complete;
   - do **not** automatically advance P3B/P4 after this PR.

3. `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`
   - keep P3B **DESIGNED / NON-DISPATCHABLE**;
   - update stale sequencing language: D2 and first real native dogfood are complete, but dogfood selected this current-moment table repair before graph-object opening;
   - require a post-current-moment-deck re-anchor before P3B can become dispatch authority;
   - do not rewrite P3B’s exact-reference design itself.

Do **not** edit stable architecture or product design authorities merely to record #622 or the dogfood event. Their claims already support this change. Stable authorities do not churn for ceremony.

---

## §1 Mission and merge-ready invariant

### Mission

A GM opening one exact READY native Play Run lands on a **current-moment table deck**: the Runbook title and Scene position orient them, the current Scene’s Beats are immediately scannable, and one wide rich Beat stage answers “what is happening now?” without exposing equal-weight Scene/Beat browser columns.

### Merge-ready invariant

> **For one P3A-admitted `NativeRunbookReadyDeck`, native Table mode renders Run title → Scene orientation → Beat strip → one wide focused Beat stage using only P1-derived Scene/Beat/Choice/Option identity, the exact already-imported TipTap document, and the existing P2 Run progress. Local Scene/Beat focus is presentation state and produces no Runtime write. Explicit `Make current`, resolve/unresolve, Choice selection, and note mutations continue to replace the full existing progress snapshot under the current `run_revision` CAS and preserve all unrelated progress fields. Rich Scene/Beat bodies are derived directly from the admitted `importedDoc` nodes inside existing P1 ownership boundaries; this PR performs no second Markdown fetch, no second Markdown parse, no heading-name classification, and no durable grammar/schema/API/backend change. Table remains default; D2 Runbook mode remains the full exact read-only document and switching projections alone preserves local focus and writes nothing.**

### Product falsification

The PR fails even if tests are green when the GM’s first scan remains:

> Which Scene/Beat list button is selected?

The intended first scan is:

> What is happening in this Beat right now?

### Pre-dispatch critique

| Question | Required answer |
|---|---|
| Does one independently useful capability govern the slice? | **Yes.** Replace identity-browser Table presentation with current-moment projection while preserving the exact same authorities and mutations. |
| Does the slice require P3B/P4/Plan→Runbook? | **No.** Object opening, Combat, Roll, Items, and authoring remain later capabilities. |
| Does the slice require a new durable Beat semantic? | **No.** The existing Beat boundary + rich authored body is sufficient for the first useful deck. |
| Does `spine / optional / interrupt` exist as an admitted durable value today? | **No.** Reserve no fake badge; do not infer it. |
| Most dangerous interaction regression | Local preview click silently writes `current_scene_id/current_beat_id`, turning browsing into Runtime mutation. |
| Most dangerous authority regression | Rich stage re-parses/fetches current workspace Markdown and accidentally shows a different revision than the admitted Run binding. |
| Most dangerous CAS regression | `Make current` or resolve rewrites one field but drops prior selections/notes/resolved/current values. |
| Most dangerous UX regression | CSS changes make the new DOM horizontal but still visually present navigation chrome as the product center. |
| Stop condition | If implementation claims usability requires a new durable Markdown/TipTap kind, heading ontology, Beat-kind field, consequence model, typed-reference opener, new Runtime field, or backend/API change: **STOP and return to steward.** |

---

## §2 Authority, code seam, and prototype mining boundary

### Read in this order before writing

1. `AGENTS.md`
2. `Docs/Design/DESIGN-play-surface-projection.md`
3. `Docs/Design/DESIGN-play-native-current-moment-deck.md`
4. `Docs/Reports/REPORT-pr578-play-dogfood-mining.md`
5. `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`
6. `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`
7. `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md`
8. `Docs/Plans/HANDOFF-PLAY-native-runbook-table-deck.md`
9. `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`
10. `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts`
11. `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts`
12. `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx`
13. `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx`
14. `apps/live-control-ui/src/playSurface/playSurface.css`
15. `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx` — read/reuse only unless a real incompatibility triggers STOP
16. `apps/live-control-ui/src/styles.css` — read dark-shell vocabulary; expected no modification

Optional evidence-only read:

- PR #578 mined head `88e4d65e7ed69afe262008749194e2b948ce4c43`
- `apps/live-control-ui/src/playSurface/beats/BeatsPanel.tsx`

If reading #578, apply the mining rule exactly:

> **Preserve the interaction that worked. Remove the adventure-specific mechanism that made it work.**

Do not cherry-pick or copy the prototype wholesale.

### Existing durable authority — unchanged

```text
P1
  Scene / Beat / Choice / Option stable marker identity
  structure index

P2
  Run exact Playable binding
  sealed manifest
  run_revision CAS
  progress:
    current_scene_id
    current_beat_id
    resolved_beat_ids
    selections
    notes_by_element_id

P3A
  exact Run + manifest + committed snapshot admission
  one imported TipTap document
  Play READY/fail-closed behavior

D1
  explicit Start Run

D2
  Table / full exact Runbook modes
  ordinary H1/H2 body-boundary correction
```

This PR consumes all of those. It replaces none of them.

### What #578 contributes to this slice

Keep the **interaction shape** only:

- horizontal Scene deck / position;
- horizontal Beat strip;
- wide focused Beat stage;
- current/resolved state visible without suffix-heavy admin labels;
- table-first hierarchy;
- return to exact table position.

Do **not** keep:

- `ofConksHempholmBeats.ts`;
- `PlayRunStateDocument` adventure enums;
- `buildPlayLocalGraphReferenceResolution()`;
- `ofConksPlayObjectBridge.ts`;
- `ofConksThreatPlayBridge.ts`;
- prep HTML / `MirewardPrep` host;
- campaign-specific branch dictionaries;
- hardcoded `spine / optional / interrupt` data;
- heading-text mutation locators;
- prototype CSS wholesale.

### No new Playable semantic in this slice

The product target vocabulary remains:

```text
At the table
Read aloud
GM note
Rules now
Warnings
Consequences
Open now
Tools
```

But the first implementation does **not** manufacture these as fields by parsing display headings.

Required first-slice interpretation:

```text
focused Beat body
  = primary at-table authored material

existing semantic callout nodes
  = retain their existing visual semantics in authored order

unrecognized prose/subheadings
  = remain authored document content
```

Do not reorder authored blocks to mimic #578’s object shape.

Beat kind `spine / optional / interrupt`, Consequences, Open now, and contextual Tools remain absent unless an already-shipped authority truthfully supplies them. Empty future regions are omitted.

---

## §3 Required product shape and interaction semantics

### 3.1 Overall READY Table hierarchy

Replace:

```text
[ Scene vertical list ] [ Beat vertical list ] [ authored dump ]
```

with:

```text
C2 Session 27 — Mireward Climax                         Table | Runbook
[quiet status / Run details]

‹ Previous     Scene 1 / 1 · Mireward Siege Climax     Next ›
[compact direct Scene picker if useful]
[Scene context ▸]

Beats  [Survive breach] [Town siege] [Thrin] [Wall] [Aftermath]

┌───────────────────────────────────────────────────────────────┐
│ CURRENT / PREVIEW                                            │
│ Survive the current breach                  Resolve / current │
│                                                               │
│ rich exact authored Beat body                                │
│ callouts / lists / paragraphs / references retain rendering  │
│                                                               │
│ choices if authored                                           │
│ notes ▸                                                       │
└───────────────────────────────────────────────────────────────┘
```

No peer Scene/Beat side columns remain in default Table mode.

### 3.2 Run bar

Human Runbook title is the dominant Run identity.

Keep:

- `Table` / `Runbook` projection control;
- mutation conflict/unknown safety banners;
- preview/current truth where applicable.

Raw support identity becomes quiet detail, not the page headline:

- Run UUID;
- campaign ID;
- Playable revision;
- Run revision;
- content SHA if currently shown or needed for support.

Recommended product shape: a compact `Run details` disclosure. Exact HTML is implementation-owned; the requirement is visual subordination without deleting support truth.

### 3.3 Scene deck — orientation, not state mutation

Scene navigation is session orientation.

Required behaviors:

- show selected/focused Scene title;
- show authored position `Scene N / total`;
- Previous / Next focus adjacent authored Scenes locally;
- direct Scene selection remains possible without a vertical full-height button rail;
- focusing a Scene does **not** call `putPlayRunProgress`;
- Runtime-current Scene is visibly distinguishable from a locally previewed Scene;
- focusing a new Scene selects an appropriate local Beat for display, normally that Scene’s first Beat, without persisting it;
- if returning to the Runtime-current Scene, prefer its Runtime-current Beat when it belongs to that Scene.

Do not silently persist Scene focus merely because the operator clicked Previous/Next/direct picker.

### 3.4 Scene context

The existing authored Scene body remains useful but must not compete with the Beat stage.

Required:

- render the Scene body as a compact read-only disclosure/secondary region;
- derive it from the exact admitted rich body fragment, not `bodyText` if rich structure is available;
- no semantic parsing into `intent`, `clock`, `pressure`, etc.;
- omit or collapse naturally when empty;
- if a focused Scene has no Beats, provide the existing explicit ability to make that Scene Runtime-current with `current_beat_id: null`.

### 3.5 Beat strip

The Beat strip is the near-term navigation control inside the selected Scene.

Each Beat must truthfully encode:

- focused;
- Runtime current;
- resolved/unresolved.

Required interaction semantics:

- clicking the Beat title changes local focus only;
- local focus alone never mutates Runtime;
- resolved Beats remain reopenable/focusable;
- resolution is one explicit interaction and continues to use existing P2 CAS;
- do not encode state primarily through appended text such as `· current · resolved`;
- accessible labels/ARIA still expose state to assistive technology;
- strip may horizontally scroll/wrap responsively; it must not become another vertical equal-weight browser on ordinary desktop widths.

Do not show `spine / optional / interrupt` because current admitted data does not contain that durable property.

### 3.6 Focused Beat stage

This is the product center.

Stage header requires:

- Beat title;
- `Current` or truthful `Preview` state;
- resolved state/control;
- one compact **Make current** action only when the focused Beat is not the Runtime current Beat.

`Make current` semantics:

```text
focused Beat B in Scene S
  → one replaceProgress call
  → current_scene_id = S
  → current_beat_id = B
  → preserve resolved_beat_ids
  → preserve selections
  → preserve notes_by_element_id
```

Do not perform separate Scene then Beat writes.

If the Run has no current Scene/Beat, the existing P3A preview contract remains truthful: show first authored Scene/Beat as preview, with no mutation until the operator explicitly makes it current.

### 3.7 Rich authored Beat body

Current code flattens Playable body nodes into `bodyText`.

This slice must additionally carry a rich read-only fragment for Scene/Beat presentation from the **already admitted `importedDoc`**.

Required projection shape, exact type name implementation-owned:

```text
NativeRunbookAuthoredElement
  id
  kind
  title
  bodyText        # may remain as derived convenience/backward compatibility
  rich body doc   # TipTap JSON fragment wrapped as doc
```

Rules:

- construct the rich body fragment while `slicePlayableBodies(...)` is already traversing `importedDoc`;
- preserve node order and attrs exactly;
- wrapping existing body nodes in `{ type: "doc", content: [...] }` is allowed;
- no serialize→Markdown→parse roundtrip;
- no `markdownToTiptapDoc` second invocation for individual elements;
- no workspace/API refetch;
- no mutation of `deck.importedDoc`;
- ordinary unmarked root H1/H2 still terminate the Playable body exactly as D2 established;
- unmarked H3/H4+ inside a Beat remain inside its rich body;
- existing semantic callout nodes such as GM-NOTE / READ-ALOUD / RULES / WARNING retain their existing native rendering in authored order.

Use existing `MarkdownEditorCore` read-only rendering if it accepts the derived document without a new storage seam. If it does not, stop before modifying TipTap core architecture merely to force this PR through.

### 3.8 Choices and Options

Existing generic P1 Choice/Option + P2 selection semantics remain.

Required:

- keep authored choices available for the selected Scene;
- present them below/subordinate to the current Beat stage rather than as peer navigation;
- existing explicit radio/selection mutation remains CAS-backed;
- preserve all unrelated Runtime fields;
- do not reinterpret Session 27 strategic directions as Choice/Option merely because the UI has a decision region.

### 3.9 Runtime notes

Existing `notes_by_element_id` authority remains.

Required UX:

- keep note editing for the focused Beat/Scene;
- move it to a compact disclosure or subordinate region instead of a permanent wide textarea competing with the Beat body;
- Save note remains explicit;
- preserve existing element-key and CAS semantics.

### 3.10 Table / Runbook projection switch

D2 remains intact.

Required:

- Table default on fresh READY/run identity change;
- Runbook is secondary full exact document view;
- Table → Runbook → Table produces zero Runtime writes;
- local focused Scene/Beat returns after the mode switch if no authoritative Run update changed the deck;
- Runbook view must visually belong to the shared dark AppChrome shell rather than a white/cream document app pasted into it.

### 3.11 Shared dark-shell visual contract

The application root is already `color-scheme: dark` with AppChrome values such as:

```text
#12141a root
#171b24 / #161922 surfaces
#2a3142 borders
#e8eaef primary text
#9aa3b5 secondary text
#7aa2f7 active accent
```

These are implementation context, not a frozen token API.

Required visual outcome:

- Play Canvas is continuous with AppChrome’s dark shell;
- no large `#fff`, `#fbf7ef`, `#f3ead8`, or similar cream panels as the default Play deck;
- one strong current/focus accent family;
- resolved state is quieter but readable, not disabled;
- preview is distinct from current but not alarm-colored;
- safety/conflict banners remain high contrast;
- rich `MarkdownEditorCore` read-only areas inherit/receive a Play dark treatment without changing global editor behavior for Plan/Build;
- responsive mobile/narrow widths may stack controls, but the desktop default remains current-moment stage rather than three equal columns.

Do not modify `src/styles.css` just to recolor Play. Keep Play-specific treatment Play-owned in `playSurface.css` unless a real shared-host defect is discovered; that would require a scope stop/rebrief.

---

## §4 Files in scope — exclusive write lease

The implementation lane owns exactly these expected paths.

| Field | Required content |
|---|---|
| Branch / isolated checkout | `agent/play-current-beat-table-stage` in this worktree |
| Runtime/state ownership | No new durable runtime representation. Existing `putPlayRunProgress` CAS only for Make current / resolve / Choice / note. Tests use in-memory fixtures; do not point automated tests at a real operator Run under `out/runtime/play/**`. |

| Action | Path | Purpose |
|---|---|---|
| Create | `Docs/Plans/HANDOFF-PLAY-current-beat-table-stage.md` | checked-in D4 implementation authority |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md` | atomic backward-looking D2/#622 merged/historical sync + name this current-Beat successor |
| Modify | `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md` | keep P3B non-dispatchable behind this deck then re-anchor |
| Modify | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` | D2 complete + D3 dogfood decision + select D4 current; do not pre-mark D4 complete |
| Modify | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts` | carry exact admitted TipTap body fragments on authored Scene/Beat/Choice/Option slices |
| Modify | `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts` | prove rich fragments, H3-inside-Beat, ordinary H2 boundary, no second parse |
| Modify | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx` | replace three-column identity browser with current-moment Table hierarchy |
| Modify | `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx` | owning UI proofs: local focus, Make current CAS, preview, mode switch, rich body |
| Modify | `apps/live-control-ui/src/playSurface/playSurface.css` | dark-shell current-moment deck; no cream three-column default |

### Create

- `Docs/Plans/HANDOFF-PLAY-current-beat-table-stage.md`

### Modify — backward-looking state-authority sync

- `Docs/Plans/HANDOFF-PLAY-native-runbook-instructions.md`
- `Docs/Plans/HANDOFF-PLAY-native-graph-object-sheet.md`
- `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`

### Modify — implementation

- `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.ts`
- `apps/live-control-ui/src/playSurface/runbook/nativeRunbookProjection.test.ts`
- `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.tsx`
- `apps/live-control-ui/src/playSurface/runbook/RunbookTableDeck.test.tsx`
- `apps/live-control-ui/src/playSurface/playSurface.css`

### Read-only expected dependencies

- `apps/live-control-ui/src/tiptap/MarkdownEditorCore.tsx`
- `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.ts`
- `apps/live-control-ui/src/tiptap/markdown/markdownToTiptap.test.ts`
- `apps/live-control-ui/src/styles.css`
- `apps/live-control-ui/src/App.test.tsx`

### Bounded discovery

At most **two** additional paths under:

`apps/live-control-ui/src/playSurface/runbook/`

may be **created** only if extracting one purely presentational current-moment component materially improves `RunbookTableDeck.tsx` readability. Allowed shape:

```text
CurrentMomentTable.tsx
CurrentMomentTable.test.tsx
```

or one equivalently focused component/test pair.

Constraints:

- presentation only;
- no API calls in the extracted component;
- no durable state authority;
- no second parser;
- no new cross-surface abstraction;
- if extraction would move mutation/CAS ownership or require more than two paths, keep implementation in `RunbookTableDeck.tsx` or stop/rebrief.

### Explicitly outside lease

No changes without steward rebrief to:

- `apps/live-control-ui/src/api/**`
- `apps/live_control_server/**`
- `src/**`
- `apps/live-control-ui/src/tiptap/**`
- `apps/live-control-ui/src/graphReference/**`
- `apps/live-control-ui/src/statblocks/**`
- `apps/live-control-ui/src/planSurface/**`
- `apps/live-control-ui/src/chrome/**`
- `apps/live-control-ui/src/styles.css`
- Playable marker grammar/extensions
- Run/manifest schema
- Combat state
- PR #578 files/branches

A need for any of these is a stop/split signal, not silent scope expansion.

### Runtime/state ownership

This lane changes no durable runtime representation.

It **does call the existing** `putPlayRunProgress` mutation through `RunbookTableDeck` for the existing explicit actions:

- make current;
- resolve/unresolve;
- Choice selection;
- note save.

Parallel lanes must not concurrently redesign these Play Runtime mutation interactions in the same component. Source worktree isolation does not isolate shared live `out/runtime/play/**` state; do not point automated tests at a real operator Run.

---

## §5 Implementation decomposition and nano-commit story

The implementation should remain reviewable as a small sequence. Exact commit count is not a grading target; preserve conceptual boundaries.

### Nano 1 — check in handoff + synchronize completed D2/dogfood truth

Expected:

- create this handoff;
- mark D2 #622 merged/historical;
- update living roadmap to `62f7f9e...`, D2 complete, dogfood UX finding, D4 current;
- keep P3B non-dispatchable behind D4/re-anchor.

No product code in this commit if practical.

### Nano 2 — preserve rich Playable body fragments from the admitted document

In `nativeRunbookProjection.ts`:

- extend authored slices/elements with the rich TipTap body fragment;
- derive fragment in the same admitted `importedDoc` traversal used for body ownership;
- preserve `bodyText` where useful for current compatibility/tests;
- no reparse/refetch;
- no change to manifest membership, admission, structure ordering, or P2 overlay.

Owning projection tests first.

### Nano 3 — replace Table identity browser with current-moment hierarchy

In `RunbookTableDeck.tsx` (+ optional one presentation component):

- quiet Run bar;
- Scene deck/position and direct selection;
- compact Scene context;
- Beat strip;
- wide focused rich Beat stage;
- local focus vs Runtime-current truth;
- `Make current` one-CAS behavior;
- integrated resolve state;
- subordinate choices/notes;
- preserve D2 mode switch.

### Nano 4 — make Play visually native to the dark AppChrome shell

In `playSurface.css` only:

- remove three-column Table layout styling;
- remove white/cream default deck surfaces;
- style Scene/Beat orientation and focus/current/resolved states;
- style read-only rich body/Runbook editor inside Play dark shell;
- preserve responsive behavior and safety contrast.

### Nano 5 — review evidence / roadmap row

After implementation behavior is known:

- add the current D4 roadmap review/evidence row with the actual implementation/evidence SHA;
- do not mark D4 merged/complete;
- do not name P3B as current successor before post-merge/re-dogfood truth exists.

---

## §6 Required adversarial and product proofs

### A. READY opens on current moment

Given:

```text
current_scene_id = scene:gate
current_beat_id = beat:inside
```

Table opens with:

- Runbook title visible;
- Scene position/title visible;
- Beat strip visible;
- `Inside` as the wide stage;
- current truth visually/semantically present;
- no equal-weight Scenes/Beats columns.

Zero writes occur during initial render.

### B. Empty Runtime remains truthful preview

Given no current Scene/Beat:

- first authored Scene/Beat may be focused as preview;
- preview state is visible;
- no Runtime write occurs;
- `Make current` is available;
- `Make current` writes the exact Scene+Beat pair once.

### C. Local Beat focus does not mutate Runtime

```text
runtime current = beat:approach
click beat:inside in strip
```

Required:

- stage changes to `Inside`;
- `Inside` is Preview/focused, not Runtime-current;
- `putPlayRunProgress` call count remains 0;
- current indicator remains on `Approach` in the strip;
- clicking `Make current` then emits one CAS write setting `scene:gate + beat:inside` and preserving every unrelated progress field.

### D. Local Scene focus does not mutate Runtime

With at least two Scenes:

```text
runtime current = scene:A / beat:A1
focus Next Scene B
```

Required:

- Scene B + appropriate local Beat are displayed;
- Runtime current remains A/A1;
- no write until explicit `Make current`;
- direct Scene picker obeys the same rule;
- returning to Scene A restores A1 when it remains the Runtime current Beat.

### E. Scene with no Beats can still become current

Required:

- Scene orientation/context remains usable;
- explicit `Make current Scene` performs one CAS write;
- `current_scene_id = focused Scene`;
- `current_beat_id = null`;
- all other progress preserved.

### F. Resolve is independent from current focus

Required:

- resolving focused Beat changes only membership in `resolved_beat_ids`;
- current Scene/Beat, selections, notes remain byte-equivalent in request body except canonical resolved ordering;
- resolved Beat remains focusable/reopenable;
- unresolve reverses only that membership.

### G. Rich Beat body comes from one admitted import

Use a test Runbook Beat containing at minimum:

```markdown
ordinary paragraph

- list item

> [!GM-NOTE]
> Keep this hidden from players.

> [!READ-ALOUD]
> The wall buckles inward.

#### Local subheading
More Beat prose.
```

Required projection proof:

- rich Beat fragment contains the imported structured nodes/attrs in order;
- it is not a new `markdownToTiptapDoc` parse of extracted text;
- H3/H4 substructure inside Beat remains inside the fragment;
- ordinary root H2 following the Beat remains outside the fragment per D2;
- `bodyText` may flatten for convenience but is not the stage renderer.

Required component proof:

- rich stage renders meaningful paragraph/list/callout/subheading content through existing read-only TipTap rendering;
- the stage does not display marker comments as prose.

### H. Table → Runbook → Table preserves local focus

```text
runtime current = Approach
local focus = Inside
open Runbook
return Table
```

Required:

- zero Runtime writes from mode changes;
- local focus returns to Inside;
- Runtime current remains Approach;
- full Runbook still contains ordinary instructions outside Playable bodies.

### I. Existing Choice/Option mutation does not regress

Required:

- selecting one option updates only that `choiceId` entry;
- current/resolved/notes preserved;
- CAS conflict/unknown behavior remains existing fail-closed behavior.

### J. Existing note mutation does not regress

Required:

- note target is focused Beat when present, otherwise focused Scene;
- note UI is subordinate/collapsible but still explicit;
- Save changes only the named `notes_by_element_id` entry;
- all other progress preserved.

### K. CAS conflict / unknown outcome remains fail-closed

Existing behavior remains:

- one failed write;
- exact Run GET reconciliation;
- no silent retry or merge;
- safety banner visible;
- authoritative Run overlay accepted only under existing P3A binding rules.

The redesign must not turn these safety banners into hidden/toast-only failures.

### L. Dark-shell visual falsification

Reviewer visual inspection at ordinary desktop width must confirm:

- no three peer columns;
- current/focused Beat stage dominates page area;
- Scene navigation reads as orientation;
- Beat navigation reads as a compact strip;
- raw IDs are subordinate;
- no large white/cream Runbook or stage surface against dark AppChrome;
- current/resolved/preview can be distinguished before reading suffix prose;
- Session 27’s first visible question is “what is happening now?”

DOM/unit tests cannot by themselves satisfy this visual proof.

---

## §7 Verification contract

### 7.1 Focused UI/projection tests

From `apps/live-control-ui`:

```bash
pnpm exec vitest run \
  src/playSurface/runbook/nativeRunbookProjection.test.ts \
  src/playSurface/runbook/RunbookTableDeck.test.tsx \
  src/App.test.tsx \
  src/tiptap/markdown/markdownToTiptap.test.ts
```

If §4 bounded discovery creates one focused presentation test, include it in the command.

Why these boundaries:

- `nativeRunbookProjection.test.ts` owns rich fragment derivation + D2 body ownership;
- `RunbookTableDeck.test.tsx` owns local focus/current/resolved/CAS/mode interaction;
- `App.test.tsx` protects real native `/play` READY composition/Start Run integration from Table DOM redesign fallout;
- `markdownToTiptap.test.ts` protects the reused rich semantic import/callout behavior even though this PR must not modify the parser.

### 7.2 Compile/build

```bash
pnpm run typecheck
pnpm run build
```

### 7.3 Existing Play Runtime backend regression

No backend path may change, but the frontend continues to depend on the exact P2 progress contract. Run focused owning regression from repo root:

```bash
uv run pytest -q \
  tests/test_live_play_run_progress.py \
  tests/test_play_run_progress.py \
  tests/test_live_play_runs.py
```

If those exact filenames have moved on current `main`, stop and report the authority change rather than substituting unrelated tests silently.

### 7.4 Repository hygiene

```bash
uv run python scripts/steward_preflight.py \
  --handoff Docs/Plans/HANDOFF-PLAY-current-beat-table-stage.md

git diff --check

git diff --name-only 62f7f9e856327247b8677b4c951801e4c58a826c...HEAD
```

Changed paths must match §4 plus at most the explicitly bounded two-path presentation extraction.

### 7.5 Visual dogfood proof

This is a UX repair; browser inspection is substantive evidence, not ceremony.

Minimum visual walkthrough on the implementation branch:

1. open one READY Run with at least one Scene and multiple Beats;
2. verify the Table default is Run title → Scene deck → Beat strip → wide stage;
3. focus another Beat and verify no Runtime mutation occurs;
4. make it current and verify current state moves;
5. resolve/unresolve and verify strip state;
6. open/close Scene context;
7. open Notes without it dominating the page;
8. switch Table → Runbook → Table and verify focus returns;
9. inspect dark-shell continuity at ordinary desktop width;
10. hard reload and verify authoritative current/resolved state survives.

Preferred operator evidence is the existing C2S27 Run if available safely in the operator environment. Do **not** make automated tests mutate that real Run. If that runtime state is unavailable in the isolated lane, use another deliberate local READY Run for browser inspection and say so.

Review does not require screenshot files to be committed. A reviewer must still inspect the rendered result; DOM assertions are insufficient to prove hierarchy/contrast.

---

## §8 Review handback contract

Keep handback concise. The reviewer cares about product/process truth, not ceremony.

Provide:

1. PR URL, exact base, exact head, implementation/evidence head if distinct.
2. Changed-path list and whether §4 bounded discovery was used.
3. One-sentence disposition of the merge-ready invariant.
4. Atomic predecessor sync disposition:
   - D2 #622 merged/historical recorded correctly;
   - roadmap integration tip/current slice correct;
   - P3B still non-dispatchable.
5. Exact focused test/typecheck/build/backend results.
6. Adversarial proof summary for:
   - local focus no write;
   - one-CAS Make current;
   - rich fragment from admitted document;
   - mode switch focus preservation;
   - CAS conflict/unknown unchanged.
7. Visual walkthrough result: whether the default scan is current moment rather than identity browser.
8. Any stop condition or scope amendment.
9. Explicit confirmation that the following remain false:
   - new Playable grammar;
   - Beat kind persistence;
   - Consequence parsing/persistence;
   - P3B graph-reference opening;
   - Object Sheets;
   - Add to Combat / P4;
   - Roll/Items tools;
   - Plan→Runbook authoring;
   - backend/API/Runtime schema changes;
   - #578 mechanism reuse.

Do not turn a stale bookkeeping evidence pointer or verbose proof packaging into an independent review blocker when product/state authority is otherwise truthful. Do treat incorrect backward-looking D2/roadmap/P3B sync as a real process defect.

---

## §9 Stop / split conditions

Stop before coding outside the approved contract if any of the following becomes necessary:

1. **New durable Markdown/TipTap kind** to represent At the table, Beat kind, Consequences, Open now, Tools, or another section.
2. **Heading-name ontology** (`## At the table`, `### If they wait`, etc.) used as a hidden semantic schema.
3. **New Runtime field/schema/API** beyond existing progress.
4. **Backend change** to support the layout.
5. **Second Markdown fetch/parser/import** for Scene/Beat bodies.
6. **Graph/reference resolution** to make the basic current-moment deck useful.
7. **Combat/Roll/Items/Mechanics integration** as a prerequisite.
8. **Shared AppChrome/global style change** to make Play dark instead of Play-owned CSS.
9. **TipTap core modification** rather than reusing read-only rendering of admitted JSON.
10. **More than one extra presentation component/test pair** under the bounded discovery allowance.
11. **Need to cherry-pick/copy #578 implementation** rather than implement the accepted interaction over native authorities.
12. **Another active lane takes any §4 implementation path or mutates the same Play Runtime interaction contract.**

If one appears, report the pressure and propose the smallest split. Do not widen the PR silently.

---

## §10 Explicit non-goals

This PR does **not**:

- redesign admission;
- redesign Start Run;
- alter Run/manifest binding;
- change Scene/Beat/Choice/Option identity;
- add or infer `spine / optional / interrupt`;
- persist At the table / Read aloud / GM note / Rules now as new kinds;
- parse Consequences from prose;
- open typed references;
- make P3B dispatchable;
- add Play Object Sheets;
- add Combat or Add to Combat;
- add Roll, Items, or mechanics tools;
- redesign Plan or Build;
- add Runbook authoring;
- edit the full Runbook in Play;
- create the missing C2S27 dogfood report;
- move Runtime state into the Runbook;
- persist local focus or Table/Runbook mode;
- restore prep HTML;
- restore `MirewardPrep` globals;
- merge/cherry-pick PR #578;
- generalize adventure-specific prototype data.

---

## §11 Post-merge disposition

Do **not** automatically dispatch P3B or P4 when this PR merges.

The next cycle is:

```text
merge current-moment deck
  → atomic successor sync / re-anchor
  → dogfood Session 27-style Table UX again
  → identify the next actual table blocker
  → only then choose P3B / Combat / Roll / authoring / another Play slice
```

The current design hypothesis is that after the table hierarchy is repaired, **Open now / Play Object Sheets** may become the next high-value interaction. That is a hypothesis, not dispatch authority.

The post-merge question is not “what roadmap item was waiting?”

It is:

> **What prevented the GM from staying in native Play during the next real table walkthrough?**

