"""Buddy activation is a verified registry CAS, never a fabricated Graph head."""

from tests.application_state.world_catalog_fixtures import store_world, world_snapshot
from dataclasses import replace
from types import SimpleNamespace

import pytest

from apps.live_control_server.models.extract_promote import FirstWorldNativeTarget
from apps.live_control_server.ports.world_graph_initialization import (
    WorldGraphInitializationReceipt,
)
from apps.live_control_server.services.world_container_registry import (
    create_world_container,
    get_world_container,
)
from apps.live_control_server.services.world_graph_binding import (
    activate_reviewed_native_graph,
    WorldGraphBindingError,
)


def _fixture(root):
    world = create_world_container(name="Activation proof")
    reservation = world.native_graph_binding
    target = FirstWorldNativeTarget(
        native_world_id=reservation.native_world_id,
        provisioning_id=reservation.provisioning_id,
        binding_version=1,
    )
    receipt = WorldGraphInitializationReceipt(
        world_id=target.native_world_id,
        initialization_id=target.provisioning_id,
        published_revision_id="D0",
        reviewed_contribution_id="contribution",
        reviewed_contribution_sha256="b" * 64,
        accepted_assertion_ids=("assertion",),
        outcome="initialized",
        command_sha256="c" * 64,
    )
    verified = SimpleNamespace(
        world_id=target.native_world_id,
        initialization_id=target.provisioning_id,
        published_revision_id="D0",
        command_sha256="c" * 64,
        source_plan_id="plan",
        source_plan_sha256="d" * 64,
        campaign_id=None,
    )
    revisions = {"D0": None, "C1": "D0"}

    def get_revision(native_id, revision_id):
        assert native_id == target.native_world_id
        return (
            SimpleNamespace(
                revision=SimpleNamespace(
                    world_id=native_id,
                    revision_id=revision_id,
                    parent_revision_id=revisions[revision_id],
                )
            )
            if revision_id in revisions
            else None
        )

    services = SimpleNamespace(
        binding=SimpleNamespace(
            world_id=target.native_world_id,
            genesis="reviewed_world_initialization",
            dungeonmind_first_revision_id="D0",
            dungeonmind_head_revision_id="C1",
        ),
        bundle=SimpleNamespace(
            world_graph=SimpleNamespace(get_revision=get_revision),
            reviewed_world_initializations=SimpleNamespace(
                get_for_world=lambda _: verified
            ),
        ),
    )
    return world, target, receipt, verified, revisions, services


def _activate(root, world, target, receipt, services, validator=None):
    return activate_reviewed_native_graph(
        world.world_id,
        target=target,
        receipt=receipt,
        plan_id="plan",
        plan_digest="sha256:" + "d" * 64,
        authority_validator=validator or (lambda _: services),
    )


def test_verified_descendant_activates_same_identity_and_replays_without_registry_write(
    tmp_path,
):
    world, target, receipt, _, _, services = _fixture(tmp_path)
    active = _activate(tmp_path, world, target, receipt, services)
    binding = active.native_graph_binding
    assert binding.status == "active"
    assert binding.binding_version == target.binding_version == 1
    assert binding.provisioning_id == target.provisioning_id
    assert binding.initialization_revision_id == "D0"
    assert binding.validated_head_revision_id == "C1"
    before = world_snapshot()
    assert (
        _activate(
            tmp_path,
            world,
            target,
            replace(receipt, outcome="already_initialized"),
            services,
        )
        == active
    )
    assert world_snapshot() == before


@pytest.mark.parametrize(
    "damage",
    [
        "operation",
        "command",
        "plan",
        "scope",
        "foreign_world",
        "adoption",
        "wrong_genesis",
        "orphan",
        "cycle",
        "missing_parent",
        "genesis_parent",
    ],
)
def test_invalid_reviewed_proof_never_activates(tmp_path, damage):
    world, target, receipt, verified, revisions, services = _fixture(tmp_path)
    if damage == "operation":
        verified.initialization_id = "provision:" + "f" * 32
    if damage == "command":
        verified.command_sha256 = "f" * 64
    if damage == "plan":
        verified.source_plan_id = "foreign"
    if damage == "scope":
        verified.campaign_id = "foreign"
    if damage == "foreign_world":
        verified.world_id = "foreign"
    if damage == "adoption":
        services.binding.genesis = "existing_world_adoption"
    if damage == "wrong_genesis":
        services.binding.dungeonmind_first_revision_id = "foreign"
    if damage == "orphan":
        revisions["C1"] = None
    if damage == "cycle":
        revisions["C1"] = "C1"
    if damage == "missing_parent":
        revisions["C1"] = "missing"
    if damage == "genesis_parent":
        revisions["D0"] = "foreign"
    before = world_snapshot()
    with pytest.raises(WorldGraphBindingError):
        _activate(tmp_path, world, target, receipt, services)
    assert world_snapshot() == before
    assert (
        get_world_container(world.world_id).native_graph_binding.status
        == "provisioning"
    )


