# HANDOFF — Typed Runbook Reference Chips

**Created:** 2026-06-18  
**Repo:** `Drakosfire/DungeonMindBuddy`  
**Target branch:** `feat/runbook-reference-chips`  
**Target PR title:** `feat(command-board): add typed runbook reference chips`  
**Status:** Ready for coding agent  
**Mode:** Small implementation slice. Keep scope tight.

---

## 0. Mission

Implement typed Markdown reference chips for the Command Board Markdown renderer.

A Markdown runbook should be able to contain readable fallback links like:

```md
[Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)
[North Reach Gate](#dmb-ref:location:north-reach-gate)
[Sewer Meat Creature](#dmb-ref:statblock:sewer-meat-creature)
[Gate Dilemma d12](#dmb-ref:roll-table:gate-dilemma-d12)
[Session 22 ending](#dmb-ref:citation:c2s22-ending)
[North Gate Combat](#dmb-action:combat:north-gate-combat)
```

When rendered in the existing Command Board Markdown renderer, valid typed references should become inert inline chips with semantic classes and data attributes. The chips should make the runbook feel like a script with live hyperlinks, while still preserving plain Markdown readability.

This PR is **only** the renderer/chip contract. Do not build the resolver, popover, Tiptap chip node, combat launch, roll UI, or document manager in this slice.

---

## 1. Grounding / Why this matters

The product direction is captured in the runbook design docs:

- The session runbook is the table-facing projection of prep, not the prep database itself.
- The runbook reads like a linear script and behaves like a command surface.
- Important nouns and procedures become typed references.
- Canon/reference data, runbook prose, and operational state remain separate.

Relevant design anchors:

- `Docs/Plans/DESIGN-session-runbook-command-surface.md`
- `Docs/Design/DESIGN-runbook-roadmap-and-session-ingestion.md`
- `Docs/Plans/PLAN-configurable-markdown-rendering-and-tiptap-styling.md`
- `Docs/Design/DESIGN-mireward-command-board-shell.md`
- `Docs/Plans/C2S23-MIREWARD-DOGFOOD-NOTES.md`

Read at least the following sections before coding:

1. `Docs/Plans/DESIGN-session-runbook-command-surface.md`
   - §0 North Star
   - §2 Product Distinction
   - §5 Typed Reference Model
   - §7 Visual Language
   - §12 PR 1 — Typed Markdown Reference Chips
   - §14 Design Guardrails
2. `Docs/Design/DESIGN-runbook-roadmap-and-session-ingestion.md`
   - §0 Purpose
   - §1 Core Product Boundary
   - Track A / PR 1
   - §7 Manual Dogfood Policy
   - §8 Design Guardrails
3. `Docs/Plans/PLAN-configurable-markdown-rendering-and-tiptap-styling.md`
   - §3 Core Architecture Decision
   - renderer outputs semantic HTML; theme layer owns presentation.

Important product guardrails:

- Do not let the runbook become a dashboard.
- Do not let Tiptap become canon by accident.
- Do not hide write boundaries.
- Do not put combat HP or live clocks in prose.
- Do not build a generic CMS before proving one playable runbook loop.

---

## 2. Current repo state to understand

### PR 134 is already merged

`feat(command-board): add Tiptap Markdown file write prepare and commit` is merged into `main`.

That means the browser-local Tiptap working-board state and backend Markdown prepare/commit boundary already exist. Do not reimplement them.

### Renderer seam

The static Markdown renderer is here:

```txt
evals/c2_live_prep/mireward-prep/assets/prep-markdown.js
```

It is intentionally lightweight and dependency-free. The key seam is `inlineMarkdown(text)`, which currently:

1. Escapes HTML.
2. Converts inline code.
3. Converts Markdown links to `<a href="..." data-md-link="1">...</a>`.
4. Converts bold/italic.

This is the right place to add typed chip detection.

### Theme seam

Markdown visual styling lives here:

```txt
evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css
```

Renderer output should remain semantic. CSS should own the look.

### Tests

Focused renderer tests live here:

```txt
apps/live-control-ui/src/test/prepMarkdownRenderer.test.ts
```

The tests load `prep-markdown.js` through Node `vm`, render into a DOM host, and assert HTML structure. Extend this test file.

### Fixture page

Visual fixture material lives here:

```txt
evals/c2_live_prep/mireward-prep/fixtures/markdown-theme-sample.md
evals/c2_live_prep/mireward-prep/markdown-theme-fixtures.html
```

