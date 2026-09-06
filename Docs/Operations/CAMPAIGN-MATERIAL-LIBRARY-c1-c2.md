# CAMPAIGN MATERIAL LIBRARY — Longmont C1 / C2

```text
Status: ACTIVE TRANSITIONAL RECOVERY LIBRARY

Purpose:
Keep a durable human-readable locator for existing C1/C2 material until
APP-STATE + durable artifact storage + remote hosting + backup/redundancy
make this ledger unnecessary.

This file is not product authority and does not authorize reconstruction
or mutation. It records where exact material currently survives.
```

**Surveyed:** 2026-09-06  
**Product `main`:** `678e9c276ad58505c53ce61d5a659ea8c792ca31`  
**APP-STATE:** `dungeonbuddy_application_state` @ `127.0.0.1:54329`, schema `20260902_0005` (`LIVE-READ`)  
**Ingest identity digest (sorted `run_id` SHA-256):** `59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1`

Root aliases (no home-directory paths):

| Alias | Meaning |
| --- | --- |
| `current-main` | This survey checkout of current `main` |
| `primary-checkout` | DFC-1 historical root `DungeonMindBuddy` |
| `of-conks` | DFC-1 historical root `DungeonMindBuddy-of-conks-end-to-end` (UI/design evidence only; not target corpus) |
| `stewardship-si6` | DFC-1 historical root `DungeonMindBuddy-stewardship-finish-si` |
| `leftover-app-state` | Configured local PostgreSQL `dungeonbuddy_application_state` |

Do not enumerate every World graph node here. World availability is in `REPORT-c1-c2-demo-readiness.md`.

---

## 1. Recap / source prose (git-tracked)

Canonical normalized recaps for the dogfood sessions. Titles are filenames, not product authority.

