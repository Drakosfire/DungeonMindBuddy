from copy import deepcopy
import pytest
from src.graph_memory.extraction.worldbuilding_role_support import (
    compile_role_support,
    REASON,
)


def fixture(texts):
    refs = [
        {"source_span_ref_id": f"s:{i}", "anchor_quotes": [t]}
        for i, t in enumerate(texts)
    ]
    graph = {
        "nodes": [
            {
                "node_id": "npc:nera",
                "label": "Nera",
                "node_type": "character",
                "description": "Role source prose.",
            },
            {"node_id": "loc:inn", "label": "Silver Inn", "node_type": "location"},
        ],
        "edges": [
            {
                "edge_id": "edge:role",
                "from_node_id": "npc:nera",
                "to_node_id": "loc:inn",
                "label": "Nera owns Silver Inn",
                "relationship_type": "owns",
                "evidence_refs": refs,
            }
        ],
        "deferred_items": [],
    }
    rows = [
        {
            "source_span_ref_id": f"s:{i}",
            "text": t,
            "line_start": i + 1,
            "line_end": i + 1,
        }
        for i, t in enumerate(texts)
    ]
    return graph, rows


def test_role_only_is_deferred_with_raw_and_support_preserved_and_idempotent():
    graph, rows = fixture(["**Nera** – **Proprietor of the Silver Inn**"])
    original = deepcopy(graph)
    result, diag = compile_role_support(graph, rows)
    assert (
        not result["edges"] and result["nodes"] == graph["nodes"] and graph == original
    )
    item = result["deferred_items"][0]
    assert (
        item["reason"] == REASON
        and item["evidence_refs"] == graph["edges"][0]["evidence_refs"]
    )
    assert diag["ownership_role_support"]["records"][0]["raw_edge"] == graph["edges"][0]
    again, _ = compile_role_support(result, rows)
    assert again == result


@pytest.mark.parametrize(
    "texts,expected",
    [
        (
            ["Nera — Proprietor of the Silver Inn", "Nera owns the Silver Inn."],
            "ownership_proposition_present",
        ),
        (
            ["Nera — Proprietor of the Silver Inn", "She inherited it."],
            "unresolved_support",
        ),
        (["Pippa — Proprietor of the Silver Inn"], "unresolved_support"),
        (["Nera — Proprietor of Copper Inn"], "unresolved_support"),
        (["Nera is not proprietor of Silver Inn."], "unresolved_support"),
        (["If Nera becomes proprietor of Silver Inn."], "unresolved_support"),
        (
            ['"Nera — Proprietor of the Silver Inn" is a forged sign.'],
            "unresolved_support",
        ),
        (["Nera — Proprietor of the Silver Inn..."], "unresolved_support"),
        (["Nera holds the deed to the Silver Inn."], "unresolved_support"),
    ],
)
def test_other_support_keeps_candidate_and_reports_honest_state(texts, expected):
    graph, rows = fixture(texts)
    result, diag = compile_role_support(graph, rows)
    assert result == graph
    assert diag["ownership_role_support"]["records"][0]["decision"] == expected


@pytest.mark.parametrize(
    "damage", ["empty", "missing", "duplicate", "invalid_quote", "mixed"]
)
def test_damaged_support_never_recognized_as_role_only(damage):
    graph, rows = fixture(["Nera — Proprietor of the Silver Inn"])
    refs = graph["edges"][0]["evidence_refs"]
    if damage == "empty":
        refs.clear()
    if damage == "missing":
        refs[0]["source_span_ref_id"] = "absent"
    if damage == "duplicate":
        refs.append(deepcopy(refs[0]))
    if damage == "invalid_quote":
        refs[0]["anchor_quotes"] = ["Nera owns it."]
    if damage == "mixed":
        refs.append(
            {"source_span_ref_id": "missing", "anchor_quotes": ["She inherited it."]}
        )
    result, diag = compile_role_support(graph, rows)
    assert (
        result == graph
        and diag["ownership_role_support"]["records"][0]["decision"]
        == "unresolved_support"
    )