def test_other_world_change_during_validation_does_not_block_activation(tmp_path):
    world, target, receipt, _, _, services = _fixture(tmp_path)

    def concurrent_write(_):
        create_world_container(name="Concurrent legitimate World")
        return services

    active = _activate(tmp_path, world, target, receipt, services, concurrent_write)
    assert active.native_graph_binding.status == "active"


def test_same_world_revision_change_during_validation_requires_original_retry(tmp_path):
    world, target, receipt, _, _, services = _fixture(tmp_path)

    def concurrent_write(_):
        store_world(world.model_copy(update={"name": "Changed during validation"}))
        return services

    with pytest.raises(WorldGraphBindingError):
        _activate(tmp_path, world, target, receipt, services, concurrent_write)
    assert (
        get_world_container(world.world_id).native_graph_binding.status
        == "provisioning"
    )
    assert (
        _activate(
            tmp_path, world, target, receipt, services
        ).native_graph_binding.status
        == "active"
    )


pytestmark = pytest.mark.usefixtures("application_state_dsn")


def test_active_replay_rejects_same_world_metadata_aba(tmp_path):
    world, target, receipt, _, _, services = _fixture(tmp_path)
    active = _activate(tmp_path, world, target, receipt, services)

    def aba(_):
        store_world(active.model_copy(update={"name": "Temporary change"}))
        store_world(active)
        return services

    with pytest.raises(WorldGraphBindingError):
        _activate(tmp_path, world, target, receipt, services, aba)
    assert get_world_container(world.world_id) == active
    assert _activate(tmp_path, world, target, receipt, services) == active


@pytest.mark.parametrize("operation", ["publish", "publish_prospective_publication", "rollback", "close", "delete_revision"])
def test_native_first_world_activation_readonly_adapter_refuses_writes(operation):
    from apps.live_control_server.services.world_graph_binding import _NativeFirstWorldReadOnlyRepository

    calls = []
    underlying = SimpleNamespace(**{operation: lambda *args, **kwargs: calls.append(operation)})
    readonly = _NativeFirstWorldReadOnlyRepository(underlying)
    with pytest.raises(WorldGraphBindingError, match="non-read operation"):
        getattr(readonly, operation)()
    assert calls == []


def test_native_first_world_activation_readonly_adapter_preserves_read_identity():
    from apps.live_control_server.services.world_graph_binding import _NativeFirstWorldReadOnlyRepository

    marker = object()
    calls = []
    underlying = SimpleNamespace(get_head=lambda space: calls.append(space) or marker)
    assert _NativeFirstWorldReadOnlyRepository(underlying).get_head("exact-space") is marker
    assert calls == ["exact-space"]


@pytest.mark.parametrize("deny_owner", [False, True])
def test_native_first_world_hosted_recovery_uses_signed_scope_without_run_reload(monkeypatch, deny_owner):
    import asyncio
    import json
    from fastapi import HTTPException
    from starlette.requests import Request
    from apps.live_control_server.models import native_first_world_publication as models
    from apps.live_control_server.services import hosted_native_graph_access as access
    from apps.live_control_server.services import native_first_world_publication as native
    from apps.live_control_server.services import promotable_ingest_run as runs

    plan = SimpleNamespace(world_id="signed-world")
    calls = []
    monkeypatch.setattr(access, "_hosted_subject", lambda request: "owner")
    monkeypatch.setattr(models.NativeFirstWorldConfirmRequest, "model_validate",
                        lambda body: SimpleNamespace(plan=plan))

    def decode(value, *, principal_subject):
        assert value is plan and principal_subject == "hosted_dms:owner"
        calls.append("signature")
        return value

    def owner(subject, world):
        assert subject == "owner" and world == "signed-world"
        calls.append("owner")
        if deny_owner:
            raise HTTPException(status_code=403)

    monkeypatch.setattr(native, "decode_native_plan", decode)
    monkeypatch.setattr(access, "_owned_world", owner)
    monkeypatch.setattr(runs, "resolve_promotable_ingest_run",
                        lambda *args, **kwargs: pytest.fail("recovery reloaded a mutable run"))
    body = json.dumps({"schema": models.NATIVE_CONFIRM_SCHEMA, "plan": {}}).encode()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request = Request({"type": "http", "method": "POST", "path": access.FIRST_WORLD_CONFIRM_PATH,
                       "query_string": b"", "headers": []}, receive)
    if deny_owner:
        with pytest.raises(HTTPException) as error:
            asyncio.run(access.resolve_hosted_first_world(request))
        assert error.value.status_code == 403
        assert not hasattr(request.state, "hosted_first_world")
    else:
        assert asyncio.run(access.resolve_hosted_first_world(request)) == "signed-world"
        assert request.state.hosted_first_world == "signed-world"
    assert calls == ["signature", "owner"]


