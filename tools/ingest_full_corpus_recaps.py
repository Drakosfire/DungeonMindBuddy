#!/usr/bin/env python3
"""Chronological C1→C2 recap ingest with intra-document pass parallelism.

Frozen 42-session corpus: C1 S1–17 + C2 S1–25. Do not regenerate C2 S26/S27.

This is autoregressive candidate generation: each recap's extraction receives
``extra_known_entities`` accumulated from prior **candidate graphs**. It is not
a governed World-through-N−1 extraction.

Documents stay serial. Independent node/beat passes inside one recap may
overlap. Edge and party_claimed_fill remain after consolidation.

Does not publish to DungeonMind. Provider arms land under
``out/full_corpus_world_graph_ingestion/<arm>/`` so OpenAI and DeepSeek
candidates can be compared. APP-STATE ExtractionRun registration is skipped
so this worktree does not collide with a live Buddy postgres.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

CENSUS_TOOL = ROOT / "tools" / "census_full_corpus.py"
DEFAULT_OUT = ROOT / "out" / "full_corpus_world_graph_ingestion"
OPENAI_ARM = "openai-gpt-5.4-mini"
DEEPSEEK_ARM = "deepseek-v4.1-flash"
DEEPSEEK_MODEL = "deepseek/deepseek-v4.1-flash"
CANDIDATE_NODE_KIND = {
    "character": "npc",
    "npc": "npc",
    "location": "location",
    "faction": "faction",
    "organization": "group",
    "group": "group",
    "item": "item",
    "creature": "creature",
}


def _load_census():
    spec = importlib.util.spec_from_file_location("census_full_corpus", CENSUS_TOOL)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


census = _load_census()


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class RecapJob:
    campaign_id: str
    session_number: int
    path: Path
    relpath: str

    @property
    def session_id(self) -> str:
        return f"session-{self.session_number}"

    @property
    def job_id(self) -> str:
        return f"{self.campaign_id}/session-{self.session_number}"


@dataclass
class IngestReceipt:
    job_id: str
    campaign_id: str
    session_number: int
    relpath: str
    status: str
    extra_known_entity_count: int
    node_pass_workers: int
    wall_ms: float
    independent_wall_ms: float | None
    independent_sum_ms: float | None
    independent_workers: int | None
    total_cost_usd: float
    model_id: str | None
    candidate_path: str | None
    error: str | None = None


def chronological_jobs(records: Sequence[Mapping[str, Any]] | None = None) -> list[RecapJob]:
    records = list(records if records is not None else census.census_records())
    jobs: list[RecapJob] = []
    for campaign in ("longmont-c1", "longmont-c2"):
        for rec in census.chronological_recaps(records, campaign):
            jobs.append(
                RecapJob(
                    campaign_id=str(rec["campaign"]),
                    session_number=int(rec["session_number"]),
                    path=ROOT / "corpus" / "eldyrwild-markdown" / rec["path"],
                    relpath=str(rec["path"]),
                )
            )
    return jobs


def recap_independent_pass_count() -> int:
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE

    count = len(RECAP_EXTRACTION_PROFILE.node_passes)
    if RECAP_EXTRACTION_PROFILE.beat_pass is not None:
        count += 1
    return count


def known_entities_from_candidate_graph(graph: Mapping[str, Any]) -> tuple[Any, ...]:
    from src.graph_memory import identity_resolution as ir
    from src.graph_memory.extraction.known_entity_registry import known_entities_from_world_graph

    adapted_nodes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node in graph.get("nodes") or []:
        if not isinstance(node, Mapping):
            continue
        label = str(node.get("label") or "").strip()
        node_type = str(node.get("node_type") or "").strip()
        kind = CANDIDATE_NODE_KIND.get(node_type)
        if not label or kind is None:
            continue
        slug = ir.normalize_label(label).replace(" ", "-")
        if not slug or slug in seen:
            continue
        seen.add(slug)
        aliases = [a for a in (node.get("aliases") or []) if isinstance(a, str) and a.strip()]
        adapted_nodes.append(
            {
                "node_id": f"candidate:{slug}",
                "label": label,
                "kind": kind,
                "aliases": aliases,
            }
        )
    return tuple(known_entities_from_world_graph({"nodes": adapted_nodes}))


def _source_artifact_id(job: RecapJob, digest: str) -> str:
    return f"full-corpus:{job.campaign_id}:{job.session_id}:{digest[:12]}"


def _run_dir_for(output_dir: Path, job: RecapJob) -> Path:
    return output_dir / "runs" / job.campaign_id / f"session-{job.session_number:02d}"


def _load_resumed_result(run_dir: Path) -> Any | None:
    candidate_path = run_dir / "candidate_graph.json"
    telemetry_path = run_dir / "pass_telemetry.json"
    if not candidate_path.is_file() or not telemetry_path.is_file():
        return None
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    telemetry = json.loads(telemetry_path.read_text(encoding="utf-8"))
    if not isinstance(candidate, dict) or "nodes" not in candidate:
        return None

    class _Resumed:
        candidate_graph = candidate
        pass_telemetry = telemetry.get("pass_telemetry") or {}
        total_cost_usd = float(telemetry.get("total_cost_usd") or 0.0)
        model_id = telemetry.get("model_id")
        known_entity_mentions = None

    mentions_path = run_dir / "known_entity_mentions.json"
    if mentions_path.is_file():
        _Resumed.known_entity_mentions = json.loads(mentions_path.read_text(encoding="utf-8"))
    return _Resumed()


def load_provider_keys(*, require_openai: bool = False, require_openrouter: bool = False) -> None:
    from dotenv import load_dotenv

    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()
    try:
        git_dir = subprocess.check_output(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=ROOT,
            text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        git_dir = ""
    if git_dir:
        main_env = Path(git_dir).parent / ".env"
        if main_env.is_file():
            load_dotenv(main_env, override=False)
    if require_openai and not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not configured in this worktree or the main checkout .env"
        )
    if require_openrouter and not (
        os.environ.get("OPENROUTER_API_KEY") or os.environ.get("DUNGEONBUDDY_OPENROUTER")
    ):
        raise SystemExit(
            "OPENROUTER_API_KEY (or DUNGEONBUDDY_OPENROUTER) is not configured "
            "in this worktree or the main checkout .env"
        )


def extract_recap_job(
    job: RecapJob,
    *,
    extra_known_entities: tuple[Any, ...] = (),
    node_pass_workers: int = 1,
    client: Any | None = None,
    output_dir: Path,
    model_id: str | None = None,
) -> tuple[Any, Path]:
    from graph_memory.source_span import (
        build_source_span_index_for_text,
        source_span_index_to_dict,
    )
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        extract_category_candidate_graph,
        resolve_category_graph_model,
    )
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE

    run_dir = _run_dir_for(output_dir, job)
    resumed = _load_resumed_result(run_dir)
    if resumed is not None:
        return resumed, run_dir

    text = job.path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    artifact_id = _source_artifact_id(job, digest)
    index = build_source_span_index_for_text(
        source_artifact_id=artifact_id,
        content_sha256=digest,
        text=text,
    )
    span_payload = source_span_index_to_dict(index)
    result = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id=job.campaign_id,
            session_id=job.session_id,
            session_number=job.session_number,
            source_span_index=span_payload,
            source_text=text,
            source_artifact_id=artifact_id,
            source_ref_id=str(span_payload.get("source_ref_id") or "") or None,
            profile=RECAP_EXTRACTION_PROFILE,
            extra_known_entities=extra_known_entities or None,
            node_pass_workers=node_pass_workers,
            model_id=model_id or resolve_category_graph_model(None),
        ),
        client=client,
    )
    _write_json(run_dir / "candidate_graph.json", result.candidate_graph)
    _write_json(run_dir / "source_span_index.json", span_payload)
    if result.known_entity_mentions is not None:
        _write_json(run_dir / "known_entity_mentions.json", result.known_entity_mentions)
    _write_json(
        run_dir / "pass_telemetry.json",
        {
            "model_id": result.model_id,
            "total_cost_usd": result.total_cost_usd,
            "pass_telemetry": result.pass_telemetry,
        },
    )
    return result, run_dir


def run_serial_ingest(
    jobs: Sequence[RecapJob],
    *,
    extract_one: Callable[..., tuple[Any, Path | None]],
    node_pass_workers: int,
    output_dir: Path,
    active_documents: dict[str, int] | None = None,
) -> list[IngestReceipt]:
    """Run recaps in given order. Never overlaps documents."""
    extras: list[Any] = []
    receipts: list[IngestReceipt] = []
    lock = threading.Lock()
    tracker = active_documents if active_documents is not None else {}
    tracker.setdefault("max_active", 0)
    tracker.setdefault("active", 0)

    for index, job in enumerate(jobs, start=1):
        started = time.perf_counter()
        print(f"[{index}/{len(jobs)}] {job.job_id}", flush=True)
        with lock:
            tracker["active"] = int(tracker.get("active") or 0) + 1
            tracker["max_active"] = max(
                int(tracker.get("max_active") or 0), int(tracker["active"])
            )
            if int(tracker["active"]) != 1:
                raise RuntimeError(
                    f"document chronology violated: {job.job_id} started while "
                    f"{tracker['active']} documents were active"
                )
        try:
            result, run_dir = extract_one(
                job,
                extra_known_entities=tuple(extras),
                node_pass_workers=node_pass_workers,
                output_dir=output_dir,
            )
            candidate = result.candidate_graph if result is not None else {}
            extras.extend(known_entities_from_candidate_graph(candidate or {}))
            concurrency = (result.pass_telemetry or {}).get("_independent_pass_concurrency") or {}
            receipts.append(
                IngestReceipt(
                    job_id=job.job_id,
                    campaign_id=job.campaign_id,
                    session_number=job.session_number,
                    relpath=job.relpath,
                    status="ok",
                    extra_known_entity_count=len(extras),
                    node_pass_workers=node_pass_workers,
                    wall_ms=round((time.perf_counter() - started) * 1000.0, 2),
                    independent_wall_ms=concurrency.get("wall_ms"),
                    independent_sum_ms=concurrency.get("sum_elapsed_ms"),
                    independent_workers=concurrency.get("workers"),
                    total_cost_usd=float(getattr(result, "total_cost_usd", 0.0) or 0.0),
                    model_id=getattr(result, "model_id", None),
                    candidate_path=(
                        None
                        if run_dir is None
                        else str((run_dir / "candidate_graph.json").relative_to(ROOT))
                        if run_dir.is_relative_to(ROOT)
                        else str(run_dir / "candidate_graph.json")
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001 - fail this document, stop the chain
            receipts.append(
                IngestReceipt(
                    job_id=job.job_id,
                    campaign_id=job.campaign_id,
                    session_number=job.session_number,
                    relpath=job.relpath,
                    status="failed",
                    extra_known_entity_count=len(extras),
                    node_pass_workers=node_pass_workers,
                    wall_ms=round((time.perf_counter() - started) * 1000.0, 2),
                    independent_wall_ms=None,
                    independent_sum_ms=None,
                    independent_workers=None,
                    total_cost_usd=0.0,
                    model_id=None,
                    candidate_path=None,
                    error=str(exc),
                )
            )
            return receipts
        finally:
            with lock:
                tracker["active"] = int(tracker.get("active") or 0) - 1
    return receipts


@dataclass
class PreflightClient:
    """Zero-cost client that holds independent passes so overlap is measurable."""

    hold_s: float = 0.04
    passes: list[str] = field(default_factory=list)
    active: int = 0
    max_active: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def run_pass(
        self,
        pass_name: str,
        *,
        model_id: str,
        instructions: str,
        user_content: str,
        pass_spec=None,
    ) -> dict[str, Any]:
        independent = pass_name not in {"edge_pass", "party_claimed_fill"}
        started = time.perf_counter()
        if independent:
            with self._lock:
                self.active += 1
                self.max_active = max(self.max_active, self.active)
            time.sleep(self.hold_s)
            with self._lock:
                self.active -= 1
        with self._lock:
            self.passes.append(pass_name)
        parsed: dict[str, Any]
        if pass_name == "edge_pass":
            parsed = {"observation_edges": []}
        elif pass_name == "beat_pass":
            parsed = {"observation_beats": []}
        else:
            parsed = {"observation_nodes": []}
        return {
            "parsed": parsed,
            "cost_usd": 0.0,
            "usage": {},
            "elapsed_ms": round((time.perf_counter() - started) * 1000.0, 2),
            "response_id": f"preflight-{pass_name}",
        }


def run_concurrency_preflight(
    *,
    output_dir: Path,
    hold_s: float = 0.04,
) -> dict[str, Any]:
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions,
        extract_category_candidate_graph,
    )
    from src.graph_memory.extraction.recap_extraction_profile import RECAP_EXTRACTION_PROFILE

    jobs = chronological_jobs()
    independent = recap_independent_pass_count()
    span_index = {
        "schema": "dmb_source_span_index_v0",
        "version": "0.1",
        "campaign_id": "longmont-c1",
        "session_id": "session-1",
        "source_artifact_id": "artifact:preflight",
        "source_ref_id": "artifact:preflight:text",
        "spans": [
            {
                "span_id": "span-1",
                "source_span_ref_id": "span-1",
                "source_artifact_id": "artifact:preflight",
                "kind": "paragraph",
                "text": "The party reaches Mirathorn.",
            }
        ],
    }
    serial_client = PreflightClient(hold_s=hold_s)
    extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c1",
            session_id="session-1",
            session_number=1,
            source_span_index=span_index,
            profile=RECAP_EXTRACTION_PROFILE,
            node_pass_workers=1,
        ),
        client=serial_client,
    )
    parallel_client = PreflightClient(hold_s=hold_s)
    parallel = extract_category_candidate_graph(
        CategoryGraphExtractionOptions(
            campaign_id="longmont-c1",
            session_id="session-1",
            session_number=1,
            source_span_index=span_index,
            profile=RECAP_EXTRACTION_PROFILE,
            node_pass_workers=independent,
        ),
        client=parallel_client,
    )
    concurrency = parallel.pass_telemetry["_independent_pass_concurrency"]
    tracker: dict[str, int] = {}

    def _fake_extract(job: RecapJob, **kwargs: Any) -> tuple[Any, Path | None]:
        class _Result:
            candidate_graph = {"nodes": []}
            pass_telemetry = {"_independent_pass_concurrency": concurrency}
            total_cost_usd = 0.0
            model_id = "preflight"

        return _Result(), None

    receipts = run_serial_ingest(
        jobs[:3],
        extract_one=_fake_extract,
        node_pass_workers=independent,
        output_dir=output_dir,
        active_documents=tracker,
    )
    payload = {
        "schema": "dmb_full_corpus_concurrency_preflight_v1",
        "generated_at": _utc_now(),
        "document_chronology": {
            "policy": "serial_c1_then_c2",
            "job_count": len(jobs),
            "campaign_1_sessions": [j.session_number for j in jobs if j.campaign_id == "longmont-c1"],
            "campaign_2_sessions": [j.session_number for j in jobs if j.campaign_id == "longmont-c2"],
            "first_three_job_ids": [r.job_id for r in receipts],
            "max_active_documents": tracker.get("max_active"),
        },
        "in_document": {
            "independent_pass_count": independent,
            "serial_max_active_passes": serial_client.max_active,
            "parallel_max_active_passes": parallel_client.max_active,
            "parallel_workers": concurrency["workers"],
            "parallel_wall_ms": concurrency["wall_ms"],
            "parallel_sum_elapsed_ms": concurrency["sum_elapsed_ms"],
            "edge_remains_last": parallel_client.passes[-1] == "edge_pass",
            "safe_node_pass_workers": independent,
        },
        "worldbuilding": "DEFER",
        "app_state_registration": "skipped",
    }
    _write_json(output_dir / "PREFLIGHT.json", payload)
    report = f"""# Full-corpus concurrency preflight

