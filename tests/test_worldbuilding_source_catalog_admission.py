"""Registered Build evidence must open through the actual native observation reader."""

import os

import pytest

from tests.test_recap_source_observation_followup import (
    observation_case as _observation_fixture,
)
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
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding as actual_binding,
)

observation_case = _observation_fixture

pytestmark = pytest.mark.skipif(
    not os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL"),
    reason="requires dedicated disposable Core PostgreSQL",
)


def test_registered_build_prepare_admits_exact_world_source_and_confirm_only_proves(
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
    admitted = plan.source_admission
    assert admitted is not None and admitted.campaign_id is None
    native_artifact = case["bundle"].sources.get_artifact(admitted.source_artifact_id)
    assert native_artifact.world_id == case["world"]
    assert native_artifact.campaign_id is None
    assert admitted.content_sha256 == plan.publication_binding.source_sha256
    assert all(a.campaign_scope is None for a in plan.effect.accepted_proposals)
    repeated = prepare_worldbuilding(
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
    assert repeated.source_admission == admitted
    from apps.live_control_server.services.extract_promote import ExtractPromoteError
    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )

    registered = get_source_artifact(root, admitted.source_artifact_id)
    assert registered.world_id == registered.campaign_id == "publication-managed"
    from apps.live_control_server.services import (
        worldbuilding_graph_publication as publication,
    )

    real_admit = publication._prepare_source_admission
    registry_path = root / "out/registries/world_containers.json"
    saved_registry = registry_path.read_bytes()

    def rebind_after_admission(resolved_run, binding):
        result = real_admit(resolved_run, binding)
        registry = json.loads(saved_registry)
        registry["records"][0]["native_graph_binding"]["native_world_id"] = (
            "other-native-world"
        )
        registry_path.write_text(json.dumps(registry))
        return result

    with monkeypatch.context() as race:
        race.setattr(publication, "_prepare_source_admission", rebind_after_admission)
        with pytest.raises(ExtractPromoteError) as drift:
            prepare_worldbuilding(
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
        assert drift.value.code == "worldbuilding_source_binding_changed"
    registry_path.write_bytes(saved_registry)
    assert (
        case["bundle"].world_graph.get_head(case["world"]).head_revision_id
        == parent.head_revision_id
    )
    tampered = plan.model_copy(
        update={
            "source_admission": admitted.model_copy(
                update={
                    "source_revision_id": "forged:revision",
                }
            )
        }
    )
    with pytest.raises(ExtractPromoteError):
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=tampered))
    from apps.live_control_server.ports.world_graph_source_admission import (
        WorldGraphSourceAdmissionError,
    )

    class MissingProof:
        def prove_or_admit(self, request):
            pytest.fail("Confirm must not admit or repair catalog authority")

        def prove(self, **kwargs):
            raise WorldGraphSourceAdmissionError(
                "Missing proof", code="source_not_admitted"
            )

    monkeypatch.setattr(
        "apps.live_control_server.ports.world_graph_source_admission_access.get_world_graph_source_admission_authority",
        lambda: MissingProof(),
    )
    with pytest.raises(ExtractPromoteError) as rejected:
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    assert rejected.value.code == "source_not_admitted"
    assert (
        case["bundle"].world_graph.get_head(case["world"]).head_revision_id
        == parent.head_revision_id
    )
