# PLAN — Configurable Markdown Rendering + Tiptap Styling for DungeonBuddy Command Board

**Status:** Draft plan  
**Scope:** DungeonBuddy Command Board Markdown previews, Markdown embeds, future Tiptap editable surfaces, and shared visual theming inspired by Canvas + DungeonMind statblock styling.  
**Primary goal:** Make rendered Markdown and future Tiptap fields styleable from configuration without making the Markdown renderer or Tiptap schema responsible for presentation.

---

## 0. Executive Summary

DungeonBuddy already has a centralized Markdown rendering seam: Markdown text flows through `MirewardMarkdown.render(markdown)` and is inserted into viewer/embed containers as HTML. The correct next step is to add a configurable theme layer around that renderer.

The Markdown renderer should continue to output stable semantic HTML: headings, paragraphs, links, lists, tables, blockquotes, code blocks, and horizontal rules. Styling should be selected by config through a wrapper class, `data-md-theme`, and CSS variables. This keeps the renderer predictable, keeps styling portable, and aligns with the Canvas lesson that structural layout and visual styling must stay separate.

This plan makes the first version easy: apply theme wrappers and CSS variables to Markdown viewer bodies and embedded Markdown blocks. Later phases can add semantic Markdown extensions, Tiptap theme parity, richer DungeonBuddy blocks, and export/print variants.

---

## 1. Product Intent

The system should support three related but distinct rendering modes:

- [ ] **Command Board mode:** dark, operational, fast at-table readability.
- [ ] **DungeonMind Statblock mode:** parchment/PHB-inspired visual treatment for generated monsters, reference material, printable previews, and statblock-adjacent text.
- [ ] **Canvas/export mode:** print-aware, page-aware, layout-safe rendering for handouts or generated documents.

The goal is not to make Markdown become a statblock component system. The goal is to make Markdown previews and future rich-text fields visually coherent with DungeonBuddy surfaces.

---

## 2. Current State

### 2.1 Existing Markdown renderer

- [ ] Markdown is currently rendered by `evals/c2_live_prep/mireward-prep/assets/prep-markdown.js`.
- [ ] It is intentionally lightweight and dependency-free.
- [ ] It strips frontmatter.
- [ ] It escapes raw HTML.
- [ ] It renders:
  - [ ] headings
  - [ ] paragraphs
  - [ ] links
  - [ ] inline code
  - [ ] bold/italic
  - [ ] code fences
  - [ ] tables
  - [ ] blockquotes
  - [ ] ordered and unordered lists
  - [ ] horizontal rules

### 2.2 Existing render call site

- [ ] `prep.js` has a centralized `renderMarkdownHtml(markdownText)` function.
- [ ] If `window.MirewardMarkdown.render` is unavailable, it falls back to escaped `<pre><code>`.
- [ ] Markdown viewer content is inserted into `#md-viewer-body`.
- [ ] `#md-viewer-body` already has classes: `md-viewer-body md-content`.
- [ ] Markdown body links are rewired after render.

### 2.3 Existing CSS base

- [ ] `prep.css` already defines a dark Command Board token set:
  - [ ] `--bg`
  - [ ] `--bg-card`
  - [ ] `--bg-input`
  - [ ] `--fg`
  - [ ] `--fg-mute`
  - [ ] `--fg-dim`
  - [ ] `--border`
  - [ ] `--accent`
  - [ ] `--good`
  - [ ] `--warn`
  - [ ] `--info`
  - [ ] `--mono`
  - [ ] `--radius`

### 2.4 Canvas/statblock styling lessons

- [ ] Canvas separates structural layout from visual styling.
- [ ] Canvas uses strict structural styles where measurement and visible layers must match.
- [ ] DungeonMind statblock export already expresses a usable visual grammar:
  - [ ] parchment/white surfaces
  - [ ] red-brown headings
  - [ ] gold/brown borders
  - [ ] serif fantasy fonts
  - [ ] stat summary cards
  - [ ] ability tables
  - [ ] quickfacts
  - [ ] action/trait sections
  - [ ] print-aware rules

