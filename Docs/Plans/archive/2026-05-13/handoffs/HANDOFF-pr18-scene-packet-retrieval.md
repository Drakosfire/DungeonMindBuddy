---
pr_body_template: |
  ## Summary
  Wire opt-in scene-beat packet retrieval so a strongly hit beat is surfaced as a scored scene context packet instead of competing for leftover greedy expansion slots.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after running every §7 command}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

> **MERGED:** `main` @ `545bd08892481ef2169deabaa4b1739ea77d46ba` (2026-05-13T01:40:16Z); verified head **`efd2807d902fbdaac911d762efbdbad82ea2246e`**; strict **§4 allowlist 8/8**; pytest + committed `--check*` lanes green; C1S13 temp scene-packet smoke shows **`scene_beat_packet_summary`** with **`questions_with_packet_units_added` 21**, **`total_packet_units_added` 90**, populated **`packet_beat_ids`**, and **`stormspire_activity_arrival`** **`scene_beat_packets.packets[]`** carrying **`beat_id`**, **`score`**, **`first_pass_unit_ids`**, **`packet_unit_ids`**. Verdict **APPROVE** expressed as **`COMMENTED`** (self-review fallback). Cost **`$0`**.

# HANDOFF — PR #18: Scene-Packet Retrieval From Beat-Level Scores

**Created:** 2026-05-12 (UTC).  
**Status:** COMPLETED — merged; atomic doc-sync archived this handoff.  
**Parent agent:** Cursor agent; dispatcher is responsible for post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, `M2: in_progress`, `M3: complete`, `M4: not_started`). This handoff opened a candidate scene-packet retrieval lane before any default retrieval promotion.

---

## §0 Re-anchor Snapshot

- Current local `main` at handoff authoring: `07c341b5606b1aa82aa50d444e1ac8854bef5787` (`docs(plan): sync PR #17 scene-beat rebenchmark merge`). Note: at the time of authoring this doc-sync commit was local-only and `origin/main` still pointed at PR #17 merge `28e98a89e591e7203d0b163d2ab445ac11509995`. The dispatcher must push/sync the doc commit before dispatching this PR, or ensure the worker branches from a remote that already contains this handoff.
- Latest workstream state: PR #17 is merged. It built beat-enriched records, opt-in `expand_same_beat_limit`, and a C1S13 scene-beat question-delta lane, but the live C1S13 run emitted **0** `expanded_same_beat:*` hits. The flag was active and records carried beats (`records_with_beat_id: 62`, `beat_count: 12`), but greedy adjacent expansion filled the remaining hit budget first.
- Observed mechanism gap: C1S13 questions often hit the correct scene beat strongly. Example: `stormspire_activity_arrival` first-pass hit `c1s13-b003-academy-intake-briefing` with 3 units, aggregate score 11, and direct Academy tokens, but only 3 of the beat's 7 units surfaced; missing support tokens (`potions`, `runes`, `wards`) stayed outside context.
- Current blocker remains PR #12 `promotion_gate_candidate.status:none_found`; this PR is not a default flip. It tests whether scene beats should be elevated as scored context packets.
- Existing dirty/untracked files in the dispatcher's local worktree are unrelated unless explicitly listed in §4. Do not include them in this PR.

## §1 Mission

Add an explicit scene-beat packet retrieval mode that scores first-pass hits by `beat_id`, surfaces qualifying beats as scene context packets outside the greedy expansion budget, and reports whether those packets actually contributed to C1S13 retrieval.

## §2 Why this slice

- PR #17 proved beat metadata and same-beat expansion plumbing, but it did **not** prove beat-based retrieval contribution: `expanded_same_beat` was absent from the C1S13 output and baseline vs scene-beat top-hit unit lists were identical.
- The failure was architectural, not just threshold tuning: current `greedy` expansion emits adjacent rows before same-beat rows, so same-beat candidates are crowded out even when a question clearly hits a scene beat.
- The intended mechanism is now beat-level retrieval: individual units still score normally, but scored first-pass units are grouped into a scene packet. A qualifying packet surfaces a capped line-ordered slice of that beat as context and is tracked separately from adjacent/shared-route/route-family expansion.
- This PR does **not** edit corpus content, manual labels, benchmark gold, route-equivalence ranking, planner prompts, canvases, or committed `cohort_l3_ab_*` artifacts. It is candidate retrieval wiring plus deterministic proof artifacts under `/tmp`.

