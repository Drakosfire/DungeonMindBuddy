"""Frozen synthetic gold for producer source indexes → canonical party evidence."""

from copy import deepcopy
import json

import pytest
from jsonschema import ValidationError, validate

from src.graph_memory.extraction.party_claimed_fill import (
    ClaimPacket,
    ClaimedEntity,
    SourceBoundPartyFillSpec,
    bind_fill_evidence,
    apply_fill_to_parts,
    render_fill_prompt,
    PASS_NAME,
)
from src.graph_memory.extraction.category_candidate_graph_schema import (
    schema_for_pass_spec,
)
from src.graph_memory.extraction.category_candidate_graph_extractor import (
    sanitize_parts,
)
from src.graph_memory.extraction.graph_ingest_packaging import _write_validation_report


def packet():
    return ClaimPacket(
        claims=[
            ClaimedEntity(
                "pc:ari",
                "Ari",
                "pc",
                "ari",
                2,
                (
                    "artifact:immutable:sha256:abc:paragraph:001",
                    "artifact:immutable:sha256:abc:paragraph:002",
                ),
                ("Ari",),
            )
        ],
        source_rows=[
            {
                "source_span_ref_id": "artifact:immutable:sha256:abc:paragraph:001",
                "text": "Ari held the gate.",
            },
            {
                "source_span_ref_id": "artifact:immutable:sha256:abc:paragraph:002",
                "text": "Ari returned to camp.",
            },
            {
                "source_span_ref_id": "artifact:immutable:sha256:abc:paragraph:003",
                "text": "Bea kept watch.",
            },
        ],
        allowed_target_node_ids=[],
        baseline_nodes_by_id={
            "pc:ari": {
                "node_id": "pc:ari",
                "label": "Ari",
                "description": "Existing accepted baseline",
                "evidence_refs": [
                    {
                        "source_span_ref_id": "artifact:immutable:sha256:abc:paragraph:001",
                        "anchor_quotes": ["held the gate"],
                    }
                ],
            }
        },
    )


def offered():
    return {
        "filled_nodes": [
            {
                "node_id": "pc:ari",
                "source_contexts": [
                    {"source_row_index": 0},
                    {"source_row_index": 1},
                ],
            }
        ]
    }


def spec():
    return SourceBoundPartyFillSpec(
        PASS_NAME,
        "character",
        "fill",
        "fill",
        kind="claimed_fill",
        source_row_indexes=(0, 1, 2),
    )


def test_source_indexes_are_provider_schema_and_host_bound_without_mutating_packet():
    p, raw = packet(), offered()
    original = deepcopy(p)
    prompt = render_fill_prompt(p)
    assert "Source row 0" in prompt
    assert "artifact:immutable" not in prompt
    validate(raw, schema_for_pass_spec(spec()))
    bound, diag = bind_fill_evidence(p, raw)
    assert diag["enrichment_complete"]
    assert p == original
    assert raw == offered()
    parts, applied = apply_fill_to_parts(
        {"nodes": list(p.baseline_nodes_by_id.values())},
        parsed=bound,
        claimed_ids={"pc:ari"},
    )
    assert applied["filled_applied"] == 1
    clean, dropped = sanitize_parts(
        parts, {row["source_span_ref_id"] for row in p.source_rows}
    )
    assert not dropped["dropped_no_valid_evidence"]
    assert [
        ref["source_span_ref_id"] for ref in clean["nodes"][0]["evidence_refs"]
    ] == [row["source_span_ref_id"] for row in p.source_rows[:2]]


@pytest.mark.parametrize("index", [-1, 3, True, "0"])
def test_unknown_or_noninteger_rows_rejected_by_schema_and_host(index):
    raw = offered()
    raw["filled_nodes"][0]["source_contexts"][0]["source_row_index"] = index
    with pytest.raises(ValidationError):
        validate(raw, schema_for_pass_spec(spec()))
    bound, diag = bind_fill_evidence(packet(), raw)
    assert bound is None
    assert "unknown_source_row" in diag["binding_errors"]