---

## 3. Core Architecture Decision

### Decision

Use a **theme wrapper + CSS variable config** around Markdown output.

Markdown renderer responsibility:

- [ ] Parse Markdown.
- [ ] Escape unsafe text.
- [ ] Output semantic HTML.
- [ ] Add only minimal semantic classes where content meaning demands it.

Theme layer responsibility:

- [ ] Select the visual mode.
- [ ] Apply wrapper class or `data-md-theme`.
- [ ] Apply CSS variables.
- [ ] Style generic Markdown tags.
- [ ] Style known semantic blocks.
- [ ] Avoid altering content meaning.

Application responsibility:

- [ ] Choose a default theme per surface.
- [ ] Allow specific embeds/viewers to override the theme.
- [ ] Keep corpus writes and canon boundaries unchanged.

---

## 4. Non-Goals

- [ ] Do not make the Markdown renderer generate presentation-heavy statblock HTML in phase 1.
- [ ] Do not introduce arbitrary raw HTML rendering.
- [ ] Do not make Markdown previews editable by default.
- [ ] Do not make canon corpus files directly editable through the preview modal.
- [ ] Do not merge combat tracker operational state into Markdown/Tiptap.
- [ ] Do not require Tiptap to ship before themed Markdown rendering.
- [ ] Do not make Canvas structural/page measurement rules depend on Command Board CSS.
- [ ] Do not import the entire Canvas export stylesheet into the Command Board blindly.

---

## 5. Theme Model

### 5.1 Theme registry

Create a small theme registry in a new file:

`evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.js`

Proposed shape:

```js
window.MirewardMarkdownThemes = {
  defaultThemeId: "command",
  themes: {
    command: {
      label: "Command Board",
      className: "md-theme-command",
      variables: {
        "--md-bg": "var(--bg-card)",
        "--md-surface": "var(--bg-input)",
        "--md-fg": "var(--fg)",
        "--md-muted": "var(--fg-mute)",
        "--md-border": "var(--border)",
        "--md-accent": "var(--accent)",
        "--md-heading": "var(--fg)"
      }
    },
    statblock: {
      label: "DungeonMind Statblock",
      className: "md-theme-statblock",
      variables: {
        "--md-bg": "#f7ebd7",
        "--md-surface": "rgba(255, 249, 237, 0.85)",
        "--md-fg": "#2b1d0f",
        "--md-muted": "rgba(43, 29, 15, 0.72)",
        "--md-border": "#c0ad6a",
        "--md-accent": "#a11d18",
        "--md-heading": "#58180d"
      }
    },
    plain: {
      label: "Plain Reference",
      className: "md-theme-plain",
      variables: {}
    }
  }
};
```

Checklist:

- [ ] Add theme registry file.
- [ ] Load it after `prep-markdown.js` and before `prep.js`, or make `prep.js` tolerate missing registry.
- [ ] Add `getMarkdownTheme(themeId)` helper.
- [ ] Add `applyMarkdownTheme(element, themeId)` helper.
- [ ] Ensure missing theme falls back to `command`.

### 5.2 Theme selector fields

Support these theme inputs:

- [ ] `viewerMeta.theme`
- [ ] `data-md-theme` on markdown embed host
- [ ] default page-level theme
- [ ] future user config / campaign config

Priority order:

1. Explicit call-site theme.
2. Element `data-md-theme`.
3. Page default.
4. Registry default.
5. Hardcoded `command`.

---

## 6. Phase 1 — Theme Wrapper for Markdown Viewer

### Goal

Make the existing Markdown modal styleable by config without changing renderer output.

### Implementation

Modify `setMarkdownViewerState(kind, repoRelative, message, viewerMeta)`:

- [x] Read `viewerMeta.theme`.
- [x] Get `#md-viewer-body`.
- [x] Clear previous theme classes and inline `--md-*` variables.
- [x] Apply chosen theme class.
- [x] Apply theme variables with `style.setProperty`.
- [x] Add `data-md-theme="<themeId>"`.
- [x] Render existing HTML exactly as before.
- [x] Keep `wireMarkdownBodyLinks(body, repoRelative)` unchanged.

