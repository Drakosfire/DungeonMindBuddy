---
document_id: dmb-design-play-current-moment-cockpit
title: Play Current-Moment Cockpit — Interaction and State Contract
document_class: product_design
status: active
version: 1.0
created_at: "2026-08-21"
updated_at: "2026-08-21"
workstream: PLAY-SURFACE
architecture_authority: "ARCHITECTURE-playable-material-and-runtime.md"
companion_designs:
  play_projection: "DESIGN-play-surface-projection.md"
  authoring_adoption: "DESIGN-playable-authoring-and-adoption.md"
  approved_target: "DESIGN-play-surface-gm-cockpit-target.md"
evidence:
  - "PR #626 — Lane A2 readability + active-Run dogfood (Docs/Reports/REPORT-play-readability-dogfood-2026-08.md)"
  - "C2S27 native Play dogfood — BLOCKED / PLAY NOT READY (Docs/Reports/REPORT-play-c2s27-native-runbook-dogfood-2026-08.md)"
  - "PR #578 — Of Conks / Hempholm table-ready dogfood"
---

# Play Current-Moment Cockpit — Interaction and State Contract

## 0. Purpose and boundary

This document is the reviewed contract that turns the approved GM cockpit
target (`DESIGN-play-surface-gm-cockpit-target.md`) into implementation-ready
semantics. It exists so that no implementation PR has to decide the structural
meaning of Beat, Scene, Decision, consequence, current position, relevance,
Run migration, or Plan→Playable adoption inside product code.

It resolves, in one place:

1. canonical Beat-first Playable containment;
2. the Playable wire/serialization replacement for the Scene-first P1 grammar;
3. manifest membership/versioning replacing Scene-first P2B1;
4. Runtime current-position semantics replacing Scene-first P2B2;
5. Decision selection, consequence, and changed-relevance behavior;
6. the migration/reconciliation posture for existing sealed Scene-first Runs;
7. P2C rebase behavior across the grammar boundary;
8. the Plan→Playable authoring relationship;
9. the cockpit interaction contract, independent of exact CSS;
10. the `At a Glance` relevant-now projection contract;
11. accessibility/table-speed expectations carried forward from PR #626.

The approved target image remains stronger than a mood board and weaker than a
wire/pixel spec. This contract freezes **information architecture, interaction,
and durable semantics**. It deliberately does not freeze colors, fonts, icons,
spacing values, panel geometry, mobile composition, capability-nav labels, or
the exact membership of `At a Glance`.

Nothing here is implemented by the design PR that introduces this document.
The first implementation slice is selected by
`Docs/Plans/HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md`.

---

## 1. Canonical Playable containment (Beat-first)

The C2S27 dogfood falsified Scene-first table organization. This section
freezes the replacement containment model. There is exactly one canonical
model; no parallel equivalent representation is introduced.

### 1.1 The model

```text
Runbook (Playable Artifact)
  → ordered Beats                    durable order

Beat
  → kind: spine | optional | interrupt
  → table objective / pressure / phase
  → semantic blocks (At the table, Read aloud, GM note, Rules now, Warning)
  → ordered Scenes                   durable order
  → ordered Decisions                durable order
  → Beat-level consequences
  → typed references / contextual tools

Scene
  → concrete playable situation inside exactly one Beat
  → semantic blocks
  → typed references

Decision (durable element kind: choice)
  → prompt / meaning
  → ordered Options                  durable order

Option
  → label
  → authored consequences
  → authored transition edges (activate / suppress later Beats or Scenes)
```

### 1.2 Explicit answers

1. **Does a Runbook own an ordered collection of Beats directly?**
   Yes. Beats are direct, ordered children of the Runbook. There is no
   intermediate container.
2. **Does every Scene belong to exactly one Beat?**
   Yes. A Scene has exactly one durable parent Beat. A Scene cannot exist
   outside a Beat and cannot be shared by two Beats; two Beats that need the
   same situation reference separate Scenes or share a typed reference, never
   the same Scene identity.
3. **Can a Beat be current with no current Scene?**
   Yes. A Beat is a runnable table state by itself (objective/pressure/phase).
   `currentSceneId` is optional at all times (§4).
4. **Does every Beat require at least one Scene?**
   No. A Beat with zero Scenes is valid and runnable. Scenes are one way to
   realize a Beat, not a requirement for one.
5. **What is the canonical owner of a Decision?**
   The Beat. A Decision is a durable ordered child of exactly one Beat.
6. **Can a Decision be associated with a specific Scene while remaining
   Beat-owned?**
   Yes. A Decision may carry an optional `scene` association meaning "this
   decision is projected in this situation." The association is a projection
   hint only; it never changes the Decision's durable Beat parent, and losing
   or changing it never orphans Runtime selections (§7).
7. **Can a Scene own Decisions directly?**
   No. Scene→Decision visibility is always a projection of the Decision's
   optional Scene association. Durable ownership is Beat-only. This keeps one
   containment representation and prevents the old Scene-first grammar from
   surviving as a shadow model.
8. **Can consequences attach to Beat, Decision Option, Scene, or more than
   one?**
   Consequences attach to exactly two kinds of owners:
   - **Beat** — what becomes true when the Beat resolves or stalls;
   - **Option** — what becomes true when that Option is selected.
   Scenes do not own consequences. A Scene-level outcome is authored as a Beat
   consequence (the Scene is the situation; the Beat is the objective whose
   outcome it is) or as an Option consequence. This keeps `consequences` the
   single canonical outcome concept.
9. **What order is durable and what order is projection-only?**
   Durable: Runbook→Beat order, Beat→Scene order, Beat→Decision order,
   Decision→Option order. Projection-only: `At a Glance` ordering, relevance
   emphasis ordering, and any cockpit layout arrangement.