| Campaign | Session | Material type | Human title/description | Stable ID | Current product authority | Root | Exact relative path | Git-tracked / DB / local-only | Owning surface | Visible in product? | Openable? | Interaction level | Redundancy posture | Evidence provenance | Known blocker / notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | session-10 | recap/source | Thraxx and the Last Warehouse | `artifact:recap:longmont-c1:session-10` (on adopted runs) | Git-tracked file; SourceArtifact id on ingest.run | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 10 - Thraxx and the Last Warehouse.md` | Git-tracked | Ingest | Catalog-visible session; prose not rendered after Load | File exists; Graph Review does not show it | CATALOG_ONLY | Git + leftover ingest.run pointer | `LIVE-READ` | Exact-review resolver rejects `validated` |
| C2 | session-23 | recap/source | Mireward Gate Battle | `artifact:recap:longmont-c2:session-23` | Git-tracked file; SourceArtifact id on ingest.run | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md` | Git-tracked | Ingest | Catalog-visible; prose not rendered after Load | File exists; Graph Review does not show it | CATALOG_ONLY | Git + leftover ingest.run pointer | `LIVE-READ` | Same resolver dead-end; gold fixture expected in picker |
| C2 | session-25 | recap/source | Mireward Gate Battle II | `artifact:recap:longmont-c2:session-25:fd38b5915b32` (one run) | Git-tracked file; SourceArtifact id on ingest.run | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | Git-tracked | Ingest | Catalog-visible; prose not rendered after Load | File exists on `current-main` | CATALOG_ONLY | Git + leftover ingest.run pointer | `LIVE-READ` | Known current example of validated history dead-end |
| C1 | session-1 | recap/source | Stonebridge and Glowkindle Rats (additional rich-interaction session; gold expected) | several ingest.run SourceArtifact ids | Git-tracked file | `current-main` | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Stonebridge and Glowkindle Rats.md` | Git-tracked | Ingest | Session tab + gold expected label | File exists | CATALOG_ONLY | Git | `LIVE-READ` | Four catalog runs; picker shows history, not reviewable |

Many additional C1/C2 recaps exist under the same `Session Recaps/` tree (canonical, `_normalized`, `_breadcrumbed`, `_archive`). They are git-tracked on `current-main`. This library does not list every archive copy. Absence from the Ingest catalog means **not adopted as an ExtractionRun**, not `MISSING`.

---

## 2. Ingest runs (APP-STATE)

Leftover APP-STATE currently holds **53** canonical `ingest.run` rows (24 C1 / 29 C2). Status mix: `validated=36`, `prepared=17`, `reviewable=0`. Product catalog `GET /api/live/graph-preview/extraction-runs` schema `dmb_extraction_run_catalog_v1` (`LIVE-READ`).

Review-package seam for representative IDs returns `422 run_not_promotable` / `extraction run is not reviewable: validated` (`LIVE-READ`).

### 2.1 Required / richest sessions

| Campaign | Session | Material type | Stable IDs | Authority | Interaction level | Evidence | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C1 | session-10 | Ingest run | `graph-ingest:longmont-c1:session-10:20260722T023135Z` | leftover-app-state | CATALOG_ONLY | `LIVE-READ` | Load dialog lists the run as validated / not review-ready |
| C2 | session-23 | Ingest run | `graph-ingest:longmont-c2:session-23:20260629T040857Z` (loaded) plus nine siblings below | leftover-app-state | CATALOG_ONLY | `LIVE-READ` | Richest catalog session (10 runs); gold expected `graph-memory:session-23-candidate-graph-gold:v0` |
| C2 | session-25 | Ingest run | `graph-ingest:longmont-c2:session-25:20260808T005650Z` plus seven siblings below | leftover-app-state | CATALOG_ONLY | `LIVE-READ` | User-visible Graph Review dead-end |
| C1 | session-1 | Ingest run | four IDs below | leftover-app-state | CATALOG_ONLY | `LIVE-READ` | Gold expected `graph-memory:session-1-candidate-graph-gold:v1` |

### 2.2 All leftover ingest.run identities

Grouped by campaign/session. All `leftover-app-state`, owning surface Ingest, visible in catalog, not exact-reviewable.

**longmont-c1 / session-1** (4, validated):  
`graph-ingest:longmont-c1:session-1:20260701T185713Z`  
`graph-ingest:longmont-c1:session-1:20260701T204409Z`  
`graph-ingest:longmont-c1:session-1:20260701T215257Z`  
`graph-ingest:longmont-c1:session-1:vocabulary-ablation-projection-dogfood`

**longmont-c1 / session-2** (2, validated):  
`graph-ingest:longmont-c1:session-2:20260706T023954Z`  
`graph-ingest:longmont-c1:session-2:20260706T024026Z`

**longmont-c1 / session-3** (5, validated=3 / prepared=2):  
`graph-ingest:longmont-c1:session-3:20260718T221306Z`  
`graph-ingest:longmont-c1:session-3:20260718T221321Z`  
`graph-ingest:longmont-c1:session-3:20260718T221836Z`  
`graph-ingest:longmont-c1:session-3:20260718T225145Z`  
`graph-ingest:longmont-c1:session-3:20260718T225250Z`

**longmont-c1 / session-4..9,11,13,17** (1 each, validated):  
`graph-ingest:longmont-c1:session-4:20260719T154814Z`  
`graph-ingest:longmont-c1:session-5:20260719T201457Z`  
`graph-ingest:longmont-c1:session-6:20260719T230637Z`  
`graph-ingest:longmont-c1:session-7:20260721T141801Z`  
`graph-ingest:longmont-c1:session-8:20260721T231322Z`  
`graph-ingest:longmont-c1:session-9:20260722T020338Z`  
`graph-ingest:longmont-c1:session-10:20260722T023135Z`  
`graph-ingest:longmont-c1:session-11:20260724T031946Z`  
`graph-ingest:longmont-c1:session-13:20260727T200538Z`  
`graph-ingest:longmont-c1:session-17:20260724T031527Z`

**longmont-c1 / session-12** (3, validated=2 / prepared=1):  
`graph-ingest:longmont-c1:session-12:20260725T234131Z`  
`graph-ingest:longmont-c1:session-12:20260727T180223Z`  
`graph-ingest:longmont-c1:session-12:20260727T181654Z`

**longmont-c2 / session-23** (10, validated=6 / prepared=4):  
`graph-ingest:longmont-c2:session-23:20260629T040857Z`  
`graph-ingest:longmont-c2:session-23:20260629T041111Z`  
`graph-ingest:longmont-c2:session-23:20260629T125348Z`  
`graph-ingest:longmont-c2:session-23:20260629T125456Z`  
`graph-ingest:longmont-c2:session-23:20260629T144607Z`  
`graph-ingest:longmont-c2:session-23:20260629T183203Z`  
`graph-ingest:longmont-c2:session-23:20260726T195010Z`  
`graph-ingest:longmont-c2:session-23:20260726T195016Z`  
`graph-ingest:longmont-c2:session-23:20260726T195019Z`  
`graph-ingest:longmont-c2:session-23:20260726T195025Z`

**longmont-c2 / session-24** (11, validated=4 / prepared=7):  
`graph-ingest:longmont-c2:session-24:20260629T031256Z`  
`graph-ingest:longmont-c2:session-24:20260629T031305Z`  
`graph-ingest:longmont-c2:session-24:20260629T031852Z`  
`graph-ingest:longmont-c2:session-24:20260629T031856Z`  
`graph-ingest:longmont-c2:session-24:20260629T032202Z`  
`graph-ingest:longmont-c2:session-24:20260629T033807Z`  
`graph-ingest:longmont-c2:session-24:20260629T035216Z`  
`graph-ingest:longmont-c2:session-24:20260629T035803Z`  
`graph-ingest:longmont-c2:session-24:20260713T181901Z`  
`graph-ingest:longmont-c2:session-24:20260713T182027Z`  
`graph-ingest:longmont-c2:session-24:manual-projection-dogfood`

**longmont-c2 / session-25** (8, validated=5 / prepared=3):  
`graph-ingest:longmont-c2:session-25:20260808T005650Z`  
`graph-ingest:longmont-c2:session-25:20260808T010324Z`  
`graph-ingest:longmont-c2:session-25:20260808T010457Z`  
`graph-ingest:longmont-c2:session-25:20260808T175430Z`  
`graph-ingest:longmont-c2:session-25:20260808T175628Z`  
`graph-ingest:longmont-c2:session-25:20260808T180543Z`  
`graph-ingest:longmont-c2:session-25:20260808T181823Z`  
`graph-ingest:longmont-c2:session-25:20260808T182312Z`

---

## 3. Candidate / review artifact bundles

These are **not** APP-STATE. DFC-2c stored URI/sha256 claims on `ingest.run` components; bytes remain repo-relative `out/` on historical checkouts.

Session 25 example (`graph-ingest:longmont-c2:session-25:20260808T005650Z`):

| Kind | Relative URI | `current-main` | `primary-checkout` | Authority class |
| --- | --- | --- | --- | --- |
| source_artifact | `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 25 - Mireward Gate Battle II.md` | file | file | Git-tracked file |
| candidate_graph | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/candidate_graph.json` | missing | file | local untracked artifact / repo-relative `out/` |
| source_span_index | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/source_span_index.json` | missing | file | local untracked artifact / repo-relative `out/` |
| validation_report | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/candidate_validation_report.json` | missing | file | local untracked artifact / repo-relative `out/` |
| provenance_index | `out/graph_memory/runs/longmont-c2/session-25/20260808T005534Z/provenance_index.json` | missing | file | local untracked artifact / repo-relative `out/` |

