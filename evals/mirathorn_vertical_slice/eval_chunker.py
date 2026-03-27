"""Phase A gate: evaluate automated chunking against hand-authored Step 1 units."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INPUT_DIR = Path(__file__).resolve().parent / "input"

sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.chunker import chunk_document  # noqa: E402
from src.ingestion.docx_converter import docx_to_markdown  # noqa: E402


MIRATHORN_DOCX = Path(
    "/media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/Docs/"
    "Eldyrwild and Campaign Context/Elderwyld/Cities and Towns/Mirathorn/"
    "The City of Mirathorn.docx"
)


def _load_json(name: str) -> list[dict]:
    return json.loads((INPUT_DIR / name).read_text(encoding="utf-8"))


def _normalize_path(path: list[str]) -> tuple[str, ...]:
    normalized: list[str] = []
    for part in path:
        token = part.strip().lower().rstrip(":")
        if token:
            normalized.append(token)
    return tuple(normalized)


def _tokens(text: str) -> set[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return {tok for tok in cleaned.split() if len(tok) > 2}


def _best_overlap_ratio(hand_text: str, auto_units: list[dict]) -> float:
    hand_tokens = _tokens(hand_text)
    if not hand_tokens:
        return 0.0
    best = 0.0
    for unit in auto_units:
        overlap = len(hand_tokens & _tokens(str(unit["text"])))
        ratio = overlap / len(hand_tokens)
        if ratio > best:
            best = ratio
    return best


def _non_empty_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def main() -> int:
    if not MIRATHORN_DOCX.exists():
        print(f"ERROR: Mirathorn docx not found: {MIRATHORN_DOCX}")
        return 1

    hand_authored = _load_json("evidence_units.json")
    hand_authored = [u for u in hand_authored if u.get("document_id") == "doc_city_of_mirathorn"]

    auto_units = chunk_document(
        docx_path=MIRATHORN_DOCX,
        document_id="doc_city_of_mirathorn",
        document_title="The City of Mirathorn",
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
    )

    hand_paths = {_normalize_path(unit["section_path"]) for unit in hand_authored}
    auto_paths = {_normalize_path(unit["section_path"]) for unit in auto_units}
    missing_paths = sorted(path for path in hand_paths if path not in auto_paths)
    hand_leafs = {path[-1] for path in hand_paths if path}
    auto_components = {part for path in auto_paths for part in path}
    missing_leafs = sorted(leaf for leaf in hand_leafs if leaf not in auto_components)

    overlaps = [(_normalize_path(unit["section_path"]), _best_overlap_ratio(unit["text"], auto_units)) for unit in hand_authored]
    weak_overlaps = [item for item in overlaps if item[1] < 0.45]

    markdown = docx_to_markdown(MIRATHORN_DOCX)
    lines = _non_empty_lines(markdown)
    joined_chunk_text = "\n".join(unit["text"] for unit in auto_units)
    first_line_present = lines[0] in joined_chunk_text if lines else False
    last_line_present = lines[-1] in joined_chunk_text if lines else False

    print("=== CHUNKER EVALUATION (Mirathorn) ===")
    print(f"Hand-authored units: {len(hand_authored)}")
    print(f"Automated units: {len(auto_units)}")
    print(f"Unique hand section paths: {len(hand_paths)}")
    print(f"Unique automated section paths: {len(auto_paths)}")
    print(f"Missing hand paths in automation: {len(missing_paths)}")
    if missing_paths:
        for path in missing_paths:
            print(f"  - {' > '.join(path)}")
    print(f"Missing hand section leafs in automation components: {len(missing_leafs)}")
    if missing_leafs:
        for leaf in missing_leafs:
            print(f"  - {leaf}")

    print("\nHand evidence overlap checks (threshold: 0.45):")
    print(f"  - Weak overlaps: {len(weak_overlaps)}")
    for path, score in weak_overlaps:
        print(f"    {' > '.join(path)} = {score:.3f}")

    print("\nCoverage checks:")
    print(f"  - First non-empty markdown line covered: {first_line_present}")
    print(f"  - Last non-empty markdown line covered: {last_line_present}")

    passed = (
        len(auto_units) > len(hand_authored)
        and len(missing_leafs) <= 2
        and not weak_overlaps
        and first_line_present
        and last_line_present
    )
    print(f"\nPASS: {passed}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
