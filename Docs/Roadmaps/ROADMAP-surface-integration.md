# SURFACE-INTEGRATION — Blocking Program Roadmap

**Status:** CLOSED — SI-6 accepted; blocking program complete  
**Parent:** [`ROADMAP-con-ready.md`](ROADMAP-con-ready.md)  
**Re-anchored:** 2026-09-04  
**Repository:** `Drakosfire/DungeonMindBuddy`  
**SI-6 report:** [`../Reports/REPORT-surface-integration-si6-clean-start.md`](../Reports/REPORT-surface-integration-si6-clean-start.md)

---

## Purpose

SURFACE-INTEGRATION established that an assembled DungeonBuddy runtime can truthfully report which authorities it is connected to and whether those foundations are usable before product Surfaces, Agents, or operators reason about application state.

CON-READY remains the GM-visible acceptance authority. SURFACE-INTEGRATION is a **closed** blocking child program.

The program closed after finish-only stewardship: Play/Combat required **no new SI channels**; PR #674 received disposition **CLOSE/SUPERSEDE**; SI-6 clean-start witness **ACCEPTED** (PR #682). Do not reopen Surface Information adoption as a migration quota.

---

## Feature freeze

**Lifted by SI-6 acceptance.** CON-READY again owns next product sequence (SI-7 re-sequencing completed by pointing at DOGFOOD-CONTINUITY / DFC-1). Prior freeze list remains historical context; do not auto-resume the oldest parked branch without CON-READY selection.

---

## Program sequence

| Slice | Capability | Status |
|---|---|---|
| SI-1 | Canonical assembled-runtime preflight | **DONE** — PR #675 merged @ `c77260b044873f3ccfb5b77e7fce643539ca9abf` (final implementation head `e71b637a3d09da439d069a7eafeb2f4be8dc31a2`, six review cycles) |
| SI-2 | Surface Information Contract v1 | **DONE** — PR #676 merged @ `cd6b20ffe151dc43dc21cb71ed77208389059566` (final implementation head `1ced8ea147f8119a424e9f44787cb7246ddb969d`, two review cycles) |
| SI-3 | Plan graph information reference implementation | **DONE** — PR #677 merged @ `29932a8ecb74b4bcbf12633f5167470a7f05fb81` (final implementation head `345ee6957dadaa1d9052d60b70396534d7590ac8`, five review cycles) |
| SI-4 | Ingest application-state authority | **DONE** — PR #679 merged @ `010634f8ea48ed396024c79db90f41d6ba92f249` (final implementation head `55414e141f6508049c56c82bfb37bce7d9f3ba51`, two review cycles) |
| SI-5A | Build World Graph Surface Information adoption | **DONE** — PR #680 merged @ `a543af46f21d31d6ad83a88c3b2911ca4e0e4016` (final implementation head `4ccbe0fad1f5c9c60c3ced6173d842a77b162289`, three review cycles) |
| SI-5B | Ingest application-state Surface Information adoption | **DONE** — PR #681 merged @ `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb` (final implementation head `d0e9aaa80a78f71ad6bfd2195002eb5de67f098f`, three review cycles) |
| **SI-5 remainder** | Finish-only Play / Combat-facing disposition and Agent/#674 disposition | **DONE** — no SI-5C/D code; #674 CLOSED/SUPERSEDED |
| SI-6 | Clean-start assembled-product witness | **DONE / ACCEPTED** — PR #682 merged @ `86296a4021816862b1ee82cbf7478b2882493963`; accepted witness head `9349cb4b64d8a4849c4f379277ddb15df1fdc81a`; formal review cycles **2** (final ACCEPT `5109075232`) |
| SI-7 | Thaw + re-sequence paused feature roadmaps | **DONE** — freeze lifted; next forcing function is DOGFOOD-CONTINUITY DFC-1 (historical material inventory), not automatic resume of oldest parked BF3B branch |

Do not pre-mark unrelated successors `DONE`.

---

## Relationship to CON-READY

Existing CON-READY user stories remain valid. The temporary SURFACE-INTEGRATION feature freeze is lifted. Continuity of accumulated dogfood material is now the active CON-READY forcing function via [`HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`](../Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md).

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

Finish-only steward mission: **COMPLETE** — see [`../Reports/REPORT-surface-integration-si6-clean-start.md`](../Reports/REPORT-surface-integration-si6-clean-start.md)

Closed stewardship handoff: [`../Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md`](../Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md)

Completed predecessor (SI-5B): [`../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md)

Completed SI-5A reference: [`../Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md)