Across all 53 leftover runs, all three required review files (`source_artifact`, `source_span_index`, `candidate_graph`) are together on `primary-checkout` for **31** runs and on `current-main` for **0** runs (`LIVE-READ` path existence; no file mutation). Interaction level: `STRANDED_EXACT` bytes + `CATALOG_ONLY` product.

Do not treat `current-main` missing `out/` as proof the bytes never existed.

---

## 4. Plan

Leftover APP-STATE **Plan count = 0** (`list_plans(status=None)`, `LIVE-READ`). Workspace document registry HTTP: `records=0`.

DFC-2a recovered exactly one Plan into an earlier leftover DB that was destroyed when local Postgres/tmpfs restarted. That recovered identity is **not** in the current leftover database. Historical locators remain DFC-1/DFC-2a evidence:

| Identity | Title label | DFC-2a leftover fate | Bytes at DFC-2a | Current leftover | Interaction level |
| --- | --- | --- | --- | --- | --- |
| `80630cc2-33ee-40db-bf9d-fb5217085e17` | C2 Session 27 Prep | recovered exactly then lost with DB recreate | 2631 | NOT_ADOPTED | STRANDED_EXACT (files) / NOT_ADOPTED (current DB) |
| `00000000-0000-4000-8000-000000000000` | probe | blank leftover residue then lost | 0 | NOT_ADOPTED | MISSING_BYTES |
| `61b3a73b-df4e-4133-9879-bb2096796055` | C2 Session 27 Prep | blank leftover residue then lost | 0 | NOT_ADOPTED | MISSING_BYTES |
| `c2121a99-d0da-4ba1-b1ef-511f4f2e3abf` | C2 Session 23 Prep | blank leftover residue then lost | 0 | NOT_ADOPTED | MISSING_BYTES |
| `d6ed9790-ebbf-401d-90ba-182aff80917d` | C2 Session 23 Prep | blank leftover residue then lost | 0 | NOT_ADOPTED | MISSING_BYTES |

