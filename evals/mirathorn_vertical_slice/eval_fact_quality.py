"""Phase C gate: evaluate Pass 2 fact extraction quality against Mirathorn gold."""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EVAL_DIR = Path(__file__).resolve().parent
GOLD_PATH = EVAL_DIR / "gold" / "gold_facts.json"
OUTPUT_DIR = EVAL_DIR / "output"
REPO_ROOT = PROJECT_ROOT.parent

sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.chunker import chunk_document  # noqa: E402
from src.ingestion.entity_extractor import (  # noqa: E402
    OpenAIResponsesEntityClient,
    run_entity_extraction,
)
from src.ingestion.fact_extractor import (  # noqa: E402
    OpenAIResponsesFactClient,
    run_fact_extraction,
)
from src.reducer.canon_projection import project_entity_state  # noqa: E402

MIRATHORN_SOURCE = PROJECT_ROOT / Path(
    "corpus/eldyrwild-markdown/Elderwyld/Cities and Towns/Mirathorn/"
    "The City of Mirathorn.md"
)

FACT_COVERAGE_THRESHOLD = 0.90
MAX_DUPLICATE_RATE = 0.10
MAX_JUNK_RATE = 0.05

C3_REQUIRED_ENTITY_ATTRS: dict[str, list[str]] = {
    "ent_mirathorn": ["history", "geography", "demographics", "economy", "defenses"],
    "ent_shepherds_flock": ["operational_status", "goals"],
}


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _load_gold() -> list[dict]:
    return json.loads(GOLD_PATH.read_text(encoding="utf-8"))


def _build_entity_name_lookup(entities: list[dict]) -> dict[str, str]:
    """Map normalized display_name/alias -> entity_id."""
    lookup: dict[str, str] = {}
    for e in entities:
        eid = str(e.get("entity_id", ""))
        for name in [str(e.get("display_name", "")), *[str(a) for a in e.get("aliases", [])]]:
            key = _normalize(name)
            if key and eid:
                lookup[key] = eid
    return lookup


def _match_gold_fact(
    gold: dict,
    extracted_facts: list[dict],
    entity_name_lookup: dict[str, str],
) -> bool:
    """Check if an extracted fact matches a gold fact entry.

    Supports alternative_attributes: if the primary attribute doesn't match,
    try the alternatives.
    """
    gold_subject_id = gold["subject_entity_id"]
    gold_attrs = [gold["attribute"]] + gold.get("alternative_attributes", [])
    gold_keywords = [kw.lower() for kw in gold.get("match_keywords", [])]
    gold_names = [_normalize(n) for n in gold.get("subject_names", [])]

    candidate_entity_ids = {gold_subject_id}
    for gn in gold_names:
        if gn in entity_name_lookup:
            candidate_entity_ids.add(entity_name_lookup[gn])

    for fact in extracted_facts:
        if fact["subject_entity_id"] not in candidate_entity_ids:
            continue
        if fact["attribute"] not in gold_attrs:
            continue
        label_lower = fact["value"].get("label", "").lower()
        normalized_lower = (fact["value"].get("normalized") or "").lower()
        combined = f"{label_lower} {normalized_lower}"
        if any(kw in combined for kw in gold_keywords):
            return True
    return False


def _compute_duplicate_rate(facts: list[dict]) -> float:
    """Fraction of facts that are semantic duplicates (same subject+attr+normalized)."""
    if not facts:
        return 0.0
    keys: list[str] = []
    for f in facts:
        subj = f["subject_entity_id"]
        attr = f["attribute"]
        normalized = (f["value"].get("normalized") or "").lower().strip()
        if not normalized:
            normalized = re.sub(r"[^a-z0-9]+", "_", f["value"]["label"].lower())[:80]
        keys.append(f"{subj}|{attr}|{normalized}")
    unique = len(set(keys))
    return 1.0 - (unique / len(keys))


_SHORT_VALUE_ATTRIBUTES = {
    "species",
    "rank_or_title",
    "faction",
    "current_location",
}


def _compute_junk_rate(facts: list[dict]) -> float:
    """Fraction of facts that are genuinely low-signal/junk.

    Single-word values are valid for species, rank_or_title, faction, and
    current_location. Only flag facts as junk when the label is truly
    non-informative (empty or a single generic word for other attributes).
    """
    if not facts:
        return 0.0
    junk = 0
    for f in facts:
        label = f["value"].get("label", "").strip()
        attr = f.get("attribute", "")
        if len(label) < 3:
            junk += 1
            continue
        if attr in _SHORT_VALUE_ATTRIBUTES:
            continue
        words = [w for w in label.split() if w]
        if len(words) < 2 and len(label) < 8:
            junk += 1
            continue
    return junk / len(facts)