10. **What does `spine | optional | interrupt` mean for containment versus
    display?**
    It is a Beat **kind**: a small product vocabulary describing the Beat's
    role in session pacing. It affects projection emphasis and default
    previous/next navigation order. It does not change containment, identity,
    or membership, and it is not an event taxonomy.

### 1.3 Identity

Stable identity survives ordinary title/prose edits. Identity is carried by
semantic-Markdown directives, never by heading text:

```text
beat:<slug>      Beat
scene:<slug>     Scene
choice:<slug>    Decision (see below)
option:<slug>    Option
```

**Decision is the product word; `choice` is the durable element kind.** P1C
merged stable Choice/Option identity as a proven primitive. Renaming the wire
kind would orphan existing v1 identity for no semantic gain, so the Beat-first
grammar keeps `kind=choice` / `kind=option` on the wire and presents them as
Decisions/Options in product copy. This contract uses "Decision" in prose and
`choice` wherever the wire/serialization is meant.

---

## 2. Playable serialization — the v2 grammar (P1 replacement)

The shipped P1 grammar (`dmb-playable-element:v1`) is Scene-first: Scene at
H2, Beat/Choice at H3, every Beat/Choice required to belong to a Scene, and a
current Beat rejected unless it belongs to the current Scene. That grammar
cannot serialize the model in §1. The replacement is a new versioned grammar,
not a reinterpretation of v1.

### 2.1 Grammar version and heading map

Beat-first Playable structure is serialized as `dmb-playable-element:v2`
directives in the same admitted durable Playable work object (workspace
document / Markdown Canvas). No second Playable database is created.

```text
<!-- dmb-playable-element:v2 kind=beat id=beat:<slug> [beat_kind=spine|optional|interrupt] -->
## <Beat title>                     ← H2

<!-- dmb-playable-element:v2 kind=scene id=scene:<slug> -->
### <Scene title>                   ← H3, inside the current Beat

<!-- dmb-playable-element:v2 kind=choice id=choice:<slug> [scene=scene:<slug>] -->
### <Decision prompt>               → H3, inside the current Beat

<!-- dmb-playable-element:v2 kind=option id=option:<slug> -->
- <Option label>                    → marked list item, inside the current choice
```

Rules:

- `beat` directives attach to H2 headings.
- `scene` and `choice` directives both attach to H3 headings and are
  contained by the nearest preceding Beat. Scene and Decision are siblings
  at the same heading level; the directive `kind` — never the heading
  level — distinguishes them. This is deliberate: heading level must not
  imply Scene-to-Decision nesting, because Decisions are Beat-owned
  (§1.2). A `choice` never contains a `scene`; a `scene` never contains a
  `choice`; each is contained directly by the Beat. The optional `scene`
  attribute on `choice` names the projection association from §1.2(6) and
  must reference a Scene inside the same Beat.
- `option` directives attach to list items inside the current choice body.
- Heading level is part of the grammar. A `beat` directive on anything but
  H2, a `scene` or `choice` directive on anything but H3, or an `option`
  directive anywhere but a marked list item is a validation failure, not a
  reinterpretation.

### 2.2 Semantic blocks

Beat and Scene bodies may carry the existing semantic block vocabulary — `At
the table`, `Read aloud`, `GM note`, `Rules now`, `Warning`, `Consequence` —
plus typed references and contextual tool references. These are
presentation/use semantics inside an element body; they do not create new
containment kinds. Option bodies carry their consequences as authored
`Consequence` content and their transition edges as authored transition
attributes (§2.4).

### 2.3 Non-semantic content

Unmarked headings and ordinary prose remain non-semantic authored content.
The merged D2 rule carries forward unchanged: ordinary unmarked root headings
terminate the preceding playable body slice so later instructions stay visible
in full-structure views without acquiring element identity. Non-semantic
content never becomes a Beat/Scene/Decision by position or styling.

### 2.4 Transition edges

An Option's effect on later relevance is authored as a small transition
vocabulary on the option directive:

```text
<!-- dmb-playable-element:v2 kind=option id=option:<slug>
     activates=beat:<slug>,scene:<slug>
     suppresses=beat:<slug> -->
```

- `activates` — the referenced Beats/Scenes become emphasized for this Run
  when the Option is selected.
- `suppresses` — the referenced Beats/Scenes become de-emphasized for this
  Run when the Option is selected.
- Absence of an edge means the Option is relevance-neutral.

This is the entire transition vocabulary. There is no condition expression
language, no event bus, no arbitrary state reducer (§5.1 of the design
handoff). Targets must be IDs inside the same Runbook; edges to external
documents are validation failures.

### 2.5 Validation — fail closed

A v2 document is rejected as Playable structure (while remaining an ordinary
document) when any of these hold:

- duplicate element ID anywhere in the document;
- `scene` outside any Beat, or nested under a Scene;
- `choice` outside any Beat;
- `option` outside any Decision;
- `choice` whose `scene` association names a Scene outside its Beat or an
  unknown Scene;
- transition edge targeting an unknown ID;
- unknown `kind`, malformed directive, or unknown grammar version;
- a directive inside literal fenced code (fence interiors are never parsed;
  the v1 `~~~`/variable-length-backtick literal-treatment rule carries forward
  unchanged).

Validation failures are truthful authoring errors surfaced in the editor/Plan
surface. They are never silently repaired, re-anchored by heading text, or
dropped.

### 2.6 Forward versioning and coexistence

- The directive version is the grammar contract: `v1` documents keep v1
  semantics, `v2` documents get the model in §1.
- v1 documents are **not** auto-migrated. Converting a v1 Runbook to v2 is an
  explicit one-way authoring action that produces a new committed revision
  (§6.2).
- A document mixes grammar versions never: one document's directive family is
  determined by the versions present; a document containing both `v1` and
  `v2` structural directives is a validation failure.

