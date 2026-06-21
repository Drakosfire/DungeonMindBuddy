# Design: Command Board Surfaces — Plan, Play, Build

**Status:** Direction record after North Gate Tiptap dogfood
**Scope:** Command Board surfaces — Plan anchor pane, Play runbook UX, Build (named but not yet designed)
**Related:** runbook roadmap, Runbook Lantern anchor, PRs #135–#148, `Docs/Plans/HANDOFF-plan-mode-command-board-jumpstart.md`

---

## 0. Three surfaces, one memory

The Command Board projects the same campaign memory through **three named surfaces**:


| Surface   | Role today                                 | Primary question                                                                                |
| --------- | ------------------------------------------ | ----------------------------------------------------------------------------------------------- |
| **Plan**  | Workshop + anchor pane when overlays close | What slice of the campaign matters for the next session, and what is ready to commit?           |
| **Play**  | Table-facing runbook + operational tools   | What does the GM need in the next few minutes without losing place?                             |
| **Build** | Named, not yet designed or built           | What durable world objects (NPCs, locations, items, adversaries, rules) should exist in corpus? |


Plan replaces the older **Prep Mode** vocabulary. Play and Build are peers in the model, not afterthoughts.

**Build is not in scope for design or implementation yet.** It is still first-class in the product model so Plan and Play do not paint it into a corner.

### Surfaces teach each other

Each surface we design is both a **consumer** and a **writer** of lessons about the others:

- **Plan** consumes Build's world objects (hubs, statblocks, roll tables) and writes session scope: descriptor, ingest status, runbook target, operational seeds.
- **Play** consumes Plan's runbook and committed prep; writes back operational friction (rules hovers, spawn templates, beat navigation gaps).
- **Build** (future) will consume Play/Plan friction — the objects and depth levels the GM kept reaching for — and write durable corpus artifacts.

Every Plan or Play design decision should be checked against: **what does this imply for the other two surfaces?** Record the answer in design docs or dogfood notes so Build inherits requirements from evidence, not guesses.

All three surfaces stay constrained by the same authority boundaries:

```txt
Canon/reference = corpus files and read-only indexes
Runbook prose = session script / prep Markdown / Tiptap export
Session descriptor = planning lens (scope, sources, seeds)
Operational state = combat, clocks, live JSON — never canon prose
```

### Overlays are a shared projection primitive

Popups, hovers, and drawers are **not** a Play-only mechanism. They are the shared way every surface projects detail and tools without becoming a multi-tab dashboard. Plan, Play, and Build can all **emit** the same overlay vocabulary:

```txt
inline chip -> compact popover -> context drawer -> full modal
```

What differs per surface is **what remains when the overlay closes** (the anchor), not whether overlays exist:

- **Plan** closes back to the anchor pane (descriptor, ingest status, save boundary, workshop).
- **Play** closes back to the focused beat (never lose the table moment).
- **Build** (future) will close back to the object being constructed and its interconnections.

Design overlay components (chip, popover, drawer, modal, hover card) as **surface-agnostic** with a surface-aware "return target." Reuse the same `RunbookReferenceOverlay` / popover shell across surfaces rather than reinventing per surface.

---

## 1. What the spike proved

The North Gate Tiptap work proved the mechanics that should remain part of the Runbook Lantern direction:

1. The semantic Markdown bridge is the strongest win: Tiptap can author structured runbook intent while exported Markdown remains the durable, table-facing artifact.
2. Inline typed pills make prose feel like a command surface without requiring the runbook to become a dashboard.
3. Descriptors are the start of a document model: document identity, local draft identity, target artifact, and route behavior should not stay hardcoded forever.
4. The prepare/commit flow is the right safety instinct: local edits should be reviewed before they materialize as files.
5. Block badges are useful state awareness: live material, draft material, locked material, and reference-only material need to be distinguishable.

The key sentence for the next phase:

> The Tiptap spike proved the editing mechanics; Play Mode must now make those mechanics disappear behind a focused table surface.

## 2. What dogfood exposed

Dogfood exposed that the current Live Play surface still behaves too much like a website:

```txt
click link
navigate away
lose place
return manually
```

That is acceptable during exploration, but costly during play. A GM in the middle of a beat is tracking table attention, pressure, NPC posture, likely player actions, and spoken text. Navigation away from the current moment forces the GM to rebuild context manually.

The desired Play Mode behavior is different:

```txt
click handle
open overlay / panel / focused layer
use detail or tool
close
return to exact beat
```

The current implementation succeeded as a laboratory. The next product risk is freezing the laboratory shape into the product by extracting `/tiptap-callout-spike` too early.

