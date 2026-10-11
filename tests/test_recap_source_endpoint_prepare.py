"""Actual partial history -> mixed reconciliation -> native/Harness/source proof."""

import copy
import os
import pytest

from tests.test_recap_source_observation_followup import (
    observation_case as observation_case,
    review_and_confirm,
)
from apps.live_control_server.services.recap_source_endpoint_prepare import (
    HistoricalEndpointReference,
    prepare_source_proven_endpoints,
    reprove_source_proven_endpoints,
    SourceProvenEndpointError,
)
from apps.live_control_server.services.graph_object_authoring_prepare import (
    GraphObjectAuthoringObjectRefPayload,
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
    RETRIEVAL_OBJECT_REQUEST_SCHEMA,
    RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
)
from graph_memory.interaction.session import GraphRetrievalSession, SessionSnapshot
from graph_memory.interaction.session_store import clear_sessions, create_session
from graph_memory.interaction.expansion_executor import execute_expand_graph_retrieval
from graph_memory.extract_promote_proposal import (
    compute_proposal_digest,
    validate_recap_source_observation_basis,
)

pytestmark = pytest.mark.skipif(
    not os.environ.get("DMB_RECAP_OBSERVATION_TEST_DATABASE_URL"),
    reason="dedicated disposable Core fixture required",
)


def historical(case):
    old = case["package"]
    node = next(
        a
        for a in old["effect"]["accepted_proposals"]
        if a["assertion_kind"] == "node" and a["label"] == "The Annex"
    )
    description = next(
        a
        for a in old["effect"]["accepted_proposals"]
        if a["assertion_kind"] == "attribute"
        and a["subject_node_id"] == node["subject_node_id"]
    )
    receipt, package_bytes, _ = review_and_confirm(
        case, old, [node["assertion_id"], description["assertion_id"]]
    )
    ref = HistoricalEndpointReference(
        raw_node_id="loc_annex",
        subject=GraphObjectAuthoringObjectRefPayload(
            refKind="existing_graph_node",
            nodeId=node["subject_node_id"],
            label="no label authority",
            kind="location",
        ),
        publication_revision_id=receipt["committed_revision_id"],
        package_bytes=package_bytes,
    )
    return ref, receipt


def prepare(case, ref, *, new=("npc_mira",), edges=True):
    return prepare_source_proven_endpoints(
        bundle=case["bundle"],
        managed_world_id="managed-test",
        source_run_id=case["run_id"],
        endpoints=[ref],
        new_node_ids=list(new),
        repo_root=case["root"],
        include_edges=edges,
    )


