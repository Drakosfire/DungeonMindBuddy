"""Tests for the breadcrumb query canvas payload generator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from evals.sentence_routing_retrieval_falsification import (
    breadcrumb_query_canvas_payload as gen,
)


# ---------------------------------------------------------------------------
# Synthetic fixtures
# ---------------------------------------------------------------------------


def _make_gold() -> dict:
    return {
        "schema": "dmb_breadcrumb_query_natural_gold_v1",
        "campaign_id": "longmont-c2",
        "default_query_spec": {
            "session_min": 20,
            "session_max": 20,
            "max_hits": 12,
            "expand_context": True,
            "expand_seed_hits": 5,
            "expand_adjacent_window": 2,
            "expand_shared_route_limit": 3,
            "expand_route_family_limit": 3,
            "expand_first_pass_cap": 9,
        },
        "scenarios": [
            {
                "id": "nat_captain_after_forest",
                "question": "What happened to the captain after the migrating forest pulled back?",
                "notes": "Synthetic gold note for captain after forest.",
                "expected_answer": "Captain Lysandra returns disoriented but recovering.",
                "must_hit_tokens": ["captain", "forest", "tower"],
                "expect_route_substrings": [
                    "NPCs/captain_lysandra_ironveil",
                    "NPCs/sara_mirathorn_operator",
                ],
                "min_context_support_ratio": 0.75,
            },
            {
                "id": "nat_voices_tower_officer",
                "question": "Does the recap tie voices or a tower drawing to a specific officer?",
                "notes": "Voices/tower drawing tied to a specific officer.",
                "expected_answer": "Yes — Captain Lysandra ties voices to a tower drawing.",
                "must_hit_tokens": ["voices", "tower", "captain", "blueprint"],
                "expect_unit_id_substrings": ["u-L0019-05", "u-L0019-10"],
                "expect_route_substrings": ["NPCs/captain_lysandra_ironveil"],
                "must_not_cooccur": {"blueprint": ["no mention of any drawing"]},
                "min_context_support_ratio": 1.0,
            },
        ],
    }


def _make_hit(*, unit_id: str, score: int, route_strings: list[str]) -> dict:
    return {
        "hit_id": unit_id,
        "unit_id": unit_id,
        "score": score,
        "line_start": 1,
        "line_end": 1,
        "source_recap_path": "synthetic/recap.md",
        "routes": [{"normalized_route": r} for r in route_strings],
        "why_matched": ["lex"],
    }


def _make_report(*, captain_pass: bool = False, voices_pass: bool = False) -> dict:
    captain_hits = [
        _make_hit(
            unit_id="u-L0017-04",
            score=17,
            route_strings=[
                "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                "Longmont Campaign/Campaign 2/NPCs/sara_mirathorn_operator/",
            ],
        ),
        _make_hit(
            unit_id="u-L0019-13",
            score=15,
            route_strings=[
                "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
            ],
        ),
        _make_hit(
            unit_id="u-L0019-11",
            score=14,
            route_strings=[
                "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
            ],
        ),
    ]
    voices_hits = [
        _make_hit(
            unit_id="u-L0019-13",
            score=27,
            route_strings=[
                "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                "Elderwyld/Unknown Sites/Voices Tower/",
            ],
        ),
        _make_hit(
            unit_id="u-L0019-06",
            score=21,
            route_strings=[
                "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
            ],
        ),
    ]
    if voices_pass:
        # Add the expected drawing/blueprint units to make hard gates pass.
        voices_hits.extend(
            [
                _make_hit(
                    unit_id="u-L0019-05",
                    score=18,
                    route_strings=[
                        "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    ],
                ),
                _make_hit(
                    unit_id="u-L0019-10",
                    score=18,
                    route_strings=[
                        "Longmont Campaign/Campaign 2/NPCs/captain_lysandra_ironveil/",
                    ],
                ),
            ]
        )

    captain_row = {
        "scenario_id": "nat_captain_after_forest",
        "ok": bool(captain_pass),
        "violations": [] if captain_pass else ["llm_context_support_below_threshold"],
        "context_support_ratio": 1.0,
        "llm_context_support_ratio": 0.5 if not captain_pass else 0.85,
        "embedding_similarity": {
            "model": "text-embedding-3-large",
            "cosine_similarity": 0.7396,
            "cost_usd": 3.055e-05,
        },
        "top_hit": dict(captain_hits[0]),
        "hit_count": len(captain_hits),
        "hit_context_preview": "Lysandra after forest, fragmented memory.",
        "llm_answer_preview": "Captain Lysandra returns disoriented; tea recovers her.",
        "llm_usage": {"input_tokens": 900, "output_tokens": 180, "cached_input_tokens": 0},
        "llm_cost_usd": 0.0040,
        "llm_model": "gpt-5.3-chat-latest",
        "expected_answer": "Captain Lysandra returns disoriented but recovering.",
        "full_result": {
            "campaign_id": "longmont-c2",
            "contract": "session_memory_candidate_v1",
            "schema": "session_memory_candidate_v1",
            "query": "captain forest",
            "hits": captain_hits,
            "trace": {
                "max_hits": 12,
                "expand_context": True,
                "expand_first_pass_cap": 9,
                "examined_records": 87,
                "filtered_records": 70,
                "matched_records": 12,
                "returned_hits": 3,
            },
        },
    }

    voices_row = {
        "scenario_id": "nat_voices_tower_officer",
        "ok": bool(voices_pass),
        "violations": (
            []
            if voices_pass
            else [
                "missing_expected_unit_id_hit",
                "context_support_below_threshold",
            ]
        ),
        "context_support_ratio": 0.75 if not voices_pass else 1.0,
        "llm_context_support_ratio": 0.75 if not voices_pass else 1.0,
        "embedding_similarity": {
            "model": "text-embedding-3-large",
            "cosine_similarity": 0.7366,
            "cost_usd": 2.5e-05,
        },
        "top_hit": dict(voices_hits[0]),
        "hit_count": len(voices_hits),
        "hit_context_preview": "Voices and tower context.",
        "llm_answer_preview": "Voices tied to Captain Lysandra; drawing absent.",
        "llm_usage": {"input_tokens": 880, "output_tokens": 140, "cached_input_tokens": 0},
        "llm_cost_usd": 0.0035,
        "llm_model": "gpt-5.3-chat-latest",
        "expected_answer": "Yes — Captain Lysandra ties voices to a tower drawing.",
        "full_result": {
            "campaign_id": "longmont-c2",
            "contract": "session_memory_candidate_v1",
            "schema": "session_memory_candidate_v1",
            "query": "voices tower officer",
            "hits": voices_hits,
            "trace": {
                "max_hits": 12,
                "expand_context": True,
                "expand_first_pass_cap": 9,
            },
        },
    }

    return {
        "records_source": "/tmp/synthetic_records.jsonl",
        "gold": "/tmp/synthetic_gold.json",
        "gold_schema": "dmb_breadcrumb_query_natural_gold_v1",
        "all_ok": captain_pass and voices_pass,
        "results": [captain_row, voices_row],
        "llm_enabled": True,
        "llm_model": "gpt-5.3-chat-latest",
        "embedding_model": "text-embedding-3-large",
        "aggregate_llm_cost_usd": 0.0075,
        "aggregate_embedding_cost_usd": 0.0001,
        "scenario_estimated_cost_usd": 0.0076,
        "embedding_similarity_enabled": True,
    }


def _make_records_text() -> dict[str, str]:
    return {
        "u-L0017-04": "Sara reports mumbling about the forest leaving and time behaving strangely.",
        "u-L0019-05": "She finds Lysandra drawing in the dirt.",
        "u-L0019-06": "She says it is a tower where the voices are coming from.",
        "u-L0019-10": "It appears to be a top-down blueprint of a tower and is very well done.",
        "u-L0019-11": "Finally, after drinking the tea, Lysandra comes out of the spell.",
        "u-L0019-13": "Lysandra remembers voices in the dark after the group left into the forest.",
    }


# ---------------------------------------------------------------------------
# build_payload — summary, suite, run rows
# ---------------------------------------------------------------------------


def test_build_payload_summary_counts_pass_fail_and_cost() -> None:
    gold = _make_gold()
    report = _make_report(captain_pass=False, voices_pass=False)

    payload = gen.build_payload(report=report, gold=gold, records_text=_make_records_text())

    summary = payload["summary"]
    assert payload["schema"] == gen.PAYLOAD_SCHEMA
    assert summary["executableCount"] == 2
    assert summary["llmPassCount"] == 0
    assert summary["llmFailCount"] == 2
    assert summary["llmPassLabel"] == "0/2"
    assert summary["expandEnabled"] is True
    assert summary["expandFirstPassCap"] == 9
    assert summary["expansionLabel"] == "9 lexical + 3 expansion slots"
    assert summary["costLabel"] == "$0.0076"
    assert summary["llmModel"] == "gpt-5.3-chat-latest"
    assert summary["embeddingModel"] == "text-embedding-3-large"

    pass_tile = next(t for t in summary["statTiles"] if t["label"].startswith("Hard-gate pass"))
    assert pass_tile["value"] == "0/2"
    assert pass_tile["tone"] == "warning"


def test_build_payload_summary_handles_disabled_expansion() -> None:
    gold = _make_gold()
    gold["default_query_spec"]["expand_context"] = False
    gold["default_query_spec"].pop("expand_first_pass_cap", None)
    report = _make_report()

    payload = gen.build_payload(report=report, gold=gold)
    summary = payload["summary"]

    assert summary["expandEnabled"] is False
    assert summary["expandFirstPassCap"] is None
    assert summary["expansionLabel"] == "12 lexical hits"
    assert any(t["label"].startswith("Max hits (12 lexical hits)") for t in summary["statTiles"])


def test_build_payload_uses_deterministic_pass_count_when_provided() -> None:
    gold = _make_gold()
    report = _make_report()
    deterministic = _make_report(captain_pass=True, voices_pass=False)

    payload = gen.build_payload(
        report=report,
        gold=gold,
        deterministic=deterministic,
        records_text=_make_records_text(),
    )
    summary = payload["summary"]

    assert summary["deterministicPassCount"] == 1
    assert summary["deterministicTotal"] == 2
    assert summary["deterministicPassLabel"] == "1/2"


def test_build_payload_run_rows_match_results() -> None:
    gold = _make_gold()
    report = _make_report()
    payload = gen.build_payload(report=report, gold=gold, records_text=_make_records_text())

    rows = payload["runRows"]
    assert [row[0] for row in rows] == [
        "nat_captain_after_forest",
        "nat_voices_tower_officer",
    ]
    assert [row[1] for row in rows] == ["FAIL", "FAIL"]
    assert rows[0][6] == "—"
    assert rows[0][7] == "2/2@9"
    assert rows[1][6] == "0/2@9"
    assert rows[1][7] == "1/1@9"
    assert rows[0][8] == "llm_context_support_below_threshold"
    assert rows[1][8].startswith("missing_expected_unit_id_hit")
    assert rows[0][4] == "0.7396"


def test_build_payload_summary_prepends_macro_top_k_recall_tiles() -> None:
    gold = _make_gold()
    report = _make_report()
    payload = gen.build_payload(report=report, gold=gold, records_text=_make_records_text())
    labels = [t["label"] for t in payload["summary"]["statTiles"]]
    assert any(x.startswith("Macro unit recall") for x in labels)
    assert any(x.startswith("Macro route recall") for x in labels)


def test_meta_session_hit_preview_is_compact_not_lexical_blob() -> None:
    hit = {
        "unit_id": "meta-session-0020-locations",
        "routes": [{"normalized_route": "Elderwyld/Cities and Towns/Mirathorn"}],
    }
    blob_records = {"meta-session-0020-locations": "session locations location places " * 50}
    preview = gen._hit_preview_text(hit, blob_records)
    assert "Session location index" in preview
    assert "Mirathorn" in preview
    assert preview != blob_records["meta-session-0020-locations"]


def test_build_payload_suite_rows_include_deferred_row_even_if_absent_from_gold() -> None:
    gold = _make_gold()
    report = _make_report()
    payload = gen.build_payload(report=report, gold=gold, records_text=_make_records_text())

    suite = payload["suiteRows"]
    suite_ids = [row[1] for row in suite]
    assert suite_ids == gen.SUITE_ROW_ORDER
    deferred = [row for row in suite if row[0].lower() == "deferred"]
    assert len(deferred) == 1
    assert deferred[0][1] == "q_timeline_vs_recap"


# ---------------------------------------------------------------------------
# Scenario card derivation: missing/recovered evidence + critique
# ---------------------------------------------------------------------------


def test_scenario_card_flags_missing_expected_units_and_routes() -> None:
    gold = _make_gold()
    report = _make_report()
    payload = gen.build_payload(report=report, gold=gold, records_text=_make_records_text())

    voices_card = next(
        c for c in payload["scenarioCards"] if c["id"] == "nat_voices_tower_officer"
    )
    missing = "\n".join(voices_card["missingExpected"])
    assert "u-L0019-05" in missing
    assert "u-L0019-10" in missing
    # The expected route is present in the synthetic hits, so it should not be flagged.
    assert "Missing expected route hit" not in missing
    assert "Failed" in voices_card["critique"] or "Missing expected units" in voices_card["critique"]


def test_scenario_card_recovers_evidence_against_baseline() -> None:
    """Baseline has no drawing/blueprint hits; current report has both."""
    gold = _make_gold()
    report = _make_report(voices_pass=True)
    baseline = _make_report(voices_pass=False)

    payload = gen.build_payload(
        report=report,
        gold=gold,
        baseline=baseline,
        records_text=_make_records_text(),
    )
    voices_card = next(
        c for c in payload["scenarioCards"] if c["id"] == "nat_voices_tower_officer"
    )
    recovered_line = next(
        line for line in voices_card["missingExpected"] if line.startswith("Recovered vs baseline")
    )
    assert "u-L0019-05" in recovered_line
    assert "u-L0019-10" in recovered_line
    assert "Recovered units vs baseline" in voices_card["critique"]


def test_scenario_card_renders_required_evidence_and_metrics() -> None:
    gold = _make_gold()
    report = _make_report()
    payload = gen.build_payload(report=report, gold=gold, records_text=_make_records_text())

    captain = next(c for c in payload["scenarioCards"] if c["id"] == "nat_captain_after_forest")
    assert "Tokens: captain, forest, tower" in captain["requiredEvidence"]
    assert any(item.startswith("Routes:") for item in captain["requiredEvidence"])
    assert captain["metrics"]["embeddingSimilarity"] == "0.7396"
    assert captain["metrics"]["topKUnitEvidence"] == "—"
    assert captain["metrics"]["topKRouteEvidence"] == "2/2@9"
    assert captain["metrics"]["topHit"].startswith("u-L0017-04, score 17")
    assert captain["retrievedHits"][0]["unit"] == "u-L0017-04"
    assert "captain_lysandra_ironveil" in captain["retrievedHits"][0]["routes"]


# ---------------------------------------------------------------------------
# Generated-block rendering and canvas update
# ---------------------------------------------------------------------------


def _wrap_canvas(block: str) -> str:
    return (
        "import { Stack } from 'cursor/canvas';\n"
        f"{block}\n"
        "\nexport default function Canvas() { return null; }\n"
    )


def test_build_payload_prepends_cohort_callout_and_kernel_clause() -> None:
    gold = _make_gold()
    gold["default_query_spec"]["tokenizer_mode"] = "restrained"
    gold["default_query_spec"]["expansion_allocation_mode"] = "greedy"
    report = _make_report()
    cohort = {
        "aggregate": {
            "passes_per_run": [5, 5, 5],
            "pass_count_mean": 5.0,
            "cost_usd": {"mean": 0.047},
        },
        "config": {
            "tokenizer_mode": "restrained",
            "expansion_allocation_mode": "greedy",
            "expand_first_pass_cap": 9,
        },
        "promotion_gate": {"no_high_signal_regression_all_runs": True},
    }
    payload = gen.build_payload(report=report, gold=gold, cohort_summary=cohort)
    assert payload["callouts"][0]["title"] == "LLM cohort (multi-run)"
    assert "N=3 cohort" in payload["callouts"][0]["body"]
    assert "tokenizer_mode=restrained" in payload["callouts"][1]["body"]
    assert "expansion_allocation_mode=greedy" in payload["callouts"][1]["body"]


def test_render_generated_block_is_stable_and_idempotent() -> None:
    gold = _make_gold()
    report = _make_report()
    payload = gen.build_payload(report=report, gold=gold)

    block_1 = gen.render_generated_block(payload)
    block_2 = gen.render_generated_block(payload)
    assert block_1 == block_2
    assert gen.CANVAS_BLOCK_BEGIN in block_1
    assert gen.CANVAS_BLOCK_END in block_1
    assert "const canvasData = {" in block_1


def test_update_canvas_text_replaces_only_generated_block(tmp_path: Path) -> None:
    initial_block = (
        f"{gen.CANVAS_BLOCK_BEGIN}\n"
        "const canvasData = { stub: true } as const;\n"
        f"{gen.CANVAS_BLOCK_END}"
    )
    canvas_text = _wrap_canvas(initial_block)

    payload = gen.build_payload(report=_make_report(), gold=_make_gold())
    new_block = gen.render_generated_block(payload)

    out = gen.update_canvas_text(canvas_text, new_block)
    # Imports and default export survive; only the generated block changed.
    assert out.startswith("import { Stack } from 'cursor/canvas';\n")
    assert out.endswith("export default function Canvas() { return null; }\n")
    assert "stub: true" not in out
    assert '"schema": "breadcrumb_query_canvas_payload_v1"' in out

    # Idempotent: running update again with the same block must not change the file.
    out_again = gen.update_canvas_text(out, new_block)
    assert out_again == out


def test_update_canvas_text_raises_without_markers(tmp_path: Path) -> None:
    canvas_text = "// no markers here\nexport default function Canvas() { return null; }\n"
    with pytest.raises(ValueError, match="missing the generated-block markers"):
        gen.update_canvas_text(canvas_text, "anything")


# ---------------------------------------------------------------------------
# CLI behavior: --check stale guard
# ---------------------------------------------------------------------------


def test_cli_check_passes_for_fresh_canvas_and_fails_when_stale(tmp_path: Path) -> None:
    gold_path = tmp_path / "gold.json"
    report_path = tmp_path / "report.json"
    canvas_path = tmp_path / "canvas.tsx"

    gold = _make_gold()
    report = _make_report()
    gold_path.write_text(json.dumps(gold), encoding="utf-8")
    report_path.write_text(json.dumps(report), encoding="utf-8")

    # Seed the canvas with a stub block so the generator can replace it.
    seed_block = (
        f"{gen.CANVAS_BLOCK_BEGIN}\n"
        "const canvasData = { stub: true } as const;\n"
        f"{gen.CANVAS_BLOCK_END}"
    )
    canvas_path.write_text(_wrap_canvas(seed_block), encoding="utf-8")

    repo_root = Path(__file__).resolve().parents[1]
    cmd_check_stale = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload",
        "--report",
        str(report_path),
        "--gold",
        str(gold_path),
        "--canvas-tsx",
        str(canvas_path),
        "--check",
    ]
    res_stale = subprocess.run(cmd_check_stale, cwd=repo_root, capture_output=True, text=True)
    assert res_stale.returncode == 1, res_stale.stderr
    assert "stale" in res_stale.stderr

    cmd_refresh = [
        sys.executable,
        "-m",
        "evals.sentence_routing_retrieval_falsification.breadcrumb_query_canvas_payload",
        "--report",
        str(report_path),
        "--gold",
        str(gold_path),
        "--canvas-tsx",
        str(canvas_path),
    ]
    res_refresh = subprocess.run(cmd_refresh, cwd=repo_root, capture_output=True, text=True)
    assert res_refresh.returncode == 0, res_refresh.stderr
    assert "stub: true" not in canvas_path.read_text(encoding="utf-8")

    res_fresh = subprocess.run(cmd_check_stale, cwd=repo_root, capture_output=True, text=True)
    assert res_fresh.returncode == 0, res_fresh.stderr
    assert "up to date" in res_fresh.stdout
