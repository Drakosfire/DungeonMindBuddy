"""Provider-free oracle for the proposed source-statement harness contract.

These envelopes are evaluator inputs, NOT an accepted runtime wire schema.
An owner adapter must supply real captures before this can measure product
behavior. Reviewed expectations are an independent input, not an entailment
oracle: matching them proves contract conformance only.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping


REVIEW_SCHEMA = "buddy_source_statement_review_v1"
CAPTURE_SCHEMA = "buddy_source_statement_capture_v1"
CLAUSE_FIELDS = {
    "world", "campaign", "logical_source", "source_sha256", "start_byte",
    "end_byte", "clause_sha256", "disambiguator",
}
STATEMENT_FIELDS = {
    "clause", "meaning", "episode", "mode", "reporter", "uncertainty",
    "qualifications", "referents", "embedded_content_factive", "assertion_target",
}
CONTEXT_FIELDS = {"world", "campaign", "visibility", "revision", "domain_ref", "profile_ref"}
EDGE_FIELDS = {"edge_id", "statement_id", "entity_id", "predicate", "context"}


def _digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")).hexdigest()


def _fields(value, fields, label):
    if not isinstance(value, Mapping) or set(value) != fields:
        raise ValueError(f"{label}: missing or unknown fields")


def _text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label}: nonblank text required")


def _hash(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError("exact SHA256 required")


def _strings(values, label, *, nonempty=False):
    if not isinstance(values, list) or (nonempty and not values):
        raise ValueError(f"{label}: list required")
    for value in values:
        _text(value, label)
    if len(set(values)) != len(values):
        raise ValueError(f"{label}: duplicate values")


def correspondence_key(clause):
    """Identity depends only on immutable source location, never interpretation.

    SHA fields/byte coordinates must be verified against admitted source bytes
    by the capture adapter. This function cannot certify unavailable bytes.
    """
    _fields(clause, CLAUSE_FIELDS, "clause")
    for key in ("world", "campaign", "logical_source", "disambiguator"):
        _text(clause[key], key)
    for key in ("source_sha256", "clause_sha256"):
        _hash(clause[key])
    start, end = clause["start_byte"], clause["end_byte"]
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        raise ValueError("immutable byte extent required")
    return "source-clause:v1:" + _digest(dict(clause))


def semantic_digest(statement):
    _fields(statement, STATEMENT_FIELDS, "statement")
    correspondence_key(statement["clause"])
    for field in ("meaning", "episode", "mode"):
        _text(statement[field], field)
    if statement["mode"] not in {"narrator", "reported", "uncertain"}:
        raise ValueError("unknown source-statement mode")
    if statement["reporter"] is not None:
        _text(statement["reporter"], "reporter")
    if statement["mode"] == "reported" and statement["reporter"] is None:
        raise ValueError("reported statement requires reporter")
    _strings(statement["uncertainty"], "uncertainty")
    _strings(statement["referents"], "referents", nonempty=True)
    if not isinstance(statement["qualifications"], dict) or not statement["qualifications"]:
        raise ValueError("qualification bundle required")
    if statement["embedded_content_factive"] is not False:
        raise ValueError("embedded content must remain nonfactive")
    if statement["assertion_target"] != "source_statement":
        raise ValueError("assertion target must be source statement")
    return _digest(dict(statement))


def compare_correspondence(original, incoming):
    old_key = correspondence_key(original["clause"])
    new_key = correspondence_key(incoming["clause"])
    old_digest, new_digest = semantic_digest(original), semantic_digest(incoming)
    if old_key != new_key:
        return "distinct_source_clause"
    return "replay" if old_digest == new_digest else "reinterpretation_conflict"


def _context(context):
    _fields(context, CONTEXT_FIELDS, "context")
    for value in context.values():
        _text(value, "exact context reference")


def _statements(rows, context):
    if not isinstance(rows, list):
        raise ValueError("statements must be a list")
    result = {}
    for statement in rows:
        digest = semantic_digest(statement)
        clause = statement["clause"]
        if (clause["world"], clause["campaign"]) != (context["world"], context["campaign"]):
            raise ValueError("statement scope mismatch")
        key = correspondence_key(clause)
        if key in result:
            raise ValueError("duplicate source clause, including episode regrouping")
        result[key] = digest
    return result


def _partial_order(rows, expected):
    """Reject duplicate pairs (even with different support) and cycles."""
    adjacency = {key: set() for key in expected}
    indegree = {key: 0 for key in expected}
    pairs = set()
    for row in rows:
        _fields(row, {"before", "after", "source_support_ref"}, "partial order")
        for value in row.values():
            _text(value, "partial order reference")
        before, after = row["before"], row["after"]
        if before not in expected or after not in expected or before == after:
            raise ValueError("partial order references unknown or identical clauses")
        if (before, after) in pairs:
            raise ValueError("duplicate partial order edge")
        pairs.add((before, after))
        adjacency[before].add(after)
        indegree[after] += 1
    ready = [key for key, degree in indegree.items() if degree == 0]
    visited = 0
    while ready:
        key = ready.pop()
        visited += 1
        for after in adjacency[key]:
            indegree[after] -= 1
            if indegree[after] == 0:
                ready.append(after)
    if visited != len(expected):
        raise ValueError("cyclic partial order")


def evaluate_contract(review, capture):
    """Compare independent reviewed expectations with a captured experiment.

    Invalid oracle input raises; observed counterexamples become failed
    objectives. No providers, persistence, runtime imports or source copies.
    """
    _fields(review, {"schema", "context", "statements", "direct_relations", "order", "original_bindings", "about_edges"}, "review")
    if review["schema"] != REVIEW_SCHEMA:
        raise ValueError("unknown review envelope")
    _context(review["context"])
    expected = _statements(review["statements"], review["context"])
    if not expected:
        raise ValueError("empty review cannot prove contract")
    original_bindings = review["original_bindings"]
    if not isinstance(original_bindings, dict) or set(original_bindings) != set(expected):
        raise ValueError("independently pinned original receipt bindings required")
    for key, binding in original_bindings.items():
        _fields(binding, {"native_id", "semantic_digest", "receipt_id"}, "original binding")
        _text(binding["native_id"], "original native ID")
        _text(binding["receipt_id"], "original receipt ID")
        if binding["semantic_digest"] != expected[key]:
            raise ValueError("original receipt semantic digest differs from review")
    if len({b["native_id"] for b in original_bindings.values()}) != len(expected):
        raise ValueError("original receipt aliases distinct clauses")
    if not isinstance(review["direct_relations"], list) or not isinstance(review["order"], list):
        raise ValueError("review relations/order must be lists")
    # Direct facts are separate reviewed objects; an index or report is not one.
    for relation in review["direct_relations"]:
        _fields(relation, {"subject", "predicate", "object", "independent_review_ref"}, "direct relation")
        for value in relation.values():
            _text(value, "direct relation")
        if relation["predicate"] in {"about", "reported_by"}:
            raise ValueError("index/attribution is not a direct event fact")
    _partial_order(review["order"], expected)
    # These are independently pinned expected index edges, not adapter claims
    # that native authorization was verified. Real adapters must prove that.
    if not isinstance(review["about_edges"], list):
        raise ValueError("reviewed about edges required")
    expected_edges = {}
    by_id = {original_bindings[correspondence_key(s["clause"])]["native_id"]: s
             for s in review["statements"]}
    for edge in review["about_edges"]:
        _fields(edge, EDGE_FIELDS, "reviewed about edge")
        for field in ("edge_id", "statement_id", "entity_id", "predicate"):
            _text(edge[field], field)
        if (edge["predicate"] != "about" or edge["context"] != review["context"]
                or edge["statement_id"] not in by_id
                or edge["entity_id"] not in by_id[edge["statement_id"]]["referents"]):
            raise ValueError("reviewed about edge does not bind reviewed entity and statement")
        if edge["edge_id"] in expected_edges:
            raise ValueError("duplicate reviewed edge ID")
        expected_edges[edge["edge_id"]] = edge

    checks = {}
    details = {}

    def check(name, passed, reason):
        checks[name] = bool(passed)
        if not passed:
            details[name] = reason

    capture_fields = {"schema", "selection_context", "read_context", "selected_keys", "selected_statements",
                      "statements", "direct_relations", "order", "bindings", "discovery", "recovery"}
    if not isinstance(capture, Mapping) or set(capture) != capture_fields:
        raise ValueError("capture: missing or unknown fields")
    check("envelope", capture["schema"] == CAPTURE_SCHEMA, "unknown capture schema")
    check("exact_context", capture["selection_context"] == capture["read_context"] == review["context"],
          "selection/readback context differs from reviewed context")
    try:
        _strings(capture["selected_keys"], "selection", nonempty=True)
        selected = set(capture["selected_keys"])
        selected_bundles = _statements(capture["selected_statements"], review["context"])
        check("actual_selection", selected == set(expected) and selected_bundles == expected,
              "selection missing, extra or changed; complete qualified bundles required")
    except (ValueError, TypeError) as exc:
        selected = set()
        check("actual_selection", False, str(exc))
    try:
        actual = _statements(capture["statements"], review["context"])
        check("atomic_nonfactive_bundles", actual == expected,
              "missing/changed meaning, episode, attribution, uncertainty, qualification or evidence")
    except (ValueError, TypeError) as exc:
        actual = {}
        check("atomic_nonfactive_bundles", False, str(exc))
    check("no_direct_fact_leakage", capture["direct_relations"] == review["direct_relations"],
          "unreviewed direct relation or report/index promoted to event fact")
    check("supported_partial_order", capture["order"] == review["order"],
          "dropped order, invented total order, timestamp or causal connection")

    bindings = capture["bindings"]
    try:
        if not isinstance(bindings, dict) or set(bindings) != set(expected):
            raise ValueError("missing/extra correspondence bindings")
        ids = []
        for key, binding in bindings.items():
            _fields(binding, {"native_id", "semantic_digest", "receipt_id"}, "receipt binding")
            _text(binding["native_id"], "native ID")
            _text(binding["receipt_id"], "receipt ID")
            if binding["semantic_digest"] != expected[key]:
                raise ValueError("semantic digest differs under stable clause key")
            ids.append(binding["native_id"])
        if len(set(ids)) != len(ids):
            raise ValueError("distinct clauses aliased to one native statement")
        check("receipt_correspondence", True, "")
    except (ValueError, TypeError) as exc:
        ids = []
        check("receipt_correspondence", False, str(exc))

    discovery = capture["discovery"]
    try:
        _fields(discovery, {"entity_id", "pages", "expanded_ids", "claims_absence"}, "discovery")
        _text(discovery["entity_id"], "discovery entity")
        relevant = {bindings[k]["native_id"] for k, s in zip(expected, review["statements"])
                    if discovery["entity_id"] in s["referents"]} if checks["receipt_correspondence"] else set()
        if not relevant:
            raise ValueError("discovery needs a reviewed entity with selected statements")
        pages = discovery["pages"]
        if not isinstance(pages, list) or not pages:
            raise ValueError("discovery pages required")
        found, previous, seen_cursors = set(), None, set()
        for page in pages:
            _fields(page, {"context", "entity_id", "cursor", "next_cursor", "has_more", "statement_ids",
                           "predicate", "direction", "hops", "edges"}, "page")
            if (page["predicate"] != "about" or page["direction"] != "incoming"
                    or type(page["hops"]) is not int or page["hops"] != 1):
                raise ValueError("discovery requires one incoming-about hop")
            if page["context"] != review["context"] or page["entity_id"] != discovery["entity_id"]:
                raise ValueError("cross-scope/revision continuation")
            if page["cursor"] != previous or type(page["has_more"]) is not bool:
                raise ValueError("broken continuation chain")
            _strings(page["statement_ids"], "page statements")
            if not isinstance(page["edges"], list):
                raise ValueError("captured incoming edge bindings required")
            page_edge_ids, page_subject_ids = set(), set()
            for edge in page["edges"]:
                _fields(edge, EDGE_FIELDS, "captured about edge")
                _text(edge["edge_id"], "captured edge ID")
                if (edge != expected_edges.get(edge["edge_id"])
                        or edge["entity_id"] != discovery["entity_id"]):
                    raise ValueError("missing/foreign/changed reviewed incoming edge binding")
                if edge["edge_id"] in page_edge_ids:
                    raise ValueError("duplicate edge in one page")
                page_edge_ids.add(edge["edge_id"])
                page_subject_ids.add(edge["statement_id"])
            if page_subject_ids != set(page["statement_ids"]):
                raise ValueError("discovery pointer lacks matching incoming edge binding")
            if not set(page["statement_ids"]) <= relevant:
                raise ValueError("foreign/hidden statement leaked through index")
            found.update(page["statement_ids"])
            previous = page["next_cursor"]
            if page["has_more"]:
                _text(previous, "continuation cursor")
                if previous in seen_cursors:
                    raise ValueError("cyclic continuation")
                seen_cursors.add(previous)
            elif previous is not None or page is not pages[-1]:
                raise ValueError("page after terminal result")
        _strings(discovery["expanded_ids"], "expanded statements")
        if type(discovery["claims_absence"]) is not bool:
            raise ValueError("absence flag must be boolean")
        check("qualified_discovery", set(discovery["expanded_ids"]) == found,
              "index pointer missing ordinary complete subject expansion")
        complete = not pages[-1]["has_more"] and found == relevant
        check("complete_discovery", complete, "explicit partial result; no complete coverage proof")
        check("no_false_absence", not discovery["claims_absence"],
              "selected relevant statements exist; partial/index results cannot establish absence")
    except (ValueError, TypeError, KeyError) as exc:
        for name in ("qualified_discovery", "complete_discovery", "no_false_absence"):
            check(name, False, str(exc))

    recovery = capture["recovery"]
    try:
        _fields(recovery, {"acknowledgment_lost", "original_bindings", "recovered_bindings", "fresh_publications"}, "recovery")
        if type(recovery["acknowledgment_lost"]) is not bool or type(recovery["fresh_publications"]) is not int:
            raise ValueError("recovery flags/count invalid")
        recovered = (recovery["original_bindings"] == recovery["recovered_bindings"] == bindings == original_bindings
                     and recovery["fresh_publications"] == 0)
        check("original_receipt_recovery", recovered,
              "retry must recover original receipt/IDs/digests without fresh publication")
    except (ValueError, TypeError) as exc:
        check("original_receipt_recovery", False, str(exc))

    return {"schema": "buddy_source_statement_contract_result_v1",
            "objectives_met": sum(checks.values()), "objectives_assessed": len(checks),
            "contract_conforms": all(checks.values()), "checks": checks, "counterexamples": details,
            "semantic_entailment_verified": False, "source_bytes_verified": False,
            "runtime_behavior_verified": False, "full_system_ingestion_verified": False,
            "historical_scores_changed": False}
