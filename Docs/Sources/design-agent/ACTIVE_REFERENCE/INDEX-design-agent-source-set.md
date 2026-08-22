# Design Agent Source Set — Curated Manifest

**Status:** ACTIVE REFERENCE / process index  
**Created:** 2026-08-02  
**Repository authority refresh:** 2026-08-22 post-PR #627 PLAY-SURFACE Lane A3 current-moment cockpit design merge under CON-READY parent acceptance, plus BF1 beat-first Playable foundation dispatch, based on `f8354f5659f5ff5188ad549419dffa4bbf3ed2ba`
**Project Sources snapshot date:** 2026-08-02 — do not advance this date until the operator actually replaces/re-observes the user-managed Project Sources set  
**Repo-resident export mirror:** [`Docs/Sources/design-agent/`](../Sources/design-agent/)  
**Document class:** curated source index — **not** architecture, roadmap, or PR-sequence authority

## Purpose

Give a fresh design/review steward one checked-in answer to two separate questions:

1. **Which repository documents are current enough to use as immediate / Project Sources?**
2. **Where can the operator pick up a clean upload bundle without reconstructing it from chat or download-suffixed files?**

The canonical documents listed below remain authoritative at their normal repository paths. `Docs/Sources/design-agent/` is only an export mirror. Never edit a mirror copy as source authority; refresh it from the canonical file instead.

## Authority rule

```text
Current GitHub main is repository truth.
Project Sources are user-managed context inputs, not the repository.
The export mirror is a convenience copy, not a second authority.
ACTIVE AUTHORITY documents may direct work within their stated domain.
ACTIVE REFERENCE and PROCESS documents provide current context/process but cannot invent product sequence.
Historical, superseded, proposal, source-only, evidence-only, and chat copies cannot override current repository authority.
```