---

## 3. Manifest membership and versioning (P2B1 replacement)

The sealed Run reference manifest is the Runtime-side integrity sidecar. The
existing principle is preserved: **the sidecar is not a copied Runbook** — it
stores identity, membership, parentage, and the transition edges Runtime must
interpret, while prose/titles/blocks are read from the pinned revision bytes
the Run is bound to.

### 3.1 New schema version

```text
dmb_play_run_reference_manifest_v2
```

A Run's manifest schema version is fixed at seal time and never changes
in-place. v1 and v2 manifests coexist; each is read by its own reader. Unknown
schema versions fail closed.

### 3.2 v2 membership payload

```text
schema_version: dmb_play_run_reference_manifest_v2
run_id
playable_artifact_id
playable_revision
playable_content_sha256
sealed_at
beats:    [{ beat_id, beat_kind }]                 # membership set (see order rule below)
scenes:   [{ scene_id, beat_id }]                  # parent Beat required
choices:  [{ choice_id, beat_id, scene_id? }]      # scene_id = projection association
options:  [{ option_id, choice_id }]               # parent Decision required
edges:    [{ option_id, effect: activate|suppress, target_kind: beat|scene, target_id }]
```

Membership exists to validate Runtime references and to make relevance
derivation integrity-checked against the sealed revision:

- `beats`/`scenes`/`choices`/`options` prove which IDs the Run may reference.
- `edges` are sealed because Runtime derives relevance from them (§5); they
  are the one piece of authored content Runtime interprets rather than
  renders, so they belong inside the integrity boundary.
- Display titles, prose, semantic blocks, and **all document order** are
  **not** stored; they come from the pinned revision bytes, exactly as in
  P2B1/P3A. **Document order has exactly one authority: the bound
  revision bytes.** Manifest arrays are membership sets whose
  serialization order mirrors the document for human inspection only;
  no consumer may treat manifest array order as order authority. The
  admission rule (bound revision/digest must equal the current workspace
  revision) guarantees those bytes are available whenever a Run is
  admitted, so §4 seeding ("first Beat in durable document order") and
  previous/next navigation both read order from the bound revision
  bytes — never from the manifest.

### 3.3 Seal and replay rules

- Seal derives the manifest from the **exact still-current bound revision/SHA**
  at Run creation, failing closed if the workspace has already advanced (the
  merged P2B1 rule, unchanged).
- Replay uses the immutable sidecar and never consults current workspace
  state (unchanged).
- Fail-closed on: duplicate IDs, membership reference to an unknown ID, edge
  targeting an unknown ID, edge targeting an ID outside the sealed document,
  unknown effect kind, unknown schema version.
- Transition edges that must be immutable for the Run's revision: **all of
  them**. Relevance derivation must be reproducible for the life of the Run;
  an edge that could drift under the Run would make the same selection mean
  different things on different days.


### 3.4 Rollout gate — v2 Runs are not READY-admissible in BF1

The READY invariant ("a READY v2 Run has a seeded `currentBeatId`", §4) and
the BF1 slice boundary ("no Runtime current-position change", §15) meet here.
The gate is explicit:

- BF1 ships v2 grammar, structure index, and v2 manifest seal/replay. Run
  creation against a v2 revision succeeds and seals the v2 manifest, but the
  new Run holds **no `currentBeatId`** and is **never admitted to READY**:
  the admission path rejects it fail-closed (`v2 Run admission requires the
  BF2 current-position slice`). The Run record is truthful about this state,
  exactly like an incomplete-seal Run.
- BF2 lands the §4 seeding rule and flips v2 admission on. At no merge point
  can a v2 Run be READY without a seeded `currentBeatId`.
- v1 Runs are unaffected: they create, seal, and admit exactly as on current
  `main`.

---

## 4. Runtime current-position semantics (P2B2 replacement)

### 4.1 Durable Runtime shape (conceptual)

```text
Run
  runId
  playableArtifactId
  playableRevisionId
  currentBeatId            # required once READY
  currentSceneId?          # optional; must belong to currentBeatId when present
  resolvedBeatIds[]        # sorted, duplicate/unsorted fails closed (P2B2 rule)
  selections: { choiceId: optionId }
  notesByElementId: { playableElementId: text }
  linkedCombatRuntime?     # Combat-owned handle; wire shape still separate work
  updatedAt
```

### 4.2 Explicit answers

- **Is `currentBeatId` required once a Run is READY?** Yes. Admission seeds
  it deterministically: the first `spine` Beat in durable document order;
  when no `spine` Beat exists (including a fully typed Runbook with only
  `optional`/`interrupt` Beats), the first Beat in durable document order
  regardless of kind (read from the bound revision bytes, the sole order authority — §3.2). A Runbook with zero Beats is not runnable:
  admission fails closed with a validation error (authoring an empty
  skeleton remains legal; creating a READY Run against it is not). The
  seed is an explicit admission-time durable write, not a read-time
  "pick first/latest" heuristic; the A1 active-Run rule against inferred
  selection is preserved because the seed is recorded, CAS-mutated, and
  replayed like any other progress state. Seeding lands in BF2; until
  then the §3.4 rollout gate keeps v2 Runs out of READY.
- **Is `currentSceneId` optional?** Yes.
- **Must `currentSceneId` belong to `currentBeatId`?** Yes. The manifest
  proves membership; a Scene outside the current Beat is rejected fail-closed.
- **What happens when the operator changes Beat?** The mutation sets
  `currentBeatId` and clears `currentSceneId` unless the same explicit
  mutation also names a Scene inside the new Beat.
- **Does changing Beat automatically choose a Scene?** No. Auto-choosing would
  be a hidden navigation decision; the cockpit has a truthful Beat-only state
  instead (§9, state 2).
