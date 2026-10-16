"""Independent source-definition producer, codec and review/publication effects."""

from copy import deepcopy
import json
import os

import pytest

from apps.live_control_server.services.managed_world_graph_projection import (
    resolve_managed_world_binding as actual_managed_binding,
)
from apps.live_control_server.models.extract_promote import (
    WorldbuildingWritePlanDecisionSnapshot,
)
from apps.live_control_server.models.world_graph_mutation_context import MutationObject
from graph_memory.candidate_graph_preview import (
    candidate_graph_preview_to_dict,
)
from graph_memory.candidate_graph_to_contribution import (
    CandidateGraphMappingError,
    load_typed_candidate_graph,
)
from graph_memory.extraction.category_candidate_graph_extractor import (
    stamp_graph_evidence_refs,
)
from graph_memory.extraction.worldbuilding_definition_observations import (
    compile_definition_observations,
    PROFILE,
)
from graph_memory.worldbuilding_write_plan import (
    build_worldbuilding_write_plan,
    WorldbuildingWritePlanError,
)
from tests.test_cutover_worldbuilding_authority_port import _memory_context, _preview
from tests.test_recap_source_observation_followup import (
    observation_case as observation_case,
)
from tests.test_worldbuilding_definition_boundaries import source

ARTIFACT = "artifact:worldbuilding:test"


def candidate():
    data = candidate_graph_preview_to_dict(_preview())
    data["nodes"] = [data["nodes"][1]]
    data["nodes"][0].update(
        node_id="place:coast",
        label="The Coast",
        description="The Coast is a region.",
        evidence_refs=[
            {
                "source_span_ref_id": "source:one:span:1",
                "anchor_quotes": ["#### Fantastic Livestock for the Coast"],
            }
        ],
    )
    data["edges"] = []
    data, _ = compile_definition_observations(data, source())
    stamp_graph_evidence_refs(data, source_artifact_id=ARTIFACT)
    return data


def plan(data=None, decisions=None, context=None):
    data = candidate() if data is None else data
    preview = load_typed_candidate_graph(data, allow_source_observations=True)
    context = context or _memory_context()
    decisions = decisions or [
        dict(assertion_id="place:coast", decision="create_new"),
        *[
            dict(assertion_id=o.observation_id, decision="accept")
            for o in preview.source_observations
        ],
    ]
    return build_worldbuilding_write_plan(
        preview=preview,
        mutation_context=context,
        world_id=context.world_id,
        expected_parent_revision_id=context.revision_id,
        run_id="run:definitions",
        source_artifact_id=ARTIFACT,
        source_revision_id="sha256:abc",
        source_uri="repo://Docs/source.md",
        extraction_profile=PROFILE,
        campaign_scope=data.get("campaign_id"),
        dispositions=decisions,
    )


def test_producer_codec_roundtrip_preserves_separate_exact_qualified_definitions(
    tmp_path,
):
    data = candidate()
    path = tmp_path / "candidate.json"
    path.write_text(json.dumps(data))
    typed = load_typed_candidate_graph(
        json.loads(path.read_text()), allow_source_observations=True
    )
    assert typed.version == "0.2"
    assert len(typed.nodes) == 1 and len(typed.source_observations) == 2
    assert "Lantern Sheep" not in typed.nodes[0].description
    assert "River Goats" not in typed.nodes[0].description
    assert "only rumored" in typed.source_observations[0].description
    assert "Lantern Sheep" not in typed.source_observations[1].description
    assert len(typed.source_observations[0].evidence_refs) == 6
    canonical = json.loads(json.dumps(candidate_graph_preview_to_dict(typed)))
    fresh = load_typed_candidate_graph(canonical, allow_source_observations=True)
    assert json.loads(json.dumps(candidate_graph_preview_to_dict(fresh))) == canonical
    assert fresh.source_observations == typed.source_observations
    with pytest.raises(CandidateGraphMappingError, match="source-observation review"):
        load_typed_candidate_graph(data)


def test_v01_serialization_stays_unchanged_and_cannot_hide_observations():
    old = _preview()
    assert "source_observations" not in candidate_graph_preview_to_dict(old)
    bad = candidate()
    bad["version"] = "0.1"
    with pytest.raises(CandidateGraphMappingError):
        load_typed_candidate_graph(bad, allow_source_observations=True)


