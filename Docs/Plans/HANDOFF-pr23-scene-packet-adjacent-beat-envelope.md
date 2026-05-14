---
pr_body_template: |
  ## Summary
  Implement Option A scene-continuity packeting by extending scene-beat packet qualification to admit adjacent-beat envelopes for replay/ambush/fight-style queries, while preserving default retrieval behavior when packet mode is off.

  ## Verification (verbatim §7)
  {{TODO: paste command outputs after the worker runs §7}}

  ## `git diff --stat` (§4 paths only)
  ```text
  {{TODO}}
  ```
---

# HANDOFF — PR #23 Option A scene-continuity packet envelopes (adjacent-beat stitching)

**Created:** 2026-05-13 (UTC).  
**Status:** ACTIVE — dispatch this to one external/Codex subagent. One PR. Do not split into multiple PRs.  
**Parent agent:** Cursor agent; dispatcher is responsible for the post-merge doc-sync of `Docs/Plans/CHECKLIST-dynamic-lexical-retrieval-rollout.md` and `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` per `.cursor/rules/external-agent-pr-loop.mdc`.  
**Plan anchor:** `Docs/Plans/PLAN-split-corpus-retrieval-to-autonomous-demo.md` (`active_phase: B`, milestone progress `M2: in_progress`, `M3: complete`). This handoff advances the C1S13 falsification lane under M2.

---

## §1 Mission

Implement Option A retrieval-side scene continuity by extending scene-beat packeting to stitch adjacent beats for replay/ambush/fight intent queries, and prune duplicate context content in packet-appended hits, without introducing new schema fields or changing behavior when packet mode is disabled.

## §2 Why this slice (context for the subagent)

- PR #17 and PR #18 added scene-beat expansion and packeting surfaces, but packets currently group by a single `beat_id` and do not reliably stitch the morgue ambush continuity across adjacent beats.
- Lane-1 deep-dive evidence (`Docs/Plans/C1S13-lane1-sewer-meat-monster-deepdive.md`) shows replay-style asks need continuity across `c1s13-b009`, `c1s13-b010`, `c1s13-b011`; ordering is already deterministic after retrieval, so retrieval coverage is the bottleneck.
- This slice does **not** add a new `scene_id` field, does **not** modify prompt/annotation schema, does **not** edit gold files or committed baseline artifacts, and does **not** touch canvas emitters.

## §3 Authoritative inputs (read these in this order, before writing any code)

1. **`.cursor/rules/external-agent-pr-loop.mdc`** — the §4 allowlist / §5 denylist / §7 verification contract that this PR will be reviewed against.
2. `src/agent/session_memory_query.py` — current `_compute_scene_beat_packets` and `query_session_memory_candidate` packet wiring.
3. `Docs/Plans/C1S13-lane1-sewer-meat-monster-deepdive.md` — concrete failure evidence and target continuity behavior.
4. `evals/sentence_routing_retrieval_falsification/README.md` (§ candidate scene-beat packets) — existing fixture/smoke flow.
5. `tests/test_session_memory_query.py` and `tests/test_cohort_baseline_run.py` — canonical test layout for packet behavior and cohort-level schema behavior.
6. **`tests/conftest.py`** — confirm session-autouse `load_dungeonmindbuddy_dotenv()` is wired so live tests don't need exported keys (see `.cursor/rules/dungeonbuddy-environment.mdc`).

## §4 Files in scope (allowlist)

| Action | Path | Purpose |
|---|---|---|
| Modify | `src/agent/session_memory_query.py` | Add adjacent-beat envelope packet logic for replay/ambush/fight intent while preserving current packet caps and deterministic ordering. |
| Modify | `tests/test_session_memory_query.py` | Add focused unit tests for adjacent-beat packet qualification/admission and no-op behavior when conditions are not met. |
| Modify | `tests/test_cohort_baseline_run.py` | Add/adjust boundary test(s) to ensure scene-beat packet mode output shape remains stable with new packet trace fields/behavior. |

> The agent's expected `git diff --stat` MUST be expressible from this allowlist. If a path is not in this table, the worker will be told to revert it during review.

## §5 Files explicitly OUT OF SCOPE (denylist)

Do NOT touch any of these. Concrete collision risks named alongside the path:

| Path | Why this PR must not touch it |
|---|---|
| `evals/sentence_routing_retrieval_falsification/gold/*.json` | Gold edits can deflate/shift rubric scope; this slice is retrieval mechanics only. |
| `evals/sentence_routing_retrieval_falsification/artifacts/baselines/*.json` | Committed baseline/question-delta artifacts are frozen outputs and should only change in a dedicated regeneration slice. |
| `*.canvas.tsx` (presentation) | Presentation artifacts are out-of-scope and often regenerated locally; touching them hides retrieval-only intent. |
| `evals/sentence_routing_retrieval_falsification/cohort_*_canvas_emit.py` | Emitter/presentation logic is not part of Option A retrieval mechanics. |
| `evals/sentence_routing_retrieval_falsification/breadcrumb_unit_annotations_*` | No schema/prompt migration to `scene_id` in this slice; avoid mixing Option B work. |
| `src/prompts/*.py` | Prompt changes are out-of-scope; this slice is deterministic retrieval behavior only. |

If the worker thinks one of these is genuinely needed, it must stop and ask in the PR description before opening the PR.

## §6 Implementation contract

### `src/agent/session_memory_query.py` changes

```python
def _query_has_scene_replay_intent(query: str, query_tokens: list[str]) -> bool: ...

def _compute_scene_beat_packets(
    *,
    first_pass_scored: list[tuple[int, dict[str, Any], list[str]]],
    filtered: list[dict[str, Any]],
    threshold: int,
    top_k: int,
    unit_limit: int,
    max_packets: int,
    # new knobs for Option A:
    adjacent_beat_window: int = 1,
    replay_intent: bool = False,
) -> list[dict[str, Any]]: ...
```

Expected behavior contract:

- Keep current per-beat packet logic as baseline behavior.
- In packet mode, when `replay_intent` is true, allow packet assembly to include sibling records from adjacent beats around qualified seed beats (deterministically bounded by `adjacent_beat_window` and existing caps).
- Preserve existing output schema fields consumed by harness/tests (`beat_id`, `score`, `first_pass_unit_ids`, `packet_unit_ids`) and trace shape (`scene_beat_packets`).
- Do not require `scene_id` or any new record field in this slice.
- When appending packet records, dedupe not only by `unit_id` but also by canonical content identity so identical context units are not duplicated in `hits` for this workflow. Preferred key: `text_blake3` when present; fallback to normalized `lexical_plain` string if hash is absent.

Determinism / ordering rules:

- Preserve stable ordering by `(line_start, unit_id)` when constructing packet record order.
- Do not mutate input records in place.
- Respect existing packet caps (`scene_beat_packet_unit_limit`, `scene_beat_packet_max_packets`) and avoid unbounded expansions.

### Test expectations

```python
def test_scene_beat_packets_replay_intent_stitches_adjacent_beats() -> None: ...
def test_scene_beat_packets_non_replay_keeps_single_beat_behavior() -> None: ...
def test_scene_beat_packets_prune_duplicate_content_units() -> None: ...
```

Boundary behavior:

- Keep existing cohort scene-beat question-delta schema contract stable.
- Ensure default behavior without packet mode remains unchanged.

## §7 Verification commands

The worker must run **every** command and paste the output into the PR body. The reviewer reruns each. **Every behavioral guarantee in §9 below must be exercised by at least one command here, at the boundary the guarantee describes.**

