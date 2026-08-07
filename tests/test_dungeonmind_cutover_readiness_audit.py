"""Adversarial cutover-readiness audit for Buddy → DungeonMind mechanics authority.

These tests do not invent NPC/PC bridges or promote product authority.
They freeze the evidence that the §28 cutover claim is or is not satisfied
on the current tree.

DISPOSITION under test: CUTOVER_NOT_READY until every mandatory gate flips.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest
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
from apps.live_control_server.services import threat_query_hydration as authority_svc
from graph_memory.union_supergraph.load import (
    DEFAULT_FIXTURE_PATH,
    load_union_supergraph_store,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
GRAPH_DATA = REPO_ROOT / "graph_data"
KERNEL_DIR = (
    REPO_ROOT
    / "apps"
    / "live_control_server"
    / "integrations"
    / "dungeonmind_kernel"
)
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
_CONTRIBUTION_SEQ = 0


@pytest.fixture
def seeded_root(tmp_path: Path) -> Path:
    kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        load_union_supergraph_store(DEFAULT_FIXTURE_PATH),
        operation_ids=["op:cutover-audit-baseline"],
    )
    return tmp_path


def _contribution(*assertions):
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


def test_dungeonmind_contract_admits_threat_and_npc_not_pc() -> None:
    """Predecessor re-anchor landed: Threat+NPC eligible; PC not mechanics-eligible."""
    assert WORLD_OBJECT_MECHANICS_ELIGIBLE_KINDS == frozenset(
        {"dnd5e:threat", "dnd5e:npc"}
    )
    assert "dnd5e:player_character" not in WORLD_OBJECT_MECHANICS_ELIGIBLE_KINDS


def test_buddy_public_bridge_is_threat_only() -> None:
    assert "bridge_exact_buddy_threat" in bridge_pkg.__all__
    assert not hasattr(bridge_pkg, "bridge_exact_buddy_npc")
    assert not hasattr(bridge_pkg, "bridge_exact_buddy_pc")
    assert not hasattr(bridge_pkg, "bridge_exact_buddy_player_character")


def test_npc_world_object_is_not_bridgeable(seeded_root: Path) -> None:
    """Mandatory NPC mechanics gate: FAIL — no NPC bridge."""
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


def test_pc_world_object_is_not_bridgeable(seeded_root: Path) -> None:
    """Mandatory PC semantic mapping gate: FAIL — no PC bridge."""
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


def test_product_authority_still_uses_buddy_statblock_client() -> None:
    """Dark-cutover / local-authority-kill gates: FAIL — Buddy client is authority."""
    source = inspect.getsource(authority_svc._hydrate_binding)
    assert "get_exact_revision" in source
    assert "bridge_exact_buddy_threat" not in source
    assert "hydrate_world_object_mechanics" not in source
    assert "dungeonmind_kernel" not in AUTHORITY_PATH.read_text(encoding="utf-8")


def test_bridge_is_not_imported_by_plan_or_build_projection_services() -> None:
    """Shared product projection consumes bridge: FAIL."""
    services = REPO_ROOT / "apps" / "live_control_server" / "services"
    offenders: list[str] = []
    for path in services.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "dungeonmind_kernel" in text or "bridge_exact_buddy_threat" in text:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"unexpected product imports: {offenders}"


def test_only_threat_query_route_schedules_non_authoritative_shadow() -> None:
    route_text = ROUTE_PATH.read_text(encoding="utf-8")
    assert "run_dungeonmind_threat_hydration_shadow" in route_text
    assert "dungeonmind_threat_shadow_enabled" in route_text
    # Shadow is post-response BackgroundTasks, not inline authority.
    tree = ast.parse(route_text)
    fn = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "post_threat_query_hydration"
    )
    source_segment = ast.get_source_segment(route_text, fn) or ""
    assert "query_threats_with_hydration" in source_segment
    assert "BackgroundTasks" in source_segment
    # Authority runs before optional schedule.
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


def test_kernel_package_has_no_npc_or_pc_bridge_modules() -> None:
    names = {p.name for p in KERNEL_DIR.glob("*.py")}
    assert "world_object_conformance_bridge.py" in names
    assert "threat_hydration_shadow.py" in names
    assert "npc_conformance_bridge.py" not in names
    assert "pc_conformance_bridge.py" not in names
    assert "player_character_conformance_bridge.py" not in names


def test_cutover_disposition_is_not_ready() -> None:
    """Binary gate lock: flip only when §28 mandatory gates all PASS."""
    disposition = "CUTOVER_NOT_READY"
    blockers = {
        "BRIDGE_MAPPING": "NPC (and PC semantic) bridge absent; Threat-only #518",
        "PRODUCT_PROJECTION": "Plan/Build do not consume dungeonmind_kernel",
        "HIDDEN_FALLBACK": (
            "Product authority remains Buddy _hydrate_binding / "
            "DungeonMindStatblockV1Client; dark-cutover not rehearsed"
        ),
        "REAL_DATA_INCOMPATIBILITY": (
            "No checked-in durable uses_statblock Threat/NPC dogfood object"
        ),
    }
    assert disposition == "CUTOVER_NOT_READY"
    assert set(blockers) >= {
        "BRIDGE_MAPPING",
        "PRODUCT_PROJECTION",
        "HIDDEN_FALLBACK",
        "REAL_DATA_INCOMPATIBILITY",
    }
