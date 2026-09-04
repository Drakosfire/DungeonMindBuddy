# REPORT — Dogfood continuity historical material inventory (DFC-1)

**Created:** 2026-09-04  
**Tool:** `scripts/inventory_product_continuity.py`  
**Buddy tip under inventory:** `3b84015cc90dd6c60e8d8dca6d9e2e7516779afa`  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`  
**Mutation check:** APP-STATE row counts before/after inventory = `0/0/0/0` (plans/runbooks/ingest/play_runs) — unchanged

---

## 1. Current APP-STATE coordinates (sanitized)

| Field | Value |
|---|---|
| Configured | yes |
| Readable | yes (`schema_head_status=at_head`) |
| Host | `127.0.0.1` |
| Port | `54329` |
| Database | `dungeonbuddy_application_state` |
| Current Build registry | `out/registries/workspace_documents.json` (absent in this lane checkout) |

### Answer to Q1 — Are we pointed at the APP-STATE database that contains prior product work?

**No.** This is the SI-6 clean-start database name used for SURFACE-INTEGRATION witness. It is readable and at Alembic head, but it currently contains **zero** Plans, Runbooks, Ingest runs, and Play Runs. Prior dogfood material is **not** already loaded here; it survives only in historical checkout roots (and World Graph DungeonMind DB, which DFC-1 does not inventory).

---

## 2. Historical roots supplied (sanitized labels)

| Label | Why included |
|---|---|
| `buddy-main-checkout` | Primary long-lived checkout with Plan registry rows + large `out/graph_memory/runs/**` |
| `of-conks-end-to-end` | Of Conks Build worldbuilding sources |
| `stewardship-finish-si` | SI-6 witness Build source (`SI-6 Find-existing Witness`) |
| `play-surface-runbook-gateway` | Play/runbook authoring lane (no Play/Runbook file leftovers found) |

No home-directory discovery. Absolute paths retained only in uncommitted `out/product_continuity/inventory.*`.

---

## 3. Classification totals

| Classification | Count |
|---|---|
| `RECOVERABLE_EXACT` | 61 |
| `NEEDS_ADAPTER` | 3 |
| `CURRENT_EXACT` | 0 |
| `CURRENT_CONTAINS_HISTORY` | 0 |
| `CONFLICT` | 0 |
| `MALFORMED` | 0 |
| `ORPHAN_EVIDENCE` | 0 |
| `COMPARISON_UNAVAILABLE` | 0 |

### Per domain

| Domain | Counts |
|---|---|
| Plan | `RECOVERABLE_EXACT=7` |
| Build | `RECOVERABLE_EXACT=1`, `NEEDS_ADAPTER=3` |
| Ingest | `RECOVERABLE_EXACT=53` (all `graph_ingest_run_manifest`) |
| Runbook | _(no historical observations)_ |
| Play Run | _(no historical observations)_ |

---

## 4. Answers to the continuity questions

### Q2 — Plans already in APP-STATE vs only historical?

| Bucket | Count |
|---|---|
| Already in APP-STATE (`CURRENT_*`) | **0** |
| Only historical (`RECOVERABLE_EXACT`) | **7** |

Notable recoverable Plan IDs (exact):

- `61b3a73b-df4e-4133-9879-bb2096796055` — C2 Session 27 Prep (registry)
- `80630cc2-33ee-40db-bf9d-fb5217085e17` — C2 Session 27 Prep (registry + bytes)
- `c2121a99-d0da-4ba1-b1ef-511f4f2e3abf` — C2 Session 23 Prep
- `d6ed9790-ebbf-401d-90ba-182aff80917d` — C2 Session 23 Prep
- plus orphan/registry exact UUIDs `0bcfbf24-…`, `0eab57a6-…`, and probe id `00000000-0000-4000-8000-000000000000`

### Q3 — Build sources visible now vs stranded?

| Bucket | Count | Notes |
|---|---|---|
| Current checkout Build registry | **0** (no `out/registries/workspace_documents.json` in this lane) |
| Historical registry without recoverable bytes | **3** `NEEDS_ADAPTER` | `Ironveil Manor`, `Hempholm — run packet`, `SI-6 Find-existing Witness` |
| Historical bytes with exact UUID | **1** `RECOVERABLE_EXACT` | `out/workspace/worldbuilding/6cfebc9a-…md` |

### Q4 — Ingest: APP-STATE vs `extraction_runs.json` vs manifests?

| Source | Count |
|---|---|
| Already canonical `ingest.run` | **0** |
| `out/registries/extraction_runs.json` observations | **0** (none present in supplied roots) |
| Older `graph_ingest_run_manifest.json` (adapted exact `run_id`) | **53** `RECOVERABLE_EXACT` |

All 53 are manifest-era IDs under `out/graph_memory/runs/**` on `buddy-main-checkout` (longmont-c1 + longmont-c2 sessions). None synthesize missing `source_artifact_id`.

### Q5 — Runbooks and Play Runs in APP-STATE vs legacy artifacts?

| Domain | APP-STATE | Historical observations |
|---|---|---|
| Runbook | 0 | 0 in supplied roots |
| Play Run | 0 | 0 (`out/runtime/play/runs` absent in supplied roots) |

Play/Runbook continuity cannot be recovered from these roots; if they existed, they were never left as file leftovers here, or lived only in other APP-STATE databases not currently configured.

### Q6 — Exact recovery slices warranted next (DFC-2 candidates)

Ordered by dogfood force:

1. **DFC-2A — Plan exact adoption** using existing `import_plans_from_registry` against the recoverable Plan IDs/bytes above (especially Session 23/27 prep with bytes). Inventory-only classification today; no write in DFC-1.
2. **DFC-2B — Build source recovery** for the three `NEEDS_ADAPTER` registry rows: locate missing `target_relpath` bytes or define an exact adaptor before import; plus adopt the one `RECOVERABLE_EXACT` worldbuilding file.
3. **DFC-2C — Manifest-era Ingest adoption** for the 53 adapted `graph-ingest:…` run_ids: either promote via an explicit manifest→`ExtractionRun` importer (existing registry importer does **not** cover these) or a bounded adaptor slice that never invents IDs.
4. **DFC-2D — Locate missing Runbook/Play history** if operator has another APP-STATE DB or unscoped root containing `out/runtime/play/**` / Runbook registry rows — not justified as a blind migration from this ledger alone.
5. **DFC-NAV1** remains separate: persistent app-shell navigation without full document reload (not leased here).

---

## 5. Evidence notes

- Generated machine ledger (local, not authority): `out/product_continuity/inventory.json` / `.md`
- Unit + disposable Postgres witnesses: `tests/product_continuity/` (8 passed)
- No product writes: APP-STATE counts unchanged; registries under historical roots were read-only

---

## 6. Disposition for CON-READY

DFC-1 inventory capability is the evidence base for DFC-2. SURFACE-INTEGRATION is closed; Of Conks and Cons assembly waits on exact recovery of the recoverable Plan/Build/Ingest identities above, not on inventing new product surfaces.
