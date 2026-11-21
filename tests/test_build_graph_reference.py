from hashlib import sha256

import pytest
from pydantic import ValidationError

from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
from application_state.build_proposal.graph_reference import BuildGraphReferencePlacement
from application_state.build_proposal.prose_catalog import freeze_build_prose_catalog
from application_state.build_proposal.types import BuildProposalBasis
from application_state.errors import ApplicationStateConflictError
from apps.live_control_server.services import build_graph_reference


@pytest.fixture
def placement_capture():
    draft = "The moon shines.\n"
    editor = '{"type":"doc","content":[{"type":"paragraph","content":[{"type":"text","text":"The moon shines."}]}]}'
    basis = BuildProposalBasis(
        world_id="observatory", document_id="page", registry_revision=1,
        content_sha256=sha256(draft.encode()).hexdigest(), visibility="internal", caret=1,
        draft_sha256=sha256(draft.encode()).hexdigest(), editor_sha256=sha256(editor.encode()).hexdigest(),
        draft_generation=0, selection_generation=0,
    )
    placement = BuildGraphReferencePlacement(
        basis=basis, boundary=freeze_build_prose_catalog(basis, editor, draft).target("passage1", "insert_after"),
        reference=AuthoredGraphReferenceV1(
            managed_world_id="observatory", native_world_id="native-observatory", binding_version=1,
            graph_revision="rev:one", node_id="threat:lurker", label="Lurker",
        ),
        entity_kind="threat",
    )
    return placement, editor, draft


def test_build_reference_is_bound_to_exact_captured_boundary(placement_capture):
    placement, editor, draft = placement_capture
    placement.require_boundary(editor, draft)
    with pytest.raises(ApplicationStateConflictError, match="boundary changed"):
        placement.require_boundary(editor.replace("shines", "fades"), draft)
    with pytest.raises(ValidationError, match="requires its World"):
        BuildGraphReferencePlacement.model_validate({
            **placement.model_dump(),
            "reference": {**placement.reference.model_dump(), "managed_world_id": "foreign"},
        })


def test_build_reference_joins_exact_id_and_classification_at_current_pin(placement_capture, monkeypatch):
    placement, _, _ = placement_capture
    principal = object()
    scope = {
        "managed_world_id": "observatory", "native_world_id": "native-observatory",
        "binding_version": 1, "revision_id": "rev:one", "scope_mode": "world", "campaign_id": None,
    }
    selected = {"node_id": "threat:lurker", "label": "Lurker", "kind": "threat", "selectable": True}
    namesake = {**selected, "node_id": "location:lurker", "kind": "location"}
    payload = {"scope": scope, "identities": [namesake, selected]}

    def current(request_scope, request_principal):
        assert request_scope.managed_world_id == "observatory" and request_scope.scope_mode == "world"
        assert request_principal is principal
        return payload

    monkeypatch.setattr(build_graph_reference, "authoring_identities", current)
    build_graph_reference.require_current_build_graph_reference(placement, principal)
    wrong_kind = placement.model_copy(update={
        "reference": placement.reference.model_copy(update={"node_id": namesake["node_id"]}),
    })
    with pytest.raises(ApplicationStateConflictError, match="classification changed"):
        build_graph_reference.require_current_build_graph_reference(wrong_kind, principal)
    payload["identities"] = [namesake]
    with pytest.raises(ApplicationStateConflictError, match="identity or classification changed"):
        build_graph_reference.require_current_build_graph_reference(placement, principal)
    scope["revision_id"] = "rev:later"
    with pytest.raises(ApplicationStateConflictError, match="different or changed Graph"):
        build_graph_reference.require_current_build_graph_reference(placement, principal)
