# REPORT — DOGFOOD-CONTINUITY DFC-1 historical material inventory

**Created:** 2026-09-04  
**Capability:** read-only continuity inventory (no migration, no UI)  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-historical-material-inventory.md`  
**Branch:** `agent/dogfood-continuity-historical-inventory-v1`  
**Command:**

```bash
uv run python scripts/inventory_product_continuity.py \
  --historical-root <primary-checkout> \
  --historical-root-label primary-checkout \
  --historical-root <of-conks> \
  --historical-root-label of-conks \
  --historical-root <stewardship-si6> \
  --historical-root-label stewardship-si6 \
  --output-dir out/product_continuity
```

Generated ledger (not committed): `out/product_continuity/inventory.json` + `inventory.md`.  
This report is the sanitized W13 steward answer. Absolute home paths are omitted; use root labels only.

**Judgment of DFC-1:** not claimed here — this PR delivers the inventory capability and live evidence. Acceptance remains steward review.

---

## 1. Answers to the six steward questions

### 1. Which APP-STATE database is Buddy actually pointed at?

| Field | Value |
|---|---|
| Configured | yes |
| Readable | yes |
| Host | `127.0.0.1` |
| Port | `54329` |
| Database | `dungeonbuddy_application_state` |
| Schema head | `at_head` (Alembic head `20260902_0005` after `bootstrap_local_play.py apply`) |
| Current Build registry | `out/registries/workspace_documents.json` (absent in this inventory worktree) |

**Honest continuity finding:** this is the correct local DSN Buddy is configured to use, but the database was **empty of prior product work** at inventory time (0 Plans, 0 Runbooks, 0 `ingest.run`, 0 Play Runs). It was (re)created via bootstrap after the local Postgres container reset — the same class of clean-start APP-STATE SI-6 used intentionally. Historical product material therefore survives in **file roots**, not in the currently mounted APP-STATE.

W11: Plan/Runbook/Ingest/Play APP-STATE row counts were `0/0/0/0` before and after the inventory command.

### 2. How many historical Plans are already there vs only recoverable from old roots?

| Classification | Count |
|---|---|
| `CURRENT_EXACT` / `CURRENT_CONTAINS_HISTORY` | **0** |
| `RECOVERABLE_EXACT` | **7** |
| `CONFLICT` / `MALFORMED` | **0** |

All seven Plan identities are absent from readable APP-STATE and recoverable only from historical roots (primarily `primary-checkout`):

| Identity | Title (non-authoritative label) | Evidence |
|---|---|---|
| `00000000-0000-4000-8000-000000000000` | probe | workspace registry |
| `61b3a73b-df4e-4133-9879-bb2096796055` | C2 Session 27 Prep | workspace registry |
| `80630cc2-33ee-40db-bf9d-fb5217085e17` | C2 Session 27 Prep | registry + orphan bytes |
| `c2121a99-d0da-4ba1-b1ef-511f4f2e3abf` | C2 Session 23 Prep | workspace registry |
| `d6ed9790-ebbf-401d-90ba-182aff80917d` | C2 Session 23 Prep | workspace registry |
| `0bcfbf24-6afd-4dff-8d3b-939ca2f86cab` | _(untitled orphan)_ | orphan plan bytes |
| `0eab57a6-c1e1-4b07-a66b-b29e2ef50ed4` | _(untitled orphan)_ | orphan plan bytes |

Existing `import_plans` remains the candidate exact adoption seam for DFC-2 (not executed here).

### 3. Which Build experiments are visible now vs stranded in old registries/source files?

Current inventory worktree Build registry: **absent / empty** → 0 discoverable Build sources from current product registry.

| Classification | Count | Notes |
|---|---|---|
| `RECOVERABLE_EXACT` | 1 | orphan worldbuilding bytes `6cfebc9a-aa71-4799-8505-fbd0f5b5fb6b` @ `primary-checkout` |
| `NEEDS_ADAPTER` | 3 | registry identity only; no recoverable target bytes colocated |

Registry-only Build IDs (need a later adaptor/locator slice, not silent invent):

| Identity | Title label | Root |
|---|---|---|
| `6678fafc-cea7-4101-b36d-fa1b0a1d1170` | Ironveil Manor | `of-conks` |
| `9e7786d8-2253-4f8d-b37f-e0720feeaeda` | Hempholm — run packet | `of-conks` |
| `d10bd414-d461-48eb-a514-2c34d0fe2d8d` | SI-6 Find-existing Witness | `stewardship-si6` |

### 4. Of the historical Ingest runs, which are already `ingest.run`, which exist in `extraction_runs.json`, and which survive only as older manifests?

| Bucket | Count |
|---|---|
| Already canonical APP-STATE `ingest.run` | **0** |
| Observations from `out/registries/extraction_runs.json` | **0** (file absent in all three scanned roots) |
| Manifest-era `graph_ingest_run_manifest.json` → adapted exact identity, `RECOVERABLE_EXACT` | **53** |

Campaign split among manifest-era recoverable runs: `longmont-c1` 24, `longmont-c2` 29.  
Adaptation used the admitted `GraphIngestRunManifest` + `adapt_recap_manifest_to_extraction_run` path; **no write** occurred. A later DFC-2 slice must decide whether to drive the existing registry importer (after producing/locating `extraction_runs.json`) or add a manifest-era exact importer — that write path is out of DFC-1 scope.

### 5. Which Runbooks and Play Runs survived into APP-STATE?

| Domain | In APP-STATE now | Historical observations in scanned roots |
|---|---|---|
| Runbook | **0** | **0** (no runbook registry rows / admitted evidence under the three roots) |
| Play Run | **0** | **0** (no `out/runtime/play/runs/*.json` under the three roots) |

So for this operator's available historical checkouts, Runbook/Play continuity cannot yet be recovered from file evidence. That is an evidence gap for DFC-2, not a false “missing from APP-STATE so invent one” claim.

### 6. What exact recovery PRs are justified next?

Derived only from this ledger (named successors; not implemented here):

1. **DFC-2a — Plan exact adoption** for the seven `RECOVERABLE_EXACT` Plan IDs via the existing idempotent Plan importer against labeled historical roots (`primary-checkout` first).
2. **DFC-2b — Build orphan + registry-byte recovery** — adopt orphan `6cfebc9a-…`; separately design an adaptor/locator for the three `NEEDS_ADAPTER` registry rows (do not invent bytes).
3. **DFC-2c — Ingest manifest-era / registry adoption** — 53 exact adapted run IDs with no APP-STATE presence and no `extraction_runs.json` in scanned roots; choose one exact write seam and keep identity synthesis forbidden.
4. **DFC-2d — Runbook/Play archive hunt** — only if additional historical roots with `runbook` registry rows or `out/runtime/play/runs/*.json` are supplied; scanned roots do not justify a recovery PR yet.
5. **DFC-NAV1** — persistent app-shell navigation without full document reload — remains a **separate** UI lease (`App.tsx` / AppChrome / routing untouched by DFC-1).

---

## 2. W13 run coordinates (sanitized)

| Item | Value |
|---|---|
| Inventory worktree | `DungeonMindBuddy-dogfood-continuity-inventory` |
| Historical roots | `primary-checkout`, `of-conks`, `stewardship-si6` |
| Ledger totals | 64 items — `RECOVERABLE_EXACT` 61, `NEEDS_ADAPTER` 3 |
| Conflicts / malformed | 0 / 0 |
| Incomplete flag | `False` (APP-STATE readable) |
| Mutation | none (APP-STATE counts unchanged; inventory writes only under `out/product_continuity/**`) |
| Determinism | second run with same roots matched normalized ledger except `generated_at` |

---

## 3. Predecessor authority sync recorded in this PR

Backward-looking only (DFC-1 itself is not marked DONE):

| Fact | Recorded in |
|---|---|
| PR #682 merged @ `86296a40…`; SI-6 ACCEPTED; 2 review cycles | SI-6 report, SI roadmap, stewardship handoff |
| SURFACE-INTEGRATION CLOSED; freeze lifted | SI roadmap + CON-READY |
| SI-7 re-sequenced → DOGFOOD-CONTINUITY DFC-1 | SI roadmap + CON-READY + STEWARDS-ANCHOR |
| Old BF3B `CURRENT` retired → LATER after DFC-1 | CON-READY + STEWARDS-ANCHOR |

---

## 4. Explicit non-claims

- No Plans/Builds/Ingest/Runbooks/Play Runs were imported, migrated, or deleted.
- No `App.tsx` / AppChrome / router changes (DFC-NAV1 untouched).
- Titles and campaign/session labels above are display aids only; classifications used exact durable identity evidence only.
- An empty APP-STATE after bootstrap is **not** evidence that historical material never existed — the ledger shows where it still lives.
