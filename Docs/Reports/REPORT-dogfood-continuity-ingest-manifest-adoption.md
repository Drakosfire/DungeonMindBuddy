# REPORT — DOGFOOD-CONTINUITY DFC-2c exact historical Ingest run adoption

**Created:** 2026-09-05
**Capability:** explicit preview/apply of manifest-era Ingest runs into APP-STATE (`--all-historical-ingest` or exact `--run-id`; `--apply` requires `--expected-set-sha256`)
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ingest-manifest-adoption-v1.md`
**Branch:** `agent/dogfood-continuity-ingest-manifest-adoption-v1`
**Runtime worktree:** `DungeonMindBuddy-dogfood-continuity-ingest-manifest-adoption`
**Implementation head reviewed in Cycle 1:** `d232b894079ec404b70fbb440c1c067275d2f8da`
**This evidence refresh:** Cycle 1 W11 assembled hard-reload / post-restart UI + explicit configured-local W14 preview (report-only; no production code change)
**Historical roots (one-time operator input):** `primary-checkout`, `of-conks`, `stewardship-si6`

This report is the sanitized W11/W14 steward witness. Absolute home paths are omitted; DSN passwords are omitted.

## Steward acceptance (backward-only)

```text
PR #686                         MERGED
accepted exact head             2a088c4b357a5bc43635fd31aefad42f4b5d4e95
merge commit                    678e9c276ad58505c53ce61d5a659ea8c792ca31
formal review cycles            2
Review Cycle 1                  5121940121  REQUEST CHANGES-equivalent  (head d232b894079ec404b70fbb440c1c067275d2f8da)
Review Cycle 2                  5122077943  APPROVE-equivalent / merge-ready  (head 2a088c4b357a5bc43635fd31aefad42f4b5d4e95)
```

DFC-2c recovered **53 exact ingest.run catalog identities**, not review packages, candidate-graph bytes, or leftover Plan/Runbook/Play rows. The W14 configured-local database was **absent** at DFC-2c review time; that historical fail-closed witness stays true below.

Operator leftover apply after merge (named `dungeonbuddy_application_state` then holding 53 catalog rows) is DFC-3 survey observation, not a DFC-2c product change and not a claim that historical runs became `reviewable`.

---

## Authority coordinates (sanitized)

| Field | Value |
|---|---|
| Historical roots | `primary-checkout`, `of-conks`, `stewardship-si6` — evidence only; never product authority |
| Isolated write witness | disposable PostgreSQL `dungeonbuddy_app_state_dfc2c_w14_99f0d5803c` @ `127.0.0.1:54329` |
| Schema head | `at_head` (`20260902_0005`) |
| Configured local DSN name | `dungeonbuddy_application_state` @ `127.0.0.1:54329` |
| Configured local database | **absent** after the local Postgres container restart (ephemeral/tmpfs data) |
| Product catalog seam | `GET /api/live/graph-preview/extraction-runs` → `dmb_extraction_run_catalog_v1` |

The isolated DSN was re-pinned after `load_dungeonmindbuddy_dotenv(override=True)` so the API could not fall back to the named leftover database.

---

## W14 isolated 53-run witness

Selector: `--all-historical-ingest` against the three DFC-1 W13 roots. Pre-apply `ingest.run` count: **0**.

```text
selected exact historical Ingest identities    53
unsafe selected identities                      0
classifications                                 RECOVERABLE_EXACT=53
campaigns                                       longmont-c1=24 / longmont-c2=29
preview blocked                                 no
target_set_sha256                               44b24f69366e1e067322628b9c46c3dfb151e3bc3c789676ff806f18ba491627
historical roots digest                         9ae9acb2d5d4619b4db4cd7bed5b43d3aac759da1736bc273acde667ae3c5e62
```

Apply with `--expected-set-sha256` matching that preview hash:

```text
applied                                         true
blocked                                         false
importer imported                               53
importer noop                                   0
importer conflict                               0
product verification                            passed
historical_roots_unchanged                      true
post-apply list_extraction_runs()               53
post-apply catalog runs                         53
unavailable_component_count                     246
```

Replay against the same isolated authority (same roots, same `--all-historical-ingest`):

```text
classifications                                 CURRENT_EXACT=53
actions                                         noop=53
target_set_sha256                               44b24f69366e1e067322628b9c46c3dfb151e3bc3c789676ff806f18ba491627
importer imported                               0
importer invoked                                no (zero adopt pins)
product verification                            passed
catalog count                                   53
historical roots digest                         unchanged
```

No `run_id` or `source_artifact_id` was generated. Representative identities (exact catalog rows):

```text
longmont-c1  graph-ingest:longmont-c1:session-10:20260722T023135Z
             source_artifact_id=artifact:recap:longmont-c1:session-10
longmont-c2  graph-ingest:longmont-c2:session-23:20260629T040857Z
             source_artifact_id=artifact:recap:longmont-c2:session-23
