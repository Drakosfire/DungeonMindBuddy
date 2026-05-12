---
pr_body_template: |
  ## Summary
  Wire a candidate scene-beat retrieval lane so C1S13 can be re-benchmarked with beat-aware expansion against the current failed-question diagnostics.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after running every §7 command}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

> **MERGED:** `main` @ `28e98a89e591e7203d0b163d2ab445ac11509995` (2026-05-12T22:14:57Z); review fallback ids **`4276161552`**, **`4276396966`**, **`4276504774`**, **`4276596681`** (final round **REQUEST_CHANGES** on stale PR-body / verbatim §7 paste only; merged by operator request after verify green on head **`32727f69693b66eb10cd4c4be94e3115763f43c4`**).

# HANDOFF — PR #17: Scene-Beat Rebenchmark Wiring

**Created:** 2026-05-12 (UTC).  
**Status:** COMPLETED — merged; atomic doc-sync archived this handoff.  
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`). This handoff opens a candidate rebenchmark lane before any default retrieval promotion.

---

## §0 Re-anchor Snapshot

- Current `main` HEAD at handoff authoring: `7fe5445651b1fd7cc488ad66049425c8d9862bfa` (`docs(plan): sync PR #16 question-delta failure diagnostics merge`).
- Latest workstream state: PR #16 is merged; committed tight/natural/C1S13 question-delta artifacts now include per-question `failure_diagnostic` and top-level `failure_diagnostic_summary`.
- Current blocker: default route-equivalence ranking promotion remains blocked by PR #12 `promotion_gate_candidate.status:none_found`; C1S13 now has a corpus session-memory baseline with routes and partial pass signal, but remaining failures need a controlled "does scene-beat context expansion help?" lane.
- Existing dirty/untracked files in the dispatcher's local worktree are unrelated unless explicitly listed in §4. Do not include them in this PR.

## §1 Mission

Wire a candidate scene-beat retrieval lane that can build beat-enriched session-memory records, expand retrieval within the same beat behind an explicit flag, and re-run C1S13 question deltas without changing default retrieval.

## §2 Why this slice

- The unit-annotation pipeline already emits `beat_id` per unit and `breadcrumb_unit_annotations_compile.py` already has a narrow `enrich_records_with_beat_ids(...)` helper, but the blessed session-memory materializer and retriever do not consume that field.
- PR #16 made remaining failures machine-classifiable, so a scene-beat lane can now be judged by movement in `failure_diagnostic` buckets instead of eyeballing raw answer text.
- The intended mechanism is not "better lexical aliases." It is same-scene context recovery: if the initial hit lands inside a scene beat, retrieval should be able to bring in sibling units from that beat so expected routes, must-hit tokens, or context support can recover.
- This PR does **not** flip any default behavior, does **not** edit corpus breadcrumbs, does **not** edit gold/rubric files, and does **not** promote scene beats as production evidence. It creates the rebenchmark lane and reports the C1S13 readout.

## §3 Authoritative inputs

