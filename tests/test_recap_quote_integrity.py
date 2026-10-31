from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from apps.live_control_server.services.graph_run_registry import get_extraction_run
from apps.live_control_server.services.source_artifact_registry import (
    create_recap_source_artifact,
    load_registered_source_artifact_text,
)
from graph_memory.anchor_quotes import find_anchor_quote_matches
from graph_memory.ingestion.extraction_run import ExtractionRunStatus
from graph_memory.source_span import (
    build_source_span_index_for_text,
    source_span_index_to_dict,
)
from src.graph_memory.extraction import graph_preview_runner
from src.graph_memory.extraction.graph_ingest_packaging import (
    _quotes_match_source_span,
)
from src.graph_memory.extraction.recap_extraction_profile import (
    RECAP_PROFILE_ID,
    RECAP_PROFILE_VERSION,
)
from src.graph_memory.extraction.recap_quote_integrity import (
    DEPENDENT_ITEM_REASON,
    NONLITERAL_QUOTE_REASON,
    RecapQuoteIntegrityError,
    validate_and_defer_nonliteral_recap_items,
)
from src.graph_memory.extraction.source_adapter import NormalizedExtractionSource


SOURCE = "Frank and Sara live in Mirathorn and serve the Guard.\n\nThe north gate is closed.\n"


def _case(source_text: str = SOURCE) -> tuple[str, str, dict[str, Any], dict[int, str]]:
    artifact_id = "artifact:recap:test:session-29"
    digest = hashlib.sha256(source_text.encode("utf-8")).hexdigest()
    index = source_span_index_to_dict(
        build_source_span_index_for_text(
            source_artifact_id=artifact_id,
            content_sha256=digest,
            text=source_text,
        )
    )
    spans = {
        int(row["start_line"]): str(row["source_span_id"])
        for row in index["spans"]
    }
    return artifact_id, digest, index, spans


def _ref(
    artifact_id: str,
    span_id: str,
    quote: str,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "source_artifact_id": artifact_id,
        "source_ref_id": f"{artifact_id}:text",
        "source_span_ref_id": span_id,
        "source_anchor_id": f"anchor:{span_id}",
        "evidence_role": "source_evidence",
        "can_open_source": True,
        "can_highlight_span": True,
        "anchor_quotes": [quote],
        "anchor_quote_matches": [{"char_start": 900, "char_end": 950, "match_text": "forged"}],
        **extra,
    }


def _node(node_id: str, label: str, ref: dict[str, Any], **extra: Any) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "label": label,
        "node_type": "character",
        "description": f"Description for {label}",
        "importance": "medium",
        "semantic_state": {
            "canon_state": "candidate_extraction",
            "lifecycle_state": "candidate",
            "evidence_role": "source_evidence",
            "authority_state": "played_truth",
            "visibility_state": "gm_private",
        },
        "evidence_refs": [ref],
        "proposed_action": "create",
        "confidence": "medium",
        "warnings": [],
        "aliases": [],
        "corpus_ref": None,
        "session_actions": [],
        "enriched_by": None,
        **extra,
    }


