# Stage D NPC Entity Resolution — Vertical Slice (v0)

**Position in the events-first pipeline:** Stage A (events extraction) → Stage C (NPC bucket classification) → **Stage D (this slice — entity resolution)** → Stage E (per-NPC artifact updates).

Stage D consumes Stage C output (three buckets: `tracked_npcs_active[]`, `new_npc_candidates[]`, `unresolved_descriptors[]`) plus the same events JSON, NPC registry, and PC roster Stage C consumed, and emits **auditable merge decisions** as a **propose-only** sidecar that the GM reviews before any registry mutation.

Output is a `StageDOutput` Pydantic model with FOUR arrays:

- **`resolved_entities[]`** — every input new_candidate / unresolved_descriptor routed to one of three resolutions: `merge_to_registry_slug` (existing registry), `merge_to_canonical_new_candidate` (slug-variant collapse within new_npc_candidates[]), or `new_net_entity` (a brand-new candidate Stage D recommends).
- **`proposed_aliases[]`** — alias-string additions for existing registry slugs (e.g. attaching "the captain" as an alias on `captain_lysandra_ironveil`). The alias isn't yet in the registry; Stage D recommends it for future passes.
- **`proposed_new_records[]`** — partial `NpcRegistryRecord` rows for `new_net_entity` resolutions. Status MUST be `candidate`, `hub_path` MUST be null. These are the candidate rows for GM promotion to the per-campaign registry.
- **`unresolvable[]`** — items legitimately ambiguous after Stage D's best-effort heuristics (generic creature descriptors with no name evidence, conflicting evidence). Surfaces for GM triage and is the input pool for v1's narrow LLM coreference pass.

Stage D **never** mutates `corpus/eldyrwild-markdown/<campaign>/_npc_registry.json`. All output is written to per-run artifacts + a `proposals/` sidecar — promote-to-registry remains a GM decision.

## Layout

```
evals/stage_d_entity_resolution_vertical_slice/
  __init__.py
  README.md                              ← this file
  step1_stage_d_run.py                   ← runner (CLI entry point — deterministic v0)
  grader.py                              ← ER1-ER5 gate logic + telemetry
  stage_d_run_report.py                  ← per-run + cohort + proposals writers
  gold/
    stage_d_session20.json               ← C2S20 — clean tracked-active path
    stage_d_session1_c1.json             ← C1S1 — creature unresolvables + grishna/glowkindle proposals
    stage_d_session2_c1.json             ← C1S2 — single new_candidate (glowkindle), zero unresolved
    stage_d_session3_c1.json             ← C1S3 — bubbles slug-variant test
  fixtures/
    .gitignore                           ← allow stage_c_output_*.json; ignore everything else
    stage_c_output_session20.json        ← FROZEN Stage C S20 output
    stage_c_output_session1_c1.json      ← FROZEN Stage C C1S1 output (8 unresolved aggregated)
    stage_c_output_session2_c1.json      ← FROZEN Stage C C1S2 output (glowkindle only)
    stage_c_output_session3_c1.json      ← SYNTHESIZED Stage C C1S3 output (bubbles + bubbles_the_float_goat both present)
  artifacts/
    .gitignore
    last_stage_d_run.{md,json}           ← latest Stage D run
    runs/
      .gitkeep
      YYYY-MM-DD/
        stage_d--*.{md,json}             ← per-run artifacts (sidecar carries stage_d_output)
        stage_d_summary--*--N*.{md,json} ← cohort summary
  proposals/
    README.md                            ← propose-only sidecar contract
    <campaign>_stage_d_proposals_<ts>.json ← cohort-aggregated proposals for GM review

tests/
  test_stage_d_grader.py                 ← offline grader unit tests (no network)
```

## Strategy — deterministic-first (v0)

v0 of Stage D runs **pure-Python heuristics, no LLM call**. This keeps cost ~$0 per run, makes the contract testable offline, and proves the grader before any model spend. Heuristics, in order:

1. **PC re-check.** If a `new_npc_candidate.suggested_slug` or `unresolved_descriptor.descriptor` substring-matches a PC slug / display_name / alias, route the item to `unresolvable[]` (Stage C should have dropped it; this is a defensive net).
2. **Registry slug match.** If `suggested_slug` exactly equals an existing registry slug, route to `merge_to_registry_slug`.
3. **Registry display_name / alias substring match.** Case-insensitive substring containment between the descriptor and any registry record's `display_name` or `aliases[*]`. For unresolved_descriptors that match this way, additionally emit a `proposed_aliases[]` entry if the descriptor isn't already in the registry record's aliases.
4. **Slug-variant clustering.** Across deferred new_npc_candidates, cluster pairs where (a) the shorter slug is `>= 4` chars and is a substring of the longer (catches `bubbles` ↔ `bubbles_the_float_goat`) OR (b) Levenshtein distance `<= 2` and length difference `<= 2` (catches single-character typos like `glowkindle` ↔ `glowkindel`). Canonical = longest slug in the cluster. Canonical → `new_net_entity` + `proposed_new_records[]`; others → `merge_to_canonical_new_candidate`.
5. **Event-pool sanity check.** Every slug in `participants ∪ referenced_slugs` of the events should be accounted for downstream (PC roster, `tracked_npcs_active[]`, `resolved_entities[].canonical_slug`, or `proposed_new_records[].slug`). Gaps surface as telemetry only — NOT a gate failure.

