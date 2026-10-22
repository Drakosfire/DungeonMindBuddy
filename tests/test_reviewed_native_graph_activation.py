"""Buddy activation is a verified registry CAS, never a fabricated Graph head."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from apps.live_control_server.models.extract_promote import FirstWorldNativeTarget
from apps.live_control_server.ports.world_graph_initialization import WorldGraphInitializationReceipt
from apps.live_control_server.services.world_container_registry import (
    create_world_container, get_world_container, world_containers_path,
)
from apps.live_control_server.services.world_graph_binding import (
    activate_reviewed_native_graph, WorldGraphBindingError,
)


def _fixture(root):
    world = create_world_container(root, name="Activation proof")
    reservation = world.native_graph_binding
    target = FirstWorldNativeTarget(native_world_id=reservation.native_world_id,
        provisioning_id=reservation.provisioning_id, binding_version=1)
    receipt = WorldGraphInitializationReceipt(world_id=target.native_world_id,
        initialization_id=target.provisioning_id, published_revision_id="D0",
        reviewed_contribution_id="contribution", reviewed_contribution_sha256="b"*64,
        accepted_assertion_ids=("assertion",), outcome="initialized", command_sha256="c"*64)
    verified = SimpleNamespace(world_id=target.native_world_id,
        initialization_id=target.provisioning_id, published_revision_id="D0",
        command_sha256="c"*64, source_plan_id="plan", source_plan_sha256="d"*64, campaign_id=None)
    revisions = {"D0":None, "C1":"D0"}
    def get_revision(native_id, revision_id):
        assert native_id == target.native_world_id
        return (SimpleNamespace(revision=SimpleNamespace(world_id=native_id,
            revision_id=revision_id, parent_revision_id=revisions[revision_id]))
            if revision_id in revisions else None)
    services = SimpleNamespace(binding=SimpleNamespace(world_id=target.native_world_id,
        genesis="reviewed_world_initialization", dungeonmind_first_revision_id="D0",
        dungeonmind_head_revision_id="C1"), bundle=SimpleNamespace(
            world_graph=SimpleNamespace(get_revision=get_revision),
            reviewed_world_initializations=SimpleNamespace(get_for_world=lambda _:verified)))
    return world, target, receipt, verified, revisions, services


def _activate(root, world, target, receipt, services, validator=None):
    return activate_reviewed_native_graph(root, world.world_id, target=target, receipt=receipt,
        plan_id="plan", plan_digest="sha256:"+"d"*64,
        authority_validator=validator or (lambda _: services))


def test_verified_descendant_activates_same_identity_and_replays_without_registry_write(tmp_path):
    world, target, receipt, _, _, services = _fixture(tmp_path)
    active = _activate(tmp_path, world, target, receipt, services)
    binding = active.native_graph_binding
    assert binding.status == "active"
    assert binding.binding_version == target.binding_version == 1
    assert binding.provisioning_id == target.provisioning_id
    assert binding.initialization_revision_id == "D0"
    assert binding.validated_head_revision_id == "C1"
    before = world_containers_path(tmp_path).read_bytes()
    assert _activate(tmp_path, world, target, replace(receipt, outcome="already_initialized"), services) == active
    assert world_containers_path(tmp_path).read_bytes() == before


@pytest.mark.parametrize("damage", ["operation", "command", "plan", "scope", "foreign_world",
    "adoption", "wrong_genesis", "orphan", "cycle", "missing_parent", "genesis_parent"])
def test_invalid_reviewed_proof_never_activates(tmp_path, damage):
    world, target, receipt, verified, revisions, services = _fixture(tmp_path)
    if damage == "operation": verified.initialization_id = "provision:"+"f"*32
    if damage == "command": verified.command_sha256 = "f"*64
    if damage == "plan": verified.source_plan_id = "foreign"
    if damage == "scope": verified.campaign_id = "foreign"
    if damage == "foreign_world": verified.world_id = "foreign"
    if damage == "adoption": services.binding.genesis = "existing_world_adoption"
    if damage == "wrong_genesis": services.binding.dungeonmind_first_revision_id = "foreign"
    if damage == "orphan": revisions["C1"] = None
    if damage == "cycle": revisions["C1"] = "C1"
    if damage == "missing_parent": revisions["C1"] = "missing"
    if damage == "genesis_parent": revisions["D0"] = "foreign"
    before = world_containers_path(tmp_path).read_bytes()
    with pytest.raises(WorldGraphBindingError):
        _activate(tmp_path, world, target, receipt, services)
    assert world_containers_path(tmp_path).read_bytes() == before
    assert get_world_container(tmp_path, world.world_id).native_graph_binding.status == "provisioning"


def test_registry_drift_during_validation_requires_original_request_retry(tmp_path):
    world, target, receipt, _, _, services = _fixture(tmp_path)
    def concurrent_write(_):
        create_world_container(tmp_path, name="Concurrent legitimate World")
        return services
    with pytest.raises(WorldGraphBindingError):
        _activate(tmp_path, world, target, receipt, services, concurrent_write)
    assert get_world_container(tmp_path, world.world_id) == world
    assert _activate(tmp_path, world, target, receipt, services).native_graph_binding.status == "active"
