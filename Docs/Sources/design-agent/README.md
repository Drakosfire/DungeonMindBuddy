# Design Agent / Project Sources Export

**Status:** ACTIVE EXPORT MIRROR — non-authoritative convenience copies  
**Source capture base:** `3a52d309a606608c9338147b78e0a2f708084042`  
**Export refreshed:** 2026-08-13  
**Canonical source-set index:** [`Docs/Design/INDEX-design-agent-source-set.md`](../../Design/INDEX-design-agent-source-set.md)

This directory is the clean pickup point for refreshing ChatGPT immediate / Project Sources.

The 15 unchanged mapped sources reuse the exact canonical Git blobs from the source capture base. `INDEX-design-agent-source-set.md` is refreshed by this same change and its canonical and export paths use the same new blob. Export copies are **not a second source of truth**. If an export copy and its canonical repository path ever differ, the canonical path wins and this export needs refresh.

## Upload set

Upload the files in these folders. Classification is useful context, not precedence over the canonical source index.

### `ACTIVE_AUTHORITY/`

1. `ARCHITECTURE-campaign-supergraph.md`
2. `ROADMAP-campaign-supergraph.md`
3. `PR-TRACKER-campaign-supergraph.md`
4. `graph-document-audit.md`
5. `ARCHITECTURE-surface-interaction-layer.md`

### `ACTIVE_REFERENCE/`

6. `STATUS-world-graph-continuity-spine.md`
7. `ARCHITECTURE-plan-surface-toolbox.md`
8. `GRAPH-MEMORY-PROJECT-LAYOUT.md`
9. `PLAN-surface-interaction-hoist-build-first.md`
10. `INDEX-hermes-campaign-authoring-foundation.md`
11. `README.md`
12. `INDEX-design-agent-source-set.md`

### `SOURCE_ANCHOR/`

13. `CORPUS-ANCHOR.md`

### `PROCESS/`

14. `AGENTS.md`
15. `STEWARD-CYCLE.md`
16. `HANDOFF.template.md`

## Replace / remove from the older immediate-source set

- Replace every download-suffixed older copy (`(1)`, `(2)`, `(3)`, `(4)`, etc.) with the clean file from this export.
- Remove `JUMPSTART-docs-relevance-first.md` from active immediate sources. It is superseded by `PROCESS/STEWARD-CYCLE.md`.
- Replace the old large handoff template with `PROCESS/HANDOFF.template.md`.
- Add `PROCESS/AGENTS.md`.
- Add `ACTIVE_REFERENCE/GRAPH-MEMORY-PROJECT-LAYOUT.md`.

Do not upload unresolved source-only/historical drafts by default. See the canonical source-set index and graph document audit if a historical decision specifically requires them.

## Canonical mapping

| Export file | Canonical repository path |
|---|---|
| `ACTIVE_AUTHORITY/ARCHITECTURE-campaign-supergraph.md` | `Docs/Design/ARCHITECTURE-campaign-supergraph.md` |
| `ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` | `Docs/Roadmaps/ROADMAP-campaign-supergraph.md` |
| `ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md` | `Docs/Plans/PR-TRACKER-campaign-supergraph.md` |
| `ACTIVE_AUTHORITY/graph-document-audit.md` | `Docs/Reports/graph-document-audit.md` |
| `ACTIVE_AUTHORITY/ARCHITECTURE-surface-interaction-layer.md` | `Docs/Design/ARCHITECTURE-surface-interaction-layer.md` |
| `ACTIVE_REFERENCE/STATUS-world-graph-continuity-spine.md` | `Docs/Design/STATUS-world-graph-continuity-spine.md` |
| `ACTIVE_REFERENCE/ARCHITECTURE-plan-surface-toolbox.md` | `Docs/Design/ARCHITECTURE-plan-surface-toolbox.md` |
| `ACTIVE_REFERENCE/GRAPH-MEMORY-PROJECT-LAYOUT.md` | `Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md` |
| `ACTIVE_REFERENCE/PLAN-surface-interaction-hoist-build-first.md` | `Docs/Plans/PLAN-surface-interaction-hoist-build-first.md` |
| `ACTIVE_REFERENCE/INDEX-hermes-campaign-authoring-foundation.md` | `Docs/Design/INDEX-hermes-campaign-authoring-foundation.md` |
| `ACTIVE_REFERENCE/README.md` | `README.md` |
| `ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` | `Docs/Design/INDEX-design-agent-source-set.md` |
| `SOURCE_ANCHOR/CORPUS-ANCHOR.md` | `Docs/Anchors/CORPUS-ANCHOR.md` |
| `PROCESS/AGENTS.md` | `AGENTS.md` |
| `PROCESS/STEWARD-CYCLE.md` | `Docs/Process/STEWARD-CYCLE.md` |
| `PROCESS/HANDOFF.template.md` | `.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md` |

## Maintenance rule

Never repair an export copy in place. Repair/update the canonical repository file first, then refresh its export copy. A bundle refresh should preserve byte equality for every mapped file and should update this README's source capture base.
