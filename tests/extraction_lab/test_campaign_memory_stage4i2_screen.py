import json
import subprocess
from pathlib import Path

from extraction_lab.campaign_memory_exploratory_screen_manifest import (
    build_screen_manifest_payload,
)
from extraction_lab.campaign_memory_stage4i2_quality_packet import build_quality_packet
from extraction_lab.run_campaign_memory_stage4i2_screen import (
    LUNA_MODEL,
    stage4i2_arms,
    run_screen,
)
from src.llm.experiment_provider import DEEPSEEK_FLASH_SLUG


ROOT = Path(__file__).resolve().parents[2]
SHA = "c" * 40


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _manifest(tmp_path: Path) -> Path:
    path = tmp_path / "manifest.json"
    _write_json(path, build_screen_manifest_payload(repo_root=ROOT, repository_sha=SHA))
    return path


def _fake_census(root, *, batch_size=5, paths=None):
    n = len(list(paths)) if paths is not None else 100
    return {
        "schema": "dmb_campaign_memory_corpus_census_v1",
        "corpus_root": str(root),
        "markdown_source_count": n,
        "raw_source_bytes": n * 10,
        "parseable_source_count": n,
        "rejected_source_count": 0,
        "evidence_unit_count": n * 2,
        "batch_size": batch_size,
        "sources": [],
    }


