# DESIGN — Runbook Roadmap and Session Ingestion

**Status:** Design anchor / roadmap capture
**Created:** 2026-06-18
**Project area:** DungeonBuddy / Command Board / Tiptap runbook / session prep ingestion
**Related:**

- `Docs/Plans/DESIGN-session-runbook-command-surface.md`
- `Docs/Plans/PLAN-configurable-markdown-rendering-and-tiptap-styling.md`
- `Docs/Design/DESIGN-mireward-command-board-shell.md`
- `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`
- `Docs/Design/DESIGN-play-mode-runbook-product-direction.md`

---

## 0. Purpose

This document captures the planned PR sequence for turning the Command Board runbook into a typed, tool-aware command surface, and extends that roadmap with the missing session ingestion / next-session construction model.

The key framing:

> C2S23 Mireward is the starting point and proof model, not the hardcoded future product.

The current Mireward Live Play page, corpus indexes, Tiptap spike, Markdown renderer, and combat/toolbox surfaces prove useful interaction patterns. The next architectural step is to make those patterns reusable for building the next session, not merely continuing to run the current one.

---

## 1. Core Product Boundary

The runbook should remain a table-facing projection of prep.

It should:

- Read like a linear session script.
- Behave like a command surface.
- Make important nouns and procedures clickable.
- Preserve safe write boundaries.
- Keep canon/reference data, runbook prose, and operational state separate.

It should not become:

- A generic CMS.
- A dashboard of every prep object.
- A combat tracker embedded in prose.
- A statblock database.
- A corpus editor.
- A hidden canon mutation surface.

The durable separation remains:

```txt
Tiptap JSON = local editable working-board state
Exported Markdown = derived artifact
Backend API = intentional file materialization boundary
Prep Markdown file = durable table-facing runbook artifact
Corpus/canon = separate authority boundary
Operational JSON = live combat/clocks/tools state
```

---

## 2. Roadmap Shape

The work should proceed by small contracts rather than by attempting to build the entire runbook system at once.

Recommended tracks:

1. **Runbook rendering and chip command surface** — make Markdown references visible and interactive.
2. **Runbook authoring and safe write loop** — make Tiptap author the same artifacts safely.
3. **Session-data ingestion and dynamic next-session construction** — make C2S23 patterns reusable for C2S24 / future sessions.

Manual dogfooding should be minimal except where human UI experience is the thing being tested. Visual hierarchy, editor feel, and table-readiness require dogfood. Pure schema, parser, and refactor work should mostly rely on tests.

---

# Track A — Runbook Rendering and Chip Command Surface

## PR 1 — Typed Markdown Reference Chips

**Branch:** `feat/runbook-reference-chips`
**Title:** `feat(command-board): add typed runbook reference chips`

### Goal

Add a Markdown-compatible typed reference syntax and render recognized links as inline chips in the existing static Markdown renderer.

### Scope

Recognize links whose href starts with:

```txt
#dmb-ref:
#dmb-action:
```

Initial examples:

```md
[Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)
[North Reach Gate](#dmb-ref:location:north-reach-gate)
[Sewer Meat Creature](#dmb-ref:statblock:sewer-meat-creature)
[Gate Dilemma d12](#dmb-ref:roll-table:gate-dilemma-d12)
[Session 22 ending](#dmb-ref:citation:c2s22-ending)
[North Gate Combat](#dmb-action:combat:north-gate-combat)
```

Render valid typed refs as inert semantic chip buttons:

```html
<button
  type="button"
  class="md-ref-chip md-ref-chip-npc"
  data-md-ref-kind="ref"
  data-md-ref-type="npc"
  data-md-ref-id="lysandro-ironveil"
>
  Lysandro Ironveil
</button>
```

For action links:

```html
<button
  type="button"
  class="md-ref-chip md-ref-chip-action md-ref-chip-action-combat"
  data-md-ref-kind="action"
  data-md-ref-type="combat"
  data-md-ref-id="north-gate-combat"
>
  North Gate Combat
</button>
```

### Files likely touched

- `evals/c2_live_prep/mireward-prep/assets/prep-markdown.js`
- `evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css`
- `evals/c2_live_prep/mireward-prep/fixtures/markdown-theme-sample.md`
- `apps/live-control-ui/src/test/prepMarkdownRenderer.test.ts`

