# HANDBACK — CUTOVER D.3B physical legacy graph-engine deletion

**Lane:** CODE → REVIEW  
**Branch:** `cutover/delete-legacy-graph-engine`  
**PR title:** `CUTOVER: delete legacy Buddy graph engine`  
**Status in PR:** D.3A COMPLETE/MERGED · D.3B DOING · D.3 NOT DONE

---

## 1–4. Identity / dispatch / predecessor

| Item | Value |
|---|---|
| Dispatch base | `d4a91d7b727c0eae7dd0e09ba068e250b4819b44` — `CUTOVER: hand off legacy graph-engine deletion` |
| Branch | `cutover/delete-legacy-graph-engine` |
| Predecessor #665 accepted head | `189ffd50157534d192b2af008c48a76d12ccbc4c` |
| Predecessor #665 merge | `1a98bdb8a462ecc088ee70c2cecbed5c0d99ac3b` |
| Predecessor review | 3 formal cycles; Cycle 3 PASS-equivalent `5059851179` |
| Final PR head SHA | *(filled after push; see tip below)* |
| Executable tip | same as final PR head unless a docs-only tip follows |

## 5. DungeonMind pin

```text
dungeonmind[postgres] @ git+https://github.com/Drakosfire/DungeonMind.git@5ca5d688612349034f8ca490d465af166d883e6e
```

`pyproject.toml` / `uv.lock` **unchanged** vs dispatch base (`git diff` empty).

## 6. Parallel lease / #666

| Item | Value |
|---|---|
| #666 | OPEN — `AGENT-INTERACTION: extract ContextAssembler v1` — https://github.com/Drakosfire/DungeonMindBuddy/pull/666 |
| Lease paths | `tests/test_live_control_server.py`, `tests/test_live_query_hermes_graph.py` (and AGENT-INTERACTION product paths) **not edited** |
| Collision | None requiring serialization; D.3B absence proof **allowlists** those two test files for residual lazy Kernel imports |
| Hermes evidence | Parallel-owner: #666 still owns Hermes graph-query tests that import deleted namespaces; not rewritten in this PR |

## 7. Step-0 ledger

Canonical: `Docs/Plans/LEDGER-CUTOVER-D3B-executable-consumer-disposition.md`

Every executable consumer of retired namespaces was classified **DELETE / REHOME / REWRITE / STOP**. No `KEEP_LEGACY`.

Known D.3A seam: Threat `threat_publication_commits.py` lazy Kernel proxy → **REWRITE** (removed; DM authority verify retained; Buddy verify fail-closed).

## 8. Primary trees deleted (ABSENT)

```text
src/graph_memory/kernel/                         ABSENT  (~20 files)
src/graph_memory/world_supergraph/               ABSENT  (~9 files)
src/graph_memory/union_supergraph/               ABSENT  (~19 files)
apps/live_control_server/integrations/buddy_files/           ABSENT  (3 files)
apps/live_control_server/integrations/dungeonmind_kernel/    ABSENT  (~21 files)
```

## 9–11. Historical tools / rehomes / product rewrites (summary)

**DELETE (representative):** BuddyFiles/DM-kernel adapters; Kernel/world/union package trees; prewarm; bootstrap; union preview materializers; contribution_bundles; eldyrwild_* scripts; many Kernel-only tests/integration ports.

**REHOME:**
- `exported_contribution_evidence_ref_id` / `raw_buddy_evidence_ref_id` → `apps/.../dungeonmind/contribution_mapping.py`
- Corpus normalized recap → `apps/live_control_server/services/corpus_normalized_recap.py`
- Threat proposal helpers (no Union) → `tests/_threat_publication_helpers.py`
- Worldbuilding BLD08 / seal / candidate fixtures → `tests/_cutover_d3a_blocker_safe_fixtures.py`

**REWRITE (product seams):** Threat commits/identity/ops/proposals; threat hydration route; mutation_context_from_world_root fail-closed; first-world classify stub; projection recipes; graph_object_candidate_sources; extract_promote / extract_promote_ops; recap_graph_preview_ingest; latest_recap; world_graph_recap_projection.

**STOP:** none encountered that blocked the slice. #666 Hermes residual imports explicitly deferred.

## 12–14. Absence proofs