- **What happens when a Beat has no Scene or only optional Scenes?** The Beat
  is current by itself. Nothing is fabricated.
- **What is focus/navigation state versus durable current position?**
  Durable: `currentBeatId`, `currentSceneId`, `resolvedBeatIds`,
  `selections`, `notesByElementId`. Local-only: which card is expanded, scroll
  position, Runbook-mode expansion, hovered/peeked references, and any
  transient panel state. Cosmetic focus is never persisted as authority.
- **Is Runbook-view expansion local UI state only?** Yes.
- **What is the durable resolved-state contract?** `resolvedBeatIds[]` is the
  only resolution store; it is sorted, and duplicate or unsorted persisted
  values fail closed on load (the merged P2B2 integrity rule carries forward).
- **Can a resolved Beat remain current?** Yes. Resolution is an outcome mark,
  not navigation. A GM may keep a resolved Beat current while the table
  finishes its fallout.
- **How does explicit previous/next Beat navigation behave when relevance
  changes?** Previous/next walks the durable Beat order, skipping nothing;
  relevance derivation (§5) changes emphasis, never removes a Beat from
  navigation. The GM can always reach any Beat explicitly.

---

## 5. Decision selection, consequences, and changed relevance

This is the target's central new table interaction:
`Decision → Option selected → consequence legible → later relevance changes`.
The contract deliberately separates four things that must never be conflated:

1. **Authored intent** — the Option's consequences and transition edges in the
   Playable revision (immutable for the Run).
2. **Runtime selection** — `selections[choiceId] = optionId`, the one durable
   Decision mutation.
3. **Runtime consequences actually recorded** — what became true at the table,
   recorded only through existing explicit primitives: Beat resolution, notes,
   and (separately, Combat-owned) linked runtime. The product does not infer
   that a consequence "happened" merely because an Option was selected.
4. **Projection relevance** — derived emphasis computed from sealed edges +
   current selections.

### 5.1 Selection mutation

`choiceId → optionId` remains the only durable Decision mutation. Selecting,
changing, or clearing a selection are all ordinary CAS progress mutations
validated against the sealed manifest. There is no per-Option "applied" flag
and no consequence-execution store.

### 5.2 Relevance is derived, never persisted

For each Beat/Scene, the projection computes exactly one emphasis:

```text
emphasized    — referenced by `activates` from at least one selected Option
de-emphasized — referenced by `suppresses` from at least one selected Option
                and not also activated by a selected Option
default       — otherwise
```

`resolved` is orthogonal and comes from `resolvedBeatIds`. Emphasis is a pure
function of the sealed manifest edges and the selections map; it is
recomputed, never stored. No second copy of relevance state exists to drift.

### 5.3 GM override and unexpected play

Unexpected table play is normal and must not be trapped by authored
branching:

- Navigation is never gated by emphasis; the GM can open any Beat/Scene at
  any time.
- "Reopening" a path the authored edges suppressed is done by changing or
  clearing the selection that suppressed it — a truthful statement about what
  the table actually decided — or by simply navigating there anyway.
- The GM may resolve/unresolve Beats and write notes regardless of emphasis.
- There is no separate persisted override store in the first implementation.
  If dogfooding proves a concrete operator action that cannot be reconstructed
  from selections + edges, that evidence — not speculation — justifies adding
  one.

### 5.4 Consequences are informational first

Selecting an Option displays its authored consequences and applies its
relevance effect. Anything beyond that — advancing a clock, changing a
relationship, publishing a world fact — requires an explicit GM action through
the owning authority. Consequences never automatically mutate World, Playable,
or arbitrary Runtime state. This is how the design supports
Decision→consequence→changed-relevance without growing a general rules
engine.


### 5.5 "Active Decision" is local focus; Decisions are all-visible

The cockpit makes one Decision dominant, but there is intentionally no durable
`currentDecisionId`. The reviewed rule:

- **All-visible:** every Decision in the current context — the current
  Scene's associated Decisions plus the current Beat's unassociated Decisions
  — is visible and operable. None is hidden pending "activation," and none is
  removed by emphasis.
- **Local focus:** the dominant Decision is ephemeral UI state
  (`focusedDecisionId`), in the same class as card expansion and scroll
  position. It defaults to the first unresolved Decision **in the current
  context** in durable document order, and changes only on explicit GM
  interaction with a visible in-context Decision. Focus never escapes the
  current context: when the current context has no unresolved Decision,
  `focusedDecisionId` is **null** (State 2), even if unresolved Decisions
  exist in other Scenes or Beats — reaching those is navigation, not
  focus. This keeps focus coherent with the all-visible rule: focus can
  only name a Decision the GM can already see and operate.
- **Never authority:** focus is never persisted, never blocks navigation,
  never changes relevance derivation, and is never required to make a
  selection — any visible Decision accepts its selection mutation directly.

---

## 6. Existing sealed Runs — migration and reconciliation posture

The v2 grammar is structurally incompatible with existing Scene-first sealed
Runs. The posture is explicit and conservative:

### 6.1 Migration matrix

| Situation | Posture |
|---|---|
| Old Playable revision + old (v1) manifest + old Run | **Legacy reader, bounded by the existing admission rule.** The Run remains openable, inspectable, and runnable under v1 semantics **only while its bound revision/digest is still the current workspace revision**. When the Runbook advances to any newer revision, admission returns the existing `rebase_required` state. There is no historical Playable revision archive today, and this contract does not create one. Nothing is silently migrated. |
| Old Playable revision reopened after v2 code ships | **Stays v1.** Editing continues under v1 grammar. An explicit one-way authoring action ("adopt Beat-first structure") creates a new v2 revision; it never rewrites in place. |
| Old Run whose Runbook advanced to a Beat-first (v2) revision | **Rebase-blocked terminal state.** Admission already returns `rebase_required` (bound revision no longer current), and the only rebase target is now a v2 revision, which is refused fail-closed — the grammar boundary is a semantic break, not an ID change. The Run record and its sealed manifest remain stored and inspectable as records; they are never deleted or remapped. The operator starts a new Run against the v2 revision. |
| New v2 revision + new v2 manifest + new Run | **The normal new path.** |
| Partially/incompletely sealed Run | Existing truthful incomplete handling (A1/A2) is unchanged; incomplete Runs are never "repaired" by migration. |

