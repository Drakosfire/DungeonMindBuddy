"""Phase D gate: evaluate synthesis loop (`ingest` -> `ask`) on Mirathorn."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import shutil
import sys
from contextlib import redirect_stdout
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EVAL_DIR / "output"
REPO_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(PROJECT_ROOT))

from src.agent.context_formatter import format_projection_context  # noqa: E402
from src.agent.synthesis import synthesize_answer  # noqa: E402
from src.cli import DungeonBuddyCLI  # noqa: E402

MIRATHORN_SOURCE = PROJECT_ROOT / Path(
    "corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/"
    "The City of Mirathorn.md"
)

# D1 floors: benchmark the *interactive CLI ingest* path (chunk → extract → FactStore),
# not the eval_fact_quality direct pipeline. Verified on-disk baselines for
# `corpus/.../The City of Mirathorn.md` as of 2026-04-20 (post temporal-metadata v0.2 corpus):
#   phase_d_store: evidence_units=126, entities=86, facts=293
# eval_fact_quality (`batch_size=1`, no store merge) on the same corpus produced more facts
# (~441 in extracted_facts.json in the same period) — see Backlog for CLI/extractor parity.
# Floors are floor(0.7 × CLI-path baseline) so a ~30% drop fails D1; a ~50% drop still fails.
MIN_EVIDENCE_UNITS = 88  # floor(0.7 * 126)
MIN_ENTITIES = 60  # floor(0.7 * 86); gate uses strict `>`
MIN_FACTS = 205  # floor(0.7 * 293); gate uses strict `>`
MIN_ANSWER_CHARS = 200

ATTRIBUTE_KEYWORDS = ("history", "geography", "demographics", "economy", "defenses")


def _vlog(message: str) -> None:
    """Emit flushed progress logs for long-running Gate 3 runs."""
    print(message, flush=True)


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(needle in lowered for needle in needles)


def _run_ingest(cli: DungeonBuddyCLI, source_path: Path) -> tuple[bool, str]:
    cmd = f'ingest "{source_path}" --layer world --source-class seed_reference'
    _vlog(f"[ingest] command: {cmd}")
    capture = io.StringIO()
    with redirect_stdout(capture):
        keep_running = cli.handle_line(cmd)
    _vlog(f"[ingest] completed keep_running={keep_running}")
    return keep_running, capture.getvalue()


def _run_ask(cli: DungeonBuddyCLI, question: str) -> tuple[bool, str]:
    cmd = f'ask "{question}"'
    _vlog(f"[ask] command: {cmd}")
    capture = io.StringIO()
    with redirect_stdout(capture):
        keep_running = cli.handle_line(cmd)
    _vlog(f"[ask] completed keep_running={keep_running}")
    return keep_running, capture.getvalue()


def _gate_d1(cli: DungeonBuddyCLI) -> tuple[bool, str]:
    passed = (
        len(cli.store.evidence_units) > MIN_EVIDENCE_UNITS
        and len(cli.store.entities) > MIN_ENTITIES
        and len(cli.store.facts) > MIN_FACTS
    )
    detail = (
        f"counts evidence={len(cli.store.evidence_units)} "
        f"entities={len(cli.store.entities)} facts={len(cli.store.facts)}"
    )
    return passed, detail


def _gate_d2(answer_text: str) -> tuple[bool, str]:
    lowered = answer_text.lower()
    mentions_mirathorn = "mirathorn" in lowered
    attributes_hit = sum(1 for keyword in ATTRIBUTE_KEYWORDS if keyword in lowered)
    length_ok = len(answer_text.strip()) > MIN_ANSWER_CHARS
    no_failure_stub = "error:" not in lowered
    passed = mentions_mirathorn and attributes_hit >= 3 and length_ok and no_failure_stub
    detail = (
        f"mentions_mirathorn={mentions_mirathorn} "
        f"attributes_hit={attributes_hit} length={len(answer_text.strip())}"
    )
    return passed, detail


def _gate_d3(context: str) -> tuple[bool, str]:
    has_entity_header = "== Entity:" in context and "(" in context and ")" in context
    has_truth_or_layer = "[CANON" in context or "from: layer=" in context
    has_conflict_annotation = "CONFLICTS:" in context or "competing facts" in context
    passed = has_entity_header and has_truth_or_layer and has_conflict_annotation
    detail = (
        f"entity_header={has_entity_header} "
        f"provenance={has_truth_or_layer} conflicts={has_conflict_annotation}"
    )
    return passed, detail


def _gate_d4(cli: DungeonBuddyCLI, api_key: str) -> tuple[bool, str]:
    sequence_ok = True
    details: list[str] = []
    try:
        for line in (
            "entities",
            "projection",
            'ask "Catch me up on Mirathorn"',
            "quit",
        ):
            keep_running = cli.handle_line(line)
            if line == "quit":
                sequence_ok = sequence_ok and (keep_running is False)
            else:
                sequence_ok = sequence_ok and (keep_running is True)

        missing_file_out = io.StringIO()
        with redirect_stdout(missing_file_out):
            keep_missing_file = cli.handle_line('ingest "does_not_exist.docx" --layer world')
        missing_file_ok = keep_missing_file and "file not found" in missing_file_out.getvalue().lower()
        details.append(f"missing_file={missing_file_ok}")

        os.environ.pop("OPENAI_API_KEY", None)
        missing_key_out = io.StringIO()
        with redirect_stdout(missing_key_out):
            keep_missing_key = cli.handle_line('ask "Can you summarize this?"')
        missing_key_ok = keep_missing_key and "openai_api_key is required" in missing_key_out.getvalue().lower()
        details.append(f"missing_key={missing_key_ok}")
    finally:
        os.environ["OPENAI_API_KEY"] = api_key

    passed = sequence_ok and all("=True" in detail for detail in details)
    return passed, f"sequence_ok={sequence_ok} {' '.join(details)}"


def _artifact_paths() -> dict[str, str]:
    return {
        "context_path": str(OUTPUT_DIR / "phase_d_context.txt"),
        "answer_path": str(OUTPUT_DIR / "phase_d_answer.txt"),
        "summary_path": str(OUTPUT_DIR / "phase_d_summary.json"),
    }


def _print_artifact_locations() -> None:
    artifacts = _artifact_paths()
    print("\n=== PHASE D ARTIFACTS ===")
    print(f"context: {artifacts['context_path']}")
    print(f"answer:  {artifacts['answer_path']}")
    print(f"summary: {artifacts['summary_path']}")


def main(argv: list[str] | None = None) -> int:
    _vlog("=== MIRATHORN GATE 3 (SYNTHESIS) ===")
    _vlog("[1/10] Parsing arguments...")
    parser = argparse.ArgumentParser(description="Phase D synthesis eval runner")
    parser.add_argument(
        "--source",
        type=Path,
        default=MIRATHORN_SOURCE,
        help="Markdown source to ingest for Phase D eval",
    )
    parser.add_argument(
        "--reuse-store",
        action="store_true",
        help="Reuse existing phase_d_store instead of resetting it at startup.",
    )
    args = parser.parse_args(argv)
    source_path = args.source

    _vlog("[2/10] Loading environment candidates...")
    env_candidates = [
        REPO_ROOT / ".env.development",
        REPO_ROOT.parent / ".env.development",
    ]
    for env_file in env_candidates:
        if env_file.exists():
            try:
                load_dotenv(env_file, override=True)
                _vlog(f"  loaded env file: {env_file}")
            except OSError as exc:
                _vlog(f"  WARNING: could not load env file {env_file}: {exc}")
                _vlog("  Continuing with existing process environment.")
        else:
            _vlog(f"  env file missing: {env_file}")

    _vlog("[3/10] Validating source and API key...")
    if not source_path.exists():
        print(f"ERROR: source markdown not found: {source_path}")
        return 1

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is required for Phase D synthesis eval.")
        return 1

    _vlog("[4/10] Initializing CLI and store...")
    store_dir = OUTPUT_DIR / "phase_d_store"
    if store_dir.exists() and not args.reuse_store:
        _vlog(f"  resetting existing store_dir: {store_dir}")
        shutil.rmtree(store_dir)
    elif store_dir.exists() and args.reuse_store:
        _vlog(f"  reusing existing store_dir: {store_dir}")
    cli = DungeonBuddyCLI(store_dir=store_dir, verbose=True)
    _vlog(f"  store_dir: {store_dir}")
    _vlog(f"  source: {source_path}")

    _vlog("[5/10] Running ingest...")
    _, ingest_output = _run_ingest(cli, source_path)
    print("=== INGEST OUTPUT ===")
    print(ingest_output.strip())
    duplicate_ingest = "duplicate ingest detected" in ingest_output.lower()
    if duplicate_ingest:
        _vlog("  duplicate ingest detected; continuing with existing store state.")
    if "Error:" in ingest_output and not duplicate_ingest:
        print("EARLY EXIT: ingest command failed.")
        print("\n=== PHASE D RESULT ===")
        print("OVERALL: FAIL")
        _print_artifact_locations()
        return 1

    _vlog("[6/10] Running D1 ingest-roundtrip gate...")
    gate_d1_passed, gate_d1_detail = _gate_d1(cli)
    print(f"D1 Ingest round-trip: {'PASS' if gate_d1_passed else 'FAIL'} ({gate_d1_detail})")
    if not gate_d1_passed:
        print("EARLY EXIT: D1 failed.")
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        summary = {
            "overall_pass": False,
            "early_exit": "D1",
            "source_path": str(source_path),
            "gates": {
                "D1": {"pass": gate_d1_passed, "detail": gate_d1_detail},
            },
            "artifacts": _artifact_paths(),
        }
        (OUTPUT_DIR / "phase_d_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print("\n=== PHASE D RESULT ===")
        print("OVERALL: FAIL")
        _print_artifact_locations()
        return 1

    _vlog("[7/10] Building projection/context and running synthesis...")
    projection = cli.store.project(None)
    context = format_projection_context(projection, cli.store.list_entities(), "Catch me up on Mirathorn")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "phase_d_context.txt").write_text(context, encoding="utf-8")
    _vlog(f"  context chars: {len(context)}")
    try:
        answer = synthesize_answer(context, "Catch me up on Mirathorn")
    except Exception as exc:
        summary = {
            "overall_pass": False,
            "early_exit": "synthesis",
            "error": str(exc),
            "source_path": str(source_path),
            "gates": {
                "D1": {"pass": gate_d1_passed, "detail": gate_d1_detail},
            },
            "artifacts": _artifact_paths(),
            "context_stats": {
                "chars": len(context),
                "sha256": _sha256_text(context),
            },
        }
        (OUTPUT_DIR / "phase_d_summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        print(f"EARLY EXIT: synthesis failed: {exc}")
        print("\n=== PHASE D RESULT ===")
        print("OVERALL: FAIL")
        _print_artifact_locations()
        return 1
    (OUTPUT_DIR / "phase_d_answer.txt").write_text(answer, encoding="utf-8")
    _vlog(f"  answer chars: {len(answer)}")
    print("\n=== ASK OUTPUT ===")
    print(answer.strip())

    _vlog("[8/10] Evaluating D2/D3/D4 gates...")
    gate_d2_passed, gate_d2_detail = _gate_d2(answer)
    gate_d3_passed, gate_d3_detail = _gate_d3(context)
    gate_d4_passed, gate_d4_detail = _gate_d4(cli, api_key)
    print(f"D2 Grounded prose: {'PASS' if gate_d2_passed else 'FAIL'} ({gate_d2_detail})")
    print(f"D3 Provenance in context: {'PASS' if gate_d3_passed else 'FAIL'} ({gate_d3_detail})")
    print(f"D4 CLI stability: {'PASS' if gate_d4_passed else 'FAIL'} ({gate_d4_detail})")

    all_passed = gate_d1_passed and gate_d2_passed and gate_d3_passed and gate_d4_passed
    summary = {
        "overall_pass": all_passed,
        "source_path": str(source_path),
        "gates": {
            "D1": {"pass": gate_d1_passed, "detail": gate_d1_detail},
            "D2": {"pass": gate_d2_passed, "detail": gate_d2_detail},
            "D3": {"pass": gate_d3_passed, "detail": gate_d3_detail},
            "D4": {"pass": gate_d4_passed, "detail": gate_d4_detail},
        },
        "artifacts": _artifact_paths(),
        "context_stats": {
            "chars": len(context),
            "sha256": _sha256_text(context),
        },
        "answer_stats": {
            "chars": len(answer),
            "sha256": _sha256_text(answer),
        },
    }
    (OUTPUT_DIR / "phase_d_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    _vlog("[9/10] Wrote summary artifact.")
    print("\n=== PHASE D RESULT ===")
    print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")
    _print_artifact_locations()
    _vlog("[10/10] Gate 3 run complete.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
