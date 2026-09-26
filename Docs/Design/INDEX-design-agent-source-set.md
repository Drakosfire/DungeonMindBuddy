# Design Agent Source Set — Curated Manifest

**Status:** ACTIVE REFERENCE / process index
**Created:** 2026-08-02
**Repository authority refresh:** 2026-09-25 settlement pass on `main@9473244f57e7845928fc47225fd08863ea85804b`
**Project Sources snapshot date:** 2026-08-02 — advance only after the operator actually replaces/re-observes the user-managed set
**Repo-resident export mirror:** [`Docs/Sources/design-agent/`](../Sources/design-agent/)
**Document class:** curated source index — not architecture or sequencing authority

## Purpose

Give a fresh design/review steward the smallest current source set that can
answer ownership, product direction, and process questions without reviving
completed construction scaffolds.

## Authority rule

```text
current GitHub main + domain authority
  > active domain reference/contracts
  > AGENTS.md + STEWARD-CYCLE process
  > source anchors
  > export mirror
  > historical/superseded/project-source/chat copies
```

Project Sources are user-managed context inputs, not repository truth. The
export mirror is convenience only.

The old Campaign Supergraph roadmap/tracker/status set is no longer a global
implementation sequence. Use workstream-specific authorities.

## Current clean upload set

### ACTIVE AUTHORITY

| Role | Canonical repository path | Export copy |
|---|---|---|
| World-model invariants | [`ARCHITECTURE-campaign-supergraph.md`](ARCHITECTURE-campaign-supergraph.md) | `ACTIVE_AUTHORITY/ARCHITECTURE-campaign-supergraph.md` |
| Graph/document governance | [`../Reports/graph-document-audit.md`](../Reports/graph-document-audit.md) | `ACTIVE_AUTHORITY/graph-document-audit.md` |
| Shared interaction/chrome | [`ARCHITECTURE-surface-interaction-layer.md`](ARCHITECTURE-surface-interaction-layer.md) | `ACTIVE_AUTHORITY/ARCHITECTURE-surface-interaction-layer.md` |
| Source→World authoring ownership | [`DESIGN-source-to-world-authoring-interaction-contract.md`](DESIGN-source-to-world-authoring-interaction-contract.md) | `ACTIVE_AUTHORITY/DESIGN-source-to-world-authoring-interaction-contract.md` |
| CON-READY stewardship | [`../Plans/STEWARDS-ANCHOR-con-ready.md`](../Plans/STEWARDS-ANCHOR-con-ready.md) | `ACTIVE_AUTHORITY/STEWARDS-ANCHOR-con-ready.md` |
| CON-READY product roadmap | [`../Roadmaps/ROADMAP-con-ready.md`](../Roadmaps/ROADMAP-con-ready.md) | `ACTIVE_AUTHORITY/ROADMAP-con-ready.md` |
| Playable/runtime architecture | [`ARCHITECTURE-playable-material-and-runtime.md`](ARCHITECTURE-playable-material-and-runtime.md) | `ACTIVE_AUTHORITY/ARCHITECTURE-playable-material-and-runtime.md` |
| Play/Playable sequence | [`../Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md`](../Roadmaps/ROADMAP-playable-hoist-dungeonmind-kernel.md) | `ACTIVE_AUTHORITY/ROADMAP-playable-hoist-dungeonmind-kernel.md` |

### ACTIVE REFERENCE

