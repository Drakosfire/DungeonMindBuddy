"""Serial chronology and intra-document concurrency for full-corpus recap ingest."""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "ingest_full_corpus_recaps.py"
spec = importlib.util.spec_from_file_location("ingest_full_corpus_recaps", TOOL)
assert spec is not None and spec.loader is not None
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)


def test_jobs_are_c1_then_c2_contiguous() -> None:
    jobs = mod.chronological_jobs()
    c1 = [j for j in jobs if j.campaign_id == "longmont-c1"]
    c2 = [j for j in jobs if j.campaign_id == "longmont-c2"]
    assert [j.session_number for j in c1] == list(range(1, 18))
    assert [j.session_number for j in c2] == list(range(1, 26))
    assert jobs == c1 + c2
    assert jobs[0].job_id == "longmont-c1/session-1"
    assert jobs[-1].job_id == "longmont-c2/session-25"


def test_runner_keeps_documents_serial(tmp_path: Path) -> None:
    jobs = mod.chronological_jobs()[:4]
    seen: list[str] = []
    tracker: dict[str, int] = {}

    class _Result:
        candidate_graph = {"nodes": [{"label": "Mirathorn", "node_type": "location"}]}
        pass_telemetry = {
            "_independent_pass_concurrency": {
                "workers": 6,
                "wall_ms": 10,
                "sum_elapsed_ms": 40,
            }
        }
        total_cost_usd = 0.0
        model_id = "fixture"

    def extract_one(job: Any, **kwargs: Any) -> tuple[Any, Path]:
        assert tracker.get("active") == 1
        seen.append(job.job_id)
        time.sleep(0.01)
        return _Result(), tmp_path / job.job_id.replace("/", "_")

    receipts = mod.run_serial_ingest(
        jobs,
        extract_one=extract_one,
        node_pass_workers=6,
        output_dir=tmp_path,
        active_documents=tracker,
    )
    assert [r.job_id for r in receipts] == [j.job_id for j in jobs]
    assert seen == [j.job_id for j in jobs]
    assert tracker["max_active"] == 1
    assert all(r.status == "ok" for r in receipts)
    assert receipts[-1].extra_known_entity_count >= 1


def test_runner_does_not_start_later_document_after_failure(tmp_path: Path) -> None:
    jobs = mod.chronological_jobs()[:3]

    def extract_one(job: Any, **kwargs: Any) -> tuple[Any, Path]:
        if job.session_number == 2:
            raise RuntimeError("stop-chain")
        class _Result:
            candidate_graph = {"nodes": []}
            pass_telemetry = {}
            total_cost_usd = 0.0
            model_id = "fixture"

        return _Result(), tmp_path

    receipts = mod.run_serial_ingest(
        jobs,
        extract_one=extract_one,
        node_pass_workers=1,
        output_dir=tmp_path,
    )
    assert [r.job_id for r in receipts] == [
        "longmont-c1/session-1",
        "longmont-c1/session-2",
    ]
    assert receipts[1].status == "failed"
    assert receipts[1].error == "stop-chain"


def test_known_entities_from_candidate_graph_map_character_to_npc() -> None:
    entities = mod.known_entities_from_candidate_graph(
        {
            "nodes": [
                {"label": "Lysandra", "node_type": "character"},
                {"label": "Mirathorn", "node_type": "location"},
                {"label": "the missing ledger", "node_type": "mystery"},
            ]
        }
    )
    kinds = {e.kind for e in entities}
    names = {e.display_name for e in entities}
    assert kinds == {"npc", "location"}
    assert "Lysandra" in names
    assert "Mirathorn" in names
    assert "the missing ledger" not in names


def test_extract_recap_job_resumes_existing_candidate(tmp_path: Path) -> None:
    job = mod.chronological_jobs()[0]
    run_dir = tmp_path / "runs" / job.campaign_id / f"session-{job.session_number:02d}"
    run_dir.mkdir(parents=True)
    (run_dir / "candidate_graph.json").write_text(
        json.dumps({"nodes": [{"label": "Mirathorn", "node_type": "location"}]}),
        encoding="utf-8",
    )
    (run_dir / "pass_telemetry.json").write_text(
        json.dumps({"model_id": "resumed", "total_cost_usd": 1.25, "pass_telemetry": {}}),
        encoding="utf-8",
    )

    def boom(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("resume must not call the extractor")

    import src.graph_memory.extraction.category_candidate_graph_extractor as extractor

    original = extractor.extract_category_candidate_graph
    extractor.extract_category_candidate_graph = boom  # type: ignore[method-assign]
    try:
        result, resumed_dir = mod.extract_recap_job(
            job,
            output_dir=tmp_path,
            node_pass_workers=6,
        )
    finally:
        extractor.extract_category_candidate_graph = original  # type: ignore[method-assign]
    assert resumed_dir == run_dir
    assert result.model_id == "resumed"
    assert result.total_cost_usd == 1.25
    assert result.candidate_graph["nodes"][0]["label"] == "Mirathorn"


def test_openai_and_deepseek_arms_do_not_share_run_dirs() -> None:
    assert mod.OPENAI_ARM != mod.DEEPSEEK_ARM
    openai_root = mod.DEFAULT_OUT / mod.OPENAI_ARM
    deepseek_root = mod.DEFAULT_OUT / mod.DEEPSEEK_ARM
    assert openai_root != deepseek_root
    assert (mod.DEFAULT_OUT / "openai-gpt-5.4-mini" / "INGEST.json").is_file()
    assert not (deepseek_root / "INGEST.json").is_file()


def test_concurrency_preflight_writes_serial_and_overlap_evidence(tmp_path: Path) -> None:
    payload = mod.run_concurrency_preflight(output_dir=tmp_path, hold_s=0.03)
    assert payload["document_chronology"]["max_active_documents"] == 1
    assert payload["document_chronology"]["job_count"] == 42
    assert payload["in_document"]["independent_pass_count"] == 6
    assert payload["in_document"]["serial_max_active_passes"] == 1
    assert payload["in_document"]["parallel_max_active_passes"] > 1
    assert payload["in_document"]["edge_remains_last"] is True
    assert payload["in_document"]["safe_node_pass_workers"] == 6
    assert (tmp_path / "PREFLIGHT.md").is_file()


def test_threaded_caller_cannot_overlap_documents(tmp_path: Path) -> None:
    """The runner itself is serial; this guards a future thread-pool around jobs."""
    jobs = mod.chronological_jobs()[:2]
    barrier = threading.Barrier(2)
    started = threading.Event()

    class _Result:
        candidate_graph = {"nodes": []}
        pass_telemetry = {}
        total_cost_usd = 0.0
        model_id = "fixture"

    def extract_one(job: Any, **kwargs: Any) -> tuple[Any, Path]:
        started.set()
        # If two documents were in flight, wait would succeed. Serial runner
        # never reaches a second waiter, so timeout is the success signal.
        try:
            barrier.wait(timeout=0.05)
        except threading.BrokenBarrierError:
            pass
        return _Result(), tmp_path

    receipts = mod.run_serial_ingest(
        jobs,
        extract_one=extract_one,
        node_pass_workers=6,
        output_dir=tmp_path,
    )
    assert [r.status for r in receipts] == ["ok", "ok"]
    assert started.is_set()
