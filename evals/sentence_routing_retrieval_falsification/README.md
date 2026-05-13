# Sentence routing and retrieval falsification (scaffold)

Companion plan: `Docs/Plans/EXPERIMENT-Sentence-Routing-Retrieval-Falsification.md`
Operational guardrails: `Docs/Plans/GUARDRAILS-Sentence-Grounded-Ingestion-Vision.md`

## Pipeline steps (read this first)

**Explicit names** (what each step is for) and **legacy letter labels** (still used in filenames and JSON keys for compatibility):


| Explicit name                               | Legacy | What it does                                                | Run with                                                                     | Dated artifact filename                                                        | Last-run mirror (under `artifacts/`)               |
| ------------------------------------------- | ------ | ----------------------------------------------------------- | ---------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | -------------------------------------------------- |
| `**capture_sentence_units`**                | A      | Deterministic **sentence-unit capture** from recap markdown | `python -m evals.sentence_routing_retrieval_falsification.step1_capture_run` | `sentence_routing_stage_a_capture--<scenario>--<PASS_or_FAIL>--<UTC>.json`     | `last_sentence_routing_stage_a_capture.json`       |
| `**route_sentence_units_to_hubs`**          | B      | **Hub routing** (each unit → allowed hub slugs)             | `python -m evals.sentence_routing_retrieval_falsification.step2_route_run`   | `sentence_routing_stage_b_hub_routes--<scenario>--<PASS_or_FAIL>--<UTC>.json`  | `last_sentence_routing_stage_b_hub_routes.json`    |
| `**route_sentence_units_to_hubs` (cohort)** | B      | Repeat routing **N** times; aggregate pass rate + cost      | same module + `--n <N>` (N>1)                                                | `sentence_routing_stage_b_cohort_summary--<model>--N<n>--<UTC>.json` (+ `.md`) | (stderr lists paths; no mirror file)               |
| `**propose_new_hubs_from_unmapped_units`**  | C      | New-hub proposals (planned)                                 | `step3_propose_run.py` (TBD)                                                 | `sentence_routing_stage_c_hub_proposals--…`                                    | `last_sentence_routing_stage_c_hub_proposals.json` |
| `**assemble_hub_scoped_retrieval_context`** | D      | Scoped **retrieval context pack** (planned)                 | `step4_retrieval_pack_run.py` (TBD)                                          | `sentence_routing_stage_d_context_pack--…`                                     | `last_sentence_routing_stage_d_context_pack.json`  |


Module filenames keep the historical `step1_`* / `step2_`* pattern so `python -m` invocations stay stable; **artifact names** use the explicit `sentence_routing_stage_`* prefix.

**Gold stability (historical sidecars):** `python -m evals.sentence_routing_retrieval_falsification.stage_b_gold_stability --scenario-json <gold>.json --sidecar-glob '<glob>'` classifies each `must_route` / `must_abstain` row into **stable_pass** (passed every run), **stable_fail** (failed every run), or **flaky**, and checks **sentence_units** signatures across inputs. Use this to split a cheap always-green baseline from edge-only cohorts. `**--emit-edge-scenario PATH`** writes a new scenario whose gold is **only the flaky rows** (drops `fixture_routes`). `**--violations-aggregate-only`** with a glob over fresh sidecars prints/ writes `sentence_routing_stage_b_violation_aggregate_v1` (raw + collapsed violation-line counts, per-run telemetry slices).

## What exists today

- `**capture_sentence_units` (A):** `capture.py` splits recap lines into `sentence_units` with 1-based line addresses; `step1_capture_run.py` writes capture sidecars.
- `**route_sentence_units_to_hubs` (B):** `route_schema.py` (manifest + `sentence_hub_routes_v1`); `grader.py` (`normalize_gold_routing_matches`, `collect_stage_b_violations`); `step2_route_run.py` (OpenAI or `--no-llm` + `fixture_routes`; `--n` for cohort summaries via `sentence_routing_stage_b_cohort_report.py`). For recaps under `…/<Campaign>/Session Recaps/`, the runner loads `<Campaign>/_party_registry.json` (`schema: party_registry_v1`, `pc_party_names`) when `campaign_id` matches, and merges optional `input.pc_party_names` (harness-only extras/overrides). When the manifest is PC-only, the model user JSON also includes `routing_context.pc_roster_slugs` in manifest order so joint-band routing is a copy operation, not a prose-name inference. These fields are **not** gold; omit them when unnecessary. Sidecar `telemetry.stage_b_unit_breakdown` reports **sentence_unit** totals, **gold must_route / must_abstain** pass–fail counts (one gold row = one check), and **B0–B2 violation-line buckets**; cohort summaries copy that object onto each `runs[]` entry for Markdown expansion.
- **Stage B split pipeline + entity-candidate ablation:** `step2_discourse_pipeline_run.py` (B1 discourse → deterministic B2). Optional `--session-entity-candidates-json` merges Stage 1–style candidate lists into `routing_context` (`session_npc_candidate_names`, `session_location_candidate_names`). See `STAGE_B_ENTITY_CANDIDATES.md`.
- `**propose_new_hubs_from_unmapped_units` / `assemble_hub_scoped_retrieval_context` (C–D):** stubbed in grader telemetry until gold + runners exist.

## Run

`**capture_sentence_units` (A) — capture:**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run
```

`**route_sentence_units_to_hubs` (B) — hub routing (offline, CI-safe):** uses `fixture_routes` in `gold/scenario_mini.json`:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --no-llm
```

`**route_sentence_units_to_hubs` (B) — cohort (e.g. N=3, still offline with fixture):**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run --n 3 --no-llm
```

**Split Stage B (optional proving slice):** B1 classifies units to `sentence_discourse_state_v1` (`step2a_discourse_run.py`; `--no-llm` uses `fixture_discourse`). B2 runs the deterministic discourse→routes reducer then the same Stage B gates as the monolith (`step2b_route_from_discourse_run.py`; reads `fixture_discourse` or `--discourse-json` pointing at a B1 sidecar’s `discourse_envelope`). `step2_discourse_pipeline_run.py --n <N>` runs B1+B2 cohorts and writes `sentence_routing_stage_b_discourse_pipeline_summary--…json/md`. Artifacts: `sentence_routing_stage_b1_discourse--…json` / `last_sentence_routing_stage_b1_discourse.json`, `sentence_routing_stage_b2_from_discourse--…json` / `last_sentence_routing_stage_b2_from_discourse.json`. Smoke scenario: `gold/scenario_discourse_smoke.json`.

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2a_discourse_run --no-llm
uv run python -m evals.sentence_routing_retrieval_falsification.step2b_route_from_discourse_run
uv run python -m evals.sentence_routing_retrieval_falsification.step2_discourse_pipeline_run --n 3
```

**NPC-first PC routing context (experiment):** optional `--build-npc-first-context` runs Stage A once (`run_session_events_extraction`), writes `npc_attachment_context_v1--…json`, merges `routing_context.npc_first_context` onto overlapping sentence units, and can pair with `--prompt-variant npc_first_context_v1`. Use `--npc-first-context-json PATH` to load a sidecar instead of rebuilding. Optional `--npc-first-timeline-gold PATH` supplies NPC append vs skip alignment from a timeline-pass grading JSON (`grading.expected_appends` / `expected_skips`, NPC `/NPCs/` rows only). Cohort summary JSON/Markdown includes `npc_first_context_build_cost_usd` (Stage A only; **not** included in `runs[].cost_usd`) and `cohort_npc_first_context` (B2 failures split by units that received NPC-first enrichment vs not).

Control vs treatment (example Session 19 holdout):

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.stage_b_preflight --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session19_pc.json --corpus-root .
uv run python -m evals.sentence_routing_retrieval_falsification.step2_discourse_pipeline_run --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session19_pc.json --n 5
uv run python -m evals.sentence_routing_retrieval_falsification.step2_discourse_pipeline_run --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session19_pc.json --n 5 --prompt-variant npc_first_context_v1 --build-npc-first-context
```

**Inline recap breadcrumbs (Step 1 session memory index experiment):** `manual_labels/Session 20 - Recap.breadcrumbed.md` is the original manual baseline retrieval index for Session 20. Treat it as a machine-facing source-aligned memory surface, not a readable recap replacement. The canonical recap remains the prose artifact; breadcrumbs are for agentic planning/live-play retrieval, hub routing, unresolved-thread capture, and dry-run corpus update proposals. **Session 20 natural + planner-discovery gold** (`gold/breadcrumb_query_natural_v1.json`, `gold/breadcrumb_query_planner_discovery_v1.json`) expects indexed breadcrumbs over the **normalized** recap path `Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 20 - Gnat Swarm Marla Lysandra.md` (use a frontmatter seed with matching `source_recap_path`, e.g. `manual_labels/Session 20 - Gnat Swarm Marla Lysandra.normalized.breadcrumbed.frontmatter_seed.md`). For new validation work, prefer the routing-only path (`--ingest-routing-only`): recap prose + thin route allowlist frontmatter seed -> structured route assignments -> deterministic breadcrumb renderer.

**Normalized recap surface (gold authors):** `_normalized/` bodies intentionally omit pre-`## Recap` GM prep (examples: `## Major Beats`, `## Next Beats`, `## Loot`, `## Into the Sewer`, Looking Ahead blocks). Do not assert retrieval against text that exists only in those dropped sections when `source_recap_path` points at `_normalized/`. Policy and a concrete C1S13 example: `Docs/CONVENTION-Session-Recap-Normalization.md` (section 6, *Intentionally dropped pre-recap chrome*).

