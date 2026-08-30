# HANDBACK — CUTOVER D.3A Review Cycle 3 (CODE → REVIEW)

**Direction:** CODE → REVIEW  
**Workstream:** CUTOVER / D.3A — mounted production graph-engine excision  
**Canonical handoff:** `Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision.md`  
**Frozen design authority:** `Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md` §§6–7  
**Handback contract:** handoff §11  

This is the cumulative CODE → REVIEW handback for **Review Cycle 3**. No checked-in Cycle 1/2 §11 handback existed; Cycle 1/2 evidence is taken from PR #665 formal reviews, the RC2 head, and the cumulative diff.

---

## §11 CODE → REVIEW handback (filled)

### 1. PR / branch / exact final head SHA

| Field | Value |
| --- | --- |
| PR | **#665** — https://github.com/Drakosfire/DungeonMindBuddy/pull/665 |
| Branch | `cutover/mounted-graph-engine-excision` |
| Formal Cycle 1 reviewed head | `eb3df1abc7a39d14134e3d46b9640d0da4268942` |
| Cycle 1 review | REQUEST-CHANGES-equivalent **#5059665039** |
| Formal Cycle 2 reviewed head (previous reviewed head) | `8390f63dce142a51f54d265a54d2e69ef44f374a` |
| Cycle 2 review | REQUEST-CHANGES-equivalent **#5059754135** |
| Exact final head SHA (Review Cycle 3) | `064db76a7be5af73a655480506eab1baf6161a24` |

### 2. Exact dispatch base and later rebase

| Anchor | SHA |
| --- | --- |
| Handoff commit on main (design/dispatch seed) | `6b7706eec400129dbe01288630c443ae2d8a1e67` |
| Implementation start base named in handoff | `619aa2b0c4be67e1d3931ff50899d126d2dafa13` |
| Dispatch / current `main` anchor (PR base; RC1+) | `9570bd2636231b1f4ed9b6651da6c9a653abaa07` |
| RC2 merge of `origin/main` into branch | `91cb80d1bf23e7df3b785e1113ede595023b3833` |

No further rebase after RC2. Diff base for this handback: `9570bd26…HEAD`.

### 3. #662 predecessor

| Field | Value |
| --- | --- |
| Slice | D.2C4 manual Graph Review authoring continuity |
| PR | Buddy **#662** |
| Accepted head | `1ab48453cb556ca9d01ff84173ab3e2fdf81d1ec` |
| Merge SHA | `2f1b44aa8ad8bad78269c0cadf624882cd0f459f` |
| Formal cycles | **4** |
| Final PASS review | Cycle 4 PASS-equivalent **#5059141212** |

### 4. Current DungeonMind pin (unchanged)

```text
5ca5d688612349034f8ca490d465af166d883e6e
```

Proof: `pyproject.toml` and `uv.lock` still pin
`git+https://github.com/Drakosfire/DungeonMind.git@5ca5d688612349034f8ca490d465af166d883e6e`.
`git diff 9570bd26...HEAD -- pyproject.toml uv.lock` is empty for pin movement.

### 5. Active PR / write-lease check

At dispatch and at this handback:

* Active CUTOVER write lease: **D.3A** / `cutover/mounted-graph-engine-excision` / PR **#665**.
* Predecessor D.2C4 / #662 is `COMPLETE` / MERGED.
* D.3B remains `BLOCKED`; D.3 is not `DONE`.
* No other open PR holds the D.3A §4 production lease.

### 6. Exact cumulative changed paths (vs `9570bd26`) mapped to §4 / bounded discovery

