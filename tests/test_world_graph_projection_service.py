"""Service-boundary tests for PR007A world graph projection (OPT01 resident trust)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.services.world_graph_projection import (
    WorldGraphProjectionServiceError,
    project_world_graph,
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
from graph_memory import world_projection_cache as projection_cache_module
from graph_memory.world_projection_cache import (
    clear_projection_cache,
    make_projection_cache_key,
    projection_cache_stats,
    reset_projection_cache_single_flight_for_tests,
)
from apps.live_control_server.services.world_graph_projection_recipes import (
    projection_recipe_registry_stats,
    reset_projection_recipes_for_tests,
)

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
TRIPOD_CONTRIBUTION_ID = "contribution:022187fdefdf4557"
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture(autouse=True)
def _clear_runtime_and_cache() -> None:
    clear_projection_cache()
    reset_projection_cache_single_flight_for_tests()
    reset_projection_recipes_for_tests()
    kernel.clear_world_read_runtime()
    yield
    clear_projection_cache()
    reset_projection_cache_single_flight_for_tests()
    reset_projection_recipes_for_tests()
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


def _request(*, revision_pin: str | None = None, query_text: str | None = None) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        revision_pin=revision_pin,
        query_text=query_text,
    )


def _revision_graph_path(root: Path, revision_id: str) -> Path:
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "graph.json"
    )


def _contribution_path(root: Path, contribution_id: str) -> Path:
    safe_id = contribution_id.replace(":", "__")
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "contributions"
        / f"{safe_id}.json"
    )


def _head_path(root: Path) -> Path:
    return root / "graph_memory" / "worlds" / WORLD_ID / "head.json"


def _historical_revision(root: Path, head_revision_id: str) -> str:
    revisions_dir = root / "graph_memory" / "worlds" / WORLD_ID / "revisions"
    return next(
        path.name
        for path in sorted(revisions_dir.iterdir())
        if path.is_dir() and path.name != head_revision_id
    )


def _observation() -> kernel.ProjectionRequestObservation:
    observation = kernel.get_last_projection_observation()
    assert observation is not None
    return observation


def test_service_uses_configured_root_and_kernel_boundary(tmp_path: Path) -> None:
    _initialize(tmp_path)
    configured = tmp_path / "configured-world-root"
    configured.mkdir()
    _initialize(configured)

    with patch(
        "apps.live_control_server.services.world_graph_projection.world_graph_root",
        return_value=configured,
    ):
        projection = project_world_graph(_request())

    assert projection.summary.node_count == 12
    head, _revision, _store = kernel.open_current_world_graph(configured, WORLD_ID)
    assert projection.snapshot.revision_id == head.head_revision_id


def test_service_maps_kernel_errors(tmp_path: Path) -> None:
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "world_graph_unavailable"
    assert exc_info.value.status_code == 404


def test_service_caches_warm_projection_hits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    first = project_world_graph(_request(), root=tmp_path)
    second = project_world_graph(_request(), root=tmp_path)
    observation = _observation()
    stats = projection_cache_stats()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is second
    assert stats["hits"] >= 1
    assert observation.projection_cache_status == "hit"
    assert observation.graph_payload_reads_this_request == 0
    assert observation.contribution_reads_this_request == 0


def test_service_cache_disabled_by_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", "0")
    _initialize(tmp_path)

    first = project_world_graph(_request(), root=tmp_path)
    second = project_world_graph(_request(), root=tmp_path)
    observation = _observation()
    stats = projection_cache_stats()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is not second
    assert stats["hits"] == 0
    assert stats["size"] == 0
    assert observation.projection_cache_status == "disabled"
    assert observation.graph_payload_reads_this_request == 0
    assert observation.contribution_reads_this_request == 0


def test_service_cache_includes_query_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    request = _request(query_text="Glowkindle")
    first = project_world_graph(request, root=tmp_path)
    second = project_world_graph(request, root=tmp_path)
    observation = _observation()
    stats = projection_cache_stats()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is second
    assert stats["hits"] >= 1
    assert observation.projection_cache_status == "hit"


def test_service_cache_keys_revision_pin_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    pinned_revision = _historical_revision(tmp_path, head.head_revision_id)

    context = kernel.resolve_projection_read_context(tmp_path, _request())
    pinned_context = kernel.resolve_projection_read_context(
        tmp_path,
        _request(revision_pin=pinned_revision),
    )
    head_key = make_projection_cache_key(
        tmp_path,
        _request(),
        revision_id=context.selected_revision_id,
        head_revision_id=context.head_revision_id,
        selected_resident_generation=context.selected.generation,
        head_resident_generation=context.head.generation,
    )
    pinned_key = make_projection_cache_key(
        tmp_path,
        _request(revision_pin=pinned_revision),
        revision_id=pinned_context.selected_revision_id,
        head_revision_id=pinned_context.head_revision_id,
        selected_resident_generation=pinned_context.selected.generation,
        head_resident_generation=pinned_context.head.generation,
    )
    assert pinned_key != head_key

    head_projection = project_world_graph(_request(), root=tmp_path)
    pinned_request = _request(revision_pin=pinned_revision)
    pinned = project_world_graph(pinned_request, root=tmp_path)
    stats_after_first_pin = projection_cache_stats()
    pinned_again = project_world_graph(pinned_request, root=tmp_path)
    observation = _observation()

    assert pinned.snapshot.revision_id == pinned_revision
    assert pinned is not head_projection
    assert stats_after_first_pin["hits"] == 0
    assert pinned is pinned_again
    assert observation.projection_cache_status == "hit"


def test_resident_warm_reads_ignore_graph_and_contribution_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    warm = project_world_graph(_request(), root=tmp_path)
    revision_id = warm.snapshot.revision_id

    graph_path = _revision_graph_path(tmp_path, revision_id)
    graph_payload = json.loads(graph_path.read_text(encoding="utf-8"))
    graph_payload["campaign_id"] = "tampered-campaign-id"
    graph_path.write_text(
        json.dumps(graph_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    contrib_path = _contribution_path(tmp_path, TRIPOD_CONTRIBUTION_ID)
    contrib_payload = json.loads(contrib_path.read_text(encoding="utf-8"))
    contrib_payload["accepted_assertions"][0]["label"] = "tampered-contribution"
    contrib_path.write_text(
        json.dumps(contrib_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    same_request = project_world_graph(_request(), root=tmp_path)
    different_query = project_world_graph(
        _request(query_text="Glowkindle"),
        root=tmp_path,
    )
    observation = _observation()

    assert same_request.snapshot.revision_id == revision_id
    assert different_query.snapshot.revision_id == revision_id
    assert same_request.model_dump() == warm.model_dump()
    assert observation.graph_payload_reads_this_request == 0
    assert observation.contribution_reads_this_request == 0
    assert observation.source_index_reads_this_request == 0


def test_head_corruption_fails_closed_while_resident_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    project_world_graph(_request(), root=tmp_path)
    hits_before = projection_cache_stats()["hits"]

    head_path = _head_path(tmp_path)
    head_payload = json.loads(head_path.read_text(encoding="utf-8"))
    head_payload["world_id"] = "tampered-world"
    head_path.write_text(
        json.dumps(head_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "projection_integrity_error"
    assert exc_info.value.status_code == 409
    assert projection_cache_stats()["hits"] == hits_before


def test_scrub_and_clear_reverify_after_backing_corruption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    warm = project_world_graph(_request(), root=tmp_path)
    revision_id = warm.snapshot.revision_id

    graph_path = _revision_graph_path(tmp_path, revision_id)
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    still_warm = project_world_graph(_request(), root=tmp_path)
    assert still_warm.snapshot.revision_id == revision_id

    runtime = kernel.get_world_read_runtime()
    scrub = runtime.scrub_resident(tmp_path, WORLD_ID, revision_id)
    assert scrub["status"] == "unhealthy"

    kernel.clear_world_read_runtime()
    clear_projection_cache()

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "projection_integrity_error"
    assert exc_info.value.status_code == 409


def test_payload_cache_cannot_survive_runtime_clear_generation_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    first = project_world_graph(_request(), root=tmp_path)
    assert _observation().projection_cache_status == "miss"
    assert projection_cache_stats()["size"] == 1

    kernel.clear_world_read_runtime()

    second = project_world_graph(_request(), root=tmp_path)
    second_observation = _observation()
    assert second.snapshot.revision_id == first.snapshot.revision_id
    assert second is not first
    assert second_observation.projection_cache_status == "miss"

    third = project_world_graph(_request(), root=tmp_path)
    third_observation = _observation()
    assert third is second
    assert third_observation.projection_cache_status == "hit"


def test_service_unpinned_uses_new_head_after_advance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After head advance, unpinned requests use the new head, not a stale cache."""
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    head_a, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
    at_head_a = project_world_graph(_request(), root=tmp_path)
    assert at_head_a.snapshot.revision_id == head_a.head_revision_id

    published = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        store,
        operation_ids=["op:test-service-head-advance"],
        expected_parent_revision_id=head_a.head_revision_id,
    )
    revision_b = published.revision.revision_id
    assert revision_b != head_a.head_revision_id

    at_head_b = project_world_graph(_request(), root=tmp_path)
    observation = _observation()

    assert at_head_b.snapshot.revision_id == revision_b
    assert at_head_b is not at_head_a
    assert observation.projection_cache_status == "miss"