Generated: `{payload['generated_at']}`

## Document chronology

Policy: **serial C1 then C2**. {len(jobs)} admitted recaps. Sample execution
max-active documents: `{tracker.get('max_active')}`.

Campaign 1 sessions: {payload['document_chronology']['campaign_1_sessions']}

Campaign 2 sessions: {payload['document_chronology']['campaign_2_sessions']}

## In-document parallelism

Independent recap passes (node + beat): **{independent}**.
Edge and party_claimed_fill stay after consolidation.

| Mode | max active independent passes | wall_ms | sum elapsed_ms |
|---|---:|---:|---:|
| workers=1 | {serial_client.max_active} | — | — |
| workers={independent} | {parallel_client.max_active} | {concurrency['wall_ms']} | {concurrency['sum_elapsed_ms']} |

Safe `node_pass_workers`: **{independent}**. Extra workers cannot overlap edge/claimed-fill.

APP-STATE ExtractionRun registration is skipped for this slice so the leased
worktree does not write into a live Buddy postgres.
"""
    (output_dir / "PREFLIGHT.md").write_text(report, encoding="utf-8")
    return payload


def write_ingest_ledger(
    output_dir: Path,
    receipts: Sequence[IngestReceipt],
    *,
    provider: str,
    model_id: str,
    arm: str,
) -> None:
    payload = {
        "schema": "dmb_full_corpus_recap_ingest_v1",
        "generated_at": _utc_now(),
        "arm": arm,
        "provider": provider,
        "model_id": model_id,
        "status": "complete"
        if receipts and all(r.status == "ok" for r in receipts)
        else "incomplete",
        "receipts": [r.__dict__ for r in receipts],
        "total_cost_usd": round(sum(r.total_cost_usd for r in receipts), 6),
    }
    _write_json(output_dir / "INGEST.json", payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--provider",
        choices=("openai", "deepseek"),
        default="openai",
        help="openai uses gpt-5.4-mini Responses; deepseek uses OpenRouter DeepSeek V4.1 Flash.",
    )
    parser.add_argument("--output-dir", type=Path, default=None)
    parser.add_argument("--workers", type=int, default=recap_independent_pass_count())
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--allow-llm",
        action="store_true",
        help="Call the selected provider. Required for paid C1→C2 ingest.",
    )
    args = parser.parse_args()
    arm = DEEPSEEK_ARM if args.provider == "deepseek" else OPENAI_ARM
    out_dir = args.output_dir or (DEFAULT_OUT / arm)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.preflight:
        payload = run_concurrency_preflight(output_dir=out_dir)
        print(json.dumps(payload["in_document"], indent=2))
        print(f"Wrote {out_dir / 'PREFLIGHT.md'}")
        return

    jobs = chronological_jobs()
    if args.limit > 0:
        jobs = jobs[: args.limit]
    if args.dry_run:
        print(json.dumps([job.job_id for job in jobs], indent=2))
        return
    if not args.allow_llm:
        raise SystemExit("refusing paid extraction without --allow-llm (or use --preflight / --dry-run)")

    if args.provider == "deepseek":
        from src.graph_memory.extraction.deepseek_category_graph_pass_client import (
            DeepSeekCategoryGraphPassClient,
        )

        load_provider_keys(require_openrouter=True)
        model_id = DEEPSEEK_MODEL
        client = DeepSeekCategoryGraphPassClient(model_id=model_id)
    else:
        load_provider_keys(require_openai=True)
        model_id = None
        client = None

    def extract_one(job: RecapJob, **kwargs: Any) -> tuple[Any, Path]:
        return extract_recap_job(
            job,
            client=client,
            model_id=model_id,
            **kwargs,
        )

    workers = max(1, int(args.workers))
    receipts = run_serial_ingest(
        jobs,
        extract_one=extract_one,
        node_pass_workers=workers,
        output_dir=out_dir,
    )
    write_ingest_ledger(
        out_dir,
        receipts,
        provider="openrouter" if args.provider == "deepseek" else "openai",
        model_id=model_id or "gpt-5.4-mini",
        arm=arm,
    )
    failed = [r for r in receipts if r.status != "ok"]
    print(f"ingested {len(receipts)} recaps; failed={len(failed)}; wrote {out_dir / 'INGEST.json'}")
    if failed:
        raise SystemExit(failed[0].error or "ingest failed")


if __name__ == "__main__":
    main()