```text
# §4.5 state-authority sync
Docs/Design/STATUS-world-graph-continuity-spine.md
Docs/Plans/HANDOFF-CUTOVER-buddy-graph-engine-demolition.md
Docs/Plans/HANDOFF-CUTOVER-manual-authoring-continuity-code.md
Docs/Plans/HANDOFF-CUTOVER-mounted-graph-engine-excision.md
Docs/Plans/PR-TRACKER-campaign-supergraph.md
Docs/Plans/STEWARDS-ANCHOR-cutover.md
Docs/Roadmaps/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/PR-TRACKER-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_AUTHORITY/ROADMAP-campaign-supergraph.md
Docs/Sources/design-agent/ACTIVE_REFERENCE/STATUS-world-graph-continuity-spine.md

# §4.3 frontend
apps/live-control-ui/src/planSurface/graphPreview/GraphIngestProjectionPanel.test.tsx
apps/live-control-ui/src/planSurface/graphPreview/GraphIngestProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphMergeReconciliationMaterializationPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.test.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/GraphReviewLiveProjectionPanel.tsx
apps/live-control-ui/src/planSurface/graphReviewWorkbench/graphReviewLiveReviewState.ts
apps/live-control-ui/src/surface/modules/StatblockWorkbenchModule.tsx

# §4.1 core server / authority
apps/live_control_server/config.py
apps/live_control_server/integrations/dungeonmind/world_graph_authority_adapter.py
apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py
apps/live_control_server/integrations/dungeonmind/world_graph_reads.py
apps/live_control_server/integrations/dungeonmind/world_graph_writes.py
apps/live_control_server/integrations/dungeonmind_kernel/__init__.py
apps/live_control_server/main.py
apps/live_control_server/ports/world_graph_authority.py
apps/live_control_server/ports/world_graph_authority_access.py
apps/live_control_server/ports/world_graph_initialization_access.py
apps/live_control_server/routes/graph_authoring.py
apps/live_control_server/routes/graph_preview.py
apps/live_control_server/routes/threat_query_hydration.py
apps/live_control_server/routes/world_graph_bootstrap.py
apps/live_control_server/services/extract_promote.py
apps/live_control_server/services/first_world_graph.py
apps/live_control_server/services/first_world_graph_publication.py
apps/live_control_server/services/graph_authoring_ids.py
apps/live_control_server/services/graph_authoring_overlay_projection.py
apps/live_control_server/services/graph_gold_review.py
apps/live_control_server/services/graph_object_authoring_commit.py
apps/live_control_server/services/graph_object_authoring_prepare.py
apps/live_control_server/services/graph_object_candidate_sources.py
apps/live_control_server/services/hermes_graph_query.py
apps/live_control_server/services/recap_graph_preview_ingest.py
apps/live_control_server/services/threat_publication_commits.py
apps/live_control_server/services/threat_publication_identity.py
apps/live_control_server/services/threat_publication_operations.py
apps/live_control_server/services/threat_publication_proposals.py
apps/live_control_server/services/threat_query_hydration.py
apps/live_control_server/services/union_supergraph_projection_adapter.py
apps/live_control_server/services/world_graph_projection.py
apps/live_control_server/services/world_graph_projection_recipes.py
apps/live_control_server/services/world_graph_recap_projection.py
apps/live_control_server/services/world_graph_retrieval.py
apps/live_control_server/services/worldbuilding_graph_publication.py
apps/live_control_server/services/worldbuilding_source_span_read.py

# §4.2 pure-value relocation
apps/live_control_server/models/extract_promote.py
apps/live_control_server/models/threat_query_hydration.py
apps/live_control_server/models/threat_statblock_binding.py
apps/live_control_server/models/world_graph_contribution_models.py
apps/live_control_server/models/world_graph_contribution_values.py
apps/live_control_server/models/world_graph_contributions.py
apps/live_control_server/models/world_graph_identity_models.py
apps/live_control_server/models/world_graph_identity_policy.py
apps/live_control_server/models/world_graph_mutation_context.py

# §4.2 / bounded discovery (RC3 Kernel-free mapping extracted from dungeonmind_kernel)
apps/live_control_server/integrations/dungeonmind/assertion_qualification.py
apps/live_control_server/integrations/dungeonmind/contribution_mapping.py

# Legacy package shims still present (D.3B); import edges rehomed, not deleted
src/graph_memory/** (kernel / world_supergraph / union_supergraph and consumers touched for re-exports)

# §4.4 owning tests
tests/_cutover_d3a_blocker_safe_exec.py
tests/_cutover_d3a_blocker_safe_fixtures.py
tests/_cutover_d3a_excision_witness_body.py
tests/test_cutover_direct_dungeonmind_world_graph_reads.py
tests/test_cutover_dungeonmind_first_world_initialization.py
tests/test_cutover_graph_review_authoring_continuity.py
tests/test_cutover_mounted_authority_selector.py
tests/test_cutover_mounted_graph_engine_excision.py
tests/test_cutover_native_genesis_continuity.py
tests/test_world_graph_mutation_context_parity.py

# This handback
Docs/Plans/HANDBACK-CUTOVER-D3A-Review-Cycle-3.md
```