@pytest.mark.parametrize("observation_case", ["source_endpoint"], indirect=True)
def test_real_mixed_package_publication_relationship_and_source(observation_case):
    case = observation_case
    ref, old_receipt = historical(case)
    bundle = case["bundle"]
    parent = bundle.world_graph.get_revision(
        case["world"], old_receipt["committed_revision_id"]
    ).graph_payload
    original_bytes = case["candidate"].read_bytes()
    prepared = prepare(case, ref)
    effect = prepared["review_package"]["effect"]
    assert effect["node_id_map"]["loc_annex"] == ref.subject.node_id
    assert (
        effect["identity_basis"]["nodes"]["loc_annex"]["classification"]
        == "source_proven_endpoint"
    )
    assert not any(
        a["assertion_kind"] != "edge" and a["subject_node_id"] == ref.subject.node_id
        for a in effect["accepted_proposals"]
    )
    node = next(
        a for a in effect["accepted_proposals"] if a["assertion_kind"] == "node"
    )
    edge = next(
        a for a in effect["accepted_proposals"] if a["assertion_kind"] == "edge"
    )
    assert (
        edge["subject_node_id"] == node["subject_node_id"]
        and edge["target_node_id"] == ref.subject.node_id
    )
    assert case["candidate"].read_bytes() == original_bytes
    receipt, _, kwargs = review_and_confirm(
        case, prepared["review_package"], [node["assertion_id"], edge["assertion_id"]]
    )
    child = bundle.world_graph.get_revision(
        case["world"], receipt["committed_revision_id"]
    ).graph_payload
    for obj in parent["objects"]:
        assert (
            next(n for n in child["objects"] if n["object_id"] == obj["object_id"])
            == obj
        )
    for relation in parent["relationships"]:
        assert (
            next(
                r
                for r in child["relationships"]
                if r["relationship_id"] == relation["relationship_id"]
            )
            == relation
        )
    assert len(child["objects"]) == len(parent["objects"]) + 1
    assert len(child["relationships"]) == len(parent["relationships"]) + 1
    from apps.live_control_server.services.reviewed_extract_confirmation import (
        confirm_reviewed_extract,
    )

    assert confirm_reviewed_extract(**kwargs)["outcome"] == "already_applied"
    services = direct.direct_services_from_config(case["world"])
    ctx = {
        "worldId": case["world"],
        "campaignId": "longmont-c2",
        "revisionPin": receipt["committed_revision_id"],
        "admissibility": "gm",
        "focus": {
            "kind": "session",
            "sessionId": "session-22",
            "campaignId": "longmont-c2",
        },
    }
    request = WorldGraphObjectRequest.model_validate(
        {
            **ctx,
            "schema": RETRIEVAL_OBJECT_REQUEST_SCHEMA,
            "nodeId": node["subject_node_id"],
        }
    )
    native = services.retrieval.get_complete_object(
        direct._map_retrieval_context(request, services.binding),
        object_id=node["subject_node_id"],
    )
    assert native.found and len(native.relationships) == 1
    assert native.relationships[0].subject_object_id == node["subject_node_id"]
    assert native.relationships[0].object_object_id == ref.subject.node_id
    assert (
        native.reviewed_source_observations == ()
    )  # New description stayed default-off/unselected.
    clear_sessions()
    try:
        session = GraphRetrievalSession(
            snapshot=SessionSnapshot(
                world_id=case["world"],
                campaign_id="longmont-c2",
                revision_id=receipt["committed_revision_id"],
                focus=ctx["focus"],
            ),
            question="Where does the clerk work?",
            preflight_candidate_ids=[node["subject_node_id"]],
        )
        create_session(session)
        result = execute_expand_graph_retrieval(
            {
                "schema": "dmb_expand_graph_retrieval_request_v1",
                "retrievalSessionId": session.id,
                "operation": "object",
                "targets": [{"kind": "node", "id": node["subject_node_id"]}],
            }
        )
        assert result["relationships"][0]["targetNodeId"] == ref.subject.node_id
        assert result["relationships"][0]["sessionIds"] == ["session-22"]
        for anchor in result["sourceAnchors"]:
            opened = read_source_anchor_internal_v2(
                WorldGraphSourceAnchorReadRequest.model_validate(
                    {
                        **ctx,
                        "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                        "anchorId": anchor["anchorId"],
                        "maxChars": 4000,
                    }
                ),
                repo_root=case["root"],
            )
            assert opened.source_revision_sha256 == case["artifact"].content_sha256
            assert opened.result.outcome == "enough"
        assert any(
            "Clerk Mira works in the Annex."
            in read_source_anchor_internal_v2(
                WorldGraphSourceAnchorReadRequest.model_validate(
                    {
                        **ctx,
                        "schema": RETRIEVAL_SOURCE_ANCHOR_READ_REQUEST_SCHEMA,
                        "anchorId": a["anchorId"],
                        "maxChars": 4000,
                    }
                ),
                repo_root=case["root"],
            ).result.content
            for a in result["sourceAnchors"]
        )
    finally:
        clear_sessions()


@pytest.mark.parametrize("observation_case", ["source_endpoint"], indirect=True)
def test_binding_only_and_missing_new_node_selection(observation_case):
    case = observation_case
    ref, _ = historical(case)
    before = authority_snapshot(case)
    only = prepare(case, ref, new=(), edges=False)
    assert not only["review_package"]["effect"]["accepted_proposals"]
    assert not only["confirmable"]
    assert authority_snapshot(case) == before
    mixed = prepare(case, ref)
    edge = next(
        a
        for a in mixed["review_package"]["effect"]["accepted_proposals"]
        if a["assertion_kind"] == "edge"
    )
    with pytest.raises(ValueError, match="endpoint"):
        review_and_confirm(case, mixed["review_package"], [edge["assertion_id"]])
    altered = copy.deepcopy(mixed["review_package"]["effect"])
    altered["recap_source_observation_basis"] = {
        "schema": "dmb_recap_source_observation_basis_v1",
        "world_id": case["world"],
        "parent_revision_id": altered["parent_revision_id"],
        "subjects": [
            {
                "observation_assertion_id": edge["assertion_id"],
                "subject_id": edge["subject_node_id"],
            }
        ],
    }
    with pytest.raises(ValueError):
        validate_recap_source_observation_basis(altered)