## 3. Product thesis: Plan is not Play (Build is the third surface)

The runbook experience splits across surfaces with different interaction contracts.

### Plan surface

Plan is the workshop and the **anchor pane** — what remains when popups, hovers, and overlays close. It supports:

- generate
- retrieve
- arrange
- revise
- compare
- commit
- promote
- ingest prior-session recap into queryable corpus (first critical proof slice)

Plan can expose more plumbing because the GM is preparing, reviewing, and assembling material. It can show diffs, paths, diagnostics, target files, source provenance, index refreshes, descriptor identity, ingest status, and other implementation-adjacent details.

Plan is the most flexible surface: Tiptap markdown editing for timelines, runbooks, and prep docs; corpus-backed indexes; rules query/review; and the recap ingest wizard that proves context enrichment via retrieval.

### Play surface

Play is the table surface. It supports:

- run beats
- read aloud
- track pressure
- open detail overlays
- use tools
- make small in-context edits
- avoid losing place

Play should hide plumbing until the GM intentionally asks for it. The GM should be able to inspect detail, use a tool, or make a narrow correction without leaving the current runbook moment.

Play is narrower than Plan: combat, beat navigation, rules hovers, spawn actions — operational cockpit, not world construction.

### Build surface (named, not yet designed)

Build will be the wide write surface for durable world objects: locations, NPCs, items, adversaries, interconnected hub depth. We are not designing or building it yet.

While building Plan and Play, record what each surface keeps reaching for that belongs in Build (missing hub, shallow NPC card, rules term without graph entry, entity that needed a manual corpus crawl). Those notes become Build requirements when the surface is designed.

A session runbook can be edited in both Plan and Play, but the interaction model should differ. Plan feels like a workshop; Play feels like a calm table surface.

## 4. Runbook as script plus slide deck

A runbook should feel like a tight script plus slide deck:

- script, because it gives the GM table-ready language, beats, transitions, and contingencies;
- slide deck, because only the current moment should dominate attention while the rest remains available for orientation.

The primary unit becomes the **beat**. A GM should be able to:

- view the full runbook timeline;
- focus one beat;
- move Next / Back;
- drill into typed references without leaving;
- edit the visible beat in place eventually;
- lock live text during play.

This keeps the runbook linear enough to run while making it interactive enough to support live decisions.

## 5. Beat model, full timeline, and focused beat

First-pass terms:

- **Runbook document** — the full session script.
- **Beat** — a top-level playable unit.
- **Focused beat** — the current table-facing section.
- **Timeline view** — the full orientation mode for scanning the session shape.
- **Layer** — an overlay, modal, or side panel that preserves place.

Possible boundaries for existing Markdown:

- H2 sections are candidate beats.
- H3 sections are candidate sub-beats or detail sections.
- Callouts are beat content, not necessarily beat boundaries.

This is direction, not a schema. The next implementation should avoid over-specifying parsing before the table shell proves the right interaction model.

## 6. Reference chips as typed handles, not links

Reference chips are directionally right, but their product contract should be overlay-first. They are typed handles into context, tools, or source detail; they are not ordinary links whose primary behavior surprise-navigates the GM away from the runbook.

Target behavior:

- primary click opens an overlay, side panel, or focused layer;
- secondary action opens source, full detail, or a new tab;
- missing data is obvious but calm;
- chip color/type is consistent;
- label is clean and table-facing;
- metadata is tidy and avoids raw file plumbing unless requested.

Explicit rule:

> A chip may point at operational state, but a chip click must not mutate operational state without an explicit confirmation.

GM-facing chip stories:

- **NPC chip:** As a GM, I click an NPC chip and see a compact NPC card: role, current relevance, disposition, useful table note, and a full-detail link.
- **Location chip:** As a GM, I click a location chip and see the table-facing location summary, not a raw file.
- **Statblock chip:** As a GM, I click a statblock chip and see combat-relevant stats immediately, with future actions to add or use it.
- **Roll table chip:** As a GM, I click a roll-table chip and can read, roll, or use the table in place. Later, I may edit, save, and commit it from the same layer.
- **Citation chip:** As a GM, I click a citation chip and see the source excerpt or provenance without losing my current beat.
- **Action chip:** As a GM, I click an action chip and get a confirmation or launch layer, not an automatic operation.

## 7. In-place editing direction

The spike proves editing works. The product should not require navigating to `/tiptap-callout-spike` during live play.

Target Play Mode behavior:

1. unlock visible beat;
2. edit in place;
3. save local draft;
4. review commit;
5. commit runbook artifact;
6. return to the focused beat.

However, in-place editing should not be the next code PR. It should attach to a beat shell after beat navigation and overlays exist. Otherwise, the project will keep improving editor mechanics inside the wrong surface.

## 8. Save / commit workflow direction

The current proven pattern is correct:

```txt
edit locally
preview diff
commit intentionally
```

The product language should become calmer:

- Save local draft.
- Review file write.
- Commit reviewed runbook.
- Reload committed version.

The implementation plumbing should later move behind a reusable boundary such as `FileWriteWorkflow` or `RunbookFileWritePanel`. That boundary can own target path input, prepare state, stale token warning, diff rendering, commit response, diagnostics, backup path, and fingerprint details.

This PR does not implement that component. It names the seam so future work can extract it after the product shell is clearer.

## 9. Descriptor pressure and three-runbook test

Descriptors are right, but still spike-oriented. Future descriptor work should answer:

- What runbooks exist for this campaign or session?
- Which one is active in Play Mode?
- Which artifact is committed?
- Which local draft exists?
- What references are resolvable?
- What save targets are allowed?
- What surface opened the document: plan, play, or build?
- What operational tools are linked but not owned?

Use the three-runbook pressure test:

> What breaks if there are three runbooks?

Likely answers:

- hardcoded descriptors get noisy;
- localStorage behavior needs clearer UX;
- target path input becomes dangerous or noisy;
- import/reset behavior needs mode-aware copy;
- Live Play cannot hardcode every runbook surface.

This does not require a full descriptor schema yet. That belongs to a later session descriptor or ledger PR.

## 10. Component extraction implications

The old next step was to extract a reusable Tiptap editor from the spike. That is still useful, but it should happen later and against real product seams.

Potential future components:

- `PlayRunbookShell`
- `RunbookTimeline`
- `RunbookBeatNavigator`
- `RunbookBeatView`
- `RunbookReferenceOverlay`
- `RunbookChip`
- `RunbookBeatEditor`
- `RunbookFileWritePanel`
- `useRunbookDocumentState`
- `useRunbookLocalDraft`
- `useRunbookFileWrite`

Do not extract around `/tiptap-callout-spike` as the product. Extract around Play and Plan surface needs.

## 11. Re-sequenced roadmap

The next slices should move the product center of gravity toward Play Mode before extracting editor internals:

1. **PR 10A — Play Mode Runbook Product Direction**
  Docs only; captures dogfood and re-sequences the roadmap.
2. **PR 10B — Play Mode Beat Shell**
  Full timeline / focused beat toggle, Next / Back beat navigation, existing committed Markdown render, no editing yet, and no overlays except a placeholder shell if cheap.
3. **PR 11 — Non-Navigating Reference Overlay Shell**
  Chip primary click opens an overlay; source/full-detail is a secondary link; no mutation; no in-place editing.
4. **PR 12 — Reference Overlay Resolvers**
  NPC, location, statblock, roll-table, citation, and action cards; read-only first; existing resolver APIs where available.
5. **PR 13 — In-Place Beat Editing Spike**
  Edit one focused beat in place; local draft only at first; no full CMS.
6. **PR 14 — Save/Commit Workflow Extraction**
  Reusable `FileWriteWorkflow` / `RunbookFileWritePanel`; calmer product copy; existing backend prepare/commit unchanged.
7. **PR 15 — Descriptor-backed Multi-Runbook Play Entry**
  Select active runbook(s); no full session ledger yet.

The exact PR numbers may flex if existing numbering constraints require it. The dependency order is the important part.

## 12. Explicit non-goals

This direction PR must not implement:

- Play Mode shell
- beat parser
- beat navigation
- reference overlays
- in-place editing
- FileWritePanel extraction
- descriptor schema migration
- session ledger
- new backend routes
- new resolver APIs
- new chip behavior
- CSS redesign
- React rewrite of Live Play
- Tiptap route deletion
- combat launch behavior
- roll execution
- canon writes
- operational mutation

This is a direction and roadmap PR, not a product-code PR.

## 13. Review questions

1. Does this preserve the value of the Tiptap spike without mistaking the spike route for the product?
2. Is the Plan / Play / Build surface model clear enough to guide future PRs (even though Build is not yet designed)?
3. Is beat navigation the correct next product shell before in-place editing?
4. Are reference chips correctly framed as typed handles rather than links?
5. Does the roadmap avoid overbuilding a CMS or session ledger too early?
6. Does this still honor the Runbook Lantern boundary?