```bash
# Existing suites that own packet behavior and cohort boundary shape.
uv run pytest tests/test_session_memory_query.py -q
uv run pytest tests/test_cohort_baseline_run.py -q

# Boundary no-regression for default committed C1S13 question-delta lane.
uv run python -m evals.sentence_routing_retrieval_falsification.cohort_baseline_run \
  --manifest evals/sentence_routing_retrieval_falsification/cohorts/c1s13_v1.json \
  --check-question-delta

# Replay-intent smoke over beat-annotated C1S13 records: packet trace should qualify and add units.
uv run python - <<'PY'
import json
from pathlib import Path
from evals.sentence_routing_retrieval_falsification.breadcrumb_unit_annotations_gold import load_gold_beat_index
from src.agent.session_memory_query import load_session_memory_records_jsonl, query_session_memory_candidate

records_path = Path("corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_session_memory/Session 13 - The Meaty and the Dead.records_meta.jsonl")
gold_path = Path("evals/sentence_routing_retrieval_falsification/manual_labels/Session 13 - The Meaty and the Dead.gold.beats.breadcrumbed.md")
beat_by_unit = {}
for beat in load_gold_beat_index(gold_path):
    for unit_id in beat.unit_ids:
        beat_by_unit[str(unit_id)] = beat.beat_id
rows = []
for line in records_path.read_text(encoding="utf-8").splitlines():
    if not line.strip():
        continue
    row = json.loads(line)
    bid = beat_by_unit.get(str(row.get("unit_id")))
    if bid:
        row["beat_id"] = bid
    rows.append(row)
res = query_session_memory_candidate(
    records=rows,
    query="Create a beat by beat replay of the morgue ambush fight.",
    campaign_id="longmont-c1",
    max_hits=18,
    expand_context=True,
    scene_beat_packet_mode=True,
    scene_beat_packet_threshold=16,
    scene_beat_packet_top_k=3,
    scene_beat_packet_unit_limit=8,
    scene_beat_packet_max_packets=2,
)
trace = res.trace.get("scene_beat_packets") or {}
print({
    "qualified_count": trace.get("qualified_count"),
    "units_added": trace.get("units_added"),
    "packet_beat_ids": [p.get("beat_id") for p in trace.get("packets", [])],
})
if int(trace.get("qualified_count") or 0) < 1:
    raise SystemExit("expected at least one qualified scene packet")
if int(trace.get("units_added") or 0) < 1:
    raise SystemExit("expected scene packet mode to add at least one unit")

# Content-level dedupe assertion for this workflow.
seen_hashes = set()
dup_hashes = []
for hit in res.hits:
    uid = str(hit.get("unit_id") or "")
    rec = next((r for r in rows if str(r.get("unit_id") or "") == uid), None)
    if not rec:
        continue
    h = str(rec.get("text_blake3") or "").strip()
    if not h:
        continue
    if h in seen_hashes:
        dup_hashes.append(h)
    seen_hashes.add(h)
if dup_hashes:
    raise SystemExit(f"duplicate text_blake3 values remained in hits: {dup_hashes[:3]}")
PY
```

## §8 Reporting contract

In the PR body the worker MUST include:

1. **`git diff --stat` filtered to the §4 allowlist paths only.** Not the whole-tree stat (mixes in dispatcher's uncommitted work).
2. **Verbatim §7 output** — pass/fail counts, last 20 lines on failure.
3. **One-paragraph "what stayed unchanged"** — call out at least: default lane without packet mode unchanged, no schema migration to `scene_id`, and no gold/artifact/canvas edits.

## §9 Acceptance rubric

The reviewer will accept ONLY if every bullet below is true. Each bullet is paired with the §7 command that verifies it.

- [ ] Replay-intent scene packet mode can qualify at least one packet and add units on C1S13 beat-annotated records — verified by the replay-intent smoke `python - <<'PY' ...` command in §7.
- [ ] Packet behavior remains deterministic and existing packet/cohort tests stay green — verified by `uv run pytest tests/test_session_memory_query.py -q` and `uv run pytest tests/test_cohort_baseline_run.py -q`.
- [ ] Default committed C1S13 question-delta lane remains stable (`--check-question-delta` still passes) — verified by the cohort `--check-question-delta` command in §7.
- [ ] Packet-appended replay workflow prunes duplicate content units (content identity dedupe, not just unit-id dedupe) — verified by the replay-intent smoke duplicate-hash assertion in §7 and the new unit test in `tests/test_session_memory_query.py`.
- [ ] Scope guarantee: no files outside §4 are touched — verified by `git diff --stat <base>...HEAD` filtered to §4.

> **Reviewer reminder:** if a bullet describes a behavioral guarantee at a particular boundary (harness, dispatcher, writer), the §7 command that verifies it MUST exercise it at that boundary. Loader-side or unit-side coverage is necessary but not sufficient.

## §10 Out-of-band notes (optional)

- This slice intentionally does **not** introduce `scene_id` schema fields; that is Option B and must be a separate PR if needed.
- This slice intentionally does **not** edit benchmark gold wording or committed baseline artifacts; those are handled in dedicated rubric/data-sync slices.