def _run_graph(
    artifact_id: str,
    spans: dict[int, str],
) -> dict[str, Any]:
    return {
        "schema": "dmb_candidate_graph_preview_v0",
        "version": "0.2",
        "campaign_id": "longmont-c2",
        "session_id": "session-29",
        "source_artifact_ids": [artifact_id],
        "status": "preview",
        "preview_id": "preview:session-29",
        "diagnostics": {
            "preview_only": True,
            "extraction_performed": False,
            "llm_used": False,
            "runtime_connected": False,
            "plan_connected": False,
            "agent_interaction_connected": False,
            "corpus_scanned": False,
            "corpus_mutated": False,
            "facts_promoted": False,
            "canon_promoted": False,
            "unresolved_evidence_refs": 0,
            "missing_evidence_objects": 0,
            "warning_count": 0,
        },
        "nodes": [
            _node(
                "node:frank-sara",
                "Frank and Sara",
                _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn"),
            ),
            _node(
                "node:bad-north-guard",
                "Sara guards the north gate",
                _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn"),
            ),
        ],
        "edges": [
            {
                "edge_id": "edge:dependent",
                "from_node_id": "node:bad-north-guard",
                "to_node_id": "node:frank-sara",
                "label": "works with",
                "relationship_type": "works_with",
                "semantic_state": {
                    "canon_state": "candidate_extraction",
                    "lifecycle_state": "candidate",
                    "evidence_role": "source_evidence",
                    "authority_state": "played_truth",
                    "visibility_state": "gm_private",
                },
                "evidence_refs": [
                    _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn")
                ],
                "proposed_action": "create",
                "confidence": "medium",
                "warnings": [],
            }
        ],
        "beats": [
            {
                "beat_id": "beat:dependent",
                "title": "The guards act",
                "order": 1,
                "summary": "The guards act during the session.",
                "involved_node_ids": ["node:bad-north-guard"],
                "unresolved_thread_node_ids": [],
                "evidence_refs": [
                    _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn")
                ],
                "proposed_action": "create",
                "warnings": [],
            }
        ],
        "source_observations": [
            {
                "observation_id": "observation:dependent",
                "title": "Guard observation",
                "description": "An observation about the guard.",
                "subject_candidate_node_id": "node:bad-north-guard",
                "semantic_state": {
                    "canon_state": "candidate_extraction",
                    "lifecycle_state": "candidate",
                    "evidence_role": "source_evidence",
                    "authority_state": "played_truth",
                    "visibility_state": "gm_private",
                },
                "evidence_refs": [
                    _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn")
                ],
                "confidence": "medium",
                "warnings": [],
                "proposed_action": "create",
            }
        ],
        "proposed_writes": [
            {
                "write_id": "write:dependent-node",
                "write_type": "create_node",
                "target_id": "node:bad-north-guard",
                "label": "Create guard record",
                "reason": "The candidate is a character.",
                "evidence_refs": [
                    _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn")
                ],
                "status": "pending",
            },
            {
                "write_id": "write:dependent-write",
                "write_type": "attach_fact",
                "target_id": "write:dependent-node",
                "label": "Link guard record",
                "reason": "The guard is relevant to the candidate.",
                "evidence_refs": [
                    _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn")
                ],
                "status": "pending",
            },
        ],
        "ignored_items": [],
        "deferred_items": [],
    }


def _sanitize(graph: dict[str, Any], *, source_text: str = SOURCE):
    artifact_id, digest, index, spans = _case(source_text)
    return validate_and_defer_nonliteral_recap_items(
        graph,
        source_text=source_text,
        source_artifact_id=artifact_id,
        source_sha256=digest,
        source_span_index=index,
    )


def test_literal_matcher_normalizes_quote_spacing_punctuation_and_cache() -> None:
    source = "Frank and Sara live in Mirathorn—serving the Guard."
    artifact_id, digest, index, spans = _case(source)
    graph = {
        "source_artifact_ids": [artifact_id],
        "nodes": [
            _node(
                "node:frank",
                "Frank",
                _ref(
                    artifact_id,
                    spans[1],
                    "FRANK   AND Sara live in Mirathorn-serving the Guard.",
                ),
            )
        ],
        "edges": [],
        "beats": [],
        "deferred_items": [],
    }

    sanitized, diagnostics = validate_and_defer_nonliteral_recap_items(
        graph,
        source_text=source,
        source_artifact_id=artifact_id,
        source_sha256=digest,
        source_span_index=index,
    )

    ref = sanitized["nodes"][0]["evidence_refs"][0]
    assert sanitized["nodes"][0]["node_id"] == "node:frank"
    assert ref["anchor_quote_matches"] == [
        {
            "quote": "FRANK   AND Sara live in Mirathorn-serving the Guard.",
            "char_start": 0,
            "char_end": len(source),
            "match_text": source,
        }
    ]
    assert diagnostics["positive_items_checked"] == 1
    assert graph["nodes"][0]["evidence_refs"][0]["anchor_quote_matches"][0]["char_start"] == 900