Suggested helper:

```js
function applyMarkdownTheme(el, themeId) {
  const registry = window.MirewardMarkdownThemes || {};
  const themes = registry.themes || {};
  const id = themes[themeId] ? themeId : registry.defaultThemeId || "command";
  const theme = themes[id] || themes.command;

  if (!el || !theme) return id;

  Array.from(el.classList)
    .filter((c) => c.startsWith("md-theme-"))
    .forEach((c) => el.classList.remove(c));

  el.classList.add(theme.className || "md-theme-command");
  el.setAttribute("data-md-theme", id);

  Object.keys(el.style)
    .filter((key) => key.startsWith("--md-"))
    .forEach((key) => el.style.removeProperty(key));

  Object.entries(theme.variables || {}).forEach(([name, value]) => {
    el.style.setProperty(name, value);
  });

  return id;
}
```

Acceptance checks:

- [ ] Existing Markdown preview still opens.
- [ ] Existing generated statblock preview still opens.
- [ ] Markdown links still route through existing preview wiring.
- [ ] `viewerMeta.theme = "statblock"` visibly changes the viewer body.
- [ ] Missing theme gracefully falls back.
- [ ] No raw HTML execution is introduced.
- [ ] No corpus write behavior changes.

---

## 7. Phase 2 — Theme Wrapper for Markdown Embeds

### Goal

Make inline `data-md-embed` blocks use the same theme system.

### Implementation

In `initMarkdownEmbeds` / render path:

- [ ] Read `data-md-theme` from embed element.
- [ ] Apply theme to the rendered `.md-embed` or contained `.md-content`.
- [ ] Keep lazy loading behavior unchanged.
- [ ] Preserve current file:// guard.
- [ ] Preserve existing line-range embed behavior.

Example HTML:

```html
<div
  class="md-embed"
  data-md-embed="Corpus/Statblocks/Mireward/splintered-wretch.md"
  data-md-theme="statblock"
></div>
```

Acceptance checks:

- [ ] Existing embeds still render without adding `data-md-theme`.
- [ ] A statblock-themed embed can sit inside a dark Command Board page.
- [ ] Themed embed does not break fold/accordion scroll behavior.
- [ ] Themed embed tables remain readable.
- [ ] Links inside themed embed still route correctly.

---

## 8. Phase 3 — Base Markdown Theme CSS

### Goal

Create clean, reusable CSS for generic Markdown output.

### File

Add or extend:

`evals/c2_live_prep/mireward-prep/assets/prep-markdown-themes.css`

### Base rules

```css
.md-content {
  color: var(--md-fg, var(--fg));
}

.md-content h1,
.md-content h2,
.md-content h3,
.md-content h4 {
  color: var(--md-heading, var(--md-fg, var(--fg)));
}

.md-content a {
  color: var(--md-accent, var(--accent));
}

.md-content table {
  width: 100%;
  border-collapse: collapse;
  margin: 0.75rem 0;
}

.md-content th,
.md-content td {
  border: 1px solid var(--md-border, var(--border));
  padding: 0.4rem 0.55rem;
  vertical-align: top;
}

.md-content blockquote {
  margin: 0.75rem 0;
  padding: 0.6rem 0.85rem;
  border-left: 4px solid var(--md-accent, var(--accent));
  background: var(--md-surface, var(--bg-input));
}
```

Checklist:

- [ ] Add base `.md-content` rules.
- [ ] Add table rules.
- [ ] Add code/pre rules.
- [ ] Add blockquote rules.
- [ ] Add list spacing rules.
- [ ] Add heading spacing rules.
- [ ] Add print-safe defaults.
- [ ] Verify no global `h1/h2/table` rules leak outside `.md-content`.

---

## 9. Phase 4 — Command Theme CSS

### Goal

Keep rendered Markdown visually native inside the current Command Board.

Checklist:

- [ ] `.md-theme-command` uses current dark CSS tokens.
- [ ] Headings are compact.
- [ ] Tables match current panel/card treatment.
- [ ] Code blocks use `--mono`.
- [ ] Blockquotes use callout-like dark styling.
- [ ] Links stay blue/accent.
- [ ] Works inside modal.
- [ ] Works inside `details.fold`.
- [ ] Works in toolbox drawer if used there later.

Acceptance checks:

- [ ] Existing operational pages still look unchanged outside Markdown.
- [ ] Markdown preview does not look like pasted GitHub markdown.
- [ ] Table-heavy corpus pages are more readable.
- [ ] Long markdown previews remain scrollable and responsive.

---

## 10. Phase 5 — Statblock Theme CSS

### Goal

Create a parchment/PHB-inspired Markdown theme using the DungeonMind statblock visual grammar.

Checklist:

- [ ] `.md-theme-statblock` sets parchment background.
- [ ] Body text uses a serif/fallback stack.
- [ ] Headings use red-brown styling.
- [ ] `h1` resembles monster/title name styling.
- [ ] `h2/h3` resemble section headings.
- [ ] Tables resemble ability/quickfact tables.
- [ ] Blockquotes become read-aloud or lore boxes.
- [ ] Horizontal rules use gold/brown divider.
- [ ] Code remains readable but does not dominate.
- [ ] Theme works even if custom fonts are not available.

Example:

```css
.md-content.md-theme-statblock {
  background: var(--md-bg);
  color: var(--md-fg);
  border: 1px solid var(--md-border);
  border-radius: 8px;
  padding: 16px;
  font-family: "Bookinsanity", "Book Antiqua", Georgia, serif;
}

.md-content.md-theme-statblock h1 {
  color: var(--md-heading);
  font-size: 2rem;
  line-height: 1.1;
  margin: 0 0 0.4rem;
}

.md-content.md-theme-statblock h2 {
  color: var(--md-accent);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid rgba(88, 24, 13, 0.25);
}
```

Acceptance checks:

- [ ] Generated statblock markdown preview can use statblock theme.
- [ ] Normal prose markdown still looks good in statblock theme.
- [ ] Statblock theme does not require Canvas runtime.
- [ ] Statblock theme does not alter operational Command Board layout.
- [ ] Print preview is acceptable.

---

## 11. Phase 6 — Theme Config Storage

### Goal

Make theme choices configurable per surface and eventually per campaign/session.

Initial options:

- [ ] Hardcoded theme per call site.
- [ ] `data-md-theme` in HTML.
- [ ] Page default constant in page script.
- [ ] LocalStorage override for dogfooding.

Later options:

- [ ] `theme_config.json` under prep assets.
- [ ] FastAPI endpoint for available render themes.
- [ ] Campaign-level config.
- [ ] User-level preference.
- [ ] Theme picker UI.

Suggested simple config file later:

```json
{
  "defaultTheme": "command",
  "surfaces": {
    "live-notes": "command",
    "statblock-preview": "statblock",
    "roll-table-preview": "command",
    "print-preview": "statblock"
  }
}
```

Acceptance checks:

- [ ] Theme choice can be changed without editing renderer code.
- [ ] Theme config does not affect corpus content.
- [ ] Missing config does not break the Command Board.
- [ ] Invalid theme id produces visible fallback, not failure.

---

## 12. Phase 7 — Semantic Markdown Extensions

### Goal

Add DungeonBuddy-specific semantic blocks only after wrapper theming is proven.

Candidate syntax:

```md
> [!warning]
> Refugees panic if the flank reaches the gate.
```

```md
:::callout warn
The north gate opens only when Lysandra gives the signal.
:::
```

```md
:::read-aloud
The reeds bow outward as something huge exhales beneath the road.
:::
```

```md
:::gm-note
Use this only if the party stalls.
:::
```

Candidate rendered classes:

- [ ] `.dm-callout`
- [ ] `.dm-callout-warn`
- [ ] `.dm-callout-info`
- [ ] `.dm-read-aloud`
- [ ] `.dm-gm-note`
- [ ] `.dm-rules-note`
- [ ] `.dm-threat-clock`
- [ ] `.dm-statblock-section`