### 6.2 Hard rules

- No silent ID remapping, ever.
- No "pick newest/first" fallback, ever.
- No destructive cleanup of historical Runs as a migration strategy.
- v1→v2 document conversion is an authoring event that produces a new
- "Legacy reader" never implies a historical revision archive: it means the
  existing v1 admission path, bounded by the existing bound-revision rule.
  A v1 Run whose Runbook has advanced is `rebase_required`; when the current
  revision is v2, that state is terminal (cross-grammar rebase is refused).
  revision with new content; it is not a Runtime operation.

---

## 7. P2C rebase behavior across the grammar boundary

Merged P2C is preserve-only: a Run rebases to a newer revision of the same
Runbook only when every durable reference remains admissible. That rule is
necessary but not sufficient once containment itself can change.

- **Same-grammar rebase (v1→v1, v2→v2):** preserve-only rebase remains the
  contract, with the additions below.
- **Cross-grammar rebase (v1→v2):** out of scope for the first implementation
  (§6.1); the operator starts a new Run.
- **Scene changes parent Beat:** semantic incompatibility. A Runtime
  `currentSceneId` validated against the old parentage is not the same
  reference under the new parentage. Fail closed with a blocker receipt.
- **Decision changes Scene association but not Beat ownership:** preserved.
  The association is a projection hint, not membership; selections validate
  against `choice_id`, which is unchanged.
- **ID mapping:** none in the first implementation. No mapping language, no
  rename table.
- **Blocker receipt:** when rebase cannot preserve Runtime truth, the operator
  sees an explicit per-reference receipt — which Beat/Scene/Decision/Option
  IDs became inadmissible and why — matching the merged P2C blocker semantics.
  The Run stays bound to its source revision; nothing is half-migrated.

Conservative fail-closed beats speculative mapping at this boundary.

---

## 8. Plan → Playable authoring

The settled C2S27 rule stands: **Plan authors/adopts the exact Playable
material; there is no lossy derivative export.** Under the Beat-first model:

- **Plan edits the same admitted Playable work object directly.** The
  workspace document / Markdown Canvas remains the authoring authority; Save
  is the ordinary revision boundary.
- **Free-form planning documents** may exist for early thinking. Adopting
  their material into the Playable work object is an explicit, reviewable
  adoption action (same proposal/adoption seam as Hermes proposals), never a
  batch export.
- **Creating/reordering Beats** uses structure-aware authoring controls over
  the same document — insert Beat, move Beat, set kind — which write v2
  directives. Plan does not become a graph editor; the document stays the
  source of truth and stays readable as a document.
- **Creating/reordering Scenes within Beats** works the same way, constrained
  by the §1 containment rules with validation errors surfaced in the editor.
- **Decisions/Options/consequences** are authored as marked blocks in the
  same object: a Decision with its prompt, its ordered Options, and each
  Option's consequences and activate/suppress edges.
- **Preview honesty:** what Play projects is computed from the same committed
  revision the GM saves. The Plan preview and the Play projection are two
  projections over one truth; there is no transform that could drop semantic
  blocks, styling, or stable identity between them.
- **Semantics visible during authoring:** Beat kind, Scene membership,
  Decision Options, consequences, and transition edges are all visible and
  editable in Plan, so Play never surprises the GM with hidden structure.

---

## 9. Cockpit interaction contract

This contract is independent of exact CSS. For each state: dominant
information, durable mutation available, local-only interaction state,
exit/return behavior, and what must remain visible for orientation.

### State 1 — Resume / choose / start

- Dominant: explicit choice among Resume active Run, Start New Run, choose an
  existing Run (merged A1 semantics).
- Durable mutation: only explicit Start New (allocates one Run UUID through
  the existing create+seal flow) or explicit exact-Run open.
- Local-only: chooser browsing/highlight.
- Exit/return: Resume resolves the server-side active pointer and lands in
  State 2/3; ordinary re-entry creates no Run.
- Orientation: the active Run's identity is truthful; incomplete Runs are
  visibly distinguished from READY Runs.

### State 2 — READY cockpit, no active Decision

- Dominant: current Beat (objective/pressure/phase), current Scene when set,
  relevant-now references, previous/next Beat navigation.
- Durable mutation: set current Beat/Scene, resolve/unresolve Beat, notes.
- Local-only: card expansion, scroll, Runbook expansion.
- Exit/return: any projection opens over the moment and closes back to it.
- Orientation: Run title, current Beat, and Beat position in the Runbook
  order are always visible.

### State 3 — READY cockpit with Decisions in context

- Dominant: the focused Decision's prompt, its Options, each Option's
  consequence framing, and current selection state. "Focused" is the §5.5
  local-focus rule: all in-context Decisions remain visible and operable; the
  dominant one is ephemeral `focusedDecisionId`, never durable authority.
- Durable mutation: select/change/clear the Option (one CAS mutation) on any
  visible Decision.
- Local-only: `focusedDecisionId`, Option hover/peek at consequence detail.
- Exit/return: selection immediately re-derives emphasis (State 4).
- Orientation: the focused Decision is visibly inside the current Beat; the
  current Beat/Scene remain identifiable without scrolling away; unfocused
  in-context Decisions remain discoverable without navigation.

