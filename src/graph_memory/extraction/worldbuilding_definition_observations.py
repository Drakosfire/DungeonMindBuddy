"""Versioned source-exact definition observations on an existing place candidate."""

from copy import deepcopy
from dataclasses import replace

from .extraction_profile import register_extraction_profile
from .worldbuilding_gazetteer_trade_context import (
    GAZETTEER_TRADE_CONTEXT_PROFILE,
    compile_gazetteer_trade_context,
)
from .worldbuilding_source_sections import (
    SourceSectionRetentionError,
    owned_livestock_definitions,
    owned_livestock_sections,
)

PROFILE = "worldbuilding_gazetteer_v1@1.11"


def compile_definition_observations(graph, rows):
    result, diagnostics = compile_gazetteer_trade_context(graph, rows)
    definitions = owned_livestock_definitions(rows)
    observations = []
    for section in owned_livestock_sections(rows):
        owner = section["owner_label"].casefold()
        places = [
            node
            for node in result.get("nodes", [])
            if node.get("node_type") == "location"
            and str(node.get("label", "")).removeprefix("The ").casefold() == owner
        ]
        if len(places) != 1:
            raise SourceSectionRetentionError(
                "definition owner is not a unique place candidate"
            )
        place = places[0]
        refs = set(section["source_span_ref_ids"])
        evidence_rows = [row for row in rows if row["source_span_ref_id"] in refs]
        prose = "\n\n".join(row["text"] for row in evidence_rows)
        description = str(place.get("description") or "")
        if description.count(prose) != 1:
            raise SourceSectionRetentionError(
                "retained definition bundle is not uniquely identifiable"
            )
        place["description"] = description.replace(prose, "", 1).strip()
        # The owner heading remains identity context. Definition evidence belongs
        # to its independent review record, not to an enlarged place observation.
        place["evidence_refs"] = [
            ref
            for ref in place.get("evidence_refs", [])
            if ref.get("source_span_ref_id") not in refs
            or ref.get("source_span_ref_id") == section["owner_span_ref_id"]
        ]
        for definition in definitions:
            if definition["owner_span_ref_id"] != section["owner_span_ref_id"]:
                continue
            selected = set(definition["source_span_ref_ids"])
            observations.append(
                {
                    "observation_id": definition["definition_id"],
                    "subject_candidate_node_id": place["node_id"],
                    "title": definition["title"],
                    "description": definition["description"],
                    "semantic_state": deepcopy(place["semantic_state"]),
                    "evidence_refs": [
                        {
                            "source_span_ref_id": row["source_span_ref_id"],
                            "anchor_quotes": [row["text"]],
                        }
                        for row in rows
                        if row["source_span_ref_id"] in selected
                    ],
                    "confidence": place["confidence"],
                    "warnings": list(place.get("warnings", [])),
                    "proposed_action": "create",
                }
            )
    previous = graph.get("source_observations")
    if previous is not None and previous != observations:
        raise SourceSectionRetentionError(
            "preexisting source observations conflict with exact definitions"
        )
    result["version"] = "0.2"
    result["source_observations"] = observations
    diagnostics["source_definition_observations"] = {
        "profile": PROFILE,
        "count": len(observations),
        "source_qualification_preserved": True,
    }
    return result, diagnostics


def validate_definition_candidate(graph):
    errors = list(GAZETTEER_TRADE_CONTEXT_PROFILE.post_extraction_validator(graph))
    if graph.get("version") != "0.2" or not isinstance(
        graph.get("source_observations"), list
    ):
        errors.append(
            "definition observations require candidate v0.2 and explicit observation records"
        )
        return errors
    places = {
        n.get("node_id")
        for n in graph.get("nodes", [])
        if n.get("node_type") == "location"
    }
    if any(
        o.get("subject_candidate_node_id") not in places
        for o in graph["source_observations"]
    ):
        errors.append("definition observation subject must be its place candidate")
    return errors


GAZETTEER_DEFINITION_OBSERVATION_PROFILE = register_extraction_profile(
    replace(
        GAZETTEER_TRADE_CONTEXT_PROFILE,
        profile_version="1.11",
        source_section_retainer=compile_definition_observations,
        post_extraction_validator=validate_definition_candidate,
    )
)
