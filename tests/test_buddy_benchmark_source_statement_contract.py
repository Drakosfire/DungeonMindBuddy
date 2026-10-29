"""Synthetic contract counterexamples; none are current-runtime eval results."""

import copy
import hashlib

import pytest

from evals.buddy_benchmark.source_statement_contract import (
    CAPTURE_SCHEMA, REVIEW_SCHEMA, compare_correspondence, correspondence_key,
    evaluate_contract, semantic_digest,
)


def packet():
    context = dict(world="world:synthetic", campaign="campaign:test", visibility="gm",
                   revision="rev:1", domain_ref="domain:1:exact-digest",
                   profile_ref="profile:1:exact-digest")
    body = "Mara reports that the door may have opened.\nLater the party left."
    version = hashlib.sha256(body.encode()).hexdigest()
    statements = []
    offset = 0
    for index, line in enumerate(body.splitlines(keepends=True)):
        raw = line.encode()
        clause = dict(world=context["world"], campaign=context["campaign"],
                      logical_source="source:synthetic", source_sha256=version,
                      start_byte=offset, end_byte=offset + len(raw),
                      clause_sha256=hashlib.sha256(raw).hexdigest(), disambiguator="exact-clause")
        statements.append(dict(
            clause=clause, meaning=line.strip(), episode=f"episode:{index}",
            mode="reported" if index == 0 else "narrator",
            reporter="person:mara" if index == 0 else None,
            uncertainty=["may have"] if index == 0 else [],
            qualifications={"temporal_bounds": None, "visibility": "gm", "scope": "source statement"},
            referents=["place:door"], embedded_content_factive=False,
            assertion_target="source_statement"))
        offset += len(raw)
    keys = [correspondence_key(s["clause"]) for s in statements]
    bindings = {key: dict(native_id=f"statement:{i}", receipt_id="receipt:original",
                          semantic_digest=semantic_digest(s))
                for i, (key, s) in enumerate(zip(keys, statements))}
    order = [dict(before=keys[0], after=keys[1], source_support_ref="source:explicit-later")]
    relations = [dict(subject="person:mara", predicate="member_of", object="group:party",
                      independent_review_ref="review:separate-membership-fact")]
    review = dict(schema=REVIEW_SCHEMA, context=context, statements=statements,
                  direct_relations=relations, order=order, original_bindings=copy.deepcopy(bindings))
    capture = dict(
        schema=CAPTURE_SCHEMA, selection_context=copy.deepcopy(context),
        read_context=copy.deepcopy(context), selected_keys=keys,
        statements=copy.deepcopy(statements), direct_relations=copy.deepcopy(relations),
        order=copy.deepcopy(order), bindings=copy.deepcopy(bindings),
        discovery=dict(entity_id="place:door", pages=[dict(
            context=copy.deepcopy(context), entity_id="place:door", cursor=None,
            next_cursor=None, has_more=False, statement_ids=["statement:0", "statement:1"])],
            expanded_ids=["statement:0", "statement:1"], claims_absence=False),
        recovery=dict(acknowledgment_lost=True, original_bindings=copy.deepcopy(bindings),
                      recovered_bindings=copy.deepcopy(bindings), fresh_publications=0))
    return review, capture


def test_supported_control_measures_contract_only_and_does_not_mutate_inputs():
    review, capture = packet()
    before = copy.deepcopy((review, capture))
    result = evaluate_contract(review, capture)
    assert result["contract_conforms"]
    assert result["objectives_met"] == result["objectives_assessed"] == 11
    assert not any(result[k] for k in (
        "semantic_entailment_verified", "source_bytes_verified", "runtime_behavior_verified",
        "full_system_ingestion_verified", "historical_scores_changed"))
    assert (review, capture) == before


@pytest.mark.parametrize("field,value", [
    ("episode", None), ("reporter", None), ("uncertainty", []),
    ("qualifications", {}), ("embedded_content_factive", True),
    ("assertion_target", "fictional_event"), ("mode", "narrator"),
    ("meaning", "The door definitely opened because Mara caused it."),
    ("referents", ["person:unreviewed"]),
])
def test_dropped_or_promoted_statement_fields_fail_as_observed_counterexamples(field, value):
    review, capture = packet()
    capture["statements"][0][field] = value
    result = evaluate_contract(review, capture)
    assert not result["checks"]["atomic_nonfactive_bundles"]
    assert not result["contract_conforms"]


