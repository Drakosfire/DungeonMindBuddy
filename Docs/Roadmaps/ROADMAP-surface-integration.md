# SURFACE-INTEGRATION — Blocking Program Roadmap

**Status:** ACTIVE BLOCKING CHILD PROGRAM — SI-6 witness repair in progress (RC1)
**Parent:** [`ROADMAP-con-ready.md`](ROADMAP-con-ready.md)
**Re-anchored:** 2026-09-04
**Repository:** `Drakosfire/DungeonMindBuddy`
**SI-6 report:** [`../Reports/REPORT-surface-integration-si6-clean-start.md`](../Reports/REPORT-surface-integration-si6-clean-start.md)

---

## Purpose

SURFACE-INTEGRATION establishes that an assembled DungeonBuddy runtime can truthfully report which authorities it is connected to and whether those foundations are usable before product Surfaces, Agents, or operators reason about application state.

CON-READY remains the GM-visible acceptance authority. SURFACE-INTEGRATION is its active blocking child program.

Finish-only dispositions stand (Play/Combat: no new SI channels; #674 CLOSE/SUPERSEDE). SI-6 ACCEPT is **not** final until RC1 witness gaps on PR #682 are closed. Do not reopen Surface Information adoption as a migration quota.

---

## Feature freeze

**Still in force until SI-6 acceptance is re-earned against the full witness clauses.** Do not thaw for Play Ask, BF3C, Combat redesign, or other parked work. RC1 on PR #682 requested Play resume, Build Find-existing, Plan reactivity/fail-closed, and report accounting before ACCEPT.

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
| SI-6 | Clean-start assembled-product witness (canonical runtime → browser journey → restart/reload) | **IN PROGRESS** — PR #682 RC1 witness repair; freeze remains |
| SI-7 | Thaw + re-sequence paused feature roadmaps | Planned — only after SI-6 ACCEPT |

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

Current finish-only steward mission: **ACTIVE** — SI-6 RC1 witness repair on PR #682; see [`../Reports/REPORT-surface-integration-si6-clean-start.md`](../Reports/REPORT-surface-integration-si6-clean-start.md)

Active stewardship handoff: [`../Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md`](../Plans/HANDOFF-STEWARDSHIP-finish-surface-integration.md)

Completed predecessor (SI-5B): [`../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-ingest-run-information-adoption-v1.md)

Completed SI-5A reference: [`../Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md`](../Plans/HANDOFF-SURFACE-INTEGRATION-build-graph-information-adoption-v1.md)