def test_blank_campaign_invalid_request_precedes_storage_error(tmp_path: Path) -> None:
    """Blank campaign_id must fail as invalid_request before missing-world storage."""
    blank = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id="   ",
    )
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(blank, root=tmp_path)
    assert exc_info.value.code == "invalid_request"
    assert exc_info.value.status_code == 400
    observation = _observation()
    assert observation.campaign_id == "   "
    assert observation.graph_payload_reads_this_request == 0
    assert observation.revision_manifest_reads_this_request == 0


def test_service_emits_observation_on_storage_error(tmp_path: Path) -> None:
    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "world_graph_unavailable"
    observation = _observation()
    assert observation.world_id == WORLD_ID
    assert observation.campaign_id == CAMPAIGN_ID


def test_mismatched_projection_context_is_rejected(tmp_path: Path) -> None:
    _initialize(tmp_path)
    other = tmp_path / "other-root"
    other.mkdir()
    _initialize(other)

    request = _request()
    foreign_context = kernel.resolve_projection_read_context(other, request)
    with pytest.raises(kernel.WorldGraphProjectionError) as exc_info:
        kernel.project_world_graph_from_context(tmp_path, request, foreign_context)
    assert exc_info.value.code == "projection_internal_error"
    assert "resolved_root" in str(exc_info.value.diagnostics[0].message)