## §3 Authoritative Inputs

Read these in order before writing code:

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — §4 allowlist / §5 denylist / §7 verification contract.
2. **`Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md`** — Reanchor block and PR #17 session-log entry.
3. **`Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md`** — `execution_state`, PR #17 `external_pull_requests[]`, and current blocker narrative.
4. **`Docs/Plans/archive/2026-05-12/handoffs/HANDOFF-pr17-scene-beat-rebenchmark-wiring.md`** — prior slice contract and what not to repeat.
5. **`src/agent/session_memory_query.py`** — first-pass ranking, `_expand_hits`, trace payload, dispatcher args.
6. **`evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py`** — `query_session_memory_for_scenario` and `grade_natural_scenario_lanes`.
7. **`evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py`** — harness flags and output row metadata.
8. **`evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py`** — scene-beat question-delta lane from PR #17.
9. **C1S13 deterministic verification inputs**:
   - `corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_session_memory/Session 13 - The Meaty and the Dead.records_meta.jsonl`
   - `evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.gold.beats.breadcrumbed.md` (read-only verification fixture only)
   - `evals/sentence_routing_retrieval_falsification/gold/breadcrumb_query_natural_c1s13_v1.json`
   - `evals/sentence_routing_retrieval_falsification/breadcrumb_unit_annotations_gold.py::load_gold_beat_index`
10. **`tests/conftest.py`** — confirms repo env loading, though this PR should not require a live OpenAI call.