**Current direction (2026-05-03):** the benchmark harness is the primary path for this
use case. The lexical/event-keyword retrieval path is good enough on the known Session
20 slice to keep expanding it; planner-discovery remains useful as a diagnostic
comparator, but it is set aside as the main implementation path until the benchmark
harness proves or falsifies cross-session generalization.

### Routing-only cross-session baseline (2026-05-08)

Current best baseline for the autonomous-learning direction is the four-lane
routing-only refresh over C1S1, C1S2, C1S3, and C1S13. These runs use
`--ingest-routing-only --retrieval-only`; they do not synthesize final answers.

| Lane | Report | Pass shape | Classification |
| --- | --- | --- | --- |
| C1S1 | `artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s1_routing_refresh_retrieval_only.json` | 14/16 | roster sentence retrieves, but individual PC routes are under-tagged |
| C1S2 | `artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s2_routing_refresh_retrieval_only.json` | 15/15 | clean current control lane |
| C1S3 | `artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s3_routing_refresh_retrieval_only.json` | 12/13 | location hierarchy gap: Grishna is routed via `rivers_edge_pub`, not same-unit `stonebridge` |
| C1S13 | `artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s13_routing_refresh_retrieval_only.json` | failing holdout | alias/identity bridge regression: `draven` dropped from the necromancer kill unit |

**Cost:** routing-refresh cohort sum was about `$0.136347`:
C1S1 `$0.021429`, C1S2 `$0.012705`, C1S3 `$0.046594`, C1S13
`$0.055619`. C1S13 was about +6.8% vs prior routing-only (`$0.052079`),
so this is not a cost regression.

Interpretation rules:

- Do not collapse this into `2/4 lanes failed`. The current value is that each
  remaining failure has a distinct, local mechanism.
- C1S1 is a routing generator gap for explicit roster/identity-bundle sentences.
- C1S3 is a query-contract/design gap unless we deliberately decide parent-location
  tags should be redundantly emitted on sublocation facts.
- C1S13 is a true routing-only regression vs the prior routing-only sidecar and needs
  alias/identity-bridge protection.
- Any change to routing prompt/defaults should add sentinels for these failure families
  and rerun this four-lane refresh before promotion.

The deterministic smoke harness parses frontmatter and body inline tags, validates tag vocabulary and route existence, compares generated artifacts against the manual baseline by exact `(tag_type, route)` multiset precision/recall, and dry-runs PC/NPC `append_timeline_row(..., dry_run=True)` previews where routed hubs expose `timeline.md`:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_smoke
```

Rubric anchor:

- Hard gates: parseable frontmatter/schema, allowed tag types only, existing routes resolve, proposed routes are explicit, body tags attach to source-derived spans, PC/NPC routes are dry-run routable or skipped with a surfaced reason.
- Diagnostics: baseline precision/recall, tag density by type, Party over-routing, open-loop / `NewHubCandidate` capture, missing/invented route families, append dry-run success/skips/failures.
- End goal: sampled planning/live-play questions should retrieve the right source spans and hub routes without rereading the whole recap.

**Pronoun-resolution breadcrumb experiment:** use this when testing whether ingest can
resolve pronoun-led durable units and make those units retrievable without gold aliases
or query-specific cheats.

### Objective and tradeoff framing (non-optional)

Treat this path as a layered objective:

1. retrieval evidence reachability (unit/route constraints),
2. answer quality (LLM semantic/context),
3. cost envelope.

Do not accept "better pronoun recall" if it causes lexical flooding that displaces
high-signal units or spikes LLM incompleteness failures.

### Practical targeting strategies

When tuning pronoun enrichment, prefer these over broad lexical expansion:

- **compact entity handles:** append only entity-leaf tokens (for example, `captain lysandra ironveil`), never full route paths,
- **class scoping:** enrich PC/NPC/Party lines first; avoid location-family spray unless explicitly needed,
- **missing-term gating:** only append handles not already present in the line text,
- **hard cap:** keep appended handle terms bounded per record.

```bash
# Gate 1: can a prompt variant attach entity routes to pronoun-led units?
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_tagging_variant_runner \
  --variant pronoun_resolution_v1 \
  --sentinels evals/sentence_routing_retrieval_falsification/gold/breadcrumb_pronoun_resolution_sentinels_session20.json \
  --n 3

# Gate 2: does route-handle enrichment improve target-unit rank?
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_rank_report \
  --breadcrumb-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md" \
  --corpus-root corpus/eldyrwild-markdown \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_pronoun_rank_baseline_report.json

uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_rank_report \
  --breadcrumb-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md" \
  --corpus-root corpus/eldyrwild-markdown \
  --pronoun-route-handles \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_pronoun_rank_enriched_report.json

# Gate 3: does the enriched retrieval improve natural-query output quality?
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --breadcrumb-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 20 - Recap.breadcrumbed.md" \
  --corpus-root corpus/eldyrwild-markdown \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json \
  --pronoun-route-handles \
  --semantic-similarity \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_pronoun_handles_report.json
```

**Planner discovery vs JSONL retrieval (set aside as primary path):** `breadcrumb_query_planner_discovery_run.py` runs one live planner turn per natural gold scenario with `user_line` equal to the scenario `question` (no fixture provisioning). It logs corpus path tools from `tool_trace`, compares coverage against benchmark gold `expect_route_substrings` (JSONL retrieval rubric) and against routes from benchmark retrieval hits, scores **planner-facing opens** separately via `gold/breadcrumb_query_planner_discovery_v1.json` (`expected_open_paths` path substrings), grades the planner `message` with the same retrieval bundle as the harness (LLM gates conditioned on benchmark retrieval), and writes `artifacts/runs/<date>/breadcrumb_query_planner_discovery_report.json` plus `artifacts/last_breadcrumb_query_planner_discovery_report.json`. Use this as a diagnostic comparator for "what would the planner seek when the benchmark says context is insufficient?", not as the main path for the current lexical/event-keyword retrieval work. Use `--skip-benchmark-llm` to omit harness synthesis calls; use `--planner-session-memory-records PATH` (file must exist before the run — reuse a JSONL from `--breadcrumb-md` / `--records-jsonl`) to expose `query_session_memory` during the planner turn (ablation).

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_discovery_run \
  --records-jsonl evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/<stem>.jsonl \
  --corpus-root corpus/eldyrwild-markdown \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json \
  --planner-discovery-gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_planner_discovery_v1.json \
  --skip-benchmark-llm \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_planner_discovery_report.json

# Session-memory ablation (same JSONL as grading records)
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_planner_discovery_run \
  --records-jsonl evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/<stem>.jsonl \
  --planner-session-memory-records evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/<stem>.jsonl \
  --corpus-root corpus/eldyrwild-markdown \
  --skip-benchmark-llm \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_planner_discovery_session_memory_ablation_report.json
```

Compare Gate 3 cost and pass/fail against the current post-location baseline report
(`breadcrumb_query_natural_llm_semantic_expanded_report.json`; latest measured single
run cost: `$0.0640`).

### Required execution loop for retrieval changes

Any retrieval-affecting pronoun change should run this loop in order:

1. implement compact+targeted enrichment,
2. run Gate 2 baseline vs enriched rank report,
3. audit failing gate families (retrieval expectation vs LLM synthesis gaps),
4. run Gate 3 and report pass delta + violation-family delta + cost delta vs baseline.

### Natural gold LLM lane (cohort acceptance)

For `gold` schema `dmb_breadcrumb_query_natural_gold_v1`, any change that can move LLM synthesis or semantic gates (prompt edits, token-resolution cutovers, synthesis model swaps) should be accepted only after **three** identical `breadcrumb_query_run` invocations on the same records + gold. Report each run’s per-scenario pass count, failing `scenario_id`s, and `scenario_estimated_cost_usd`, then summarize **min / mean / max** cost across the three runs. Single-run PASS/FAIL is not a reliable signal for LLM-gated rows.

Benchmark-only semantic equivalence seeds and the frozen legacy route-stopword list used for shadow diffs live in `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/benchmark_lexicon_seeds_v1.json`. Override the path with env `DMB_BENCHMARK_LEXICON_SEEDS` when you need a fork-local copy.

#### Route equivalence manifests (Phase B)

Route-equivalence lexical artifacts are written to `evals/sentence_routing_retrieval_falsification/artifacts/lexicon/` as committed JSONL outputs for Campaign 1 and Campaign 2. Filenames follow `route_equivalence_<campaign_id>_v1.jsonl` (for example `route_equivalence_longmont_c1_v1.jsonl`).

Artifact records are built by `src/lexicon_phase_b/route_equivalence_manifest.py` and emitted through its deterministic JSONL writer. Use `uv run python scripts/build_route_equivalence_manifests.py --check` for CI-style byte checks and `uv run python scripts/build_route_equivalence_manifests.py --write` to regenerate canonical files.

Determinism is enforced with `tests/lexicon_phase_b/test_route_equivalence_artifacts_byte_stable.py`, which compares fresh builds to committed artifacts byte-for-byte and pins critical schema fields.

##### Shadow consumption (Phase C entry)

Pass `--route-equivalence-jsonl` (repeatable) to `breadcrumb_query_run` to load
the committed `route_equivalence_*_v1.jsonl` artifacts as a shadow diagnostic.
Each natural-gold scenario row gains a `shadow_route_equivalences` field with
schema `dmb_route_equivalence_shadow_v1`: edge counts, the full set of campaign
IDs present, and the source paths in input order. **Shadow-only:** retrieval,
grading, and the existing `shadow_token_resolution` field are unchanged; legacy
lexical seeds remain the active source. The field is omitted entirely when the
flag is unset (default runs remain byte-identical to current main).