### Out of scope

- Popovers.
- Resolver lookups.
- API calls.
- Tiptap chip nodes.
- Roll UI.
- Combat launch.

### Manual dogfood

Small visual dogfood only.

Open the Markdown theme fixture and confirm chips remain readable inline, visually distinct, and not more prominent than the prose around them.

---

## PR 2 — Tiptap Inline Reference Chip Spike

**Branch:** `spike/tiptap-inline-reference-chips`
**Title:** `spike(command-board): prototype Tiptap inline reference chips`

### Goal

Teach Tiptap to represent typed references as inline atom nodes and export them to the Markdown fallback syntax from PR 1.

### Scope

Add one inline atom node, likely `runbookRef`, with attrs:

```ts
type RunbookRefAttrs = {
  refType: string;
  refId: string;
  label: string;
  href: string;
};
```

Add simple developer controls to insert sample refs.

Export to Markdown:

```md
[Label](#dmb-ref:type:id)
[Label](#dmb-action:type:id)
```

### Out of scope

- Polished chip editor UI.
- Autocomplete.
- Resolver.
- Markdown import.
- Document manager.

### Manual dogfood

Minimal loop dogfood.

Insert several chips into prose, export, prepare/commit, and reload the static Command Board render. This validates the key authoring contract: Tiptap state can produce Markdown that the static renderer already enhances.

---

## PR 3 — Runbook Reference Chip Popover Shell

**Branch:** `feat/runbook-reference-popover-shell`
**Title:** `feat(command-board): add runbook reference chip popover shell`

### Goal

Make typed chips interactive without real data resolution yet.

### Scope

Clicking or focusing a chip opens a compact popover or calm side context card showing:

- Label.
- Kind.
- Type.
- Ref id.
- Href.
- Placeholder actions appropriate to the type.

The interaction ladder remains:

```txt
inline chip -> compact popover -> context drawer -> full modal
```

### Out of scope

- API-backed lookup.
- Real NPC/statblock/location rendering.
- Real roll UI.
- Combat mutation.

### Manual dogfood

Yes, but tiny.

Read a sample runbook and click several chips. Confirm the popover does not steal the thread or turn the page into a dashboard.

---

## PR 4 — API-Backed Reference Resolver v1

**Branch:** `feat/runbook-reference-resolver-v1`
**Title:** `feat(command-board): resolve runbook reference chips from live indexes`

### Goal

Resolve chips into compact cards using existing read-only indexes where available.

### Scope

Use existing or adjacent services for:

- NPCs.
- Locations.
- Statblocks.
- Roll tables.
- Citations / source placeholders.
- Actions / combat placeholders.

The resolver should return either a resolved compact payload or a clear unresolved state.

### Out of scope

- Corpus mutation.
- Full modal editors.
- Roll-table editing.
- Combat tracker mutation.
- Universal knowledge graph design.

### Manual dogfood

One scripted resolver sample:

- One NPC.
- One location.
- One statblock.
- One roll table.
- One missing ref.

Confirm unresolved refs are useful and non-alarming.

---

# Track B — Runbook Authoring and Safe Write Loop

## PR 5 — Tiptap-Authored Command Board Runbook Dogfood

**Branch:** `feat/tiptap-authored-command-board-runbook`
**Title:** `feat(command-board): dogfood a Tiptap-authored session runbook`

### Goal

Create one table-facing runbook authored through Tiptap, materialized through the backend prepare/commit flow, and rendered by the static Command Board with typed chips.

### Target file

```txt
evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md
```

### Scope

- Author one runbook through the Tiptap flow.
- Write through prepare/commit.
- Render through a static Markdown embed.
- Include chips for major initial types.
- Add an edit link from the static surface to the editor route.

### Out of scope

- Full query-param document manager.
- Markdown import.
- Corpus writes.
- Replacing every Live Play surface.

### Manual dogfood

Yes.

This is the first actual product loop. Confirm the resulting page feels like something the GM can run from, not merely a successful file write.

---

## PR 6 — Tiptap Runbook Document Descriptors

**Branch:** `feat/tiptap-runbook-document-descriptors`
**Title:** `feat(command-board): add Tiptap runbook document descriptors`