@pytest.mark.parametrize("observation_case", ["source_endpoint"], indirect=True)
@pytest.mark.parametrize(
    "drift", ["map", "package", "source", "candidate", "span", "kind", "nonancestor"]
)
def test_endpoint_proof_rejects_forged_or_changed_basis(observation_case, drift):
    from dataclasses import replace

    case = observation_case
    ref, _ = historical(case)
    if drift == "map":
        ref = replace(ref, raw_node_id="npc_mira")
    elif drift == "package":
        ref = replace(ref, package_bytes=ref.package_bytes + b" ")
    elif drift == "kind":
        ref.subject.kind = "npc"
    elif drift == "nonancestor":
        ref = replace(ref, publication_revision_id="rev:nonancestor")
    elif drift == "source":
        (case["root"] / case["artifact"].uri.removeprefix("repo://")).write_text(
            "changed"
        )
    elif drift == "candidate":
        case["candidate"].write_text(case["candidate"].read_text() + " ")
    else:
        case["span"].write_text(case["span"].read_text() + " ")
    before = authority_snapshot(case)
    with pytest.raises(ValueError):
        prepare(case, ref)
    assert authority_snapshot(case) == before


@pytest.mark.parametrize("observation_case", ["source_endpoint"], indirect=True)
def test_resealed_endpoint_override_still_requires_history(observation_case):
    case = observation_case
    ref, _ = historical(case)
    prepared = prepare(case, ref)
    package = copy.deepcopy(prepared["review_package"])
    row = package["effect"]["source_proven_endpoint_basis"]["subjects"][0]
    row["subject_id"] = "unproven"
    package["effect"]["node_id_map"]["loc_annex"] = "unproven"
    package["proposal_digest"] = compute_proposal_digest(package["effect"])
    with pytest.raises((SourceProvenEndpointError, ValueError)):
        reprove_source_proven_endpoints(
            bundle=case["bundle"], package=package, repo_root=case["root"]
        )


def authority_snapshot(case):
    """Every persisted Core row, not merely head, must remain unchanged."""
    from psycopg import sql
    from dungeonmind.infrastructure.postgres import PostgresDatabase

    with PostgresDatabase(case["dsn"]).connect() as conn:
        tables = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='dungeonmind' ORDER BY tablename"
        ).fetchall()
        assert {
            "graph_revisions",
            "contribution_reviews",
            "finalized_review_publications",
            "world_graph_heads",
        } <= {row["tablename"] for row in tables}
        return {
            row["tablename"]: conn.execute(
                sql.SQL(
                    "SELECT to_jsonb(t)::text AS value FROM {} t ORDER BY value"
                ).format(sql.Identifier("dungeonmind", row["tablename"]))
            ).fetchall()
            for row in tables
        }


def advance_parent(case):
    from dungeonmind.contracts.graph import PublishRevisionCommand
    from tests._cutover_direct_dungeonmind_read_helpers import NOW

    graph = case["bundle"].world_graph
    head = graph.get_head(case["world"]).head_revision_id
    return graph.publish_revision(
        PublishRevisionCommand(
            world_id=case["world"],
            parent_revision_id=head,
            expected_parent_revision_id=head,
            operation_ids=["test:advance-endpoint-parent"],
            graph_schema="dm_union_graph_v6",
            graph_payload=graph.get_revision(case["world"], head).graph_payload,
            created_at=NOW,
        )
    )