def test_nonliteral_node_and_all_typed_dependents_are_deferred() -> None:
    artifact_id, _, _, spans = _case()
    graph = _run_graph(artifact_id, spans)
    graph["nodes"][1]["evidence_refs"][0]["anchor_quotes"].append(
        "Sara personally guards the north gate."
    )
    original = copy.deepcopy(graph)

    sanitized, diagnostics = _sanitize(graph)

    assert graph == original
    assert [item["node_id"] for item in sanitized["nodes"]] == ["node:frank-sara"]
    assert sanitized["edges"] == []
    assert sanitized["beats"] == []
    assert sanitized["source_observations"] == []
    assert sanitized["proposed_writes"] == []
    deferred = {item["item_id"]: item for item in sanitized["deferred_items"]}
    assert set(deferred) == {
        "node:bad-north-guard",
        "edge:dependent",
        "beat:dependent",
        "observation:dependent",
        "write:dependent-node",
        "write:dependent-write",
    }
    assert deferred["node:bad-north-guard"]["warnings"] == [NONLITERAL_QUOTE_REASON]
    assert deferred["edge:dependent"]["warnings"] == [DEPENDENT_ITEM_REASON]
    assert deferred["node:bad-north-guard"]["evidence_refs"][0]["anchor_quotes"] == [
        "Frank and Sara live in Mirathorn"
    ]
    assert diagnostics["items_deferred"] == 6


def test_empty_or_forged_context_anchor_cannot_become_positive() -> None:
    artifact_id, _, _, spans = _case()
    graph = {
        "source_artifact_ids": [artifact_id],
        "nodes": [
            _node(
                "node:trusted-looking",
                "Trusted registry label",
                _ref(artifact_id, spans[1], "invented summary phrase"),
                context_anchor=True,
                corpus_ref={"type": "location", "ref_id": "mirathorn"},
            )
        ],
        "edges": [],
        "beats": [],
        "deferred_items": [],
    }

    sanitized, _ = _sanitize(graph)

    assert sanitized["nodes"] == []
    assert sanitized["deferred_items"][0]["item_id"] == "node:trusted-looking"
    assert sanitized["deferred_items"][0]["evidence_refs"] == []


@pytest.mark.parametrize("quotes", [[], [""], [None], "Frank and Sara"])
def test_missing_or_malformed_quotes_defer_the_whole_positive_item(quotes: Any) -> None:
    artifact_id, _, _, spans = _case()
    ref = _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn")
    ref["anchor_quotes"] = quotes
    graph = {
        "source_artifact_ids": [artifact_id],
        "nodes": [_node("node:frank", "Frank", ref)],
        "edges": [],
        "beats": [],
        "deferred_items": [],
    }

    sanitized, _ = _sanitize(graph)

    assert sanitized["nodes"] == []
    deferred = sanitized["deferred_items"][0]
    assert deferred["item_id"] == "node:frank"
    assert deferred["evidence_refs"] == []
    assert deferred["warnings"] == [NONLITERAL_QUOTE_REASON]


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("digest", "source_digest_mismatch"),
        ("index", "source_index_mismatch"),
        ("bounds", "source_index_invalid"),
        ("artifact", "source_artifact_mismatch"),
        ("ref", "source_ref_mismatch"),
        ("span", "source_span_mismatch"),
    ],
)
def test_source_or_evidence_identity_mismatch_fails_closed(
    mutation: str, expected_code: str
) -> None:
    artifact_id, digest, index, spans = _case()
    graph = {
        "source_artifact_ids": [artifact_id],
        "nodes": [
            _node(
                "node:frank",
                "Frank",
                _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn"),
            )
        ],
        "edges": [],
        "beats": [],
        "deferred_items": [],
    }
    kwargs: dict[str, Any] = {
        "source_text": SOURCE,
        "source_artifact_id": artifact_id,
        "source_sha256": digest,
        "source_span_index": index,
    }
    ref = graph["nodes"][0]["evidence_refs"][0]
    if mutation == "digest":
        kwargs["source_sha256"] = "0" * 64
    elif mutation == "index":
        kwargs["source_span_index"] = {**index, "extra": "forged"}
    elif mutation == "bounds":
        bad_index = copy.deepcopy(index)
        bad_index["spans"][0]["end_line"] = 999
        kwargs["source_span_index"] = bad_index
    elif mutation == "artifact":
        ref["source_artifact_id"] = "artifact:recap:other"
    elif mutation == "ref":
        ref["source_ref_id"] = "artifact:recap:other:text"
    elif mutation == "span":
        ref["source_span_ref_id"] = "span:unknown"

    with pytest.raises(RecapQuoteIntegrityError) as error:
        validate_and_defer_nonliteral_recap_items(graph, **kwargs)
    assert error.value.code == expected_code