### State 4 — Decision selected: consequence and changed relevance visible

- Dominant: the selected Option's authored consequences and the resulting
  emphasis change on later Beats/Scenes.
- Durable mutation: none beyond the selection itself; recording "what actually
  happened" uses notes/resolution explicitly.
- Local-only: which consequence detail is expanded.
- Exit/return: the GM keeps going — the cockpit returns to State 2 with the
  new emphasis visible.
- Orientation: what changed is legible at a glance; nothing navigates away
  automatically.

### State 5 — Runbook full-structure view

- Dominant: the full authored Runbook document (merged D2 projection),
  including de-emphasized material — emphasis is shown, never hidden.
- Durable mutation: none (read-only projection).
- Local-only: expansion/scroll.
- Exit/return: returns to the exact current moment (same Beat/Scene).
- Orientation: current Beat/Scene remain marked inside the full structure.

### State 6 — Context projection open (NPC/Threat/Rule/Note/Map/source)

- Dominant: the opened object's table-useful projection (Play Object Sheet
  family), led by table usefulness, not graph internals.
- Durable mutation: none from opening; explicit actions inside (e.g. Add to
  Combat) are separate cross-domain actions.
- Local-only: the panel/layer itself.
- Exit/return: close returns to the exact current moment with focus restored
  to the invoking control.
- Orientation: the current Beat context remains perceptible behind/beside the
  projection; opening a reference never mutates runtime/canon.

### State 7 — Return from projection to exact current moment

- Dominant: the same current Beat/Scene/Decision as before the projection.
- Durable mutation: none.
- Local-only: none.
- Exit/return: this state is the contract's proof point — no context
  reconstruction is required after any detail opening.
- Orientation: identical to the pre-open state.

### State 8 — Combat launch / return context boundary (interaction only)

- Dominant: explicit Combat entry from the current moment (e.g. from a Threat
  reference), and explicit return.
- Durable mutation: Combat-owned state changes belong to Combat; the Play Run
  may hold a `linkedCombatRuntime` handle (wire shape remains separate Combat
  work). Play never absorbs HP/initiative/conditions.
- Local-only: none in Play.
- Exit/return: returning lands on the exact current moment; Combat outcomes
  inform the Run only through explicit GM action (notes, resolution).
- Orientation: the session context (Run, current Beat) survives the round
  trip.

### State 9 — Warning / incomplete state

- Dominant: truthful warning — incomplete Run, blocked admission, integrity
  failure, rebase blocker receipt.
- Durable mutation: only explicit retry/repair actions that already exist.
- Local-only: dismissal of purely cosmetic notices (never of integrity
  states).
- Exit/return: repair paths return to a truthful state; fail-closed states
  stay closed.
