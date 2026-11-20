from types import SimpleNamespace

import pytest

from apps.live_control_server.services import guest_release_native_graph as reader


def test_native_reader_pins_player_audience_and_rechecks_binding(monkeypatch):
    binding = SimpleNamespace(native_world_id="native", binding_version=1)
    monkeypatch.setattr(reader, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(reader.native_registry_source, "read_repository", lambda: SimpleNamespace(
        get_head=lambda _: SimpleNamespace(head_revision_id="head")))
    calls = []
    access = SimpleNamespace(source_view=SimpleNamespace(epoch=7))
    def context(repo, world, revision, campaign, **kwargs):
        calls.append((world, revision, campaign, kwargs))
        return "context", access, None, None
    monkeypatch.setattr(reader.native_registry_source, "read_context", context)
    support = SimpleNamespace(listing=SimpleNamespace(identity=SimpleNamespace(revision_id="selected")))
    monkeypatch.setattr(reader, "EntityReadService", lambda: SimpleNamespace(list_entities_with_support=lambda _: support))
    monkeypatch.setattr(reader, "project_native_world", lambda context, support, snapshot, **kwargs: snapshot)
    actual_binding, projection, _ = reader.read_player_graph(managed_world_id="managed", revision_id="selected")
    assert actual_binding == binding and projection.admissibility == "player"
    assert calls == [("native", "selected", None, {"role": "player", "scope_mode": "world"}),
                     ("native", "selected", None, {"role": "gm", "scope_mode": "world"})]


def test_native_reader_rejects_binding_change(monkeypatch):
    bindings = iter([SimpleNamespace(native_world_id="native", binding_version=1),
                     SimpleNamespace(native_world_id="native", binding_version=2)])
    monkeypatch.setattr(reader, "resolve_managed_world_binding", lambda _: next(bindings))
    monkeypatch.setattr(reader.native_registry_source, "read_repository", lambda: SimpleNamespace(
        get_head=lambda _: SimpleNamespace(head_revision_id="selected")))
    access = SimpleNamespace(source_view=SimpleNamespace(epoch=7))
    monkeypatch.setattr(reader.native_registry_source, "read_context", lambda *a, **k: ("context", access, None, None))
    support = SimpleNamespace(listing=SimpleNamespace(identity=SimpleNamespace(revision_id="selected")))
    monkeypatch.setattr(reader, "EntityReadService", lambda: SimpleNamespace(list_entities_with_support=lambda _: support))
    monkeypatch.setattr(reader, "project_native_world", lambda *a, **k: "projection")
    with pytest.raises(reader.GuestNativeGraphError):
        reader.read_player_graph(managed_world_id="managed", revision_id="selected")


def test_native_reader_rejects_source_epoch_change_between_audiences(monkeypatch):
    binding = SimpleNamespace(native_world_id="native", binding_version=1)
    monkeypatch.setattr(reader, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(reader.native_registry_source, "read_repository", lambda: SimpleNamespace(
        get_head=lambda _: SimpleNamespace(head_revision_id="selected")))
    epochs = iter([7, 8])
    monkeypatch.setattr(reader.native_registry_source, "read_context", lambda *a, **k:
        ("context", SimpleNamespace(source_view=SimpleNamespace(epoch=next(epochs))), None, None))
    support = SimpleNamespace(listing=SimpleNamespace(identity=SimpleNamespace(revision_id="selected")))
    monkeypatch.setattr(reader, "EntityReadService", lambda: SimpleNamespace(list_entities_with_support=lambda _: support))
    monkeypatch.setattr(reader, "project_native_world", lambda *a, **k: "projection")
    with pytest.raises(reader.GuestNativeGraphError, match="authority changed"):
        reader.read_player_graph(managed_world_id="managed", revision_id="selected")


def test_native_reader_excludes_real_gm_only_fixture(monkeypatch):
    from tests.test_governed_native_source_publication_adoption import exercise, setup

    fixture = setup()
    _, receipt = exercise(fixture, "new_intervals", primary=False)
    revision = receipt.publication_receipt.published_revision_id
    binding = SimpleNamespace(native_world_id=fixture.space, binding_version=1)
    monkeypatch.setattr(reader, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(reader.native_registry_source, "read_repository", lambda: fixture.repo)
    _, projection, _ = reader.read_player_graph(managed_world_id="managed", revision_id=revision)
    assert projection.snapshot.revision_id == revision and projection.snapshot.admissibility == "player"
    assert not projection.nodes and not projection.relationships


def test_real_player_projection_rejects_entity_with_gm_only_name():
    import json
    from pathlib import Path
    from dungeonmind.application.vnext import EntityReadService
    from graph_memory.vnext import DungeonBuddyVNextProjectionInput, build_dungeonbuddy_read_context
    from graph_memory.projection.world_projection import WorldGraphProjectionEvidenceView, WorldGraphProjectionSourceArtifactView
    from apps.live_control_server.integrations.dungeonmind.vnext_world_projection import project_assertion_views, project_node_views
    from apps.live_control_server.services.guest_release_projection import GuestReleaseProjectionError, project_selected_graph
    from tests.test_v6_2_vnext_complete_object_adapter import _runtime

    fixture = json.loads((Path(__file__).parent / "fixtures/vnext/dungeonbuddy_domain_runtime_preservation_v2.json").read_text())
    for assertion in fixture["assertions"]:
        if assertion["assertion_id"] == "as:brennan-name":
            assertion["metadata"]["visibility"] = {"kind": "labels_any", "labels": ["dungeonbuddy.visibility:gm"]}
    parsed, source_reader = _runtime(fixture)
    context = build_dungeonbuddy_read_context(parsed_revision=parsed,
        projection_input=DungeonBuddyVNextProjectionInput(world_id=parsed.space_id, revision_id=parsed.revision_id,
                                                          scope_mode="world", role="player"), source_reader=source_reader)
    support = EntityReadService().list_entities_with_support(context)
    artifacts = [WorldGraphProjectionSourceArtifactView(source_artifact_id=x, source_domain="recap", uri="", campaign_id="")
                 for x in {item.source_artifact_id for item in support.evidence}]
    evidence = [WorldGraphProjectionEvidenceView(evidence_ref_id=e.evidence_ref_id,
        source_artifact_id=e.source_artifact_id, source_domain="recap") for e in support.evidence]
    _, relationships, by_entity = project_assertion_views(context, support, artifacts, evidence)
    nodes = project_node_views(support, by_entity, artifacts, evidence)
    target = next(node for node in nodes if node.node_id == "entity:npc:brennan-tallow")
    assert target.label == target.node_id
    from tests.test_guest_release_projection import _projection
    projection = _projection().model_copy(update={"nodes": nodes, "relationships": relationships})
    with pytest.raises(GuestReleaseProjectionError):
        project_selected_graph(projection, expected_world_id="private-world", expected_revision="private-revision",
                               selected_node_ids={target.node_id}, selected_edge_ids=set())


def test_player_projection_excludes_assertions_backed_only_by_gm_source(monkeypatch):
    from dataclasses import replace
    from tests import test_governed_native_source_publication_adoption as fixture
    from graph_memory.vnext.domain_runtime import PLAYER_LABEL

    case = fixture.setup()
    original_metadata = fixture.metadata
    def player_metadata(evidence, *, label="reviewed fact"):
        return replace(original_metadata(evidence, label=label),
                       visibility=fixture.wk.Visibility("labels_any", (PLAYER_LABEL,)))
    monkeypatch.setattr(fixture, "metadata", player_metadata)
    request = fixture.request(case, fixture.basis(case, "new_intervals", "publication:player-assertions"))
    receipt = fixture.publish(case, request)
    revision = receipt.publication_receipt.published_revision_id
    binding = SimpleNamespace(native_world_id=case.space, binding_version=1)
    monkeypatch.setattr(reader, "resolve_managed_world_binding", lambda _: binding)
    monkeypatch.setattr(reader.native_registry_source, "read_repository", lambda: case.repo)
    _, projection, owner_access = reader.read_player_graph(managed_world_id="managed", revision_id=revision)
    # Core's player projection requires player-admissible evidence as well as
    # player-visible assertions. Current first-World sources are GM-only.
    assert not projection.nodes
    assert owner_access.source_view.epoch >= 0
    _, owner_context, owner_support, _ = reader.read_owner_graph(
        managed_world_id="managed", revision_id=revision)
    assert owner_support.listing.admitted_assertion_ids
    assert all(owner_context.parsed.get_assertion(item) is not None
               for item in owner_support.listing.admitted_assertion_ids)


def test_owner_selection_retains_real_ingested_unknown_temporal_scope(monkeypatch):
    from tests import test_governed_native_source_publication_adoption as fixture
    from apps.live_control_server.services import guest_release_assertions as selections

    case = fixture.setup()
    _, receipt = fixture.exercise(case, "new_intervals", primary=False)
    revision = receipt.publication_receipt.published_revision_id
    monkeypatch.setattr(reader, "resolve_managed_world_binding", lambda _: SimpleNamespace(native_world_id=case.space, binding_version=1))
    monkeypatch.setattr(reader.native_registry_source, "read_repository", lambda: case.repo)
    _, context, support, access = reader.read_owner_graph(managed_world_id="managed", revision_id=revision)
    assertions = [context.parsed.get_assertion(i) for i in support.listing.admitted_assertion_ids]
    name = next(a for a in assertions if a.predicate == "dnd5e:name")
    kind = next(a for a in assertions if a.predicate == "dnd5e:classification" and a.subject_entity_id == name.subject_entity_id)
    monkeypatch.setattr(selections, "verify_source_citation", lambda **k: k["excerpt"]["id"])
    def citation(assertion):
        return assertion.metadata.evidence_ref_ids[0], {"id": "selected-excerpt"}, ()
    public, _ = selections.select_node(context=context, admitted_ids=set(support.listing.admitted_assertion_ids),
        entity_id=name.subject_entity_id, name_assertion_id=name.assertion_id, kind_assertion_id=kind.assertion_id,
        name_evidence=citation(name), kind_evidence=citation(kind), access=access,
        native_world_id=case.space, revision_id=revision)
    assert public["name_temporal"] == "unknown" and public["kind_temporal"] == "unknown"


def test_owner_selection_checks_real_private_source_proof_and_withdrawal(monkeypatch):
    from hashlib import sha256
    from uuid import uuid4
    from tests import test_governed_native_source_publication_adoption as fixture
    from apps.live_control_server.services import guest_release_assertions as selections
    from apps.live_control_server.services.guest_release_evidence import GuestReleaseEvidenceError

    document_id, excerpt_id = uuid4(), uuid4()
    admission_type = fixture.NativeTextSourceAdmissionV1
    monkeypatch.setattr(fixture, "NativeTextSourceAdmissionV1", lambda **kwargs: admission_type(
        **kwargs, origin={"namespace": "dungeonbuddy.workspace-document-registry", "object_id": str(document_id),
                          "revision_id": "registry-revision:7"}))
    case = fixture.setup()
    _, receipt = fixture.exercise(case, "new_intervals", primary=False)
    revision = receipt.publication_receipt.published_revision_id
    monkeypatch.setattr(reader, "resolve_managed_world_binding", lambda _: SimpleNamespace(native_world_id=case.space, binding_version=1))
    monkeypatch.setattr(reader.native_registry_source, "read_repository", lambda: case.repo)
    _, context, support, access = reader.read_owner_graph(managed_world_id="managed", revision_id=revision)
    assertions = [context.parsed.get_assertion(i) for i in support.listing.admitted_assertion_ids]
    name = next(a for a in assertions if a.predicate == "dnd5e:name")
    kind = next(a for a in assertions if a.predicate == "dnd5e:classification" and a.subject_entity_id == name.subject_entity_id)
    source_binding = (excerpt_id, document_id, 0, 0, 1, sha256(fixture.RAW).hexdigest(), 1, len(fixture.BODY), 7)
    excerpt = {"id": str(excerpt_id), "text": fixture.BODY[1:]}
    def select(current_access):
        return selections.select_node(context=context, admitted_ids=set(support.listing.admitted_assertion_ids),
            entity_id=name.subject_entity_id, name_assertion_id=name.assertion_id, kind_assertion_id=kind.assertion_id,
            name_evidence=(name.metadata.evidence_ref_ids[0], excerpt, source_binding),
            kind_evidence=(kind.metadata.evidence_ref_ids[0], excerpt, source_binding), access=current_access,
            native_world_id=case.space, revision_id=revision)
    public, _ = select(access)
    assert public["name_citations"] == [str(excerpt_id)]
    case.repo.withdraw_native_source(space_id=case.space, source_artifact_id=case.root.source_artifact_id,
                                     source_revision_id=case.root.source_revision_id)
    _, _, _, fresh = reader.read_owner_graph(managed_world_id="managed", revision_id=revision)
    with pytest.raises(GuestReleaseEvidenceError):
        select(fresh)
