# Stage D — Entity-Resolution Proposals

This directory holds aggregated Stage D outputs from cohort runs, prepared
for GM review before any registry mutation. Stage D is a **propose-only**
stage — it never writes to `corpus/eldyrwild-markdown/<campaign>/_npc_registry.json`.

Each `<campaign>_stage_d_proposals_<timestamp>.json` file aggregates three
buckets across N cohort runs:

* `proposed_records[]` — partial `NpcRegistryRecord` rows for entities Stage D
  resolved as `new_net_entity` (status `candidate`, `hub_path` null,
  populated `slug` / `display_name` / `aliases` / `first_session` /
  `last_session` / `notes`). These are the candidate rows that may be promoted
  into the per-campaign registry after GM review (mirrors the Stage C
  precedent at `evals/stage_c_npc_candidates_vertical_slice/proposals/`).
  Naming note: the cohort sidecar key is `proposed_records[]`; the per-run
  `stage_d_output.proposed_new_records[]` (in `artifacts/runs/*.sidecar.json`)
  is the per-run analog. Same shape; different key only because the cohort
  writer aggregates across runs.
* `proposed_aliases[]` — alias-string additions for existing registry slugs
  (e.g. attaching "the captain" as an alias on `captain_lysandra_ironveil`).
  These exist because Stage D matched an `unresolved_descriptors[]` entry
  against the registry's `display_name` / `aliases[]` substring — the alias
  isn't yet checked in, but Stage D recommends it for future passes.
* `unresolvable[]` — items Stage D's deterministic v0 declined to resolve
  (generic creature descriptions without name evidence; conflicting
  evidence). These surface for GM triage and are the candidate inputs for
  Stage D's future LLM-coreference pass (v1).

These files are **proposals, not authoritative.** Promotion to the registry
requires GM judgment (decide `candidate` vs `tracked` status, reconcile slug
variants, accept/reject alias additions, set hub_path once a hub is
authored). The relevant `[READY]` entry in `Backlog.md` is the Stage D
write-surface entry; this directory is the artifact surface that closes
that loop.

Distinct from the sibling `artifacts/runs/` directory, which holds raw
per-run sidecars + reports (gitignored — re-derivable from frozen fixtures).
Proposals are checked-in because they're the back-catalog evidence of what
Stage D recommended at a point in time.