### Goal

Replace hardcoded Tiptap document identity, title, localStorage key, and target path values with a small descriptor registry.

### Descriptor shape

```ts
type TiptapRunbookDescriptor = {
  documentId: string;
  title: string;
  campaignId: string;
  session: number;
  targetRelpath: string;
  themeId: "command" | "plain" | "statblock";
  description?: string;
};
```

### Scope

- Add a local descriptor registry.
- Support a route query like `/tiptap-callout-spike?doc=north-gate-session-runbook`.
- Key localStorage by document descriptor.
- Set default write target from descriptor.

### Out of scope

- Backend descriptor registry.
- Multi-document dashboard.
- Markdown import.

### Manual dogfood

Very light.

Open two descriptors and confirm local draft state does not collide.

---

## PR 7 — Minimal Markdown to Tiptap Import v1

**Branch:** `feat/tiptap-runbook-markdown-import-v1`
**Title:** `feat(command-board): import supported runbook Markdown into Tiptap`

### Goal

Load a committed runbook Markdown file back into Tiptap for supported syntax.

### Supported import

- Headings.
- Paragraphs.
- Lists if cheap.
- Semantic callouts.
- Typed reference links.
- Basic marks if already reliable.

### Out of scope

- Full CommonMark import.
- Arbitrary HTML.
- Corpus import.
- Perfect round-trip fidelity for unsupported Markdown.

### Manual dogfood

One reopen/edit/commit cycle.

Import an existing committed runbook, tweak one paragraph, preserve chips/callouts, commit back, and reload static render.

---

## PR 8 — Block Save-State Badges

**Branch:** `feat/runbook-block-save-state-badges`
**Title:** `feat(command-board): show runbook block save-state badges`

### Goal

Make edit, canon, and live boundaries visible at block level.

### Initial states

```txt
local scratch
saved draft
locked for live
committed prep
read-only reference
operational
```

### Scope

- Render badges for selected or hovered blocks.
- Show whether a block is local, committed, locked, read-only, or operational.
- Add basic lock/unlock affordance for live play blocks.

### Out of scope

- Full block database.
- Collaborative editing.
- Fine-grained permissions.
- Broad document workflow redesign.

### Manual dogfood

Yes, short.

Try to edit a locked block and a read-only/reference block. Confirm the UI prevents mistakes without feeling bureaucratic.

---

## PR 9 — Replace One Real Markdown Surface

**Branch:** `feat/replace-north-gate-runbook-markdown-surface`
**Title:** `feat(command-board): replace North Gate runbook surface with Tiptap-backed authoring`

### Goal

Replace one existing Markdown-only prep surface with a Tiptap-backed runbook workflow.

### Scope

- Pick one real North Gate / Live Play runbook surface.
- Keep static rendering as the play-facing default.
- Add edit link to the Tiptap document editor.
- Use descriptor route.
- Support import or explicit seeded source depending on prior PR state.
- Commit back to safe prep file.

### Out of scope

- Replacing every Markdown surface.
- Generic CMS.
- Player-facing publishing.

### Manual dogfood

Yes.

Run a mock five-minute session opening from the page. Edit one detail, prepare/commit, reload, and confirm the page updates cleanly.

---

## PR 10A — Play Mode Runbook Product Direction

**Branch:** `docs/play-mode-runbook-product-direction`
**Title:** `docs(command-board): capture play-mode runbook direction`

### Goal

Capture the dogfood learning from the North Gate Tiptap-backed Live Play runbook and re-sequence the roadmap around the Prep Mode / Play Mode split.

The old next step was to extract a reusable Tiptap editor from the spike. Dogfood showed that extraction is still needed, but not before Play Mode has a product shell. Extracting the spike too early would preserve the wrong center of gravity.

### Scope

Document:

- What the Tiptap spike proved.
- Why Live Play must behave like a table surface instead of a website.
- Prep Mode as workshop and Play Mode as table surface.
- Beat navigation as the next shell.
- Reference chips as overlay-first typed handles.
- In-place editing as a later layer on focused beats.
- Save/commit workflow extraction as a later reusable boundary.
- Descriptor pressure from multi-runbook support.

### Out of scope

