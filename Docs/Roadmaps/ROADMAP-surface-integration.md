# SURFACE-INTEGRATION — Blocking Program Roadmap

**Status:** ACTIVE BLOCKING CHILD PROGRAM
**Parent:** [`ROADMAP-con-ready.md`](ROADMAP-con-ready.md)
**Re-anchored:** 2026-09-02
**Repository:** `Drakosfire/DungeonMindBuddy`

---

## Purpose

SURFACE-INTEGRATION establishes that an assembled DungeonBuddy runtime can truthfully report which authorities it is connected to and whether those foundations are usable before product Surfaces, Agents, or operators reason about application state.

CON-READY remains the GM-visible acceptance authority. SURFACE-INTEGRATION is its active blocking child program.

---

## Feature freeze

**No DungeonBuddy feature thaw before SI-6 acceptance.**

Paused until the assembled-runtime and information-delivery contract is proven:

- PLAY-SURFACE BF3C and additional contextual inventory
- Roll interaction extraction
- prepared Encounter extraction
- additional Combat integration
- source-relative asset productization
- additional Ingest UX/capability
- new Agent Interaction capability beyond disposition of parked #674
- opportunistic Plan/Build/Play UX improvements

Allowed during the freeze: SURFACE-INTEGRATION implementation/design, fixes required by SI owning-boundary witnesses, dogfood evidence mining, critical correctness/security repair, backward-looking authority sync, independent DungeonMind library work that does not change Buddy's consumed contract.

---

## Program sequence

| Slice | Capability | Status |
|---|---|---|
| SI-1 | Canonical assembled-runtime preflight | **DONE** — PR #675 merged @ `c77260b044873f3ccfb5b77e7fce643539ca9abf` (final implementation head `e71b637a3d09da439d069a7eafeb2f4be8dc31a2`, six review cycles) |
| SI-2 | Surface Information Contract v1 | **DONE** — PR #676 merged @ `cd6b20ffe151dc43dc21cb71ed77208389059566` (final implementation head `1ced8ea147f8119a424e9f44787cb7246ddb969d`, two review cycles) |
| **SI-3** | Plan graph information reference implementation | **CURRENT** — Plan is the production Surface Information adoption; Build is an unchanged compatibility/regression witness. Build Surface Information migration belongs to SI-5 unless a later re-anchor splits it differently. |
| SI-4 | Ingest information-provider disposition | Planned |
| SI-5 | Cross-surface adoption (Plan / Build / Play / Ingest / Agent / Combat-facing projections) | Planned |
| SI-6 | Clean-start assembled-product witness (canonical runtime → browser journey → restart/reload) | Planned — **acceptance gate** |
| SI-7 | Thaw + re-sequence paused feature roadmaps | Planned |

Do not pre-mark successors `DONE`.

---

## Relationship to CON-READY

Existing CON-READY user stories remain valid. Feature dispatch is frozen until SI-6 proves the assembled runtime and information-delivery contract.

SI-1 created the runtime truth layer and is complete. SI-2 established the Surface Information Contract and is complete. SI-3 is the first product adoption: Plan Edit → World Graph objects consumes the contract reactively. Build remains a regression witness, not a second provider migration.

---

## Canonical operator command (SI-1)

```bash
uv run python scripts/preflight_surface_runtime.py
```

Optional:

```bash
uv run python scripts/preflight_surface_runtime.py --require-world <world_id>
```

---

## Stewardship

Implementation handoff: [`../Plans/HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md)

Predecessor (SI-2, complete): [`../Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-surface-information-contract-v1.md)