Implementation notes:

- [ ] Keep raw HTML disabled.
- [ ] Parse semantic blocks before paragraph rendering.
- [ ] Escape inner text.
- [ ] Add tests for malformed blocks.
- [ ] Add parity mapping for future Tiptap nodes.

Acceptance checks:

- [ ] Existing Markdown still renders the same.
- [ ] New callout syntax renders safely.
- [ ] Unknown directives render as plain text or safe fallback.
- [ ] The same semantic class can be styled by command/statblock themes differently.
- [ ] Exported Markdown remains human-readable.

---

## 13. Phase 8 — Tiptap Parity

### Goal

Ensure future Tiptap editable fields render with the same visual language as Markdown previews.

Tiptap should use:

- [ ] Same theme ids.
- [ ] Same CSS variables.
- [ ] Same semantic classes.
- [ ] Same save-target badges.
- [ ] Same visual distinction between draft, canon reference, and operational widget.

Tiptap nodes to align:

- [ ] `callout`
- [ ] `gmNote`
- [ ] `sceneBeat`
- [ ] `npcRef`
- [ ] `locationRef`
- [ ] `statblockRef`
- [ ] `rollTableRef`
- [ ] `corpusMarkdownEmbed`
- [ ] `combatWidgetRef`

Rules:

- [ ] Tiptap JSON remains working board state.
- [ ] Markdown remains corpus/export format.
- [ ] Operational state remains operational JSON.
- [ ] Canon writes still go through preview/confirm writer flow.

Acceptance checks:

- [ ] Markdown preview and Tiptap editor share visual theme.
- [ ] Tiptap read-only mode can look like Markdown preview.
- [ ] Editing chrome is visually distinct from rendered content.
- [ ] Save target is visible.
- [ ] Export selected Tiptap range to Markdown remains possible.

---

## 14. Phase 9 — Testing Plan

### Unit tests

- [ ] Markdown renderer escapes HTML.
- [ ] Markdown renderer still renders headings/lists/tables/code.
- [ ] Theme resolution falls back correctly.
- [ ] `applyMarkdownTheme` removes old theme classes.
- [ ] `applyMarkdownTheme` applies CSS variables.
- [ ] Invalid theme id does not throw.
- [ ] Semantic extension parser escapes inner content.

### Browser/manual tests

- [ ] Open markdown modal in command theme.
- [ ] Open markdown modal in statblock theme.
- [ ] Open generated statblock preview in statblock theme.
- [ ] Open inline embed in command theme.
- [ ] Open inline embed in statblock theme.
- [ ] Open markdown links inside themed content.
- [ ] Test long markdown file scroll.
- [ ] Test table-heavy markdown file.
- [ ] Test file:// guard still works.
- [ ] Test mobile width.

### Regression tests

- [ ] Existing Command Board nav unchanged.
- [ ] Existing toolbox drawer unchanged.
- [ ] Existing corpus write preview unchanged.
- [ ] Existing combat tracker unchanged.
- [ ] Existing dynamic index rendering unchanged.

---

## 15. Migration Plan

### Step A — Add theme infrastructure

- [ ] Add `prep-markdown-themes.js`.
- [ ] Add `prep-markdown-themes.css`.
- [x] Load both on pages that use Markdown viewer/embed.
- [x] Add helper functions to `prep.js`.

### Step B — Wire modal viewer

- [x] Accept `viewerMeta.theme`.
- [x] Apply theme to `#md-viewer-body`.
- [x] Use command theme by default.
- [x] Use statblock theme for generated statblock preview.

### Step C — Wire embeds

- [ ] Support `data-md-theme`.
- [ ] Apply command default.
- [ ] Dogfood a statblock-themed embed.

### Step D — Improve generic markdown CSS

- [ ] Tune table spacing.
- [ ] Tune heading hierarchy.
- [ ] Tune blockquote/callout look.
- [ ] Tune pre/code wrapping.
- [ ] Verify scroll behavior.

### Step E — Add semantic blocks