@pytest.mark.parametrize("bind", [False, True])
def test_new_and_bound_places_receive_distinct_observations_and_effect_ids(bind):
    data = candidate()
    original = deepcopy(data)
    target = "place:coast"
    context = _memory_context()
    subject = dict(assertion_id=target, decision="create_new")
    if bind:
        target = "place:durable"
        obj = MutationObject(
            object_id=target,
            label="The Coast",
            kind="location",
            canon_state="canonical",
            memory_state="graph_read_model",
        )
        context = _memory_context(objects={target: obj})
        subject = dict(
            assertion_id="place:coast", decision="bind_existing", target_node_id=target
        )
    decisions = [
        subject,
        *[
            dict(assertion_id=o["observation_id"], decision="accept")
            for o in data["source_observations"]
        ],
    ]
    result = plan(data, decisions, context)
    effect = result.effect
    observations = [
        a
        for a in effect["accepted_proposals"]
        if a["predicate"] == "worldbuilding_observation"
        and a["label"] in {"Lantern Sheep", "River Goats"}
    ]
    assert len(observations) == 2
    assert {a["subject_node_id"] for a in observations} == {target}
    assert len({a["assertion_id"] for a in observations}) == 2
    assert (
        "only rumored" in observations[0]["value"]["summary"]
        or "only rumored" in observations[1]["value"]["summary"]
    )
    for item in data["source_observations"]:
        assert len(effect["candidate_effect_map"][item["observation_id"]]) == 1
    assert result.plan_digest == plan(data, decisions, context).plan_digest
    snapshots = [
        x
        for x in effect["decision_snapshot"]
        if x["candidate_kind"] == "source_observation"
    ]
    assert len(snapshots) == 2
    for row in snapshots:
        WorldbuildingWritePlanDecisionSnapshot.model_validate(row)
    assert data == original


def test_observations_have_independent_accept_reject_and_defer_decisions():
    data = candidate()
    ids = [o["observation_id"] for o in data["source_observations"]]
    decisions = [
        dict(assertion_id="place:coast", decision="create_new"),
        dict(assertion_id=ids[0], decision="accept"),
        dict(assertion_id=ids[1], decision="reject"),
    ]
    rejected = plan(data, decisions)
    assert any(
        a["label"] == "River Goats" for a in rejected.effect["rejected_assertions"]
    )
    decisions[-1]["decision"] = "defer"
    deferred = plan(data, decisions)
    assert ids[1] in deferred.effect["deferred_candidate_ids"]
    assert deferred.effect["candidate_effect_map"][ids[1]] == []
    assert not any(
        a["label"] == "River Goats" for a in deferred.effect["accepted_proposals"]
    )


@pytest.mark.parametrize("subject_decision", ["reject", "defer"])
def test_observation_cannot_be_accepted_without_accepted_subject(subject_decision):
    data = candidate()
    decisions = [
        dict(assertion_id="place:coast", decision=subject_decision),
        *[
            dict(assertion_id=o["observation_id"], decision="accept")
            for o in data["source_observations"]
        ],
    ]
    with pytest.raises(WorldbuildingWritePlanError, match="accepted subject"):
        plan(data, decisions)


@pytest.mark.parametrize(
    "damage",
    [
        "missing_decision",
        "duplicate_id",
        "foreign_source",
        "missing_subject",
        "empty_refs",
        "qualification",
    ],
)
def test_damaged_or_unreviewed_observations_fail_closed(damage):
    data = candidate()
    decisions = None
    if damage == "missing_decision":
        decisions = [dict(assertion_id="place:coast", decision="create_new")]
    elif damage == "duplicate_id":
        data["source_observations"][1]["observation_id"] = data["source_observations"][
            0
        ]["observation_id"]
    elif damage == "foreign_source":
        data["source_observations"][0]["evidence_refs"][0]["source_artifact_id"] = (
            "foreign:artifact"
        )
    elif damage == "missing_subject":
        data["source_observations"][0]["subject_candidate_node_id"] = "missing:place"
    elif damage == "empty_refs":
        data["source_observations"][0]["evidence_refs"] = []
    else:
        data["source_observations"][0]["semantic_state"]["visibility_state"] = (
            "player_visible"
        )
    with pytest.raises((WorldbuildingWritePlanError, CandidateGraphMappingError)):
        plan(data, decisions)


