---
document_id: dmb-capability-inventory-c2s23
title: C2S23 Planning — Capability Inventory (Artifact Actions)
document_class: capability_inventory
status: active
version: 0.1
created_at: "2026-05-30T20:00:00Z"
---

# C2S23 Planning — Capability Inventory

Operational inventory for the first Session 23 dogfood round. **Status** meanings:

- **supported** — usable today through a documented entrypoint
- **partial** — exists but limited scope, stub behavior, or manual workaround required
- **unknown** — suspected plumbing; not verified for C2 dogfood
- **missing** — required for benchmark categories but no product path

**PR column** — recommended follow-up when missing or partial blocks dogfood (PR numbers per current activation roadmap slice, not historical L5 PR numbers).

---

## Ingestion and memory

| Capability | Status | Entrypoint / path | Authority lane | Evidence | Dogfood implication | If missing |
|------------|--------|-------------------|----------------|----------|---------------------|------------|
| Raw recap ingestion (stage/preview/apply) | supported | CLI: `src.live_play.recap_ingest_pipeline`; API: `apps/live_control_server/routes/recap_ingest.py` → `run_pipeline` | `pre_canonical_evidence` → `canon_play` | `tests/test_live_recap_ingest_pipeline.py`, `tests/test_live_recap_ingest_api.py` | Step 0: ingest S22 before S23 planning | — |
| Recap staging / apply / normalize | supported | Same orchestrator; operations `stage_preview`, `apply_normalize` | staged → canon recap → normalized | PR92/L5M status JSON | Operator must use non-generic slug/title on apply | — |
| Breadcrumb requirement boundary | supported | Pipeline stops at `breadcrumb_required`; status states + UI pane | normalized → `canon_play_prepared`; breadcrumb → `canon_play_routed` | `src/live_play/recap_ingest_status.py`, IngestionModule | Expected stop until breadcrumb blessed | — |
| Session memory materialization | supported | CLI `--materialize-session-memory`; API `materialize_session_memory` | `derived_memory` | Pipeline tests + materialize scripts | Only after breadcrumb exists | — |
| Recap/source session decoupled from live workspace | supported | `apps/live-control-ui/src/modules/IngestionModule.tsx` (recap session input) | — | `IngestionModule.test.tsx` | Plan S23 while ingesting S22 | — |
| LLM recap-write from pane | missing | Planner tools when `--allow-corpus-writes` only | — | — | Breadcrumb/recap prose still operator or IDE agent | PR96 (planner write UX) if needed at table |

---

## Live workspace and orientation

| Capability | Status | Entrypoint / path | Authority lane | Evidence | Dogfood implication | If missing |
|------------|--------|-------------------|----------------|----------|---------------------|------------|
| Live workspace bootstrap | supported | `src.live_play.session_bootstrap` CLI; `--write-current-live` | `planning_input` / `fresh_recap` until ingested | `tests/test_live_session_bootstrap.py` | Create `evals/c2_live_prep/live/session_23` | — |
| Plan-view timeline | supported | `GET /api/live/plan-view`; `src/live_play/projections/plan_view.py` | `planning_scaffold` + recap-derived beats | Timeline module | First orientation after bootstrap | — |
| Inspector artifact reads | supported | `GET /api/live/artifact`; `src/live_play/projections/artifacts.py` | varies by target | `tests/test_live_artifact_reads.py` | Deep-read roll tables, events, packets | — |
| Inspector capability reads | supported | `GET /api/live/capabilities`; `capability_registry.py` | — | Server tests | See what writes are offered per target | — |
| Chat / live query turn | partial | `POST /api/live/query`; `src/live_play/live_turn.py` | classifier only | `evals/c2_live_prep/run_session_22_classifier_benchmark.py` | Classifies intent; **does not run retrieval** for `context_question` | PR96 (wire context_lookup) |
| Context enrichment packet shape (live) | partial | `live_packet.context_packets` (often empty); C1S4 packet builders separate | mixed | `session_bootstrap.py`, C1S4 eval harness | No unified planning packet in live server yet | PR96 |
| Enable optional Ingestion module in layout | supported | `surface_layout.json` / `PUT /api/live/surface/layout` | — | PR93 schema + fixtures | Toggle `ingestion.enabled` | — |

---

## Writes and mutations (live-control)

