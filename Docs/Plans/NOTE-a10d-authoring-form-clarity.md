# NOTE — A10d Authoring Form Clarity (Visibility + Relationship Guidance)

> Historical implementation note. Current authoring behavior and deferred work are summarized in `Docs/Reports/SPIKE-CLOSEOUT-graph-review-authored-memory-2026-07.md`.

**Date:** 2026-07-07  
**PR anchor:** A10d / PR 289  
**Depends on:** A10b (alias prose grounding), A10c (node detail hierarchy)

## A10a findings addressed

- **Story 6 — Visibility feels safe (PARTIAL):** `table_known` and `player_visible` were merged into one dropdown option (“Table known / player visible”), which obscured who could safely know authored memory.
- **Story 3 — Stage a relationship useful at the table (PARTIAL):** Relationship type select showed raw predicate strings (`has_member`, `same_as` placeholder) without campaign-language coaching, leading to identity-merge mistakes instead of useful campaign facts.

## Changes

### Visibility option split

- `GRAPH_OBJECT_AUTHORING_VISIBILITY_OPTIONS` now lists five distinct choices: GM private, Table known, Player visible, Character-specific, Hidden until revealed.
- Each option carries a short note explaining the audience promise.
- `gm_private` remains the default for object, link-existing, and relationship forms.
- Staging tray and `friendlyVisibilityLabel()` render friendly labels instead of raw enum strings.

### Relationship guidance / coaching

- Relationship type select shows human-facing labels (`has member`, `threatens`, …) while preserving submitted predicate values.
- Known types include inline example + usage note.
- Live preview sentence appears when source, type, and target are present (e.g. “the group threatens Glowkindle”).
- Custom predicate placeholder no longer suggests `same_as`.
- Identity-like custom predicates (`same_as`, `alias_of`, …) show guidance recommending Link existing.
- Exact same source/target object refs disable “Stage relationship” with a clear warning; same label on different node IDs remains allowed.

### Staging tray

- Relationship drafts display as campaign statements (e.g. “the group threatens North Gate”) rather than raw `source has_member → target` syntax.

## What remains deferred

- Player-facing graph UI and audience preview toggle
- Backend visibility filtering changes
- Identity merge system
- LLM relationship suggestions
- Character-specific visibility targeting UI
- Statblock / encounter lookup from authoring

## Manual dogfood checklist (C1S2)

Target: `http://localhost:5173/ingest?campaign=longmont-c1&session=session-2`

1. Open graph review for C1S2.
2. Highlight “gang” and open graph authoring.
3. Confirm visibility dropdown shows separate GM private, Table known, Player visible, Character-specific, Hidden until revealed.
4. Confirm default is GM private.
5. Select Player visible and stage a draft; confirm preview/staging copy says “Player visible”.
6. Switch to Link existing; confirm Link visibility has the same separate options.
7. Relationship section: choose source “the group” and target “Glowkindle”.
8. Choose a campaign-useful predicate or custom predicate.
9. Confirm a preview sentence appears and reads like campaign language.
10. Try custom `same_as`; confirm warning recommends Link existing.
11. Try same source and target; confirm Stage relationship is disabled with useful warning.
12. Confirm no source markdown, extracted run artifacts, overlay, or event log are written until prepare/commit.

**Pass condition:** A GM can stage visibility and relationships with fewer product-category mistakes.
