"""Validate source locks, answer dependencies, graph walks, and visibility in Mirathorn gold."""

from __future__ import annotations

import ast
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
    "mirathorn_location_and_trade": {"mirathorn_location", "mirathorn_trade_routes"},
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
    "festival_of_expansion_purpose": {"festival_expansion_purpose", "festival_aspitome_history"},
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
    "answer_player_safe",
    "abstain_unsupported",
    "abstain_identity_unresolved",
}
PROFILE_FITS = {
    "in_scope",
    "partial",
    "outside_selected_pilot_scope",
    "in_scope_with_visibility_gate",
    "prepared_scenario_only",
}
GRAPH_STATUSES = {
    "required_supported_path",
    "optional_supported_edges",
    "not_required",
    "profile_dependent",
    "not_applicable",
}
TASK_SHAPES = {
    "single_source_facts",
    "multi_source_synthesis",
    "supported_graph_path_plus_multi_source_synthesis",
    "multi_fact_gm_synthesis",
    "gm_sensitive_fact",
    "player_safe_fact",
    "abstention_control",
}


def _read_sha256(path: Path) -> tuple[bytes | None, str | None]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        return None, str(exc)
    return payload, hashlib.sha256(payload).hexdigest()


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


def _native_predicates(source_text: str) -> set[str]:
    """Read the literal native predicate map without importing application code."""
    tree = ast.parse(source_text)
    for statement in tree.body:
        if not isinstance(statement, ast.AnnAssign):
            continue
        if isinstance(statement.target, ast.Name) and statement.target.id == "PREDICATE_FAMILY":
            mapping = ast.literal_eval(statement.value)
            if isinstance(mapping, dict) and all(isinstance(key, str) for key in mapping):
                return set(mapping)
    raise ValueError("could not find literal PREDICATE_FAMILY mapping")


def _check_node_selector(value: Any, *, allowed_node_types: set[str], owner: str) -> list[str]:
    errors: list[str] = []
    if not isinstance(value, dict) or not value.get("label") or not value.get("node_type"):
        return [f"{owner} must specify a node label and type"]
    if value.get("node_type") not in allowed_node_types:
        errors.append(f"{owner} node type {value.get('node_type')!r} is outside the selected baseline")
    return errors