@pytest.mark.parametrize("field", ["episode", "reporter", "uncertainty", "qualifications", "clause"])
def test_missing_atomic_field_never_admits_partial_statement(field):
    review, capture = packet()
    del capture["statements"][0][field]
    assert not evaluate_contract(review, capture)["checks"]["atomic_nonfactive_bundles"]


@pytest.mark.parametrize("predicate", ["opened", "caused", "about", "reported_by"])
def test_report_as_fact_or_standalone_index_edge_leakage(predicate):
    review, capture = packet()
    capture["direct_relations"].append(dict(subject="person:mara", predicate=predicate,
                                            object="place:door", independent_review_ref=""))
    assert not evaluate_contract(review, capture)["checks"]["no_direct_fact_leakage"]


@pytest.mark.parametrize("mutation", ["because", "reverse", "total_order", "timestamp", "drop"])
def test_partial_source_order_cannot_become_causality_or_total_chronology(mutation):
    review, capture = packet()
    row = capture["order"][0]
    if mutation == "because":
        row["caused_by"] = row["before"]
    elif mutation == "reverse":
        row["before"], row["after"] = row["after"], row["before"]
    elif mutation == "total_order":
        capture["order"].append(dict(before=row["after"], after=row["before"], source_support_ref="invented"))
    elif mutation == "timestamp":
        row["fictional_timestamp"] = "day 1"
    else:
        capture["order"] = []
    assert not evaluate_contract(review, capture)["checks"]["supported_partial_order"]


@pytest.mark.parametrize("surface", ["selection_context", "read_context", "page"])
@pytest.mark.parametrize("field", ["world", "campaign", "visibility", "revision", "domain_ref", "profile_ref"])
def test_exact_context_is_required_across_selection_discovery_and_expansion(surface, field):
    review, capture = packet()
    context = capture["discovery"]["pages"][0]["context"] if surface == "page" else capture[surface]
    context[field] = "other"
    assert not evaluate_contract(review, capture)["contract_conforms"]


def test_supported_paging_deduplicates_repeated_incoming_edges():
    review, capture = packet()
    first = capture["discovery"]["pages"][0]
    first.update(statement_ids=["statement:0"], has_more=True, next_cursor="cursor:1")
    second = copy.deepcopy(first)
    second.update(cursor="cursor:1", has_more=False, next_cursor=None,
                  statement_ids=["statement:0", "statement:1"])
    capture["discovery"]["pages"].append(second)
    assert evaluate_contract(review, capture)["contract_conforms"]


def test_partial_discovery_stays_partial_without_false_absence():
    review, capture = packet()
    capture["discovery"]["pages"][0].update(
        statement_ids=["statement:0"], has_more=True, next_cursor="cursor:1")
    capture["discovery"]["expanded_ids"] = ["statement:0"]
    result = evaluate_contract(review, capture)
    assert result["checks"]["qualified_discovery"]
    assert result["checks"]["no_false_absence"]
    assert not result["checks"]["complete_discovery"]
    capture["discovery"]["claims_absence"] = True
    assert not evaluate_contract(review, capture)["checks"]["no_false_absence"]


@pytest.mark.parametrize("defect", ["pointer_only", "foreign_id", "hidden_reporter", "wrong_entity", "cursor", "cycle"])
def test_discovery_cannot_substitute_pointers_or_leak_hidden_records(defect):
    review, capture = packet()
    page = capture["discovery"]["pages"][0]
    if defect == "pointer_only":
        capture["discovery"]["expanded_ids"] = []
    elif defect in {"foreign_id", "hidden_reporter"}:
        page["statement_ids"].append("statement:hidden")
    elif defect == "wrong_entity":
        page["entity_id"] = "entity:foreign"
    elif defect == "cursor":
        page["cursor"] = "unrelated-cursor"
    else:
        page.update(has_more=True, next_cursor="cycle")
        second = copy.deepcopy(page)
        second["cursor"] = "cycle"
        capture["discovery"]["pages"].append(second)
    assert not evaluate_contract(review, capture)["contract_conforms"]