## §4 Files In Scope (Allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/agent/session_memory_query.py` | Add opt-in scene-beat packet scoring/surfacing, trace fields, and dispatcher args while preserving default behavior. |
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_grader.py` | Pass scene-packet query-spec knobs into `query_session_memory_candidate`; preserve existing lanes. |
| Modify | `evals/sentence_routing_retrieval_falsification/breadcrumb_query_run.py` | Add explicit CLI flag(s) for scene-packet mode and report packet contribution metadata per row. |
| Modify | `evals/sentence_routing_retrieval_falsification/cohort_baseline_run.py` | Extend the candidate scene-beat comparison lane so it can run with scene packets and emit packet-contribution readouts without overwriting existing artifacts. |
| Modify | `evals/sentence_routing_retrieval_falsification/README.md` | Document scene-packet mode, how it differs from PR #17 same-beat expansion, and how to run the deterministic C1S13 smoke. |
| Modify | `tests/test_session_memory_query.py` | Unit tests for beat packet scoring, thresholding, ordering, non-greedy-budget accounting, and legacy no-op behavior. |
| Modify | `tests/test_breadcrumb_query_run_lexicon_records_jsonl.py` | Harness-boundary tests for scene-packet flags, row metadata, and default byte-identity/no-op behavior. |
| Modify | `tests/test_cohort_baseline_run.py` | Cohort-boundary tests for scene-packet output shape, packet contribution telemetry, and preservation of existing `--check*` lanes. |

> The PR's `git diff --stat` MUST be expressible from this allowlist. If a path is not in this table, expect review to request reversion.

## §5 Files Explicitly OUT OF SCOPE (Denylist)

Do NOT touch any of these. Concrete collision risks are named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `corpus/**` | This is a retrieval/harness experiment, not a corpus write or blessed memory promotion. |
| `evals/sentence_routing_retrieval_falsification/gold/**` | Gold/rubric edits would confound whether scene packets changed retrieval behavior. |
| `evals/sentence_routing_retrieval_falsification/manual_labels/**` | Manual beat labels may be read as a deterministic verification fixture, but must not be edited or treated as production input. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_*.json` | Existing committed A/B artifacts stay frozen; scene-packet outputs go to `/tmp` unless a later PR scopes committed artifacts. |
| `evals/sentence_routing_retrieval_falsification/scene_beat_memory.py` | PR #17 already built beat-enriched JSONL from unit annotations; this slice should not rework the builder unless the worker stops and explains a hard blocker. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_unit_annotations_prompt.py` | Prompt tuning is out of scope; this is retrieval weighting/surfacing only. |
| `src/prompts/**` | Planner prompt behavior is out of scope. |
| `src/agent/planner.py` | Do not register scene-packet behavior in the live planner tool surface yet. |
| `canvases/**` | Canvas refresh can follow after the packet lane proves useful. |
| `.cursor/**` | No rule/skill changes in the worker PR. |
| `Docs/Plans/**` | Parent/doc-sync owns planning docs after merge; the worker should not edit this handoff, PLAN, or CHECKLIST. |
| `Backlog.md`, `Backlog-DONE.md` | Parent owns backlog state, not the external worker. |

If one of these seems genuinely required, stop and say so in the PR body before opening the PR.

## §6 Implementation Contract

### 6.1 Scene-packet scoring in `session_memory_query.py`

Add opt-in parameters to `query_session_memory_candidate` and dispatcher args:

```python
def query_session_memory_candidate(
    *,
    ...,
    scene_beat_packet_mode: bool = False,
    scene_beat_packet_threshold: int = 16,
    scene_beat_packet_top_k: int = 3,
    scene_beat_packet_unit_limit: int = 8,
    scene_beat_packet_max_packets: int = 2,
) -> CandidateQueryResult:
    ...
```

Names can differ if the worker has a cleaner local convention, but the semantics must match:

- Default mode is off and must preserve existing outputs.
- The packet scorer runs after first-pass scoring and before `_expand_hits`.
- Group first-pass scored records by non-empty `beat_id`.
- Compute a deterministic packet score from **only query/retrieval-visible data**, never expected answers, must-hit tokens, benchmark gold, or manual labels. Suggested formula:

```python
top_scores = sorted(unit_scores_for_beat, reverse=True)[:scene_beat_packet_top_k]
scene_score = max(top_scores) + sum(top_scores) + (2 * min(len(top_scores), scene_beat_packet_top_k)) + token_diversity_bonus
```

Where `token_diversity_bonus` is a small deterministic count of distinct lexical/route tokens matched by first-pass units in that beat. If implementing a different formula, document it in code/tests and keep the same anti-long-scene principle: a long beat with one weak incidental hit must not outrank a coherent beat with multiple strong hits.

### 6.2 Scene packet surfacing

When a beat qualifies:

- Surface a line-ordered packet slice from that beat:
  1. all first-pass units from the beat,
  2. then sibling units from the same `beat_id` in `line_start`, `unit_id` order,
  3. capped by `scene_beat_packet_unit_limit`.
- Packet hits should be appended after first-pass hits and before ordinary adjacent/shared-route/route-family expansions.
- Packet hits must **not** consume the ordinary greedy expansion allocation count. In trace terms: `scene_packet_units_added` is separate from `added_adjacent`, `added_shared_route`, `added_route_family`, and `added_same_beat`.
- Packet hits may exceed `max_hits` only up to an explicit packet budget. Record the effective context size in trace. Do not silently turn `max_hits=18` into unbounded context.
- Do not duplicate units already in first-pass hits.
- Do not emit packets for missing/null `beat_id`.
- Every packet-added unit must carry an auditable `why_matched` marker, for example:

```json
"why_matched": ["scene_beat_packet:c1s13-b003-academy-intake-briefing", "scene_beat_packet_score:29"]
```

Trace shape must include enough to prove contribution:

```json
"scene_beat_packets": {
  "enabled": true,
  "threshold": 16,
  "top_k": 3,
  "unit_limit": 8,
  "max_packets": 2,
  "qualified_count": 1,
  "units_added": 4,
  "packets": [
    {
      "beat_id": "c1s13-b003-academy-intake-briefing",
      "score": 29,
      "first_pass_unit_ids": ["u-L0007-01", "u-L0007-03", "u-L0007-05"],
      "packet_unit_ids": ["u-L0007-01", "u-L0007-02", "u-L0007-03", "..."]
    }
  ]
}
```

### 6.3 Harness flags and row metadata

In `breadcrumb_query_run.py`, add explicit flags that mirror PR #17 style:

```bash
--use-scene-beat-packets
--scene-beat-packet-threshold <int>      # default 16 when flag present
--scene-beat-packet-unit-limit <int>     # default 8
--scene-beat-packet-max-packets <int>    # default 2
```

When active, deep-copy each scenario before retrieval and set the corresponding `query_spec` knobs. Each row should include:

```json
"scene_beat_packets": {
  "enabled": true,
  "threshold": 16,
  "unit_limit": 8,
  "max_packets": 2,
  "qualified_count": <from trace>,
  "units_added": <from trace>,
  "packet_beat_ids": [...]
}
```

Rows without the flag should preserve existing byte identity; omit the field if needed.

### 6.4 Cohort rebenchmark lane

Extend `cohort_baseline_run.py` without changing existing `--check`, `--check-delta`, or `--check-question-delta` behavior.

Acceptable implementation:

- Add `--use-scene-beat-packets` and the packet threshold/unit-limit/max-packets flags to the existing PR #17 scene-beat question-delta path:

```bash
--scene-beat-records-jsonl <path>
--write-scene-beat-question-delta <path>
--use-scene-beat-packets
```

- Keep schema `dmb_breadcrumb_query_cohort_scene_beat_question_delta_v1` unless the shape changes incompatibly; additive packet fields are fine.
- Per-question `with_scene_beats` must include packet telemetry when packet mode is on.
- Top-level output should include a packet contribution summary, for example:

```json
"scene_beat_packet_summary": {
  "questions_with_qualified_packets": 9,
  "questions_with_packet_units_added": 9,
  "total_packet_units_added": 42,
  "packet_beat_ids": [...]
}
```

Do not regenerate or overwrite existing committed `cohort_l3_ab_*` artifacts in this PR.

### 6.5 Deterministic C1S13 verification fixture

For the §7 smoke, use the committed manual beat labels **only** to build a deterministic temporary beat-enriched records file under `/tmp`. Do not edit the manual labels and do not wire them into production code.

Use `breadcrumb_unit_annotations_gold.load_gold_beat_index` to map `unit_id -> beat_id` and write `/tmp/c1s13_gold_scene.records_meta.jsonl`. This is a reviewer fixture that avoids a live OpenAI annotation call.

## §7 Verification Commands

The worker must run every command and paste the output into the PR body. The reviewer reruns each. Every behavioral guarantee in §9 must be exercised by at least one command here at the owning boundary.

```bash
# Unit-level: packet scoring, packet surfacing, trace metadata, and legacy no-op behavior.
uv run pytest tests/test_session_memory_query.py -q

# Harness/cohort boundary: flags, default no-op invariants, and packet contribution shape.
uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py tests/test_cohort_baseline_run.py -q

# Existing invariant lanes remain green.
uv run python scripts/materialize_session_memory.py --all-blessed --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --check
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json --check-question-delta evals/sentence_routing_retrieval_falsification/artifacts/baselines/cohort_l3_ab_question_delta_c1s13_v1.json

# Deterministic C1S13 scene-packet smoke: build beat-enriched records from committed manual beat labels as a verification fixture only.
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

out.write_text("\\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\\n", encoding="utf-8")
print({"out": str(out), "rows": len(rows), "records_with_beat_id": sum(1 for row in rows if row.get("beat_id")), "beat_count": len(set(beat_by_unit.values()))})
PY

# Scene-packet question-delta smoke. This must show packet contribution, not just enabled flags.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --scene-beat-records-jsonl /tmp/c1s13_gold_scene.records_meta.jsonl \
  --write-scene-beat-question-delta /tmp/cohort_l3_scene_packet_question_delta_c1s13_v1.json \
  --use-scene-beat-packets

# Readout proof: print verdict summary + packet contribution summary + one Stormspire packet sample.
uv run python - <<'PY'
import json
from pathlib import Path

payload = json.loads(Path("/tmp/cohort_l3_scene_packet_question_delta_c1s13_v1.json").read_text(encoding="utf-8"))
print("summary", payload.get("summary"))
print("failure_diagnostic_summary", payload.get("failure_diagnostic_summary"))
print("scene_beat_packet_summary", payload.get("scene_beat_packet_summary"))
for scenario in payload.get("scenarios", []):
    for question in scenario.get("questions", []):
        if question.get("question_id") == "stormspire_activity_arrival":
            packets = (question.get("with_scene_beats", {}).get("full_result", {}).get("trace", {}).get("scene_beat_packets") or question.get("with_scene_beats", {}).get("scene_beat_packets"))
            print("stormspire_activity_arrival_packets", json.dumps(packets, indent=2, ensure_ascii=False))
            raise SystemExit(0)
raise SystemExit("stormspire_activity_arrival not found")
PY
```

## §8 Reporting Contract

In the PR body the worker MUST include:

1. **`git diff --stat` filtered to §4 allowlist paths only.** Not the whole-tree stat.
2. **Verbatim §7 output** — pass/fail counts and the C1S13 packet readout.
3. **A one-paragraph explanation of how packet scoring works** — name the formula and why long weak beats do not dominate.
4. **C1S13 contribution readout** from `/tmp/cohort_l3_scene_packet_question_delta_c1s13_v1.json`:
   - `summary`
   - `failure_diagnostic_summary`
   - `scene_beat_packet_summary`
   - `stormspire_activity_arrival` packet sample, including packet beat ID, score, first-pass unit IDs, and packet unit IDs.
5. **What stayed unchanged:** default retrieval without scene-packet flags remains byte-stable/no-op; existing route-equivalence `--check-question-delta` still passes; no committed `cohort_l3_ab_*` artifacts changed.
6. **Cost:** `$0` expected. This PR must not run a live LLM call.

## §9 Acceptance Rubric

The reviewer will accept ONLY if every bullet below is true. Each bullet is paired with the §7 command that verifies it.

- [ ] Beat packet scoring is deterministic, uses only retrieval-visible first-pass hit data, and avoids long-scene domination via capped top-k / diversity weighting — verified by `uv run pytest tests/test_session_memory_query.py -q`.
- [ ] A qualifying beat surfaces packet units with auditable `scene_beat_packet:<beat_id>` markers and separate trace fields (`qualified_count`, `units_added`, packet score, first-pass units, packet unit IDs) — verified by `uv run pytest tests/test_session_memory_query.py -q` and the C1S13 `/tmp` readout command.
- [ ] Scene-packet units do **not** consume ordinary greedy expansion stats; `scene_packet_units_added` or equivalent is separate from `added_adjacent`, `added_shared_route`, `added_route_family`, and `added_same_beat` — verified by `uv run pytest tests/test_session_memory_query.py -q`.
- [ ] Default behavior remains unchanged when scene-packet flags are absent — verified at the harness boundary by `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py tests/test_cohort_baseline_run.py -q` plus the existing committed `--check*` commands.
- [ ] `breadcrumb_query_run.py` emits row-level packet metadata only when packet mode is active and omits it on default lanes if needed for byte identity — verified by `uv run pytest tests/test_breadcrumb_query_run_lexicon_records_jsonl.py -q`.
- [ ] `cohort_baseline_run.py` can produce a C1S13 scene-packet question-delta artifact under `/tmp` with top-level packet contribution summary and per-question packet metadata; it must not overwrite committed `cohort_l3_ab_*` artifacts — verified by `uv run pytest tests/test_cohort_baseline_run.py -q` and the `/tmp/cohort_l3_scene_packet_question_delta_c1s13_v1.json` smoke.
- [ ] The deterministic C1S13 smoke proves actual packet contribution, not just active flags: the readout must show at least one question with `units_added > 0` and a concrete `stormspire_activity_arrival` packet sample if that beat qualifies under the chosen threshold — verified by the final §7 readout command.
- [ ] No files outside §4 are touched — verified by `git diff --stat <base>...HEAD` filtered to §4.

> Reviewer reminder: if a bullet describes a behavioral guarantee at a particular boundary (retriever, harness, or cohort runner), the §7 command that verifies it MUST exercise it at that boundary. Unit-only coverage is necessary but not sufficient.

## §10 Out-of-Band Notes

- The manual C1S13 beat-label markdown is a deterministic **verification fixture** for this PR. It is not a production retrieval input and must not be edited.
- If the packet mode improves C1S13, a later PR may commit a refreshed artifact or canvas. Do not mix that visualization/output churn into this wiring PR.
- If the packet mode only improves via larger context budget, compare against a no-beat wider-hit baseline in the PR body. We need to know whether packets are earning their keep, not merely whether more text helps.
