# DESIGN - Ingest Surface

## Product definition

The Ingest Surface is the workspace for converting source artifacts into reviewed campaign memory.

## Route and navigation

- Route: `/ingest`
- Top-level nav label: `Ingest`
- Page header: `Memory Ingest`

## Why this is a surface, not a Plan toolbox tool

Graph Review + Gold Authoring now contains a full editorial loop:
source artifact -> projection comparison -> Author Draft -> prepare preview -> guarded commit -> reload/verify.

That loop needs its own canvas and safety model.

## Relationship to Plan

Plan prepares the next session.
Ingest reviews what source artifacts should become in memory.

## Completed PR 11D scope

This PR only moves Graph Review into `/ingest` and removes legacy graph/ingest destinations from the Plan toolbox.

Legacy Plan toolbox entries for Ingest Recap, Graph Preview, Graph Gold Review, Graph Review, and Vocabulary Review are archived from normal navigation. The active Graph Review + Gold Authoring Workbench now lives in `/ingest`; old Plan query-string destinations are no longer treated as first-class user surfaces.

## Reader regression cleanup - PR 11E

Reader cleanup belongs in the shared projection reader path, not in one-off lane hacks.

PR 11E strips leading YAML frontmatter before projected source prose renders. The strip is intentionally leading-only so body dividers and horizontal rules stay visible, and structured mention offsets are shifted with the removed prefix so graph pills keep anchoring to the same prose.

The obsolete single-lane "Selected live lane / Source projection" chrome should not render above the two-lane Gold Fixture / Live Run layout. The per-lane headers remain the source of truth for read-only lane identity.

Lane metadata that mostly explains run paths, options, or diagnostics should stay behind Advanced details unless it is needed for the immediate review task.

## Backlog

Top-priority:

- Collapse duplicate hover popover / node game card behavior.
- Design projected object interaction modal.
- Move stage node / relationship / resolver actions near the selected object.
- Revisit staged local proposal visibility in prose.
- Build Tiptap-backed processed markdown projection overlay.
- Dogfood complete ingestion flow.

Explicitly not in this PR:

- LLM proposal assist.
- Identity merge.
- Backend write semantic changes.
