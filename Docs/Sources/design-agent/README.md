# Design Agent / Project Sources Export

**Status:** ACTIVE EXPORT MIRROR — non-authoritative convenience copies  
**Source capture basis:** post-C2S27 CON-READY re-anchor based on `62f7f9e856327247b8677b4c951801e4c58a826c`  
**Export refreshed:** 2026-08-20  
**Canonical source-set index:** [`Docs/Design/INDEX-design-agent-source-set.md`](../../Design/INDEX-design-agent-source-set.md)

This directory is the clean pickup point for refreshing ChatGPT immediate / Project Sources.

Export copies are **not a second source of truth**. If an export copy and its canonical repository path ever differ, the canonical path wins and this export needs refresh. Files added or changed by the Playable design transaction use the exact same Git blob at canonical and export paths; unchanged mapped sources retain their existing canonical content.

The user-managed Project Sources snapshot date does **not** advance merely because this repository export changed. Advance it only after the operator actually refreshes or re-observes the product-level source set.

## Upload set

Upload the files in these folders. Classification is useful context, not precedence over the canonical source index.

### `ACTIVE_AUTHORITY/`

1. `ARCHITECTURE-campaign-supergraph.md`
2. `ROADMAP-campaign-supergraph.md`
3. `PR-TRACKER-campaign-supergraph.md`
4. `graph-document-audit.md`
5. `ARCHITECTURE-surface-interaction-layer.md`
6. `STEWARDS-ANCHOR-con-ready.md`
7. `ROADMAP-con-ready.md`
8. `ARCHITECTURE-playable-material-and-runtime.md`
9. `ROADMAP-playable-hoist-dungeonmind-kernel.md`

### `ACTIVE_REFERENCE/`

10. `STATUS-world-graph-continuity-spine.md`
11. `ARCHITECTURE-plan-surface-toolbox.md`
12. `GRAPH-MEMORY-PROJECT-LAYOUT.md`
13. `PLAN-surface-interaction-hoist-build-first.md`
14. `INDEX-hermes-campaign-authoring-foundation.md`
15. `DESIGN-play-surface-projection.md`
16. `DESIGN-playable-authoring-and-adoption.md`
17. `ANCHOR-runbook-lantern.md`
18. `README.md`
19. `INDEX-design-agent-source-set.md`

### `SOURCE_ANCHOR/`

20. `CORPUS-ANCHOR.md`

### `PROCESS/`

21. `AGENTS.md`
22. `STEWARD-CYCLE.md`
23. `HANDOFF.template.md`

## Replace / remove from the older immediate-source set

- Replace every download-suffixed older copy (`(1)`, `(2)`, `(3)`, `(4)`, etc.) with the clean file from this export.
- Remove `JUMPSTART-docs-relevance-first.md` from active immediate sources. It is superseded by `PROCESS/STEWARD-CYCLE.md`.
- Replace the old large handoff template with `PROCESS/HANDOFF.template.md`.
- Add the CON-READY anchor + roadmap and the Playable/Play authority documents listed above.
- Do not re-promote historical runbook design documents merely because they informed the new Playable architecture.

Do not upload unresolved source-only/historical drafts by default. See the canonical source-set index and graph document audit if a historical decision specifically requires them.

## Canonical mapping

| Export file | Canonical repository path |
|---|---|
| `ACTIVE_AUTHORITY/ARCHITECTURE-campaign-supergraph.md` | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| `ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` |
| `ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md` | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` |
| `ACTIVE_AUTHORITY/graph-document-audit.md` | `Docs/Reports/graph-document-audit.md` |
| `ACTIVE_AUTHORITY/ARCHITECTURE-surface-interaction-layer.md` | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` |
| `ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` | `Docs/Plans/STEWARDS-ANCHOR-con-ready.md` |
| `ACTIVE_AUTHORITY/ROADMAP-con-ready.md` | `Docs/Roadmaps/ROADMAP-con-ready.md` |
| `ACTIVE_AUTHORITY/ARCHITECTURE-playable-material-and-runtime.md` | `Docs/Design/ARCHITECTURE-playable-material-and-runtime.md` |
| `ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` | `Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md` |
| `ACTIVE_REFERENCE/STATUS-world-graph-continuity-spine.md` | `Docs/Design/STATUS-world-graph-continuity-spine.md` |
| `ACTIVE_REFERENCE/ARCHITECTURE-plan-surface-toolbox.md` | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` |
| `ACTIVE_REFERENCE/GRAPH-MEMORY-PROJECT-LAYOUT.md` | `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` |
| `ACTIVE_REFERENCE/PLAN-surface-interaction-hoist-build-first.md` | `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md` |
| `ACTIVE_REFERENCE/INDEX-hermes-campaign-authoring-foundation.md` | `Docs/Design/INDEX-hermes-campaign-authoring-foundation.md` |
| `ACTIVE_REFERENCE/DESIGN-play-surface-projection.md` | `Docs/Design/DESIGN-play-surface-projection.md` |
| `ACTIVE_REFERENCE/DESIGN-playable-authoring-and-adoption.md` | `Docs/Design/DESIGN-playable-authoring-and-adoption.md` |
| `ACTIVE_REFERENCE/ANCHOR-runbook-lantern.md` | `Docs/Design/ANCHOR-runbook-lantern.md` |
| `ACTIVE_REFERENCE/README.md` | `README.md` |
| `ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` | `Docs/Design/INDEX-design-agent-source-set.md` |
| `SOURCE_ANCHOR/CORPUS-ANCHOR.md` | `Docs/Anchors/CORPUS-ANCHOR.md` |
| `PROCESS/AGENTS.md` | `AGENTS.md` |
| `PROCESS/STEWARD-CYCLE.md` | `Docs/Process/STEWARD-CYCLE.md` |
| `PROCESS/HANDOFF.template.md` | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` |

## Maintenance rule

Never repair an export copy in place. Repair/update the canonical repository file first, then refresh its export copy. A bundle refresh should preserve byte equality for every mapped file and should update this README's capture basis.