Orphan-byte Plans `0bcfbf24-…` and `0eab57a6-…` remain `NEEDS_ADAPTER` (DFC-2p). Source root: `primary-checkout` registries/orphans from DFC-1. This survey did not re-adopt them.

Assembled `/plan` showed a chooser entry `C2 Session 23 Prep (no longer listed as active)` with id `local-plan:c917bba1-5993-4e24-96b7-b29a5376ab7d`. That is a **browser/local draft identity**, not an APP-STATE WorkObject (`CODE-ONLY` + `LIVE-READ` label). Do not treat it as recovered historical Plan `c2121a99-…`.

---

## 5. Build / worldbuilding source

APP-STATE / workspace registry: **0** Build documents (`LIVE-READ`). Assembled `/build` chooser: “Choose source” disabled, “Choose or create a source above.”

DFC-1 Build identities (all `NEEDS_ADAPTER`; not in current leftover DB):

| Identity | Title label | Root | Why stranded |
| --- | --- | --- | --- |
| `6678fafc-cea7-4101-b36d-fa1b0a1d1170` | Ironveil Manor | `of-conks` registry | missing bytes |
| `9e7786d8-2253-4f8d-b37f-e0720feeaeda` | Hempholm — run packet | `of-conks` registry | missing bytes |
| `d10bd414-d461-48eb-a514-2c34d0fe2d8d` | SI-6 Find-existing Witness | `stewardship-si6` registry | missing bytes |
| `6cfebc9a-aa71-4799-8505-fbd0f5b5fb6b` | untitled orphan | `primary-checkout` orphan bytes | no registry metadata |

Interaction level: `NOT_ADOPTED` / `NEEDS_ADAPTER`. Of Conks rows are locators only; Of Conks is not the target corpus.

---

## 6. Runbook / Play

| Material | Leftover APP-STATE | Historical DFC-1 roots | Assembled product | Interaction level |
| --- | --- | --- | --- | --- |
| Runbook | 0 | 0 admitted | `/play`: “No active Runbooks are available.” | NOT_ADOPTED |
| Play Run | 0 | 0 admitted | `/play`: “No durable Runs are available.” | NOT_ADOPTED |

Create blank Runbook was visible but disabled until Campaign is filled. This survey did not type a campaign or create a Runbook (`LIVE-READ` only).

---

## 7. What this library is not

- Not a World node dump.
- Not authorization to copy `out/` artifacts, re-ingest, or mutate leftover APP-STATE.
- Not proof that `current-main` missing files are globally missing.
