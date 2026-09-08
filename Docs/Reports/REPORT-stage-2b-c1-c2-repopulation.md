# REPORT — Stage 2B C1/C2 repopulation onto durable APP-STATE

**Created:** 2026-09-08  
**Capability:** exact Buddy-side C1/C2 continuity restore onto `127.0.0.1:54331`, then read-only rejoin of the already-durable Eldyrwild World Supergraph on `127.0.0.1:54330`  
**Handoff:** `Docs/Plans/HANDOFF-DOGFOOD-CONTINUITY-stage-2b-c1-c2-repopulation-v2.md`  
**Branch:** `dogfood-continuity/stage-2b-c1-c2-repopulation-v2`  
**Exact base:** `1ed1b6c484d898a2216330258be2897dc0588f74` (`main` after PR #692)  
**Stage 2B:** CURRENT in this PR — **not DONE** until merge + human dogfood. Stage 2 / STOP 2 remain open.

DSN passwords and `.env` contents are omitted. Recap prose is omitted.

---

## Steward facts recorded here

```text
PR #692                         MERGED (predecessor)
merge                           1ed1b6c484d898a2216330258be2897dc0588f74
reviewed head                   2bb9384099f7408cb8859c43ba98e3d8f28768aa
formal review cycles            3
Stage 2A                        DONE
Stage 2B                        CURRENT (this work)
Stage 2 / STOP 2                OPEN
```

This is not a World Graph recovery. No DungeonMind write, contribution replay, re-ingestion, or graph-head advancement was performed.

---

## Authority coordinates (sanitized)

| Field | Value |
| --- | --- |
| Buddy APP-STATE | `dungeonbuddy_application_state` @ `127.0.0.1:54331` |
| Schema | `20260906_0006` at head |
| DungeonMind World | `dungeonmind_cutover_live` @ `127.0.0.1:54330` (read-only) |
| Historical ingest root | DFC-1 `primary-checkout` (`DungeonMindBuddy` local `out/` + `evals/` manifests) |
| Product API / UI | already-running `127.0.0.1:8000` / `127.0.0.1:5173` against the durable DSN |
| Disposable tests | `127.0.0.1:54329` (`dungeonmind-postgres-dev`); never the live `54331` |

---

## Pre-write capture

Fingerprint of live `54331` before any Stage 2B product write matched the Stage 2A drill fingerprint. The durability-witness Plan was the only Content work object.

```text
pre-write fingerprint           57e74f3f3836fd126a6a62c786ed283d5f03a59c6a547e48d3291b1d1f2a97a8
pre-write backup SHA-256        2b00dc924da357a9e202fe6e6842471110b8d9466f273f999197d873cf952537
witness Plan                    3c8c6f8b-498d-4d3e-afaf-15b2e1a6520d
                                Durability Witness — Delete Me Later
ingest.run                      0
source.revision                 0
```

---

## Exact recovery

### Ingest (reuse #686 operator, unchanged)

Preview `--all-historical-ingest` against `primary-checkout`: selected 53, blocked no, `target_set_sha256` `44b24f69366e1e067322628b9c46c3dfb151e3bc3c789676ff806f18ba491627` (same handshake as DFC-2c). Apply imported 53 / conflict 0 / product verification passed. Unavailable components 246 (span/candidate/provenance bytes were not this slice).

Post-apply catalog:

```text
ingest.run count                53
longmont-c1 / longmont-c2       24 / 29
validated / prepared            36 / 17
reviewable                      0
sorted run_id identity SHA-256  59508725ad56789bc333af3cea9f311dda55b8eac1b89aa4639c49278b40f5f1
C2S25 exact run                 graph-ingest:longmont-c2:session-25:20260808T005650Z
```

The 53 identities are the ledger set. Replay classified all 53 `CURRENT_EXACT` / `noop`.

### Plan (reuse #685 operator, unchanged)

```text
document_id                     80630cc2-33ee-40db-bf9d-fb5217085e17
title                           C2 Session 27 Prep
revision                        2
bytes                           2631
content SHA-256                 d8a8595d5211d00a57731354ea06bce25aa6236332b66dece59870ed9d77a511
importer imported               1 then replay imported 0 / CURRENT_EXACT
witness Plan                    still present, unchanged
```

### Source (narrow exact-UUID assertion)

`--check-only` against the restored C2S25 run: digest/scope/revision preconditions passed; `source.revision` count stayed 0. Apply then restored the previously accepted UUID:

```text
source_artifact_id              artifact:recap:longmont-c2:session-25:fd38b5915b32
source_revision_id              8ed1e034-23c6-4295-b2ff-05d5cdd643a9
content SHA-256                 fd38b5915b32beb77142c0334c578e7ff0d46ef6d91deb545801761508d26d0d
world_id                        eldyrwild
```

Replay of the same command returned the same UUID/digest; APP-STATE fingerprint did not change.

---

## Replay and fingerprint stability

```text
post-recovery fingerprint       c1d17b77a8d2fe885ed88ed72615e2fb0b2c5f9ab2d21c7d8608145e870ba168
ingest replay                   CURRENT_EXACT=53, importer imported=0, conflict=0
plan replay                     imported=0, product verification passed
source replay                   same source_revision_id / digest; fingerprint unchanged
```

---

## Ordinary product witness

Live API (`GET /api/live/graph-preview/extraction-runs`) returned 53 runs including the C2S25 identity. Plan list returned both:

- `80630cc2-33ee-40db-bf9d-fb5217085e17` C2 Session 27 Prep revision 2
- `3c8c6f8b-498d-4d3e-afaf-15b2e1a6520d` Durability Witness — Delete Me Later revision 1

Assembled UI on `127.0.0.1:5173` (already-running Vite/API; no World write):

- Ingest Load recap picker showed C1/C2 history again; Session 25 listed `graph-ingest:longmont-c2:session-25:20260808T005650Z` as validated history.
- Loading that run bound Graph Review to the exact artifact/run, rendered the historical recap from APP-STATE, and showed World `eldyrwild` graph `rev:680c246047d67f9fe0293ee90526f670`.
- Clicking the Orik pill opened the World object card (`node:orik`, related Brin, session_recap evidence on the C2S25 artifact).
- `/plan?documentId=80630cc2-33ee-40db-bf9d-fb5217085e17` opened C2 Session 27 Prep; the durability-witness title remained present.

The already-running API served recovered identities without a restart (it reads the durable DSN). That is stronger than a bounce proof: live process + durable rows.

---

## World read-only join

World head before Stage 2B product reads and after Orik object retrieval:

```text
world                           eldyrwild
head                            rev:680c246047d67f9fe0293ee90526f670
```

C2S25 recap-inspection: `sourceStatus=available`, digest `sha256:fd38b5915b32…`. Recap-projection: `sourceRevisionId=8ed1e034-23c6-4295-b2ff-05d5cdd643a9`, `graphId=rev:680c246047d67f9fe0293ee90526f670`, `graphStatus=available`, Orik mention `node:orik`. Object retrieval `POST /api/live/world-graph/retrieval/object` outcome `enough`, snapshot `isHead=true` at that revision. Head unchanged after the click.

---

## Post-repopulation backup / second-target restore

No live `down -v`. External custom-format dump of `54331`, then restore into a second empty database on the same durable server (`dungeonbuddy_application_state_stage2b_witness`). Witness dropped after the proof.

```text
post-write backup SHA-256       23d8960f57c1c58c6982b86bbd202ff5e670c289a2a4948833fa1c317052922c
expected fingerprint            c1d17b77a8d2fe885ed88ed72615e2fb0b2c5f9ab2d21c7d8608145e870ba168
restore READY                   true
restored fingerprint            c1d17b77a8d2fe885ed88ed72615e2fb0b2c5f9ab2d21c7d8608145e870ba168
mismatches                      none
```

---

## Automated evidence

```text
uv run pytest -q \
  tests/application_state/test_source_content_postgres.py \
  tests/test_historical_recap_source_adoption.py \
  tests/test_historical_recap_world_projection.py \
  tests/test_graph_run_registry.py \
  tests/product_continuity/test_ingest_adoption_postgres.py \
  tests/product_continuity/test_plan_adoption_postgres.py
→ 83 passed
ruff check (leased source/adoption files) → All checks passed
```

Tests used disposable PostgreSQL on `54329`, not live `54331`.

---

## Code change in this slice

`persist_source_markdown(..., source_revision_id=)` is now an exact identity assertion: insert that UUID when absent, no-op when the same artifact/digest/UUID already exists, fail closed on UUID/digest mismatch or UUID reuse. The historical recap adoption CLI gained `--source-revision-id` and `--check-only`, and loads local dotenv so the operator cannot silently miss `54331`.

Adoption scripts `#685` / `#686` were not modified.

---

## Explicitly still false

- Stage 2 / STOP 2
- bulk recap source adoption beyond C2S25
- candidate graph / span / provenance byte durability
- Build recovery
- Plan archive/delete
- Stage 1 human STOP (assembled recap dogfood still belongs to the human after this merge)
