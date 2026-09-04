# SURFACE-INTEGRATION — Blocking Program Roadmap

**Status:** ACTIVE BLOCKING CHILD PROGRAM
**Parent:** [`ROADMAP-con-ready.md`](ROADMAP-con-ready.md)
**Re-anchored:** 2026-09-03
**Repository:** `Drakosfire/DungeonMindBuddy`

---

## Purpose

SURFACE-INTEGRATION establishes that an assembled DungeonBuddy runtime can truthfully report which authorities it is connected to and whether those foundations are usable before product Surfaces, Agents, or operators reason about application state.

CON-READY remains the GM-visible acceptance authority. SURFACE-INTEGRATION is its active blocking child program.

The program is now in **finish-only closure**: characterize and correct only the remaining false authority/information paths required by SI-6, explicitly dispose parked Agent PR #674, run the clean-start assembled witness, then close the blocking program. Do not expand Surface Information adoption merely for uniformity.

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
| SI-4 | Ingest application-state authority | **DONE** — PR #679 merged @ `010634f8ea48ed396024c79db90f41d6ba92f249` (final implementation head `55414e141f6508049c56c82bfb37bce7d9f3ba51`, two review cycles) |
| SI-5A | Build World Graph Surface Information adoption | **DONE** — PR #680 merged @ `a543af46f21d31d6ad83a88c3b2911ca4e0e4016` (final implementation head `4ccbe0fad1f5c9c60c3ced6173d842a77b162289`, three review cycles) |
| SI-5B | Ingest application-state Surface Information adoption | **DONE** — PR #681 merged @ `9d8c8a51c10bb2eb56739bc2661cb37f9f401ebb` (final implementation head `d0e9aaa80a78f71ad6bfd2195002eb5de67f098f`, three review cycles) |
| **SI-5 remainder** | Finish-only Play / Combat-facing disposition and Agent/#674 disposition | **CURRENT STEWARDSHIP MISSION** — add code only for an observed SI-6-blocking falsehood; no adoption quota |
| SI-6 | Clean-start assembled-product witness (canonical runtime → browser journey → restart/reload) | Planned — **acceptance gate** |
| SI-7 | Thaw + re-sequence paused feature roadmaps | Planned — state sync/re-sequencing after SI-6, not a feature slice |

Do not pre-mark successors `DONE`.

---

## Relationship to CON-READY

Existing CON-READY user stories remain valid. Feature dispatch is frozen until SI-6 proves the assembled runtime and information-delivery contract.

SI-1 created the runtime truth layer. SI-2 established the Surface Information Contract. SI-3 proved Plan Edit → World Graph objects consumes that contract reactively. SI-4 moved canonical Ingest run authority into the existing application-state PostgreSQL database. SI-5A moved Build Find-existing-object onto the same truthful World information pattern. SI-5B moved normal `/ingest` run existence and selection onto canonical APP-STATE `ingest.run` plus Surface Information.

The remaining SI-5 work is intentionally narrower than the wording “adopt Play/Combat/Agent.” The steward must first characterize whether the SI-6 journey still contains a false authority, structural-reactivity, stale-fallback, or ambiguous-identity path. A truthful existing path may be closed by explicit disposition with **no new channel or implementation PR**. PR #674 must receive a fresh explicit disposition against current `main`; it must not be casually rebased/merged simply because it remains open.

SI-6 should run at the earliest truthful opportunity. Witness-discovered blockers get the smallest repair slice possible, followed by an immediate witness rerun.

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

Current finish-only steward mission: [`../Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md`](../Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md)

Completed predecessor (SI-5B): [`../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md)

Completed SI-5A reference: [`../Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md)