When `--use-route-equivalence-for-ranking` is enabled, alias injection is
intentionally conservative: only compact entity aliases are considered (display
names plus final route handle), structural tokens like `route`, `campaign`,
`npc`, `longmont`, `c1`, and `c2` are never injected from route IDs, and a
record contributes aliases only when the scenario’s natural query text already
mentions at least one token from that record. This safety baseline prevents
manifest-wide alias injection and does not implement first-pass-route
activation.

Example:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --records-jsonl corpus/eldyrwild-markdown/Longmont\ Campaign/Campaign\ 1/Session\ Recaps/_session_memory/Session\ 01\ -\ Stonebridge\ and\ Glowkindle\ Rats.records_meta.jsonl \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json \
  --retrieval-only \
  --route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c1_v1.jsonl \
  --route-equivalence-jsonl evals/sentence_routing_retrieval_falsification/artifacts/lexicon/route_equivalence_longmont_c2_v1.jsonl
```

Example 3-run acceptance loop (records JSONL):

```bash
for i in 1 2 3; do
  uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
    --records-jsonl corpus/eldyrwild-markdown/Longmont\ Campaign/Campaign\ 1/Session\ Recaps/_session_memory/Session\ 01\ -\ Stonebridge\ and\ Glowkindle\ Rats.records_meta.jsonl \
    --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s1_v1.json \
    --output "/tmp/c1s1_records_jsonl_smoke_${i}.json"
done
```

### Next-session generalization gate

Before treating the breadcrumb/query harness as ready for an autonomous learning loop,
prove that it expands beyond Session 20:

1. Drop in a fresh recap as the source artifact and generate a sibling breadcrumb/index
   artifact with the same schema and tag vocabulary.
2. Add natural-query gold whose answers require facts introduced by that recap, not
   recycled Session 20 facts.
3. Run `breadcrumb_query_run` from the generated JSONL records; record retrieval pass,
   semantic pass, violation families, and cost.
4. Audit the JSONL and report for hardcoding: no query-specific aliases, no preloaded
   expected paths, no Session 20-only route handles, and no hand-seeded records outside
   the generated index.
5. Only then promote the path toward an autonomous loop. If the holdout fails, the next
   fix belongs in index generation or lexical/event-keyword extraction, not in
   planner-discovery prompt tuning.

The 2026-05-08 C1S1/C1S2/C1S3/C1S13 sweep is the current concrete instance of this
gate. Treat C1S2 as the clean control, C1S1 as roster/identity-bundle coverage, C1S3
as location-entity hierarchy pressure, and C1S13 as alias/identity-bridge pressure.
Future changes should report pass deltas for those named lanes and classify any
remaining failures by mechanism, not only by `all_ok`.

**Real-recap scaffold:** `gold/scenario_real_recap_template.json` — runnable default (mini fixture); copy and set `input.recap_relative_path` + `hub_manifest` + `gold_`* after GM approval (see `scenario_notes` in file).

`**route_sentence_units_to_hubs` (B) — hub routing (live LLM):** requires `OPENAI_API_KEY` after `load_dungeonmindbuddy_dotenv()`; model defaults to `DUNGEONMIND_PLANNER_MODEL` or `gpt-5.4-mini`. Chain from the capture mirror file:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step1_capture_run
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \\
  --prior-json evals/sentence_routing_retrieval_falsification/artifacts/last_sentence_routing_stage_a_capture.json
```

## Fixture + gold

- `fixtures/mini_recap.md` — tiny synthetic recap (no corpus PII).
- `gold/scenario_mini.json` — `gold_capture`, `input.hub_manifest`, `gold_routing`, `fixture_routes` for `--no-llm`.
- `gold/scenario_discourse_smoke.json` — embedded `sentence_units`, `fixture_discourse`, `gold_discourse`, `gold_routing` for split Stage B (`step2a_discourse_run` / `step2b_route_from_discourse_run`; `--no-llm` on B1).
- `gold/scenario_real_recap_template.json` — same shape with `gold_routing` using **match** rows (DESIGN §6.5); replace paths for a pinned corpus recap when promoting.
- `gold/scenario_c1_session1_pc.json`, `gold/scenario_c1_session2_pc.json`, `gold/scenario_c1_session3_pc.json`, `gold/scenario_c2_session20_pc.json` — real-recap **PC-only** routing gates for `**route_sentence_units_to_hubs` (B)** (manifest = that campaign’s PC hubs only). Semantics:
  - **must_route:** any PC named or clearly implicated as actor, object, addressee, rescuer, or **affected party** in the unit must appear in `expected_hubs` (subset of model `assigned_hubs`). After the roster is established, party-wide beats that say **the team** / **teammates** in a fight or job, or **first combat** + **team**, may **must_route all PCs**; **the group** may **must_route all PCs** when the PCs are the joint subject of movement or approach in that unit—otherwise vague **the group** framing stays **must_abstain** (see `scenario_c1_session1_pc.json` `scenario_notes`).
  - **Pronoun / continuation:** when the prior narrative focal names a PC and the unit is clearly the same beat, gold may **must_route** that PC even if the surface text is pronoun-heavy (see per-scenario `scenario_notes` + `fixture_routes`).
  - **must_abstain:** `max_assigned_hubs: 0` keeps the model from attaching recap beats to PC hubs when no PC belongs there. For **named NPCs/locations not in the manifest**, do **not** require `needs_new_hub_candidate: false` — the runner does not treat `candidate: true` as a B2 failure by itself; purely generic rows still pin `needs_new_hub_candidate: false` for abstain pressure.
- `gold/scenario_rule3_locus_line16.json` — **narrow slice:** top-level `sentence_units` = Session 20 recap **line 16 only**, same manifest as C2 Session 20; gold is the base scenario’s `must_route` / `must_abstain` for that line (cheap check for rule 3 vs rule 6 around **u-L0016-03**). `--no-llm` works without `--prior-json`. Live LLM run (requires key):

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \\
  --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_rule3_locus_line16.json \\
  --corpus-root . --n 5
```

## Hypothesis 1 (H1) — party vs generic group vs named PCs

Tool module: `[h1_routing_evidence.py](h1_routing_evidence.py)`. It classifies `violations.stage_b` strings into buckets (`named_pc_omission`, `party_reference_boundary`, `pronoun_carryover`, `out_of_manifest_candidate`, `schema_row_integrity`), prints an automated **ACCEPT_H1 / REJECT_H1 / INCONCLUSIVE** verdict from aggregate counts, and emits a **directional scorecard** (alongside binary PASS/FAIL): `named_pc_recall`, `party_boundary_precision` (generic-`group` abstain rows with no party keywords), `candidate_sanity` (gold-pinned `needs_new_hub_candidate: false` rows satisfied).

```bash
# Historical FAIL PC sidecars under artifacts/runs
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence scan-artifacts

# One run: violations + scorecard (needs matching scenario gold JSON)
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence scorecard \\
  --sidecar evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/sentence_routing_stage_b_hub_routes--....json \\
  --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c1_session1_pc.json

# After a `route_sentence_units_to_hubs` cohort (--n 5): per-cohort bucket merge, then merge all cohort summaries
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence summarize-cohort \\
  evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/sentence_routing_stage_b_cohort_summary--<model>--N5--....json

uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence aggregate-summaries \\
  path/to/cohort1.json path/to/cohort2.json path/to/cohort3.json path/to/cohort4.json

