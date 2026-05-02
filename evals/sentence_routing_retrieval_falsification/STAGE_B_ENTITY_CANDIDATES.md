# Stage B — session entity candidates (Stage 1 hook)

## Goal

Give B1 optional **soft anchors** for session NPC strings and location-like phrases so the model can prefer `missing_entity_bucket` placeholders instead of leaking manifest PCs or expanding parties on abstain rows.

This does **not** add NPC or location hubs to the PC-only manifest: [`discourse_reducer.py`](discourse_reducer.py) still routes only manifest PC slugs from PC role fields unless `the_party` expansion applies.

## Contracts

### Recap frontmatter (YAML-ish, between `---` fences)

Optional keys (comma-separated or `[a, b]` lists), parsed by [`session_entity_candidates.py`](session_entity_candidates.py):

- `session_npc_candidate_names:` — free-form NPC labels / aliases for substring hints.
- `session_location_candidate_names:` — place anchors (town regions, landmarks, generic scene nouns used as focal subjects).

### Scenario `input` JSON

- `session_entity_candidates`: `{ "npc_names": [...], "location_names": [...] }` (also accepts `*_labels` synonyms).
- Optional flat duplicates: `session_npc_candidate_names`, `session_location_candidate_names` (lists merge).

Merged lists are exposed on **`routing_context`** as:

- `session_npc_candidate_names`
- `session_location_candidate_names`

### B1 prompt rule

[`discourse_prompt.py`](discourse_prompt.py) instructs substring match (case-insensitive) when those routing_context arrays are non-empty. They are **disambiguation hints only**; `narrow_pc_only` and per-unit `active_scene_owner_hubs` still win.

### Future B1 schema (not implemented)

Optional structured outputs on [`DiscourseRow`](discourse_schema.py) such as `npc_candidate_labels` / `location_candidate_labels` would let graders separate **PC-role errors** from **entity tagging**. That requires API schema + reducer/Gold updates.

## Harness — ablation merge

[`step2_discourse_pipeline_run.py`](step2_discourse_pipeline_run.py):

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_discourse_pipeline_run \
  --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc.json \
  --session-entity-candidates-json evals/sentence_routing_retrieval_falsification/fixtures/session20_entity_candidates_ablation.json \
  --n 5
```

Fixture augments Session 20 with extra NPC tokens (`mayor`, `sheriff`) and coarse location nouns used in the recap.

## Post–Caelynn baseline (N=5, gpt-5.4-mini)

Recorded **2026-05-02** after Caelynn rubric/context updates:

| Cohort | Summary artifact |
| --- | --- |
| Full C2 | `artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc--gpt-5.4-mini--N5--20260502T024253Z.json` |
| Edge H1/H2 | `artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc_edge_slice_h1_h2_sentinel--gpt-5.4-mini--N5--20260502T024420Z.json` |

Baseline cohort aggregates (full C2 summary JSON):

- **`cost_usd.sum`**: `0.255888` (mean `0.051178`)
- **`cohort_unit_failure_events.distinct_failure_unit_ids`**: 21 units (union across runs / buckets in that summary).
- **`cohort_b1_content_failure_events.distinct_failure_unit_ids`**: `u-L0018-02`, `u-L0026-06`

## Ablation cohort (entity-candidate fixture)

After running the `--session-entity-candidates-json` command above (same model/`n`):

- **Ablation full C2**: `artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc--gpt-5.4-mini--N5--20260502T141720Z.json`
- **Ablation edge H1/H2**: `artifacts/runs/2026-05-02/sentence_routing_stage_b_discourse_pipeline_summary--sentence_routing_c2_session20_pc_edge_slice_h1_h2_sentinel--gpt-5.4-mini--N5--20260502T141757Z.json`

## Decision gate — isolated NPC pass?

**Prefer an isolated NPC / location resolution pass** when either holds:

1. Ablation does **not** materially shrink `b2_over_assigned` / `b1_over_route` driven by “ambient NPC + accidental PC hub” confusions **and** B1-content flakes (`discourse_mode`, mixed direct/topic) stay dominant → core issue is **discourse role modeling**, not entity inventory.
2. You need **retrieval targets beyond manifest PCs** (NPC hubs, location dossiers). Candidates belong in Stage 1 output consumed by that pass; B1 should stay PC-thread classification only.

**Keep tightening B1 + deterministic coherence** when:

1. Ablation shows **clear bucket drops** (especially `b2_over_assigned` on NPC-led abstain rows) **without** new `b1_missing_expected_hub` regressions on must_route PCs.
2. Failures remain **`b2_reducer_* = 0`** (B1-state attribution only) but are tied to missing continuity cues fixable by harness/context rather than new hubs.

**Empirical verdict:** explicit Stage 1-style entity candidates improve B1 but do not eliminate
the remaining abstain leakage. Keep the candidate surface, stop broad prompt tuning, and move
NPC/location retrieval targets into an isolated pass once those hubs are in scope.

## Ablation results (filled post-run)

- **Full C2 cost:** `0.254735` sum / mean `0.050947`, slightly below baseline `0.255888` / `0.051178`; **no cost regression**.
- **Full C2 pass rate:** unchanged at `0/5`.
- **Full C2 B1 content:** improved from two distinct units (`u-L0018-02`, `u-L0026-06`) to one (`u-L0026-06`), but `u-L0026-06` still fails role separation in some runs.
- **Full C2 B2 unit buckets:** distinct failing units improved `21 → 15`; `b1_missing_expected_hub` improved `6 → 2`; `b1_over_route` improved `7 → 3`; `b2_over_assigned` regressed slightly `9 → 10`.
- **Edge cost:** `0.032244` sum / mean `0.006449`, below baseline `0.035703` / `0.007141`; **no cost regression**.
- **Edge pass rate:** improved `2/5 → 3/5`, but distinct over-assigned abstain units regressed `1 → 2` (`u-L0028-07`, `u-L0030-06`).

Interpretation: the candidate list acts as useful negative/placeholder evidence for B1, but it does
not solve the cases where B1 decides an ambient NPC/location beat should inherit a PC or party.
Those remaining cases are better handled by a separate NPC/location pass or deterministic
post-B1 suppression rules than by adding more prose to the B1 prompt.