def test_unsupported_standing_link_to_deferred_node_fails_closed() -> None:
    artifact_id, _, _, spans = _case()
    graph = {
        "source_artifact_ids": [artifact_id],
        "nodes": [
            _node(
                "node:bad",
                "Bad node",
                _ref(artifact_id, spans[1], "not a literal quote"),
            )
        ],
        "edges": [],
        "beats": [],
        "deferred_items": [],
        "standing_links": [{"source": "registry", "target_node_id": "node:bad"}],
    }

    with pytest.raises(RecapQuoteIntegrityError, match="references a deferred candidate ID") as error:
        _sanitize(graph)
    assert error.value.code == "unsupported_dependent_reference"


def test_gate_preserves_candidate_version_and_absent_optional_collections() -> None:
    artifact_id, _, _, spans = _case()
    graph = {
        "schema": "dmb_candidate_graph_preview_v0",
        "version": "0.1",
        "source_artifact_ids": [artifact_id],
        "nodes": [
            _node(
                "node:frank",
                "Frank",
                _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn"),
            )
        ],
        "edges": [],
        "beats": [],
        "deferred_items": [],
    }

    sanitized, _ = _sanitize(graph)

    assert sanitized["version"] == "0.1"
    assert "source_observations" not in sanitized
    assert "proposed_writes" not in sanitized


@pytest.mark.parametrize(
    ("field", "code"),
    [
        ("nodes", "candidate_collection_invalid"),
        ("deferred_items", "deferred_collection_invalid"),
    ],
)
def test_empty_malformed_collection_is_not_treated_as_absent(field: str, code: str) -> None:
    artifact_id, _, _, spans = _case()
    graph = {
        "source_artifact_ids": [artifact_id],
        "nodes": [
            _node(
                "node:frank",
                "Frank",
                _ref(artifact_id, spans[1], "Frank and Sara live in Mirathorn"),
            )
        ],
        "edges": [],
        "beats": [],
        "deferred_items": [],
    }
    graph[field] = ""

    with pytest.raises(RecapQuoteIntegrityError) as error:
        _sanitize(graph)

    assert error.value.code == code


def test_reprocessing_is_idempotent_and_sanitizes_existing_deferred_evidence() -> None:
    artifact_id, _, _, spans = _case()
    graph = {
        "source_artifact_ids": [artifact_id],
        "nodes": [
            _node(
                "node:bad",
                "Bad node",
                _ref(artifact_id, spans[1], "not a literal quote"),
            )
        ],
        "edges": [],
        "beats": [],
        "deferred_items": [
            {
                "item_id": "deferred:old",
                "label": "Old deferred item",
                "reason": "already deferred",
                "evidence_refs": [
                    _ref(artifact_id, spans[1], "also not a literal quote")
                ],
            }
        ],
    }

    once, _ = _sanitize(graph)
    twice, second_diagnostics = _sanitize(once)

    assert twice == once
    assert len(twice["deferred_items"]) == 2
    assert twice["deferred_items"][0]["evidence_refs"] == []
    assert NONLITERAL_QUOTE_REASON in twice["deferred_items"][0]["warnings"]
    assert second_diagnostics["items_deferred"] == 0


def _admit_recap(tmp_path: Path) -> NormalizedExtractionSource:
    text = "Frank and Sara live in Mirathorn and serve the Guard.\n\nThe north gate is closed.\n"
    recap_path = tmp_path / "corpus" / "session-29.md"
    recap_path.parent.mkdir(parents=True, exist_ok=True)
    recap_path.write_text(text, encoding="utf-8")
    artifact = create_recap_source_artifact(
        tmp_path,
        world_id="world:elderwyld",
        campaign_id="longmont-c2",
        session_id="session-29",
        recap_path=recap_path,
    )
    registered, source_text = load_registered_source_artifact_text(
        tmp_path, artifact.source_artifact_id
    )
    span_index = source_span_index_to_dict(
        build_source_span_index_for_text(
            source_artifact_id=registered.source_artifact_id,
            content_sha256=registered.content_sha256 or "",
            text=source_text,
        )
    )
    return NormalizedExtractionSource(
        source_artifact_id=registered.source_artifact_id,
        source_domain=str(registered.source_domain),
        source_text=source_text,
        source_sha256=registered.content_sha256 or "",
        source_uri=registered.uri,
        campaign_id=registered.campaign_id,
        session_id=registered.session_id,
        document_class=registered.document_class,
        source_span_index=span_index,
    )