# Matrix v2.1 threshold check (uses artifacts/h1_thresholds_v2_1.json by default)
uv run python -m evals.sentence_routing_retrieval_falsification.h1_routing_evidence check-thresholds
```

## Stage B failure hypotheses (2026-04-27)

Current focus: C2 Session 20 PC-only routing, especially `gold/scenario_c2_session20_pc_edge_flaky48.json`. **Set aside `u-L0016-03` during this pass**; it has stayed a stable B1 miss across prompt variants and should not dominate the next experiment.

The working rule for new changes: judge **B1 missing expected hub** and **B2 over-assigned abstain** separately. A change that lowers B1 by increasing B2 is not a net fix unless the affected gold rows are first adjudicated as wrong.

### H2 — named-PC recall and abstain precision are in tension

Broad "include named / affected PCs" language can improve multi-PC `must_route` rows while causing B2 over-routing on NPC, object, location, and pronoun-heavy `must_abstain` rows.

**Test:** For every prompt or rubric change, compare:

- `telemetry.stage_b_unit_breakdown.violation_failure_buckets.b1_missing_expected_hub`
- `telemetry.stage_b_unit_breakdown.violation_failure_buckets.b2_over_assigned`
- total `gold_gate_checks_pass`

Acceptance is bucketed: B1 should fall without B2 exceeding the prior baseline for the same scenario and sample size.

**Result (2026-04-28 bucket sentinel):** diagnostic buckets helped the abstain side but did not solve recall. Default bucketed prompt on `scenario_c2_session20_pc_bucket_sentinel` N=3 (`.../sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--N3--20260428T164441Z.json`) had **B2 over-assignment 0/3 runs**, but still failed **B1 party recall** with `b1_missing_expected_hub` = 2, 2, 3. Cost: **$0.013699** sum, mean **$0.004566**.

**Result (2026-04-28 party_continuation_v1):** opt-in party continuation improved that same bucket sentinel (`...--pv-party_continuation_v1--N3--20260428T164939Z.json`) to **2/3 PASS**, with B1 missing = 1, 0, 0 and **B2 over-assignment still 0/3**. Cost: **$0.016597** sum, mean **$0.005532** (**+21% vs default same-scenario cohort**, below the 1.5x cost-regression threshold). However, the broader H1/H2 mixed sentinel (`...edge_slice_h1_h2_sentinel...--pv-party_continuation_v1--N3--20260428T165019Z.json`) stayed **0/3 PASS**: B2 remained 0, but `u-L0026-06` and `u-L0030-03` still failed B1, with one run over-routing `u-L0026-06` to the full roster. Do not promote this variant as default on this evidence.

**Result (2026-04-28 slice matrix):** party-continuation remains a partial lever, not a fix. On `scenario_c2_session20_pc_edge_slice_party_boundary`, default N=3 was **0/3 PASS** with B1 missing = 6, 6, 6 and B2 = 0 (`...--N3--20260428T165636Z.json`, cost **$0.020295**); `party_continuation_v1` improved to B1 missing = 3, 2, 2 with B2 still 0 but remained **0/3 PASS** (`...--pv-party_continuation_v1--N3--20260428T165710Z.json`, cost **$0.022317**, +10%). On `scenario_c2_session20_pc_edge_slice_b1_multipc_recall`, default N=3 was **0/3 PASS** (`...--N3--20260428T165925Z.json`, cost **$0.013957**) and the variant improved to **1/3 PASS** (`...--pv-party_continuation_v1--N3--20260428T165953Z.json`, cost **$0.012730**), but failures still included B1 over-route rows. This supports "variant useful for recall pressure" but not "variant safe to promote."

### H3 — pronoun-led abstain rows are a distinct failure class

Rows such as `u-L0018-10`, `u-L0030-06`, and `u-L0028-08` are vulnerable to scene-memory bleed: the model binds "she/her/they" to a prior PC even when the current unit is NPC-led or object/location-led.

**Test:** Build or reuse an abstain-only slice containing pronoun-led rows and run `--n 5`. Inspect sidecar rationales: if assigned hubs cite prior scene context instead of the current unit text plus one-hop binding, this is a pronoun-binding failure, not a named-PC rule failure.

**Result (2026-04-28 bucket sentinel):** H3 is supported. The model can usually classify pronoun-led non-PC rows as `npc_placeholder` instead of routing them to PCs, and B2 stayed clean across both default and party-continuation cohorts. Remaining issue: bucket labels are not yet hard-gate stable. Default run 3 classified `u-L0028-08` as `true_empty` instead of `npc_placeholder` and `u-L0032-08` as `event_or_object_placeholder` instead of `npc_placeholder`; party-continuation runs sometimes classified the tower line (`u-L0030-06`) as NPC-centered rather than `location_placeholder`. Keep BD soft until this stabilizes.

**Result (2026-04-28 context slice):** H3 is not closed. `scenario_c2_session20_pc_edge_slice_b2_abstain_pronoun_context` N=5 failed under both default (`...--N5--20260428T165804Z.json`, cost **$0.026766**) and `party_continuation_v1` (`...--pv-party_continuation_v1--N5--20260428T165846Z.json`, cost **$0.027643**, +3%). Several failures are schema-level B0 rows where the model assigns PC hubs while also leaving a non-null placeholder bucket, proving the new strict schema catches contradictory route semantics. Interpretation: mixed bucket sentinel success was too optimistic; H3 needs a dedicated abstain/pronoun guard or sharper prompt rule, and the context slice should stay in the required test set.

### H4 — party/group wording has positive and negative cases

Some rows require full roster (`routing_context.pc_party_names` or clear team action); others mention "group" only as background or reported memory and should abstain.

**Test:** Run a small mixed slice with positive roster-copy rows and negative background-group rows. A passing change preserves both: full roster for registered party / joint-action rows, abstain for ambient or reported "group" references.

**Result (2026-04-28):** H4 remains the dominant live failure. On the bucket sentinel, `party_continuation_v1` often recovers `u-L0026-03` and `u-L0030-03` without creating B2 over-assignment. On the broader H1/H2 sentinel, the same variant still misses `u-L0030-03` in all three runs and destabilizes `u-L0026-06` (two under-routes, one over-route). The rule helps same-slice party continuation but is not robust across mixed multi-PC / affected-PC rows.

**Result (2026-04-28 party-boundary slice):** `party_continuation_v1` improved roster-positive recall without overfiring on the five must-abstain rows: B2 stayed 0/3, while B1 misses dropped from 6/6/6 (default) to 3/2/2 (variant). It still did not pass any run. H4 is now sharper: negative group boundaries are not the immediate blocker in this slice; the blocker is incomplete full-roster expansion on positive party/group rows.

### H5 — some abstain rows are gold-review candidates

Rows like `u-L0028-07` and `u-L0018-10` may encode a GM retrieval-intent decision, not just model behavior. If the sentence should be retrievable from a PC timeline because that PC heard, caused, or is the intended continuity thread for the NPC response, move it out of `must_abstain` with a `scenario_notes` rationale. If not, keep it as hard abstain pressure.

**Test:** Human adjudication before prompt work. For each candidate, answer: "Would I want this unit retrievable from a PC hub?" Only then update gold or tighten prompt/harness rules.

**Result (2026-04-28):** the bucket-sentinel abstain adjudications are provisionally supported: `u-L0018-10`, `u-L0028-07`, `u-L0028-08`, `u-L0030-06`, `u-L0032-05`, `u-L0032-06`, and `u-L0032-08` all held B2 under both tested prompts. The disagreement is bucket semantics (`npc_placeholder` vs `location_placeholder` / `event_or_object_placeholder` / `true_empty`), not whether they should route to PC hubs.

### H6 — examples help only when they preserve rule precedence

The broad 2026-04-27 rewrite improved some adjacent multi-PC rows but regressed roster-copy and abstain precision. Surgical examples under the original rule hierarchy recovered aggregate quality.

**Test:** Any future prompt change must run against three sentinel buckets:

- dual-PC / affected-PC rows (`u-L0024-07`, `u-L0026-06`; `u-L0016-03` tracked separately)
- roster-copy / whole-party positives (`u-L0022-01`, `u-L0026-03`, `u-L0030-03`)
- pronoun or NPC/object/location abstain rows (`u-L0018-10`, `u-L0028-07`, `u-L0030-06`, `u-L0032-05`, `u-L0032-06`)

Do not accept a prompt change that improves one bucket while regressing another without explicit gold adjudication.

**Result (2026-04-28):** examples/variants still require sentinel-wide proof. `party_continuation_v1` is a useful opt-in ablation because it improved the bucket sentinel to 2/3 PASS with no B2 regressions, but the H1/H2 sentinel stayed 0/3 and exposed a new `u-L0026-06` over-route in one run. Next prompt work should target the exact distinction between roster-copy continuation (`u-L0026-03`, `u-L0030-03`) and narrow multi-PC/affected-PC rows (`u-L0026-06`) rather than adding broader continuity prose.

**Result (2026-04-28 additional slices):** the distinction above is confirmed. The party-boundary slice shows the variant can reduce missing roster rows without B2 over-assignment, while the B1-only slice shows the same variant can still over-route must_route rows whose gold expects a narrower PC subset. The next variant should be more structural than prose examples: explicitly separate **roster-copy rows** (party/group/they as joint subject of movement/perception/arrival) from **named multi-PC role rows** (only PCs with same-unit actor/object/locus roles; never expand to full roster merely because party context exists).

## Hypothesis graveyard (Stage B sentence routing)

Each entry is a hypothesis that survived initial testing but was disproved by a later cohort. Move new entries here only with cohort-summary evidence; do not retire a graveyard entry without rerunning the disproof.

### G1 — broad cross-unit continuity prose (variants `a`, `ab`, `abe`, 2026-04-27)

**Claim that died:** adding scene-memory and reported-speech carry rules as default prompt prose would close visible B1 misses on `u-L0026-03` and `u-L0018-02` while costing nothing on abstain rows.

**Disproof:** N=3 matrix on `gpt-5.4-mini` (`baseline` 30 violation strings, `a` 31, `ab` 49, `abe` 51; all 0/3 PASS), recorded in `Backlog.md` ("Stage B sentence-routing — continuity prompt rules…"). The fix converted under-routing into over-routing on `u-L0018-03`, `u-L0028-02`, `u-L0030-03`, `u-L0030-11`. Artifacts: `evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-27/sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-{baseline,a,ab,abe}--N3--*.json`.

**Lesson preserved:** broad continuity prose destabilizes abstain precision faster than it fixes recall. Future attempts must produce N≥3 evidence that *both* B1 and B2 buckets improve vs baseline before being a default. Variants `a`, `ab`, `abe` remain available as `--prompt-variant` opt-ins for ablation.

### G2 — bucket labels are stable enough to hard-gate (2026-04-28)

**Claim that died:** with `routing_diagnostic_bucket` shipped and a small adjudicated sentinel, BD checks could be flipped to hard gates (`enforce_diagnostic_buckets: true`) within one experiment cycle.

**Disproof:** on `scenario_c2_session20_pc_bucket_sentinel` N=3 default, run 3 classified `u-L0028-08` as `true_empty` instead of gold `npc_placeholder` and `u-L0032-08` as `event_or_object_placeholder` instead of `npc_placeholder` (`.../sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--N3--20260428T164441Z.json`). The `party_continuation_v1` variant on the same sentinel labelled `u-L0030-06` `npc_placeholder` rather than `location_placeholder` in some runs (`.../...--pv-party_continuation_v1--N3--20260428T164939Z.json`). Several disagreements are interpretation-of-pure-text vs. one-hop pronoun binding; lowering them to gold without sharper prompt definitions would be deflation.

**Lesson preserved:** keep BD as soft telemetry until either the prompt's bucket descriptions are sharpened on these specific ambiguous shapes or each disagreement row is re-adjudicated with a one-line `notes` rationale. The `enforce_diagnostic_buckets` switch stays in the schema for the day this hypothesis can be revived.

### G3 — a narrow-multi-PC guard can safely promote `party_continuation_v1` (2026-04-28)

**Claim that died:** `party_roster_strict_v1` (the `party_continuation_v1` addendum plus a Marla/Bonogo/Caelynn narrow-multi-PC counter-example) would preserve the roster-copy gains, close the `u-L0026-06` over-route, and move the H1/H2 mixed sentinel toward PASS.

**Disproof:** on the H1/H2 mixed sentinel, the N=5 comparison stayed **0/5 PASS** for both variants. `party_continuation_v1` produced B1 misses/over-route `[2,1,2,2,1-over]`, cost **$0.028177** (`.../sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_continuation_v1--N5--20260428T185202Z.json`). `party_roster_strict_v1` removed the over-route but worsened recall to B1 misses `[1,2,3,2,3]`, cost **$0.027778** (`.../sentence_routing_stage_b_cohort_summary--gpt-5.4-mini--pv-party_roster_strict_v1--N5--20260428T185204Z.json`). The strict addendum merely trades one failure class for another: less over-expansion, more missed roster-copy rows (`u-L0026-03`, `u-L0030-03`) while `u-L0026-06` still misses `bonogo` in all five strict runs.

**Lesson preserved:** do not keep layering prose addenda onto the same prompt surface. The next useful lever is either (a) structured preprocessing/classification that tags units as `roster_copy_candidate` vs `same_unit_role_intersection`, or (b) a base prompt rewrite with clearer rule precedence plus N=5 gates. `party_roster_strict_v1` remains useful as an opt-in negative control, not as a promotion candidate.

## Canonized learnings (Stage B sentence routing, 2026-04-28)

These are *not* hypotheses; they are the contract surfaces this work cycle proved out. Treat them as standing rules for future Stage B changes.

1. **Strict route schema is a grader, not just a label.** `RouteRow` validators (especially `diagnostic_null_when_assigned`) caught a model failure mode that single-field B1/B2 telemetry hid: `assigned_hubs=[pc] + routing_diagnostic_bucket="<placeholder>"` is a confused-routing signal, not noise. New schema fields should ship with both Pydantic validators and a grader bucket so that the contract is enforced before grading.
2. **B2 over-assignment is the cheap-to-defend axis.** Across every default and variant cohort run on PC-only manifests on 2026-04-28, B2 over-assignment stayed at or below baseline — including `0/3` on the bucket sentinel, party-boundary, abstain-pronoun-context, and B1 multi-PC recall slices. Recall (B1) is the moving target. Promoting any prompt change requires showing recall moved *without* B2 regressing.
3. **Narrow prompt addenda compete on different axes than broad ones.** `party_continuation_v1` recovers party-roster recall (bucket sentinel: 0/3 → 2/3 PASS, party-boundary: B1 misses 6/6/6 → 3/2/2) but introduces narrow over-route risk on dual/triple-PC role rows (H1/H2 sentinel: `u-L0026-06` over-routed in one run). Each new variant must be tested on a sentinel matrix, not a single scenario.
4. **Variant promotion gate.** A variant promotes to default only after N≥3 PASS on the bucket sentinel *and* the H1/H2 mixed sentinel, and B1/B2 strictly non-regressing on the party-boundary, abstain-pronoun-context, and B1 multi-PC recall slices. Single-cohort PASS on one slice is below the noise floor.
5. **Cost envelope.** Stage B PC-only cohorts on `gpt-5.4-mini` cost ~$0.004–$0.007/run on these sentinels; cohort sums at N=3 stay in the **$0.013–$0.027** band. New variants must report cohort sum and per-run mean alongside any pass-rate claim per `cost-as-signal.mdc`. Variants that double per-run mean require a paired robustness justification, not just a recall improvement.
6. **Versioned prompt content-IDs are mandatory artifact metadata.** `routing_prompt_base_id` (base text) and `routing_prompt_id` (full sent string) belong on every Stage B sidecar and at the top of every cohort summary. Cohort comparisons across days only mean something when both IDs match (or the difference is the controlled variant).
7. **Gold realignment vs deflation.** On bucket-label disagreements where the model picked `true_empty` over `npc_placeholder`, the model's pure-text reading is often defensible. Per `.cursor/rules/gold-realignment-vs-deflation.mdc`, do not edit gold to match model output without a one-line `notes` rationale grounded in the corpus. Sharpen the prompt's bucket definition first.

## New Stage B hypotheses (2026-04-28)

Each comes with the test command and the acceptance triple (B1, B2, BD), so any future agent (or you on a different day) can re-run the experiment.

### H7 — roster-copy and named-multi-PC are different decision procedures

**Claim:** the failure mode on `u-L0026-06` under `party_continuation_v1` is that a single rule is being asked to handle both "copy from `pc_roster_slugs` exactly" and "intersect with same-unit role evidence." A variant that adds a contrastive narrow-multi-PC counter-example (assign exactly the named PCs in distinct in-unit roles; do *not* expand to full roster from prior context) will recover bucket-sentinel and party-boundary recall *and* close the H1/H2 over-route on `u-L0026-06`.

**Variant under test:** `party_roster_strict_v1` — `party_continuation_v1` body plus an explicit narrow-multi-PC counter-example with a Marla/Bonogo/Caelynn shape.

**Test (sentinel matrix, N=3):** run `party_roster_strict_v1` on the bucket sentinel, the H1/H2 mixed sentinel, the party-boundary slice, and the B1 multi-PC recall slice; compare cohort summary `gold_gate_checks_pass`, `b1_missing_expected_hub`, `b2_over_assigned`, and `routing_diagnostic_histogram` against the matched-scenario `party_continuation_v1` cohorts logged under "H2 — slice matrix" and "H4 — party-boundary slice" above.

**Promotion threshold:** bucket sentinel ≥2/3 PASS, H1/H2 mixed ≥1/3 PASS (any improvement from 0/3), party-boundary B1 misses ≤3/2/2, B1 multi-PC recall ≥1/3 PASS, B2 = 0 across all four cohorts. If any cell regresses, the variant goes to the graveyard with the artifact paths.

**Result (2026-04-28, sentinel matrix N=3 each, `routing_prompt_id=14b06e98cf94c5703e1c2c14`):** H7 is **partial support; not promotable as default**. Bucket sentinel held at v1's 2/3 PASS (`...--pv-party_roster_strict_v1--N3--20260428T172707Z.json`, B1=[0,0,2], B2=[0,0,0], cost sum **$0.016487**). H1/H2 mixed sentinel stayed 0/3 but the B1 floor moved from v1's [2,2,2] to [1,2,1] and there was **no `u-L0026-06` over-route this cohort** (`...--pv-party_roster_strict_v1--N3--20260428T172738Z.json`, B2=[0,0,0], cost sum **$0.016177**, +11% vs same-scenario v1). Party-boundary slice stayed 0/3 with one run's B1 dropping from v1's worst case 3 to 1 (`...--pv-party_roster_strict_v1--N3--20260428T172741Z.json`, B1=[1,2,2], B2=[0,0,0], cost sum **$0.022212**, flat vs v1). B1 multi-PC recall regressed v1's lone PASS by losing run[1] to a B0 schema contradiction on `u-L0032-09` (assigned `karsemine` + `routing_diagnostic_bucket="npc_placeholder"` — exactly the H8 shape) instead of B1 misses (`...--pv-party_roster_strict_v1--N3--20260428T172736Z.json`, runs B1=[2,_,1] with B0=[0,1,0], cost sum **$0.012251**, flat vs v1). Total cost across the four H7 cohorts: **$0.067127** (v1 baseline same matrix: $0.066194; +1.4%).

**Verdict after N=3:** keep `party_roster_strict_v1` as an opt-in variant alongside `party_continuation_v1`. It strictly suppresses v1's `u-L0026-06`-style over-routes on this draw, improves the B1 floor on 3 of 4 sentinels, and stays B2-clean — but the H1/H2 mixed and B1 multi-PC recall PASS gates remain closed at N=3. **Update H8** to "directly observed during H7" (see below).

**Final result after N=5 H1/H2 rerun (2026-04-28):** H7's promotion claim is disproved; see graveyard **G3**. `party_roster_strict_v1` removed `party_continuation_v1`'s single over-route on `u-L0026-06`, but worsened total recall on the mixed sentinel (strict B1 misses `[1,2,3,2,3]` vs v1 `[2,1,2,2]` plus one over-route). Do not promote either variant. Keep both as opt-in controls while designing a structural classifier or a base-prompt rewrite.

### H8 — schema contradictions are confused-routing telemetry

**Claim:** B0 schema violations of the `diagnostic_null_when_assigned` form (model asserts both a PC hub and a placeholder bucket) are not noise; they are the leading indicator of a prompt rule the model cannot reliably apply. The H3 abstain-pronoun-context cohort hit several of these (`.../...--pv-party_continuation_v1--N5--20260428T165846Z.json`).

**Test:** add a cohort-level counter (`b0_diagnostic_null_when_assigned`) to the violation aggregate so this specific shape is tracked separately from "any B0." Run an N=5 cohort on the abstain-pronoun-context slice with both the current default and `party_roster_strict_v1`; see whether the new variant moves the count.

**Promotion threshold:** if `b0_diagnostic_null_when_assigned` falls under `party_roster_strict_v1` (relative to the current default on the same slice), this hypothesis is supported and the counter graduates to a sidecar field. If it stays flat, either the ambiguity is intrinsic to the abstain-pronoun shape (capture as new hypothesis), or the variant is not the right lever.

**Result (2026-04-28, observed during H7):** the H8 shape was directly observed in the H7 B1 multi-PC recall cohort: run[1] failed exclusively because of one B0 row on `u-L0032-09` of the form `assigned_hubs=["karsemine"] + routing_diagnostic_bucket="npc_placeholder"` (`evals/sentence_routing_retrieval_falsification/artifacts/runs/2026-04-28/sentence_routing_stage_b_hub_routes--sentence_routing_c2_session20_pc_edge_slice_b1_multipc_recall--FAIL--20260428T172728658143Z.json` → `violations.stage_b[0]`). With B1=B2=0 on that run, this single B0 contradiction was decisive in flipping a passing run to FAIL.

**Result (2026-04-28, counter shipped + H1/H2 N=5):** `grader.py` now emits `violation_failure_buckets.b0_diagnostic_null_when_assigned`, and parse-failure sidecars now still get a minimal `stage_b_unit_breakdown` so cohort summaries can count the H8 shape. Offline proof: `uv run pytest tests/test_sentence_routing_stage_b_grader.py -q` → **36 passed**. The paired H1/H2 mixed-sentinel N=5 cohorts had **zero** H8 contradictions for both variants: `party_continuation_v1` B0/H8 `[0/0,0/0,0/0,0/0,0/0]`; `party_roster_strict_v1` B0/H8 `[0/0,0/0,0/0,0/0,0/0]`. Interpretation: H8 is real but not the dominant mixed-sentinel blocker; it remains a required counter on future cohorts, and the next H8-specific run should target `scenario_c2_session20_pc_edge_slice_b2_abstain_pronoun_context` (where B0 contradictions originally appeared) with the new counter.

**Result (2026-04-28, abstain-pronoun-context N=5 with counter):** H8 is supported on the slice where it was first seen. `party_continuation_v1` stayed **0/5 PASS** (`...--pv-party_continuation_v1--N5--20260428T185648Z.json`, cost sum **$0.027308**, mean **$0.005462**) with B0/H8 in **2/5** runs (`b0_diagnostic_null_when_assigned=[0,0,0,1,1]`) plus B2 over-assignment in the other failures (`b2_over_assigned=[4,1,3,0,0]`). `party_roster_strict_v1` improved to **2/5 PASS** (`...--pv-party_roster_strict_v1--N5--20260428T185646Z.json`, cost sum **$0.025562**, mean **$0.005112**) and eliminated the H8 schema contradiction entirely (`b0_diagnostic_null_when_assigned=[0,0,0,0,0]`), but still over-assigned `u-L0018-10` in 3/5 (`b2_over_assigned=[0,1,0,1,1]`). Interpretation: the strict guard really does reduce confused-routing B0 on abstain-pronoun context, but the residual blocker is now a row-specific B2 pronoun/affected-party ambiguity, not a schema contradiction. Keep the H8 counter permanent.

### H9 — single-PASS evidence is below the noise floor

**Claim:** the `party_continuation_v1` 1/3 PASS on the B1 multi-PC recall slice is noise, not signal; promotion gates require either N≥3 PASS or N≥5 PASS-rate ≥80%. We have *not* run every Stage B PC cohort gate at N=5 since shipping diagnostic buckets.

**Test:** rerun the bucket sentinel and the H1/H2 mixed sentinel at N=5 against the current default prompt (`routing_prompt_base_id` of record), and again against the winning H7 variant. Record per-run pass/fail vector, not just aggregate.

**Promotion threshold:** any default-prompt change requires bucket sentinel + H1/H2 mixed both at PASS-rate ≥80% (4/5) at N=5 *before* expanding the matrix. This is the standing N gate going forward.

**Result (2026-04-28, H1/H2 mixed sentinel N=5):** H9 is supported. `party_continuation_v1` stayed **0/5 PASS** (`...--pv-party_continuation_v1--N5--20260428T185202Z.json`, cost sum **$0.028177**, mean **$0.005635**) and `party_roster_strict_v1` stayed **0/5 PASS** (`...--pv-party_roster_strict_v1--N5--20260428T185204Z.json`, cost sum **$0.027778**, mean **$0.005556**). The failure is not stochastic pass-rate noise hiding a promotable variant; the same unit IDs dominate repeatedly. For v1: `u-L0026-06` failed in 5/5 (four misses, one over-route) and `u-L0030-03` missed in 3/5. For strict: `u-L0026-06` missed `bonogo` in 5/5, `u-L0030-03` missed in 4/5, and `u-L0026-03` missed in 2/5. Bucket-sentinel N=5 remains to be run before any base-prompt promotion, but the H1/H2 mixed gate alone rejects both current variants.

### H10 — bucket-label disagreement is a definition gap, not a routing gap

**Claim:** the bucket-sentinel run-3 disagreements on `u-L0028-08` (`true_empty` vs gold `npc_placeholder`) and `u-L0032-08` (`event_or_object_placeholder` vs gold `npc_placeholder`) come from the prompt's bucket definitions being silent on (a) one-hop pronoun continuation when the antecedent is an NPC, and (b) named characters in a possessive/object frame ("trust in the city"). The fix is a one-paragraph addendum to the bucket descriptions in `ROUTING_SYSTEM_PROMPT_BASE`, *not* a new routing rule.

**Test:** draft `bucket_definitions_sharper_v1` (a base-prompt edit, not an addendum) that adds two clauses to the bucket descriptions: "When a unit is pronoun-led and the immediately previous unit anchors the pronoun to an NPC, prefer `npc_placeholder` over `true_empty`. Possessive constructions naming a non-PC person ("X is concerned about who she can trust") prefer `npc_placeholder` even when the surface verb is abstract." Run on the bucket sentinel N=5; compare BD pass count vs current default.

**Promotion threshold:** BD pass count strictly higher under the new base prompt without any B2 regression. If yes, the new base ships and bumps `ROUTING_PROMPT_BASE_ID`; if no, the disagreement rows are escalated to an explicit gold-vs-prompt adjudication and either the gold gets a `notes` rationale or the prompt acquires a different rule.

### H11 — `u-L0018-10` is the residual abstain-pronoun ambiguity after H8

**Claim:** after `party_roster_strict_v1` removes H8-style schema contradictions on the abstain-pronoun-context slice, the remaining failure is concentrated in `u-L0018-10`: the model treats the unit as PC-retrievable because a PC is the conversational/listening locus, while gold currently treats it as NPC-placeholder / no PC hub. This is not the same failure as wrong roster-copy; it is a retrieval-intent ambiguity for "NPC says/reports/frames X to or around PC" units.

**Test:** human-adjudicate `u-L0018-10` before prompt work. If the GM wants the unit retrievable from Bonogo's hub because Bonogo is the recipient/listener or continuity owner, move it from `must_abstain` to `must_route` with a `scenario_notes` rationale. If the GM wants NPC speech to stay off PC hubs unless the PC acts/decides/is affected in the same unit, keep gold unchanged and add a base-prompt rule: "reported speech / NPC concern about or to a PC does not make the PC a retrieval hub unless the PC is same-unit actor/object/locus." Then rerun the abstain-pronoun-context slice N=5.

**Promotion threshold:** after adjudication or prompt change, `party_roster_strict_v1` or the successor base prompt must reach ≥4/5 PASS on the abstain-pronoun-context slice, with `b0_diagnostic_null_when_assigned=0` and B2 over-assignment ≤1/5. If the only remaining failing row is `u-L0018-10`, do not tune prompt prose further until the gold decision is made.

### Review-first workflow

1. Generate the current edge cohort and violation aggregate.
2. Review B2 `must_abstain` rows before editing prompt text.
3. For each reviewed row, classify it as `keep_abstain`, `move_to_must_route`, or `defer`.
4. Only after adjudication, test the smallest lever that targets the dominant remaining bucket: gold realignment, narrow prompt example, harness-only instruction, or deterministic guard.

### H1/H2 experiment slices

These scenario files are carved from `gold/scenario_c2_session20_pc_edge_flaky48.json`, embed only the selected `sentence_units`, and use direct `unit_id` gold rows so line-local indexes do not need surrounding units to resolve. They include `fixture_routes` for `--no-llm` smoke tests.

- `gold/scenario_c2_session20_pc_edge_slice_b1_multipc_recall.json` — H2 named-PC recall / multi-PC `must_route` pressure, excluding `u-L0016-03`.
- `gold/scenario_c2_session20_pc_edge_slice_party_boundary.json` — H1 roster-copy positives plus generic/background group or NPC-led abstain negatives.
- `gold/scenario_c2_session20_pc_edge_slice_b2_abstain_pronoun.json` — H2 pronoun/NPC/object abstain precision rows with B2 history.
- `gold/scenario_c2_session20_pc_edge_slice_h1_h2_sentinel.json` — mixed sentinel: dual/multi-PC recall, roster positives, and B2-prone abstains.
- `gold/scenario_c2_session20_pc_bucket_sentinel.json` — **bucket sentinel:** adjudicated `gold_routing.diagnostic_buckets` on mixed roster positives (`u-L0022-01`, `u-L0026-03`, `u-L0030-03`) plus H3-prone abstain rows (`u-L0018-10`, `u-L0028-07`, `u-L0028-08`, `u-L0030-06`, `u-L0032-05`, `u-L0032-06`, `u-L0032-08`). BD mismatches are telemetry-only unless `enforce_diagnostic_buckets`. Versioned prompt + hashes live in `routing_prompt.py` (`ROUTING_PROMPT_BASE_ID` / full `routing_prompt_id` on Stage B sidecars).

### Bucketed diagnostic routing (Stage B)

**Hypothesis:** PC-only routing overloads plain `assigned_hubs=[]`; explicit per-row `routing_diagnostic_bucket` separates wrong-PC routing from legitimate non-PC / empty classifications without collapsing abstain reasons.

**Closed vocabulary** (`route_schema.py`): `npc_placeholder`, `location_placeholder`, `event_or_object_placeholder`, `new_hub_candidate`, `true_empty`; JSON `null` when any hub slug is assigned.

**Gold:** optional `gold_routing.diagnostic_buckets` keyed by `unit_id`; optional `enforce_diagnostic_buckets` (default **false** — soft BD: counts only). Histogram: `telemetry.stage_b_unit_breakdown.routing_diagnostic_histogram`.

**Prompt artifact:** `routing_prompt.py` exports `ROUTING_SYSTEM_PROMPT_BASE`, `build_routing_system_prompt()`, `ROUTING_PROMPT_BASE_ID`.

Offline smoke:

```bash
for s in \
  scenario_c2_session20_pc_edge_slice_b1_multipc_recall \
  scenario_c2_session20_pc_edge_slice_party_boundary \
  scenario_c2_session20_pc_edge_slice_b2_abstain_pronoun \
  scenario_c2_session20_pc_edge_slice_h1_h2_sentinel; do
  uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \
    --scenario-json evals/sentence_routing_retrieval_falsification/gold/${s}.json \
    --corpus-root . --no-llm --no-writes
