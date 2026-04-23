# Stage C — Registry-candidate Proposals

This directory holds aggregated `new_npc_candidates[]` outputs from Stage C cohort
runs, prepared for GM review and potential promotion into the per-campaign NPC
registries (`corpus/eldyrwild-markdown/<campaign>/_npc_registry.json`).

Each `<campaign>_registry_proposals_<timestamp>.json` file is the product of
post-processing N cohort runs against one or more session scenarios — duplicate
candidate slugs are merged across runs and scored by cross-run appearance count
(`high` ≥ 4, `medium` 2–3, `low` 1).

These files are **proposals, not authoritative.** Promotion to the registry
requires GM judgment (decide `candidate` vs `tracked` status, reconcile slug
variants, set `aliases[]`, set session bounds). The relevant `[READY]` entry
in `Backlog.md` is named "C1 NPC registry — review and promote Stage C-proposed
candidates (GM workflow)" — it tracks the workflow this directory feeds into.

Distinct from the sibling `artifacts/runs/` directory, which holds raw per-run
sidecars + reports (gitignored — re-derivable). Proposals are checked-in
because they're the back-catalog evidence of what Stage C surfaced for GM
review at a point in time.