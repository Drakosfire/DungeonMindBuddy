# ARCHIVED — Prime Design: consolidate Graph Preview, Graph Gold Review, and Vocabulary Review into one Graph Exploring tool

**Archived:** 2026-07-02  
**Status:** Completed as historical design input; superseded by Graph Review + Gold Authoring Workbench  
**Original active path:** `Docs/Plans/HANDOFF-prime-design-graph-exploring-tool-consolidation.md`  
**Superseding design:** `Docs/Design/DESIGN-graph-review-gold-authoring-workbench.md`  
**Superseding roadmap:** `Docs/Plans/ROADMAP-graph-review-gold-authoring-workbench.md`  
**Original commit:** `5fa8c23`  

## Why this was archived

This handoff framed the problem as consolidating three read-only graph review viewers:

- Graph Preview;
- Graph Gold Review;
- Vocabulary Review.

That framing produced useful implementation machinery: lane selection, run selection, comparison plumbing, delta indexing, source-span overlays, evidence panels, and a first Graph Review Workbench.

Dogfood on 2026-07-02 showed that the implementation succeeded at consolidation but failed the human UX goal. The resulting Workbench remained metadata-first: tables, scorecards, object IDs, evidence rows, and inspectors. The user needed the recap prose itself, rendered with graph pills in comparable lanes, plus a writable gold-authoring mode.

The active direction is now larger and more specific:

```text
Graph Review + Gold Authoring Workbench:
  prose-first projected review
  + game-useful node and relationship cards
  + writable gold labeling over the same projection substrate
  + existing-object linking
  + LLM proposal staging
  + safe two-phase gold fixture writes
```

## Historical value retained

The archived handoff remains useful for historical context about what was duplicated or distinct across the prior tools, especially:

- the differences between dynamically discovered live runs and static manual-review beds;
- the existing Graph Gold Review comparison backend;
- the Graph Preview prose projection primitive;
- the Vocabulary Review provenance/prompt-context background;
- the fact that Party Registry had already proven a separate write-safe pattern.

Do not use this archived handoff as the active pickup prompt. Start from the superseding design and roadmap instead.

## Completion note

The original active file was removed from `Docs/Plans/` so future agents do not treat the read-only “Graph Exploring” consolidation as the current target.