@pytest.mark.parametrize("profile_version", ["1.11", "1.12", "1.13"])
def test_registered_runner_seals_independent_observations_and_reloads(
    tmp_path, application_state_dsn, monkeypatch, profile_version
):
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(tmp_path))
    monkeypatch.setattr(
        "apps.live_control_server.services.extract_promote.repo_root", lambda: tmp_path
    )
    from types import SimpleNamespace
    from tests.test_graph_preview_runner import _admit_worldbuilding
    from src.graph_memory.extraction.graph_preview_runner import (
        ProductionExtractionRequest,
        run_production_extraction,
    )
    from src.graph_memory.extraction.bounded_recap_execution import (
        BoundedRecapPassClient,
        DEEPSEEK_MODEL,
    )
    from apps.live_control_server.services.graph_run_registry import (
        get_reviewable_extraction_run,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from apps.live_control_server.services.extract_promote import (
        _load_typed_worldbuilding_preview_for_run,
    )

    text = "\n\n".join(row["text"] for row in source()) + "\n"
    admitted = _admit_worldbuilding(tmp_path, text)
    span = admitted.source_span_index["spans"][0]["source_span_id"]

    class Fixture(BoundedRecapPassClient):
        def __init__(self):
            self.limits = SimpleNamespace(
                provider="openrouter", model=DEEPSEEK_MODEL, max_calls=8
            )
            self.calls = []

        def run_pass(self, pass_name, **kwargs):
            nodes = []
            if pass_name == "location_pass":
                nodes = [
                    dict(
                        node_id="place:coast",
                        label="The Coast",
                        node_type="location",
                        description="The Coast is named in the livestock heading.",
                        importance="high",
                        evidence_refs=[
                            dict(
                                source_span_ref_id=span,
                                anchor_quotes=[source()[0]["text"]],
                            )
                        ],
                    )
                ]
            parsed = (
                {"observation_edges": []}
                if pass_name == "edge_pass"
                else {
                    "observation_nodes": nodes,
                    "ignored_candidates": [],
                    "deferred_candidates": [],
                }
            )
            self.calls.append(
                dict(
                    pass_name=pass_name,
                    external_outcome="not_started",
                    observation=None,
                    attempt_evidence=[],
                )
            )
            return dict(
                parsed=parsed,
                cost_usd=0.0,
                usage={},
                elapsed_ms=1,
                response_id=pass_name,
            )

    result = run_production_extraction(
        ProductionExtractionRequest(
            repo_root=tmp_path,
            source=admitted,
            profile_id="worldbuilding_gazetteer_v1",
            profile_version=profile_version,
            allow_llm=True,
            model_id=DEEPSEEK_MODEL,
            category_client=Fixture(),
            output_dir=tmp_path / "observations-run",
        )
    )
    assert result.failure_kind is None, result.diagnostics
    run = get_reviewable_extraction_run(tmp_path, result.run.run_id)
    assert run.profile_id == f"worldbuilding_gazetteer_v1@{profile_version}"
    resolved = resolve_promotable_ingest_run(run.run_id, root=tmp_path)
    typed, _ = _load_typed_worldbuilding_preview_for_run(resolved)
    assert len(typed.source_observations) == 2
    assert all(
        o.evidence_refs and all(r.can_open_source for r in o.evidence_refs)
        for o in typed.source_observations
    )
    assert run.components["candidate_graph"].sha256
    from apps.live_control_server.services.extract_promote import (
        get_exact_run_review_package,
    )

    review = get_exact_run_review_package(run.run_id)
    observed = [o for o in review.assertions if o.kind == "source_observation"]
    assert len(observed) == 2 and all(
        o.subject_candidate_node_id == "place:coast" for o in observed
    )
    from apps.live_control_server.services.extract_promote import (
        _assert_and_project_candidate_evidence,
        ExtractPromoteError,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        load_source_span_index,
    )

    damaged = deepcopy(result.candidate_graph)
    damaged["source_observations"][0]["evidence_refs"][0]["anchor_quotes"] = [
        "A forged unsupported claim."
    ]
    with pytest.raises(ExtractPromoteError, match="anchor quote"):
        _assert_and_project_candidate_evidence(
            candidate_payload=damaged,
            source_prose=admitted.source_text,
            source_artifact_id=admitted.source_artifact_id,
            span_index=load_source_span_index(tmp_path, admitted.source_artifact_id),
            allow_source_observations=True,
        )

    damaged = deepcopy(result.candidate_graph)
    damaged["source_observations"][0]["evidence_refs"][0]["source_span_ref_id"] = (
        "missing:source:span"
    )
    with pytest.raises(ExtractPromoteError, match="unknown"):
        _assert_and_project_candidate_evidence(
            candidate_payload=damaged,
            source_prose=admitted.source_text,
            source_artifact_id=admitted.source_artifact_id,
            span_index=load_source_span_index(tmp_path, admitted.source_artifact_id),
            allow_source_observations=True,
        )


@pytest.mark.skipif(
    not os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL"),
    reason="dedicated disposable Core required",
)
@pytest.mark.parametrize("bind_first", [False, True])
def test_native_confirm_retains_distinct_observations_sources_and_idempotency(
    observation_case, tmp_path, monkeypatch, bind_first
):
    from tests.test_cutover_worldbuilding_authority_port import (
        _install_worldbuilding_repo,
    )
    from tests._cutover_d3a_blocker_safe_fixtures import (
        _write_bld08_reviewable_run,
        _mutate_extraction_candidate,
    )
    from apps.live_control_server.services import source_artifact_registry as registry
    from apps.live_control_server.services.workspace_document_registry import (
        get_workspace_document,
    )
    from apps.live_control_server.services.promotable_ingest_run import (
        resolve_promotable_ingest_run,
    )
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        prepare_worldbuilding,
        confirm_worldbuilding,
    )
    from apps.live_control_server.services.managed_world_graph_projection import (
        resolve_managed_world_binding,
    )
    from apps.live_control_server.models.extract_promote import (
        WorldbuildingWritePlanPrepareRequest,
        WorldbuildingWritePlanConfirmRequest,
    )
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_reads as direct,
    )
    from apps.live_control_server.services.world_graph_retrieval import (
        read_source_anchor_internal_v2,
    )
    from graph_memory.retrieval.models import (
        WorldGraphObjectRequest,
        WorldGraphSourceAnchorReadRequest,
    )
    from graph_memory.source_span import source_span_index_to_dict

    case = observation_case
    root = _install_worldbuilding_repo(monkeypatch, tmp_path, native_id=case["world"])
    monkeypatch.setenv("DMB_ARTIFACT_DATA_ROOT", str(root))
    monkeypatch.setattr(
        "apps.live_control_server.services.managed_world_graph_projection.resolve_managed_world_binding",
        resolve_managed_world_binding,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.extract_promote.resolve_managed_world_binding",
        resolve_managed_world_binding,
    )
    monkeypatch.setattr(
        "apps.live_control_server.services.worldbuilding_graph_publication.resolve_managed_world_binding",
        actual_managed_binding,
    )
    original_register = registry.create_source_artifact_from_workspace_document

    def register(repo, *, document_id, **kwargs):
        document = get_workspace_document(repo, document_id)
        (repo / document.target_relpath).write_text(
            "\n\n".join(row["text"] for row in source())
            + "\nFixture document: "
            + document_id
            + "\n"
        )
        return original_register(repo, document_id=document_id, **kwargs)

    monkeypatch.setattr(
        registry, "create_source_artifact_from_workspace_document", register
    )
    run_id, _ = _write_bld08_reviewable_run(
        root,
        profile_id=PROFILE,
        campaign_id="publication-managed",
        world_id="publication-managed",
    )
    resolved = resolve_promotable_ingest_run(run_id, root=root)
    text = resolved.normalized_recap_path.read_text()
    lines = text.splitlines()
    index = source_span_index_to_dict(
        registry.load_source_span_index(root, resolved.source_artifact_id)
    )
    rows = [
        dict(
            source_span_ref_id=s["source_span_id"],
            line_start=s["start_line"],
            line_end=s["end_line"],
            text="\n".join(lines[s["start_line"] - 1 : s["end_line"]]),
        )
        for s in index["spans"]
    ]

    def transform(data):
        place = data["nodes"][1]
        place.update(
            node_id="place:coast",
            label="The Coast",
            description="The Coast is named in the livestock heading.",
            node_type="location",
            evidence_refs=[
                dict(
                    source_span_ref_id=rows[0]["source_span_ref_id"],
                    anchor_quotes=[rows[0]["text"]],
                )
            ],
        )
        data["nodes"] = [place]
        data["edges"] = []
        changed, _ = compile_definition_observations(data, rows)
        stamp_graph_evidence_refs(
            changed,
            source_artifact_id=resolved.source_artifact_id,
            source_ref_id=index["source_ref_id"],
        )
        data.clear()
        data.update(changed)

    _mutate_extraction_candidate(root, run_id, transform)
    refreshed = resolve_promotable_ingest_run(run_id, root=root)
    data = json.loads(refreshed.candidate_graph_path.read_text())
    parent = case["bundle"].world_graph.get_head(case["world"])
    decisions = [
        dict(assertionId="place:coast", decision="create_new"),
        *[
            dict(assertionId=o["observation_id"], decision="accept")
            for o in data["source_observations"]
        ],
    ]
    if bind_first:
        seed_decisions = [
            dict(assertionId="place:coast", decision="create_new"),
            *[
                dict(assertionId=o["observation_id"], decision="defer")
                for o in data["source_observations"]
            ],
        ]
        seed = prepare_worldbuilding(
            WorldbuildingWritePlanPrepareRequest.model_validate(
                dict(
                    runId=run_id,
                    expectedParentRevisionId=parent.head_revision_id,
                    dispositions=seed_decisions,
                )
            )
        )
        confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=seed))
        parent = case["bundle"].world_graph.get_head(case["world"])
        decisions[0] = dict(
            assertionId="place:coast",
            decision="bind_existing",
            targetNodeId=seed.effect.node_id_map["place:coast"],
        )
    prepared = prepare_worldbuilding(
        WorldbuildingWritePlanPrepareRequest.model_validate(
            dict(
                runId=run_id,
                expectedParentRevisionId=parent.head_revision_id,
                dispositions=decisions,
            )
        )
    )
    receipt = confirm_worldbuilding(WorldbuildingWritePlanConfirmRequest(plan=prepared))
    repeated = confirm_worldbuilding(
        WorldbuildingWritePlanConfirmRequest(plan=prepared)
    )
    assert repeated.committed_revision_id == receipt.committed_revision_id
    old_payload = (
        case["bundle"]
        .world_graph.get_revision(case["world"], parent.head_revision_id)
        .graph_payload
    )
    new_payload = (
        case["bundle"]
        .world_graph.get_revision(case["world"], receipt.committed_revision_id)
        .graph_payload
    )
    for existing in old_payload["objects"]:
        assert (
            next(
                o
                for o in new_payload["objects"]
                if o["object_id"] == existing["object_id"]
            )
            == existing
        )
    assert old_payload["relationships"] == new_payload["relationships"]
    services = direct.direct_services_from_config(case["world"])
    context = dict(
        worldId=case["world"],
        campaignId="",
        scopeMode="world",
        focus={},
        admissibility="gm",
        revisionPin=receipt.committed_revision_id,
    )
    obj = direct.get_object_with_reviewed_sources_direct_v3(
        services,
        WorldGraphObjectRequest.model_validate(
            {
                **context,
                "schema": "dmb_world_graph_object_request_v1",
                "nodeId": prepared.effect.node_id_map["place:coast"],
            }
        ),
    )
    expected_ids = {
        identifier
        for record in data["source_observations"]
        for identifier in prepared.effect.candidate_effect_map[record["observation_id"]]
    }
    observations = [
        o for o in obj.reviewed_source_observations if o.assertion_id in expected_ids
    ]
    assert len(observations) == 2
    assert not obj.observation_gap_codes
    assert len({o.assertion_id for o in observations}) == 2
    for observation in observations:
        assert observation.source_artifact_id == resolved.source_artifact_id
        anchor = next(
            a
            for a in obj.result.source_anchors
            if observation.assertion_id in a.supporting_assertion_ids
        )
        opened = read_source_anchor_internal_v2(
            WorldGraphSourceAnchorReadRequest.model_validate(
                {
                    **context,
                    "schema": "dmb_world_graph_source_anchor_read_request_v1",
                    "anchorId": anchor.anchor_id,
                    "maxChars": 4000,
                }
            ),
            repo_root=root,
        )
        assert opened.result.outcome == "enough"
