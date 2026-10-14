"""Registered Build evidence must open through the actual native observation reader."""

import os

import pytest

from tests.test_recap_source_observation_followup import observation_case  # noqa: F401
from tests.test_cutover_worldbuilding_authority_port import _install_worldbuilding_repo
from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run
from apps.live_control_server.models.extract_promote import (
    WorldbuildingWritePlanPrepareRequest,
    WorldbuildingWritePlanConfirmRequest,
)
from apps.live_control_server.services.worldbuilding_graph_publication import (
    prepare_worldbuilding,
    confirm_worldbuilding,
)
from apps.live_control_server.integrations.dungeonmind import (
    world_graph_reads as direct,
)
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding as actual_binding,
)
from graph_memory.retrieval.models import (
    WorldGraphObjectRequest,
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL"),
    reason="requires dedicated disposable Core PostgreSQL",
)


def test_registered_build_publication_emits_readable_worldbuilding_observation(
    observation_case,
    tmp_path,
    monkeypatch,
):
    case = observation_case
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path / "repo"))
    monkeypatch.setattr(
        "apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding",
        actual_binding,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.extract_promote.resolve_managed_world_binding",
        actual_binding,
    )
    root = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id=case["world"])
    run_id, _ = _write_bld08_reviewable_run(
        root,
        world_id="publication-managed",
        campaign_id="publication-managed",
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph
    import json

    resolved = resolve_promotable_ingest_run(run_id, root=root)
    candidate = load_typed_candidate_graph(
        json.loads(resolved.candidate_graph_path.read_text())
    )
    parent = case["bundle"].world_graph.get_head(case["world"])
    plan = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            {
                "runId": run_id,
                "expectedParentRevisionId": parent.head_revision_id,
                "dispositions": [
                    {"assertionId": n.node_id, "decision": "create_new"}
                    for n in candidate.nodes
                ]
                + [
                    {"assertionId": e.edge_id, "decision": "reject"}
                    for e in candidate.edges
                ],
            }
        )
    )
    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    request = WorldGraphObjectRequest.model_validate(
        {
            "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
            "worldId": case["world"],
            "campaignId": None,
            "admissibility": "gm",
            "scopeMode": "world",
            "revisionPin": receipt.committed_revision_id,
            "nodeId": candidate.nodes[0].node_id,
        }
    )
    services = direct.direct_services_from_config(case["world"])
    result = services.retrieval.get_complete_object(
        direct._map_retrieval_context(request, services.binding),
        object_id=candidate.nodes[0].node_id,
    )
    assert result.found
    assert result.object.summary == candidate.nodes[0].description
