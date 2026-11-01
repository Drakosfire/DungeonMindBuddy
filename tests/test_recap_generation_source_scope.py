"""Source identity is generation input, never a publication certificate."""
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from graph_memory.ingestion.native_recap_source import SourceScope
from apps.live_control_server.services import recap_ingest_context as context
from apps.live_control_server.services.graph_run_registry import read_recap_source_scope, GraphRunRegistryError
from apps.live_control_server.services.ingest_run_catalog import _same_recap_ingest_context_authority

SCOPE = dict(managed_world_id="managed-a", native_world_id="native-a", binding_version=2, campaign_id="campaign-a")
HISTORY = dict(SCOPE, schema="dm_world_campaign_ingest_context_v1", head_revision_id="rev:old", graph_schema="dm_graph_v1", graph_payload_sha256="a" * 64)


@pytest.mark.parametrize("field,value", [("managed_world_id", " padded"), ("native_world_id", " "),
    ("campaign_id", "campaign-a "), ("binding_version", True), ("binding_version", "2"),
    ("binding_version", 2.0), ("binding_version", 0)])
def test_scope_model_refuses_malformed_identity(field, value):
    with pytest.raises(ValidationError):
        SourceScope.model_validate({**SCOPE, field: value})


def test_generation_resolves_source_owner_without_publication_host_or_graph(monkeypatch):
    calls = []
    def owner(world):
        calls.append(world)
        return SimpleNamespace(**{k: v for k, v in SCOPE.items() if k != "campaign_id"}, provisioning_id="reserved")
    monkeypatch.setattr(context, "resolve_managed_source_identity", owner)
    monkeypatch.setattr(context, "resolve_managed_world_binding", lambda *_: pytest.fail("Graph binding read"))
    monkeypatch.setattr(context, "read_recap_ingest_context", lambda **_: pytest.fail("publication observation"))
    monkeypatch.delenv(context.BASE_URL_ENV, raising=False)
    monkeypatch.delenv(context.TOKEN_ENV, raising=False)
    assert context.resolve_recap_source_scope(managed_world_id="managed-a", campaign_id="campaign-a").model_dump() == SCOPE
    assert calls == ["managed-a"]


@pytest.mark.parametrize("value", [SCOPE, HISTORY])
def test_one_reader_and_catalog_use_identity_across_fresh_and_historical(value):
    assert read_recap_source_scope(value, campaign_id="campaign-a").model_dump() == SCOPE
    assert _same_recap_ingest_context_authority(value, SCOPE)
    assert _same_recap_ingest_context_authority(value, HISTORY)
    assert not _same_recap_ingest_context_authority(value, {**SCOPE, "binding_version": 3})


@pytest.mark.parametrize("value", [{**SCOPE, "head_revision_id": "untyped"},
    {**HISTORY, "graph_payload_sha256": "bad"}, {k: v for k, v in HISTORY.items() if k != "head_revision_id"},
    {**SCOPE, "binding_version": True}, {**SCOPE, "native_world_id": " other"},
    {**HISTORY, "schema": "unknown"}, {**HISTORY, "extra": "unknown"}])
def test_incomplete_or_malformed_scope_never_becomes_authority(value):
    with pytest.raises(GraphRunRegistryError):
        read_recap_source_scope(value, campaign_id="campaign-a")
    assert not _same_recap_ingest_context_authority(value, SCOPE)


def test_publication_still_checks_current_membership_for_four_key_generation(monkeypatch):
    from apps.live_control_server.services import extract_promote
    calls = []
    def missing(**kwargs):
        calls.append(kwargs)
        raise context.RecapIngestContextError("membership removed", code="world_campaign_membership_not_found", status_code=404)
    monkeypatch.setattr(context, "read_recap_ingest_context", missing)
    with pytest.raises(extract_promote.ExtractPromoteError, match="authority is unavailable"):
        extract_promote._assert_current_recap_ingest_context(SCOPE, managed_world_id="managed-a", campaign_id="campaign-a")
    assert calls == [{"managed_world_id": "managed-a", "campaign_id": "campaign-a"}]