done
```

Live N=3 example:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \
  --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc_edge_slice_h1_h2_sentinel.json \
  --corpus-root . --n 3
```

Report the acceptance triple from each cohort summary: `gold_gate_checks_pass`, `b1_missing_expected_hub`, and `b2_over_assigned`, plus diagnostic bucket pass/fail when using `diagnostic_buckets`, plus the cohort **Cost** (`cost_usd.sum` and per-run mean/min/max; compare to prior Stage B cohorts per `cost-as-signal.mdc`).

**Bucket sentinel commands:**

```bash
uv run pytest tests/test_sentence_routing_stage_b_grader.py -q
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \
  --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc_bucket_sentinel.json \
  --corpus-root . --no-llm --no-writes
uv run python -m evals.sentence_routing_retrieval_falsification.step2_route_run \
  --scenario-json evals/sentence_routing_retrieval_falsification/gold/scenario_c2_session20_pc_bucket_sentinel.json \
  --corpus-root . --n 3
```

## Breadcrumb Query Canvas Refresh

The breadcrumb query semantic-review canvas at
`/home/drakosfire/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/breadcrumb-query-semantic-review.canvas.tsx`
is data-driven. Every dynamic field (pass counts, costs, scenario rows,
recovered/missed evidence, expansion config) is derived from a benchmark
report by `breadcrumb_query_canvas_payload.py` and embedded inline between
explicit markers:

```text
// BEGIN GENERATED BREADCRUMB_QUERY_CANVAS_DATA
const canvasData = { ... } as const;
type CanvasData = typeof canvasData;
// END GENERATED BREADCRUMB_QUERY_CANVAS_DATA
```

### Hard rules

- **Do not hand-edit** anything between `BEGIN GENERATED BREADCRUMB_QUERY_CANVAS_DATA`
and `END GENERATED BREADCRUMB_QUERY_CANVAS_DATA`. Rerun the generator instead.
- Hand-edit layout/components **outside** the generated block only.
- If the canvas stat block disagrees with a fresh report, **the report wins**
— rerun the generator instead of patching literals.
- When adding a new payload field, update `BreadcrumbQueryCanvasData`/
`breadcrumb_query_canvas_payload.py`, the canvas renderer, and
`tests/test_breadcrumb_query_canvas_payload.py` together in the same change.

### Refresh after a benchmark run

Run the generator directly:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload \
  --report evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_llm_semantic_expanded_report.json \
  --deterministic-report evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_expanded_deterministic_report.json \
  --baseline-report evals/sentence_routing_retrieval_falsification/manual_labels/artifacts/breadcrumb_query_natural_llm_semantic_promoted_report.json \
  --canvas-tsx /home/drakosfire/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/breadcrumb-query-semantic-review.canvas.tsx