The HTML fixture page already renders the shared Markdown sample across command/statblock/plain themes. Add chip examples to the Markdown sample rather than creating a new page unless there is a strong reason.

---

## 3. Desired syntax and parser contract

Recognize two typed href forms:

```txt
#dmb-ref:<type>:<id>
#dmb-action:<type>:<id>
```

Initial supported `#dmb-ref` types for this PR:

```txt
npc
location
statblock
roll-table
citation
```

`#dmb-action` should support at least:

```txt
combat
```

The broader design uses `action` as a conceptual type, but the Markdown syntax for live actions is `#dmb-action:<action-type>:<action-id>`. Do not require action hrefs to be written as `#dmb-ref:action:*` in this PR.

Recommended parser helper in `prep-markdown.js`:

```js
const DMB_REF_TYPES = new Set([
  "npc",
  "location",
  "statblock",
  "roll-table",
  "citation",
]);

const DMB_ACTION_TYPES = new Set([
  "combat",
]);

function parseDmbTypedHref(href) {
  const raw = String(href || "").trim();

  const refMatch = raw.match(/^#dmb-ref:([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_-]*)$/);
  if (refMatch) {
    const type = refMatch[1];
    const id = refMatch[2];
    if (!DMB_REF_TYPES.has(type)) return null;
    return { kind: "ref", type: type, id: id };
  }

  const actionMatch = raw.match(/^#dmb-action:([a-z][a-z0-9-]*):([a-z0-9][a-z0-9_-]*)$/);
  if (actionMatch) {
    const type = actionMatch[1];
    const id = actionMatch[2];
    if (!DMB_ACTION_TYPES.has(type)) return null;
    return { kind: "action", type: type, id: id };
  }

  return null;
}
```

ID rules for this PR:

- Lowercase alphanumeric start.
- Then lowercase alphanumeric, underscore, or hyphen.
- No spaces.
- No slashes.
- No dots.
- No URL decoding.
- No arbitrary protocols.

Reason: make the enhancement contract stable and safe before resolver work.

---

## 4. Renderer output contract

### Valid `#dmb-ref`

Input:

```md
[Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil)
```

Output should be equivalent to:

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

### Valid `#dmb-action`

Input:

```md
[North Gate Combat](#dmb-action:combat:north-gate-combat)
```

Output should be equivalent to:

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

### Ordinary Markdown links

Ordinary links must preserve the existing contract:

```html
<a href="..." data-md-link="1">Label</a>
```

This matters because `prep.js` rewires `a[data-md-link]` into Markdown previews / repo links. Chips should not be `a[data-md-link]` and should not navigate.

### Invalid typed refs

Malformed or unsupported typed refs should not become chips.

Acceptable fallback for this PR: render as the normal escaped link using the existing link contract.

Examples that should **not** become chips:

```md
[Bad](#dmb-ref:npc:)
[Bad](#dmb-ref:npc:bad/id)
[Bad](#dmb-ref:npc:BadId)
[Bad](#dmb-ref:unknown:thing)
[Bad](#dmb-action:unknown:thing)
```

Do not silently drop text.

---

## 5. Security and escaping requirements

The renderer already escapes raw HTML before inline transforms. Preserve that safety.

Required behavior:

- Link/chip labels are escaped.
- Raw HTML in labels does not execute.
- No `<script>` appears from input text.
- Valid chips are inert `<button type="button">` elements.
- Unknown/malformed typed refs fall back safely.
- Ordinary links still behave as ordinary links.
- Do not introduce arbitrary raw HTML support.
- Do not treat unsafe protocols as commands.

Specific regression to test:

```md
[<img src=x onerror=alert(1)>](#dmb-ref:npc:bad-label)
```

Expected:

- No `img` element in the output DOM.
- Button text content equals the literal label text.
- No executable handler.

---

## 6. CSS expectations

Add chip styles to:

```txt
evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css
```

Candidate classes:

```txt
.md-ref-chip
.md-ref-chip-npc
.md-ref-chip-location
.md-ref-chip-statblock
.md-ref-chip-roll-table
.md-ref-chip-citation
.md-ref-chip-action
.md-ref-chip-action-combat
```

Visual intent:

- Chips are enriched inline links, not badges that dominate prose.
- They should work in command, statblock, and plain themes.
- They should remain readable in a paragraph, list item, table cell, heading, and callout body.
- They should be keyboard-focusable and have a visible focus style.
- They should not introduce layout jumps.

Suggested semantic colors:

```txt
NPCs              warm/person
Locations         cool/place
Statblocks        danger/threat
Roll tables       utility/procedure
Citations         muted/source
Live actions      strong/action
```

Implementation suggestion:

Use a shared `.md-ref-chip` base and type-specific CSS variables. Example style shape:

```css
.md-content[data-md-theme] .md-ref-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  margin: 0 0.05rem;
  padding: 0.08rem 0.42rem;
  border: 1px solid var(--md-ref-chip-border, var(--md-border, var(--border)));
  border-radius: 999px;
  color: var(--md-ref-chip-fg, var(--md-accent, var(--accent)));
  background: var(--md-ref-chip-bg, transparent);
  font: inherit;
  font-weight: 650;
  line-height: 1.45;
  cursor: default;
}
```

Avoid over-polishing. This PR only needs a clear type signal.

---

## 7. Fixture / dogfood content

Update:

```txt
evals/c2_live_prep/mireward-prep/fixtures/markdown-theme-sample.md
```

Add a section like:

```md
## Typed Reference Chip Fixtures

If the players push toward the refugees, use [Gate Dilemma d12](#dmb-ref:roll-table:gate-dilemma-d12).

If combat starts, launch [North Gate Combat](#dmb-action:combat:north-gate-combat).

Active threats: [Sewer Meat Creature](#dmb-ref:statblock:sewer-meat-creature), [Aberrant Meatwing](#dmb-ref:statblock:aberrant-meatwing), [Corrupted Meat Golem](#dmb-ref:statblock:corrupted-meat-golem).

Key people: [Lysandro Ironveil](#dmb-ref:npc:lysandro-ironveil), [Brin Holloway](#dmb-ref:npc:brin-holloway), [Captain Lysandra Ironveil](#dmb-ref:npc:captain-lysandra-ironveil).

Location context: [North Reach Gate](#dmb-ref:location:north-reach-gate), [Mireward Wall](#dmb-ref:location:mireward-wall).

Source: [Session 22 ending](#dmb-ref:citation:c2s22-ending).
```

This is enough for visual review on `markdown-theme-fixtures.html`, which already renders the shared sample through the existing embed path.

Do not add a new fixture page unless necessary.

---

## 8. Tests to add

Extend:

```txt
apps/live-control-ui/src/test/prepMarkdownRenderer.test.ts
```

Add tests that assert:

1. NPC refs render as chips.
2. Location refs render as chips.
3. Statblock refs render as chips.
4. Roll-table refs render as chips.
5. Citation refs render as chips.
6. Combat action refs render as action chips.
7. Chips expose:
   - `data-md-ref-kind`
   - `data-md-ref-type`
   - `data-md-ref-id`
8. Chips are `<button type="button">`.
9. Chip labels are escaped.
10. Malformed typed refs do not become chips.
11. Unknown typed refs do not become chips.
12. Ordinary links still render as `a[data-md-link="1"]`.
13. Unsafe/raw HTML still does not execute or become DOM elements.
14. Typed refs inside callout bodies render correctly.
15. Typed refs inside tables render correctly if cheap to add.

Tests should not depend on exact whitespace in output HTML. Query the DOM.

Useful test helper pattern already exists:

```ts
const host = renderHost("See [Plan](../../Docs/Plans/example.md).");
const link = host.querySelector("a");
```

Use DOM queries like:

```ts
const chip = host.querySelector(".md-ref-chip-npc");
expect(chip?.tagName.toLowerCase()).toBe("button");
expect(chip?.getAttribute("type")).toBe("button");
expect(chip?.getAttribute("data-md-ref-kind")).toBe("ref");
expect(chip?.getAttribute("data-md-ref-type")).toBe("npc");
expect(chip?.getAttribute("data-md-ref-id")).toBe("lysandro-ironveil");
expect(chip?.textContent).toBe("Lysandro Ironveil");
```

---

## 9. Validation commands

Run focused frontend tests:

```bash
cd apps/live-control-ui
npm run test -- src/test/prepMarkdownRenderer.test.ts
```

Also run a whitespace check from repo root if available in the environment:

```bash
git diff --check
```

Optional visual dogfood:

```bash
cd apps/live-control-ui
npm run dev
```

Then open the fixture page through the local dev server and inspect:

```txt
/evals/c2_live_prep/mireward-prep/markdown-theme-fixtures.html
```

If the dev server path differs in local setup, use the existing Command Board route convention from prior slices. Do not spend the PR adding a launch helper.

