"""Phase D gate: evaluate synthesis loop (`ingest` -> `ask`) on Mirathorn."""

from __future__ import annotations

import io
import os
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

MIN_EVIDENCE_UNITS = 100
MIN_ENTITIES = 100
MIN_FACTS = 400
MIN_ANSWER_CHARS = 200

ATTRIBUTE_KEYWORDS = ("history", "geography", "demographics", "economy", "defenses")


def _contains_any(haystack: str, needles: tuple[str, ...]) -> bool:
    lowered = haystack.lower()
    return any(needle in lowered for needle in needles)


def _run_ingest(cli: DungeonBuddyCLI) -> tuple[bool, str]:
    cmd = f'ingest "{MIRATHORN_SOURCE}" --layer world --source-class seed_reference'
    capture = io.StringIO()
    with redirect_stdout(capture):
        keep_running = cli.handle_line(cmd)
    return keep_running, capture.getvalue()


def _run_ask(cli: DungeonBuddyCLI, question: str) -> tuple[bool, str]:
    cmd = f'ask "{question}"'
    capture = io.StringIO()
    with redirect_stdout(capture):
        keep_running = cli.handle_line(cmd)
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


def main() -> int:
    env_candidates = [
        REPO_ROOT / ".env.development",
        REPO_ROOT.parent / ".env.development",
    ]
    for env_file in env_candidates:
        if env_file.exists():
            load_dotenv(env_file, override=True)

    if not MIRATHORN_SOURCE.exists():
        print(f"ERROR: Mirathorn source markdown not found: {MIRATHORN_SOURCE}")
        return 1

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is required for Phase D synthesis eval.")
        return 1

    store_dir = OUTPUT_DIR / "phase_d_store"
    cli = DungeonBuddyCLI(store_dir=store_dir, verbose=True)

    _, ingest_output = _run_ingest(cli)
    print("=== INGEST OUTPUT ===")
    print(ingest_output.strip())
    if "Error:" in ingest_output:
        print("EARLY EXIT: ingest command failed.")
        print("\n=== PHASE D RESULT ===")
        print("OVERALL: FAIL")
        return 1

    gate_d1_passed, gate_d1_detail = _gate_d1(cli)
    print(f"D1 Ingest round-trip: {'PASS' if gate_d1_passed else 'FAIL'} ({gate_d1_detail})")
    if not gate_d1_passed:
        print("EARLY EXIT: D1 failed.")
        print("\n=== PHASE D RESULT ===")
        print("OVERALL: FAIL")
        return 1

    projection = cli.store.project(None)
    context = format_projection_context(projection, cli.store.list_entities(), "Catch me up on Mirathorn")
    try:
        answer = synthesize_answer(context, "Catch me up on Mirathorn")
    except Exception as exc:
        print(f"EARLY EXIT: synthesis failed: {exc}")
        print("\n=== PHASE D RESULT ===")
        print("OVERALL: FAIL")
        return 1
    print("\n=== ASK OUTPUT ===")
    print(answer.strip())

    gate_d2_passed, gate_d2_detail = _gate_d2(answer)
    gate_d3_passed, gate_d3_detail = _gate_d3(context)
    gate_d4_passed, gate_d4_detail = _gate_d4(cli, api_key)
    print(f"D2 Grounded prose: {'PASS' if gate_d2_passed else 'FAIL'} ({gate_d2_detail})")
    print(f"D3 Provenance in context: {'PASS' if gate_d3_passed else 'FAIL'} ({gate_d3_detail})")
    print(f"D4 CLI stability: {'PASS' if gate_d4_passed else 'FAIL'} ({gate_d4_detail})")

    all_passed = gate_d1_passed and gate_d2_passed and gate_d3_passed and gate_d4_passed
    print("\n=== PHASE D RESULT ===")
    print(f"OVERALL: {'PASS' if all_passed else 'FAIL'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