| Capability | Status | Entrypoint / path | Authority lane | Evidence | Dogfood implication | If missing |
|------------|--------|-------------------|----------------|----------|---------------------|------------|
| Append observation | supported | `POST /api/live/commands` `append_observation`; Inspector UI | `live_observation` | `tests/test_live_command_bus.py` | Capture S23 prep notes; not S22 play canon | — |
| Roll-table read (registered) | partial | Artifact read when `known_roll_tables` populated | `reference_tool` | Bootstrap leaves list empty unless seeded | Dogfood must seed tables into packet | PR95 (bootstrap seeding) |
| Roll-table patch | supported | `patch_artifact` lane `prep_note`; preview-first UI | `reference_tool` / `audit` | `tests/test_live_artifact_patching.py` | Patch existing prep tables only | — |
| Roll-table creation | missing | No command/API to create new table file + register in packet | `reference_tool` | Runbook: empty `known_roll_tables` | Questions on new swamp/travel tables blocked | PR95 |
| Live command bus: NPC/location patch | missing | `patch_artifact` roll_table-only | — | `artifact_patching.py` | Cannot patch dossier/hub from pane | PR96 |
| Corpus write from live-control | missing | No pane route to `write_corpus_file` | `canon_play` / timelines | Planner-only with flag | Recap/timeline writes via IDE agent | PR96 |

---

## Corpus / hub actions (outside live-control pane)

| Capability | Status | Entrypoint / path | Authority lane | Evidence | Dogfood implication | If missing |
|------------|--------|-------------------|----------------|----------|---------------------|------------|
| NPC hub read | supported | Corpus tree + `read_corpus_file` (planner/IDE) | hub README, dossier, statblock | Conventions in `Docs/CONVENTION-NPC-Hub-Package.md` | Manual navigation for NPC questions | — |
| NPC hub write (timeline row) | partial | `append_timeline_row` / planner; not live pane | `canon_play` pointer | `src/agent/corpus_writer.py` allowlist | After recap exists; two-phase | PR96 for operator UX |
| NPC hub write (new hub / dossier) | partial | Allowlist: create README/timeline/dossier paths; dossier/statblock denied | — | `corpus_writer.py` | New NPC from S22 may need IDE agent | PR96 |
| Location hub read | supported | Corpus + plan-view `location` targets (read-only refs) | world/campaign hubs | `plan_view.py` location rows | Scene grounding | — |
| Location hub write | partial | Allowlist: `Elderwyld/Locations/<file>.md` create | world reference | `corpus_writer.py` | New location markdown via planner, not pane | PR96 |
| Town / economy prep note | partial | `Session Prep/*.md` append allowlist | `planning_scaffold` | `corpus_writer.py` `_PREP_SESSION_APPEND_RE` | Consolidate prep notes; no live pane | PR96 |
| Route equivalence create/update | partial | `src/lexicon_phase_b/route_equivalence_manifest.py` (offline manifest build) | normalization | Lexicon tests | Spelling/route review post-ingest; not in live UI | PR95 (operator workflow) |
| Breadcrumb bless / generate | partial | Existing content ops + scripts; not PR93 pane | `canon_play_routed` | Materialize gate in pipeline | Manual step between apply and memory | Document in runbook only |

---

## Activation and retrieval

| Capability | Status | Entrypoint / path | Authority lane | Evidence | Dogfood implication | If missing |
|------------|--------|-------------------|----------------|----------|---------------------|------------|
| Manifest-like source activation | missing | Planned PR92 in roadmap (not this PR) | role + authority per source | `ROADMAP-c2s23-authority-activation-and-dogfood.md` | Cannot answer “query all relevant S23 sources” in one pass | **PR95** |
| Retrieval over ingested context (live) | missing | `context_lookup` stub in `live_turn.py` | `derived_memory`, hubs | diagnostic `context_lookup_not_executed_in_L2` | Chat will not ground NPC/scene answers | **PR96** |
| Retrieval smoke (offline) | supported | `evals/c2_live_prep/smoke_retrieval_packets.py` | session memory JSONL | C2S22 artifact runs | Use for comparison only; not wired to live UI | — |
| Session memory query (library) | supported | `src.agent.session_memory_query` | `derived_memory` | Used by C1S4 / smoke scripts | Manual or script-assisted recall | PR96 to expose in live |

---

## Benchmark artifacts (this PR)

| Capability | Status | Entrypoint / path | Evidence |
|------------|--------|-------------------|----------|
| C2S23 dogfood question seed | supported | `evals/c2_live_prep/benchmarks/c2s23_dogfood_questions.seed.json` | This PR |
| Manual baseline template | supported | `evals/c2_live_prep/benchmarks/c2s23_manual_baseline.template.md` | This PR |
| Automated scoring / gold | missing | — | Intentionally deferred |

---

## Summary for dogfood

**Ready today:** S22 ingest (CLI or pane), S23 bootstrap, timeline, inspector reads, append observation, roll-table patch on **existing** registered tables, manual corpus navigation.

**Blockers for full benchmark categories:** activated manifest (PR95), live retrieval / context packets (PR96), roll-table creation + packet seeding (PR95), unified operator writes for hubs/prep (PR96).

Update this table after the first manual baseline if friction reveals misclassified statuses.