### 7. Full Step-0 import/selector inventory (retained executable hits)

Retained mounted production paths are DungeonMind-only. Classified residual hits:

| Hit | Classification |
| --- | --- |
| `graph_memory.kernel` / `world_supergraph` / `union_supergraph` package trees | `HISTORICAL_SOURCE` — still on disk for **D.3B**; blocked before app import in owning witness |
| `integrations/dungeonmind_kernel/**` | Unmounted/historical bridge; mounted product paths rewired off it in RC3 (`contribution_mapping` / `assertion_qualification`) |
| Threat `kernel` lazy proxy in `threat_publication_commits.py` | Explicit inject/test-only path; DungeonMind port path uses `_blocked_kernel_hook` (no eager merge/lookup) |
| `graph_memory.worldbuilding_write_plan` / `extract_promote_ops` / `extract_promote_proposal` | Storage-neutral / historical helpers still imported where classification allows; not the three forbidden engine namespaces |
| Parity tests importing legacy kernel models | `LEGACY_FIXTURE` — compare-only; not mounted product boot |

No retained mounted capability still requires Buddy local head/revision/store semantics under the blocker.

### 8. Exact pure-value relocations and parity evidence

Earlier cycles (cumulative):

* Identity models/policy + mutation-context → `apps/live_control_server/models/world_graph_*`
* Contribution factories, threat/statblock bindings, retrieval errors, recap projection contracts → Buddy-owned models/services

RC3 additions:

* `contribution_mapping.py` — Kernel-free Buddy→DungeonMind contribution mapping (extracted from historical kernel/adoption path)
* `assertion_qualification.py` — Kernel-free assertion kind/predicate qualification

Parity: `tests/test_world_graph_mutation_context_parity.py` (3 tests) — rehomed mutation-context/identity JSON parity vs legacy kernel models.

### 9. Authority selector/factory matrix

`tests/test_cutover_mounted_authority_selector.py`:

| State | Result |
| --- | --- |
| unset env | defaults → DungeonMind |
| `buddy_files` / `quiesced` / unknown | fail closed |
| factories | DungeonMind-only adapters |
| alternate `world_root` | fail closed |
| `buddy_files` mode cannot select factory | fail closed |

### 10. Fresh-interpreter import-blocker setup

`tests/test_cutover_mounted_graph_engine_excision.py` installs `sys.meta_path` **Blocker** for
`graph_memory.kernel` / `world_supergraph` / `union_supergraph` **before** importing
`tests._cutover_d3a_excision_witness_body` / `create_app`. Subprocess fresh interpreter; in-process post-import blockers are not used as evidence.

### 11. App boot / lifespan under blocker

Witness: `create_app()` + TestClient lifespan; `GET /health` → **200**. Kernel prewarm removed from `main.py` lifespan. Forbidden modules remain unloaded.

### 12. Exact mounted boundaries exercised under blocker

**Still (RC2+):** projection/retrieval/source-admission; 410 retired routes; lifespan; filesystem absence; AST/static no-escape on mounted projection/retrieval.

