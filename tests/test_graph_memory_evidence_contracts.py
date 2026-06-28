from __future__ import annotations

import pytest
from pydantic import ValidationError

from graph_memory.evidence import (
    KNOWN_SOURCE_DOMAINS,
    GraphMemoryEvidenceRef,
    GraphMemorySourceArtifact,
    is_known_source_domain,
)
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_payload,
)
from graph_memory.union_supergraph.model import (
    UnionSupergraphEvidence,
    UnionSupergraphSourceArtifact,
)


@pytest.fixture
def fixture() -> dict:
    return load_union_supergraph_payload(DEFAULT_FIXTURE_PATH)


def test_known_source_domains_include_current_union_supergraph_domains(
    fixture: dict,
) -> None:
    assert set(fixture["source_domains"]).issubset(KNOWN_SOURCE_DOMAINS)


def test_is_known_source_domain_accepts_known_domain() -> None:
    assert is_known_source_domain("recap") is True


def test_is_known_source_domain_rejects_unknown_domain() -> None:
    assert is_known_source_domain("unknown_domain") is False


def test_source_artifact_model_parses_fixture_artifact(fixture: dict) -> None:
    artifact_data = fixture["source_artifacts"][
        "artifact:recap:longmont-c2:session-23"
    ]

    artifact = GraphMemorySourceArtifact.model_validate(artifact_data)

    assert artifact.source_artifact_id == "artifact:recap:longmont-c2:session-23"
    assert artifact.source_domain == "recap"
    assert artifact.campaign_id == "longmont-c2"
    assert artifact.uri.endswith("source_artifact.json")
    assert artifact.model_extra["session_id"] == "session-23"


def test_evidence_ref_model_parses_recap_evidence(fixture: dict) -> None:
    evidence_data = fixture["evidence"]["evidence:session-23:caelynn:recap-mention"]

    evidence = GraphMemoryEvidenceRef.model_validate(evidence_data)

    assert evidence.source_domain == "recap"
    assert evidence.session_id == "session-23"
    assert evidence.source_span_ref_id == "spref:session-23:p014"
    assert evidence.can_open_source is True
    assert evidence.can_highlight_span is True


def test_evidence_ref_model_parses_worldbuilding_evidence(fixture: dict) -> None:
    evidence_data = fixture["evidence"]["evidence:worldbuilding:caelynn:character-note"]

    evidence = GraphMemoryEvidenceRef.model_validate(evidence_data)

    assert evidence.source_domain == "worldbuilding"
    assert evidence.session_id is None
    assert evidence.locator == "worldbuilding/characters/caelynn.md#read-model-example"
    assert evidence.can_open_source is True
    assert evidence.can_highlight_span is False


def test_evidence_ref_session_scoped_helper(fixture: dict) -> None:
    recap_data = fixture["evidence"]["evidence:session-23:caelynn:recap-mention"]
    worldbuilding_data = fixture["evidence"][
        "evidence:worldbuilding:caelynn:character-note"
    ]

    assert GraphMemoryEvidenceRef.model_validate(recap_data).is_session_scoped is True
    assert (
        GraphMemoryEvidenceRef.model_validate(worldbuilding_data).is_session_scoped
        is False
    )


def test_evidence_ref_source_locator_helper(fixture: dict) -> None:
    recap_data = fixture["evidence"]["evidence:session-23:caelynn:recap-mention"]
    worldbuilding_data = fixture["evidence"][
        "evidence:worldbuilding:caelynn:character-note"
    ]
    no_locator_data = {
        **worldbuilding_data,
        "locator": None,
        "uri": None,
        "source_locator": None,
        "line_ref": None,
        "source_span_ref_id": None,
    }

    assert GraphMemoryEvidenceRef.model_validate(recap_data).has_source_locator is True
    assert (
        GraphMemoryEvidenceRef.model_validate(worldbuilding_data).has_source_locator
        is True
    )
    assert GraphMemoryEvidenceRef.model_validate(no_locator_data).has_source_locator is False


def test_evidence_ref_rejects_invalid_basic_types(fixture: dict) -> None:
    evidence_data = {
        **fixture["evidence"]["evidence:session-23:caelynn:recap-mention"],
        "can_open_source": "true",
    }

    with pytest.raises(ValidationError, match="can_open_source"):
        GraphMemoryEvidenceRef.model_validate(evidence_data)


def test_union_supergraph_evidence_type_is_shared_contract() -> None:
    assert issubclass(UnionSupergraphEvidence, GraphMemoryEvidenceRef)


def test_union_supergraph_source_artifact_type_is_shared_contract() -> None:
    assert issubclass(UnionSupergraphSourceArtifact, GraphMemorySourceArtifact)
