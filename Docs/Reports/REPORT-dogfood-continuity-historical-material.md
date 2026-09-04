# REPORT — DOGFOOD-CONTINUITY DFC-1 historical material inventory

**Created:** 2026-09-04  
**RC1 repair:** 2026-09-04 (after formal review `5114899356` on PR #684 @ `695e5029…`)  
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
| Current Build registry | `out/registries/workspace_documents.json` (absent in this inventory worktree → authoritatively empty, readable) |

**Honest continuity finding:** this is the correct local DSN Buddy is configured to use, but the database was **empty of prior product work** at inventory time (0 Plans, 0 Runbooks, 0 `ingest.run`, 0 Play Runs). It was (re)created via bootstrap after the local Postgres container reset — the same class of clean-start APP-STATE SI-6 used intentionally. Historical product material therefore survives in **file roots**, not in the currently mounted APP-STATE.

W11: Plan/Runbook/Ingest/Play APP-STATE row counts were `0/0/0/0` before and after the inventory command.

### 2. How many historical Plans are already there vs only recoverable from old roots?

| Classification | Count |
|---|---|
| `CURRENT_EXACT` / `CURRENT_CONTAINS_HISTORY` | **0** |
| `RECOVERABLE_EXACT` | **5** (registry metadata + recoverable bytes/durable fields) |
| `NEEDS_ADAPTER` | **2** (UUID-bearing orphan bytes only — identity known, WorkObject metadata incomplete for existing importer) |
| `CONFLICT` / `MALFORMED` | **0** |

`RECOVERABLE_EXACT` Plans (candidate for existing `import_plans_from_registry`; all under `primary-checkout`):

| Identity | Title (non-authoritative label) | Evidence |
|---|---|---|
| `00000000-0000-4000-8000-000000000000` | probe | workspace registry + bytes |
| `61b3a73b-df4e-4133-9879-bb2096796055` | C2 Session 27 Prep | workspace registry + bytes |
| `80630cc2-33ee-40db-bf9d-fb5217085e17` | C2 Session 27 Prep | registry + orphan bytes |
| `c2121a99-d0da-4ba1-b1ef-511f4f2e3abf` | C2 Session 23 Prep | workspace registry + bytes |
| `d6ed9790-ebbf-401d-90ba-182aff80917d` | C2 Session 23 Prep | workspace registry + bytes |

`NEEDS_ADAPTER` Plans (do **not** feed the existing Plan importer alone):

| Identity | Evidence |
|---|---|
| `0bcfbf24-6afd-4dff-8d3b-939ca2f86cab` | orphan bytes only |
| `0eab57a6-c1e1-4b07-a66b-b29e2ef50ed4` | orphan bytes only |

### 3. Which Build experiments are visible now vs stranded in old registries/source files?

Current inventory worktree Build registry: **absent / empty** → 0 discoverable Build sources from current product registry.

| Classification | Count | Notes |
|---|---|---|
| `RECOVERABLE_EXACT` | **0** | none had both registry metadata and colocated recoverable bytes |
| `NEEDS_ADAPTER` | **4** | 3 registry-only (no bytes); 1 orphan-bytes-only |

| Identity | Title label | Root / evidence | Why not recoverable-exact |
|---|---|---|---|
| `6678fafc-cea7-4101-b36d-fa1b0a1d1170` | Ironveil Manor | `of-conks` registry | missing bytes |
| `9e7786d8-2253-4f8d-b37f-e0720feeaeda` | Hempholm — run packet | `of-conks` registry | missing bytes |
| `d10bd414-d461-48eb-a514-2c34d0fe2d8d` | SI-6 Find-existing Witness | `stewardship-si6` registry | missing bytes |
| `6cfebc9a-aa71-4799-8505-fbd0f5b5fb6b` | _(untitled)_ | `primary-checkout` orphan bytes | no registry metadata |

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

1. **DFC-2a — Plan exact adoption** for the **five** `RECOVERABLE_EXACT` Plan IDs via the existing idempotent Plan importer against `primary-checkout`. The two orphan-byte-only Plans stay out of that importer until a metadata adaptor exists.
2. **DFC-2b — Build adaptor / locator** — all four Build identities are `NEEDS_ADAPTER` (locate missing bytes for registry rows, or reconstruct registry metadata for the orphan). Do not invent bytes or metadata.
3. **DFC-2c — Ingest manifest-era / registry adoption** — 53 exact adapted run IDs with no APP-STATE presence and no `extraction_runs.json` in scanned roots; choose one exact write seam and keep identity synthesis forbidden.
4. **DFC-2d — Runbook/Play archive hunt** — only if additional historical roots with `runbook` registry rows or `out/runtime/play/runs/*.json` are supplied; scanned roots do not justify a recovery PR yet.
5. **DFC-NAV1** — persistent app-shell navigation without full document reload — remains a **separate** UI lease (`App.tsx` / AppChrome / routing untouched by DFC-1).

---

## 2. W13 run coordinates (sanitized)

| Item | Value |
|---|---|
| Inventory worktree | `DungeonMindBuddy-dogfood-continuity-inventory` |
| Historical roots | `primary-checkout`, `of-conks`, `stewardship-si6` |
| Ledger totals | 64 items — `RECOVERABLE_EXACT` **58**, `NEEDS_ADAPTER` **6** |
| Conflicts / malformed | 0 / 0 |
| Incomplete flag | `False` (APP-STATE readable; Build registry absent=empty readable) |
| Mutation | none (APP-STATE counts unchanged; inventory writes only under `out/product_continuity/**`) |

### RC1 classification corrections vs pre-review report

| Change | Before RC1 | After RC1 |
|---|---|---|
| Plan `RECOVERABLE_EXACT` | 7 (included 2 orphan-only) | **5** |
| Plan `NEEDS_ADAPTER` | 0 | **2** (orphan-only) |
| Build `RECOVERABLE_EXACT` | 1 (orphan-only) | **0** |
| Build `NEEDS_ADAPTER` | 3 | **4** |
| Ingest / Runbook / Play | unchanged | unchanged |

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
- `RECOVERABLE_EXACT` is not permission to write; orphan-byte-only identities are intentionally `NEEDS_ADAPTER`.
