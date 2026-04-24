from __future__ import annotations

import argparse
import asyncio
from dataclasses import replace
import hashlib
import json
import logging
import os
import shlex
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

from openai import OpenAI

from src.agent.context_formatter import format_projection_context
from src.agent.document_planner import build_document_roster, plan_documents_async
from src.agent.evidence_retriever import (
    collect_provenance_evidence_for_entities,
    rank_entities_by_evidence_overlap,
    retrieve_relevant_evidence,
)
from src.agent.retriever import (
    filter_projection,
    retrieve_relevant_entities,
    semantic_rerank_entities,
)
from src.agent.scope_relevance import question_mentioned_entity_ids
from src.agent.planner import run_planning_session
from src.agent.synthesis import synthesize_answer_async
from src.compiler.wiki_compiler import compile_wiki, list_wiki_targets
from src.ingestion.chunker import chunk_document
from src.ingestion.frontmatter import (
    FrontmatterError,
    load_document_frontmatter,
    write_document_with_frontmatter,
)
from src.ingestion.frontmatter_inference import (
    OpenAIFrontmatterInferenceClient,
    infer_frontmatter_metadata,
    metadata_preview,
)
from src.ingestion.entity_extractor import (
    AsyncOpenAIResponsesEntityClient,
    apply_entity_batch_outputs_to_cache,
    prepare_entity_batch_requests,
    run_entity_extraction,
    _load_fast_smart_model_id,
)
from src.ingestion.fact_extractor import (
    AsyncOpenAIResponsesFactClient,
    apply_fact_batch_outputs_to_cache,
    prepare_fact_batch_requests,
    run_fact_extraction,
    _load_model_id as _load_fact_structured_model_id,
)
from src.ingestion.source_anchor import lint_source_anchors
from src.ingestion.openai_batch_pipeline import run_batch_job
from src.contracts.schema_validation import validate_many
from src.contracts.temporal_tick_gate import (
    campaign_temporal_quality_summary,
    campaign_temporal_consistency_violations,
    campaign_temporal_tick_violations,
)
from src.reducer.canon_projection import attach_scope_relevance_metadata
from src.store import FactStore

LOGGER_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _snake_case(value: str) -> str:
    lowered = value.lower()
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in lowered)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "document"


def _load_env() -> None:
    from src.bootstrap_env import load_dungeonmindbuddy_dotenv

    load_dungeonmindbuddy_dotenv()


def _fact_counts_by_entity(store: FactStore) -> dict[str, int]:
    counts: dict[str, int] = {}
    for fact in store.facts:
        subject = str(fact.get("subject_entity_id", "")).strip()
        if not subject:
            continue
        counts[subject] = counts.get(subject, 0) + 1
    return counts


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute_ingest_key_for_path(
    source_path: Path,
    *,
    layer: str | None = None,
    campaign: str | None = None,
    source_class_cli: str | None = None,
    title: str | None = None,
    no_frontmatter: bool = False,
) -> str | None:
    """Return the ingest_key used in ``FactStore.ingest_index`` when scope is known without user input.

    Matches ``DungeonBuddyCLI._cmd_ingest`` for the same path and CLI overrides. Returns ``None`` when
    ingest would require interaction (missing frontmatter), invalid frontmatter, metadata/CLI conflicts,
    or incomplete scope — callers should run normal ingest in those cases.
    """
    if not source_path.exists():
        return None

    metadata_layer = layer
    metadata_campaign_id = campaign
    metadata_source_class = source_class_cli

    if source_path.suffix.lower() == ".md":
        try:
            metadata, _body = load_document_frontmatter(source_path)
        except FrontmatterError:
            return None
        if metadata is None and not no_frontmatter:
            return None
        if metadata is not None:
            md = metadata.to_dict()
            conflicts: list[str] = []
            if layer and layer != md["canon_layer"]:
                conflicts.append(
                    f"--layer={layer} conflicts with frontmatter canon_layer={md['canon_layer']}"
                )
            if campaign is not None and campaign != md["campaign_id"]:
                conflicts.append(
                    f"--campaign={campaign} conflicts with frontmatter campaign_id={md['campaign_id']}"
                )
            if source_class_cli and source_class_cli != md["source_class"]:
                conflicts.append(
                    f"--source-class={source_class_cli} conflicts with frontmatter "
                    f"source_class={md['source_class']}"
                )
            if title and title != md["title"]:
                conflicts.append(f"--title={title} conflicts with frontmatter title={md['title']}")
            if conflicts:
                return None
            metadata_layer = str(md["canon_layer"])
            metadata_campaign_id = (
                str(md["campaign_id"]) if md.get("campaign_id") is not None else None
            )
            metadata_source_class = str(md["source_class"])

    if metadata_layer is None:
        return None
    if metadata_layer == "campaign" and not metadata_campaign_id:
        return None

    source_class = metadata_source_class
    if not source_class:
        source_class = "seed_reference" if metadata_layer == "world" else "planning_document"

    source_fingerprint = _file_sha256(source_path)
    return (
        f"{source_fingerprint}|layer={metadata_layer}|campaign={metadata_campaign_id}|source_class={source_class}"
    )


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def _schema_gate(name: str, records: list[dict[str, Any]], schema_name: str) -> dict[str, Any]:
    errors: list[str] = []
    try:
        validate_many(records, schema_name)
    except Exception as exc:  # pragma: no cover - exercised by ingest gate failure tests.
        errors.append(str(exc))
    return {
        "name": name,
        "pass": not errors,
        "schema": schema_name,
        "errors": errors,
        "count": len(records),
    }


def _build_ingest_gate_report(
    *,
    evidence_units: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
) -> dict[str, Any]:
    layer_errors: list[str] = []
    for unit in evidence_units:
        evidence_id = str(unit.get("evidence_id", "unknown"))
        layer = str(unit.get("canon_layer", ""))
        campaign_id = unit.get("campaign_id")
        if layer == "world" and campaign_id is not None:
            layer_errors.append(f"{evidence_id}: world evidence has campaign_id")
        if layer == "campaign" and not campaign_id:
            layer_errors.append(f"{evidence_id}: campaign evidence missing campaign_id")

    gates = [
        {
            "name": "stage_chunk_build_non_empty",
            "pass": len(evidence_units) > 0,
            "errors": [] if evidence_units else ["chunking produced zero evidence units"],
            "count": len(evidence_units),
        },
        {
            "name": "stage_chunk_layer_integrity",
            "pass": not layer_errors,
            "errors": layer_errors,
            "count": len(evidence_units),
        },
        _schema_gate("stage_chunk_schema", evidence_units, "evidence_unit.schema.json"),
        {
            "name": "stage_entity_extraction_non_empty",
            "pass": len(entities) > 0,
            "errors": [] if entities else ["entity extraction produced zero entities"],
            "count": len(entities),
        },
        _schema_gate("stage_entity_schema", entities, "entity.schema.json"),
        {
            "name": "stage_fact_extraction_non_empty",
            "pass": len(facts) > 0,
            "errors": [] if facts else ["fact extraction produced zero facts"],
            "count": len(facts),
        },
        _schema_gate("stage_fact_schema", facts, "fact.schema.json"),
    ]
    tick_errors = campaign_temporal_tick_violations(evidence_units, facts)
    gates.append(
        {
            "name": "stage_campaign_narrative_temporal_tick",
            "pass": not tick_errors,
            "errors": tick_errors,
            "count": len(facts),
        }
    )
    consistency_errors = campaign_temporal_consistency_violations(evidence_units, facts)
    gates.append(
        {
            "name": "stage_campaign_temporal_consistency",
            "pass": not consistency_errors,
            "errors": consistency_errors,
            "count": len(facts),
        }
    )
    quality_summary = campaign_temporal_quality_summary(evidence_units, facts)
    gates.append(
        {
            "name": "stage_campaign_temporal_quality_warning",
            "pass": True,
            "warnings": quality_summary["warnings"],
            "metrics": quality_summary["metrics"],
            "count": len(facts),
        }
    )
    return {
        "overall_pass": all(gate["pass"] for gate in gates),
        "gates": gates,
        "counts": {
            "evidence_units": len(evidence_units),
            "entities": len(entities),
            "facts": len(facts),
        },
    }


def _write_ingest_stage_artifacts(
    *,
    artifacts_dir: Path,
    evidence_units: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    facts: list[dict[str, Any]],
    gate_report: dict[str, Any],
) -> None:
    _write_json(artifacts_dir / "stage_chunks.json", evidence_units)
    _write_json(artifacts_dir / "stage_entities.json", entities)
    _write_json(artifacts_dir / "stage_facts.json", facts)
    _write_json(artifacts_dir / "gate_report.json", gate_report)


