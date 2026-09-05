# REPORT — DOGFOOD-CONTINUITY DFC-2c exact historical Ingest run adoption

**Created:** 2026-09-05
**Capability:** explicit preview/apply of manifest-era Ingest runs into APP-STATE (`--all-historical-ingest` or exact `--run-id`; `--apply` requires `--expected-set-sha256`)
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-ingest-manifest-adoption-v1.md`
**Branch:** `agent/dogfood-continuity-ingest-manifest-adoption-v1`
**Runtime worktree:** `DungeonMindBuddy-dogfood-continuity-ingest-manifest-adoption`
**Code head for this witness:** `710527fe75f75526d7abb87d6e85fef8a02738e0`
**Historical roots (one-time operator input):** `primary-checkout`, `of-conks`, `stewardship-si6`

This report is the sanitized W11/W14 steward witness. Absolute home paths are omitted; DSN passwords are omitted.

DFC-2c itself is **not** marked complete here. Acceptance remains steward review.

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

## Configured local APP-STATE

The `.env` DSN still names `dungeonbuddy_application_state`, but that logical database **does not exist** on the current local Postgres (`FATAL: database "dungeonbuddy_application_state" does not exist`). Preview/apply against leftover local authority was therefore not a safe exact write.

No leftover DFC-2a Plan rows were recreated, deleted, or overwritten. Isolated W14 is the write witness.

---

## W11 product catalog / restart

Isolated Buddy API was started from this worktree with the witness DSN re-pinned after dotenv. `GET /api/live/graph-preview/extraction-runs` returned HTTP 200, schema `dmb_extraction_run_catalog_v1`, **53** runs (24/29 campaign split), including both representative IDs above. Catalog rows are canonical `ExtractionRun` JSON; they do not carry manifest locators.

`/ingest` load-session dialog (same catalog seam) showed historical runs as catalog-visible history:

- Campaign Longmont C2 / Session 23: `graph-ingest:longmont-c2:session-23:20260629T040857Z` selected as Live (canonical).
- Campaign Longmont C1 / Session 10: `graph-ingest:longmont-c1:session-10:20260722T023135Z` selected as Live (canonical).

UI status for those rows: catalog-visible, not `REVIEWABLE` exact-review candidates (`validated` + missing component bytes). That is artifact-continuity debt, not catalog deletion.

API was stopped and restarted against the same isolated database. Catalog after restart: **53** / 24 C1 / 29 C2 / both representative IDs present. Browser automation was unavailable for a second `/ingest` pass after restart; the catalog HTTP seam is the same payload `/ingest` consumes.

---

## Artifact non-claim

DFC-2c recovered **run records**, not candidate graphs, telemetry files, or source-span indexes. Isolated apply reported `unavailable_component_count=246`. Missing component URIs did not hide the 53 canonical catalog rows. Artifact relocation is a later evidence-driven slice.

---

## Tests and hygiene (code head `710527fe`)

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

- DFC-2c is not DONE.
- Historical component/artifact bytes are not guaranteed openable.
- Configured local APP-STATE was not adopted because that database is currently absent.
- `/ingest` graph-review load can show historical runs as visible history without making them REVIEWABLE when component files are missing.