- [ ] Add warning/info/read-aloud/gm-note syntax.
- [ ] Add CSS for each theme.
- [ ] Add fixtures.
- [ ] Add tests.

### Step F — Tiptap bridge

- [ ] Create shared theme ids.
- [ ] Apply same classes to Tiptap editor root.
- [ ] Map Tiptap callout nodes to same classes.
- [ ] Export semantic nodes to Markdown syntax.

---

## 16. Recommended First Slice

The first implementation slice should be intentionally narrow:

- [ ] Add theme registry.
- [ ] Add `applyMarkdownTheme`.
- [ ] Add command and statblock CSS themes.
- [ ] Apply command theme to default markdown viewer.
- [ ] Apply statblock theme to generated statblock previews.
- [ ] Support `data-md-theme` on embeds.
- [ ] Do not alter Markdown parser behavior yet.
- [ ] Do not add Tiptap yet.
- [ ] Do not change corpus write flow.

Success criteria:

- [ ] Markdown previews look intentionally styled rather than generic.
- [ ] Generated statblock previews visually connect to DungeonMind statblock/Canvas output.
- [ ] No existing Command Board functionality regresses.
- [ ] The styling layer is clearly config-driven.
- [ ] The renderer remains stable and semantic.

---

## 17. Risks and Mitigations

### Risk: Renderer becomes presentation-specific

Mitigation:

- [ ] Keep phase 1 renderer output unchanged.
- [ ] Put visual decisions in CSS themes.
- [ ] Only add semantic classes when there is real content meaning.

### Risk: CSS leaks into Command Board chrome

Mitigation:

- [ ] Scope all rules under `.md-content`.
- [ ] Use `data-md-theme` and `.md-theme-*`.
- [ ] Avoid global tag selectors.

### Risk: Statblock theme implies full statblock correctness

Mitigation:

- [ ] Treat statblock theme as presentation for Markdown previews.
- [ ] Keep mechanical statblock rendering separate.
- [ ] Use dedicated statblock components for structured mechanics later.

### Risk: Canvas styles imported too broadly

Mitigation:

- [ ] Reuse visual tokens and lessons, not the whole runtime stylesheet.
- [ ] Keep Canvas structural layout separate.
- [ ] Do not let markdown themes control page measurement.

### Risk: Theme config becomes too complex

Mitigation:

- [ ] Start with three themes.
- [ ] Allow missing/invalid themes to fall back.
- [ ] Avoid user-facing picker until dogfood proves value.

---

## 18. Open Decisions

- [ ] Should the default theme be global `command`, with statblock only opt-in?
- [ ] Should generated statblock preview always use `statblock`, or should it remember last selected?
- [ ] Should inline embeds inherit page theme or always default command?
- [ ] Should theme config live in JS first or JSON first?
- [ ] Should semantic Markdown extensions use Obsidian-style callouts, container directives, or both?
- [ ] Should print/export styles live in a third theme or as media rules on `statblock`?
- [ ] Should Tiptap expose a theme selector per document, per block, or per surface only?

---

## 19. Definition of Done for v1

- [ ] `command`, `statblock`, and `plain` themes exist.
- [ ] Markdown modal accepts and applies theme config.
- [ ] Markdown embeds accept and apply theme config.
- [ ] Generated statblock preview uses statblock theme.
- [ ] Existing Markdown links continue to work.
- [ ] Existing corpus write preview still works.
- [ ] Existing dynamic indexes still work.
- [ ] No raw HTML rendering added.
- [ ] CSS is scoped under `.md-content`.
- [ ] Plan doc updated with completed checkboxes.

---

## 20. Future Expansion

Once v1 is proven:

- [ ] Add semantic callout parser.
- [ ] Add read-aloud box syntax.
- [ ] Add GM-only note syntax.
- [ ] Add Tiptap editor root theming.
- [ ] Add Tiptap semantic node parity.
- [ ] Add Markdown export from Tiptap with semantic syntax.
- [ ] Add theme config endpoint.
- [ ] Add screenshot/visual regression fixtures.
- [ ] Add print preview mode.
- [ ] Add page/handout rendering mode using Canvas compatibility rules.