The runner exposes `--enable-llm-coreference` as a documented **no-op** in v0; v1 will add a narrow LLM coreference pass for the hard unresolvables that deterministic heuristics can't crack (Kirfan-class — named only in event text without a `referenced_slugs[]` anchor).

## How to run

```bash
# Single run against the canonical bubbles slug-variant scenario
uv run python -m evals.stage_d_entity_resolution_vertical_slice.step1_stage_d_run \
    --scenario-json evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session3_c1.json --n 1

# 5-run cohort smoke (deterministic v0 produces identical output across runs;
# the cohort run is included for parity with Stage C and to exercise the
# proposals-aggregation writer end-to-end)
uv run python -m evals.stage_d_entity_resolution_vertical_slice.step1_stage_d_run \
    --scenario-json evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session3_c1.json --n 5

# Dry run (no artifacts written)
uv run python -m evals.stage_d_entity_resolution_vertical_slice.step1_stage_d_run \
    --scenario-json evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session20.json --no-writes
```

### Campaign 1 — Session 1 / 2 / 3 (mirrors Stage C C1 triple)

Stage C ships frozen `stage_a_events_session{1,2,3}_c1.json` plus `stage_c_session{1,2,3}_c1.json` gold. Stage D consumes the matching **frozen Stage C output** fixtures (`stage_c_output_session{1,2,3}_c1.json`) plus the same events path and `Longmont Campaign/Campaign 1/_npc_registry.json`. All three scenarios are **$0/run** in v0 (deterministic).

```bash
for s in 1 2 3; do
  uv run python -m evals.stage_d_entity_resolution_vertical_slice.step1_stage_d_run \
    --scenario-json "evals/stage_d_entity_resolution_vertical_slice/gold/stage_d_session${s}_c1.json" \
    --n 1 --no-writes -q
done
```

Cost: **$0 per run** in v0 (no LLM call).

## Gates

| Gate | Description | Hard fail when |
|------|-------------|----------------|
| **ER1** | Schema validity. Output is a JSON object with the four required arrays; every record's required fields typed correctly; every `canonical_slug` and `proposed_new_records[*].slug` matches `^[a-z0-9_]+$`; every `source_index` resolves to a real position in the Stage C input bucket named by `source_kind`; `resolution` ∈ `{merge_to_registry_slug, merge_to_canonical_new_candidate, new_net_entity}`; `source_kind` ∈ `{unresolved_descriptor, new_candidate}`. | Any violation |
| **ER2** | PC safety. No `resolved_entities[*].canonical_slug`, `proposed_new_records[*].slug`, or `proposed_aliases[*].target_slug` is in the PC roster. Mirrors NC2 one stage downstream. | Any leak |
| **ER3** | No false merges (precision). Every `merge_to_registry_slug` must point at a slug that exists in the registry; every `merge_to_canonical_new_candidate` must point at a slug actually in the input `new_npc_candidates[*].suggested_slug` pool. Gold `must_not_merge[]` pairs (e.g. `["cat owl", "grishna"]`) must NEVER share a canonical_slug. | Any false merge |
| **ER4** | Recall (within scope). Gold `must_merge_clusters[]` (e.g. `["bubbles", "bubbles_the_float_goat"]`) must collapse to one canonical_slug; gold `must_resolve_unresolved[]` substring patterns must NOT remain in `unresolvable[]`. | Any cluster split or required-resolution still unresolvable |
| **ER5** | Registry / status policy. Every `proposed_new_records[*]` validates against `schemas/v0.1/npc_registry.schema.json`; `status` MUST be `candidate`; `hub_path` MUST be null; `slug` MUST NOT collide with an existing registry slug (Stage D is propose-only — never silently overwrite curated rows). | Any policy violation |

## Telemetry exposed

```json
{
  "resolved_count": 5,
  "proposed_aliases_count": 0,
  "proposed_new_records_count": 3,
  "unresolvable_count": 0,
  "resolution_counts": {
    "merge_to_registry_slug": 2,
    "merge_to_canonical_new_candidate": 0,
    "new_net_entity": 3
  },
  "pc_leaks": [],
  "bad_resolution_targets": [],
  "forbidden_pair_violations": [],
  "must_merge_cluster_splits": [],
  "must_resolve_unresolved_still_unresolved": [],
  "bad_records": [],
  "event_pool_size": 5,
  "accounted_size": 5,
  "unaccounted_event_slugs": []
}
```

