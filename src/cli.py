from __future__ import annotations

import argparse
import asyncio
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
from typing import Sequence

from dotenv import load_dotenv

from src.agent.context_formatter import format_projection_context
from src.agent.synthesis import synthesize_answer_async
from src.ingestion.chunker import chunk_document
from src.ingestion.entity_extractor import AsyncOpenAIResponsesEntityClient, run_entity_extraction
from src.ingestion.fact_extractor import AsyncOpenAIResponsesFactClient, run_fact_extraction
from src.store import FactStore

LOGGER_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def _snake_case(value: str) -> str:
    lowered = value.lower()
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in lowered)
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "document"


def _load_env() -> None:
    project_root = Path(__file__).resolve().parents[1]
    env_candidates = [
        project_root / ".env.development",
        project_root.parents[0] / ".env.development",
    ]
    for env_file in env_candidates:
        if env_file.exists():
            load_dotenv(env_file, override=True)


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
        if command == "entities":
            self._cmd_entities(args)
            return True
        if command == "projection":
            self._cmd_projection(args)
            return True
        if command == "compact":
            self._cmd_compact(args)
            return True

        print(f"Error: unknown command '{command}'")
        return True

    def _cmd_ingest(self, args: Sequence[str]) -> None:
        run_id = f"ingest-{uuid.uuid4().hex[:10]}"
        started = time.perf_counter()
        parser = argparse.ArgumentParser(prog="ingest", add_help=False)
        parser.add_argument("path")
        parser.add_argument("--layer", required=True, choices=["world", "campaign"])
        parser.add_argument("--campaign")
        parser.add_argument("--source-class")
        parser.add_argument("--title")
        parser.add_argument("--force", action="store_true")
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

        if parsed.layer == "campaign" and not parsed.campaign:
            print("Error: --campaign is required when --layer=campaign")
            self._record_event(
                "ingest_runs",
                {
                    "run_id": run_id,
                    "timestamp": _utc_now_iso(),
                    "status": "error",
                    "error": "missing_campaign_id",
                    "source_path": str(source_path),
                    "layer": parsed.layer,
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

        source_class = parsed.source_class
        if not source_class:
            source_class = "seed_reference" if parsed.layer == "world" else "planning_document"

        title = parsed.title or source_path.stem
        document_id = f"doc_{_snake_case(source_path.stem)}"
        campaign_id = parsed.campaign
        source_fingerprint = _file_sha256(source_path)
        ingest_key = (
            f"{source_fingerprint}|layer={parsed.layer}|campaign={campaign_id}|source_class={source_class}"
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
                    "layer": parsed.layer,
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
                "layer": parsed.layer,
                "campaign_id": campaign_id,
                "source_class": source_class,
                "title": title,
                "document_id": document_id,
                "source_fingerprint": source_fingerprint,
            },
        )

        try:
            t0 = time.perf_counter()
            evidence_units = chunk_document(
                docx_path=source_path,
                document_id=document_id,
                document_title=title,
                canon_layer=parsed.layer,
                campaign_id=campaign_id,
                source_class=source_class,
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

            entity_client = AsyncOpenAIResponsesEntityClient(api_key=api_key)
            t1 = time.perf_counter()
            entities = run_entity_extraction(
                evidence_units,
                known_entities=self.store.list_entities(),
                cache_dir=cache_dir,
                openai_client=entity_client,
                allow_heuristic_fallback=False,
            )
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

            fact_client = AsyncOpenAIResponsesFactClient(api_key=api_key)
            t2 = time.perf_counter()
            facts = run_fact_extraction(
                evidence_units,
                entities=entities,
                canon_layer=parsed.layer,
                campaign_id=campaign_id,
                source_class=source_class,
                cache_dir=cache_dir,
                openai_client=fact_client,
                allow_heuristic_fallback=False,
            )
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
                },
            )
            print(f"  Pass 2 fact extraction... {len(facts)} facts")
            self.logger.info(
                "Ingest run_id=%s stage=fact_extraction facts=%d duration_ms=%d",
                run_id,
                len(facts),
                fact_ms,
            )
            if len(facts) == 0:
                raise RuntimeError("Early exit: fact extraction produced zero facts.")
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

        self.store.add_evidence_units(evidence_units)
        self.store.add_entities(entities)
        self.store.add_facts(facts)
        self.store.record_ingest_fingerprint(
            ingest_key,
            {
                "source_path": str(source_path),
                "layer": parsed.layer,
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
            f"{len(self.store.facts)} facts."
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
                "layer": parsed.layer,
                "campaign_id": campaign_id,
                "source_class": source_class,
                "document_id": document_id,
                "source_fingerprint": source_fingerprint,
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

        projection = self.store.project(parsed.campaign)
        self._record_event(
            "ask_runs",
            {
                "run_id": run_id,
                "timestamp": _utc_now_iso(),
                "status": "started",
                "question": parsed.question,
                "campaign_id": parsed.campaign,
                "projection_metrics": projection.get("metrics", {}),
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
            context = format_projection_context(projection, self.store.list_entities(), parsed.question)
            context_chars = len(context)
            format_ms = int((time.perf_counter() - format_started) * 1000)
            self.logger.info(
                "Ask run_id=%s stage=context_formatter context_chars=%d duration_ms=%d",
                run_id,
                context_chars,
                format_ms,
            )
            model_started = time.perf_counter()
            answer = asyncio.run(synthesize_answer_async(context, parsed.question))
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
            return
        print(answer)
        total_ms = int((time.perf_counter() - started) * 1000)
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
            entity_type = str(entity.get("entity_type", "other"))
            fact_count = counts.get(entity_id, 0)
            print(f"- {display_name} ({entity_type}) [{entity_id}] facts={fact_count}")
        self.logger.info("Entities listed count=%d", len(entities))

    def _cmd_projection(self, args: Sequence[str]) -> None:
        parser = argparse.ArgumentParser(prog="projection", add_help=False)
        parser.add_argument("--campaign")
        parsed = self._safe_parse(parser, args)
        if parsed is None:
            return
        projection = self.store.project(parsed.campaign)
        context = format_projection_context(projection, self.store.list_entities())
        print(context)
        self.logger.info(
            "Projection printed campaign_id=%s projected_entities=%s open_conflicts=%s context_chars=%d",
            parsed.campaign,
            projection.get("metrics", {}).get("projected_entities"),
            projection.get("metrics", {}).get("open_conflicts"),
            len(context),
        )

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


def _build_root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="DungeonMindBuddy CLI")
    parser.add_argument("--store", type=Path, default=Path("./dungeonbuddy_store"))
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