@pytest.mark.parametrize("field,value", [
    ("episode", "regrouped"), ("meaning", "A different interpretation"),
    ("reporter", "person:other"), ("uncertainty", ["possibly"]),
    ("qualifications", {"temporal_bounds": "invented"}), ("referents", ["place:other"]),
])
def test_interpretation_changes_keep_correspondence_and_require_conflict(field, value):
    review, _ = packet()
    original = review["statements"][0]
    changed = copy.deepcopy(original)
    changed[field] = value
    assert correspondence_key(original["clause"]) == correspondence_key(changed["clause"])
    assert semantic_digest(original) != semantic_digest(changed)
    assert compare_correspondence(original, changed) == "reinterpretation_conflict"
    assert compare_correspondence(original, copy.deepcopy(original)) == "replay"


def test_episode_regrouping_cannot_smuggle_duplicate_clause_into_review_or_readback():
    review, capture = packet()
    duplicate = copy.deepcopy(review["statements"][0])
    duplicate["episode"] = "another-episode"
    capture["statements"].append(duplicate)
    assert not evaluate_contract(review, capture)["checks"]["atomic_nonfactive_bundles"]
    review["statements"].append(duplicate)
    with pytest.raises(ValueError, match="duplicate source clause"):
        evaluate_contract(review, capture)


def test_identical_repeated_text_at_different_byte_locations_is_distinct():
    review, _ = packet()
    original = review["statements"][0]
    repeated = copy.deepcopy(original)
    repeated["clause"]["start_byte"] += 100
    repeated["clause"]["end_byte"] += 100
    assert compare_correspondence(original, repeated) == "distinct_source_clause"


@pytest.mark.parametrize("field,value", [("start_byte", True), ("end_byte", 0),
                                        ("source_sha256", "opaque-revision"), ("episode", "evade")])
def test_clause_identity_rejects_invalid_coordinates_or_interpretive_fields(field, value):
    review, _ = packet()
    clause = copy.deepcopy(review["statements"][0]["clause"])
    clause[field] = value
    with pytest.raises(ValueError):
        correspondence_key(clause)


@pytest.mark.parametrize("defect", ["new_id", "new_receipt", "fresh_publication", "semantic_change", "missing_mapping"])
def test_lost_acknowledgment_requires_original_receipt_mapping(defect):
    review, capture = packet()
    recovery = capture["recovery"]
    key = capture["selected_keys"][0]
    if defect == "new_id":
        recovery["recovered_bindings"][key]["native_id"] = "statement:new"
    elif defect == "new_receipt":
        recovery["recovered_bindings"][key]["receipt_id"] = "receipt:new"
    elif defect == "fresh_publication":
        recovery["fresh_publications"] = 1
    elif defect == "semantic_change":
        recovery["recovered_bindings"][key]["semantic_digest"] = "new"
    else:
        del recovery["recovered_bindings"][key]
    assert not evaluate_contract(review, capture)["checks"]["original_receipt_recovery"]


def test_changed_meaning_cannot_reseal_new_digest_under_old_review():
    review, capture = packet()
    capture["statements"][0]["episode"] = "regrouped"
    key = capture["selected_keys"][0]
    capture["bindings"][key]["semantic_digest"] = semantic_digest(capture["statements"][0])
    result = evaluate_contract(review, capture)
    assert not result["checks"]["atomic_nonfactive_bundles"]
    assert not result["checks"]["receipt_correspondence"]


def test_self_consistent_fresh_ids_cannot_replace_independently_pinned_receipt():
    review, capture = packet()
    key = capture["selected_keys"][0]
    for mapping in (capture["bindings"], capture["recovery"]["original_bindings"],
                    capture["recovery"]["recovered_bindings"]):
        mapping[key].update(native_id="statement:fresh", receipt_id="receipt:fresh")
    capture["discovery"]["pages"][0]["statement_ids"][0] = "statement:fresh"
    capture["discovery"]["expanded_ids"][0] = "statement:fresh"
    result = evaluate_contract(review, capture)
    assert not result["checks"]["original_receipt_recovery"]
    assert not result["contract_conforms"]


def test_empty_or_incomplete_review_is_not_an_oracle():
    review, capture = packet()
    review["statements"] = []
    with pytest.raises(ValueError, match="empty review"):
        evaluate_contract(review, capture)


def test_explicit_empty_selection_is_not_defaults():
    review, capture = packet()
    capture["selected_keys"] = []
    assert not evaluate_contract(review, capture)["checks"]["actual_selection"]