`unaccounted_event_slugs` is the event-pool sanity check (heuristic 5 above) — non-gating telemetry that surfaces gaps where a slug appears in the events but not in any downstream Stage C / Stage D bucket.

## Offline tests

```bash
uv run pytest tests/test_stage_d_grader.py -v
```

23 tests covering ER1 (5), ER2 (3), ER3 (4), ER4 (3), ER5 (4), the deterministic resolver helpers (3), and the top-level orchestrator shape (1). Synthetic registry + Stage C output + events fixtures inline; no corpus dependency.

## Open follow-ups (v1+)

1. **Narrow LLM coreference pass.** v0 deterministic heuristics can't crack the Kirfan-class case (named NPC mentioned only in event text without a `referenced_slugs[]` anchor). v1 will add an `--enable-llm-coreference` pass that consumes `unresolvable[]` + the events JSON and proposes additional resolutions. The CLI flag is already wired as a no-op in v0.
2. **Stage E (per-NPC artifact update)** — consumes `tracked_npcs_active[]` (from Stage C) ∪ `resolved_entities[*].canonical_slug` where `resolution=merge_to_registry_slug` (from this stage). Separate slice.
3. **GM promotion workflow.** Shipped as `scripts/promote_stage_d_proposals.py` — see "GM promotion workflow" below.

See `Docs/Plans/AUDIT-Stage-D-Entity-Resolution-Discovery.md` for the full design audit motivating this slice.

## GM promotion workflow

`scripts/promote_stage_d_proposals.py` aggregates Stage D propose-only sidecars
(both cohort `proposals/<campaign>_stage_d_proposals_*.json` and per-run
`artifacts/runs/YYYY-MM-DD/stage_d--*.json`) for one campaign and flags
registry collisions. Default mode is **deterministic-only**: the deterministic
flags (`slug_collision`, `display_name_overlap`, `pc_collision`) plus raw
evidence (descriptors, sessions, event indices) carry every signal the GM
needs for the easy-case promotion review. Pair the JSON output with the
browser viewer at `promotions/viewer.html` (drag-drop, no server required).

Pass `--with-llm` to additionally call `gpt-5.4-mini` for an
accept / reject / defer / merge_into_existing recommendation per slug.
Useful for hard cases (Kirfan-class coreference, alias semantics) or to
sanity-check the GM's own judgment.

The CLI is **propose-only**: it never mutates `_npc_registry.json`. The GM
applies promotions by hand after reading the Markdown table or by reviewing
the JSON sidecar in the browser viewer.

```bash
# C1 — combine cohort proposals + per-run sidecars from a given day
uv run python -m scripts.promote_stage_d_proposals \
    --campaign-id longmont-c1 \
    --proposals "evals/stage_d_entity_resolution_vertical_slice/proposals/longmont-c1_stage_d_proposals_*.json" \
    --per-run "evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--*c1*--PASS--*.json" \
    --registry "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/_npc_registry.json"

# C2 — only S20 cohort
uv run python -m scripts.promote_stage_d_proposals \
    --campaign-id longmont-c2 \
    --proposals "evals/stage_d_entity_resolution_vertical_slice/proposals/longmont-c2_stage_d_proposals_*.json" \
    --per-run "evals/stage_d_entity_resolution_vertical_slice/artifacts/runs/2026-04-22/stage_d--*session20*--PASS--*.json" \
    --registry "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json"

# Opt into the model recommendation pass for hard cases or sanity-checking
uv run python -m scripts.promote_stage_d_proposals --with-llm \
    --campaign-id longmont-c2 \
    --proposals "evals/stage_d_entity_resolution_vertical_slice/proposals/longmont-c2_stage_d_proposals_*.json" \
    --per-run "" \
    --registry "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/_npc_registry.json"
```

When `--with-llm` is passed: ~$0.001-$0.002 per slug judged via
`gpt-5.4-mini` (resolved from `MODEL_POLICY.json` action
`corpus_session_planner`). Cost guard warns above $0.50 USD per invocation
and aborts above $2.00. The legacy `--no-llm` flag is accepted for
back-compat (it is now the default and a no-op; a deprecation note is
printed to stderr if used).

Per-run sidecars carry `stage_d_output.proposed_new_records[]` and survive
filename collisions in `proposals/`; passing both `--proposals` and `--per-run`
gives the most complete cross-source aggregation. Aggregation is by `slug`:
`first_session` = min, `last_session` = max, `aliases` = union (order
preserved), evidence rows accumulate per source-of-evidence.

See `evals/stage_d_entity_resolution_vertical_slice/promotions/README.md` for
the on-disk sidecar shape and `tests/test_promote_stage_d_proposals.py` for
the offline contract tests.