def test_deterministic_read_counts_across_focus_pin_and_clear(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from graph_memory.projection.world_projection import WorldGraphProjectionFocus

    monkeypatch.setenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", "0")
    _initialize(tmp_path)
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    pinned_revision = _historical_revision(tmp_path, head.head_revision_id)

    cold = project_world_graph(_request(), root=tmp_path)
    cold_obs = _observation()
    assert cold_obs.resident_status == "miss"
    assert cold_obs.graph_payload_reads_this_request == 1
    assert cold_obs.revision_manifest_reads_this_request == 1
    assert cold_obs.contribution_reads_this_request > 0
    cold_contributions = cold_obs.contribution_reads_this_request

    warm = project_world_graph(_request(), root=tmp_path)
    warm_obs = _observation()
    assert warm.snapshot.revision_id == cold.snapshot.revision_id
    assert warm_obs.resident_status == "hit"
    assert warm_obs.graph_payload_reads_this_request == 0
    assert warm_obs.revision_manifest_reads_this_request == 0
    assert warm_obs.contribution_reads_this_request == 0
    assert warm_obs.source_index_reads_this_request == 0

    focused = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        focus=WorldGraphProjectionFocus(kind="session", session_id=FOCUS_SESSION_ID),
    )
    focus_proj = project_world_graph(focused, root=tmp_path)
    focus_obs = _observation()
    assert focus_proj.snapshot.focus.kind == "session"
    assert focus_obs.resident_status == "hit"
    assert focus_obs.graph_payload_reads_this_request == 0
    assert focus_obs.contribution_reads_this_request == 0

    # Admit the historical pin before head advances so the later pinned request
    # can prove selected-resident reuse.
    project_world_graph(_request(revision_pin=pinned_revision), root=tmp_path)

    published = kernel.publish_world_revision(
        tmp_path,
        WORLD_ID,
        kernel.load_world_graph_revision(tmp_path, WORLD_ID, head.head_revision_id),
        operation_ids=["op:test-deterministic-pin-after-advance"],
        expected_parent_revision_id=head.head_revision_id,
    )
    assert published.revision.revision_id != head.head_revision_id

    pinned = project_world_graph(
        _request(revision_pin=pinned_revision),
        root=tmp_path,
    )
    pinned_obs = _observation()
    assert pinned.snapshot.revision_id == pinned_revision
    assert pinned.snapshot.head_revision_id == published.revision.revision_id
    # Selected pin is a resident hit; only the new head may cold-load.
    assert pinned_obs.resident_status == "hit"
    assert pinned_obs.graph_payload_reads_this_request == 1
    assert pinned_obs.revision_manifest_reads_this_request == 1
    assert pinned_obs.contribution_reads_this_request == cold_contributions

    kernel.clear_world_read_runtime()
    clear_projection_cache()
    post_clear = project_world_graph(_request(), root=tmp_path)
    post_clear_obs = _observation()
    assert post_clear.snapshot.revision_id == published.revision.revision_id
    assert post_clear_obs.resident_status == "miss"
    assert post_clear_obs.graph_payload_reads_this_request == 1
    assert post_clear_obs.revision_manifest_reads_this_request == 1
    assert post_clear_obs.contribution_reads_this_request > 0