For Campaign Supergraph implementation order, [`PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) remains the sole implementation sequence.

## Current clean upload set

### ACTIVE AUTHORITY

| Role | Canonical repository path | Export copy |
|---|---|---|
| Campaign / World Supergraph architecture | [`Docs/Design/ARCHITECTURE-campaign-supergraph.md`](ARCHITECTURE-campaign-supergraph.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ARCHITECTURE-campaign-supergraph.md` |
| Campaign Supergraph roadmap | [`Docs/Roadmaps/ROADMAP-campaign-supergraph.md`](../Roadmaps/ROADMAP-campaign-supergraph.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md` |
| Campaign Supergraph implementation sequence | [`Docs/Plans/PR-TRACKER-campaign-supergraph.md`](../Plans/PR-TRACKER-campaign-supergraph.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md` |
| Graph documentation governance | [`Docs/Reports/graph-document-audit.md`](../Reports/graph-document-audit.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/graph-document-audit.md` |
| Shared surface interaction/chrome authority | [`Docs/Design/ARCHITECTURE-surface-interaction-layer.md`](ARCHITECTURE-surface-interaction-layer.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ARCHITECTURE-surface-interaction-layer.md` |
| CON-READY stewardship anchor | [`Docs/Plans/STEWARDS-ANCHOR-con-ready.md`](../Plans/STEWARDS-ANCHOR-con-ready.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` |
| CON-READY product roadmap | [`Docs/Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-con-ready.md` |
| Playable Material / Runtime architecture | [`Docs/Design/ARCHITECTURE-playable-material-and-runtime.md`](ARCHITECTURE-playable-material-and-runtime.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ARCHITECTURE-playable-material-and-runtime.md` |
| Playable architecture graduation roadmap / Play sequence | [`Docs/Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`](../Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md) | `Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` |

### ACTIVE REFERENCE

| Role | Canonical repository path | Export copy |
|---|---|---|
| World Graph current state | [`Docs/Design/STATUS-world-graph-continuity-spine.md`](STATUS-world-graph-continuity-spine.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/STATUS-world-graph-continuity-spine.md` |
| Plan surface composition | [`Docs/Design/ARCHITECTURE-plan-surface-toolbox.md`](ARCHITECTURE-plan-surface-toolbox.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/ARCHITECTURE-plan-surface-toolbox.md` |
| Graph runtime/eval/fixture path layout | [`Docs/Design/GRAPH-MEMORY-PROJECT-LAYOUT.md`](GRAPH-MEMORY-PROJECT-LAYOUT.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/GRAPH-MEMORY-PROJECT-LAYOUT.md` |
| Surface-interaction hoist sequence | [`Docs/Plans/PLAN-surface-interaction-hoist-build-first.md`](../Plans/PLAN-surface-interaction-hoist-build-first.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/PLAN-surface-interaction-hoist-build-first.md` |
| Hermes product/source index | [`Docs/Design/INDEX-hermes-campaign-authoring-foundation.md`](INDEX-hermes-campaign-authoring-foundation.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-hermes-campaign-authoring-foundation.md` |
| Play table projection design | [`Docs/Design/DESIGN-play-surface-projection.md`](DESIGN-play-surface-projection.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-play-surface-projection.md` |
| Playable authoring/adoption design | [`Docs/Design/DESIGN-playable-authoring-and-adoption.md`](DESIGN-playable-authoring-and-adoption.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/DESIGN-playable-authoring-and-adoption.md` |
| Runbook Lantern compatibility anchor | [`Docs/Design/ANCHOR-runbook-lantern.md`](ANCHOR-runbook-lantern.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/ANCHOR-runbook-lantern.md` |
| Repository overview | [`README.md`](../../README.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/README.md` |
| This source-set index | [`Docs/Design/INDEX-design-agent-source-set.md`](INDEX-design-agent-source-set.md) | `Docs/Sources/design-agent/ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` |

### SOURCE ANCHOR

| Role | Canonical repository path | Export copy |
|---|---|---|
| Eldyrwild / Longmont corpus paths | [`Docs/Anchors/CORPUS-ANCHOR.md`](../Anchors/CORPUS-ANCHOR.md) | `Docs/Sources/design-agent/SOURCE_ANCHOR/CORPUS-ANCHOR.md` |

### PROCESS

| Role | Canonical repository path | Export copy |
|---|---|---|
| Foundational repository operating law | [`AGENTS.md`](../../AGENTS.md) | `Docs/Sources/design-agent/PROCESS/AGENTS.md` |
| Design/review steward lifecycle | [`Docs/Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md) | `Docs/Sources/design-agent/PROCESS/STEWARD-CYCLE.md` |
| Per-slice handoff skeleton | [`.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`](../../.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md) | `Docs/Sources/design-agent/PROCESS/HANDOFF.template.md` |

## Play / Playable authority relation

For CR05–CR07 design work, resolve conflicts in this order:

```text
CON-READY roadmap + stewardship anchor (parent acceptance)
→ ROADMAP-playable-hoist-dungeonmind-kernel (PLAY-SURFACE sequence / current dispatch state)
→ ARCHITECTURE-playable-material-and-runtime
→ DESIGN-play-current-moment-cockpit (Beat-first contract) /
  DESIGN-play-surface-projection / DESIGN-playable-authoring-and-adoption /
  DESIGN-play-surface-gm-cockpit-target (approved target)
→ current implementation contracts/code
→ C2S27 dogfood report (REPORT-play-c2s27-native-runbook-dogfood-2026-08)
→ PR #578 mining evidence
→ historical runbook direction docs
```

This does not change Campaign Supergraph's separate graph implementation-sequence authority.

The PR #578 mining report is canonical evidence at:

```text
Docs/Reports/REPORT-pr578-play-dogfood-mining.md
```

but is intentionally **not** included in the default immediate-source bundle. It cannot override architecture/design/roadmap authority.

## Reconciliation against the 2026-08-02 immediate-source snapshot

The old downloaded/attached set is now stale in several meaningful ways:

- `JUMPSTART-docs-relevance-first.md` is **SUPERSEDED**. Do not upload it as active process context; use `PROCESS/STEWARD-CYCLE.md`.
- The old `HANDOFF.template(1).md` predates the template diet and repeats foundational process law. Replace it with `PROCESS/HANDOFF.template.md`.
- `AGENTS.md` is now foundational process authority and should be present in immediate sources.
- `GRAPH-MEMORY-PROJECT-LAYOUT.md` remains an active reference and should be present; it was absent from the current attached set.
- CON-READY and the Playable/Play design authorities are now part of the clean immediate-source bundle.
- Historical runbook documents remain evidence and should not be promoted back into ACTIVE REFERENCE.
- Download-suffixed copies such as `(1)`, `(2)`, `(3)`, `(4)` should be replaced with the clean export filenames so provenance is obvious.

The old source-only names (`PROPOSAL-context-audit-source-reanchor.md`, `source-reconciliation-report(2).md`, `LLM-graph-construction.md`, `PROJECT-SOURCES-OPERATING-TEMPLATE.md`, and historical download aliases) are intentionally **not** copied into the clean export. Their historical classification remains documented in [`Docs/Reports/graph-document-audit.md`](../Reports/graph-document-audit.md).

## Precedence when sources conflict

```text
1. Current main + domain ACTIVE AUTHORITY
2. Current domain ACTIVE REFERENCE / accepted contracts
3. AGENTS.md foundational process law
4. STEWARD-CYCLE.md steward process
5. SOURCE_ANCHOR path indexes
6. Docs/Sources/design-agent export copies (convenience mirror only)
7. Historical / superseded / proposal / evidence-only / source-only material
8. Attached Project Sources and chat summaries when they disagree with current repo
```

## Refresh procedure

When the operator wants a new immediate-source bundle:

1. Pin current `main` exactly.
2. Reconcile this index against current active authority/reference/process docs.
3. Refresh every `Docs/Sources/design-agent/` copy from its canonical repository path; copies must be byte-identical at the pinned revision.
4. Verify the bundle contains no active copy of superseded Jumpstart or other historical/source-only material.
5. Upload the classified bundle files to Project Sources / immediate sources.
6. Only after the operator actually refreshes or re-observes that user-managed set should `Project Sources snapshot date` advance.

The export folder README records its capture basis and upload order.

## Explicit exclusions

Do not put these into the clean immediate-source bundle by default:

- corpus prose payloads under `corpus/`;
- generated eval artifacts, run reports, and fixture dumps under `evals/**/artifacts/` or `out/`;
- PR #578 mining evidence unless specifically reviewing Play successors;
- active implementation handoffs that change per slice;
- stale/completed handoffs still carrying historical status;
- archived evidence trees;
- runtime source code used as if it were normative architecture;
- local/source-only proposal or research files without explicit operator intent.

## Non-goals

- This index does not create a second architecture authority.
- The export mirror does not become writable design authority.
- It does not automatically mutate the user's Project Sources UI.
- It does not claim attached sources are refreshed until the operator actually replaces them.
