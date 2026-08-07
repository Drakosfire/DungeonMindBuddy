"""OPT03 bounded projection recipe registry proofs (E1/E2)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from apps.live_control_server.services.world_graph_projection import project_world_graph
from apps.live_control_server.services.world_graph_projection_recipes import (
    get_recipe_observations,
    list_projection_recipe_keys_for_tests,
    projection_recipe_registry_stats,
    register_projection_recipe,
    reset_projection_recipes_for_tests,
    warm_projection_recipes_for_ready_revision,
)
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionRequest,
)
from graph_memory.world_projection_cache import clear_projection_cache

import graph_memory.kernel as kernel

BUNDLE_PATH = Path(
    "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture(autouse=True)
def _reset_recipe_state(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    reset_projection_recipes_for_tests()
    clear_projection_cache()
    kernel.clear_world_read_runtime()
    yield
    reset_projection_recipes_for_tests()
    clear_projection_cache()
    kernel.clear_world_read_runtime()


def _initialize(root: Path) -> None:
    bundle = load_contribution_bundle(BUNDLE_PATH)
    by_id = {item.contribution_id: item for item in bundle.contributions}
    plan = WorldInitializationPlan(
        schema=PLAN_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus_session_id=FOCUS_SESSION_ID,
        ordered_contributions=[
            WorldInitializationContribution(
                contribution_id=contribution_id,
                payload_sha256=kernel.compute_contribution_payload_sha256(
                    by_id[contribution_id]
                ),
            )
            for contribution_id in ORDERED_CONTRIBUTION_IDS
        ],
        approval_attestation=WorldInitializationApprovalAttestation(
            bundle_id="eldyrwild-longmont-c2-initial-v1",
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )
    initialize_world_from_contributions(
        root,
        plan=plan,
        contributions=list(bundle.contributions),
        actor="gm",
    )


def _request(
    *,
    revision_pin: str | None = None,
    query_text: str | None = None,
    campaign_id: str = CAMPAIGN_ID,
) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=campaign_id,
        revision_pin=revision_pin,
        query_text=query_text,
    )


def test_e1_eligibility_registers_unpinned_non_query_and_refreshes(
    tmp_path: Path,
) -> None:
    _initialize(tmp_path)
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    pinned_revision = next(
        path.name
        for path in sorted(
            (tmp_path / "graph_memory" / "worlds" / WORLD_ID / "revisions").iterdir()
        )
        if path.is_dir() and path.name != head.head_revision_id
    )
    project_world_graph(_request(revision_pin=pinned_revision), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 0

    project_world_graph(_request(query_text="Glowkindle"), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 0

    project_world_graph(_request(), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 1
    registered = [
        obs for obs in get_recipe_observations() if obs.status == "registered"
    ]
    assert len(registered) == 1

    project_world_graph(_request(), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 1
    refreshed = [
        obs for obs in get_recipe_observations() if obs.status == "refreshed"
    ]
    assert len(refreshed) == 1


def test_e1_register_projection_recipe_noop_when_cache_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", "0")
    _initialize(tmp_path)
    register_projection_recipe(_request(), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 0
    assert get_recipe_observations() == []


def test_e2_lru_capacity_evicts_oldest(tmp_path: Path) -> None:
    _initialize(tmp_path)
    reset_projection_recipes_for_tests(max_entries=2)
    for idx in range(3):
        register_projection_recipe(
            _request(campaign_id=f"campaign-{idx}"),
            root=tmp_path,
        )
    keys = list_projection_recipe_keys_for_tests()
    assert len(keys) == 2
    assert keys[0].campaign_id == "campaign-1"
    assert keys[1].campaign_id == "campaign-2"


def test_e2_ttl_expiry_drops_stale_recipes(tmp_path: Path) -> None:
    _initialize(tmp_path)
    clock = {"now": 1000.0}
    reset_projection_recipes_for_tests(
        max_entries=4,
        ttl_s=60.0,
        clock=lambda: clock["now"],
    )
    register_projection_recipe(_request(campaign_id="fresh"), root=tmp_path)
    clock["now"] = 1070.0
    warm_projection_recipes_for_ready_revision(
        root=tmp_path,
        world_id=WORLD_ID,
        revision_id=kernel.open_world_graph_head(tmp_path, WORLD_ID).head_revision_id,
        still_current=lambda: True,
    )
    assert projection_recipe_registry_stats()["size"] == 0


def test_e2_warm_batch_cap_and_root_world_filter(tmp_path: Path) -> None:
    _initialize(tmp_path)
    other_root = tmp_path / "other"
    other_root.mkdir()
    _initialize(other_root)
    reset_projection_recipes_for_tests(warm_batch=2)

    for idx in range(4):
        register_projection_recipe(
            _request(campaign_id=f"campaign-{idx}"),
            root=tmp_path,
        )
    register_projection_recipe(
        _request(campaign_id="other-world"),
        root=other_root,
    )

    revision_id = kernel.open_world_graph_head(tmp_path, WORLD_ID).head_revision_id

    with patch(
        "apps.live_control_server.services.world_graph_projection.project_world_graph",
        side_effect=lambda *_args, **_kwargs: None,
    ) as mocked:
        warm_projection_recipes_for_ready_revision(
            root=tmp_path,
            world_id=WORLD_ID,
            revision_id=revision_id,
            still_current=lambda: True,
        )
    assert mocked.call_count == 2


def test_e2_warm_does_not_refresh_recipe_ttl_or_mru(tmp_path: Path) -> None:
    """Background replay must not treat publication as fresh user demand."""
    _initialize(tmp_path)
    clock = {"now": 1000.0}
    reset_projection_recipes_for_tests(
        max_entries=4,
        ttl_s=60.0,
        warm_batch=4,
        clock=lambda: clock["now"],
    )
    register_projection_recipe(_request(campaign_id="older"), root=tmp_path)
    register_projection_recipe(_request(campaign_id="newer"), root=tmp_path)
    before = list_projection_recipe_keys_for_tests()
    assert [key.campaign_id for key in before] == ["older", "newer"]

    revision_id = kernel.open_world_graph_head(tmp_path, WORLD_ID).head_revision_id
    clock["now"] = 1040.0
    with patch(
        "apps.live_control_server.services.world_graph_projection.project_world_graph",
        side_effect=lambda *_args, **_kwargs: None,
    ):
        warm_projection_recipes_for_ready_revision(
            root=tmp_path,
            world_id=WORLD_ID,
            revision_id=revision_id,
            still_current=lambda: True,
        )

    after_warm = list_projection_recipe_keys_for_tests()
    assert [key.campaign_id for key in after_warm] == ["older", "newer"]

    # Original last_used_at was 1000; TTL 60s means expiry at 1060 even though
    # warm ran at 1040. If warm had refreshed recency, the recipe would survive.
    clock["now"] = 1061.0
    warm_projection_recipes_for_ready_revision(
        root=tmp_path,
        world_id=WORLD_ID,
        revision_id=revision_id,
        still_current=lambda: True,
    )
    assert projection_recipe_registry_stats()["size"] == 0