**Now EXECUTES (RC3 closes RC2 blocker):**

| Boundary | Evidence |
| --- | --- |
| Threat publish / retry | `exercise_threat_publish_recover` |
| Worldbuilding publish / retry | `exercise_worldbuilding_publish_recover` |
| First-world D0 + D.2C4 Graph Review prepare/commit/retry/recovery | `exercise_first_world_and_graph_review` |
| Hermes `run_hermes_graph_query` | `exercise_hermes_graph_query` |

Entry: `_cutover_d3a_excision_witness_body` → `exercise_all_owning_workflows` after blocker-armed app boot.

### 13. Legacy filesystem absence before/after

Witness asserts `repo/graph_memory/worlds` absent before boot and still absent after retained workflows. No legacy worlds directory created.

### 14. Retired 410 routes (still registered)

| Route family | Code | Status |
| --- | --- | --- |
| UnionSupergraph preview | `union_supergraph_preview_retired` | **410** |
| World-graph bootstrap status/prepare/confirm | `world_graph_bootstrap_retired` | **410** |
| Merge-reconciliation prepare/apply | `graph_authoring_store_retired` | **410** |

Routes remain registered (not 404). Graph Review `/prepare` + `/commit` are **not** 410.

### 15. Retained graph-preview route proof

Witness hits retained gold/manual/recap-style projection and search routes; status not in `{404, 410}`.

### 16. D.2C4 Graph Review prepare/commit under blocker

`exercise_first_world_and_graph_review`: post-genesis Graph Review prepare → commit → retry/recovery against DungeonMind with blocker active and source admission intact.

### 17. D.2C3 native D0 continuity under blocker

Same exercise: first-world prepare/confirm yields native D0 via DungeonMind reviewed initialization under blocker.

### 18. Threat / worldbuilding / first-world regression

Executed under blocker (not module-import-only): threat confirm + exact retry; worldbuilding prepare/confirm + exact retry; first-world D0 as above.

**Product fixes required by deeper witness (RC3):**

* `first_world_graph_publication.py` — `compute_contribution_payload_sha256` from `apps.live_control_server.models.world_graph_contributions` (not kernel)
* `threat_publication_commits.py` — no eager kernel merge/lookup on DungeonMind port path (`_blocked_kernel_hook`)
* `contribution_mapping.py` + `assertion_qualification.py` — kernel-free mapping extracted from `dungeonmind_kernel`
* `world_graph_initialization_adapter.py`, `world_graph_writes.py`, `worldbuilding_graph_publication.py` — rewired off `dungeonmind_kernel` for mounted paths

### 19. Hermes / latest-recap regression

`exercise_hermes_graph_query` runs `run_hermes_graph_query` with FakeHost under blocker. Recap projection contracts remain on Buddy-owned modules from earlier rehomes.

### 20. Frontend retirement + Statblock context

* Plan Union preview: explicit retired UI; no `getUnionSupergraphProjection` / no enabled Open Union Graph action
* Graph Review live/candidate: `projectionStatus === "retired"`; no automatic/reload Union API call
* Merge materialization panel labeled retired
* Statblock create scope uses native World Graph projection head (not bootstrap status)

### 21. Every test / build / lint command with counts

```text
# Ruff (RC3 touched product/test files) — clean
uv run ruff check \
  tests/_cutover_d3a_blocker_safe_fixtures.py \
  tests/_cutover_d3a_blocker_safe_exec.py \
  tests/_cutover_d3a_excision_witness_body.py \
  tests/test_cutover_mounted_graph_engine_excision.py \
  apps/live_control_server/integrations/dungeonmind/assertion_qualification.py \
  apps/live_control_server/integrations/dungeonmind/contribution_mapping.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_initialization_adapter.py \
  apps/live_control_server/integrations/dungeonmind/world_graph_writes.py \
  apps/live_control_server/services/first_world_graph_publication.py \
  apps/live_control_server/services/threat_publication_commits.py \
  apps/live_control_server/services/worldbuilding_graph_publication.py
# → All checks passed! (0 errors; F401 Any removed from blocker_safe_fixtures)

# Owning witness + direct DM reads + mutation-context parity
# (with DMB_CUTOVER_TEST_DATABASE_URL set)
uv run pytest \
  tests/test_cutover_mounted_graph_engine_excision.py \
  tests/test_cutover_direct_dungeonmind_world_graph_reads.py \
  tests/test_world_graph_mutation_context_parity.py \
  -q
# → 54 passed, 0 failed, 0 skipped
```