class DungeonBuddyCLI:
    def __init__(self, *, store_dir: Path, verbose: bool = False) -> None:
        _load_env()
        self.store_dir = Path(store_dir)
        self.verbose = verbose
        self.logs_dir = self.store_dir / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.store = FactStore(self.store_dir)
        if self.store_dir.exists():
            self.store.load()
        self.logger = logging.getLogger("dungeonbuddy.cli")
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        self._retrieval_embedding_model: Any | None = None
        self._retrieval_embedding_model_id: str | None = None

    def _load_retrieval_embedding_model(self, model_id: str) -> Any | None:
        """Load and cache retrieval embedding model; return None on failure."""
        if self._retrieval_embedding_model is not None and self._retrieval_embedding_model_id == model_id:
            return self._retrieval_embedding_model
        try:
            from evals.mirathorn_vertical_slice.embedding_scorer import (
                embedding_available,
                load_embedding_model,
            )
        except Exception as exc:
            self.logger.warning(
                "Semantic rerank unavailable (embedding loader import failed): %s",
                exc,
            )
            return None
        if not embedding_available():
            self.logger.warning(
                "Semantic rerank requested but sentence-transformers is unavailable"
            )
            return None
        try:
            model = load_embedding_model(model_id=model_id)
        except Exception as exc:
            self.logger.warning("Failed to load retrieval embedding model %s: %s", model_id, exc)
            return None
        self._retrieval_embedding_model = model
        self._retrieval_embedding_model_id = model_id
        return model

    @staticmethod
    def _fuse_ranked_entities(
        ranked_entities: list[tuple[str, float]],
        evidence_overlap_scores: dict[str, float],
        *,
        evidence_boost: float,
        cap: int,
    ) -> list[tuple[str, float]]:
        if not ranked_entities:
            return ranked_entities
        score_map: dict[str, float] = {eid: float(score) for eid, score in ranked_entities}
        floor = min(score_map.values()) if score_map else 0.01
        for entity_id, overlap_score in evidence_overlap_scores.items():
            score_map[entity_id] = score_map.get(entity_id, floor * 0.75) + (
                max(0.0, overlap_score) * max(0.0, evidence_boost)
            )
        reranked = sorted(score_map.items(), key=lambda row: row[1], reverse=True)
        if cap > 0:
            return reranked[:cap]
        return reranked

    @staticmethod
    def _fit_context_budget(
        *,
        projection: dict[str, Any],
        entities: list[dict[str, Any]],
        question: str,
        evidence_units: list[dict[str, Any]],
        scope_document_ids: list[str],
        scope_confidence: float,
        min_scope_confidence: float,
        min_entity_evidence_count: int,
        hard_exclude_out_of_scope: bool,
        unknown_exploration_quota: int,
        include_scope_annotations: bool,
        priority_entity_ids: list[str] | None,
        max_entities: int,
        max_chars: int,
        wiki_pages: dict[str, str] | None = None,
    ) -> tuple[str, int, bool]:
        cap = max(1, int(max_entities))
        context = ""
        truncated = False
        while True:
            context = format_projection_context(
                projection,
                entities,
                question,
                evidence_units=evidence_units,
                scope_document_ids=scope_document_ids,
                scope_confidence=scope_confidence,
                min_scope_confidence=min_scope_confidence,
                min_entity_evidence_count=min_entity_evidence_count,
                hard_exclude_out_of_scope=hard_exclude_out_of_scope,
                unknown_exploration_quota=unknown_exploration_quota,
                include_scope_annotations=include_scope_annotations,
                max_entities=cap,
                priority_entity_ids=priority_entity_ids,
                wiki_pages=wiki_pages,
            )
            if len(context) <= max_chars or cap <= 5:
                truncated = cap < max_entities or len(context) > max_chars
                break
            next_cap = max(5, int(cap * 0.75))
            if next_cap == cap:
                next_cap = cap - 1
            cap = max(5, next_cap)
        return context, cap, truncated

    @staticmethod
    def _build_provenance_appendix(
        *,
        projection: dict[str, Any],
        evidence_units: list[dict[str, Any]],
        max_total_chars: int,
        base_context_len: int,
    ) -> tuple[str, dict[str, Any]]:
        """Append raw evidence text for provenance IDs on retrieved (filtered) entities."""
        budget = max(0, max_total_chars - base_context_len - 4)
        stats: dict[str, Any] = {
            "appendix_chars": 0,
            "provenance_evidence_ids_seen": 0,
            "provenance_evidence_ids_included": 0,
        }
        if budget < 120:
            return "", stats

        evidence_by_id = {
            str(u.get("evidence_id", "")).strip(): str(u.get("text", "")).strip()
            for u in evidence_units
            if str(u.get("evidence_id", "")).strip()
        }
        ordered_ids: list[str] = []
        seen: set[str] = set()
        for _eid, payload in (projection.get("entities") or {}).items():
            for _attr, ap in (payload.get("attributes") or {}).items():
                for ev in ap.get("provenance_evidence_ids") or []:
                    eid = str(ev).strip()
                    if eid and eid not in seen:
                        seen.add(eid)
                        ordered_ids.append(eid)
        stats["provenance_evidence_ids_seen"] = len(ordered_ids)

        chunks: list[str] = ["## Supporting evidence excerpts"]
        total = len(chunks[0])
        included = 0
        for eid in ordered_ids:
            text = evidence_by_id.get(eid, "")
            if not text:
                continue
            block = f"[{eid}] {text}"
            add = len(block) + (2 if len(chunks) else 0)
            if total + add > budget:
                remain = budget - total - 2
                if remain > 80:
                    chunks.append(f"[{eid}] {text[:remain]}...")
                    included += 1
                break
            chunks.append(block)
            total += add
            included += 1
        appendix = "\n\n".join(chunks) if len(chunks) > 1 else ""
        stats["appendix_chars"] = len(appendix)
        stats["provenance_evidence_ids_included"] = included
        return appendix, stats

    @staticmethod
    def _metadata_conflicts(
        *,
        provided_layer: str | None,
        provided_campaign: str | None,
        provided_source_class: str | None,
        provided_title: str | None,
        metadata: dict[str, str | int | None],
    ) -> list[str]:
        conflicts: list[str] = []
        if provided_layer and provided_layer != metadata["canon_layer"]:
            conflicts.append(
                f"--layer={provided_layer} conflicts with frontmatter canon_layer={metadata['canon_layer']}"
            )
        if provided_campaign is not None and provided_campaign != metadata["campaign_id"]:
            conflicts.append(
                f"--campaign={provided_campaign} conflicts with frontmatter campaign_id={metadata['campaign_id']}"
            )
        if provided_source_class and provided_source_class != metadata["source_class"]:
            conflicts.append(
                f"--source-class={provided_source_class} conflicts with frontmatter source_class={metadata['source_class']}"
            )
        if provided_title and provided_title != metadata["title"]:
            conflicts.append(
                f"--title={provided_title} conflicts with frontmatter title={metadata['title']}"
            )
        return conflicts

    def _confirm_inferred_frontmatter(self, source_path: Path, text: str) -> bool:
        inference_client = None
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            inference_client = OpenAIFrontmatterInferenceClient(api_key=api_key)
        inferred = infer_frontmatter_metadata(
            path=source_path,
            text=text,
            openai_client=inference_client,
        )
        print("Proposed frontmatter metadata:")
        print(metadata_preview(inferred))
        answer = input("Apply this frontmatter to the document? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Error: frontmatter inference not confirmed.")
            return False
        write_document_with_frontmatter(source_path, metadata=inferred, body=text)
        print(f"Frontmatter written to {source_path}")
        return True

    def run(self) -> int:
        while True:
            try:
                line = input("dungeonbuddy> ").strip()
            except EOFError:
                print()
                return 0
            except KeyboardInterrupt:
                print()
                return 0
            if not line:
                continue
            keep_running = self.handle_line(line)
            if not keep_running:
                return 0

    def handle_line(self, line: str) -> bool:
        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            print(f"Error: unable to parse command: {exc}")
            return True

        if not tokens:
            return True
        command, args = tokens[0], tokens[1:]

        if command in {"quit", "exit"}:
            return False
        if command == "ingest":
            self._cmd_ingest(args)
            return True
        if command == "ask":
            self._cmd_ask(args)
            return True
        if command == "plan":
            self._cmd_plan(args)
            return True
        if command == "entities":
            self._cmd_entities(args)
            return True
        if command == "projection":
            self._cmd_projection(args)
            return True
        if command == "compact":
            self._cmd_compact(args)
            return True
        if command == "canon-decision":
            self._cmd_canon_decision(args)
            return True
        if command == "compile-wiki":
            self._cmd_compile_wiki(args)
            return True
        if command == "anchor-lint":
            self._cmd_anchor_lint(args)
            return True

        print(f"Error: unknown command '{command}'")
        return True

    def _cmd_plan(self, args: Sequence[str]) -> None:
        parser = argparse.ArgumentParser(prog="plan", add_help=False)
        parser.add_argument(
            "--corpus-dir",
            type=str,
            default="corpus/eldyrwild-markdown",
            help="Directory relative to project root (default: corpus/eldyrwild-markdown).",
        )
        parser.add_argument(
            "--model",
            type=str,
            default="",
            help="Optional OpenAI model id override.",
        )
        parser.add_argument(
            "--allow-corpus-writes",
            action="store_true",
            help=(
                "Register guarded write tools (`write_corpus_file`, `append_timeline_row`). "
                "Two-phase commit is required and dossier/seed/statblock files stay read-only. "
                "Equivalent to env DUNGEONMIND_PLANNER_ALLOW_WRITES=1."
            ),
        )
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return
        project_root = Path(__file__).resolve().parents[1]
        corpus_dir = (project_root / parsed.corpus_dir).resolve()
        model = parsed.model.strip() or None
        run_planning_session(
            corpus_dir,
            model,
            allow_corpus_writes=bool(parsed.allow_corpus_writes) or None,
        )

    def _cmd_ingest(self, args: Sequence[str]) -> None:
        run_id = f"ingest-{uuid.uuid4().hex[:10]}"
        started = time.perf_counter()
        parser = argparse.ArgumentParser(prog="ingest", add_help=False)
        parser.add_argument("path")
        parser.add_argument("--layer", choices=["world", "campaign"])
        parser.add_argument("--campaign")
        parser.add_argument("--source-class")
        parser.add_argument("--title")
        parser.add_argument("--chunk-min-chars", type=int, default=50)
        parser.add_argument("--entity-concurrency", type=int, default=8)
        parser.add_argument("--fact-concurrency", type=int, default=8)
        parser.add_argument(
            "--batch-size",
            type=int,
            default=5,
            help="Evidence units per LLM call for entity/fact extraction (default 5)",
        )
        parser.add_argument("--no-frontmatter", action="store_true")
        parser.add_argument("--force", action="store_true")
        parser.add_argument(
            "--use-openai-batch-api",
            action="store_true",
            help="Use OpenAI Batch API for entity/fact extraction (async, ~50%% cost vs realtime)",
        )
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return

        source_path = Path(parsed.path)
        if not source_path.exists():
            print(f"Error: file not found: {source_path}")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "file_not_found",
                    "source_path": str(source_path),
                },
            )
            return

        metadata_layer = parsed.layer
        metadata_campaign_id = parsed.campaign
        metadata_source_class = parsed.source_class
        metadata_title = parsed.title or source_path.stem

        if source_path.suffix.lower() == ".md":
            try:
                metadata, body = load_document_frontmatter(source_path)
            except FrontmatterError as exc:
                print(f"Error: invalid frontmatter: {exc}")
                self._record_event(
                    "ingest_runs",
                    {
                        "run_id": run_id,
                        "timestamp": _utc_now_iso(),
                        "status": "error",
                        "error": "invalid_frontmatter",
                        "detail": str(exc),
                        "source_path": str(source_path),
                    },
                )
                return
            if metadata is None and not parsed.no_frontmatter:
                if not self._confirm_inferred_frontmatter(source_path, body):
                    self._record_event(
                        "ingest_runs",
                        {
                            "run_id": run_id,
                            "timestamp": _utc_now_iso(),
                            "status": "error",
                            "error": "frontmatter_inference_declined",
                            "source_path": str(source_path),
                        },
                    )
                    return
                metadata, _ = load_document_frontmatter(source_path)

            if metadata is not None:
                md = metadata.to_dict()
                conflicts = self._metadata_conflicts(
                    provided_layer=parsed.layer,
                    provided_campaign=parsed.campaign,
                    provided_source_class=parsed.source_class,
                    provided_title=parsed.title,
                    metadata=md,
                )
                if conflicts:
                    print("Error: frontmatter conflicts with CLI arguments:")
                    for conflict in conflicts:
                        print(f"  - {conflict}")
                    self._record_event(
                        "ingest_runs",
                        {
                            "run_id": run_id,
                            "timestamp": _utc_now_iso(),
                            "status": "error",
                            "error": "frontmatter_cli_conflict",
                            "source_path": str(source_path),
                            "conflicts": conflicts,
                        },
                    )
                    return
                metadata_layer = str(md["canon_layer"])
                metadata_campaign_id = (
                    str(md["campaign_id"]) if md.get("campaign_id") is not None else None
                )
                metadata_source_class = str(md["source_class"])
                metadata_title = str(md["title"])

        if metadata_layer is None:
            print("Error: --layer is required when frontmatter is absent or bypassed.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "missing_layer",
                    "source_path": str(source_path),
                },
            )
            return

        if metadata_layer == "campaign" and not metadata_campaign_id:
            print("Error: campaign metadata is required for campaign-layer ingest.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "missing_campaign_id",
                    "source_path": str(source_path),
                    "layer": metadata_layer,
                },
            )
            return
        if parsed.chunk_min_chars < 1:
            print("Error: --chunk-min-chars must be >= 1.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "invalid_chunk_min_chars",
                    "source_path": str(source_path),
                    "chunk_min_chars": parsed.chunk_min_chars,
                },
            )
            return
        if parsed.entity_concurrency < 1:
            print("Error: --entity-concurrency must be >= 1.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "invalid_entity_concurrency",
                    "source_path": str(source_path),
                    "entity_concurrency": parsed.entity_concurrency,
                },
            )
            return
        if parsed.fact_concurrency < 1:
            print("Error: --fact-concurrency must be >= 1.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "invalid_fact_concurrency",
                    "source_path": str(source_path),
                    "fact_concurrency": parsed.fact_concurrency,
                },
            )
            return
        if parsed.batch_size < 1:
            print("Error: --batch-size must be >= 1.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "invalid_batch_size",
                    "source_path": str(source_path),
                    "batch_size": parsed.batch_size,
                },
            )
            return

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OPENAI_API_KEY is required for ingest.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "missing_openai_api_key",
                    "source_path": str(source_path),
                },
            )
            return

        source_class = metadata_source_class
        if not source_class:
            source_class = "seed_reference" if metadata_layer == "world" else "planning_document"

        title = metadata_title
        document_id = f"doc_{_snake_case(source_path.stem)}"
        campaign_id = metadata_campaign_id
        source_fingerprint = _file_sha256(source_path)
        ingest_key = (
            f"{source_fingerprint}|layer={metadata_layer}|campaign={campaign_id}|source_class={source_class}"
        )

        self.store_dir.mkdir(parents=True, exist_ok=True)
        cache_dir = self.store_dir / ".cache"
        if self.store.has_ingest_fingerprint(ingest_key) and not parsed.force:
            print("Error: duplicate ingest detected for identical source fingerprint/scope. Use --force to reingest.")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "duplicate_ingest",
                    "source_path": str(source_path),
                    "layer": metadata_layer,
                    "campaign_id": campaign_id,
                    "source_class": source_class,
                    "source_fingerprint": source_fingerprint,
                },
            )
            return
        self.logger.info("Ingest start run_id=%s source=%s", run_id, source_path)
        self._record_event(
            "ingest_runs",
            {
                "run_id": run_id,
                "timestamp": _utc_now_iso(),
                "status": "started",
                "source_path": str(source_path),
                "layer": metadata_layer,
                "campaign_id": campaign_id,
                "source_class": source_class,
                "title": title,
                "document_id": document_id,
                "chunk_min_chars": parsed.chunk_min_chars,
                "entity_concurrency": parsed.entity_concurrency,
                "fact_concurrency": parsed.fact_concurrency,
                "extraction_batch_size": parsed.batch_size,
                "source_fingerprint": source_fingerprint,
            },
        )

        try:
            t0 = time.perf_counter()
            project_root = Path(__file__).resolve().parents[1]
            corpus_root = (project_root / "corpus" / "eldyrwild-markdown").resolve()
            try:
                corpus_source_path = source_path.resolve().relative_to(corpus_root).as_posix()
            except ValueError:
                corpus_source_path = source_path.resolve().as_posix()
            evidence_units = chunk_document(
                docx_path=source_path,
                document_id=document_id,
                document_title=title,
                canon_layer=metadata_layer,
                campaign_id=campaign_id,
                source_class=source_class,
                min_chars=parsed.chunk_min_chars,
                corpus_source_path=corpus_source_path,
            )
            chunk_ms = int((time.perf_counter() - t0) * 1000)
            self._record_event(
                "model_calls",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "stage": "chunk_document",
                    "duration_ms": chunk_ms,
                    "input_units": len(evidence_units),
                },
            )
            print(f"  Chunking... {len(evidence_units)} evidence units")
            self.logger.info(
                "Ingest run_id=%s stage=chunk_document units=%d duration_ms=%d",
                run_id,
                len(evidence_units),
                chunk_ms,
            )
            if len(evidence_units) == 0:
                raise RuntimeError("Early exit: chunking produced zero evidence units.")

            recap_artifacts: dict[str, list[dict[str, Any]]] = {
                "event_records": [],
                "claims": [],
            }
            entity_model = _load_fast_smart_model_id()
            fact_model = _load_fact_structured_model_id()

            if parsed.use_openai_batch_api:
                batch_work = self.logs_dir / "openai_batch" / run_id
                batch_work.mkdir(parents=True, exist_ok=True)

                t1 = time.perf_counter()
                ent_lines, ent_manifest = prepare_entity_batch_requests(
                    evidence_units,
                    known_entities=self.store.list_entities(),
                    model=entity_model,
                    batch_size=parsed.batch_size,
                    cache_dir=cache_dir,
                )
                _write_json(batch_work / "entity_batch_manifest.json", ent_manifest)
                ent_batch_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
                entity_batch_api_calls = 0
                if ent_lines:
                    batch_client = OpenAI(api_key=api_key)
                    out_rows, err_rows, _meta = run_batch_job(
                        batch_client,
                        lines=ent_lines,
                        work_dir=batch_work,
                        file_prefix="entity",
                    )
                    if err_rows:
                        print(
                            f"  Warning: entity batch error file has {len(err_rows)} row(s).",
                            flush=True,
                        )
                    fails, ent_batch_usage = apply_entity_batch_outputs_to_cache(
                        out_rows,
                        ent_manifest,
                        model_id=entity_model,
                        cache_dir=cache_dir,
                    )
                    if fails:
                        raise RuntimeError(
                            "OpenAI Batch entity step failed for custom_id(s): " + ", ".join(fails)
                        )
                    entity_batch_api_calls = 1

                entity_result = run_entity_extraction(
                    evidence_units,
                    known_entities=self.store.list_entities(),
                    model=entity_model,
                    concurrency=parsed.entity_concurrency,
                    batch_size=parsed.batch_size,
                    cache_dir=cache_dir,
                    openai_client=None,
                    allow_heuristic_fallback=False,
                    recap_artifacts=recap_artifacts,
                )
                entities = entity_result["entities"]
                entity_ms = int((time.perf_counter() - t1) * 1000)
                self._record_event(
                    "model_calls",
                    {
                        "run_id": run_id,
                        "timestamp": _utc_now_iso(),
                        "stage": "entity_extraction",
                        "duration_ms": entity_ms,
                        "input_units": len(evidence_units),
                        "output_entities": len(entities),
                        "model_role": "structured_generation",
                        "usage": ent_batch_usage,
                        "cache_hits": entity_result["cache_hits"],
                        "cache_misses": entity_result["cache_misses"],
                        "model_name": entity_result.get("model_name", ""),
                        "event_records_count": len(recap_artifacts["event_records"]),
                        "claims_count": len(recap_artifacts["claims"]),
                        "openai_batch": True,
                        "api_calls": entity_batch_api_calls,
                    },
                )
                print(f"  Pass 1 entity extraction (OpenAI Batch)... {len(entities)} entities")
                self.logger.info(
                    "Ingest run_id=%s stage=entity_extraction batch_api entities=%d duration_ms=%d",
                    run_id,
                    len(entities),
                    entity_ms,
                )
            else:
                entity_client = AsyncOpenAIResponsesEntityClient(api_key=api_key)
                t1 = time.perf_counter()
                entity_result = run_entity_extraction(
                    evidence_units,
                    known_entities=self.store.list_entities(),
                    model=entity_model,
                    concurrency=parsed.entity_concurrency,
                    batch_size=parsed.batch_size,
                    cache_dir=cache_dir,
                    openai_client=entity_client,
                    allow_heuristic_fallback=False,
                    recap_artifacts=recap_artifacts,
                )
                entities = entity_result["entities"]
                entity_usage = entity_result["usage"]
                entity_ms = int((time.perf_counter() - t1) * 1000)
                self._record_event(
                    "model_calls",
                    {
                        "run_id": run_id,
                        "timestamp": _utc_now_iso(),
                        "stage": "entity_extraction",
                        "duration_ms": entity_ms,
                        "input_units": len(evidence_units),
                        "output_entities": len(entities),
                        "model_role": "structured_generation",
                        "usage": entity_usage,
                        "cache_hits": entity_result["cache_hits"],
                        "cache_misses": entity_result["cache_misses"],
                        "model_name": entity_result.get("model_name", ""),
                        "event_records_count": len(recap_artifacts["event_records"]),
                        "claims_count": len(recap_artifacts["claims"]),
                    },
                )
                print(f"  Pass 1 entity extraction... {len(entities)} entities")
                self.logger.info(
                    "Ingest run_id=%s stage=entity_extraction entities=%d duration_ms=%d",
                    run_id,
                    len(entities),
                    entity_ms,
                )

            if len(entities) == 0:
                raise RuntimeError("Early exit: entity extraction produced zero entities.")

            if parsed.use_openai_batch_api:
                batch_work = self.logs_dir / "openai_batch" / run_id
                t2 = time.perf_counter()
                fact_lines, fact_manifest = prepare_fact_batch_requests(
                    evidence_units,
                    entities=entities,
                    model=fact_model,
                    batch_size=parsed.batch_size,
                    cache_dir=cache_dir,
                )
                _write_json(batch_work / "fact_batch_manifest.json", fact_manifest)
                fact_batch_usage = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
                fact_batch_api_calls = 0
                if fact_lines:
                    batch_client = OpenAI(api_key=api_key)
                    out_rows, err_rows, _meta = run_batch_job(
                        batch_client,
                        lines=fact_lines,
                        work_dir=batch_work,
                        file_prefix="fact",
                    )
                    if err_rows:
                        print(
                            f"  Warning: fact batch error file has {len(err_rows)} row(s).",
                            flush=True,
                        )
                    fails, fact_batch_usage = apply_fact_batch_outputs_to_cache(
                        out_rows,
                        fact_manifest,
                        model_id=fact_model,
                        cache_dir=cache_dir,
                    )
                    if fails:
                        raise RuntimeError(
                            "OpenAI Batch fact step failed for custom_id(s): " + ", ".join(fails)
                        )
                    fact_batch_api_calls = 1

                fact_result = run_fact_extraction(
                    evidence_units,
                    entities=entities,
                    canon_layer=metadata_layer,
                    campaign_id=campaign_id,
                    source_class=source_class,
                    model=fact_model,
                    concurrency=parsed.fact_concurrency,
                    batch_size=parsed.batch_size,
                    cache_dir=cache_dir,
                    openai_client=None,
                    allow_heuristic_fallback=False,
                )
                facts = fact_result["facts"]
                fact_ms = int((time.perf_counter() - t2) * 1000)
                self._record_event(
                    "model_calls",
                    {
                        "run_id": run_id,
                        "timestamp": _utc_now_iso(),
                        "stage": "fact_extraction",
                        "duration_ms": fact_ms,
                        "input_units": len(evidence_units),
                        "input_entities": len(entities),
                        "output_facts": len(facts),
                        "model_role": "structured_generation",
                        "usage": fact_batch_usage,
                        "cache_hits": fact_result["cache_hits"],
                        "cache_misses": fact_result["cache_misses"],
                        "scoped_prompts": fact_result["scoped_prompts"],
                        "model_name": fact_result.get("model_name", ""),
                        "openai_batch": True,
                        "api_calls": fact_batch_api_calls,
                    },
                )
                print(f"  Pass 2 fact extraction (OpenAI Batch)... {len(facts)} facts")
                self.logger.info(
                    "Ingest run_id=%s stage=fact_extraction batch_api facts=%d duration_ms=%d",
                    run_id,
                    len(facts),
                    fact_ms,
                )
            else:
                fact_client = AsyncOpenAIResponsesFactClient(api_key=api_key)
                t2 = time.perf_counter()
                fact_result = run_fact_extraction(
                    evidence_units,
                    entities=entities,
                    canon_layer=metadata_layer,
                    campaign_id=campaign_id,
                    source_class=source_class,
                    model=fact_model,
                    concurrency=parsed.fact_concurrency,
                    batch_size=parsed.batch_size,
                    cache_dir=cache_dir,
                    openai_client=fact_client,
                    allow_heuristic_fallback=False,
                )
                facts = fact_result["facts"]
                fact_usage = fact_result["usage"]
                fact_ms = int((time.perf_counter() - t2) * 1000)
                self._record_event(
                    "model_calls",
                    {
                        "run_id": run_id,
                        "timestamp": _utc_now_iso(),
                        "stage": "fact_extraction",
                        "duration_ms": fact_ms,
                        "input_units": len(evidence_units),
                        "input_entities": len(entities),
                        "output_facts": len(facts),
                        "model_role": "structured_generation",
                        "usage": fact_usage,
                        "cache_hits": fact_result["cache_hits"],
                        "cache_misses": fact_result["cache_misses"],
                        "scoped_prompts": fact_result["scoped_prompts"],
                        "model_name": fact_result.get("model_name", ""),
                    },
                )
                print(f"  Pass 2 fact extraction... {len(facts)} facts")
                self.logger.info(
                    "Ingest run_id=%s stage=fact_extraction facts=%d duration_ms=%d",
                    run_id,
                    len(facts),
                    fact_ms,
                )
            print(f"  Pass 2 fact extraction... {len(facts)} facts")
            self.logger.info(
                "Ingest run_id=%s stage=fact_extraction facts=%d duration_ms=%d",
                run_id,
                len(facts),
                fact_ms,
            )
        except Exception as exc:
            print(f"Error: ingest failed: {exc}")
            self.logger.exception("Ingest failed run_id=%s", run_id)
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": str(exc),
                    "source_path": str(source_path),
                },
            )
            return

        artifacts_dir = self.logs_dir / "ingest_artifacts" / run_id
        gate_report = _build_ingest_gate_report(
            evidence_units=evidence_units,
            entities=entities,
            facts=facts,
        )
        _write_ingest_stage_artifacts(
            artifacts_dir=artifacts_dir,
            evidence_units=evidence_units,
            entities=entities,
            facts=facts,
            gate_report=gate_report,
        )
        if not gate_report["overall_pass"]:
            print(f"Error: ingest stage gates failed. See {artifacts_dir / 'gate_report.json'}")
            self.logger.error("Ingest gate failure run_id=%s", run_id)
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "stage_gates_failed",
                    "source_path": str(source_path),
                    "artifact_dir": str(artifacts_dir),
                    "gate_report_path": str(artifacts_dir / "gate_report.json"),
                },
            )
            return

        self.store.add_evidence_units(evidence_units)
        self.store.add_entities(entities)
        self.store.add_facts(facts)
        if recap_artifacts["event_records"]:
            self.store.add_event_records(recap_artifacts["event_records"])
        if recap_artifacts["claims"]:
            self.store.add_claims(recap_artifacts["claims"])
        self.store.record_ingest_fingerprint(
            ingest_key,
            {
                "source_path": str(source_path),
                    "layer": metadata_layer,
                "campaign_id": campaign_id,
                "source_class": source_class,
                "document_id": document_id,
                "recorded_at": _utc_now_iso(),
                "source_fingerprint": source_fingerprint,
            },
        )
        self.store.save()
        print(
            "  Stored. Total: "
            f"{len(self.store.evidence_units)} evidence units, "
            f"{len(self.store.entities)} entities, "
            f"{len(self.store.facts)} facts, "
            f"{len(recap_artifacts['event_records'])} event_records, "
            f"{len(recap_artifacts['claims'])} claims."
        )
        total_ms = int((time.perf_counter() - started) * 1000)
        self._record_event(
            "ingest_runs",
            {
                "run_id": run_id,
                "timestamp": _utc_now_iso(),
                "status": "completed",
                "duration_ms": total_ms,
                "source_path": str(source_path),
                "layer": metadata_layer,
                "campaign_id": campaign_id,
                "source_class": source_class,
                "document_id": document_id,
                "chunk_min_chars": parsed.chunk_min_chars,
                "entity_concurrency": parsed.entity_concurrency,
                "fact_concurrency": parsed.fact_concurrency,
                "extraction_batch_size": parsed.batch_size,
                "source_fingerprint": source_fingerprint,
                "artifact_dir": str(artifacts_dir),
                "gate_report_path": str(artifacts_dir / "gate_report.json"),
                "counts": {
                    "evidence_units_extracted": len(evidence_units),
                    "entities_extracted": len(entities),
                    "facts_extracted": len(facts),
                    "store_evidence_units_total": len(self.store.evidence_units),
                    "store_entities_total": len(self.store.entities),
                    "store_facts_total": len(self.store.facts),
                },
            },
        )
        self.logger.info("Ingest completed run_id=%s duration_ms=%d", run_id, total_ms)

    def _cmd_ask(self, args: Sequence[str]) -> None:
        run_id = f"ask-{uuid.uuid4().hex[:10]}"
        started = time.perf_counter()
        parser = argparse.ArgumentParser(prog="ask", add_help=False)
        parser.add_argument("question")
        parser.add_argument("--campaign")
        parser.add_argument("--require-campaign", action="store_true")
        parser.add_argument(
            "--scope-document",
            action="append",
            default=[],
            help="Document ID to prioritize for scoped retrieval (repeatable).",
        )
        parser.add_argument(
            "--scope-confidence",
            type=float,
            default=1.0,
            help="Confidence in scope inference [0.0, 1.0].",
        )
        parser.add_argument(
            "--min-scope-confidence",
            type=float,
            default=0.75,
            help="Minimum scope confidence required for hard out-of-scope exclusion.",
        )
        parser.add_argument(
            "--min-entity-evidence-count",
            type=int,
            default=2,
            help="Minimum evidence count before confident out-of-scope classification.",
        )
        parser.add_argument(
            "--hard-exclude-out-of-scope",
            action="store_true",
            help="Hard-exclude confidently out-of-scope entities from context.",
        )
        parser.add_argument(
            "--unknown-exploration-quota",
            type=int,
            default=10,
            help="Reserve top-context slots for unknown-signal entities.",
        )
        parser.add_argument(
            "--include-scope-annotations",
            action="store_true",
            help="Show per-entity scope relevance annotations in rendered context.",
        )
        parser.add_argument(
            "--retrieval",
            action="store_true",
            default=True,
            help="Use question-aware retrieval to select relevant entities (default).",
        )
        parser.add_argument(
            "--no-retrieval",
            action="store_true",
            default=False,
            help="Disable retrieval; send full projection to the LLM.",
        )
        parser.add_argument(
            "--retrieval-top-k",
            type=int,
            default=30,
            help="Max entities to retrieve (before graph expansion). Default: 30.",
        )
        parser.add_argument(
            "--evidence-first",
            action="store_true",
            default=False,
            help="Run organization-first evidence retrieval before entity ranking.",
        )
        parser.add_argument(
            "--evidence-top-k",
            type=int,
            default=24,
            help="Top evidence units to seed before neighbor expansion. Default: 24.",
        )
        parser.add_argument(
            "--evidence-neighbor-window",
            type=int,
            default=1,
            help="Source-order window for evidence neighbor expansion. Default: 1.",
        )
        parser.add_argument(
            "--evidence-max-neighbors",
            type=int,
            default=24,
            help="Maximum evidence neighbors to add. Default: 24.",
        )
        parser.add_argument(
            "--evidence-entity-boost",
            type=float,
            default=0.8,
            help="Boost weight when evidence links to entity provenance. Default: 0.8.",
        )
        parser.add_argument(
            "--corpus-lexicon-boost",
            action="store_true",
            default=False,
            help="Enable corpus-lexicon phrase boosts for evidence retrieval.",
        )
        parser.add_argument(
            "--corpus-lexicon-path",
            type=str,
            default="",
            help="Optional path to corpus lexicon JSON (defaults to store/corpus_lexicon.json).",
        )
        parser.add_argument(
            "--alias-normalization",
            action="store_true",
            default=False,
            help="Enable alias/acronym normalization from corpus lexicon.",
        )
        parser.add_argument(
            "--alias-match-weight",
            type=float,
            default=0.06,
            help="Per-hit score boost for corpus alias phrase matches. Default: 0.06.",
        )
        parser.add_argument(
            "--corpus-lexicon-max-boost",
            type=float,
            default=0.35,
            help="Max total corpus lexicon phrase boost per unit. Default: 0.35.",
        )
        parser.add_argument(
            "--evidence-adaptive-top-k",
            action="store_true",
            default=False,
            help="Enable adaptive evidence top-k up to a bounded maximum.",
        )
        parser.add_argument(
            "--evidence-adaptive-top-k-max",
            type=int,
            default=48,
            help="Upper cap for adaptive evidence top-k. Default: 48.",
        )
        parser.add_argument(
            "--evidence-density-threshold",
            type=float,
            default=0.3,
            help="Adaptive threshold as max_score multiplier. Default: 0.3.",
        )
        parser.add_argument(
            "--evidence-entity-aware",
            action="store_true",
            default=False,
            help="Enable provenance-aware evidence second pass from top entities.",
        )
        parser.add_argument(
            "--evidence-two-pass",
            action="store_true",
            default=False,
            help=(
                "Run evidence without entity-aware expansion, then add provenance chunks "
                "from top overlap entities (ordered two-pass; use instead of --evidence-entity-aware)."
            ),
        )
        parser.add_argument(
            "--evidence-entity-quota",
            type=int,
            default=10,
            help="How many top overlap entities to inspect for evidence expansion.",
        )
        parser.add_argument(
            "--evidence-entity-evidence-quota",
            type=int,
            default=12,
            help="How many provenance evidence IDs to add in entity-aware pass.",
        )
        parser.add_argument(
            "--semantic-rerank",
            action="store_true",
            default=False,
            help="Apply embedding-based rerank over top lexical retrieval candidates.",
        )
        parser.add_argument(
            "--semantic-rerank-top-k",
            type=int,
            default=24,
            help="How many retrieved entities to rerank semantically. Default: 24.",
        )
        parser.add_argument(
            "--semantic-rerank-weight",
            type=float,
            default=0.6,
            help="Weight for semantic similarity when fusing rerank score. Default: 0.6.",
        )
        parser.add_argument(
            "--semantic-rerank-model",
            type=str,
            default="perplexity-ai/pplx-embed-v1-0.6B",
            help="Embedding model ID for semantic reranking.",
        )
        parser.add_argument(
            "--context-max-entities",
            type=int,
            default=80,
            help="Hard cap for entities passed to context formatter. Default: 80.",
        )
        parser.add_argument(
            "--context-max-chars",
            type=int,
            default=20000,
            help="Hard cap target for formatted context chars. Default: 20000.",
        )
        parser.add_argument(
            "--synthesis-profile",
            type=str,
            default="",
            help="Optional synthesis prompt profile (e.g. mirathorn).",
        )
        parser.add_argument(
            "--synthesis-verbosity",
            type=str,
            default="",
            help="Optional synthesis verbosity mode (default|compact|verbose).",
        )
        parser.add_argument(
            "--two-step-synthesis",
            action="store_true",
            default=False,
            help="First LLM call extracts claims from context; second call answers from claims.",
        )
        parser.add_argument(
            "--synthesis-citation-structure",
            action="store_true",
            default=False,
            help="Append Evidence/Analysis structure requirements to the synthesis system prompt.",
        )
        parser.add_argument(
            "--document-planner",
            action="store_true",
            default=False,
            help="LLM-select scope documents before evidence-first chunk retrieval.",
        )
        parser.add_argument(
            "--document-planner-model",
            type=str,
            default="",
            help="Optional model override for document planner (default from MODEL_POLICY).",
        )
        parser.add_argument(
            "--projection-enriched",
            action="store_true",
            default=False,
            help="Append provenance evidence text for retrieved entities to context.",
        )
        parser.add_argument(
            "--rich-entity-summaries",
            action="store_true",
            default=False,
            help="Use denser entity summaries for retrieval (keyword/index signal).",
        )
        parser.add_argument(
            "--use-wiki",
            action="store_true",
            default=False,
            help="Use LLM-authored wiki pages for retrieval index and context when wiki_pages.json exists.",
        )
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return

        if parsed.require_campaign and not parsed.campaign:
            print("Error: campaign scope is required for this ask run.")
            self._record_event(
                "ask_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "missing_campaign_scope",
                    "question": parsed.question,
                    "campaign_id": parsed.campaign,
                },
            )
            return

        if parsed.scope_confidence < 0.0 or parsed.scope_confidence > 1.0:
            print("Error: --scope-confidence must be between 0.0 and 1.0.")
            return
        if parsed.min_scope_confidence < 0.0 or parsed.min_scope_confidence > 1.0:
            print("Error: --min-scope-confidence must be between 0.0 and 1.0.")
            return
        if parsed.min_entity_evidence_count < 1:
            print("Error: --min-entity-evidence-count must be >= 1.")
            return
        if parsed.unknown_exploration_quota < 0:
            print("Error: --unknown-exploration-quota must be >= 0.")
            return
        if parsed.semantic_rerank_top_k < 1:
            print("Error: --semantic-rerank-top-k must be >= 1.")
            return
        if parsed.semantic_rerank_weight < 0:
            print("Error: --semantic-rerank-weight must be >= 0.")
            return
        if parsed.evidence_top_k < 1:
            print("Error: --evidence-top-k must be >= 1.")
            return
        if parsed.evidence_neighbor_window < 0:
            print("Error: --evidence-neighbor-window must be >= 0.")
            return
        if parsed.evidence_max_neighbors < 0:
            print("Error: --evidence-max-neighbors must be >= 0.")
            return
        if parsed.evidence_entity_boost < 0:
            print("Error: --evidence-entity-boost must be >= 0.")
            return
        if parsed.alias_match_weight < 0:
            print("Error: --alias-match-weight must be >= 0.")
            return
        if parsed.corpus_lexicon_max_boost < 0:
            print("Error: --corpus-lexicon-max-boost must be >= 0.")
            return
        if parsed.evidence_adaptive_top_k_max < 1:
            print("Error: --evidence-adaptive-top-k-max must be >= 1.")
            return
        if parsed.evidence_density_threshold <= 0 or parsed.evidence_density_threshold > 1:
            print("Error: --evidence-density-threshold must be in (0, 1].")
            return
        if parsed.evidence_entity_quota < 0:
            print("Error: --evidence-entity-quota must be >= 0.")
            return
        if parsed.evidence_entity_evidence_quota < 0:
            print("Error: --evidence-entity-evidence-quota must be >= 0.")
            return
        if parsed.context_max_entities < 1:
            print("Error: --context-max-entities must be >= 1.")
            return
        if parsed.context_max_chars < 1000:
            print("Error: --context-max-chars must be >= 1000.")
            return

        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY is required for ask.")
            self._record_event(
                "ask_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "missing_openai_api_key",
                    "question": parsed.question,
                    "campaign_id": parsed.campaign,
                },
            )
            return

        if parsed.rich_entity_summaries:
            os.environ["DMB_RICH_ENTITY_SUMMARIES"] = "1"
            self._entity_index = None
        else:
            os.environ.pop("DMB_RICH_ENTITY_SUMMARIES", None)

        use_wiki = bool(parsed.use_wiki) or os.environ.get("DMB_USE_WIKI", "").strip() == "1"
        wiki_pages_for_context: dict[str, str] | None = None
        if use_wiki:
            if self.store.has_wiki():
                wiki_pages_for_context = dict(self.store.wiki_pages)
                self._entity_index = None
            else:
                print(
                    "Warning: --use-wiki / DMB_USE_WIKI but store has no wiki pages; "
                    "run `compile-wiki` first. Using projection only.",
                    file=sys.stderr,
                )
                use_wiki = False

        projection = self.store.project(parsed.campaign)
        scope_document_ids = [str(doc_id).strip() for doc_id in parsed.scope_document if str(doc_id).strip()]
        document_planner_meta: dict[str, Any] = {"enabled": False}
        if parsed.document_planner:
            roster, candidate_doc_ids = build_document_roster(
                self.store.evidence_units,
                campaign_id=parsed.campaign,
            )
            dpmodel = (parsed.document_planner_model or "").strip() or None
            doc_plan = asyncio.run(
                plan_documents_async(
                    parsed.question,
                    roster,
                    candidate_doc_ids,
                    model=dpmodel,
                )
            )
            document_planner_meta = {
                "enabled": True,
                "selected_document_ids": list(doc_plan.selected_document_ids),
                "reasoning": doc_plan.reasoning,
                "duration_ms": doc_plan.duration_ms,
                "fallback": doc_plan.fallback,
                "model": doc_plan.model,
            }
            if not doc_plan.fallback:
                scope_document_ids = sorted(
                    set(scope_document_ids) | set(doc_plan.selected_document_ids)
                )
        if scope_document_ids:
            projection = attach_scope_relevance_metadata(
                projection=projection,
                evidence_units=self.store.evidence_units,
                scope_document_ids=scope_document_ids,
                scope_confidence=parsed.scope_confidence,
                min_scope_confidence=parsed.min_scope_confidence,
                min_entity_evidence_count=parsed.min_entity_evidence_count,
                mentioned_entity_ids=question_mentioned_entity_ids(
                    parsed.question, self.store.list_entities()
                ),
            )
        use_retrieval = parsed.retrieval and not parsed.no_retrieval
        retrieval_meta: dict[str, Any] = {
            "enabled": False,
            "document_planner": document_planner_meta,
            "wiki": {
                "enabled": bool(use_wiki and wiki_pages_for_context),
                "page_count": len(wiki_pages_for_context or {}),
            },
        }
        priority_entity_ids: list[str] = []
        corpus_lexicon: dict[str, Any] | None = None
        if parsed.corpus_lexicon_boost or parsed.alias_normalization:
            lexicon_path = (
                Path(parsed.corpus_lexicon_path).expanduser()
                if parsed.corpus_lexicon_path
                else self.store.store_dir / "corpus_lexicon.json"
            )
            if lexicon_path.exists():
                try:
                    payload = json.loads(lexicon_path.read_text(encoding="utf-8"))
                    if isinstance(payload, dict):
                        corpus_lexicon = payload
                except json.JSONDecodeError:
                    self.logger.warning("Invalid corpus lexicon JSON at %s", lexicon_path)
            else:
                self.logger.info("Corpus lexicon path not found: %s", lexicon_path)
        if use_retrieval:
            retrieval_started = time.perf_counter()
            evidence_meta: dict[str, Any] = {"enabled": False}
            evidence_entity_scores: dict[str, float] = {}
            if parsed.evidence_first:
                evidence_started = time.perf_counter()
                two_pass_provenance_added = 0
                entity_aware_pass1 = (
                    bool(parsed.evidence_entity_aware) and not bool(parsed.evidence_two_pass)
                )
                evidence_result = retrieve_relevant_evidence(
                    parsed.question,
                    self.store.evidence_units,
                    campaign_id=parsed.campaign,
                    scope_document_ids=scope_document_ids,
                    top_k=parsed.evidence_top_k,
                    neighbor_window=parsed.evidence_neighbor_window,
                    max_neighbors=parsed.evidence_max_neighbors,
                    corpus_lexicon=(
                        corpus_lexicon
                        if (parsed.corpus_lexicon_boost or parsed.alias_normalization)
                        else None
                    ),
                    enable_alias_normalization=parsed.alias_normalization,
                    alias_match_weight=parsed.alias_match_weight,
                    lexicon_max_boost=parsed.corpus_lexicon_max_boost,
                    include_legacy_phrase_boost=True,
                    adaptive_top_k=parsed.evidence_adaptive_top_k,
                    adaptive_top_k_max=parsed.evidence_adaptive_top_k_max,
                    adaptive_density_threshold=parsed.evidence_density_threshold,
                    projection=projection,
                    entity_awareness_enabled=entity_aware_pass1,
                    entity_quota=parsed.evidence_entity_quota,
                    entity_evidence_quota=parsed.evidence_entity_evidence_quota,
                )
                if parsed.evidence_two_pass:
                    base_ids = list(evidence_result.selected_evidence_ids)
                    seen: set[str] = set(base_ids)
                    overlap_scores = rank_entities_by_evidence_overlap(projection, seen)
                    top_entities = sorted(
                        overlap_scores,
                        key=lambda eid: overlap_scores[eid],
                        reverse=True,
                    )[: max(1, int(parsed.evidence_entity_quota))]
                    provenance_ids = collect_provenance_evidence_for_entities(
                        projection,
                        top_entities,
                    )
                    quota = max(0, int(parsed.evidence_entity_evidence_quota))
                    merged = list(base_ids)
                    for eid in provenance_ids:
                        if eid in seen:
                            continue
                        if two_pass_provenance_added >= quota:
                            break
                        merged.append(eid)
                        seen.add(eid)
                        two_pass_provenance_added += 1
                    doc_set: set[str] = set()
                    for unit in self.store.evidence_units:
                        ue = str(unit.get("evidence_id", "")).strip()
                        if ue in seen:
                            doc_set.add(str(unit.get("document_id", "")).strip())
                    dbg = dict(evidence_result.debug)
                    dbg["two_pass"] = True
                    dbg["two_pass_provenance_added"] = two_pass_provenance_added
                    evidence_result = replace(
                        evidence_result,
                        selected_evidence_ids=merged,
                        selected_document_ids=sorted(doc_set),
                        debug=dbg,
                    )
                evidence_entity_scores = rank_entities_by_evidence_overlap(
                    projection,
                    set(evidence_result.selected_evidence_ids),
                )
                priority_entity_ids = sorted(
                    evidence_entity_scores,
                    key=lambda entity_id: evidence_entity_scores[entity_id],
                    reverse=True,
                )
                evidence_meta = {
                    "enabled": True,
                    "duration_ms": int((time.perf_counter() - evidence_started) * 1000),
                    "top_k": parsed.evidence_top_k,
                    "neighbor_window": parsed.evidence_neighbor_window,
                    "max_neighbors": parsed.evidence_max_neighbors,
                    "selected_count": len(evidence_result.selected_evidence_ids),
                    "seeded_count": len(evidence_result.seeded_evidence_ids),
                    "selected_evidence_ids": evidence_result.selected_evidence_ids,
                    "selected_document_ids": evidence_result.selected_document_ids,
                    "debug": evidence_result.debug,
                    "corpus_lexicon_boost": bool(parsed.corpus_lexicon_boost),
                    "alias_normalization": bool(parsed.alias_normalization),
                    "evidence_adaptive_top_k": bool(parsed.evidence_adaptive_top_k),
                    "evidence_entity_aware": bool(parsed.evidence_entity_aware),
                    "evidence_two_pass": bool(parsed.evidence_two_pass),
                    "two_pass_provenance_added": two_pass_provenance_added,
                }
            ranked, self._entity_index = retrieve_relevant_entities(
                parsed.question,
                projection,
                self.store.list_entities(),
                top_k=parsed.retrieval_top_k,
                index=getattr(self, "_entity_index", None),
                wiki_pages=wiki_pages_for_context if use_wiki else None,
            )
            if evidence_entity_scores:
                ranked = self._fuse_ranked_entities(
                    ranked,
                    evidence_entity_scores,
                    evidence_boost=parsed.evidence_entity_boost,
                    cap=parsed.retrieval_top_k,
                )
            semantic_rerank_meta: dict[str, Any] = {
                "enabled": False,
            }
            if parsed.semantic_rerank and ranked:
                emb_model = self._load_retrieval_embedding_model(parsed.semantic_rerank_model)
                if emb_model is not None:
                    rerank_started = time.perf_counter()
                    ranked = semantic_rerank_entities(
                        parsed.question,
                        ranked,
                        index=self._entity_index,
                        embedding_model=emb_model,
                        rerank_top_k=parsed.semantic_rerank_top_k,
                        blend_weight=parsed.semantic_rerank_weight,
                    )
                    semantic_rerank_meta = {
                        "enabled": True,
                        "top_k": parsed.semantic_rerank_top_k,
                        "weight": parsed.semantic_rerank_weight,
                        "model": parsed.semantic_rerank_model,
                        "duration_ms": int((time.perf_counter() - rerank_started) * 1000),
                    }
                else:
                    semantic_rerank_meta = {
                        "enabled": False,
                        "requested": True,
                        "reason": "embedding_unavailable",
                    }
            selected_ids = {eid for eid, _ in ranked}
            pre_count = len(projection.get("entities", {}))
            projection = filter_projection(projection, selected_ids)
            retrieval_ms = int((time.perf_counter() - retrieval_started) * 1000)
            retrieval_meta = {
                "enabled": True,
                "top_k": parsed.retrieval_top_k,
                "pre_filter_count": pre_count,
                "post_filter_count": len(selected_ids),
                "duration_ms": retrieval_ms,
                "top_5": [(eid, round(s, 4)) for eid, s in ranked[:5]],
                "selected_entity_ids": [eid for eid, _ in ranked],
                "semantic_rerank": semantic_rerank_meta,
                "evidence_first": evidence_meta,
                "document_planner": document_planner_meta,
                "wiki": {
                    "enabled": bool(use_wiki and wiki_pages_for_context),
                    "page_count": len(wiki_pages_for_context or {}),
                },
            }
            self.logger.info(
                "Ask run_id=%s stage=retrieval entities=%d/%d duration_ms=%d",
                run_id,
                len(selected_ids),
                pre_count,
                retrieval_ms,
            )

        self._record_event(
            "ask_runs",
            {
                "run_id": run_id,
                "timestamp": _utc_now_iso(),
                "status": "started",
                "question": parsed.question,
                "campaign_id": parsed.campaign,
                "scope_document_ids": scope_document_ids,
                "scope_confidence": parsed.scope_confidence,
                "hard_exclude_out_of_scope": parsed.hard_exclude_out_of_scope,
                "projection_metrics": projection.get("metrics", {}),
                "retrieval": retrieval_meta,
            },
        )
        self.logger.info(
            "Ask start run_id=%s campaign_id=%s question_chars=%d projected_entities=%s",
            run_id,
            parsed.campaign,
            len(parsed.question),
            projection.get("metrics", {}).get("projected_entities"),
        )
        try:
            format_started = time.perf_counter()
            context, context_entity_cap, context_budget_truncated = self._fit_context_budget(
                projection=projection,
                entities=self.store.list_entities(),
                question=parsed.question,
                evidence_units=self.store.evidence_units,
                scope_document_ids=scope_document_ids,
                scope_confidence=parsed.scope_confidence,
                min_scope_confidence=parsed.min_scope_confidence,
                min_entity_evidence_count=parsed.min_entity_evidence_count,
                hard_exclude_out_of_scope=parsed.hard_exclude_out_of_scope,
                unknown_exploration_quota=parsed.unknown_exploration_quota,
                include_scope_annotations=parsed.include_scope_annotations,
                priority_entity_ids=priority_entity_ids,
                max_entities=parsed.context_max_entities,
                max_chars=parsed.context_max_chars,
                wiki_pages=wiki_pages_for_context if use_wiki else None,
            )
            context_chars = len(context)
            format_ms = int((time.perf_counter() - format_started) * 1000)
            self.logger.info(
                "Ask run_id=%s stage=context_formatter context_chars=%d duration_ms=%d",
                run_id,
                context_chars,
                format_ms,
            )
            projection_enriched_meta: dict[str, Any] = {"enabled": False}
            if parsed.projection_enriched and use_retrieval:
                appendix, pe_stats = DungeonBuddyCLI._build_provenance_appendix(
                    projection=projection,
                    evidence_units=self.store.evidence_units,
                    max_total_chars=parsed.context_max_chars,
                    base_context_len=len(context),
                )
                if appendix:
                    combined = context + "\n\n" + appendix
                    if len(combined) > parsed.context_max_chars:
                        combined = combined[: parsed.context_max_chars]
                    context = combined
                    context_chars = len(context)
                    projection_enriched_meta = {"enabled": True, **pe_stats}
            elif parsed.projection_enriched:
                projection_enriched_meta = {
                    "enabled": False,
                    "reason": "requires_retrieval",
                }
            retrieval_meta["projection_enriched"] = projection_enriched_meta
            retrieval_meta["rich_entity_summaries"] = bool(parsed.rich_entity_summaries)

            model_started = time.perf_counter()
            synthesis_meta: dict[str, Any] = {}
            answer = asyncio.run(
                synthesize_answer_async(
                    context,
                    parsed.question,
                    synthesis_profile=(parsed.synthesis_profile or None),
                    verbosity=(parsed.synthesis_verbosity or None),
                    two_step=True if parsed.two_step_synthesis else None,
                    citation_structure=True if parsed.synthesis_citation_structure else None,
                    synthesis_meta_out=synthesis_meta,
                    wiki_mode=bool(use_wiki and wiki_pages_for_context),
                )
            )
            model_ms = int((time.perf_counter() - model_started) * 1000)
            self._record_event(
                "model_calls",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "stage": "synthesis",
                    "duration_ms": model_ms,
                    "model_role": "retrieval_synthesis",
                    "context_chars": len(context),
                    "question_chars": len(parsed.question),
                    "answer_chars": len(answer),
                    "synthesis_profile": parsed.synthesis_profile or "",
                    "synthesis_verbosity": parsed.synthesis_verbosity or "",
                    "synthesis_meta": synthesis_meta,
                },
            )
            self.logger.info(
                "Ask run_id=%s stage=synthesis answer_chars=%d duration_ms=%d",
                run_id,
                len(answer),
                model_ms,
            )
        except Exception as exc:
            print(f"Error: ask failed: {exc}")
            self.logger.exception("Ask failed run_id=%s", run_id)
            self._record_event(
                "ask_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": str(exc),
                    "question": parsed.question,
                    "campaign_id": parsed.campaign,
                },
            )
            self._last_ask_meta = {
                "run_id": run_id,
                "question": parsed.question,
                "status": "error",
                "error": str(exc),
                "retrieval": retrieval_meta,
                "synthesis_profile": parsed.synthesis_profile or "",
                "synthesis_verbosity": parsed.synthesis_verbosity or "",
                "synthesis_meta": {},
            }
            return
        print(answer)
        total_ms = int((time.perf_counter() - started) * 1000)
        self._last_ask_meta = {
            "run_id": run_id,
            "question": parsed.question,
            "status": "completed",
            "duration_ms": total_ms,
            "context_chars": context_chars,
            "context_text": context,
            "context_entity_cap": context_entity_cap,
            "context_budget_truncated": context_budget_truncated,
            "answer_chars": len(answer),
            "retrieval": retrieval_meta,
            "projection_metrics": projection.get("metrics", {}),
            "synthesis_profile": parsed.synthesis_profile or "",
            "synthesis_verbosity": parsed.synthesis_verbosity or "",
            "synthesis_meta": synthesis_meta,
        }
        self._record_event(
            "ask_runs",
            {
                "run_id": run_id,
                "timestamp": _utc_now_iso(),
                "status": "completed",
                "duration_ms": total_ms,
                "question": parsed.question,
                "campaign_id": parsed.campaign,
                "answer_chars": len(answer),
                "projection_metrics": projection.get("metrics", {}),
                "retrieval": retrieval_meta,
                "synthesis_profile": parsed.synthesis_profile or "",
                "synthesis_verbosity": parsed.synthesis_verbosity or "",
            },
        )
        self.logger.info("Ask completed run_id=%s duration_ms=%d", run_id, total_ms)

    def _cmd_entities(self, args: Sequence[str]) -> None:
        if args:
            print("Error: entities takes no arguments")
            return
        counts = _fact_counts_by_entity(self.store)
        entities = sorted(
            self.store.list_entities(),
            key=lambda entity: counts.get(str(entity.get("entity_id", "")), 0),
            reverse=True,
        )
        if not entities:
            print("(no entities)")
            return
        for entity in entities:
            entity_id = str(entity.get("entity_id", ""))
            display_name = str(entity.get("display_name", entity_id))
            entity_class = str(entity.get("entity_class", entity.get("entity_type", "concept")))
            fact_count = counts.get(entity_id, 0)
            print(f"- {display_name} ({entity_class}) [{entity_id}] facts={fact_count}")
        self.logger.info("Entities listed count=%d", len(entities))

    def _cmd_projection(self, args: Sequence[str]) -> None:
        parser = argparse.ArgumentParser(prog="projection", add_help=False)
        parser.add_argument("--campaign")
        parser.add_argument(
            "--scope-document",
            action="append",
            default=[],
            help="Document ID to prioritize for scoped retrieval (repeatable).",
        )
        parser.add_argument("--scope-confidence", type=float, default=1.0)
        parser.add_argument("--min-scope-confidence", type=float, default=0.75)
        parser.add_argument("--min-entity-evidence-count", type=int, default=2)
        parser.add_argument("--hard-exclude-out-of-scope", action="store_true")
        parser.add_argument("--unknown-exploration-quota", type=int, default=10)
        parser.add_argument("--include-scope-annotations", action="store_true")
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return
        if parsed.scope_confidence < 0.0 or parsed.scope_confidence > 1.0:
            print("Error: --scope-confidence must be between 0.0 and 1.0.")
            return
        if parsed.min_scope_confidence < 0.0 or parsed.min_scope_confidence > 1.0:
            print("Error: --min-scope-confidence must be between 0.0 and 1.0.")
            return
        if parsed.min_entity_evidence_count < 1:
            print("Error: --min-entity-evidence-count must be >= 1.")
            return
        if parsed.unknown_exploration_quota < 0:
            print("Error: --unknown-exploration-quota must be >= 0.")
            return
        projection = self.store.project(parsed.campaign)
        scope_document_ids = [str(doc_id).strip() for doc_id in parsed.scope_document if str(doc_id).strip()]
        if scope_document_ids:
            projection = attach_scope_relevance_metadata(
                projection=projection,
                evidence_units=self.store.evidence_units,
                scope_document_ids=scope_document_ids,
                scope_confidence=parsed.scope_confidence,
                min_scope_confidence=parsed.min_scope_confidence,
                min_entity_evidence_count=parsed.min_entity_evidence_count,
            )
        context = format_projection_context(
            projection,
            self.store.list_entities(),
            evidence_units=self.store.evidence_units,
            scope_document_ids=scope_document_ids,
            scope_confidence=parsed.scope_confidence,
            min_scope_confidence=parsed.min_scope_confidence,
            min_entity_evidence_count=parsed.min_entity_evidence_count,
            hard_exclude_out_of_scope=parsed.hard_exclude_out_of_scope,
            unknown_exploration_quota=parsed.unknown_exploration_quota,
            include_scope_annotations=parsed.include_scope_annotations,
        )
        print(context)
        self.logger.info(
            "Projection printed campaign_id=%s projected_entities=%s open_conflicts=%s context_chars=%d",
            parsed.campaign,
            projection.get("metrics", {}).get("projected_entities"),
            projection.get("metrics", {}).get("open_conflicts"),
            len(context),
        )

    def _cmd_canon_decision(self, args: Sequence[str]) -> None:
        parser = argparse.ArgumentParser(prog="canon-decision", add_help=False)
        parser.add_argument("action", choices=["add"])
        parser.add_argument("json_path", type=Path)
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return
        path = parsed.json_path
        if not path.exists():
            print(f"Error: file not found: {path}")
            return
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            print(f"Error: invalid JSON: {exc}")
            return
        if not isinstance(payload, list):
            print("Error: canon decision file must be a JSON array of decisions.")
            return
        try:
            validate_many(payload, "canon_decision.schema.json")
        except Exception as exc:
            print(f"Error: schema validation failed: {exc}")
            return
        self.store.add_canon_decisions(payload)
        self.store.save()
        print(f"Added {len(payload)} canon decision record(s); store saved.")

    def _cmd_compact(self, args: Sequence[str]) -> None:
        if args:
            print("Error: compact takes no arguments")
            return
        stats = self.store.compact()
        self.store.save()
        print(
            "Compaction complete: "
            f"evidence {stats['evidence_before']} -> {stats['evidence_after']}, "
            f"facts {stats['facts_before']} -> {stats['facts_after']}."
        )

    def _cmd_anchor_lint(self, args: Sequence[str]) -> None:
        parser = argparse.ArgumentParser(prog="anchor-lint", add_help=False)
        parser.add_argument(
            "--corpus-root",
            type=str,
            default="corpus/eldyrwild-markdown",
            help="Corpus root path used for relative source anchors.",
        )
        parser.add_argument(
            "--include-legacy-unanchored",
            action="store_true",
            help="Validate legacy_unanchored anchors too (normally skipped).",
        )
        parser.add_argument(
            "--max-issues",
            type=int,
            default=20,
            help="Max issues to print before truncating output.",
        )
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return
        project_root = Path(__file__).resolve().parents[1]
        corpus_root = (project_root / parsed.corpus_root).resolve()
        report = lint_source_anchors(
            corpus_root=corpus_root,
            evidence_units=self.store.evidence_units,
            facts=self.store.facts,
            event_records=self.store.event_records,
            claims=self.store.claims,
            include_legacy_unanchored=bool(parsed.include_legacy_unanchored),
        )
        summary = report["summary"]
        print(
            "Anchor lint: "
            f"ok={report['ok']} "
            f"records_checked={summary['records_checked']} "
            f"anchors_total={summary['anchors_total']} "
            f"anchors_validated={summary['anchors_validated']} "
            f"anchors_valid={summary['anchors_valid']} "
            f"issues={summary['anchors_with_issues']}"
        )
        max_issues = max(0, int(parsed.max_issues))
        issues = report["issues"]
        for issue in issues[:max_issues]:
            print(
                f"- {issue.get('record_type')}:{issue.get('record_id')} "
                f"anchor#{issue.get('anchor_index')} {issue.get('issue')}"
            )
        if len(issues) > max_issues:
            print(f"... {len(issues) - max_issues} more issue(s) not shown")
        if not report["ok"]:
            print("Anchor lint found stale/missing anchors.")

    def _cmd_compile_wiki(self, args: Sequence[str]) -> None:
        parser = argparse.ArgumentParser(prog="compile-wiki", add_help=False)
        parser.add_argument("--campaign", type=str, default="", help="Campaign id for projection (e.g. longmont-c1).")
        parser.add_argument(
            "--min-connectivity",
            type=float,
            default=0.3,
            help="Composite connectivity threshold (default 0.3). Ignored with --full.",
        )
        parser.add_argument(
            "--full",
            action="store_true",
            help="Compile wiki for every projected entity (ignores connectivity threshold).",
        )
        parser.add_argument(
            "--entity",
            action="append",
            default=[],
            help="Compile only this entity_id (repeatable).",
        )
        parser.add_argument(
            "--list",
            action="store_true",
            dest="list_only",
            help="List entity_ids that would be compiled; do not call the model.",
        )
        parser.add_argument(
            "--no-incremental",
            action="store_true",
            help="Recompile all targets even when fact hash unchanged.",
        )
        parser.add_argument(
            "--max-workers",
            type=int,
            default=8,
            help="Parallel LLM calls (default 8).",
        )
        parser.add_argument(
            "--include-generic-names",
            action="store_true",
            help="Do not skip generic display names (she, meat, group, ...).",
        )
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return

        if not os.getenv("OPENAI_API_KEY"):
            print("Error: OPENAI_API_KEY is required for compile-wiki.")
            return

        campaign_id = str(parsed.campaign).strip() or None
        entity_ids = [str(e).strip() for e in parsed.entity if str(e).strip()]

        if parsed.list_only:
            rows = list_wiki_targets(
                self.store,
                campaign_id=campaign_id,
                min_connectivity=parsed.min_connectivity,
                full=parsed.full,
                skip_generic_names=not parsed.include_generic_names,
            )
            print(f"Would compile {len(rows)} entity wiki page(s):")
            for eid, score, dn in rows[:500]:
                print(f"  {eid}\tscore={score:.4f}\t{dn}")
            if len(rows) > 500:
                print(f"  ... and {len(rows) - 500} more")
            return

        try:
            new_pages = compile_wiki(
                self.store,
                campaign_id,
                entity_ids=entity_ids or None,
                min_connectivity=parsed.min_connectivity,
                full=parsed.full,
                incremental=not parsed.no_incremental,
                max_workers=max(1, int(parsed.max_workers)),
                skip_generic_names=not parsed.include_generic_names,
            )
        except Exception as exc:
            print(f"Error: compile-wiki failed: {exc}")
            self.logger.exception("compile-wiki failed")
            return

        self.store.save()
        print(f"compile-wiki: wrote {len(new_pages)} page(s); total wiki pages={len(self.store.wiki_pages)}.")

    @staticmethod
    def _safe_parse(
        parser: argparse.ArgumentParser, args: Sequence[str]
    ) -> argparse.Namespace | None:
        try:
            return parser.parse_args(list(args))
        except SystemExit:
            return None

    def _record_event(self, stream_name: str, payload: dict) -> None:
        path = self.logs_dir / f"{stream_name}.jsonl"
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


DEFAULT_STORE_DIR = Path("out/stores/dungeonbuddy_store")


def _build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DungeonMindBuddy CLI")
    parser.add_argument(
        "--store",
        type=Path,
        default=DEFAULT_STORE_DIR,
        help="Fact store directory (default: out/stores/dungeonbuddy_store)",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable debug-level logs.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_root_parser()
    ns = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if ns.verbose else logging.INFO,
        format=LOGGER_FORMAT,
        force=True,
    )
    cli = DungeonBuddyCLI(store_dir=ns.store, verbose=ns.verbose)
    return cli.run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
