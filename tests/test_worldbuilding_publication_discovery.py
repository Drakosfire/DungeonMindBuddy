"""Actual native publication followed by plan-free exact-run discovery."""

import json
import os
from dataclasses import replace

import pytest

from tests.test_recap_source_observation_followup import observation_case as _observation_case
from tests.test_worldbuilding_source_catalog_admission import (
    unique_registered_source_bytes as _unique_registered_source_bytes,
)
from tests.test_cutover_worldbuilding_authority_port import _install_worldbuilding_repo
from tests._cutover_d3a_blocker_safe_fixtures import _write_bld08_reviewable_run
from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
    DungeonMindWorldGraphAuthorityAdapter,
)
from apps.live_control_server.models.extract_promote import (
    WorldbuildingWritePlanPrepareRequest, WorldbuildingWritePlanConfirmRequest,
)
from apps.live_control_server.services.worldbuilding_graph_publication import (
    prepare_worldbuilding, confirm_worldbuilding,
)
from apps.live_control_server.services.worldbuilding_publication_coverage import (
    get_worldbuilding_publication_coverage,
)
from apps.live_control_server.services.promotable_ingest_run import resolve_promotable_ingest_run
from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding as actual_binding,
)
from apps.live_control_server.ports.world_graph_authority import (
    WorldbuildingPublicationDiscoveryRequest, WorldGraphAuthorityError,
)
from graph_memory.candidate_graph_to_contribution import load_typed_candidate_graph

observation_case = _observation_case
unique_registered_source_bytes = _unique_registered_source_bytes
pytestmark = pytest.mark.skipif(
    not os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL"),
    reason="dedicated disposable Core PostgreSQL required",
)


def _published_case(case, tmp_path, monkeypatch, *, publish=True):
    root = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id=case["world"])
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(root))
    monkeypatch.setattr(
        "apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding",
        actual_binding,
    )
    run_id, _ = _write_bld08_reviewable_run(
        root, world_id="publication-managed", campaign_id="publication-managed",
    )
    resolved = resolve_promotable_ingest_run(run_id, root=root)
    preview = load_typed_candidate_graph(json.loads(resolved.candidate_graph_path.read_text()))
    parent = case["bundle"].world_graph.get_head(case["world"])
    plan = prepare_worldbuilding(WorldbuildingWritePlanPrepareRequest.model_validate({
        "runId": run_id, "expectedParentRevisionId": parent.head_revision_id,
        "dispositions": [{"assertionId": node.node_id, "decision": "create_new"}
                         for node in preview.nodes]
        + [{"assertionId": edge.edge_id, "decision": "reject"} for edge in preview.edges],
    }))
    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan)) if publish else None
    adapter = DungeonMindWorldGraphAuthorityAdapter(database_url=case["dsn"])
    monkeypatch.setattr(
        "apps.live_control_server.services.worldbuilding_publication_coverage.get_world_graph_authority",
        lambda: adapter,
    )
    return root, resolved, preview, receipt, adapter


def test_fresh_discovery_after_real_publication_never_confirms_or_admits(
    observation_case, tmp_path, monkeypatch,
):
    case = observation_case
    _root, resolved, preview, receipt, adapter = _published_case(case, tmp_path, monkeypatch)
    head = case["bundle"].world_graph.get_head(case["world"])

    def forbidden(*args, **kwargs):
        pytest.fail("discovery must not publish, recover, prepare or first-admit")

    monkeypatch.setattr(adapter, "publish", forbidden)
    monkeypatch.setattr(adapter, "recover", forbidden)
    monkeypatch.setattr(
        "apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter."
        "DungeonMindWorldGraphSourceAdmissionAdapter.prove_or_admit", forbidden,
    )
    result = get_worldbuilding_publication_coverage(resolved.run_id)
    assert result.status == "published"
    assert result.historical_only
    assert len(result.publications) == 1
    assert result.publications[0].published_revision_id == receipt.committed_revision_id
    assert result.publications[0].unmapped_assertion_ids == []
    assert len([facet for item in result.candidates for facet in item.facets
                if facet.facet == "existence" and facet.verdict == "accepted"]) == len(preview.nodes)
    assert all(item.status == "published_facts" for item in result.candidates
               if item.candidate_kind == "node")
    assert case["bundle"].world_graph.get_head(case["world"]) == head