def _check_graph_paths(
    *,
    question: dict[str, Any],
    known_fact_ids: set[str],
    allowed_node_types: set[str],
    native_predicates: set[str],
    pinned_predicates: set[str],
) -> list[str]:
    errors: list[str] = []
    question_id = question.get("id")
    traversal = question.get("graph_traversal")
    if not isinstance(traversal, dict):
        return [f"question {question_id} needs graph_traversal metadata"]
    status = traversal.get("status")
    paths = traversal.get("paths")
    if status not in GRAPH_STATUSES:
        errors.append(f"question {question_id} has an unknown graph_traversal status")
    if not isinstance(paths, list):
        return errors + [f"question {question_id} graph_traversal.paths must be an array"]

    if status == "required_supported_path" and not paths:
        errors.append(f"question {question_id} requires at least one supported graph path")
    if status in {"not_required", "profile_dependent", "not_applicable"} and paths:
        errors.append(f"question {question_id} cannot claim paths for status {status}")
    if status == "optional_supported_edges" and not paths:
        errors.append(f"question {question_id} must list its optional supported edges")

    question_fact_ids = set(question.get("fact_ids") or [])
    for path_index, path in enumerate(paths):
        owner = f"question {question_id} path {path_index}"
        if not isinstance(path, dict):
            errors.append(f"{owner} must be an object")
            continue
        start = path.get("start")
        target = path.get("target")
        errors.extend(_check_node_selector(start, allowed_node_types=allowed_node_types, owner=f"{owner} start"))
        errors.extend(_check_node_selector(target, allowed_node_types=allowed_node_types, owner=f"{owner} target"))
        direction = path.get("direction")
        if direction != "forward":
            errors.append(f"{owner} must encode edges in forward direction")
        steps = path.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{owner} needs one or more explicit edge steps")
            continue
        minimum_steps = 2 if status == "required_supported_path" else 1
        if len(steps) < minimum_steps:
            errors.append(f"{owner} has fewer than {minimum_steps} required edge steps")

        current = start
        for step_index, step in enumerate(steps):
            step_owner = f"{owner} step {step_index}"
            if not isinstance(step, dict):
                errors.append(f"{step_owner} must be an object")
                continue
            edge_from = step.get("from")
            edge_to = step.get("to")
            errors.extend(_check_node_selector(edge_from, allowed_node_types=allowed_node_types, owner=f"{step_owner} from"))
            errors.extend(_check_node_selector(edge_to, allowed_node_types=allowed_node_types, owner=f"{step_owner} to"))
            if current != edge_from:
                errors.append(f"{step_owner} is not edge-contiguous with the previous path node")
            current = edge_to
            predicate = step.get("predicate")
            if predicate not in native_predicates or predicate not in pinned_predicates:
                errors.append(f"{step_owner} predicate {predicate!r} is not in the pinned native vocabulary")
            evidence_ids = step.get("evidence_fact_ids")
            if (
                not isinstance(evidence_ids, list)
                or not evidence_ids
                or any(fact_id not in known_fact_ids for fact_id in evidence_ids)
            ):
                errors.append(f"{step_owner} must cite known evidence fact ids")
            elif any(fact_id not in question_fact_ids for fact_id in evidence_ids):
                errors.append(f"{step_owner} evidence facts must be dependencies of its question")
        if current != target:
            errors.append(f"{owner} target does not match the final edge endpoint")

    aggregate_ids = traversal.get("aggregated_fact_ids", [])
    if not isinstance(aggregate_ids, list) or any(fact_id not in known_fact_ids for fact_id in aggregate_ids):
        errors.append(f"question {question_id} has unknown aggregated fact ids")
    elif any(fact_id not in question_fact_ids for fact_id in aggregate_ids):
        errors.append(f"question {question_id} aggregates facts outside its answer dependencies")
    if status == "required_supported_path" and not traversal.get("forbidden_inferences"):
        errors.append(f"question {question_id} must record path-related forbidden inferences")
    if status in {"not_required", "profile_dependent", "not_applicable"} and not traversal.get("note"):
        errors.append(f"question {question_id} must explain why no graph path is claimed")
    return errors


