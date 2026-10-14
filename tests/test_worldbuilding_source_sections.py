"""Source retention respects explicit owners, qualifiers and section boundaries."""

from copy import deepcopy

import pytest

from src.graph_memory.extraction.worldbuilding_source_sections import (
    SourceSectionRetentionError, retain_owned_sections,
)


def rows():
    texts = [
        "#### Fantastic Livestock for the Exampleland",
        "#### 1. Glow Sheep", "Milk is believed to heal; not proven.",
        "## Animal Products and Uses:", "**Example:** A luminous cloak.",
        "#### 2. Float Goats", "Some goat riders use harnesses.",
        "### Unrelated city", "Do not attach this city fact to Exampleland.",
    ]
    return [{"source_span_ref_id": f"span:{index}", "line_start": index + 1,
             "line_end": index + 1, "text": text} for index, text in enumerate(texts)]


def graph():
    return {"nodes": [
        {"node_id": "region", "label": "The Exampleland", "node_type": "location",
         "description": "Original model context.", "evidence_refs": []},
        {"node_id": "city", "label": "City", "node_type": "location",
         "description": "City context.", "evidence_refs": []},
    ]}


def test_retains_exact_qualified_prose_and_evidence_without_crossing_owner():
    original = graph()
    transformed, diagnostics = retain_owned_sections(original, rows())
    region = transformed["nodes"][0]
    assert "Milk is believed to heal; not proven." in region["description"]
    assert "**Example:** A luminous cloak." in region["description"]
    assert "Unrelated city" not in region["description"]
    assert len(region["evidence_refs"]) == 7
    assert diagnostics["retained_sections"][0]["subsections"] == 2
    assert transformed["nodes"][1] == original["nodes"][1]
    assert original == graph()
    assert retain_owned_sections(original, rows())[0] == transformed
    assert retain_owned_sections(transformed, rows())[0] == transformed


@pytest.mark.parametrize("case", ["absent", "ambiguous", "wrong_kind", "sequence", "unbounded"])
def test_recognized_layout_cannot_silently_lose_ownership_or_boundaries(case):
    candidate, source = graph(), rows()
    if case == "absent":
        candidate["nodes"] = candidate["nodes"][1:]
    elif case == "ambiguous":
        candidate["nodes"].append(deepcopy(candidate["nodes"][0]))
    elif case == "wrong_kind":
        candidate["nodes"][0]["node_type"] = "creature"
    elif case == "sequence":
        source[5]["text"] = "#### 9. Float Goats"
    else:
        source = source[:7]
    with pytest.raises(SourceSectionRetentionError):
        retain_owned_sections(candidate, source)


def test_unrecognized_document_is_unchanged():
    candidate = graph()
    transformed, diagnostic = retain_owned_sections(candidate, rows()[1:])
    assert transformed == candidate
    assert diagnostic["retained_sections"] == []


def test_actual_candidate_assembly_preserves_prose_and_stamps_all_evidence():
    from src.graph_memory.extraction.category_candidate_graph_extractor import (
        CategoryGraphExtractionOptions, FixtureCategoryGraphPassClient, run_category_pipeline,
    )
    from src.graph_memory.extraction.worldbuilding_gazetteer_profile import (
        GAZETTEER_PROFILE, GAZETTEER_SOURCE_RETENTION_PROFILE,
    )
    from src.graph_memory.extraction.worldbuilding_profile_catalog import (
        PUBLISHABLE_WORLDBUILDING_PROFILES,
    )
    source_rows = rows()
    body = "\n".join(row["text"] for row in source_rows)
    outputs = {"location_pass": {"observation_nodes": [
        {**graph()["nodes"][0], "importance": "medium", "evidence_refs": [
            {"source_span_ref_id": "span:0", "anchor_quotes": [source_rows[0]["text"]]},
        ]},
    ]}}
    options = CategoryGraphExtractionOptions(
        campaign_id="synthetic", session_id=None, session_number=None,
        source_artifact_id="artifact:synthetic", source_text=body,
        source_span_index={"source_artifact_id": "artifact:synthetic",
                           "source_ref_id": "artifact:synthetic:text", "spans": source_rows},
        profile=GAZETTEER_SOURCE_RETENTION_PROFILE, enable_party_claimed_fill=False,
    )
    result = run_category_pipeline(FixtureCategoryGraphPassClient(outputs), options)
    node = result.candidate_graph["nodes"][0]
    assert "Milk is believed to heal; not proven." in node["description"]
    assert "Unrelated city" not in node["description"]
    assert len(node["evidence_refs"]) == 7
    assert all(ref["source_artifact_id"] == "artifact:synthetic" for ref in node["evidence_refs"])
    assert outputs["location_pass"]["observation_nodes"][0]["description"] == "Original model context."
    assert result.consolidation_diagnostics["source_section_retention"]["retained_sections"][0]["subsections"] == 2
    assert GAZETTEER_PROFILE.source_section_retainer is None
    assert PUBLISHABLE_WORLDBUILDING_PROFILES["worldbuilding_gazetteer_v1@1.1"] is options.profile


@pytest.mark.parametrize("heading", [
    "#### Unrelated city", "#### Fantastic Livestock for the Otherland",
])
def test_peer_heading_ends_prior_owner_before_foreign_prose(heading):
    source = rows()
    source[7]["text"] = heading
    if "Otherland" in heading:
        with pytest.raises(SourceSectionRetentionError):
            retain_owned_sections(graph(), source)
    else:
        transformed, _ = retain_owned_sections(graph(), source)
        assert "Do not attach this city fact" not in transformed["nodes"][0]["description"]
        assert len(transformed["nodes"][0]["evidence_refs"]) == 7