def test_complete_empty_and_foreign_source_do_not_claim_published(
    observation_case, tmp_path, monkeypatch,
):
    case = observation_case
    _root, resolved, _preview, _receipt, _adapter = _published_case(
        case, tmp_path, monkeypatch, publish=False,
    )
    result = get_worldbuilding_publication_coverage(resolved.run_id)
    assert result.status == "not_published"
    assert result.publications == []
    assert all(item.status == "not_published" for item in result.candidates)


def test_changed_source_or_candidate_cannot_inherit_coverage(
    observation_case, tmp_path, monkeypatch,
):
    case = observation_case
    _root, resolved, preview, receipt, adapter = _published_case(case, tmp_path, monkeypatch)
    request = WorldbuildingPublicationDiscoveryRequest(
        case["world"], receipt.committed_revision_id, resolved.run_id,
        resolved.source_artifact_id, resolved.source_revision_id,
        resolved.sealed_source_uri, preview,
    )
    with pytest.raises(WorldGraphAuthorityError):
        adapter.discover_worldbuilding_publications(replace(request, source_revision_id="sha256:" + "a" * 64))
    changed_nodes = tuple(replace(node, description="Altered extraction meaning")
                          for node in preview.nodes)
    changed = adapter.discover_worldbuilding_publications(
        replace(request, preview=replace(preview, nodes=changed_nodes)),
    )
    assert changed.publications
    assert not any(facet.facet == "existence" for facet in changed.publications[0].facets)
    assert changed.publications[0].unmapped_assertion_ids


def test_second_selective_description_publication_aggregates_without_latest_alias_ledger(
    observation_case, tmp_path, monkeypatch,
):
    case = observation_case
    _root, resolved, preview, first, _adapter = _published_case(case, tmp_path, monkeypatch)
    selected = preview.nodes[0]
    second_plan = prepare_worldbuilding(WorldbuildingWritePlanPrepareRequest.model_validate({
        "runId": resolved.run_id, "expectedParentRevisionId": first.committed_revision_id,
        "dispositions": [{"assertionId": node.node_id,
                          "decision": "bind_existing" if node.node_id == selected.node_id else "defer",
                          **({"targetNodeId": selected.node_id} if node.node_id == selected.node_id else {})}
                         for node in preview.nodes]
        + [{"assertionId": edge.edge_id, "decision": "defer"} for edge in preview.edges],
    }))
    second = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=second_plan))
    result = get_worldbuilding_publication_coverage(resolved.run_id)
    assert result.status == "published"
    assert len(result.publications) == 2
    assert result.publications[0].published_revision_id == second.committed_revision_id
    assert result.publications[1].published_revision_id == first.committed_revision_id
    selected_coverage = next(row for row in result.candidates if row.candidate_id == selected.node_id)
    assert {fact.facet for fact in selected_coverage.facets} >= {"existence", "description"}
    assert all(not row.unmapped_assertion_ids for row in result.publications)