def test_e1_service_registers_eligible_recipe_not_pin_or_query(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    project_world_graph(_request(), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 1

    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    pinned_revision = _historical_revision(tmp_path, head.head_revision_id)
    project_world_graph(_request(revision_pin=pinned_revision), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 1

    project_world_graph(_request(query_text="Glowkindle"), root=tmp_path)
    assert projection_recipe_registry_stats()["size"] == 1


def test_e3_concurrent_identical_miss_builds_once_and_coalesces(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    build_started = threading.Event()
    release_build = threading.Event()
    build_count = {"n": 0}
    original = kernel.project_world_graph_from_context

    def _gated_build(*args, **kwargs):
        build_count["n"] += 1
        build_started.set()
        assert release_build.wait(timeout=30.0)
        return original(*args, **kwargs)

    errors: list[BaseException] = []
    results: list = []
    waiter_observation: list[kernel.ProjectionRequestObservation] = []

    def _call(*, record_observation: bool = False) -> None:
        try:
            results.append(project_world_graph(_request(), root=tmp_path))
            if record_observation:
                observation = kernel.get_last_projection_observation()
                if observation is not None:
                    waiter_observation.append(observation)
        except BaseException as exc:
            errors.append(exc)

    with patch.object(kernel, "project_world_graph_from_context", side_effect=_gated_build):
        first = threading.Thread(target=_call)
        second = threading.Thread(target=_call, kwargs={"record_observation": True})
        first.start()
        assert build_started.wait(timeout=30.0)
        second.start()
        time.sleep(0.05)
        release_build.set()
        first.join(timeout=30.0)
        second.join(timeout=30.0)

    assert not errors
    assert build_count["n"] == 1
    assert len(results) == 2
    assert results[0] is results[1]
    assert len(waiter_observation) == 1
    assert waiter_observation[0].projection_cache_status == "coalesced"


def test_e3_builder_failure_propagates_without_cache_and_retry_works(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    build_started = threading.Event()
    release_build = threading.Event()
    attempts = {"n": 0}
    original = kernel.project_world_graph_from_context

    def _failing_then_ok(*args, **kwargs):
        attempts["n"] += 1
        build_started.set()
        assert release_build.wait(timeout=30.0)
        if attempts["n"] == 1:
            raise kernel.WorldGraphProjectionError(
                "simulated build failure",
                code="projection_internal_error",
                status_code=500,
            )
        return original(*args, **kwargs)

    errors: list[BaseException] = []

    def _call() -> None:
        try:
            project_world_graph(_request(), root=tmp_path)
        except BaseException as exc:
            errors.append(exc)

    with patch.object(kernel, "project_world_graph_from_context", side_effect=_failing_then_ok):
        first = threading.Thread(target=_call)
        second = threading.Thread(target=_call)
        first.start()
        assert build_started.wait(timeout=30.0)
        second.start()
        time.sleep(0.05)
        release_build.set()
        first.join(timeout=30.0)
        second.join(timeout=30.0)

    assert len(errors) == 2
    assert projection_cache_stats()["size"] == 0

    project_world_graph(_request(), root=tmp_path)
    assert projection_cache_stats()["size"] == 1


def test_e7_cache_disabled_skips_recipes_and_single_flight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", "0")
    _initialize(tmp_path)

    first = project_world_graph(_request(), root=tmp_path)
    second = project_world_graph(_request(), root=tmp_path)
    observation = _observation()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is not second
    assert projection_recipe_registry_stats()["size"] == 0
    assert projection_cache_stats()["size"] == 0
    assert observation.projection_cache_status == "disabled"


def test_e3_clear_during_build_does_not_repopulate_completed_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    build_started = threading.Event()
    release_build = threading.Event()
    original = kernel.project_world_graph_from_context
    errors: list[BaseException] = []

    def _gated_build(*args, **kwargs):
        build_started.set()
        assert release_build.wait(timeout=30.0)
        return original(*args, **kwargs)

    def _call() -> None:
        try:
            project_world_graph(_request(), root=tmp_path)
        except BaseException as exc:
            errors.append(exc)

    with patch.object(kernel, "project_world_graph_from_context", side_effect=_gated_build):
        builder = threading.Thread(target=_call)
        builder.start()
        assert build_started.wait(timeout=30.0)
        clear_projection_cache()
        release_build.set()
        builder.join(timeout=30.0)

    assert len(errors) == 1
    # Service maps the single-flight reset into the stable internal-error envelope.
    assert isinstance(errors[0], WorldGraphProjectionServiceError)
    assert errors[0].code == "projection_internal_error"
    assert projection_cache_stats()["size"] == 0


def _run_builder_paused_after_build(
    tmp_path: Path,
) -> tuple[threading.Thread, threading.Event, threading.Event, list[BaseException]]:
    after_build = threading.Event()
    release_publish = threading.Event()
    errors: list[BaseException] = []

    def _after_builder_before_publish() -> None:
        after_build.set()
        assert release_publish.wait(timeout=30.0)

    def _call() -> None:
        try:
            project_world_graph(_request(), root=tmp_path)
        except BaseException as exc:
            errors.append(exc)

    projection_cache_module._after_builder_before_publish_hook = (
        _after_builder_before_publish
    )
    builder = threading.Thread(target=_call)
    builder.start()
    assert after_build.wait(timeout=30.0)
    return builder, after_build, release_publish, errors


def test_e3_clear_after_builder_before_publish_leaves_cache_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Production clear invalidates builders paused after builder() returns."""
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    previous_hook = projection_cache_module._after_builder_before_publish_hook
    release_publish: threading.Event | None = None
    try:
        builder, _after_build, release_publish, errors = _run_builder_paused_after_build(
            tmp_path
        )
        clear_projection_cache()
        release_publish.set()
        builder.join(timeout=30.0)
    finally:
        projection_cache_module._after_builder_before_publish_hook = previous_hook
        if release_publish is not None:
            release_publish.set()

    assert len(errors) == 1
    assert isinstance(errors[0], WorldGraphProjectionServiceError)
    assert errors[0].code == "projection_internal_error"
    assert projection_cache_stats()["size"] == 0


def test_e3_completed_clear_before_generation_bump_allows_republish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The unsafe ordering: empty completed cache, then let an old builder put.

    Production ``clear_projection_cache`` must not separate these steps. This
    test performs only the completed-cache clear so the paused builder can
    still pass its generation check and republish — proving why bump+clear
    must share the publish lock.
    """
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    _initialize(tmp_path)

    previous_hook = projection_cache_module._after_builder_before_publish_hook
    release_publish: threading.Event | None = None
    try:
        builder, _after_build, release_publish, errors = _run_builder_paused_after_build(
            tmp_path
        )
        # Deliberately omit the generation bump / in-flight invalidation.
        projection_cache_module._PROJECTION_CACHE.clear()
        release_publish.set()
        builder.join(timeout=30.0)
    finally:
        projection_cache_module._after_builder_before_publish_hook = previous_hook
        if release_publish is not None:
            release_publish.set()

    assert errors == []
    assert projection_cache_stats()["size"] == 1
    clear_projection_cache()
    assert projection_cache_stats()["size"] == 0
