"""Retain exact source-backed trade access details on a Gazetteer location."""

from __future__ import annotations

import re
from copy import deepcopy
from dataclasses import replace
from typing import Any

from .category_candidate_graph_extractor import materialize_promote_evidence_ref
from .extraction_profile import register_extraction_profile
from .worldbuilding_gazetteer_governance import (
    GAZETTEER_GOVERNANCE_PROFILE,
    _document_city_title,
    _matching_city_nodes,
    _normalized_label,
    _physical_source_lines,
    compile_gazetteer_governance_relations,
)
from .worldbuilding_gazetteer_scenario_scope import _heading, _ordered_rows


PROFILE_VERSION = "1.10"
PROFILE = f"worldbuilding_gazetteer_v1@{PROFILE_VERSION}"
_TRADE_ACCESS = re.compile(
    r"\b(?:[^.!?]*\b(?:trade hub|trading hub|commercial hub|market center)"
    r"[^.!?]*?\baccess\s+to\s+)"
    r"(?P<routes>[^.!?]+)[.!?]",
    re.IGNORECASE,
)


def _trade_section_claims(rows: list[dict[str, Any]]) -> tuple[int, list[dict[str, Any]]]:
    lines = _physical_source_lines(rows)
    sections = [
        index
        for index, row in enumerate(lines)
        if (heading := _heading(row["text"])) is not None
        and heading[0] == 3
        and heading[1].rstrip(":").strip().casefold() == "economy and trade"
    ]
    if len(sections) != 1:
        return len(sections), []

    start = sections[0]
    section_level = 3
    claims = []
    for row in lines[start + 1 :]:
        heading = _heading(row["text"])
        if heading is not None and heading[0] <= section_level:
            break
        for match in _TRADE_ACCESS.finditer(row["text"]):
            claims.append({
                **row,
                "sentence": match.group(0).strip(),
                "routes": match.group("routes").strip(),
            })
    return 1, claims


def _source_binding(node: dict[str, Any]) -> tuple[str, str] | None:
    refs = node.get("evidence_refs")
    if not isinstance(refs, list):
        return None
    bindings = {
        (ref.get("source_artifact_id"), ref.get("source_ref_id"))
        for ref in refs
        if isinstance(ref, dict)
        and ref.get("evidence_role") == "source_evidence"
        and ref.get("can_open_source") is True
        and isinstance(ref.get("source_artifact_id"), str)
        and ref.get("source_artifact_id")
        and isinstance(ref.get("source_ref_id"), str)
        and ref.get("source_ref_id")
    }
    if len(bindings) != 1:
        return None
    artifact_id, source_ref_id = next(iter(bindings))
    return (artifact_id, source_ref_id) if artifact_id and source_ref_id else None


def _attach_trade_evidence(
    node: dict[str, Any], *, source_span_ref_id: str, sentence: str,
    source_artifact_id: str, source_ref_id: str,
) -> str | None:
    refs = node.get("evidence_refs")
    if not isinstance(refs, list):
        return None
    existing = [
        ref for ref in refs
        if isinstance(ref, dict) and ref.get("source_span_ref_id") == source_span_ref_id
    ]
    if len(existing) > 1:
        return None
    if existing:
        ref = existing[0]
        if (
            ref.get("source_artifact_id") != source_artifact_id
            or ref.get("source_ref_id") != source_ref_id
            or ref.get("source_anchor_id") != f"anchor:{source_span_ref_id}"
            or ref.get("evidence_role") != "source_evidence"
            or ref.get("can_open_source") is not True
        ):
            return None
        quotes = ref.get("anchor_quotes")
        if not isinstance(quotes, list):
            return None
        if sentence in quotes:
            return "already_present"
        quotes.append(sentence)
        return "quote_added"

    evidence = materialize_promote_evidence_ref(
        {
            "source_span_ref_id": source_span_ref_id,
            "anchor_quotes": [sentence],
        },
        source_artifact_id=source_artifact_id,
        source_ref_id=source_ref_id,
    )
    if evidence is None or evidence.get("can_open_source") is not True:
        return None
    refs.append(evidence)
    return "attached"


def _apply_trade_context(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result = deepcopy(graph)
    nodes = result.get("nodes")
    if not isinstance(nodes, list) or any(not isinstance(node, dict) for node in nodes):
        raise ValueError("candidate graph nodes must be a list of objects")

    section_count, claims = _trade_section_claims(_ordered_rows(rows))
    if section_count != 1:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "trade_section_not_unique",
            "section_count": section_count,
        }
    if len(claims) != 1:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "trade_access_claim_not_unique",
            "claim_count": len(claims),
        }

    title = _document_city_title(rows)
    if title is None:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "city_title_unresolved",
        }
    city_name, _title_row = title
    locations = _matching_city_nodes(nodes, city_name)
    if len(locations) != 1:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "city_location_not_unique",
            "location_count": len(locations),
        }

    location = locations[0]
    claim = claims[0]
    source_span_ref_id = str(claim.get("source_span_ref_id") or "")
    binding = _source_binding(location)
    if (
        binding is None
        or not source_span_ref_id.startswith(binding[0] + ":span:")
    ):
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "trade_source_binding_unverified",
            "source_span_ref_id": source_span_ref_id,
        }

    if not isinstance(location.get("description"), (str, type(None))):
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "city_description_invalid",
            "source_span_ref_id": source_span_ref_id,
        }

    evidence_status = _attach_trade_evidence(
        location,
        source_span_ref_id=source_span_ref_id,
        sentence=claim["sentence"],
        source_artifact_id=binding[0],
        source_ref_id=binding[1],
    )
    if evidence_status is None:
        return result, {
            "profile": PROFILE,
            "status": "skipped",
            "reason": "trade_evidence_conflict",
            "source_span_ref_id": source_span_ref_id,
        }

    description = str(location.get("description") or "")
    route_text = _normalized_label(claim["routes"])
    description_text = _normalized_label(description)
    description_status = "already_present"
    if route_text not in description_text:
        support_line = f"Trade access: {claim['routes']}."
        location["description"] = f"{description.rstrip()}\n\n{support_line}".strip()
        description_status = "added"

    status = (
        "added"
        if description_status == "added" or evidence_status != "already_present"
        else "already_present"
    )
    return result, {
        "profile": PROFILE,
        "status": status,
        "description_status": description_status,
        "evidence_status": evidence_status,
        "node_id": location.get("node_id"),
        "source_span_ref_id": source_span_ref_id,
        "source_quote": claim["sentence"],
    }


def compile_gazetteer_trade_context(
    graph: dict[str, Any], rows: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any]]:
    result, diagnostics = compile_gazetteer_governance_relations(graph, rows)
    result, trade_diagnostics = _apply_trade_context(result, rows)
    diagnostics["source_grounded_trade_context"] = trade_diagnostics
    return result, diagnostics


GAZETTEER_TRADE_CONTEXT_PROFILE = register_extraction_profile(replace(
    GAZETTEER_GOVERNANCE_PROFILE,
    profile_version=PROFILE_VERSION,
    source_section_retainer=compile_gazetteer_trade_context,
))
