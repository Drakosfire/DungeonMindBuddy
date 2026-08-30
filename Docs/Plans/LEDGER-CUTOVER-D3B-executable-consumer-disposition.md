# LEDGER — CUTOVER D.3B executable-consumer disposition



**Created:** 2026-08-29

**Dispatch base:** `d4a91d7b727c0eae7dd0e09ba068e250b4819b44`

**Branch:** `cutover/delete-legacy-graph-engine`

**Method:** AST import + `importlib.import_module` + literal `import graph_memory.kernel` scan across `apps/`, `src/`, `scripts/`, `tests/` (excluding the five primary deletion trees themselves).

**Dispositions:** DELETE / REHOME / REWRITE / STOP only (no KEEP_LEGACY).

**Parallel lease:** PR #666 paths are excluded from edit; listed as REWRITE-owner-elsewhere when they only mention retired names in comments/strings, or STOP if deletion requires editing them.



## Primary deletion trees (DELETE as packages)



| Path | Disposition |

|---|---|

| `src/graph_memory/kernel/**` | DELETE |

| `src/graph_memory/world_supergraph/**` | DELETE |

| `src/graph_memory/union_supergraph/**` | DELETE |

| `apps/live_control_server/integrations/buddy_files/**` | DELETE |

| `apps/live_control_server/integrations/dungeonmind_kernel/**` | DELETE (no REHOME of whole bridge; completed migration/conformance tooling) |



## Known D.3A seam (must REWRITE before package delete)



| Path | Disposition | Notes |

|---|---|---|

| `apps/live_control_server/services/threat_publication_commits.py` | REWRITE | Remove `_KernelProxy`, BuddyFiles authority constructor, and Kernel default merge/lookup/verify paths. Keep injected `merge_fn`/`lookup_fn` only when useful without Kernel. Mounted DungeonMind path unchanged. |

| `apps/live_control_server/services/threat_publication_identity.py` | REWRITE | Dead `_KernelProxy` with no call sites → remove. |

| `apps/live_control_server/services/threat_publication_operations.py` | REWRITE | Dead `_KernelProxy` → remove. |

| `apps/live_control_server/services/threat_publication_proposals.py` | REWRITE | Dead `_KernelProxy` → remove. |



## Mounted product / proof consumers



| Path | Disposition | Notes |

|---|---|---|

| `apps/.../models/world_graph_mutation_context.py` | REWRITE | Delete `mutation_context_from_world_root` Kernel helper (Buddy-only). Keep DungeonMind hydration helpers. |

| `apps/.../routes/threat_query_hydration.py` | REWRITE | Drop `dungeonmind_kernel` shadow background; query/hydration stays mounted. |

| `apps/.../services/extract_promote.py` | REWRITE | Remove Buddy confirm + Kernel already-applied path; DungeonMind confirm remains. |

| `apps/.../services/first_world_graph.py` | REWRITE | Remove `classify_world_graph_state` Buddy store classifier (only buddy_files caller). |

| `apps/.../services/graph_object_candidate_sources.py` | REWRITE | Fail-closed unavailable for Union store scopes; no `union_supergraph` import. |

| `apps/.../services/world_graph_projection_recipes.py` | REWRITE | Already no-op under DungeonMind; remove `_kernel()` import. |

| `apps/.../services/recap_graph_preview_ingest.py` | REWRITE | Stop materializing UnionSupergraphStore; keep candidate/packaging without engine packages. Extract corpus helpers out of adapter before deleting adapter. |

| `apps/.../services/world_graph_recap_projection.py` | REWRITE | Consume rehomed corpus-markdown helper (not adapter). |

| `src/graph_memory/extract_promote_ops.py` | REWRITE | Keep `resolve_merged_contribution_from_package` Kernel-free; remove/fail-closed Buddy `confirm_extract_promote` Kernel merge. |

| `src/graph_memory/interaction/latest_recap.py` | REWRITE | Remove `world_supergraph.storage` fallback; unknown/fail-closed without Buddy head. Do not edit #666-leased `hermes_graph_query.py`. |

| `src/graph_memory/ingestion/graph_ingest_verified_snapshot.py` | REWRITE / REHOME | Drop Union model dependency or rehome minimal DTO into non-engine owner if still required by recap packaging. |

| `src/graph_memory/projection/recap_projection.py` | REWRITE / REHOME | Overlay product uses contracts; remove Union store builders or rehome pure view helpers. |



## Historical / retired implementation (DELETE)



| Path | Disposition | Notes |

|---|---|---|

| `apps/.../services/world_graph_bootstrap.py` | DELETE | Implementation behind retained 410 routes. |

| `apps/.../services/world_graph_prewarm.py` | DELETE | Lifespan Kernel prewarm retired. |

| `apps/.../services/union_supergraph_projection_adapter.py` | DELETE after REHOME | Rehome `load_corpus_normalized_recap_markdown` (+ errors) first. |

| `apps/.../services/graph_merge_reconciliation_materialize.py` | DELETE | Behind retained 410s. |