def test_recap_runner_persists_sanitized_candidate_and_unchanged_private_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    application_state_dsn: str,
) -> None:
    assert application_state_dsn
    source = _admit_recap(tmp_path)
    raw_response = json.dumps(
        {
            "schema": "dmb_private_extraction_review_bundle_v1",
            "profile": f"{RECAP_PROFILE_ID}@{RECAP_PROFILE_VERSION}",
            "source_artifact_id": source.source_artifact_id,
            "source_sha256": source.source_sha256,
            "untrusted_provider_payload": "original bytes stay private",
        },
        separators=(",", ":"),
    )

    def extract(options, *, client):
        span_ids = {
            int(row["start_line"]): str(row["source_span_id"])
            for row in options.source_span_index["spans"]
        }
        graph = _run_graph(source.source_artifact_id, span_ids)
        graph["nodes"][1]["evidence_refs"][0]["anchor_quotes"].append(
            "Sara personally guards the north gate."
        )
        return SimpleNamespace(
            candidate_graph=graph,
            consolidation_diagnostics={"fixture": "fake extraction"},
            private_response_evidence=raw_response,
            known_entity_mentions=None,
        )

    monkeypatch.setattr(graph_preview_runner, "extract_category_candidate_graph", extract)
    result = graph_preview_runner.run_production_extraction(
        graph_preview_runner.ProductionExtractionRequest(
            repo_root=tmp_path,
            source=source,
            profile_id=RECAP_PROFILE_ID,
            profile_version=RECAP_PROFILE_VERSION,
            allow_llm=True,
            output_dir=tmp_path / "runs",
            initial_lineage={"native_world_id": "world:elderwyld", "campaign_id": "longmont-c2"},
        )
    )

    loaded = get_extraction_run(tmp_path, result.run.run_id)
    assert loaded.status == ExtractionRunStatus.REVIEWABLE
    candidate_path = tmp_path / loaded.components["candidate_graph"].uri.removeprefix("repo://")
    saved_graph = json.loads(candidate_path.read_text(encoding="utf-8"))
    assert [node["node_id"] for node in saved_graph["nodes"]] == ["node:frank-sara"]
    assert {item["item_id"] for item in saved_graph["deferred_items"]} >= {
        "node:bad-north-guard",
        "edge:dependent",
        "beat:dependent",
        "observation:dependent",
    }
    from application_state.ingest.components import get_component_bytes
    raw_ref = loaded.components["raw_model_response"]
    assert get_component_bytes(run_id=loaded.run_id, kind=raw_ref.kind,
        content_sha256=raw_ref.sha256) == raw_response.encode("utf-8")
    source_path = tmp_path / loaded.components["source_artifact"].uri.removeprefix("repo://")
    assert source_path.read_text(encoding="utf-8") == source.source_text
    index_path = tmp_path / loaded.components["source_span_index"].uri.removeprefix("repo://")
    saved_index = json.loads(index_path.read_text(encoding="utf-8"))
    assert saved_index == source.source_span_index
    diagnostics_ref = loaded.components["consolidation_diagnostics"]
    diagnostics = json.loads(get_component_bytes(run_id=loaded.run_id, kind=diagnostics_ref.kind,
        content_sha256=diagnostics_ref.sha256))
    assert diagnostics["recap_quote_integrity"]["items_deferred"] == 6

    spans = {span["source_span_id"]: span for span in saved_index["spans"]}
    positive_refs = 0
    for collection in ("nodes", "edges", "beats", "source_observations"):
        for item in saved_graph.get(collection, []):
            for ref in item["evidence_refs"]:
                positive_refs += 1
                assert find_anchor_quote_matches(
                    SOURCE.splitlines()[0], ref["anchor_quotes"]
                )
                span = spans.get(ref["source_span_ref_id"])
                assert span is not None
                assert _quotes_match_source_span(ref, span, source.source_text)
    assert positive_refs == 1
