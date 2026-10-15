"""Validate the source lock and manual claims in Mirathorn query gold v1."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

GOLD_PATH = (
    Path(__file__).resolve().parent
    / "examples/mirathorn_worldbuilding_query_gold_v1/gold.json"
)
REPO_ROOT = Path(__file__).resolve().parents[2]
REQUIRED_EXPECTATIONS = {
    "mirathorn_location_and_trade",
    "council_and_representative_interests",
    "float_goat_transport",
    "festival_of_expansion_purpose",
    "thalia_guard_corruption_continuity",
}
REQUIRED_EXPECTATION_FACTS = {
    "mirathorn_location_and_trade": {
        "mirathorn_location",
        "mirathorn_trade_routes",
    },
    "council_and_representative_interests": {
        "mirathorn_governance",
        "elara_leads_council",
        "barin_commerce_concern",
        "grobnok_cultural_concern",
        "tinkerbright_arcane_concern",
        "thalia_law_order_role",
        "thalia_corruption_stance",
        "torrin_guild_concern",
        "merril_agriculture_concern",
        "rurik_infrastructure_concern",
    },
    "float_goat_transport": {
        "float_goats_water_walking",
        "float_goats_transport_goods",
        "mirathorn_approach_floatgoats",
    },
    "festival_of_expansion_purpose": {
        "festival_expansion_purpose",
        "festival_aspitome_history",
    },
    "thalia_guard_corruption_continuity": {
        "thalia_law_order_role",
        "thalia_corruption_stance",
        "thalia_unaware_enchantment",
    },
}
DISPOSITIONS = {
    "answer",
    "answer_with_scope_note",
    "answer_gm_only",
    "abstain_unsupported",
    "abstain_identity_unresolved",
}


def _check_evidence(
    *,
    records: list[dict[str, Any]],
    source_lines: list[str],
    owner: str,
) -> list[str]:
    errors: list[str] = []
    for index, record in enumerate(records):
        start = record.get("start_line")
        end = record.get("end_line")
        if not isinstance(start, int) or not isinstance(end, int):
            errors.append(f"{owner} evidence {index} must use integer line bounds")
            continue
        if start < 1 or end < start or end > len(source_lines):
            errors.append(f"{owner} evidence {index} has invalid source bounds {start}:{end}")
            continue
        quote = record.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            errors.append(f"{owner} evidence {index} requires a non-empty quote anchor")
            continue
        excerpt = "\n".join(source_lines[start - 1 : end])
        if quote not in excerpt:
            errors.append(f"{owner} evidence {index} quote is absent from lines {start}:{end}")
    return errors


def validate_gold(
    gold_path: Path = GOLD_PATH,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Return deterministic source, schema, and reference validation errors."""
    errors: list[str] = []
    try:
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read gold JSON: {exc}"]

    if gold.get("schema_version") != "dmb_mirathorn_worldbuilding_query_gold_v1":
        errors.append("unsupported schema_version")
    if gold.get("status") != "hand_authored_pre_inference":
        errors.append("gold must remain marked hand_authored_pre_inference")

    corpus = gold.get("corpus")
    if not isinstance(corpus, dict):
        return errors + ["corpus metadata must be an object"]
    try:
        source_bytes = (repo_root / corpus["source_path"]).read_bytes()
        source_text = source_bytes.decode("utf-8")
    except (KeyError, OSError, UnicodeDecodeError) as exc:
        return errors + [f"could not read the declared source bytes: {exc}"]
    actual_source_sha = hashlib.sha256(source_bytes).hexdigest()
    if actual_source_sha != corpus.get("sha256"):
        errors.append("source SHA-256 differs from the pinned saved revision")
    source_lines = source_text.splitlines()

    profile = gold.get("profile_snapshot")
    if not isinstance(profile, dict):
        errors.append("profile_snapshot must be an object")
    else:
        profile_path = profile.get("source_path")
        try:
            profile_bytes = (repo_root / profile_path).read_bytes()
        except (TypeError, OSError) as exc:
            errors.append(f"could not read the pinned profile source: {exc}")
        else:
            if hashlib.sha256(profile_bytes).hexdigest() != profile.get("source_sha256"):
                errors.append("profile source SHA-256 differs from the recorded profile snapshot")

    facts = gold.get("facts")
    questions = gold.get("questions")
    omissions = gold.get("explicit_omissions")
    if not isinstance(facts, list) or not isinstance(questions, list) or not isinstance(omissions, list):
        return errors + ["facts, questions, and explicit_omissions must be arrays"]

    fact_ids = [fact.get("id") for fact in facts if isinstance(fact, dict)]
    if len(fact_ids) != len(facts) or len(fact_ids) != len(set(fact_ids)):
        errors.append("fact records must have unique string ids")
    known_fact_ids = set(fact_ids)

    for fact in facts:
        if not isinstance(fact, dict):
            continue
        if not fact.get("claim") or not fact.get("graph_role"):
            errors.append(f"fact {fact.get('id')} needs a claim and graph_role")
        if not isinstance(fact.get("evidence"), list) or not fact["evidence"]:
            errors.append(f"fact {fact.get('id')} must cite at least one exact source span")
        else:
            errors.extend(
                _check_evidence(
                    records=fact["evidence"],
                    source_lines=source_lines,
                    owner=f"fact {fact.get('id')}",
                )
            )
        if fact.get("profile_fit") not in {
            "in_scope",
            "partial",
            "needs_spoiler_policy",
            "needs_classification_review",
            "excluded_by_current_profile",
        }:
            errors.append(f"fact {fact.get('id')} has no recognized profile_fit disposition")

    question_ids: list[str] = []
    covered_expectations: set[str] = set()
    fact_ids_by_expectation: dict[str, set[str]] = {}
    for question in questions:
        if not isinstance(question, dict):
            errors.append("question records must be objects")
            continue
        question_id = question.get("id")
        question_ids.append(question_id)
        if not question.get("prompt") or not question.get("answer_key"):
            errors.append(f"question {question_id} needs a prompt and answer_key")
        if question.get("expected_disposition") not in DISPOSITIONS:
            errors.append(f"question {question_id} has an unknown expected_disposition")
        refs = question.get("fact_ids")
        if not isinstance(refs, list) or any(ref not in known_fact_ids for ref in refs):
            errors.append(f"question {question_id} references an unknown fact id")
        if question.get("expected_disposition", "").startswith("abstain") and refs:
            errors.append(f"abstention question {question_id} must not require positive fact ids")
        if not question.get("expected_disposition", "").startswith("abstain") and not refs:
            errors.append(f"answerable question {question_id} must reference its gold facts")
        hops = question.get("minimum_relationship_hops", 0)
        path = question.get("required_graph_path", [])
        if hops:
            if not isinstance(hops, int) or hops < 1:
                errors.append(f"question {question_id} has invalid minimum_relationship_hops")
            if not isinstance(path, list) or len(path) < hops + 1:
                errors.append(f"question {question_id} path is shorter than its declared hop minimum")
        covers = question.get("covers_expectations", [])
        if not isinstance(covers, list):
            errors.append(f"question {question_id} covers_expectations must be an array")
        else:
            covered_expectations.update(covers)
            for expectation in covers:
                fact_ids_by_expectation.setdefault(expectation, set()).update(refs or [])
        errors.extend(
            _check_evidence(
                records=question.get("evidence", []),
                source_lines=source_lines,
                owner=f"question {question_id}",
            )
        )

    if len(question_ids) != len(set(question_ids)):
        errors.append("question ids must be unique")

    required = set(gold.get("required_expectations", []))
    if required != REQUIRED_EXPECTATIONS:
        errors.append("required_expectations must equal the frozen five-item goal list")
    missing_coverage = required - covered_expectations
    if missing_coverage:
        errors.append(f"required expectations are not covered by questions: {sorted(missing_coverage)}")
    for expectation, required_fact_ids in REQUIRED_EXPECTATION_FACTS.items():
        missing_facts = required_fact_ids - fact_ids_by_expectation.get(expectation, set())
        if missing_facts:
            errors.append(
                f"expectation {expectation} is missing required gold facts: {sorted(missing_facts)}"
            )

    omission_ids = [item.get("id") for item in omissions if isinstance(item, dict)]
    if len(omission_ids) != len(omissions) or len(omission_ids) != len(set(omission_ids)):
        errors.append("explicit omissions must have unique ids")
    for omission in omissions:
        if not isinstance(omission, dict):
            continue
        bounds = omission.get("lines")
        if (
            not isinstance(bounds, list)
            or len(bounds) != 2
            or not all(isinstance(value, int) for value in bounds)
            or bounds[0] < 1
            or bounds[1] < bounds[0]
            or bounds[1] > len(source_lines)
        ):
            errors.append(f"omission {omission.get('id')} has invalid source line bounds")
        if not omission.get("decision") or not omission.get("profile_behavior"):
            errors.append(f"omission {omission.get('id')} needs a decision and profile_behavior")

    return errors


def main() -> int:
    errors = validate_gold()
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    print(
        "Mirathorn query gold valid: "
        f"{len(gold['facts'])} facts, {len(gold['questions'])} questions, "
        f"{len(gold['explicit_omissions'])} explicit omissions; source and profile hashes match."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
