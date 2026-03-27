"""Phase B gate: evaluate Pass 1 entity extraction recall against Mirathorn gold."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
INPUT_DIR = EVAL_DIR / "input"
GOLD_PATH = EVAL_DIR / "gold" / "gold_entities.json"
OUTPUT_DIR = EVAL_DIR / "output"
REPO_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.chunker import chunk_document  # noqa: E402
from src.ingestion.entity_extractor import OpenAIResponsesEntityClient, run_entity_extraction  # noqa: E402
from src.store import FactStore  # noqa: E402

MIRATHORN_DOCX = Path(
    "/media/drakosfire/Projects/DungeonOverMind/DungeonMindBuddy/Docs/"
    "Eldyrwild and Campaign Context/Elderwyld/Cities and Towns/Mirathorn/"
    "The City of Mirathorn.docx"
)
STRICT_RECALL_THRESHOLD = 0.90
LOOSE_RECALL_THRESHOLD = 0.95
MAX_ENTITIES_PER_UNIT = 1.80


def _load_gold() -> list[dict]:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _has_match_strict(gold_name: str, candidates: set[str]) -> bool:
    return _normalize(gold_name) in candidates


def _has_match_loose(gold_name: str, candidates: set[str]) -> bool:
    needle = _normalize(gold_name)
    if not needle:
        return False
    for candidate in candidates:
        if needle == candidate:
            return True
        # Keep loose mode for diagnostics only.
        if needle in candidate or candidate in needle:
            return True
    return False


def main() -> int:
    env_file = REPO_ROOT / ".env.development"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    if not MIRATHORN_DOCX.exists():
        print(f"ERROR: Mirathorn docx not found: {MIRATHORN_DOCX}")
        return 1
    if not GOLD_PATH.exists():
        print(f"ERROR: Gold entity file missing: {GOLD_PATH}")
        return 1
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is required for strict Phase B gate.")
        return 1

    evidence_units = chunk_document(
        docx_path=MIRATHORN_DOCX,
        document_id="doc_city_of_mirathorn",
        document_title="The City of Mirathorn",
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
    )
    cache_dir = OUTPUT_DIR / "entity_cache"
    client = OpenAIResponsesEntityClient(api_key=api_key)
    model = os.getenv("DMB_ENTITY_MODEL")
    try:
        entities = run_entity_extraction(
            evidence_units,
            model=model,
            cache_dir=cache_dir,
            openai_client=client,
            # Phase B strict gate should validate true extraction path, not regex fallback.
            allow_heuristic_fallback=False,
        )
    except ValueError as exc:
        print("=== ENTITY RECALL EVALUATION (Mirathorn) ===")
        print("FAIL: extraction gate refused heuristic fallback.")
        print(f"Detail: {exc}")
        return 1

    # Exercise persistence/dedup path in the gate, as required by Phase B integration.
    store = FactStore(OUTPUT_DIR / "entity_recall_store")
    store.add_entities(entities)
    extracted = store.list_entities()

    candidate_names: set[str] = set()
    for entity in extracted:
        display = str(entity.get("display_name", "")).strip()
        if display:
            candidate_names.add(_normalize(display))
        for alias in entity.get("aliases", []):
            alias_text = str(alias).strip()
            if alias_text:
                candidate_names.add(_normalize(alias_text))

    gold = _load_gold()
    total = len(gold)
    strict_matched = 0
    loose_matched = 0
    strict_missing: list[str] = []
    loose_missing: list[str] = []
    for item in gold:
        names = [str(item.get("name", "")), *[str(x) for x in item.get("aliases", [])]]
        strict_hit = any(_has_match_strict(name, candidate_names) for name in names)
        loose_hit = any(_has_match_loose(name, candidate_names) for name in names)
        if strict_hit:
            strict_matched += 1
        else:
            strict_missing.append(str(item.get("name", "<unnamed>")))
        if loose_hit:
            loose_matched += 1
        else:
            loose_missing.append(str(item.get("name", "<unnamed>")))

    strict_recall = strict_matched / total if total else 0.0
    loose_recall = loose_matched / total if total else 0.0
    entity_density = (len(extracted) / len(evidence_units)) if evidence_units else 0.0
    passed = (
        strict_recall >= STRICT_RECALL_THRESHOLD
        and loose_recall >= LOOSE_RECALL_THRESHOLD
        and entity_density <= MAX_ENTITIES_PER_UNIT
    )

    print("=== ENTITY RECALL EVALUATION (Mirathorn) ===")
    print(f"Evidence units: {len(evidence_units)}")
    print(f"Extracted entities (deduped): {len(extracted)}")
    print(f"Entities per evidence unit: {entity_density:.3f} (max {MAX_ENTITIES_PER_UNIT:.2f})")
    print(f"Gold entities: {total}")
    print(f"Strict matched: {strict_matched}")
    print(f"Strict recall: {strict_recall:.3f}")
    print(f"Loose matched: {loose_matched}")
    print(f"Loose recall: {loose_recall:.3f}")
    if strict_missing:
        print("Strict missing entities:")
        for name in strict_missing:
            print(f"  - {name}")
    if loose_missing:
        print("Loose missing entities:")
        for name in loose_missing:
            print(f"  - {name}")
    print(
        "PASS "
        f"(strict>={STRICT_RECALL_THRESHOLD:.2f}, "
        f"loose>={LOOSE_RECALL_THRESHOLD:.2f}, "
        f"density<={MAX_ENTITIES_PER_UNIT:.2f}): {passed}"
    )

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