| `apps/.../services/graph_review_contribution_merge.py` | DELETE | Dead Kernel Graph Review merge; D.2C4 uses DungeonMind. |

| `apps/.../services/c1_world_graph_additive_apply.py` | DELETE | Completed C1 apply tooling. |

| `apps/.../services/cutover_*.py` | DELETE | Completed cutover producers. |

| `apps/.../services/eldyrwild_*.py` | DELETE | Completed Eldyrwild repair/conformance producers. |

| `src/graph_memory/contribution_bundles/**` | DELETE | Only bootstrap/C1/legacy tests. |

| `src/graph_memory/temporal_shadow*.py` (+ CLIs) | DELETE | Non-mounted extraction tooling. |

| `src/graph_memory/interaction/digest_audit.py` | DELETE | Script/test forensic against Buddy stores. |

| `src/graph_memory/world_graph_mutation_context.py` | DELETE | Duplicate Kernel-backed module; apps models is owner. |

| `scripts/*` AST hits listed below | DELETE | Completed migration/bench/dogfood against Buddy stores. |



## Scripts (DELETE)



- `scripts/audit_graph_source_digests.py`

- `scripts/bench_world_graph_warm_path.py`

- `scripts/build_eldyrwild_dungeonmind_v6_adoption_bundle.py`

- `scripts/build_eldyrwild_relationship_semantic_closure_manifest.py`

- `scripts/compare_direct_dungeonmind_world_graph_reads.py`

- `scripts/heal_eldyrwild_contribution_integrity.py`

- `scripts/hermes_graph_dogfood_gate.py`

- `scripts/hermes_s1_latest_recap_dogfood.py`

- `scripts/spike_graph_native_contribution_union.py`

- `scripts/supersede_session24_overlapping_pc_node_assertions.py`



## Tests — surviving product/proof (REWRITE)



Retain and strip legacy imports:



- `tests/_cutover_d3a_*` witness helpers

- `tests/test_cutover_mounted_graph_engine_excision.py`

- `tests/test_cutover_native_genesis_continuity.py`

- `tests/test_cutover_native_governed_write.py`

- `tests/test_cutover_threat_authority_port*.py`

- `tests/test_cutover_worldbuilding_authority_port*.py`

- `tests/test_cutover_direct_dungeonmind_world_graph_reads.py`

- `tests/test_cutover_dungeonmind_first_world_initialization.py`

- `tests/test_cutover_graph_review_authoring_continuity.py` (if present / Kernel-free)

- Focused Threat/worldbuilding/first-world DungeonMind suites that remain green without Kernel after rewrite

- New absence proofs added by D.3B



## Tests — #666 parallel lease (do not edit)



- `tests/test_live_control_server.py`

- `tests/test_live_query_hermes_graph.py`

- plus product paths listed in handoff §4.5



If physical deletion requires changing those files → STOP / serialize with #666.



## Tests — DELETE (legacy engine / completed conformance)



All remaining AST consumers under `tests/` that exist only to exercise Kernel / WorldSupergraph / UnionSupergraph / BuddyFiles / dungeonmind_kernel conformance, including but not limited to:



- `tests/test_graph_kernel_*.py`

- `tests/test_graph_memory_union_*.py` / preview-union / merge-reconciliation apply

- `tests/test_eldyrwild_*.py` / `tests/test_dungeonmind_whole_world_*.py` / relationship conformance bridges

- `tests/test_cutover_alias_*` / `tests/test_cutover_identity_*` / `tests/test_cutover_whole_*` / `tests/test_cutover_relationship_*`

- `tests/test_world_graph_bootstrap_service.py` / `tests/test_world_graph_prewarm_service.py`

- `tests/test_temporal_shadow*.py`

- BuddyFiles-era Threat unit suites that cannot run without Kernel defaults (after REWRITE of product Threat path, DM integration suites remain)



Exact deleted-test count will be reported in the CODE→REVIEW handback.



## STOP conditions checked at ledger freeze



| Candidate | Decision |

|---|---|

| Threat Kernel fallback still required by mounted product | **No** — D.3A proved DM path; REWRITE removes latent import. |

| Graph Review still requires `graph_review_contribution_merge` Kernel merge | **No** — only self-test imports it; D.2C4 uses DungeonMind. |

| Recap ingest requires UnionSupergraphStore materialization | **REWRITE** fail-closed / non-store packaging; not STOP unless rewrite changes public wire contracts unexpectedly. |

| `latest_recap` Buddy head fallback | **REWRITE** fail-closed; do not edit #666 lease. |

| Storage-neutral contracts only inside engine trees | **None found** beyond types already rehomed under `apps/.../models/world_graph_*` or pending minimal DTO rehome from `union_supergraph.model` / `kernel.temporal` if a survivor still needs them — prefer DELETE of temporal_shadow consumers over rehoming temporal. |

| #666 collision | Avoided; STOP if unavoidable. |



## Packaging / entrypoints



`pyproject.toml` has **zero** hooks naming the retired packages at dispatch head.