def _fake_lab(**kwargs):
    out = Path(kwargs["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    _write_json(out / "entity_results.json", [])
    _write_json(out / "fact_results.json", [])
    _write_json(
        out / "aggregate_metrics.json",
        {"entity_anchor_recall": 1.0, "fact_anchor_recall": 0.6},
    )
    return out


def _fake_batch(calls, *, cost=0.01):
    def fake(argv, cwd):
        calls.append(list(argv))
        store = Path(argv[argv.index("--store") + 1])
        model = argv[argv.index("--structured-generation-model") + 1]
        _write_json(store / "entities.json", [{"entity_id": "e1", "display_name": "Brin Holloway"}])
        _write_json(
            store / "facts.json",
            [
                {
                    "fact_id": "f1",
                    "subject_entity_id": "e1",
                    "attribute": "species",
                    "value": {"label": "human"},
                }
            ],
        )
        logs = store / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        (store / ".cache").mkdir(exist_ok=True)
        rows = [
            {"stage": "entity_extraction", "model_name": model},
            {"stage": "fact_extraction", "model_name": model},
        ]
        (logs / "model_calls.jsonl").write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        _write_json(
            logs / "batch_report.json",
            {
                "run_window": {"elapsed_seconds": 1.25},
                "files": {"total": 7, "succeeded": 7, "failed": 0, "skipped": 0},
                "api_calls": {"total": 84, "entity_extraction": 42, "fact_extraction": 42},
                "tokens": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "cached_tokens": 2,
                    "cached_input_tokens": 2,
                    "uncached_input_tokens": 18,
                    "reasoning_tokens": 4,
                    "visible_output_tokens": 6,
                    "parsed_output_bytes": 50,
                    "cache_rate": 0.1,
                },
                "cost_estimate": {"estimated_cost_usd": cost},
                "local_cache": {"overall_hit_rate": 0.0},
                "timing": {
                    "entity_extraction_ms": 400,
                    "fact_extraction_ms": 500,
                    "request_elapsed_p50_ms": 120.0,
                    "request_elapsed_p95_ms": 200.0,
                    "request_elapsed_max_ms": 250.0,
                    "request_elapsed_count": 84,
                },
            },
        )
        return subprocess.CompletedProcess(argv, 0, stdout="batch ok", stderr="")

    return fake


def _run(tmp_path: Path, out: Path, **kwargs):
    return run_screen(
        manifest_path=_manifest(tmp_path),
        out_dir=out,
        repo_root=ROOT,
        repository_sha_reader=lambda _root: SHA,
        worktree_clean_reader=lambda _root: True,
        census_fn=_fake_census,
        lab_fn=_fake_lab,
        environ={
            "OPENAI_API_KEY": "test-only",
            "DUNGEONBUDDY_OPENROUTER": "test-only-openrouter",
        },
        **kwargs,
    )


def test_stage4i2_dry_run_sends_zero_api_calls_and_creates_no_output(tmp_path: Path) -> None:
    calls = []
    out = tmp_path / "out"
    result = _run(tmp_path, out, runner=_fake_batch(calls))
    assert result["mode"] == "dry_run"
    assert result["api_calls"] == 0
    assert result["plan"]["will_execute"] is False
    assert result["plan"]["arm_count"] == 16
    assert result["plan"]["extraction_context_mode"] == "whole_document"
    assert result["plan"]["run_order"][0] == "deepseek-none"
    assert result["plan"]["run_order"][-1] == "luna-flex-max"
    assert calls == []
    assert not out.exists()


def test_stage4i2_execute_isolates_stores_and_whole_document_contract(tmp_path: Path) -> None:
    calls = []
    out = tmp_path / "out"
    receipt = _run(tmp_path, out, execute=True, runner=_fake_batch(calls))
    arms = stage4i2_arms()
    assert receipt["status"] == "completed"
    assert len(calls) == 16
    stores = [Path(argv[argv.index("--store") + 1]) for argv in calls]
    assert len(set(stores)) == 16
    for argv, arm in zip(calls, arms, strict=True):
        joined = " ".join(argv)
        assert "--resume" not in argv
        assert "--use-batch-api" not in argv
        assert argv[argv.index("--structured-generation-model") + 1] == arm["model"]
        assert argv[argv.index("--openai-service-tier") + 1] == arm["service_tier"]
        assert argv[argv.index("--reasoning-effort") + 1] == arm["reasoning_effort"]
        assert argv[argv.index("--extraction-context-mode") + 1] == "whole_document"
        assert argv[argv.index("--extraction-provider") + 1] == arm["provider"]
        assert argv[argv.index("--fact-contract") + 1] == "payload_lean_v1"
        if arm["provider"] == "openrouter":
            assert argv[argv.index("--openrouter-provider-pin") + 1] == "DeepSeek"
            assert arm["model"] == DEEPSEEK_FLASH_SLUG
        else:
            assert arm["model"] == LUNA_MODEL
            assert "--openrouter-provider-pin" not in argv
        assert "gold/entity_anchors.json" not in joined
        assert "gold/fact_anchors.json" not in joined
        assert "PREREGISTRATION-DOGFOOD-CONTINUITY-stage4i" not in joined
    flex = next(argv for argv, arm in zip(calls, arms) if arm["arm_id"] == "luna-flex-medium")
    standard = next(argv for argv, arm in zip(calls, arms) if arm["arm_id"] == "luna-standard-medium")
    assert flex[flex.index("--openai-service-tier") + 1] == "flex"
    assert standard[standard.index("--openai-service-tier") + 1] == "standard"
    packet = json.loads((out / "deepseek-none" / "quality_packet.json").read_text(encoding="utf-8"))
    assert packet["evaluator_llm"] is False
    assert packet["store_mutated"] is False
    assert packet["witnesses"][0]["entity_ids"] == ["e1"]


def test_quality_packet_is_analysis_only() -> None:
    entities = [
        {"entity_id": "orik", "display_name": "Orik Tane", "aliases": []},
        {"entity_id": "orric", "display_name": "Orric Tane", "aliases": []},
    ]
    facts = [
        {
            "fact_id": "f1",
            "subject_entity_id": "orik",
            "attribute": "species",
            "value": {"label": "human"},
        }
    ]
    original = json.dumps(entities + facts, sort_keys=True)
    packet = build_quality_packet(
        entities=entities,
        facts=facts,
        arm={"arm_id": "x", "model": LUNA_MODEL, "provider": "openai", "service_tier": "flex", "reasoning_effort": "medium"},
    )
    assert json.dumps(entities + facts, sort_keys=True) == original
    assert packet["evaluator_llm"] is False
    assert packet["diagnostics"]["identity_candidates"][0]["classification"] == "POSSIBLE_LOCAL_RECONCILIATION"