- Runtime code.
- Play Mode shell.
- Beat parser or navigation.
- Reference overlays.
- In-place editing.
- File-write component extraction.
- Backend routes, resolver APIs, session ledger, CMS, canon writes, or operational mutation.

### Manual dogfood

No runtime dogfood. This is a design lock and roadmap correction.

## PR 10B — Play Mode Beat Shell

**Branch:** `feat/play-mode-runbook-beat-shell`
**Title:** `feat(command-board): add play-mode runbook beat shell`

### Goal

Build the smallest Play Mode shell before extracting editor internals.

### Scope

- Full timeline / focused beat toggle.
- Next / Back beat navigation.
- Existing committed Markdown render as source.
- No editing yet.
- No real overlays yet, except a placeholder layer if cheap.

### Out of scope

- In-place editing.
- Reference resolvers.
- File-write workflow extraction.
- Descriptor schema migration.
- Session ledger.

### Manual dogfood

Yes. Run a short table-flow read and confirm the GM can move between beats without losing place.

## Later — Reusable Tiptap Runbook Editor / File Write Extraction

The reusable editor is still needed, but extraction should follow real product seams rather than the `/tiptap-callout-spike` route shape.

Likely later seams include `RunbookBeatEditor`, `RunbookFileWritePanel`, `useRunbookDocumentState`, `useRunbookLocalDraft`, and `useRunbookFileWrite`.

---

# Track C — Session Data Ingestion and Dynamic Next-Session Building

## 3. Why this track exists

The current C2S23 Mireward Command Board proves the interaction model, but it is still too hardcoded in places.

Existing dynamic mechanisms:

- Static Command Board / Live Play page.
- Markdown embeds and previews.
- Read-only corpus indexes for NPCs, locations, roll tables, and statblocks.
- Browser-local combat/toolbox/scratch/timeline state.
- Tiptap local working-board state.
- Safe Markdown prepare/commit flow.

Current pain:

- Planning state lives across handoffs, session notes, dogfood notes, static HTML, localStorage, corpus paths, and generated artifacts.
- Live Play page structure can become busy when runbook, source links, provenance, and launch cards compete.
- Combat defaults and session-specific launch data are embedded in shared JS rather than described as session data.
- C2S23 should become the model for building the next session, not the permanent product shape.

The next architecture needs a session descriptor / ledger.

---

## 4. Three lanes of session data

Do not merge all data into one object.

Keep three lanes distinct:

```txt
Canon/reference data = corpus files and read-only indexes
Runbook data = Markdown/Tiptap documents and descriptors
Operational live state = session-local JSON seeds + mutable browser/current state
```

### Canon/reference data

Examples:

- NPC dossiers.
- Location hubs.
- Statblocks.
- Roll tables.
- Citation/source documents.

This data is resolved behind chips and reference panes. It is not directly edited through the runbook.

### Runbook data

Examples:

- Opening read-aloud.
- Scene beats.
- GM notes.
- Choices and consequences.
- Which references matter now.
- Which tools are relevant now.

This data is authored through Tiptap or Markdown and materialized through safe prep-file writes.

### Operational live state

Examples:

- Combat HP.
- Initiative.
- Clocks.
- Temporary play notes.
- Current tool outputs.

This data is mutable during play and must not be embedded as canon or durable prose by accident.

---

## PR 11 — Session Descriptor Manifest v0

**Branch:** `spike/session-descriptor-manifest-v0`
**Title:** `spike(command-board): describe a session from manifest data`

### Goal

Create a small descriptor that describes a session without hardcoding the Live Play page to one scenario.

### Candidate shape

```ts
type SessionDescriptor = {
  schema_version: "dmb_session_descriptor_v0";
  campaign_id: string;
  session_id: string;
  session_number: number;
  title: string;
  status: "planning" | "ready" | "live" | "complete";
  runbook: {
    document_id: string;
    target_relpath: string;
    theme_id: "command" | "plain" | "statblock";
  };
  source_docs: SessionSourceDoc[];
  reference_scopes: SessionReferenceScope[];
  operational_seeds: {
    combat_seed_relpath?: string;
    clocks_seed_relpath?: string;
  };
  tools: string[];
};
```

### Scope

- Add one descriptor for the current C2S23 model.
- Read/display descriptor metadata in one place.
- Do not generate pages yet.

