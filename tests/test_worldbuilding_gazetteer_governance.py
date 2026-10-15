from __future__ import annotations

from copy import deepcopy

import pytest

from src.graph_memory.extraction.worldbuilding_gazetteer_governance import (
    GAZETTEER_GOVERNANCE_PROFILE,
    PROFILE,
    _apply_governance_relation,
    compile_gazetteer_governance_relations,
)
from src.graph_memory.extraction.worldbuilding_profile_catalog import (
    PUBLISHABLE_WORLDBUILDING_PROFILES,
)


def _rows(*texts: str) -> list[dict[str, object]]:
    return [
        {
            "source_span_ref_id": f"span:{line}",
            "line_start": line,
            "line_end": line,
            "text": text,
        }
        for line, text in enumerate(texts, 1)
    ]


def _source_ref(row: dict[str, object]) -> dict[str, object]:
    span_ref = row["source_span_ref_id"]
    return {
        "source_span_ref_id": span_ref,
        "anchor_quotes": [row["text"]],
        "source_artifact_id": "artifact:mirathorn:r2",
        "source_ref_id": "artifact:mirathorn:r2:text",
        "source_anchor_id": f"anchor:{span_ref}",
        "label": span_ref,
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
    }


def _graph(rows: list[dict[str, object]]) -> dict[str, object]:
    evidence = _source_ref(rows[4])
    semantic_state = {
        "authority_state": "system_derived",
        "canon_state": "worldbuilding_draft",
        "evidence_role": "source_evidence",
        "lifecycle_state": "candidate",
        "visibility_state": "gm_private",
    }
    return {
        "nodes": [
            {
                "node_id": "loc_mirathorn",
                "label": "Mirathorn",
                "node_type": "location",
                "semantic_state": deepcopy(semantic_state),
                "evidence_refs": [deepcopy(evidence)],
            },
            {
                "node_id": "org_mirathorn_city_council",
                "label": "Mirathorn City Council",
                "node_type": "organization",
                "semantic_state": deepcopy(semantic_state),
                "evidence_refs": [deepcopy(evidence)],
            },
        ],
        "edges": [],
    }


def test_build_profile_adds_source_backed_governance_relation_idempotently():
    rows = _rows(
        "# The City of Mirathorn",
        "## Location",
        "Mirathorn stands at a trade crossing.",
        "### Governance:",
        "A democratic city-state governed by a council representing various races and guilds.",
        "#### Plot Hooks and Encounters",
        "An unplayed hook belongs only to the prepared scene.",
        "## Council",
    )
    graph = _graph(rows)
    original = deepcopy(graph)

    result, diagnostics = compile_gazetteer_governance_relations(graph, rows)

    assert graph == original
    assert len(result["nodes"]) == 2
    relation = next(edge for edge in result["edges"] if edge["relationship_type"] == "governs")
    assert relation["from_node_id"] == "org_mirathorn_city_council"
    assert relation["to_node_id"] == "loc_mirathorn"
    assert relation["evidence_refs"] == [_source_ref(rows[4]), _source_ref(rows[0])]
    for node in result["nodes"]:
        assert _source_ref(rows[0]) in node["evidence_refs"]
    assert relation["semantic_state"]["lifecycle_state"] == "candidate"
    assert diagnostics["source_grounded_governance"]["status"] == "added"
    assert diagnostics["source_grounded_governance"]["source_span_ref_id"] == "span:5"
    assert diagnostics["prepared_scenario_scope"]["sections"][0]["heading"] == "Plot Hooks and Encounters"

    repeated, repeated_diagnostics = _apply_governance_relation(result, rows)
    assert repeated == result
    assert repeated_diagnostics["status"] == "already_present"


@pytest.mark.parametrize(
    ("council_label", "expected"),
    [
        ("Mirathorn City Council", "added"),
        ("City Council of Mirathorn", "added"),
        ("Council of Mirathorn", "added"),
    ],
)
def test_city_council_alias_forms_are_explicitly_bound(council_label, expected):
    rows = _rows(
        "# The City of Mirathorn", "## History", "Long ago.",
        "### Governance:",
        "A democratic city-state governed by a council representing various races.",
    )
    graph = _graph(rows)
    graph["nodes"][1]["label"] = council_label
    result, diagnostics = _apply_governance_relation(graph, rows)
    assert diagnostics["status"] == expected
    assert len(result["edges"]) == 1


def test_frontmatter_city_title_binds_the_exact_saved_document():
    rows = _rows(
        "---",
        'title: "The City of Mirathorn"',
        "---",
        "### Governance:",
        "A democratic city-state governed by a council representing various races.",
    )
    result, diagnostics = _apply_governance_relation(_graph(rows), rows)
    assert diagnostics["status"] == "added"
    assert result["edges"][0]["to_node_id"] == "loc_mirathorn"