@pytest.mark.parametrize(
    "source_text",
    [
        "Ephanna will use Eldritch Blast.",
        "If the ward breaks, Ephanna may cast Eldritch Blast.",
        "Ephanna did not use Eldritch Blast.",
        "Orik told Ephanna to use Eldritch Blast.",
        "Ephanna held the gate. She will use Eldritch Blast next time.",
    ],
)
def test_public_party_fill_preserves_complete_source_modality(source_text):
    p = packet()
    p.claims[0] = ClaimedEntity(
        "pc:ephanna", "Ephanna", "pc", "ephanna", 1,
        ("artifact:immutable:sha256:abc:paragraph:001",), ("Ephanna",),
    )
    p.baseline_nodes_by_id = {
        "pc:ephanna": {
            "node_id": "pc:ephanna",
            "label": "Ephanna",
            "description": "Existing accepted baseline",
        }
    }
    p.source_rows = [
        {
            "source_span_ref_id": "artifact:immutable:sha256:abc:paragraph:001",
            "text": source_text,
        }
    ]
    raw = offered()
    raw["filled_nodes"][0]["node_id"] = "pc:ephanna"
    raw["filled_nodes"][0]["source_contexts"] = [{"source_row_index": 0}]

    bound, diag = bind_fill_evidence(p, raw)

    assert diag["enrichment_complete"]
    node = bound["filled_nodes"][0]
    assert node["description"] == source_text
    assert node["session_actions"] == [source_text]
    assert node["evidence_refs"] == [
        {
            "source_span_ref_id": "artifact:immutable:sha256:abc:paragraph:001",
            "anchor_quotes": [source_text],
        }
    ]


def test_party_fill_rejects_a_source_row_not_bound_to_that_claim():
    raw = offered()
    raw["filled_nodes"][0]["source_contexts"][1]["source_row_index"] = 2
    bound, diag = bind_fill_evidence(packet(), raw)
    assert bound is None
    assert "source_row_not_linked_to_claim" in diag["binding_errors"]


@pytest.mark.parametrize(
    "damage",
    [
        "out_of_range_row",
        "cross_row",
        "empty_contexts",
        "partial",
        "duplicate",
        "invented",
        "provider_prose",
    ],
)
def test_invalid_fill_is_atomic_and_keeps_baseline(damage):
    p, raw = packet(), offered()
    node = raw["filled_nodes"][0]
    if damage == "out_of_range_row":
        node["source_contexts"][0]["source_row_index"] = 99
    elif damage == "cross_row":
        node["source_contexts"][1]["source_row_index"] = 2
    elif damage == "empty_contexts":
        node["source_contexts"] = []
    elif damage == "partial":
        p.claims.append(ClaimedEntity("pc:bea", "Bea", "pc", "bea", 1, (), ("Bea",)))
    elif damage == "duplicate":
        raw["filled_nodes"].append(deepcopy(node))
    elif damage == "invented":
        node["node_id"] = "pc:invented"
    elif damage == "provider_prose":
        node["description"] = "Provider-written paraphrase."
    baseline = deepcopy(p.baseline_nodes_by_id)
    bound, diag = bind_fill_evidence(p, raw)
    assert bound is None
    assert not diag["enrichment_complete"]
    assert p.baseline_nodes_by_id == baseline


def test_packaging_counts_nested_refs_and_rejects_unresolved(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    p, raw = packet(), offered()
    bound, _ = bind_fill_evidence(p, raw)
    parts, _ = apply_fill_to_parts(
        {"nodes": list(p.baseline_nodes_by_id.values())},
        parsed=bound,
        claimed_ids={"pc:ari"},
    )
    graph = {**parts, "edges": [], "beats": []}
    index = tmp_path / "source_span_index.json"
    index.write_text(
        json.dumps(
            {"spans": [{"span_id": row["source_span_ref_id"]} for row in p.source_rows]}
        )
    )
    path = tmp_path / "candidate_graph.json"

    def check():
        path.write_text(json.dumps(graph))
        result = _write_validation_report(
            output_dir=tmp_path,
            campaign_id="synthetic",
            session_id="session-1",
            candidate_graph_path=path,
            candidate_graph=graph,
            source_span_index_path=index,
        )
        return result, json.loads(result.path.read_text())["diagnostics"]

    result, diagnostics = check()
    assert result.valid
    assert diagnostics["evidence_ref_count"] == 2
    assert diagnostics["resolvable_evidence_ref_count"] == 2
    graph["nodes"][0]["evidence_refs"][0]["source_span_ref_id"] = "shortened"
    result, diagnostics = check()
    assert not result.valid
    assert diagnostics["unresolved_evidence_ref_count"] == 1
    assert diagnostics["resolvable_evidence_ref_count"] == 1




def test_packaging_marks_preserved_incomplete_fill_unready(tmp_path, monkeypatch):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    graph = {
        "nodes": [
            {
                **packet().baseline_nodes_by_id["pc:ari"],
                "warnings": ["party_claimed_fill_incomplete"],
            }
        ],
        "edges": [],
        "beats": [],
    }
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(graph))
    result = _write_validation_report(
        output_dir=tmp_path,
        campaign_id="synthetic",
        session_id="session-1",
        candidate_graph_path=path,
        candidate_graph=graph,
    )
    assert not result.valid
    report = json.loads(result.path.read_text())
    assert report["diagnostics"]["party_fill_incomplete_node_count"] == 1
    assert report["diagnostics"]["evidence_resolution_checked"] is False
    assert report["diagnostics"]["resolvable_evidence_ref_count"] == 0