```

`--baseline-report` and `--deterministic-report` are optional; pass them when
you have either artifact for the same gold/corpus and want recovered/missed
evidence in the per-scenario cards or the deterministic pass count alongside
the LLM pass count.

Or chain it onto `breadcrumb_query_run` so the canvas refreshes automatically
after the report is written:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --records-jsonl <records>.jsonl \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_v1.json \
  --semantic-similarity \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_llm_semantic_expanded_report.json \
  --canvas-tsx /home/drakosfire/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/breadcrumb-query-semantic-review.canvas.tsx \
  --canvas-baseline-report evals/sentence_routing_retrieval_falsification/manual_labels/artifacts/breadcrumb_query_natural_llm_semantic_promoted_report.json \
  --canvas-deterministic-report evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_expanded_deterministic_report.json
```

### C1S1 benchmark review canvas (benchmark-owned refresh)

For natural gold that targets the C1S1 lane (gold filename contains `c1s1`, or any scenario `id` starts with `c1s1_`), each `breadcrumb_query_run` invocation **patches the C1S1 benchmark review canvas** in the same process after the report JSON is written. The default target is the Cursor-managed file under `~/.cursor/projects/<workspace-slug>/canvases/c1s1-breadcrumb-query-benchmark-review.canvas.tsx` (same resolution as other harness canvases: set `DMB_CURSOR_CANVAS_DIR` to override the canvases parent directory). The report includes a `c1s1_canvas_refresh` object (`enabled`, `targets`, `updated`, `unchanged`, `errors`); the final stdout JSON line echoes that under `c1s1_canvas_refresh`.

- **Extra targets:** pass `--c1s1-canvas-tsx PATH` one or more times when you need a non-default canvas file. When any `--c1s1-canvas-tsx` is set, those paths are used **instead of** the default (repeat the default Cursor-managed path explicitly if you need both).
- **Opt out:** `--skip-c1s1-canvas-refresh` skips the patch even for C1S1 gold (and records `reason: skipped_by_flag` in the report when a refresh would otherwise have run).
- **Standalone emitter** (same markers): `python -m evals.sentence_routing_retrieval_falsification.c1s1_benchmark_canvas_emit --report … --gold …`.
- **Troubleshooting:** if the canvas file is missing `// BEGIN GENERATED C1S1_HARNESS_DETAIL` / `// END GENERATED C1S1_HARNESS_DETAIL`, the run exits non-zero after writing the report; fix the canvas template once, then re-run.

### C1S2 candidate + benchmark canvases

**Contracts:** see [`C1S2_BENCHMARK_CONTRACTS.md`](C1S2_BENCHMARK_CONTRACTS.md).

**Candidate JSON (gold-agnostic):**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.c1s2_query_candidate_build
uv run python -m evals.sentence_routing_retrieval_falsification.c1s2_query_candidate_canvas_emit \
  --candidates evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/c1s2_query_candidates_<stamp>.json \
  --canvas-tsx ~/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/c1s2-breadcrumb-query-candidate-review.canvas.tsx
```

**Natural benchmark run (manual/reference artifact; requires `OPENAI_API_KEY` unless `--retrieval-only` is set):**

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --breadcrumb-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 2 - Finishing the Job.breadcrumbed.md" \
  --corpus-root corpus/eldyrwild-markdown \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_c1s2_report.json \
  --c1s2-canvas-tsx ~/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/c1s2-breadcrumb-query-benchmark-review.canvas.tsx \
  --skip-c1s1-canvas-refresh
```

For natural C1S2 gold, `breadcrumb_query_run` also auto-patches the Cursor-managed `c1s2-breadcrumb-query-benchmark-review.canvas.tsx` (same `DMB_CURSOR_CANVAS_DIR` resolution as C1S1). Use `--c1s2-canvas-tsx` for extra targets, `--skip-c1s2-canvas-refresh` to opt out. The report includes `c1s2_canvas_refresh`; the runner exits non-zero if any canvas patch errors.

**Current routing-only control (2026-05-08):** C1S2 is the clean control lane for the
cross-session routing-only baseline: `artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s2_routing_refresh_retrieval_only.json`
passes 15/15 with cost `$0.012705`. Use this lane to catch broad prompt regressions
before over-fitting fixes to C1S1, C1S3, or C1S13.

The full manual C1S2 `.breadcrumbed.md` body is historical until realigned with current
normalization; do not use a manual-reference failure as evidence against the
routing-only baseline.

**Offline report (no API, expected_answer as LLM stand-in):** for CI or canvas refresh without a live cohort, `c1s2_offline_benchmark_report_build` writes `breadcrumb_query_natural_c1s2_report_offline.json` (`scenario_estimated_cost_usd: 0`). **This does not satisfy the 3-run LLM acceptance gate** — run three identical live harness invocations for that.

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.c1s2_offline_benchmark_report_build
uv run python -m evals.sentence_routing_retrieval_falsification.c1s2_benchmark_canvas_emit \
  --report evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_c1s2_report_offline.json \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s2_v1.json \
  --canvas-tsx ~/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/c1s2-breadcrumb-query-benchmark-review.canvas.tsx