Focused selector matrix (supplemental): `tests/test_cutover_mounted_authority_selector.py` (5 tests) — DungeonMind-only factory matrix.

### 22. Required PostgreSQL witness skip count

**0** required PG skips (`DMB_CUTOVER_TEST_DATABASE_URL` set for the owning cohort).

### 23. Verification provenance table

| Evidence family | Provenance |
| --- | --- |
| Owning fresh-interpreter demolition witness (PG) | author-local |
| Direct DungeonMind read cohort | author-local |
| Mutation-context parity | author-local |
| Authority selector matrix | author-local |
| Ruff on RC3 touched files | author-local |
| `git diff --check` on RC3 paths | author-local (clean) |
| Dependency pin / mirrors | author-local |
| CI | none attached to this head |
| Manual dogfood | not claimed |

### 24. `git diff --check`, Ruff, dependency immutability, pin, mirrors

* RC3 paths: `git diff --check` clean
* Ruff: clean on touched files (see §21)
* DungeonMind pin immutable at `5ca5d688…`
* Tracker/roadmap/status mirrors: `cmp` identical for PR-TRACKER, ROADMAP, STATUS pairs under `Docs/Sources/design-agent/`

### 25. No destructive user-data cleanup

Confirmed: no user-data wipe paths. Test helpers may truncate the **cutover test** DungeonMind database only under `DMB_CUTOVER_TEST_DATABASE_URL`.

### 26. D.3B package deletion still false

Confirmed present:

```text
src/graph_memory/kernel/**
src/graph_memory/world_supergraph/**
src/graph_memory/union_supergraph/**
```

D.3A does not claim physical deletion.

### 27. Backward state sync

```text
D.2C4  COMPLETE / MERGED  (#662; accepted 1ab48453…; merge 2f1b44aa…; 4 cycles; PASS 5059141212)
D.3A   DOING / active write lease / this PR #665
D.3B   BLOCKED
D.3    NOT DONE
```

### 28. Stop conditions encountered

**none** — Kernel escapes discovered by the deeper owning witness were fixed in-product rather than STOP/split.

---

## Review Cycle 3 delta (vs RC2 head `8390f63d`)

Closes RC2 finding #3: import-blocked owning proof now **executes** the frozen retained-workflow matrix (Threat, worldbuilding, first-world D0, Graph Review prepare/commit/retry, Hermes), with zero required PG skips, plus Kernel-free contribution mapping and the threat/first-world escape fixes required by that proof.

## Nano-commits (branch story)

1. `d45bd921` sync merged Graph Review predecessor / freeze D.3A inventory  
2. `2fa062ed` rehome surviving graph product values  
3. `c38d59c3` rehome contribution and projection contracts  
4. `a79d38b6` make mounted World Graph authority DungeonMind-only  
5. `e5cdd9f7` retire mounted legacy graph routes and prewarm  
6. `eb3df1ab` retire store-backed graph UI and prove engine absence ← RC1 head  
7. `91cb80d1` merge origin/main for RC2 base  
8. `8390f63d` close RC1 Kernel escape and witness gaps ← RC2 head  
9. this RC3 commit — deepen demolition witness and close mounted Kernel escapes  

---

**Successor after merge:** D.3B physical legacy-package deletion. D.3 remains NOT DONE until D.3B merges.
