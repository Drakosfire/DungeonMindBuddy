"""First-World facade preserves the publication owner's authorization callback."""
import pytest

from apps.live_control_server.services import extract_promote as facade
from apps.live_control_server.services import first_world_graph_publication as owner


@pytest.mark.parametrize("operation", ["prepare_first_world", "confirm_first_world"])
def test_facade_forwards_exact_authorizer_and_preserves_denial(monkeypatch, operation):
    request = object()
    response = object()
    seen = []

    def authorize(world_id):
        seen.append(world_id)
        if world_id == "forbidden-world":
            raise PermissionError("World access denied")

    def implementation(value, *, authorize_world):
        assert value is request
        assert authorize_world is authorize
        authorize_world("allowed-world")
        return response

    monkeypatch.setattr(owner, operation, implementation)
    assert getattr(facade, operation)(request, authorize_world=authorize) is response
    assert seen == ["allowed-world"]

    def denied(value, *, authorize_world):
        assert value is request
        authorize_world("forbidden-world")
        pytest.fail("publication must stop after authorization denial")

    monkeypatch.setattr(owner, operation, denied)
    with pytest.raises(PermissionError, match="World access denied"):
        getattr(facade, operation)(request, authorize_world=authorize)
    assert seen == ["allowed-world", "forbidden-world"]


@pytest.mark.parametrize("operation", ["prepare_first_world", "confirm_first_world"])
def test_internal_call_without_authorizer_preserves_optional_contract(monkeypatch, operation):
    request = object()
    response = object()

    def implementation(value, *, authorize_world):
        assert value is request
        assert authorize_world is None
        return response

    monkeypatch.setattr(owner, operation, implementation)
    assert getattr(facade, operation)(request) is response