Read these in order before writing code:

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — §4 allowlist / §5 denylist / §7 verification contract.
2. **`Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`** — Reanchor block and Phase C evidence, especially PR #16 and the "corpus session-memory promotion" session-log entry.
3. **`Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`** — `execution_state.next_gate_command`, `integration_notes`, and latest `external_pull_requests[]`.
4. **`evals/sentence_routing_retrieval_falsification/breadcrumb_unit_annotations_compile.py`** — existing `enrich_records_with_beat_ids(...)`, `derive_beat_spans(...)`, and `compile_location_beat_rows(...)` helpers.
5. **`evals/sentence_routing_retrieval_falsification/breadcrumb_unit_annotations_run.py`** — report shape: `schema: dmb_unit_annotations_ingest_report_v1`, `parsed`, `beat_spans`, `location_beat_rows`, `telemetry_cost`.
6. **`src/agent/session_memory_query.py`** — candidate retriever scoring and expansion behavior; same-beat expansion belongs here, behind an explicit query parameter.
7. **`evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`** — harness boundary for explicit flags. Mirror the existing `--use-route-equivalence-for-ranking` no-default-change pattern.
8. **`evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py`** — cohort A/B driver and question-delta builder.
9. **C1S13 current inputs**:
   - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_session_memory/Session 13 - The Meaty and the Dead.records_meta.jsonl`
   - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md`
   - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 13 - The Meaty and the Dead.frontmatter_seed.md`
   - `evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json`
   - `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json`
10. **`tests/conftest.py`** — confirms repo `.env` loading for live OpenAI calls when the optional C1S13 annotation-generation smoke is run.

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Create | `evals/sentence_routing_retrieval_falsification/scene_beat_memory.py` | Deterministically load unit-annotation output and emit beat-enriched session-memory JSONL plus meta JSON. |
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_unit_annotations_compile.py` | Reuse or tighten `enrich_records_with_beat_ids(...)` so it preserves input records, attaches only deterministic beat metadata, and is safe for JSONL emission. |
| Modify | `src/agent/session_memory_query.py` | Add explicit same-beat expansion support behind a query parameter; default behavior must remain unchanged. |
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | Pass a scenario `query_spec` same-beat expansion knob into `query_session_memory_candidate`. |
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Add harness flag(s) for scene-beat expansion and report fields proving when the lane was active. |
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Add a candidate C1S13 scene-beat comparison mode or write path that produces question-level before/after diagnostics without disturbing existing baseline/equivalence checks. |
| Modify | `evals/sentence_routing_retrieval_falsification/README.md` | Document the candidate scene-beat lane, its non-promotion status, and how to run the C1S13 rebenchmark. |
| Modify | `tests/test_session_memory_query.py` | Unit tests for same-beat expansion ordering, gating, and legacy no-op behavior. |
| Create | `tests/test_scene_beat_memory.py` | Unit tests for deterministic beat-enriched JSONL/meta emission from tiny records and tiny unit annotations. |
| Modify | `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Harness-boundary tests for scene-beat flags and default byte-identity when flags are absent. |
| Modify | `tests/test_cohort_baseline_run.py` | Cohort-boundary tests for the scene-beat comparison output shape and preservation of existing `--check*` lanes. |

> The PR's `git diff --stat` MUST be expressible from this allowlist. If a path is not in this table, expect review to request reversion.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks are named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `corpus/**` | This is a candidate rebenchmark lane, not a corpus write or blessed memory promotion. No `_breadcrumbed/` or `_session_memory/` files should change in this PR. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold/rubric edits would confound whether scene-beat expansion helped retrieval. |
| `evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.gold.beats.breadcrumbed.md` | Manual beat gold is an evaluation reference, not an input to production retrieval wiring. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_unit_annotations_prompt.py` | The beat-boundary prompt was already promoted separately. Do not tune prompts in a retrieval wiring PR. |
| `src/prompts/**` | Planner prompt behavior is out of scope; this slice is retrieval harness wiring only. |
| `src/agent/planner.py` | Do not register scene-beat behavior in the live planner tool surface yet. This PR proves the benchmark lane first. |
| `canvases/**` | Canvas refresh can follow after we know whether the lane moves failures. Do not mix visualization churn into this wiring PR. |
| `.cursor/**` | No rule/skill changes in this PR. |
| `Backlog.md`, `Backlog-DONE.md` | Parent/doc-sync owns backlog state, not the external worker. |
| Existing untracked local artifacts under `evals/sentence_routing_retrieval_falsification/artifacts/` | Do not assume the dispatcher's dirty worktree exists on your branch. Generate temp artifacts under `/tmp` during verification unless §4 is updated by the parent. |

If one of these seems genuinely required, stop and say so in the PR body before opening the PR.

## §6 Implementation Contract

### 6.1 Beat-enriched memory builder

Create `evals/sentence_routing_retrieval_falsification/scene_beat_memory.py` with a small deterministic API:

```python
SCENE_BEAT_MEMORY_META_SCHEMA_V1 = "dmb_scene_beat_memory_meta_v1"

def load_unit_annotations_payload(path: Path) -> RecapUnitAnnotationsV1:
    """Accept either raw dmb_recap_unit_annotations_v1 JSON or a run report with parsed."""

def build_scene_beat_records(
    *,
    records: list[dict[str, Any]],
    annotations: RecapUnitAnnotationsV1,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return records copied from input with beat_id attached where unit_id matches."""

def write_scene_beat_records(
    *,
    records_jsonl: Path,
    unit_annotations_json: Path,
    out_jsonl: Path,
    out_meta: Path,
) -> dict[str, Any]:
    """Read, enrich, write JSONL + meta, and return the meta dict."""
```

Rules:

- Do not mutate input record dicts.
- Preserve record order and every existing field/value exactly unless adding beat metadata.
- Attach `beat_id` only when the source unit annotation has a non-null `beat_id`.
- `lexical_plain` must remain unchanged in this PR. The first proof should isolate same-beat expansion, not lexical stuffing.
- Meta JSON must include at least: schema, input paths as workspace-relative POSIX when possible, `record_count`, `records_with_beat_id`, `beat_count`, and `source_recap_path`.
- The CLI must write only when explicit `--out-jsonl` and `--out-meta` are provided. No default writes to corpus or committed artifact paths.

Expected CLI shape:

```bash
uv run python -m evals.sentence_routing_retrieval_falsification.scene_beat_memory \
  --records-jsonl <input.records_meta.jsonl> \
  --unit-annotations-json <annotations-or-report.json> \
  --out-jsonl /tmp/c1s13_scene_beat.records_meta.jsonl \
  --out-meta /tmp/c1s13_scene_beat.records_meta.json
```

### 6.2 Same-beat expansion in retriever

In `src/agent/session_memory_query.py`, add a query parameter with default zero:

```python
def query_session_memory_candidate(
    ...,
    expand_same_beat_limit: int = 0,
    ...
) -> CandidateQueryResult:
    ...
```

Behavior:

- Default `expand_same_beat_limit=0` must be byte-for-byte equivalent at the harness boundary for existing runs.
- When `expand_context` is active and `expand_same_beat_limit > 0`, use `beat_id` from first-pass seed hits to add sibling records from the same `beat_id`.
- Same-beat additions must be clearly marked in `why_matched`, e.g. `expanded_same_beat:<beat_id>`.
- Do not add same-beat records that are already in first-pass hits.
- Do not expand across null/missing `beat_id`.
- Preserve current adjacency/shared-route/route-family behavior unless the flag is active.
- Ordering must be deterministic: lower `line_start`, then `unit_id`, within each selected beat is acceptable.

### 6.3 Harness flag

In `breadcrumb_query_grader.py`, pass `query_spec.expand_same_beat_limit` into the retriever.

In `breadcrumb_query_run.py`, add explicit CLI flags:

```bash
--use-scene-beat-expansion
--scene-beat-expand-limit <int>  # default 8 when flag is present; 0 otherwise
```

When active, deep-copy each scenario before retrieval and set:

```python
scenario["query_spec"]["expand_context"] = True
scenario["query_spec"]["expand_same_beat_limit"] = limit
```

Each output row should include:

```json
"scene_beat_expansion": {
  "enabled": true,
  "expand_same_beat_limit": 8,
  "records_with_beat_id": <count if cheap to compute, else null>
}
```

Rows without the flag should either omit this field or emit `enabled: false`, but existing committed baseline checks must stay byte-identical. If preserving byte identity requires omission on the default path, omit it.

### 6.4 Cohort rebenchmark lane

In `cohort_baseline_run.py`, add a scene-beat comparison path without changing existing `--check`, `--check-delta`, or `--check-question-delta` behavior.

Acceptable implementation choices:

- Add a new explicit command such as `--write-scene-beat-question-delta <path>` with required `--scene-beat-records-jsonl <path>` for single-scenario C1S13 use.
- Or add `--mode baseline|with-equivalence|with-scene-beats|both` plus a manifest optional key `scene_beat_records_jsonl`, as long as existing `both` keeps its current baseline vs equivalence meaning.

The output schema must not pretend scene beats are route equivalence. Use a distinct schema id, for example:

```python
COHORT_SCENE_BEAT_QUESTION_DELTA_SCHEMA_V1 = "dmb_breadcrumb_query_cohort_scene_beat_question_delta_v1"
```

Minimum output fields:

- `schema_id`
- `manifest`
- `baseline_records_jsonl`
- `scene_beat_records_jsonl`
- `retrieval_only: true`
- `llm_enabled: false`
- per-question baseline row
- per-question `with_scene_beats` row
- per-question `delta.verdict` using the existing verdict vocabulary where possible
- per-question `failure_diagnostic` for the scene-beat lane, reusing PR #16 classifier semantics where applicable
- top-level `failure_diagnostic_summary`

Do not regenerate or overwrite existing committed `cohort_l3_ab_*` artifacts in this PR.

## §7 Verification Commands

The worker must run every command and paste the output into the PR body. The reviewer reruns each. Every behavioral guarantee in §9 must be exercised by at least one command here at the owning boundary.

```bash
# Unit-level: scene-beat JSONL builder and retriever expansion behavior.
uv run pytest tests/test_scene_beat_memory.py tests/test_session_memory_query.py -q

# Harness/cohort boundary: flags, default no-op invariants, and scene-beat comparison shape.
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py tests/test_cohort_baseline_run.py -q

# Existing invariant lanes must remain green.
uv run pytest tests/lexicon_phase_b/ tests/test_breadcrumb_query_run_lexicon_records_jsonl.py tests/test_cohort_baseline_run.py -q

# Existing committed checks must remain byte-stable.
uv run python scripts/materialize_session_memory.py --all-blessed --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# Live C1S13 annotation smoke for the actual rebenchmark input.
# Cost-bearing: report scenario_estimated_cost_usd from /tmp/c1s13_unit_annotations_scene_beat.json.
uv run python -m evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_run \
  --corpus-root corpus/eldyrwild-markdown \
  --ingest-recap-md "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 13 - The Meaty and the Dead.md" \
  --ingest-frontmatter-seed-md "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_breadcrumbed/Session 13 - The Meaty and the Dead.frontmatter_seed.md" \
  --gold-md "evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.gold.beats.breadcrumbed.md" \
  --skip-semantic \
  --output /tmp/c1s13_unit_annotations_scene_beat.json

# Build candidate beat-enriched records outside corpus/ and committed artifacts.
uv run python -m evals.sentence_routing_retrieval_falsification.scene_beat_memory \
  --records-jsonl "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_session_memory/Session 13 - The Meaty and the Dead.records_meta.jsonl" \
  --unit-annotations-json /tmp/c1s13_unit_annotations_scene_beat.json \
  --out-jsonl /tmp/c1s13_scene_beat.records_meta.jsonl \
  --out-meta /tmp/c1s13_scene_beat.records_meta.json

# Rebenchmark C1S13 failed-question behavior with the candidate scene-beat lane.
# Use the exact command shape implemented in §6.4; paste the summary counts and diagnostic buckets.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --scene-beat-records-jsonl /tmp/c1s13_scene_beat.records_meta.jsonl \
  --write-scene-beat-question-delta /tmp/cohort_l3_scene_beat_question_delta_c1s13_v1.json
```

If the final command name differs because §6.4 chooses the manifest-key implementation, keep the same proof obligation: produce `/tmp/cohort_l3_scene_beat_question_delta_c1s13_v1.json` and paste the before/after pass counts plus `failure_diagnostic_summary`.

## §8 Reporting Contract

In the PR body the worker MUST include:

1. **`git diff --stat` filtered to §4 allowlist paths only.** Not the whole-tree stat.
2. **Verbatim §7 output** — pass/fail counts, and last 20 lines on failure.
3. **C1S13 scene-beat readout** from `/tmp/cohort_l3_scene_beat_question_delta_c1s13_v1.json`:
   - baseline pass/fail count,
   - with-scene-beats pass/fail count,
   - verdict counts (`improved`, `regressed`, `unchanged_pass`, `unchanged_fail` or equivalent),
   - `failure_diagnostic_summary`,
   - one improved or still-failing question sample if any exists.
4. **Cost:** quote `telemetry_cost.scenario_estimated_cost_usd` from `/tmp/c1s13_unit_annotations_scene_beat.json`, compare it against the prior C1S13 unit-annotation run if available in the PR body context; otherwise state that no committed cost baseline exists for this exact live annotation smoke.
5. **What stayed unchanged:** explicitly state that default retrieval without scene-beat flags remains byte-stable and that existing route-equivalence `--check-question-delta` still passes.

## §9 Acceptance Rubric

The reviewer will accept ONLY if every bullet below is true. Each bullet is paired with the §7 command that verifies it.

- [ ] Beat-enriched memory is deterministic, preserves input record order, preserves `lexical_plain`, and attaches `beat_id` only by matching `unit_id` from `dmb_recap_unit_annotations_v1` — verified by `uv run pytest tests/test_scene_beat_memory.py tests/test_session_memory_query.py -q`.
- [ ] Same-beat expansion is opt-in only; default `query_session_memory_candidate` and default `breadcrumb_query_run` behavior are unchanged — verified by `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py tests/test_cohort_baseline_run.py -q` plus existing committed check commands.
- [ ] Same-beat expansion emits auditable `why_matched` markers and never expands across missing/null beat IDs — verified by `uv run pytest tests/test_session_memory_query.py -q`.
- [ ] The cohort runner can produce a distinct scene-beat question-delta artifact without overwriting existing `cohort_l3_ab_*` artifacts and without reusing the route-equivalence schema name — verified by `uv run pytest tests/test_cohort_baseline_run.py -q` and the `/tmp/...scene_beat_question_delta...json` smoke.
- [ ] Existing invariant lanes remain green: materialized corpus memory check, default cohort baseline check, and C1S13 current question-delta check — verified by the three existing committed-check commands in §7.
- [ ] The PR reports the actual C1S13 scene-beat readout and cost, even if the result is "no improvement" or a regression — verified by PR body content and `/tmp/cohort_l3_scene_beat_question_delta_c1s13_v1.json`.
- [ ] No files outside §4 are touched — verified by `git diff --stat <base>...HEAD` filtered to §4.

> Reviewer reminder: if a bullet describes a behavioral guarantee at the harness boundary, unit-level helper tests are not sufficient. Require the `breadcrumb_query_run` / `cohort_baseline_run` boundary tests to pass.

## §10 Out-of-Band Notes

- This slice intentionally leaves canvas refresh out. If scene beats move C1S13 failures, a follow-up can update `cohort_l3_question_deep_dive_canvas_emit.py` or add a dedicated scene-beat canvas.
- This slice intentionally leaves live planner integration out. Do not add scene-beat expansion to `src/agent/planner.py` until the benchmark lane produces evidence worth promoting.
- The live unit-annotation command is cost-bearing because it calls OpenAI. The retrieval/materialization/cohort commands after that are retrieval-only and should cost `$0`.
- If the worker cannot run the live annotation smoke because no API key is available after `.env` loading, it must still complete all deterministic tests and state the blocker clearly in the PR body; the parent reviewer can run the live smoke locally before merge.