@pytest.mark.parametrize("mode", ["governs", "source_observations"])
def test_current_profile_relationship_and_distinct_observation_facets(
    observation_case, tmp_path, monkeypatch, mode,
):
    import copy
    from apps.live_control_server.services import source_artifact_registry as registry
    from apps.live_control_server.services.workspace_document_registry import get_workspace_document
    from tests._cutover_d3a_blocker_safe_fixtures import _mutate_extraction_candidate
    from tests.test_worldbuilding_definition_boundaries import source
    from graph_memory.extraction.worldbuilding_definition_observations import compile_definition_observations
    from graph_memory.extraction.category_candidate_graph_extractor import stamp_graph_evidence_refs

    case = observation_case
    root = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id=case["world"])
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(root))
    monkeypatch.setattr(
        "apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding",
        actual_binding,
    )
    register = registry.create_source_artifact_from_workspace_document
    sentence = "Testport Council governs Testport."
    body = sentence if mode == "governs" else "\n\n".join(row["text"] for row in source())

    def register_source(repo, *, document_id, **kwargs):
        document = get_workspace_document(repo, document_id)
        (repo / document.target_relpath).write_text(body + "\n")
        return register(repo, document_id=document_id, **kwargs)

    monkeypatch.setattr(registry, "create_source_artifact_from_workspace_document", register_source)
    run_id, _ = _write_bld08_reviewable_run(root, world_id="publication-managed",
        campaign_id="publication-managed", profile_id="worldbuilding_gazetteer_v1@1.13")
    resolved = resolve_promotable_ingest_run(run_id, root=root)
    index = json.loads(resolved.source_span_index_path.read_text())
    lines = resolved.normalized_recap_path.read_text().splitlines()
    rows = [dict(source_span_ref_id=row["source_span_id"], line_start=row["start_line"],
                 line_end=row["end_line"], text="\n".join(lines[row["start_line"]-1:row["end_line"]]))
            for row in index["spans"]]

    def transform(data):
        if mode == "source_observations":
            place = data["nodes"][1]
            place.update(node_id="place:coast", label="The Coast", node_type="location",
                description="The Coast is named in the livestock heading.",
                evidence_refs=[dict(source_span_ref_id=rows[0]["source_span_ref_id"],
                                    anchor_quotes=[rows[0]["text"]])])
            data["nodes"] = [place]
            data["edges"] = []
            changed, _ = compile_definition_observations(data, rows)
            stamp_graph_evidence_refs(changed, source_artifact_id=resolved.source_artifact_id,
                                      source_ref_id=index["source_ref_id"])
            data.clear()
            data.update(changed)
            return
        reference = dict(source_artifact_id=resolved.source_artifact_id,
            source_ref_id=index["source_ref_id"], source_span_ref_id=rows[0]["source_span_ref_id"],
            source_anchor_id="anchor:" + resolved.source_artifact_id + ":" + rows[0]["source_span_ref_id"],
            anchor_quotes=[sentence], evidence_role="source_evidence", label="Governance",
            can_open_source=True, can_highlight_span=True)
        for node, identifier, label, kind in zip(data["nodes"], ("council", "city"),
                ("Testport Council", "Testport"), ("organization", "location"), strict=True):
            node.update(node_id=identifier, label=label, node_type=kind, description=sentence,
                        evidence_refs=[copy.deepcopy(reference)])
        edge = data["edges"][0]
        edge.update(edge_id="governs", from_node_id="council", to_node_id="city",
                    relationship_type="governs", label=sentence, evidence_refs=[reference])
        data["edges"] = [edge]
        data["version"] = "0.2"
        data["source_observations"] = []

    _mutate_extraction_candidate(root, run_id, transform)
    resolved = resolve_promotable_ingest_run(run_id, root=root)
    preview = load_typed_candidate_graph(json.loads(resolved.candidate_graph_path.read_text()),
                                         allow_source_observations=True)
    parent = case["bundle"].world_graph.get_head(case["world"])
    plan = prepare_worldbuilding(WorldbuildingWritePlanPrepareRequest.model_validate({
        "runId": run_id, "expectedParentRevisionId": parent.head_revision_id,
        "dispositions": [{"assertionId": node.node_id, "decision": "create_new"}
                         for node in preview.nodes]
        + [{"assertionId": edge.edge_id, "decision": "accept"} for edge in preview.edges]
        + [{"assertionId": row.observation_id, "decision": "accept"}
           for row in preview.source_observations],
    }))
    confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=plan))
    result = get_worldbuilding_publication_coverage(run_id)
    assert result.status == "published"
    assert result.publications[0].unmapped_assertion_ids == []
    facets = [fact for row in result.candidates for fact in row.facets]
    assert len([fact for fact in facets if fact.facet == "relationship"]) == (1 if mode == "governs" else 0)
    assert len([fact for fact in facets if fact.facet == "observation"]) == (2 if mode == "source_observations" else 0)