| Proof | Result | Provenance |
|---|---|---|
| Directory absence (5 trees) | ABSENT | author-local |
| Executable import absence (`apps/`, `src/`) | 0 AST hits | author-local |
| `tests/test_cutover_d3b_legacy_graph_engine_absence.py` | green (in floor) | author-local |
| Packaging/entrypoint | retired trees absent; 410 routes retained | author-local via D.3A witness |

## 15–25. Owning floor (author-local)

```bash
export DMB_CUTOVER_TEST_DATABASE_URL='postgresql://dungeonmind:dungeonmind-dev@127.0.0.1:54329/dmb_cutover_test'
uv run pytest \
  tests/test_cutover_mounted_graph_engine_excision.py \
  tests/test_cutover_d3b_legacy_graph_engine_absence.py \
  tests/test_cutover_mounted_authority_selector.py \
  tests/test_cutover_threat_authority_port.py \
  tests/test_cutover_worldbuilding_authority_port.py \
  tests/test_cutover_native_governed_write.py \
  tests/test_cutover_dungeonmind_first_world_initialization.py \
  tests/test_cutover_native_genesis_continuity.py \
  tests/test_cutover_graph_review_authoring_continuity.py \
  tests/test_world_graph_source_admission.py \
  -q
```

**Result:** `105 passed, 10 warnings` · **required PG skips: 0**

| Cohort | Result |
|---|---|
| D.3A fresh-interpreter mounted witness + 410s | green (via `test_cutover_mounted_graph_engine_excision`) |
| Legacy filesystem absence | green (witness asserts no `graph_memory/worlds` resurrection) |
| Native projection/retrieval | green (witness + genesis) |
| D.2C3 genesis | green |
| D.2C4 Graph Review + source admission | green (`test_world_graph_source_admission`: 6 passed) |
| Threat port | green |
| Worldbuilding port | green |
| First-world D₀ | green |
| Authority selector | green |
| Hermes | parallel-owner #666 (NOT rewritten) |

## 26. Test deletion accounting

```text
legacy paths deleted (all):     229
  tests deleted:                123
  primary graph-engine trees:   kernel+world+union+buddy_files+dungeonmind_kernel (~72)
surviving tests rewritten:      cutover threat/worldbuilding/first-world/genesis/graph-review + fixtures
new absence / helper tests:     2 (+ corpus_normalized_recap service module)
required PG skipped:            0
```

Suite shrinkage is intentional DELETE of Kernel-only / BuddyFiles-only cohorts.

## 27–30. Lint / static / pin

| Check | Result | Provenance |
|---|---|---|
| `uv run ruff check` on existing changed `*.py` | All checks passed | author-local |
| `git diff --check` | clean | author-local |
| Pin/lockfile | unchanged | author-local |
| CI | NOT_RUN (no CI gate claimed) | — |
| Independent reviewer rerun | NOT_RUN | — |

## 31. State-authority mirrors

| Pair | Result |
|---|---|
| PR-TRACKER ↔ ACTIVE_AUTHORITY | EQUAL |
| ROADMAP ↔ ACTIVE_AUTHORITY | EQUAL |
| STATUS ↔ ACTIVE_REFERENCE | EQUAL |

In-flight labels: **D.3A COMPLETE/MERGED**, **D.3B DOING**, **D.3 NOT DONE**.

## 32. Verification provenance table

| Family | Provenance |
|---|---|
| Step-0 ledger | author-local |
| Physical deletion + absence tests | author-local |
| Owning floor (105) | author-local |
| Source admission (6) | author-local |
| Ruff / diff-check | author-local |
| Reviewer-independent rerun | NOT_RUN |
| CI | NOT_RUN |
| Manual dogfood | NOT_RUN |

## 33–35. Confirmations

- No user/local data cleanup ran (test DB truncate only under `DMB_CUTOVER_TEST_DATABASE_URL`).
- D.3A remains COMPLETE/MERGED; D.3B remains DOING; D.3 remains NOT DONE in this PR.
- Stop conditions: **none** (Hermes/#666 residual imports explicitly excluded by lease, not STOP).

---

## Central invariant (post-deletion)

```text
graph_memory/kernel                 ABSENT
graph_memory/world_supergraph       ABSENT
graph_memory/union_supergraph       ABSENT
integrations/buddy_files            ABSENT
integrations/dungeonmind_kernel     ABSENT as compatibility owner

DungeonMind product workflows       GREEN (author-local floor)
legacy graph filesystem             still ABSENT
Buddy authority resurrection        IMPOSSIBLE via deleted packages
```