@pytest.mark.parametrize("observation_case", ["source_endpoint"], indirect=True)
@pytest.mark.parametrize("drift", ["origin", "fingerprint", "inactive", "redirected"])
def test_confirm_reproves_current_subject_without_partial_effects(
    observation_case, monkeypatch, drift
):
    """Inject drift at read ports after preparation; keep the writer and DB real."""
    from dataclasses import replace
    from types import SimpleNamespace
    from dungeonmind.domain.canonical import canonical_sha256
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_writes as writes,
    )
    from apps.live_control_server.services import (
        recap_source_endpoint_prepare as endpoints,
    )
    from apps.live_control_server.services.reviewed_extract_confirmation import (
        confirm_reviewed_extract,
    )

    case = observation_case
    ref, _ = historical(case)
    advance_parent(
        case
    )  # Separate immutable historical publication from current parent.
    package = prepare(case, ref)["review_package"]
    selected = [
        a["assertion_id"]
        for a in package["effect"]["accepted_proposals"]
        if a["assertion_kind"] in {"node", "edge"}
    ]
    _, _, kwargs = review_and_confirm(case, package, selected, confirm=False)
    before = authority_snapshot(case)
    proven = endpoints.prove_source_subject

    if drift in {"origin", "fingerprint"}:

        def changed_read(**arguments):
            bundle = arguments["bundle"]
            graph = bundle.world_graph

            def get_revision(world, revision):
                stored = graph.get_revision(world, revision)
                if revision != arguments["parent_id"]:
                    return stored
                payload = copy.deepcopy(stored.graph_payload)
                obj = next(
                    n
                    for n in payload["objects"]
                    if n["object_id"] == ref.subject.node_id
                )
                if drift == "origin":
                    obj["assertion_metadata"]["assertion_id"] = (
                        "assertion:unproved-origin"
                    )
                else:
                    obj["label"] = "changed current subject fingerprint"
                return stored.model_copy(
                    update={
                        "graph_payload": payload,
                        "revision": stored.revision.model_copy(
                            update={"graph_payload_sha256": canonical_sha256(payload)}
                        ),
                    }
                )

            proxy = SimpleNamespace(
                world_graph=SimpleNamespace(get_revision=get_revision),
                finalized_review_publications=bundle.finalized_review_publications,
                contribution_reviews=bundle.contribution_reviews,
                sources=bundle.sources,
                identity_decisions=bundle.identity_decisions,
            )
            # Native complete-read authority stays real; only the revision read is faulted.
            real_direct = direct.direct_services_from_bundle
            with monkeypatch.context() as local:
                local.setattr(
                    direct,
                    "direct_services_from_bundle",
                    lambda *_: real_direct(bundle, case["world"]),
                )
                return proven(**{**arguments, "bundle": proxy})

        monkeypatch.setattr(endpoints, "prove_source_subject", changed_read)
    elif drift == "inactive":
        real_direct = direct.direct_services_from_bundle

        def inactive_read(bundle, world):
            services = real_direct(bundle, world)
            retrieve = services.retrieval.get_complete_object
            return SimpleNamespace(
                binding=services.binding,
                retrieval=SimpleNamespace(
                    get_complete_object=lambda *a, **k: replace(
                        retrieve(*a, **k), found=False
                    )
                ),
            )

        def inactive_proof(**arguments):
            with monkeypatch.context() as local:
                local.setattr(direct, "direct_services_from_bundle", inactive_read)
                return proven(**arguments)

        monkeypatch.setattr(endpoints, "prove_source_subject", inactive_proof)
    else:
        build = writes.mutation_context_from_revision_payload

        def redirected_read(*args, **kwargs):
            context = build(*args, **kwargs)
            return replace(
                context,
                identity_redirects={ref.subject.node_id: "node:redirect-target"},
            )

        def redirected_proof(**arguments):
            with monkeypatch.context() as local:
                local.setattr(
                    writes, "mutation_context_from_revision_payload", redirected_read
                )
                return proven(**arguments)

        monkeypatch.setattr(endpoints, "prove_source_subject", redirected_proof)

    with pytest.raises(writes.WorldGraphWriteError) as error:
        confirm_reviewed_extract(**kwargs)
    assert error.value.code == "governed_write_source_endpoint_drift"
    assert authority_snapshot(case) == before


@pytest.mark.parametrize("observation_case", ["source_endpoint"], indirect=True)
def test_confirm_rejects_actual_advanced_parent_without_partial_effects(
    observation_case,
):
    from apps.live_control_server.integrations.dungeonmind import (
        world_graph_writes as writes,
    )
    from apps.live_control_server.services.reviewed_extract_confirmation import (
        confirm_reviewed_extract,
    )

    case = observation_case
    ref, _ = historical(case)
    package = prepare(case, ref)["review_package"]
    selected = [
        a["assertion_id"]
        for a in package["effect"]["accepted_proposals"]
        if a["assertion_kind"] in {"node", "edge"}
    ]
    _, _, kwargs = review_and_confirm(case, package, selected, confirm=False)
    advance_parent(case)
    before = authority_snapshot(case)
    with pytest.raises(writes.WorldGraphWriteError) as error:
        confirm_reviewed_extract(**kwargs)
    assert error.value.code == "governed_write_stale_parent"
    assert authority_snapshot(case) == before