def validate_gold(
    gold_path: Path = GOLD_PATH,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Return source, profile, graph-path, and visibility validation errors."""
    errors: list[str] = []
    try:
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return [f"could not read gold JSON: {exc}"]

    if gold.get("schema_version") != "dmb_mirathorn_worldbuilding_query_gold_v1":
        errors.append("unsupported schema_version")
    if gold.get("status") != "hand_authored_before_target_run_development_not_blind":
        errors.append("gold must state that it is development gold before the target run, not a blind holdout")
    methodology = gold.get("methodology")
    if not isinstance(methodology, dict) or methodology.get("study_design") != "development_not_blind":
        errors.append("methodology must identify development, non-blind study design")
    elif methodology.get("authored_before_target_run") is not True or not methodology.get("prior_related_work_reviewed"):
        errors.append("methodology must scope timing and acknowledge prior related work")

    corpus = gold.get("corpus")
    if not isinstance(corpus, dict):
        return errors + ["corpus metadata must be an object"]
    source_bytes, actual_source_sha = _read_sha256(repo_root / corpus.get("source_path", ""))
    if source_bytes is None:
        return errors + [f"could not read the declared source bytes: {actual_source_sha}"]
    if actual_source_sha != corpus.get("sha256"):
        errors.append("source SHA-256 differs from the pinned saved revision")
    try:
        source_lines = source_bytes.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        return errors + [f"declared source is not UTF-8: {exc}"]

    profile = gold.get("profile_snapshot")
    if not isinstance(profile, dict):
        return errors + ["profile_snapshot must be an object"]
    if profile.get("snapshot_role") != "selected_pilot_profile_baseline_not_execution_evidence":
        errors.append("profile snapshot must distinguish pilot baseline from executed profile")
    if profile.get("execution_profile") != "unverified" or profile.get("runtime_document_class") != "unverified":
        errors.append("this gold cannot claim an execution profile or registered document class")
    profile_paths = [
        {"source_path": profile.get("source_path"), "source_sha256": profile.get("source_sha256")},
        profile.get("profile_catalog", {}),
        *(profile.get("available_profiles") or []),
    ]
    for snapshot in profile_paths:
        if not isinstance(snapshot, dict):
            errors.append("profile source snapshots must be objects")
            continue
        path = snapshot.get("source_path")
        expected_sha = snapshot.get("source_sha256")
        if not isinstance(path, str) or not isinstance(expected_sha, str):
            errors.append("profile source snapshot requires path and SHA-256")
            continue
        payload, actual_sha = _read_sha256(repo_root / path)
        if payload is None:
            errors.append(f"could not read pinned profile source {path}: {actual_sha}")
        elif actual_sha != expected_sha:
            errors.append(f"profile source SHA-256 differs for {path}")
    available_profile_ids = {
        item.get("id") for item in profile.get("available_profiles", []) if isinstance(item, dict)
    }
    if "worldbuilding_gazetteer_v1@1.5" not in available_profile_ids:
        errors.append("profile snapshot must acknowledge available Gazetteer v1.5")

    graph_contract = gold.get("graph_contract_snapshot")
    if not isinstance(graph_contract, dict):
        return errors + ["graph_contract_snapshot must be an object"]
    predicate_source_path = graph_contract.get("source_path")
    predicate_source_sha = graph_contract.get("source_sha256")
    predicate_bytes, actual_predicate_sha = _read_sha256(repo_root / str(predicate_source_path or ""))
    native_predicates: set[str] = set()
    if predicate_bytes is None:
        errors.append(f"could not read pinned predicate source: {actual_predicate_sha}")
    elif actual_predicate_sha != predicate_source_sha:
        errors.append("predicate source SHA-256 differs from the pinned graph contract")
    else:
        try:
            native_predicates = _native_predicates(predicate_bytes.decode("utf-8"))
        except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
            errors.append(f"could not read native predicate vocabulary: {exc}")
    pinned_predicates = graph_contract.get("legal_predicates_used")
    if (
        not isinstance(pinned_predicates, list)
        or len(pinned_predicates) != len(set(pinned_predicates))
        or any(predicate not in native_predicates for predicate in pinned_predicates)
    ):
        errors.append("legal_predicates_used must be unique members of the pinned native vocabulary")
        pinned_predicates = []
    pinned_predicate_set = set(pinned_predicates)

    facts = gold.get("facts")
    questions = gold.get("questions")
    omissions = gold.get("explicit_omissions")
    if not isinstance(facts, list) or not isinstance(questions, list) or not isinstance(omissions, list):
        return errors + ["facts, questions, and explicit_omissions must be arrays"]
    fact_ids = [fact.get("id") for fact in facts if isinstance(fact, dict)]
    if len(fact_ids) != len(facts) or len(fact_ids) != len(set(fact_ids)) or any(not isinstance(item, str) for item in fact_ids):
        errors.append("fact records must have unique string ids")
    known_fact_ids = set(fact_ids)
    hidden_fact_ids: set[str] = set()
    for fact in facts:
        if not isinstance(fact, dict):
            continue
        fact_id = fact.get("id")
        if not fact.get("claim") or not fact.get("fact_role"):
            errors.append(f"fact {fact_id} needs a claim and fact_role")
        evidence = fact.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"fact {fact_id} must cite at least one exact source span")
        else:
            errors.extend(_check_evidence(records=evidence, source_lines=source_lines, owner=f"fact {fact_id}"))
        if fact.get("profile_fit") not in PROFILE_FITS:
            errors.append(f"fact {fact_id} has no recognized selected-profile disposition")
        representation = fact.get("representation_expectation")
        if not isinstance(representation, dict) or not representation.get("mode") or not representation.get("note"):
            errors.append(f"fact {fact_id} needs a representation expectation and note")
        elif not isinstance(representation.get("typed_node_required_for_answer"), bool):
            errors.append(f"fact {fact_id} must state whether a typed node is required for answer correctness")
        elif fact.get("profile_fit") in {"outside_selected_pilot_scope", "prepared_scenario_only"} and representation["typed_node_required_for_answer"]:
            errors.append(f"fact {fact_id} cannot require an out-of-profile typed node to answer")
        if fact.get("visibility") == "gm_spoiler_sensitive":
            hidden_fact_ids.add(fact_id)

    baseline_node_types = set(profile.get("admitted_node_types") or [])
    question_ids: list[str] = []
    covered_expectations: set[str] = set()
    fact_ids_by_expectation: dict[str, set[str]] = {}
    multi_source_count = 0
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
            refs = []
        if len(refs) != len(set(refs)):
            errors.append(f"question {question_id} has duplicate fact dependencies")
        disposition = question.get("expected_disposition")
        if str(disposition).startswith("abstain") and refs:
            errors.append(f"abstention question {question_id} must not require positive fact ids")
        if not str(disposition).startswith("abstain") and not refs:
            errors.append(f"answerable question {question_id} must reference its gold facts")
        if "minimum_relationship_hops" in question or "required_graph_path" in question:
            errors.append(f"question {question_id} must not count descriptive phrases as graph hops")
        task_shape = question.get("task_shape")
        if task_shape not in TASK_SHAPES:
            errors.append(f"question {question_id} has an unknown task_shape")
        if task_shape in {"multi_source_synthesis", "supported_graph_path_plus_multi_source_synthesis"}:
            multi_source_count += 1
            if len(refs) < 2:
                errors.append(f"multi-source question {question_id} must depend on multiple gold facts")
        if question.get("audience") not in {"gm", "player"}:
            errors.append(f"question {question_id} must declare a GM or player audience")
        must_not_disclose = question.get("must_not_disclose_fact_ids")
        if not isinstance(must_not_disclose, list) or any(item not in known_fact_ids for item in must_not_disclose):
            errors.append(f"question {question_id} has invalid must_not_disclose_fact_ids")
            must_not_disclose = []
        hidden_refs = set(refs) & hidden_fact_ids
        if question.get("audience") == "player":
            if hidden_refs:
                errors.append(f"player question {question_id} depends on GM-only facts")
            if not hidden_fact_ids.issubset(set(must_not_disclose)):
                errors.append(f"player question {question_id} must explicitly exclude every hidden fact")
        if disposition == "answer_gm_only" and (question.get("audience") != "gm" or not hidden_refs):
            errors.append(f"GM-only answer {question_id} must be GM-scoped and depend on a hidden fact")
        if disposition == "answer_player_safe" and question.get("audience") != "player":
            errors.append(f"player-safe answer {question_id} must have player audience")
        if hidden_refs and question.get("audience") != "gm":
            errors.append(f"question {question_id} exposes a hidden fact outside the GM audience")

        errors.extend(_check_graph_paths(
            question=question,
            known_fact_ids=known_fact_ids,
            allowed_node_types=baseline_node_types,
            native_predicates=native_predicates,
            pinned_predicates=pinned_predicate_set,
        ))
        covers = question.get("covers_expectations", [])
        if not isinstance(covers, list):
            errors.append(f"question {question_id} covers_expectations must be an array")
        else:
            covered_expectations.update(covers)
            for expectation in covers:
                fact_ids_by_expectation.setdefault(expectation, set()).update(refs)
        errors.extend(_check_evidence(
            records=question.get("evidence", []),
            source_lines=source_lines,
            owner=f"question {question_id}",
        ))

    if len(question_ids) != len(set(question_ids)):
        errors.append("question ids must be unique")
    if multi_source_count < 2:
        errors.append("gold must include at least two multi-source question forms")

    required = set(gold.get("required_expectations", []))
    if required != REQUIRED_EXPECTATIONS:
        errors.append("required_expectations must equal the frozen five-item goal list")
    missing_coverage = required - covered_expectations
    if missing_coverage:
        errors.append(f"required expectations are not covered by questions: {sorted(missing_coverage)}")
    for expectation, required_fact_ids in REQUIRED_EXPECTATION_FACTS.items():
        missing_facts = required_fact_ids - fact_ids_by_expectation.get(expectation, set())
        if missing_facts:
            errors.append(f"expectation {expectation} is missing required gold facts: {sorted(missing_facts)}")

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
        f"{len(gold['explicit_omissions'])} explicit omissions; source, profiles, predicates, paths, and visibility match."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
