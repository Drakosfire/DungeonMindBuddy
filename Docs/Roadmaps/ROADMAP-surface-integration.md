# SURFACE-INTEGRATION — Blocking Program Roadmap

**Status:** ACTIVE BLOCKING CHILD PROGRAM  
**Parent:** [`ROADMAP-con-ready.md`](ROADMAP-con-ready.md)  
**Re-anchored:** 2026-09-01  
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
| **SI-1** | Canonical assembled-runtime preflight | **CURRENT** |
| SI-2 | Surface Information Contract v1 | Planned |
| SI-3 | Graph lens reference implementation (Plan/Build rich panel) | Planned |
| SI-4 | Ingest information-provider disposition | Planned |
| SI-5 | Cross-surface adoption (Plan / Build / Play / Ingest / Agent / Combat-facing projections) | Planned |
| SI-6 | Clean-start assembled-product witness (canonical runtime → browser journey → restart/reload) | Planned — **acceptance gate** |
| SI-7 | Thaw + re-sequence paused feature roadmaps | Planned |

Do not pre-mark successors `DONE`.

---

## Relationship to CON-READY

Existing CON-READY user stories remain valid. Feature dispatch is frozen until SI-6 proves the assembled runtime and information-delivery contract.

SI-1 creates the runtime truth layer. It does **not** implement the Surface Information Contract or repair OC-020.

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

Implementation handoff: [`../Plans/HANDOFF-SURFACE-INTEGRATION-runtime-preflight-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-runtime-preflight-v1.md)