```

---

## Configured local APP-STATE (W14 preview, fail-closed)

Same `--all-historical-ingest` selector and three DFC-1 W13 roots, against the configured `.env` DSN. Isolated witness DSN was **not** pinned. No `--apply`.

```text
configured_db_name          dungeonbuddy_application_state
host/port                   127.0.0.1:54329
configured_local_exists     False
mode                        preview
blocked                     True
applied                     False
selected_count              53
classifications             COMPARISON_UNAVAILABLE=53
actions                     block=53
app_state_configured        True
app_state_readable          False
schema_head_status          unavailable
detail                      preview only; no importer write
product_verification        skipped
unsafe_count                53
sample_reason               current APP-STATE ingest authority is not authoritatively readable
target_set_sha256           44b24f69366e1e067322628b9c46c3dfb151e3bc3c789676ff806f18ba491627
historical_roots_unchanged  true
importer imported           0
```

The named leftover database is absent (`FATAL: database "dungeonbuddy_application_state" does not exist`). That is a valid fail-closed reason not to perform the real local migration: current authority is not authoritatively readable, so every selected identity is `COMPARISON_UNAVAILABLE` / `block`. The matching `target_set_sha256` is the historical-manifest fingerprint set, not proof that local APP-STATE already contains those rows.

No leftover DFC-2a Plan rows were recreated, deleted, or overwritten. Isolated W14 remains the only write witness.

---

## W11 assembled restart/reload

Isolated Buddy API + Vite UI were started from this worktree with the witness DSN re-pinned after dotenv. Product catalog seam:

```text
GET /api/live/graph-preview/extraction-runs
HTTP 200
schema_version  dmb_extraction_run_catalog_v1
count           53
campaigns       longmont-c1=24 / longmont-c2=29
```

Catalog rows are canonical `ExtractionRun` JSON; they do not carry manifest locators.

Assembled `/ingest` Graph Review Workbench → Load recap (same catalog seam) showed historical runs as catalog-visible, selectable history:

- Campaign Longmont C2 / Session 23: `graph-ingest:longmont-c2:session-23:20260629T040857Z` selected as Live (canonical).
- Campaign Longmont C1 / Session 10: `graph-ingest:longmont-c1:session-10:20260722T023135Z` selected as Live (canonical).

Hard reload of `http://127.0.0.1:5173/ingest` remounted Graph Review Workbench. Load recap again listed both campaigns. Session 23 still offered the same C2 identity; Session 10 still offered `graph-ingest:longmont-c1:session-10:20260722T023135Z`.

API was stopped and restarted against the same isolated database. HTTP catalog after restart: **53** / 24 C1 / 29 C2 / both representative IDs present.

Assembled `/ingest` was opened again after that restart (full remount of Graph Review Workbench). Load recap still listed Longmont C1 and C2 history. Session 23 still offered `graph-ingest:longmont-c2:session-23:20260629T040857Z`; Session 10 was selected as Live (canonical) `graph-ingest:longmont-c1:session-10:20260722T023135Z`.

Sequence actually witnessed:

```text
/ingest → Load recap → C1/C2 representative history visible and selectable
hard reload /ingest → Load recap → same C1/C2 history still visible/selectable
stop/restart API against same isolated DB → HTTP catalog still 53 / 24 / 29
/ingest remount → Load recap → same C1/C2 history still visible/selectable
```

UI status for those rows remains catalog-visible history, not `REVIEWABLE` exact-review candidates (`validated` + missing component bytes). That is artifact-continuity debt, not catalog deletion. No AppChrome/router/UI change was required.

---

## Artifact non-claim

DFC-2c recovered **run records**, not candidate graphs, telemetry files, or source-span indexes. Isolated apply reported `unavailable_component_count=246`. Missing component URIs did not hide the 53 canonical catalog rows. Artifact relocation is a later evidence-driven slice.

---

## Tests and hygiene (implementation head `710527fe`, reviewed at `d232b894`)

```text
uv run pytest tests/product_continuity/test_ingest_adoption.py \
  tests/product_continuity/test_ingest_adoption_postgres.py -q
→ 26 passed

uv run ruff check src/product_continuity/ingest_adoption.py \
  scripts/adopt_historical_ingest_runs.py \
  tests/product_continuity/test_ingest_adoption.py \
  tests/product_continuity/test_ingest_adoption_postgres.py
→ All checks passed

uv run python -m compileall -q src/product_continuity/ingest_adoption.py \
  scripts/adopt_historical_ingest_runs.py
→ ok

git diff --check origin/main...HEAD
→ clean
```

Changed paths stay inside HANDOFF §4 (Phase 0 docs + adoption service/CLI/tests + this report). No DFC-1 classifier, recap-manifest adapter, ingest importer, migration, production API/UI, Build, Plan archive, Runbook/Play, navigation, Combat, or Agent code changed.

---

## Explicit non-claims

- DFC-2c is DONE / ACCEPTED for exact catalog-row adoption only.
- Historical component/artifact bytes are not guaranteed openable.
- At DFC-2c review time, configured local APP-STATE was not adopted: preview against the named leftover DSN was fail-closed (`COMPARISON_UNAVAILABLE=53`, `block=53`, `applied=false`) because that database was absent / not authoritatively readable.
- `/ingest` graph-review load can show historical runs as visible history without making them REVIEWABLE when the run is `validated`/`prepared` or component files are missing.
- Post-merge leftover apply and Graph Review `validated` dead-ends belong to DFC-3, not this PR.