```

**Tagging sentinels (C1S2):** `gold/breadcrumb_tagging_sentinels_c1s2.json` (do not reuse Session 20 sentinels for this recap).

### C1S3 candidate + benchmark canvases (Session 3 — The Stone Bridge Flood)

Mirrors the C1S2 workflow: `c1s3_query_candidate_build`, `c1s3_query_candidate_canvas_emit`, natural gold `gold/breadcrumb_query_natural_c1s3_v1.json`, tagging sentinels `gold/breadcrumb_tagging_sentinels_c1s3.json`, benchmark emitter `c1s3_benchmark_canvas_emit`.

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.c1s3_query_candidate_build
uv run python -m evals.sentence_routing_retrieval_falsification.c1s3_query_candidate_canvas_emit \
  --candidates evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/c1s3_query_candidates_<stamp>.json \
  --canvas-tsx ~/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/c1s3-breadcrumb-query-candidate-review.canvas.tsx

uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --breadcrumb-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 3 - The Stone Bridge Flood.breadcrumbed.md" \
  --corpus-root corpus/eldyrwild-markdown \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s3_v1.json \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_c1s3_report.json \
  --c1s3-canvas-tsx ~/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/c1s3-breadcrumb-query-benchmark-review.canvas.tsx \
  --skip-c1s1-canvas-refresh --skip-c1s2-canvas-refresh
```

For C1S3 natural gold, `breadcrumb_query_run` auto-refreshes the Cursor-managed `c1s3-breadcrumb-query-benchmark-review.canvas.tsx` when that file exists under `DMB_CURSOR_CANVAS_DIR`. **If the default Cursor path is missing**, run the matching canvas emitter first or pass `--c1s3-canvas-tsx` with an existing target path so the runner does not exit non-zero on `FileNotFoundError`.

**Current routing-only pressure lane (2026-05-08):** `artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s3_routing_refresh_retrieval_only.json`
passes 12/13. The remaining failure, `c1s3_stonebridge_npc_roster_associated`, is
not simple Grishna omission: Grishna is routed in generated records, but via the
`rivers_edge_pub` sublocation rather than same-unit `stonebridge`. Treat this as a
location hierarchy / location-entity query design question unless the routing contract
is explicitly changed to require redundant parent-location tags.

The full manual C1S3 `.breadcrumbed.md` body is also historical until realigned with
current normalization. The routing-only report above is the current regression surface.

### C1S13 holdout ingestion + retrieval (Session 13 — The Meaty and the Dead)

Use this when validating the "fresh recap -> routing-only breadcrumb ingest ->
retrieval" holdout loop for Campaign 1 Session 13.

Single command (generates breadcrumb markdown from recap + frontmatter seed, then
normalizes to records and runs retrieval grading):

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --ingest-routing-only \
  --ingest-recap-md "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md" \
  --ingest-frontmatter-seed-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.normalized.breadcrumbed.frontmatter_seed.md" \
  --ingest-breadcrumb-out evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/c1s13_routing_refresh.breadcrumbed.routing_only.md \
  --corpus-root corpus/eldyrwild-markdown \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json \
  --retrieval-only \
  --output evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_c1s13_routing_refresh_retrieval_only.json \
  --skip-c1s1-canvas-refresh --skip-c1s2-canvas-refresh --skip-c1s3-canvas-refresh
```

The C1S13 benchmark review canvas (`c1s13-breadcrumb-query-benchmark-review.canvas.tsx`) defaults to the Cursor project canvases directory (same layout as other benchmark canvases: `DMB_CURSOR_CANVAS_DIR` or `~/.cursor/projects/<workspace-slug>/canvases/`). Run `c1s13_benchmark_canvas_emit` to create or refresh that file before patching.

**Current routing-only regression sentinel (2026-05-08):** compare new runs against
`artifacts/runs/2026-05-08/breadcrumb_query_natural_c1s13_report_retrieval_only.routing_only.json`.
The refresh report `breadcrumb_query_natural_c1s13_routing_refresh_retrieval_only.json`
regressed `necromancer_question_identity_trap`: the prior artifact routed the
necromancer kill unit to both `necromancer` and `draven`; the refresh dropped
`draven`, causing `missing_expected_route_hit` and `semantic_verdict:fail_incomplete`.

### Anti-stale check (CI / pre-commit)

Verify the canvas is in sync with the latest committed report without
mutating the file:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload \
  --report evals/sentence_routing_retrieval_falsification/artifacts/runs/<date>/breadcrumb_query_natural_llm_semantic_expanded_report.json \
  --canvas-tsx /home/drakosfire/.cursor/projects/home-drakosfire-Projects-DungeonOverMind-DungeonMindBuddy/canvases/breadcrumb-query-semantic-review.canvas.tsx \
  --check
```

`--check` exits non-zero when the generated block would change. Treat that
as "rerun the refresh command", not "patch the canvas by hand."

## Known limitations (v0 capture)

Sentence splitting uses a simple regex; abbreviations and dialogue punctuation can misfire. The suite is designed to be **falsifiable**: tighten rules or replace with a tokenizer once failure buckets justify it.

### Cohort L3 alias-saturation diagnostic canvas

Use the retrieval-only alias-saturation emitter to aggregate committed L3 question-delta artifacts and generate a deterministic evidence canvas for threshold/promotion-gate analysis:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_l3_alias_saturation_canvas_emit \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s1_to_c1s3_v1.json \
  --input evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_natural_v1.json
```

By default the emitter writes the Cursor-managed canvas under `~/.cursor/projects/<workspace-slug>/canvases/` (override with `DMB_CURSOR_CANVAS_DIR` or `--output`).

L3 question-delta artifacts also include deterministic per-question failure diagnostics:

- `failure_diagnostic.bucket` values are closed: `passed`, `equivalence_helped`, `ranking_regression`, `missing_lexical_handle`, `retriever_support_gap`, `gold_or_rubric_gap`.
- `failure_diagnostic.reasons` provides deterministic textual reasons from existing retrieval fields only.
- `failure_diagnostic.baseline_missing_route_substrings` and `failure_diagnostic.with_equivalence_missing_route_substrings` preserve expected-route order for quick side-by-side triage.
- `failure_diagnostic_summary` at artifact top-level aggregates bucket counts for machine-readable promotion-gate checks.

### Candidate scene-beat rebenchmark lane (PR #17 slice)

This lane is **candidate-only** and does not change default retrieval behavior.

- Build beat-enriched records from existing session-memory + unit-annotation output:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.scene_beat_memory \
  --records-jsonl "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_session_memory/Session 13 - The Meaty and the Dead.records_meta.jsonl" \
  --unit-annotations-json /tmp/c1s13_unit_annotations_scene_beat.json \
  --out-jsonl /tmp/c1s13_scene_beat.records_meta.jsonl \
  --out-meta /tmp/c1s13_scene_beat.records_meta.json
```

- Run natural benchmark with opt-in same-beat expansion:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_query_run \
  --records-jsonl /tmp/c1s13_scene_beat.records_meta.jsonl \
  --gold evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json \
  --retrieval-only \
  --use-scene-beat-expansion \
  --scene-beat-expand-limit 8 \
  --output /tmp/c1s13_scene_beat_run.json
```

- Produce cohort question-level delta (baseline vs with-scene-beats):

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --scene-beat-records-jsonl /tmp/c1s13_scene_beat.records_meta.jsonl \
  --write-scene-beat-question-delta /tmp/cohort_l3_scene_beat_question_delta_c1s13_v1.json
```

### Candidate scene-beat packets (PR #18 slice)

`--use-scene-beat-expansion` (PR #17) adds sibling rows through the normal expansion budget.  
`--use-scene-beat-packets` (PR #18) instead scores first-pass hits grouped by `beat_id` and appends a capped packet before ordinary expansion accounting.

Deterministic C1S13 smoke (fixture-only beat labels, no production wiring):

```bash
uv run python - <<'PY'
import json
from pathlib import Path
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_gold import load_gold_beat_index
records_path = Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_session_memory/Session 13 - The Meaty and the Dead.records_meta.jsonl")
gold_path = Path("evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.gold.beats.breadcrumbed.md")
out = Path("/tmp/c1s13_gold_scene.records_meta.jsonl")
beat_by_unit = {}
for beat in load_gold_beat_index(gold_path):
    for unit_id in beat.unit_ids:
        beat_by_unit[str(unit_id)] = beat.beat_id
rows = []
for line in records_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    beat_id = beat_by_unit.get(str(row.get("unit_id")))
    if beat_id:
        row["beat_id"] = beat_id
    rows.append(row)
out.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
print({"out": str(out), "rows": len(rows), "records_with_beat_id": sum(1 for row in rows if row.get("beat_id")), "beat_count": len(set(beat_by_unit.values()))})
PY

uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --scene-beat-records-jsonl /tmp/c1s13_gold_scene.records_meta.jsonl \
  --write-scene-beat-question-delta /tmp/cohort_l3_scene_packet_question_delta_c1s13_v1.json \
  --use-scene-beat-packets
```


## Baseline lane policy

- Default `--write` and `--check` now run the promoted equivalence lane (`--mode with-equivalence`).
- Legacy baseline remains available for diagnostics with `--mode baseline`.
- Delta and question-delta diagnostics continue to compare legacy baseline vs promoted equivalence using `--mode both`.