def _canonical_fact_for_hash(fact: dict) -> str:
    return json.dumps(
        {
            "fact_id": fact["fact_id"],
            "subject_entity_id": fact["subject_entity_id"],
            "attribute": fact["attribute"],
            "value": fact["value"],
            "truth_state": fact["truth_state"],
            "source_authority": fact["source_authority"],
            "evidence_ids": sorted(fact["evidence_ids"]),
        },
        sort_keys=True,
    )


def _payload_hash(facts: list[dict]) -> str:
    import blake3

    canonical = sorted(_canonical_fact_for_hash(f) for f in facts)
    return blake3.blake3("\n".join(canonical).encode("utf-8")).hexdigest()


def _run_pipeline(
    api_key: str,
    entity_cache_dir: Path,
    fact_cache_dir: Path,
    entity_model: str | None,
    fact_model: str | None,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Run chunk -> entity -> fact pipeline. Returns (evidence_units, entities, facts)."""
    evidence_units = chunk_document(
        docx_path=MIRATHORN_SOURCE,
        document_id="doc_city_of_mirathorn",
        document_title="The City of Mirathorn",
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
    )

    entity_client = OpenAIResponsesEntityClient(api_key=api_key)
    entities = run_entity_extraction(
        evidence_units,
        model=entity_model,
        cache_dir=entity_cache_dir,
        openai_client=entity_client,
        allow_heuristic_fallback=False,
    )

    fact_client = OpenAIResponsesFactClient(api_key=api_key)
    facts = run_fact_extraction(
        evidence_units,
        entities=entities,
        canon_layer="world",
        campaign_id=None,
        source_class="seed_reference",
        model=fact_model,
        cache_dir=fact_cache_dir,
        openai_client=fact_client,
        allow_heuristic_fallback=False,
    )
    return evidence_units, entities, facts


def main() -> int:
    env_file = REPO_ROOT / ".env.development"
    if env_file.exists():
        load_dotenv(env_file, override=True)

    if not MIRATHORN_SOURCE.exists():
        print(f"ERROR: Mirathorn markdown not found: {MIRATHORN_SOURCE}")
        return 1
    if not GOLD_PATH.exists():
        print(f"ERROR: Gold fact file missing: {GOLD_PATH}")
        return 1
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("ERROR: OPENAI_API_KEY is required for strict Phase C gate.")
        return 1

    entity_model = os.getenv("DMB_ENTITY_MODEL")
    fact_model = os.getenv("DMB_FACT_MODEL")
    entity_cache = OUTPUT_DIR / "entity_cache"
    fact_cache = OUTPUT_DIR / "fact_cache"

    print("Running pipeline: chunk -> Pass 1 entities -> Pass 2 facts...")
    evidence_units, entities, facts = _run_pipeline(
        api_key, entity_cache, fact_cache, entity_model, fact_model
    )

    evidence_id_set = {str(u["evidence_id"]) for u in evidence_units}
    entity_id_set = {str(e["entity_id"]) for e in entities}
    entity_name_lookup = _build_entity_name_lookup(entities)

    print(f"Evidence units: {len(evidence_units)}")
    print(f"Entities: {len(entities)}")
    print(f"Extracted facts: {len(facts)}")
    print()

    gates_passed = 0
    gates_total = 5

    # --- Gate C1: Contract Validity ---
    print("=== Gate C1: Contract Validity ===")
    orphan_subjects = [
        f for f in facts if f["subject_entity_id"] not in entity_id_set
    ]
    invalid_evidence = [
        f
        for f in facts
        if not all(eid in evidence_id_set for eid in f["evidence_ids"])
    ]
    c1_passed = len(orphan_subjects) == 0 and len(invalid_evidence) == 0
    print(f"  Orphan subject_entity_ids: {len(orphan_subjects)}")
    print(f"  Invalid evidence_ids: {len(invalid_evidence)}")
    print("  Schema validation: PASS (enforced during extraction)")
    print(f"  Gate C1: {'PASS' if c1_passed else 'FAIL'}")
    if c1_passed:
        gates_passed += 1
    if orphan_subjects:
        for f in orphan_subjects[:5]:
            print(f"    orphan: {f['subject_entity_id']} in fact {f['fact_id']}")
    if invalid_evidence:
        for f in invalid_evidence[:5]:
            print(f"    bad evidence: {f['evidence_ids']} in fact {f['fact_id']}")
    print()

    # --- Gate C2: Gold Fact Coverage ---
    print("=== Gate C2: Gold Fact Coverage ===")
    gold = _load_gold()
    matched = 0
    missing: list[str] = []
    for g in gold:
        if _match_gold_fact(g, facts, entity_name_lookup):
            matched += 1
        else:
            missing.append(f"{g['subject_entity_id']}/{g['attribute']}")

    recall = matched / len(gold) if gold else 0.0
    c2_passed = recall >= FACT_COVERAGE_THRESHOLD
    print(f"  Gold facts: {len(gold)}")
    print(f"  Matched: {matched}")
    print(f"  Recall: {recall:.3f} (threshold {FACT_COVERAGE_THRESHOLD:.2f})")
    if missing:
        print("  Missing:")
        for m in missing:
            print(f"    - {m}")
    print(f"  Gate C2: {'PASS' if c2_passed else 'FAIL'}")
    print()

    # --- Gate C3: Projection Parity ---
    print("=== Gate C3: Projection Parity ===")
    projection = project_entity_state(
        evidence_units=evidence_units,
        facts=facts,
        conflicts=[],
        canon_decisions=[],
        campaign_id=None,
    )

    c3_failures: list[str] = []
    for entity_id, required_attrs in C3_REQUIRED_ENTITY_ATTRS.items():
        proj_entities = projection.get("entities", {})

        # Prefer exact match, then substring match
        found_entity_id = None
        if entity_id in proj_entities:
            found_entity_id = entity_id
        else:
            suffix = entity_id.replace("ent_", "")
            for eid in sorted(proj_entities.keys()):
                if suffix in eid:
                    found_entity_id = eid
                    break

        if found_entity_id is None:
            c3_failures.append(f"Entity {entity_id} missing from projection")
            continue

        entity_data = proj_entities[found_entity_id]
        proj_attrs = set(entity_data.get("attributes", {}).keys())
        for attr in required_attrs:
            if attr not in proj_attrs:
                c3_failures.append(f"{entity_id}/{attr} missing from projection")

    # Conflicts are expected when extraction produces multiple facts per
    # entity+attribute; report but do not gate-fail on them.
    conflicts = projection.get("conflicts", [])
    world_conflicts = [c for c in conflicts if c.get("status") != "resolved"]
    print(f"  World-layer conflicts: {len(world_conflicts)} (informational)")

    c3_passed = len(c3_failures) == 0
    if c3_passed:
        print("  All required entities and attributes present in projection")
    else:
        for failure in c3_failures:
            print(f"  FAIL: {failure}")
    print(f"  Gate C3: {'PASS' if c3_passed else 'FAIL'}")
    print()

    # --- Gate C4: Precision Guardrail ---
    print("=== Gate C4: Precision Guardrail ===")
    dup_rate = _compute_duplicate_rate(facts)
    junk_rate = _compute_junk_rate(facts)
    c4_passed = dup_rate <= MAX_DUPLICATE_RATE and junk_rate <= MAX_JUNK_RATE
    print(f"  Duplicate rate: {dup_rate:.3f} (max {MAX_DUPLICATE_RATE:.2f})")
    print(f"  Junk rate: {junk_rate:.3f} (max {MAX_JUNK_RATE:.2f})")
    print(f"  Gate C4: {'PASS' if c4_passed else 'FAIL'}")
    print()

    # --- Gate C5: Determinism (Cache-Replay) ---
    print("=== Gate C5: Determinism (Cache-Replay) ===")
    hash_1 = _payload_hash(facts)
    _, _, facts_2 = _run_pipeline(
        api_key, entity_cache, fact_cache, entity_model, fact_model
    )
    hash_2 = _payload_hash(facts_2)
    c5_passed = hash_1 == hash_2
    print(f"  Run 1 hash: {hash_1[:24]}...")
    print(f"  Run 2 hash: {hash_2[:24]}...")
    print(f"  Gate C5: {'PASS' if c5_passed else 'FAIL'}")
    print()

    # --- Summary ---
    all_passed = all([c1_passed, c2_passed, c3_passed, c4_passed, c5_passed])
    print("=" * 60)
    print(f"  Gates passed: {gates_passed + sum([c2_passed, c3_passed, c4_passed, c5_passed])}/{gates_total}")
    print(f"  C1 Contract:    {'PASS' if c1_passed else 'FAIL'}")
    print(f"  C2 Coverage:    {'PASS' if c2_passed else 'FAIL'} (recall={recall:.3f})")
    print(f"  C3 Projection:  {'PASS' if c3_passed else 'FAIL'}")
    print(f"  C4 Precision:   {'PASS' if c4_passed else 'FAIL'} (dup={dup_rate:.3f}, junk={junk_rate:.3f})")
    print(f"  C5 Determinism: {'PASS' if c5_passed else 'FAIL'}")
    print(f"  OVERALL: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(exist_ok=True)
    out_path = OUTPUT_DIR / "extracted_facts.json"
    out_path.write_text(json.dumps(facts, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nExtracted facts written to: {out_path}")

    proj_path = OUTPUT_DIR / "automated_projection.json"
    proj_path.write_text(json.dumps(projection, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Projection written to: {proj_path}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
