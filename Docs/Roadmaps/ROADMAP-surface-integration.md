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
| SI-3 | Plan graph information reference implementation | **DONE** — PR #677 merged @ `29932a8ecb74b4bcbf12633f5167470a7f05fb81` (final implementation head `345ee6957dadaa1d9052d60b70396534d7590ac8`, five review cycles) |
| **SI-4** | Ingest application-state authority | **CURRENT** — canonical `ExtractionRun` lifecycle moves into Buddy `dungeonbuddy_application_state` PostgreSQL (`ingest.run`). No file fallback, no dual write. GraphIngest manifests remain compatibility artifacts, not product authority. |
| SI-5 | Cross-surface adoption (Plan / Build / Play / Ingest / Agent / Combat-facing projections) | Planned |
| SI-6 | Clean-start assembled-product witness (canonical runtime → browser journey → restart/reload) | Planned — **acceptance gate** |
| SI-7 | Thaw + re-sequence paused feature roadmaps | Planned |

Do not pre-mark successors `DONE`.

---

## Relationship to CON-READY

Existing CON-READY user stories remain valid. Feature dispatch is frozen until SI-6 proves the assembled runtime and information-delivery contract.

SI-1 created the runtime truth layer and is complete. SI-2 established the Surface Information Contract and is complete. SI-3 proved Plan Edit → World Graph objects consumes that contract reactively. SI-4 moves canonical Ingest run authority into the existing application-state PostgreSQL database so a fresh worktree can see the same runs. Build Surface Information migration and `/ingest` provider adoption belong to SI-5.

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

Implementation handoff: [`../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-application-state-authority-v1.md)

Predecessor (SI-3, complete): [`../Plans/HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-plan-graph-information-reference.md)