### Out of scope

- Full session database.
- User-facing descriptor editor.
- Automated next-session generation.

### Manual dogfood

None beyond inspecting the rendered metadata once.

---

## PR 12 — Unified Typed Reference Index v0

**Branch:** `spike/runbook-reference-index-v0`
**Title:** `spike(command-board): expose unified typed reference index`

### Goal

Expose one normalized read-only reference index for chip resolution.

Existing per-domain crawlers can remain internally separate. The frontend and chip resolver should see a common shape.

### Candidate shape

```ts
type ReferenceIndexEntry = {
  type: "npc" | "location" | "statblock" | "roll-table" | "citation";
  id: string;
  label: string;
  source_path: string;
  summary?: string;
  tags?: string[];
  resolver_payload?: unknown;
};
```

### Scope

- Compose existing NPC/location/statblock/roll-table indexes.
- Normalize IDs and labels.
- Return clear diagnostics.
- Keep it read-only.

### Out of scope

- Whole-corpus search.
- Database migration.
- GraphQL.
- Corpus mutation.

### Manual dogfood

None. Unit tests and one resolver integration test are enough.

---

## PR 13 — Session Operational Seeds v0

**Branch:** `spike/session-operational-seeds-v0`
**Title:** `spike(command-board): move live combat defaults into session seeds`

### Goal

Move current hardcoded combat defaults and session-specific operational defaults into session seed files.

### Candidate files

```txt
evals/c2_live_prep/mireward-prep/content/sessions/c2s23/session-seed.json
evals/c2_live_prep/mireward-prep/content/sessions/c2s24/session-seed.json
```

### Key distinction

```txt
Encounter seed = reusable starting configuration
Combat state = mutable live table state
Runbook = prose and contextual references
Corpus = canon/reference truth
```

### Scope

- Extract C2S23 combat defaults into a seed file.
- Load combat defaults from seed.
- Preserve browser-local mutable state once initialized.
- Add a reset/reseed action if needed.

### Out of scope

- Persisting live combat state to corpus.
- Server-backed live combat storage.
- Multi-user combat state.

### Manual dogfood

Small.

Load combat from seed, change HP/initiative, reload, and confirm current live state persists while the seed remains unchanged.

---

## PR 14 — Next-Session Builder Spike

**Branch:** `spike/next-session-builder-from-current-assets`
**Title:** `spike(command-board): generate a next-session draft descriptor from existing prep`

### Goal

Use existing prep, session notes, handoffs, dogfood notes, and reference indexes to create a draft next-session descriptor and starter runbook.

### Inputs

- Current session descriptor.
- Current runbook Markdown.
- Dogfood notes.
- Session notes / handoff docs.
- Reference index.
- Operator-specified next-session premise.

### Outputs

Candidate draft artifacts:

```txt
evals/c2_live_prep/mireward-prep/content/tiptap/c2s24-session-runbook.md
evals/c2_live_prep/mireward-prep/content/sessions/c2s24/session-descriptor.json
evals/c2_live_prep/mireward-prep/content/sessions/c2s24/session-seed.json
```

### Scope

- Generate draft prep artifacts only.
- Use safe allowlisted write boundaries or a similarly explicit draft-write path.
- Preserve clear provenance from input docs.

### Out of scope

- Canon mutation.
- Fully automated session prep.
- Replacing GM review.
- Running live state forward from the prior session.

### Manual dogfood

Yes, once.

Read the generated next-session runbook and answer: “Would I build from this?” This is a creative/product quality checkpoint, not a recurring regression task.

---

## PR 15 — Dynamic Live Play Page from Session Descriptor

**Branch:** `feat/live-play-from-session-descriptor`
**Title:** `feat(command-board): render Live Play from session descriptor`

### Goal

Render the Live Play surface from session descriptor data rather than hardcoded C2S23 page content.

### Scope

A descriptor-driven Live Play page should render:

- Session title and status.
- Runbook Markdown embed.
- Edit link to the descriptor’s Tiptap document.
- Reference resolver scope.
- Combat seed/load controls.
- Relevant NPC/location/statblock/roll-table panes or links.
- Toolbox availability.
- Provenance collapsed by default.

### Out of scope

