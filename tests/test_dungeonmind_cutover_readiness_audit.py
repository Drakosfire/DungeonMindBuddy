"""Adversarial cutover-readiness audit for Buddy → DungeonMind mechanics authority.

These tests freeze executable evidence for the §28 cutover claim.
They do not invent NPC/PC product authority or promote DungeonMind.

DISPOSITION under test: CUTOVER_NOT_READY until every mandatory gate flips.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import inspect
from pathlib import Path
from typing import Any

import pytest
from dungeonmind.contracts.projection import Admissibility
from dungeonmind.domain.canonical import canonical_sha256
from dungeonmind_dnd.application.world_object_mechanics import (
    hydrate_world_object_mechanics,
)
from dungeonmind_dnd.contracts.mechanics_resources import (
    DndMechanicsResourceEnvelope,
    DndMechanicsResourceRef,
)
from dungeonmind_dnd.contracts.world_object_mechanics import (
    WORLD_OBJECT_MECHANICS_ELIGIBLE_KINDS,
)

import graph_memory.kernel as kernel
from apps.live_control_server.integrations import dungeonmind_kernel as bridge_pkg
from apps.live_control_server.integrations.dungeonmind_kernel.config import (
    dungeonmind_threat_shadow_enabled,
)
from apps.live_control_server.integrations.dungeonmind_kernel.world_object_conformance_bridge import (
    ThreatConformanceBridgeError,
    bridge_exact_buddy_threat,
)
from apps.live_control_server.integrations.dungeonmind_statblocks.errors import (
    StatblockIntegrationError,
)
from apps.live_control_server.services import threat_query_hydration as authority_svc
from apps.live_control_server.services import union_supergraph_projection_adapter as plan_proj
from apps.live_control_server.services import world_graph_projection as wg_proj
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)
from graph_memory.union_supergraph.statblock_binding import (
    CONTRACT,
    CONTRACT_VERSION,
    PROVIDER,
    compute_binding_id,
    edge_id_from_binding_id,
    external_statblock_node_id,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_DATA = REPO_ROOT / "graph_data"
ROUTE_PATH = (
    REPO_ROOT
    / "apps"
    / "live_control_server"
    / "routes"
    / "threat_query_hydration.py"
)
AUTHORITY_PATH = (
    REPO_ROOT
    / "apps"
    / "live_control_server"
    / "services"
    / "threat_query_hydration.py"
)

WORLD_ID = "cutover-audit-world"
CAMPAIGN_ID = "longmont-c2"
THREAT_ID = "threat:cutover-cardinality"
STATBLOCK_ID = "sb_cutover01"
STATBLOCK_REV = "rev_cutover01"
MECHANICS_PAYLOAD = {
    "name": "Cutover Cardinality Threat",
    "size": "Medium",
    "type": "humanoid",
    "alignment": "neutral",
    "armor_class": 15,
    "hit_points": 45,
    "speed": {"walk": 30},
    "abilities": {
        "str": 14,
        "dex": 12,
        "con": 13,
        "int": 10,
        "wis": 11,
        "cha": 9,
    },
}
PAYLOAD_DIGEST = canonical_sha256(MECHANICS_PAYLOAD)
BUDDY_DIGEST = f"sha256:{PAYLOAD_DIGEST}"
_CONTRIBUTION_SEQ = 0


class _CountingResolver:
    def __init__(self, envelope: DndMechanicsResourceEnvelope) -> None:
        self.envelope = envelope
        self.calls: list[DndMechanicsResourceRef] = []

    def resolve(self, resource_ref: DndMechanicsResourceRef) -> DndMechanicsResourceEnvelope:
        self.calls.append(resource_ref)
        return self.envelope


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:cutover-audit-baseline"],
    )
    return tmp_path


def _contribution(*assertions: Any):
    global _CONTRIBUTION_SEQ
    _CONTRIBUTION_SEQ += 1
    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="manual_import",
        source_artifact_id="graph-native:cutover-audit",
        source_revision_id=f"audit-{_CONTRIBUTION_SEQ}",
        campaign_scope=CAMPAIGN_ID,
        accepted_assertions=list(assertions),
    )


def _binding(
    *,
    role: str,
    phase_key: str | None = None,
    variant_label: str | None = None,
    threat_node_id: str = THREAT_ID,
) -> dict[str, str | None]:
    return {
        "schema": "dmb_threat_statblock_binding_v1",
        "binding_id": compute_binding_id(
            threat_node_id=threat_node_id,
            provider=PROVIDER,
            statblock_id=STATBLOCK_ID,
            revision_id=STATBLOCK_REV,
            contract=CONTRACT,
            contract_version=CONTRACT_VERSION,
            definition_digest=BUDDY_DIGEST,
            role=role,
            phase_key=phase_key,
            variant_label=variant_label,
        ),
        "provider": PROVIDER,
        "statblock_id": STATBLOCK_ID,
        "revision_id": STATBLOCK_REV,
        "contract": CONTRACT,
        "contract_version": CONTRACT_VERSION,
        "definition_digest": BUDDY_DIGEST,
        "role": role,
        "phase_key": phase_key,
        "variant_label": variant_label,
    }


def _resource_value() -> dict[str, object]:
    return {
        "kind": "external_resource",
        "role": "statblock",
        "external_resource": {
            "schema": "dmb_external_resource_v1",
            "provider": PROVIDER,
            "resource_type": "statblock",
            "resource_id": STATBLOCK_ID,
            "contract": CONTRACT,
            "contract_version": CONTRACT_VERSION,
        },
    }


def _binding_value(binding: dict[str, str | None]) -> dict[str, object]:
    return {
        "edge_id": edge_id_from_binding_id(str(binding["binding_id"])),
        "direction": "outbound",
        "threat_statblock_binding": binding,
    }


def _publish_kind(root: Path, *, node_id: str, kind: str, role: str) -> str:
    assertion = kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=f"Audit {kind}",
        campaign_scope=CAMPAIGN_ID,
        value={
            "kind": kind,
            "role": role,
            "source_domains": ["manual_seed"],
        },
    )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(assertion)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _publish_threat(root: Path) -> None:
    _publish_kind(root, node_id=THREAT_ID, kind="threat", role="threat")


def _publish_bindings(root: Path, bindings: list[dict[str, str | None]]) -> str:
    assertions: list[Any] = [
        kernel.build_assertion(
            assertion_kind="node",
            acceptance_state="accepted",
            subject_node_id=external_statblock_node_id(STATBLOCK_ID),
            label=f"External {STATBLOCK_ID}",
            campaign_scope=CAMPAIGN_ID,
            value=_resource_value(),
        )
    ]
    for binding in bindings:
        assertions.append(
            kernel.build_assertion(
                assertion_kind="edge",
                acceptance_state="accepted",
                subject_node_id=THREAT_ID,
                target_node_id=external_statblock_node_id(STATBLOCK_ID),
                predicate="uses_statblock",
                campaign_scope=CAMPAIGN_ID,
                value=_binding_value(binding),
            )
        )
    result = kernel.merge_contribution_to_revision(
        root, world_id=WORLD_ID, contribution=_contribution(*assertions)
    )
    assert result.published and result.revision_id
    return result.revision_id


def _five_role_bindings() -> list[dict[str, str | None]]:
    return [
        _binding(role="primary"),
        _binding(role="alternate"),
        _binding(role="phase", phase_key="bloodied"),
        _binding(role="encounter_variant", variant_label="night raid"),
        _binding(role="template", variant_label="elite"),
    ]


def _semantic_set(result: Any) -> set[tuple[Any, ...]]:
    """Order-independent semantic attachment identity (not graph-revision mech IDs)."""
    return {
        (
            item.attachment.role,
            item.attachment.phase_key,
            item.attachment.variant_label,
            item.attachment.binding.resource_ref.resource_id,
            item.attachment.binding.resource_ref.resource_revision,
            item.attachment.binding.resource_ref.payload_sha256,
        )
        for item in result.attachments
    }


def _hydrate_all(result: Any) -> int:
    from dungeonmind.application.graph_snapshot import UnionGraphV3SnapshotReader
    from dungeonmind.infrastructure.semantic_profiles import StaticSemanticProfileRegistry
    from dungeonmind_dnd.application.world_object_vocabulary import (
        load_builtin_v3_descriptor,
    )

    reader = UnionGraphV3SnapshotReader(
        profile_registry=StaticSemanticProfileRegistry([load_builtin_v3_descriptor()])
    )
    hydrate_count = 0
    for item in result.attachments:
        resource_ref = item.attachment.binding.resource_ref
        envelope = DndMechanicsResourceEnvelope(
            resource_ref=resource_ref,
            mechanics_payload=copy.deepcopy(MECHANICS_PAYLOAD),
        )
        resolver = _CountingResolver(envelope)
        hydration = hydrate_world_object_mechanics(
            item.attachment.binding,
            admissibility=Admissibility.GM,
            graph_revision=result.target_revision,
            graph_reader=reader,
            resource_resolver=resolver,
        )
        assert hydration.mechanics_payload == MECHANICS_PAYLOAD
        assert len(resolver.calls) == 1
        assert resolver.calls[0] == resource_ref
        hydrate_count += 1
    return hydrate_count


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(rel)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_dungeonmind_contract_admits_threat_and_npc_not_pc() -> None:
    """Predecessor re-anchor landed: Threat+NPC eligible; PC not mechanics-eligible."""
    assert WORLD_OBJECT_MECHANICS_ELIGIBLE_KINDS == frozenset(
        {"dnd5e:threat", "dnd5e:npc"}
    )
    assert "dnd5e:player_character" not in WORLD_OBJECT_MECHANICS_ELIGIBLE_KINDS


def test_canonical_public_bridge_entrypoint_rejects_npc(seeded_root: Path) -> None:
    """NPC mechanics gate: FAIL — only public exact bridge rejects kind=npc."""
    assert bridge_pkg.__all__  # package exports are the public surface
    assert "bridge_exact_buddy_threat" in bridge_pkg.__all__
    revision_id = _publish_kind(
        seeded_root,
        node_id="npc:cutover-lysandra-standin",
        kind="npc",
        role="ally",
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id="npc:cutover-lysandra-standin",
        )
    assert exc.value.reason == "source_object_kind_not_bridgeable"


def test_canonical_public_bridge_entrypoint_rejects_pc(seeded_root: Path) -> None:
    """PC semantic mapping gate: FAIL — only public exact bridge rejects kind=pc."""
    revision_id = _publish_kind(
        seeded_root,
        node_id="pc:cutover-bonogo-standin",
        kind="pc",
        role="player_character",
    )
    with pytest.raises(ThreatConformanceBridgeError) as exc:
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id="pc:cutover-bonogo-standin",
        )
    assert exc.value.reason == "source_object_kind_not_bridgeable"


def test_product_authority_entrypoint_does_not_invoke_dungeonmind_bridge() -> None:
    """Dark-cutover / local-authority-kill: FAIL — Buddy client remains product authority."""
    hydrate_source = inspect.getsource(authority_svc._hydrate_binding)
    query_source = inspect.getsource(authority_svc.query_threats_with_hydration)
    authority_text = AUTHORITY_PATH.read_text(encoding="utf-8")

    assert "get_exact_revision" in hydrate_source
    assert "bridge_exact_buddy_threat" not in hydrate_source
    assert "bridge_exact_buddy_threat" not in query_source
    assert "hydrate_world_object_mechanics" not in hydrate_source
    assert "run_dungeonmind_threat_hydration_shadow" not in authority_text
    for export in bridge_pkg.__all__:
        if export.startswith(("bridge_", "run_")):
            assert export not in authority_text


def test_product_authority_has_no_alternate_hydration_fallback() -> None:
    """HIDDEN_FALLBACK is NOT a proven defect: failures stay typed, no second path."""
    source = inspect.getsource(authority_svc._hydrate_binding)
    assert "get_exact_revision" in source
    # Failures map to typed statuses; there is no secondary local hydrator call.
    for forbidden in (
        "bridge_exact_buddy_threat",
        "hydrate_world_object_mechanics",
        "load_local",
        "fallback",
        "latest",
        "get_current",
    ):
        assert forbidden not in source
    assert "exact_revision_missing" in source
    assert "unavailable" in source
    assert "integrity_failure" in source


def test_canonical_plan_and_world_projection_entrypoints_do_not_consume_bridge() -> None:
    """Shared product projection consumes bridge: FAIL on canonical entrypoints."""
    plan_source = inspect.getsource(plan_proj)
    wg_source = inspect.getsource(wg_proj)
    for export in bridge_pkg.__all__:
        if export.startswith(("bridge_", "run_")):
            assert export not in plan_source
            assert export not in wg_source
    assert "dungeonmind_kernel" not in plan_source
    assert "dungeonmind_kernel" not in wg_source


def test_threat_query_route_schedules_shadow_after_authority_response() -> None:
    route_text = ROUTE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(route_text)
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "post_threat_query_hydration"
    )
    source_segment = ast.get_source_segment(route_text, fn) or ""
    assert "query_threats_with_hydration" in source_segment
    assert "BackgroundTasks" in source_segment
    assert "run_dungeonmind_threat_hydration_shadow" in source_segment
    assert source_segment.index("query_threats_with_hydration") < source_segment.index(
        "add_task"
    )


def test_shadow_default_disabled_and_typo_safe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", raising=False)
    assert dungeonmind_threat_shadow_enabled() is False
    monkeypatch.setenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", "true")
    assert dungeonmind_threat_shadow_enabled() is False
    monkeypatch.setenv("DUNGEONMIND_THREAT_HYDRATION_SHADOW_ENABLED", "1")
    assert dungeonmind_threat_shadow_enabled() is True


def test_no_durable_graph_data_uses_statblock_bindings() -> None:
    """Real Threat mechanics dogfood gate: NOT YET PROVEN in checked-in graph_data."""
    hits: list[str] = []
    for path in GRAPH_DATA.rglob("*.json"):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if "uses_statblock" in text:
            hits.append(str(path.relative_to(REPO_ROOT)))
    assert hits == [], (
        "unexpected durable uses_statblock in graph_data; update cutover disposition: "
        + ", ".join(hits)
    )


def test_five_role_cardinality_enumerate_hydrate_and_reverse_order(
    seeded_root: Path,
) -> None:
    """Handoff §9: one object with five roles; reverse storage; same semantic set."""
    forward = _five_role_bindings()
    reverse = list(reversed(forward))

    _publish_threat(seeded_root)
    revision_forward = _publish_bindings(seeded_root, forward)
    result_forward = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_forward,
        threat_node_id=THREAT_ID,
    )
    assert len(result_forward.attachments) == 5
    roles = {item.attachment.role for item in result_forward.attachments}
    assert roles == {
        "primary",
        "alternate",
        "phase",
        "encounter_variant",
        "template",
    }
    # Same exact resource → one generic binding; five specialized attachments.
    assert len({item.target_binding_id for item in result_forward.attachments}) == 1
    assert len({item.target_attachment_id for item in result_forward.attachments}) == 5
    assert _hydrate_all(result_forward) == 5
    forward_set = _semantic_set(result_forward)

    # Fresh world for reversed insertion order.
    root_b = seeded_root.parent / "reverse-order"
    root_b.mkdir()
    kernel.publish_world_revision(
        root_b,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:cutover-audit-reverse"],
    )
    _publish_threat(root_b)
    revision_reverse = _publish_bindings(root_b, reverse)
    result_reverse = bridge_exact_buddy_threat(
        root=root_b,
        world_id=WORLD_ID,
        revision_id=revision_reverse,
        threat_node_id=THREAT_ID,
    )
    assert len(result_reverse.attachments) == 5
    assert _hydrate_all(result_reverse) == 5
    assert _semantic_set(result_reverse) == forward_set


def test_bridge_execution_is_read_only_against_source_graph(seeded_root: Path) -> None:
    """§21 executed snapshot: bridge does not mutate the source World Graph tree."""
    _publish_threat(seeded_root)
    bindings = _five_role_bindings()[:1]
    revision_id = _publish_bindings(seeded_root, bindings)
    before = _tree_digest(seeded_root)
    result = bridge_exact_buddy_threat(
        root=seeded_root,
        world_id=WORLD_ID,
        revision_id=revision_id,
        threat_node_id=THREAT_ID,
    )
    assert len(result.attachments) == 1
    with pytest.raises(ThreatConformanceBridgeError):
        bridge_exact_buddy_threat(
            root=seeded_root,
            world_id=WORLD_ID,
            revision_id=revision_id,
            threat_node_id="threat:missing",
        )
    after = _tree_digest(seeded_root)
    assert before == after


def test_cutover_disposition_is_not_ready() -> None:
    """Binary gate lock: flip only when §28 mandatory gates all PASS."""
    disposition = "CUTOVER_NOT_READY"
    blockers = {
        "BRIDGE_MAPPING": "NPC (and PC semantic) bridge absent; Threat-only #518",
        "PRODUCT_PROJECTION": (
            "Canonical Plan/world projection and Threat product authority do not "
            "consume dungeonmind_kernel; dark-cutover / poisoned-fallback not exercisable"
        ),
        "REAL_DATA_INCOMPATIBILITY": (
            "No checked-in durable uses_statblock Threat/NPC dogfood object"
        ),
    }
    # HIDDEN_FALLBACK is explicitly NOT listed: current Buddy authority fails closed
    # without an alternate hydrator. Poisoned A-vs-B remains BLOCKED BY PRODUCT_PROJECTION.
    assert disposition == "CUTOVER_NOT_READY"
    assert "HIDDEN_FALLBACK" not in blockers
    assert set(blockers) == {
        "BRIDGE_MAPPING",
        "PRODUCT_PROJECTION",
        "REAL_DATA_INCOMPATIBILITY",
    }


def test_statblock_integration_error_categories_exist_for_fail_closed_authority() -> None:
    """Sanity: authority typed failures are real categories, not hidden recovery."""
    assert issubclass(StatblockIntegrationError, Exception)