- Orientation: warnings are visually distinct from prose (PR #626 baseline)
  and never overwrite the current-moment context.

### State 10 — Narrow viewport degradation (conceptual priority)

- Dominant: current Beat first, then current Scene, then focused Decision (§5.5),
  then relevant-now support, then navigation.
- Durable mutation: unchanged.
- Local-only: stacking/collapse.
- Exit/return: unchanged.
- Orientation: when space forces choices, orientation beats density; collapse
  order follows the dominance order above. Exact breakpoints are an
  implementation/design-system decision.

---

## 10. `At a Glance` — relevant-now projection contract

The target's `At a Glance` region is a **projection contract**, not a fixed
schema and not a universal object dashboard.

- **Contributing authorities:** Playable (typed references authored on the
  current Beat/Scene), Runtime (notes on current elements; linked Combat
  handle when present), Mechanics (exact threat/statblock bindings reachable
  from those references), World (identity/role of referenced objects), Source
  (human-readable source labels on referenced material).
- **Seeding:** the current Beat and current Scene's authored references seed
  the region. Nothing appears merely because it exists in the campaign.
- **Runtime contribution:** small current-run status only — e.g. an active
  linked Combat, an unresolved note — never a runtime dump.
- **Mechanics/Combat links:** represented as typed references opening the
  normal projections (State 6) or the explicit Combat action (State 8).
- **Curated, not exhaustive:** the region shows what is relevant now. Full
  graph adjacency remains Advanced / another projection.
- **Empty state:** when nothing is relevant, the region says so truthfully
  and points at the Runbook full-structure view. It never fabricates filler.

---

## 11. Accessibility and table speed

The PR #626 readability baseline is retained and extended, not re-decided:

- current/selected/emphasis states are perceivable without color alone
  (text/icon/weight in addition to color);
- primary controls remain keyboard reachable with visible focus;
- opening a context projection and closing it returns focus to the invoking
  control;
- high-frequency actions (previous/next Beat, select Option, resolve, note)
  keep table-speed target sizes;
- dense structural metadata (UUIDs, revisions) stays visually subordinate to
  authored content;
- warnings remain distinct from prose;
- emphasis changes from Decisions are announced in text ("now emphasized" /
  "now de-emphasized"), not by color shift alone.

Exact CSS values remain unfrozen here.

---

## 12. Required design examples

### Example A — current moment without a Decision

Material: the Lane A1/A2 dogfood Runbook shape (Gate / Approach), extended to
Beat-first form.

```text
Runbook: Wall Breach at the Mill
  beat:approach   (spine)     "Approach the breach"
    scene:gate                "The mill gate"
  beat:aftermath  (optional)  "After the breach"
    scene:counting            "Counting the cost"
```

Run state (durable):

```text
currentBeatId:  beat:approach
currentSceneId: scene:gate
resolvedBeatIds: []
selections: {}
notesByElementId: { scene:gate: "Players suspect the miller" }
```

Cockpit projection (derived, not stored):

```text
Current Beat:  Approach the breach — objective/pressure text
Current Scene: The mill gate — situation text
At a Glance:   references authored on beat:approach / scene:gate
No Decision in the current context (nothing to focus)
```

Durable versus projection-only: the Run fields above are durable; the Beat
deck position, card expansion, and At a Glance ordering are projection-only.

### Example B — Decision changes later relevance

Authored (Playable, immutable for the Run):

```text
Decision choice:seal-or-search  "Seal the breach now, or search the mill first?"
  Option option:seal    "Seal it now"
    consequence: "The breach is contained; the miller's secret stays buried."
    activates:   beat:aftermath
  Option option:search  "Search first"
    consequence: "You find the ledger, but the breach widens."
    activates:   scene:cellar
    suppresses:  beat:aftermath
```

Runtime selection (durable): `selections[choice:seal-or-search] = option:search`.

Resulting relevance projection (derived): `scene:cellar` emphasized;
`beat:aftermath` de-emphasized; both remain navigable and visible in Runbook
view.

Operator override/reopen: the GM changes the selection to `option:seal` (the
table actually reversed), or simply navigates to `beat:aftermath` anyway —
navigation was never gated. No override store exists.

Not automatically mutated: the miller NPC's World relationships, any clock
values, and the "you find the ledger" fiction. Recording that the ledger was
actually found is an explicit note/resolution; promoting it to World truth is
the separate governed path.

### Example C — C2S27-style table pressure

Repository evidence: the C2S27 dogfood (`REPORT-play-c2s27-native-runbook-
dogfood-2026-08.md`) ran the Mireward wall-breach session where the HTML
Combat Tracker carried the table while native Play was abandoned. Under this
contract, that same moment projects as:

```text
Current Beat:  "Hold the wall" (spine) — pressure: the breach is widening
Current Scene: "The breach line" — threats referenced here
Focused Decision (§5.5): "Fall back or hold?"
  Hold  → consequence: "The line holds; the wounded stay in reach."
          suppresses beat:regroup
  Fall back → consequence: "The courtyard is given up."
          activates beat:regroup, suppresses scene:breach-line
At a Glance: the two referenced Threats (exact mechanics), the linked Combat
             handle once the GM explicitly launches Combat, the note
             "Torbin fled west" recorded earlier on scene:breach-line
```

The GM orients (Beat/Scene visible), the table decides, the GM records the
selection in one action, consequences and changed emphasis are immediately
legible, the Threat sheet opens and closes without losing the moment, and
Combat launches as an explicit cross-domain action whose state remains
Combat-owned. The messy live moment — pressure, threats, a note, a branch —
is representable without navigating away.

### Example D — old Run across the grammar boundary

Old: v1 Scene-first Run `R-old` bound to revision 12 of Runbook `M`, sealed
under `dmb_play_run_reference_manifest_v1` (Scene at H2, Beat/Choice at H3).

New: the GM explicitly adopts Beat-first structure in Plan, producing revision
13 of `M` serialized as v2 — a new committed revision, not an in-place
rewrite.

Behavior:

- Once revision 13 is committed, `R-old` admission returns the existing
  `rebase_required` state: its bound revision is no longer the current
  workspace revision, and no historical revision archive exists to serve
  revision 12 bytes.
- Rebase of `R-old` to revision 13 is refused fail-closed: the receipt lists
  that containment itself changed (v1-to-v2), so no preserve-only proof is
  possible. `R-old` is now in a truthful rebase-blocked terminal state.
- The operator starts a new Run against revision 13, which seals a v2
  manifest.
- Nothing about `R-old` is deleted, remapped, or reinterpreted; the Run
  record and sealed manifest remain stored and inspectable as records.

### Example E — Plan authors what Play will run

The GM authors in Plan, directly in the admitted Playable work object:

```text
<!-- dmb-playable-element:v2 kind=beat id=beat:approach beat_kind=spine -->
## Approach the breach
<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->
### The mill gate
<!-- dmb-playable-element:v2 kind=choice id=choice:seal-or-search scene=scene:gate -->
### Seal the breach now, or search the mill first?
<!-- dmb-playable-element:v2 kind=option id=option:seal activates=beat:aftermath -->
- Seal it now
```

Ordinary Save commits revision N. Play admits a Run against revision N and
projects exactly the Beat/Scene/Decision the GM saw in Plan — same bytes,
same IDs, same blocks. No export, no transform, no dropped styling, no
semantic drift between workshop and table.

---

## 13. Design consistency audit

| Concern | Existing truth | Reviewed decision | Authority updated |
|---|---|---|---|
| Beat/Scene containment | Beat-first direction; wire unresolved; shipped P1/P2 Scene-first | §1: Runbook→Beats; Beat owns Scenes/Decisions; Scene has exactly one Beat; Beat runnable without Scene. §2: Scene and Decision serialize as H3 siblings under the Beat; the directive kind, never heading level, distinguishes them | this document; architecture §5 |
| Decision ownership | stable Choice/Option primitive (P1C); exact containment unresolved | §1.2: Beat-owned; optional Scene projection association; `choice` stays the wire kind, "Decision" the product word | this document; architecture §6 |
| Manifest | Scene-first P2B1, identity/membership only | §3: `dmb_play_run_reference_manifest_v2` adds parentage + sealed activate/suppress edges; prose and all document order stay in the pinned revision bytes (sole order authority) | this document; architecture §5/§7 |
| Current position | Scene-first relationship constraint (Beat must belong to current Scene) | §4: `currentBeatId` required and seeded at admission; `currentSceneId` optional and must belong to current Beat | this document; architecture §7 |
| Relevance | product requirement; persistence unresolved | §5: derived from sealed edges + selections; never persisted; two-effect vocabulary; navigation never gated | this document; architecture §6/§7 |
| Old Runs | v1 manifests/Runs exist | §6: legacy reader; explicit one-way v2 adoption at authoring; no cross-grammar rebase; no silent remapping | this document; architecture §7/§11 |
| Rebase | preserve-only P2C | §7: same-grammar preserve-only; parent-Beat change fails closed; Scene-association change preserved; no ID mapping | this document; architecture §7 |
| Plan→Playable | no lossy export (settled) | §8: Plan edits the same admitted work object; explicit adoption for free-form docs; preview = same revision | this document; authoring design |
| Cockpit UX | approved target image | §9/§10/§11: ten-state interaction contract; At a Glance projection contract; #626 accessibility baseline retained | this document; projection design |
| Combat seam | Combat-owned; C2S27 ran on the tracker | §9 state 8: explicit launch/return interaction boundary; no Combat schema absorbed; durability remains Lane B | this document only |

No row defers a product/architecture question needed by the first
implementation slice.

---

## 14. Table-running state-transition table

| Action | Kind | Detail |
|---|---|---|
| Open/resume Run | durable Runtime read + active-pointer read | bare `/play` resolves the Play-owned active selection (A1); no Run created |
| Start New Run | durable Runtime mutation | explicit create+seal; one UUID per explicit attempt (D1) |
| Select Beat | durable Runtime mutation | sets `currentBeatId`; clears `currentSceneId` unless a Scene in the new Beat is named in the same mutation |
| Select Scene | durable Runtime mutation | sets `currentSceneId`; must belong to current Beat |
| Resolve/unresolve Beat | durable Runtime mutation | `resolvedBeatIds`, sorted, fail-closed integrity |
| Select/change/clear Decision Option | durable Runtime mutation | `selections[choiceId]`; relevance re-derived, not stored |
| Decision changes relevance | local projection derivation | pure function of sealed edges + selections |
| Open/close contextual projection | local projection/focus only | never mutates runtime/canon; focus returns to invoker |
| Switch Table/Runbook | local projection/focus only | mode and expansion are local (D2) |
| Write note | durable Runtime mutation | `notesByElementId` under CAS |
| Choose another Run | durable Runtime read + explicit navigation | chooser entry itself creates nothing |
| Launch/return Combat | cross-domain explicit action | Combat-owned state; Play holds at most a linked handle |

---

## 15. Implementation decomposition

Atomic capabilities, in dependency order. Only the first is authorized by the
successor handoff in this design PR.

### BF1 — Beat-first Playable grammar and manifest foundation

- Capability: v2 serialization (parse/validate/serialize), structure index
  over v2, and v2 manifest seal/replay — no cockpit UI, no Runtime
  current-position change.
- Owning flow: PLAY-SURFACE.
- Merge-ready invariant: a v2 Runbook round-trips through
  import/edit/save/reload with stable Beat/Scene/Decision/Option identity;
  validation fails closed on illegal containment, duplicate IDs, and bad
  edges; a Run created against a v2 revision seals a v2 manifest whose
  membership and edges replay without consulting current workspace state.
- Expected production write lease: Playable grammar/serialization, structure
  index, manifest service/routes, and their tests.
- Rollout gate: §3.4 applies — BF1 seals v2 manifests but never admits a
  v2 Run to READY; BF2 lands the §4 seed and flips admission.
- Runtime state collisions: none — v1 Runs and manifests untouched.
- Predecessor: this design PR.
- Remains false after merge: cockpit UI, v2 current-position semantics,
  relevance projection, Plan authoring controls, any migration tooling.

### BF2 — Runtime current-position v2 and relevance derivation

- Capability: `currentBeatId` seeding/optionality rules, Scene membership
  validation, derived emphasis from sealed edges.
- Predecessor: BF1. Remains false: cockpit presentation of the new semantics.

### BF3 — Current-moment cockpit projection

- Capability: the §9 interaction contract as the default Play table view over
  v2 Runs, retaining the #626 readability baseline.
- Predecessor: BF2. Remains false: Plan-side Beat-first authoring controls.

### BF4 — Plan Beat-first authoring composition

- Capability: structure-aware Beat/Scene/Decision authoring over the admitted
  work object, with the honest preview of §8.
- Predecessor: BF1 (grammar), schedulable in parallel with BF2/BF3 after a
  fresh re-anchor.

### BF5 — Legacy v1 reader hardening and operator-facing migration posture

- Capability: the §6/§7 matrix as product behavior — legacy open, explicit
  v2 adoption action, fail-closed cross-grammar receipts.
- Predecessor: BF1–BF3 evidence.

Combat durability (Lane B) remains separately sequenced and is not a
predecessor of BF1.

---

## 16. Roadmap review disposition

```text
ROADMAP_REVIEW — UPDATED
```

This design PR freezes previously unresolved structural design: Beat-first
containment (§1), the v2 wire grammar (§2), the v2 manifest (§3), v2
current-position semantics (§4), derived relevance (§5), the migration/rebase
posture (§6/§7), and the Plan→Playable composition (§8). The living roadmap's
"next design task" gate is consumed by this contract, and its "next dispatch"
becomes BF1 via `HANDOFF-PLAY-SURFACE-beat-first-playable-foundation.md`.
Scene-first remains falsified as the target model; this PR does not implement
or claim the Beat-first structure in code.

---

## 17. Non-goals

- No production implementation in the introducing PR.
- No general condition/rules engine, event bus, or workflow DSL.
- No persisted relevance copy without dogfood evidence that derivation is
  insufficient.
- No automatic consequence execution into World/Runtime state.
- No Combat persistence decisions (Lane B remains separate).
- No second Play chrome; shared AppChrome/projection-host ownership stands.
- No frozen aesthetics: colors, fonts, icons, spacing, panel geometry, mobile
  composition, and exact `At a Glance` membership remain open.
- No claim that existing sealed Runs have been migrated.
- No claim that cross-worktree persistence is solved (CR-U17 remains false
  overall).