- Generic dashboard builder.
- Player-facing publishing.
- Replacing all support panes.
- Server-side live state sync.

### Manual dogfood

Yes.

Open the next-session Live Play surface and confirm it feels like a cockpit, not a source index.

---

## 5. Ingestion Model

There are two meanings of ingestion, and they need different handling.

### 5.1 Index ingestion

Index ingestion reads existing files and exposes them as typed references.

Examples:

- NPC index.
- Location index.
- Statblock index.
- Roll-table index.
- Citation/source index.

This is mostly deterministic and testable. It should use allowlisted roots and produce read-only reference records.

### 5.2 Session construction ingestion

Session construction ingestion synthesizes a playable draft from messy planning material.

Inputs may include:

- Prior runbook.
- Prior session notes.
- Handoffs.
- Dogfood notes.
- Corpus indexes.
- Operator premise.
- Open loops.
- Current campaign constraints.

Outputs should be draft prep artifacts:

- Session descriptor.
- Starter runbook Markdown.
- Optional combat/clocks/tool seeds.
- Source/provenance notes.

This should not write canon. It should prepare the next session for GM review.

---

## 6. Desired Next-Session Flow

The target data flow:

```txt
Existing corpus + session notes + handoffs + dogfood notes
        ↓
Reference index + planning ledger
        ↓
Next-session descriptor
        ↓
Starter runbook Markdown / Tiptap draft
        ↓
Optional combat/clocks/tool seeds
        ↓
Static Live Play page renders from descriptor
        ↓
During play, operational state mutates separately
```

The descriptor chooses what matters for a session. It does not become canon.

The runbook projects table-facing sequence and references. It does not own canonical truth.

The chip resolver points back to canon/reference sources. It does not edit them.

The combat tracker mutates live operational state. It does not rewrite prose or corpus.

---

## 7. Manual Dogfood Policy

Manual dogfood is critical when the question is human experience:

- Are chips readable inline?
- Does a popover preserve the reading thread?
- Does the Tiptap authoring loop feel safe?
- Can the GM run from the static page?
- Does the next-session page feel like a cockpit rather than a source index?

Manual dogfood should be minimal or skipped when the question is mechanical:

- Parser behavior.
- Schema validation.
- Link safety.
- Descriptor lookup.
- Reference normalization.
- Pure component extraction.

This keeps dogfood meaningful instead of turning every PR into a manual ritual.

---

## 8. Design Guardrails

Do not jump directly from typed chips to an AI-generated whole-session cockpit.

The stable intermediate artifact is the **session descriptor**.

Do not treat C2S23 live state as future session state.

Use C2S23 as evidence:

- Markdown embeds are useful.
- Dynamic indexes are useful.
- Human labels matter more than internal IDs.
- Nested scroll hurts at table.
- Provenance should be collapsed by default.
- Source links drift and need checking.
- Static Command Board remains a strong at-table product.
- Tiptap is an authoring surface, not canon.

The next session should reuse the machinery, not inherit the old state.

---

## 9. Recommended Sequencing

Near-term:

1. PR 1 — Typed Markdown reference chips.
2. PR 2 — Tiptap inline reference chip spike.
3. PR 3 — Chip popover shell.
4. PR 4 — Reference resolver v1.
5. PR 5 — Tiptap-authored runbook dogfood.

Bridge to Play Mode:

6. PR 6 — Document descriptors.
7. PR 7 — Markdown import.
8. PR 8 — Block save-state badges.
9. PR 9 — Replace one real Markdown surface.
10. PR 10A — Play Mode runbook product direction.
11. PR 10B — Play Mode beat shell.
12. PR 11 — Non-navigating reference overlay shell.
13. PR 12 — Reference overlay resolvers.
14. PR 13 — In-place beat editing spike.
15. PR 14 — Save/commit workflow extraction.
16. PR 15 — Descriptor-backed multi-runbook Play entry.

Next-session infrastructure continues after the Play Mode shell and descriptor-backed entry clarify the product boundary:

17. Session descriptor manifest v0.
18. Unified typed reference index v0.
19. Session operational seeds v0.
20. Next-session builder spike.
21. Dynamic Live Play page from session descriptor.

The important restraint is sequencing. The project becomes powerful by layering small, durable contracts.