@pytest.mark.parametrize("principal", [None, "", "   ", 1])
def test_native_first_world_activation_requires_current_principal_before_reads(monkeypatch, principal):
    from apps.live_control_server.services import native_first_world_publication as native
    from apps.live_control_server.services.world_graph_binding import activate_native_first_world

    monkeypatch.setattr(native, "decode_native_plan", lambda *args, **kwargs: pytest.fail("missing principal reached decoding"))
    before = world_snapshot()
    with pytest.raises(WorldGraphBindingError, match="current confirming principal") as error:
        activate_native_first_world("world", plan=object(), repository=object(), principal_subject=principal)
    assert error.value.status_code == 403
    assert world_snapshot() == before


@pytest.mark.parametrize("damage", [None, "missing", "plan", "operation", "world", "contribution", "campaign"])
def test_historical_first_world_recovery_is_receipt_only_and_never_activates(tmp_path, damage):
    from datetime import UTC, datetime
    from dungeonmind.contracts.reviewed_world_initialization import ReviewedWorldInitializationReceiptV1
    from apps.live_control_server.services.first_world_graph_publication import recover_historical_first_world
    from apps.live_control_server.services.extract_promote import ExtractPromoteError

    world, target, _, _, _, _ = _fixture(tmp_path)
    plan = SimpleNamespace(world_id=world.world_id, native_target=target, schema_="historical-plan-v3",
                           plan_id="plan", plan_digest="sha256:" + "a" * 64,
                           contribution_id="reviewed-contribution", contribution_payload_sha256="b" * 64)
    receipt = ReviewedWorldInitializationReceiptV1(
        initialization_id=target.provisioning_id, world_id=target.native_world_id, campaign_id=None,
        source_plan_schema=plan.schema_, source_plan_id=plan.plan_id, source_plan_sha256="a" * 64,
        command_sha256="c" * 64, reviewed_contribution_id=plan.contribution_id,
        reviewed_contribution_sha256="d" * 64, published_revision_id="historical-D0",
        published_graph_payload_sha256="e" * 64, accepted_assertion_ids=["assertion"],
        actor="historical-actor", initialized_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    fields = {"plan": "source_plan_sha256", "operation": "initialization_id",
              "world": "world_id", "contribution": "reviewed_contribution_id", "campaign": "campaign_id"}
    if damage in fields:
        value = "f" * 64 if damage == "plan" else "foreign"
        receipt = receipt.model_copy(update={fields[damage]: value})
    calls = []

    def get_for_world(space):
        assert space == target.native_world_id
        calls.append("receipt")
        return None if damage == "missing" else receipt

    def authorize(managed):
        assert managed == world.world_id
        calls.append("authorize")

    before = world_snapshot()
    kwargs = dict(authorize_world=authorize, receipt_repository=SimpleNamespace(get_for_world=get_for_world))
    if damage:
        with pytest.raises(ExtractPromoteError):
            recover_historical_first_world(SimpleNamespace(plan=plan), **kwargs)
        assert calls == ["authorize", "receipt"]
    else:
        result = recover_historical_first_world(SimpleNamespace(plan=plan), **kwargs)
        assert result.activation_status == "historical_only"
        assert result.historical_receipt == receipt
        assert result.historical_receipt.reviewed_contribution_sha256 != plan.contribution_payload_sha256
        assert calls == ["authorize", "receipt", "authorize"]
    assert world_snapshot() == before
    assert get_world_container(world.world_id).native_graph_binding.status == "provisioning"