---

## 10. Acceptance criteria

This PR is complete when:

- Valid `#dmb-ref:<type>:<id>` links render as `.md-ref-chip` buttons.
- Valid `#dmb-action:combat:<id>` links render as action chip buttons.
- Supported ref types have distinct semantic classes.
- Ref kind/type/id are available as data attributes.
- Ordinary links still render and rewire as before.
- Malformed typed refs fall back safely.
- Label escaping remains safe.
- Renderer tests cover valid, malformed, ordinary, and unsafe cases.
- The visual fixture demonstrates each major chip type.
- No resolver/popover/API lookup/Tiptap node/combat launch is added.

---

## 11. Out of scope / do not do

Do **not** implement:

- Tiptap inline chip nodes.
- Tiptap chip insertion UI.
- Chip popovers.
- Reference resolver API.
- NPC/location/statblock cards.
- Roll-table UI.
- Combat launch.
- Markdown import.
- Session descriptor manifest.
- Backend persistence changes.
- Corpus writes.
- A generic component library.
- A dashboard redesign.

This PR should be easy to review because it changes one renderer seam, one CSS file, one fixture, and one test file.

---

## 12. Common pitfalls

### Pitfall: Turning malformed typed links into broken chips

If type/id parsing fails, use the old normal-link path. Do not create half-valid chips.

### Pitfall: Accidentally breaking ordinary links

The existing `a[data-md-link="1"]` contract matters. `prep.js` uses it to rewire Markdown preview links and repo-relative links.

### Pitfall: Over-styling chips

Chips should be recognizable, not loud. They live inside prose.

### Pitfall: Building PR 3 early

Do not add click handlers or popovers. Button chips are intentionally inert in PR 1.

### Pitfall: Adding backend awareness

Do not resolve IDs. The chip is only a semantic doorway in this PR.

### Pitfall: Unsafe HTML regression

The renderer is dependency-free and safety-sensitive. Preserve escape-first behavior.

---

## 13. Suggested implementation order

1. Add `DMB_REF_TYPES`, `DMB_ACTION_TYPES`, and `parseDmbTypedHref()` in `prep-markdown.js` near `inlineMarkdown()`.
2. Add a small `renderDmbRefChip(label, parsed)` helper that uses `escapeHtml()` on label/type/id-derived output.
3. Modify the Markdown link replacement in `inlineMarkdown()`:
   - parse href.
   - if valid typed ref/action, return chip HTML.
   - otherwise return existing `<a data-md-link="1">` HTML.
4. Add renderer tests for valid chips and safety/fallback behavior.
5. Add chip CSS to `prep-markdown-themes.css`.
6. Add fixture section to `markdown-theme-sample.md`.
7. Run focused tests.
8. Inspect visual fixture if possible.
9. Keep commit scoped.

---

## 14. Expected final file list

Likely changed files:

```txt
evals/c2_live_prep/mireward-prep/assets/prep-markdown.js
evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css
evals/c2_live_prep/mireward-prep/fixtures/markdown-theme-sample.md
apps/live-control-ui/src/test/prepMarkdownRenderer.test.ts
```

No backend files expected.

No Tiptap extension files expected.

No corpus files expected.

---

## 15. PR summary template

Use something close to this in the PR body:

```md
### Motivation

Typed runbook reference chips are the smallest step from static Markdown previews toward a table-facing command surface. They keep Markdown readable while giving Command Board a stable semantic contract for future popovers and resolver work.

### Description

- Detect valid `#dmb-ref:<type>:<id>` and `#dmb-action:combat:<id>` Markdown links in the lightweight renderer.
- Render valid typed refs as inert inline chip buttons with semantic classes and `data-md-ref-*` attributes.
- Preserve ordinary Markdown link behavior and safe fallback for malformed refs.
- Add chip styling across Markdown themes and update the visual fixture sample.
- Extend renderer tests for valid chips, malformed refs, ordinary links, and escaping safety.

### Testing

- `cd apps/live-control-ui && npm run test -- src/test/prepMarkdownRenderer.test.ts`
- `git diff --check`
```

---

## 16. End-state after this PR

After this PR, the Command Board can render a Markdown runbook that still reads naturally in raw form but displays type-colored inline chips in the browser.

This unlocks the next slices:

1. Tiptap inline reference chip spike.
2. Reference chip popover shell.
3. API-backed resolver v1.
4. Tiptap-authored runbook dogfood.

Do not pull those future slices into this PR.