| Role | Canonical repository path | Export copy |
|---|---|---|
| Plan composition | [`ARCHITECTURE-plan-surface-toolbox.md`](ARCHITECTURE-plan-surface-toolbox.md) | `ACTIVE_REFERENCE/ARCHITECTURE-plan-surface-toolbox.md` |
| Buddy graph/extraction path layout | [`GRAPH-MEMORY-PROJECT-LAYOUT.md`](GRAPH-MEMORY-PROJECT-LAYOUT.md) | `ACTIVE_REFERENCE/GRAPH-MEMORY-PROJECT-LAYOUT.md` |
| Play current-moment design | [`DESIGN-play-current-moment-cockpit.md`](DESIGN-play-current-moment-cockpit.md) | `ACTIVE_REFERENCE/DESIGN-play-current-moment-cockpit.md` |
| Play projection design | [`DESIGN-play-surface-projection.md`](DESIGN-play-surface-projection.md) | `ACTIVE_REFERENCE/DESIGN-play-surface-projection.md` |
| Playable authoring/adoption | [`DESIGN-playable-authoring-and-adoption.md`](DESIGN-playable-authoring-and-adoption.md) | `ACTIVE_REFERENCE/DESIGN-playable-authoring-and-adoption.md` |
| Play GM cockpit target | [`DESIGN-play-surface-gm-cockpit-target.md`](DESIGN-play-surface-gm-cockpit-target.md) | `ACTIVE_REFERENCE/DESIGN-play-surface-gm-cockpit-target.md` |
| Runbook compatibility | [`ANCHOR-runbook-lantern.md`](ANCHOR-runbook-lantern.md) | `ACTIVE_REFERENCE/ANCHOR-runbook-lantern.md` |
| Agent context compilation | [`DECISION-agent-context-compilation.md`](DECISION-agent-context-compilation.md) | `ACTIVE_REFERENCE/DECISION-agent-context-compilation.md` |
| AgentRuntime/harness direction | [`DECISION-agent-runtime-and-semantic-adjudication.md`](DECISION-agent-runtime-and-semantic-adjudication.md) | `ACTIVE_REFERENCE/DECISION-agent-runtime-and-semantic-adjudication.md` |
| Repository overview | [`../../README.md`](../../README.md) | `ACTIVE_REFERENCE/README.md` |
| This manifest | [`INDEX-design-agent-source-set.md`](INDEX-design-agent-source-set.md) | `ACTIVE_REFERENCE/INDEX-design-agent-source-set.md` |

### SOURCE ANCHOR

- [`../Anchors/CORPUS-ANCHOR.md`](../Anchors/CORPUS-ANCHOR.md) → `SOURCE_ANCHOR/CORPUS-ANCHOR.md`

### PROCESS

- [`../../AGENTS.md`](../../AGENTS.md) → `PROCESS/AGENTS.md`
- [`../Process/STEWARD-CYCLE.md`](../Process/STEWARD-CYCLE.md) → `PROCESS/STEWARD-CYCLE.md`
- [`../../.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md`](../../.cursor/skills/external-agent-pr-loop/templates/HANDOFF.template.md) → `PROCESS/HANDOFF.template.md`

## Explicitly retired from the immediate source bundle

| Document | Classification | Reason |
|---|---|---|
| `ROADMAP-campaign-supergraph.md` | **SETTLEMENT_HOLD / program history** | Self-declared roadmap is stale; physical retirement waits for the #755–#761 UI stack to release the path |
| `PR-TRACKER-campaign-supergraph.md` | **HISTORICAL / FROZEN** | CUTOVER closed; no new dispatch |
| `STATUS-world-graph-continuity-spine.md` | **HISTORICAL / FROZEN** | August migration snapshot, not current state |
| `PLAN-surface-interaction-hoist-build-first.md` | **SUPERSEDED** | Construction target landed; DOGFOOD-POLISH closeout owns evidence |
| `INDEX-hermes-campaign-authoring-foundation.md` | **SUPERSEDED** | Hermes is an AgentRuntime adapter, not product architecture |
| `JUMPSTART-docs-relevance-first.md` | **SUPERSEDED** | Use STEWARD-CYCLE |
| old download-suffixed HANDOFF template | **SUPERSEDED** | Use canonical current template |

These files may remain reachable for historical links. They must not be
uploaded as current Project Sources.

## Settlement hold

`ROADMAP-campaign-supergraph.md` is the one intentionally unresolved physical
retirement in this pass. UI PR #755 edits that path and #755–#761 are an
existing stack. The blocked successor handoff
`Docs/Plans/HANDOFF-SETTLEMENT-retire-campaign-supergraph-roadmap.md`
owns retirement only after that stack drains and a fresh re-anchor confirms the
path is free.

## Refresh procedure

1. Pin current `main`.
2. Reconcile this index against current domain authorities and open PR leases.
3. Refresh mapped export copies from canonical paths; they must be byte-identical.
4. Ensure retired files above are absent from the clean export.
5. Upload the clean classified bundle.
6. Advance the Project Sources snapshot date only after the user-managed set is actually replaced/re-observed.

## Non-goals

This index does not create architecture, mutate the Project Sources UI, or turn
historical evidence into current authority.