def test_profile_reads_frontmatter_and_governance_from_multiline_source_spans():
    statement = "A democratic city-state governed by a council representing various races."
    rows = [
        {
            "source_span_ref_id": "span:frontmatter",
            "line_start": 1,
            "line_end": 3,
            "text": '---\ntitle: "The City of Mirathorn"\n---',
        },
        {
            "source_span_ref_id": "span:history",
            "line_start": 4,
            "line_end": 5,
            "text": "## History\nFounded long ago.",
        },
        {
            "source_span_ref_id": "span:governance",
            "line_start": 6,
            "line_end": 7,
            "text": f"### Governance:\n{statement}",
        },
    ]
    governance_ref = _source_ref(rows[2])
    governance_ref["anchor_quotes"] = [statement]
    semantic_state = {
        "authority_state": "system_derived",
        "canon_state": "worldbuilding_draft",
        "evidence_role": "source_evidence",
        "lifecycle_state": "candidate",
        "visibility_state": "gm_private",
    }
    graph = {
        "nodes": [
            {
                "node_id": "loc_mirathorn",
                "label": "Mirathorn",
                "node_type": "location",
                "semantic_state": deepcopy(semantic_state),
                "evidence_refs": [deepcopy(governance_ref)],
            },
            {
                "node_id": "org_mirathorn_city_council",
                "label": "Mirathorn City Council",
                "node_type": "organization",
                "semantic_state": deepcopy(semantic_state),
                "evidence_refs": [deepcopy(governance_ref)],
            },
        ],
        "edges": [],
    }

    result, diagnostics = _apply_governance_relation(graph, rows)

    assert diagnostics["status"] == "added"
    assert result["edges"][0]["evidence_refs"][0]["source_span_ref_id"] == "span:governance"
    title_ref = result["edges"][0]["evidence_refs"][1]
    assert title_ref["source_span_ref_id"] == "span:frontmatter"
    assert title_ref["anchor_quotes"] == ['title: "The City of Mirathorn"']


def test_ambiguous_or_unopenable_endpoints_do_not_create_a_relation():
    rows = _rows(
        "# The City of Mirathorn", "## History", "Long ago.",
        "### Governance:",
        "A democratic city-state governed by a council representing various races.",
    )
    graph = _graph(rows)
    graph["nodes"].append(deepcopy(graph["nodes"][1]))
    result, diagnostics = _apply_governance_relation(graph, rows)
    assert result["edges"] == []
    assert diagnostics["reason"] == "governance_endpoints_not_unique"

    graph = _graph(rows)
    graph["nodes"][0]["evidence_refs"][0]["can_open_source"] = False
    result, diagnostics = _apply_governance_relation(graph, rows)
    assert result["edges"] == []
    assert diagnostics["reason"] == "endpoint_missing_openable_governance_evidence"


def test_conflicting_reverse_or_duplicate_governance_edges_are_not_repaired():
    rows = _rows(
        "# The City of Mirathorn", "## History", "Long ago.",
        "### Governance:",
        "A democratic city-state governed by a council representing various races.",
    )
    graph = _graph(rows)
    graph["edges"] = [{
        "edge_id": "existing-reversed",
        "from_node_id": "loc_mirathorn",
        "to_node_id": "org_mirathorn_city_council",
        "relationship_type": "governs",
        "evidence_refs": [_source_ref(rows[4])],
    }]
    result, diagnostics = _apply_governance_relation(graph, rows)
    assert result["edges"] == graph["edges"]
    assert diagnostics["reason"] == "conflicting_or_duplicate_governance_edge"


def test_only_a_governance_section_and_explicit_city_state_sentence_qualify():
    rows = _rows(
        "# The City of Mirathorn",
        "## History",
        "A democratic city-state governed by a council representing various races.",
        "## Key Locations",
        "Market Street.",
    )
    graph = _graph(rows)
    result, diagnostics = _apply_governance_relation(graph, rows)
    assert result["edges"] == []
    assert diagnostics["status"] == "not_applicable"


def test_profile_is_a_new_catalogued_extension_of_prepared_scenario_scope():
    assert PROFILE == "worldbuilding_gazetteer_v1@1.9"
    assert GAZETTEER_GOVERNANCE_PROFILE.profile_version == "1.9"
    assert GAZETTEER_GOVERNANCE_PROFILE.profile_id == "worldbuilding_gazetteer_v1"
    assert PROFILE in PUBLISHABLE_WORLDBUILDING_PROFILES
