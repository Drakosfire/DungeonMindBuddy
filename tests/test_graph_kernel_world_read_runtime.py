"""Lifecycle proofs for OPT01 resident world revision runtime (E2/E3/E5/E6)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

import graph_memory.kernel as kernel
from graph_memory.contribution_bundles import load_contribution_bundle
from graph_memory.kernel.world_initialization import initialize_world_from_contributions
from graph_memory.kernel.world_initialization_models import (
    PLAN_SCHEMA,
    WorldInitializationApprovalAttestation,
    WorldInitializationContribution,
    WorldInitializationPlan,
)
from graph_memory.evidence.assertion_support import DurableAssertionSupport
from graph_memory.kernel.world_projection import (
    WorldGraphProjectionError,
    _load_revision_store_with_integrity,
)
from graph_memory.kernel.world_read_runtime import (
    WorldReadRuntime,
    begin_request_io,
    clear_world_read_runtime,
    get_request_io,
    reset_request_io,
)
from graph_memory.projection.world_projection import (
    PROJECTION_REQUEST_SCHEMA,
    WorldGraphProjectionRequest,
)
from graph_memory.world_supergraph import paths as world_paths

REPO_ROOT = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
    REPO_ROOT
    / "graph_data/approved_contribution_bundles/eldyrwild-longmont-c2-initial-v1"
)
BUNDLE_DIGEST = (
    "5f8288d3052a9e59192884f2c35a13d51f665095d84cca2081a56638108d3fa5"
)
BUNDLE_ID = "eldyrwild-longmont-c2-initial-v1"
WORLD_ID = "eldyrwild"
CAMPAIGN_ID = "longmont-c2"
FOCUS_SESSION_ID = "session-23"
APPROVED_MERGE_SHA = "65ae001e0852d827ecd680200a965a576c705b1d"
ACTOR = "gm"
TRIPOD_CONTRIBUTION_ID = "contribution:022187fdefdf4557"

ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


@pytest.fixture
def loaded_bundle():
    return load_contribution_bundle(BUNDLE_PATH)


@pytest.fixture(autouse=True)
def _isolated_runtime() -> None:
    clear_world_read_runtime()
    reset_request_io()
    yield
    clear_world_read_runtime()
    reset_request_io()


def _plan(bundle) -> WorldInitializationPlan:
    by_id = {item.contribution_id: item for item in bundle.contributions}
    return WorldInitializationPlan(
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
            bundle_id=BUNDLE_ID,
            bundle_digest=BUNDLE_DIGEST,
            approved_bundle_merge_sha=APPROVED_MERGE_SHA,
        ),
    )


def _initialize(root: Path, bundle) -> kernel.WorldInitializationResult:
    return initialize_world_from_contributions(
        root,
        plan=_plan(bundle),
        contributions=list(bundle.contributions),
        actor=ACTOR,
    )


def _request(*, revision_pin: str | None = None) -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        revision_pin=revision_pin,
    )


def _revision_graph_path(root: Path, revision_id: str) -> Path:
    return world_paths.graph_payload_path(root, WORLD_ID, revision_id)


def _contribution_path(root: Path, contribution_id: str) -> Path:
    return world_paths.contribution_path(root, WORLD_ID, contribution_id)


def _fresh_runtime() -> WorldReadRuntime:
    clear_world_read_runtime()
    return WorldReadRuntime(capacity=8)


def _active_contribution_count(root: Path, revision_id: str) -> int:
    store = kernel.load_world_graph_revision(root, WORLD_ID, revision_id)
    ids: set[str] = set()
    for raw_support in store.assertion_support.values():
        support = DurableAssertionSupport.model_validate(raw_support)
        if support.support_state != "supported" or not support.active_contribution_ids:
            continue
        ids.update(support.active_contribution_ids)
    return len(ids)


def test_cold_then_warm_get_or_load_preserves_generation_and_io(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    revision_id = result.current_head_revision_id
    runtime = _fresh_runtime()

    begin_request_io()
    cold = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    cold_counters = get_request_io()
    assert cold_counters is not None
    assert cold_counters.graph_payload_reads == 1
    assert cold_counters.revision_manifest_reads == 1
    assert cold_counters.contribution_reads == _active_contribution_count(
        tmp_path,
        revision_id,
    )

    reset_request_io()
    begin_request_io()
    warm = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    warm_counters = get_request_io()
    assert warm_counters is not None
    assert warm.generation == cold.generation
    assert warm_counters.graph_payload_reads == 0
    assert warm_counters.revision_manifest_reads == 0
    assert warm_counters.contribution_reads == 0
    assert warm_counters.source_index_reads == 0


def test_coalesced_concurrent_cold_load_single_io_batch(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    revision_id = result.current_head_revision_id
    expected_contributions = _active_contribution_count(tmp_path, revision_id)
    runtime = _fresh_runtime()

    thread_count = 4
    start_barrier = threading.Barrier(thread_count + 1)
    release_load = threading.Event()
    errors: list[BaseException] = []
    residents: list = []
    worker_counters: list = []
    lock = threading.Lock()

    original_cold_load = runtime._cold_load

    def _gated_cold_load(*args, **kwargs):
        release_load.wait(timeout=30)
        return original_cold_load(*args, **kwargs)

    def _worker() -> None:
        try:
            start_barrier.wait(timeout=30)
            begin_request_io()
            resident = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
            counters = get_request_io()
            with lock:
                residents.append(resident)
                if counters is not None:
                    worker_counters.append(counters)
        except BaseException as exc:
            with lock:
                errors.append(exc)

    with patch.object(runtime, "_cold_load", side_effect=_gated_cold_load):
        threads = [threading.Thread(target=_worker) for _ in range(thread_count)]
        for thread in threads:
            thread.start()
        start_barrier.wait(timeout=30)
        release_load.set()
        for thread in threads:
            thread.join(timeout=30)

    assert not errors
    assert len(residents) == thread_count
    generations = {resident.generation for resident in residents}
    assert len(generations) == 1

    loader_counters = [
        counters
        for counters in worker_counters
        if counters.graph_payload_reads > 0 or counters.contribution_reads > 0
    ]
    assert len(loader_counters) == 1
    counters = loader_counters[0]
    assert counters.graph_payload_reads == 1
    assert counters.revision_manifest_reads == 1
    assert counters.contribution_reads == expected_contributions
    assert all(
        counters.graph_payload_reads == 0 and counters.contribution_reads == 0
        for counters in worker_counters
        if counters not in loader_counters
    )


def test_failed_cold_load_does_not_retain_resident_and_retry_succeeds(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    revision_id = result.current_head_revision_id
    graph_path = _revision_graph_path(tmp_path, revision_id)
    original_bytes = graph_path.read_bytes()
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    runtime = _fresh_runtime()
    thread_count = 2
    start_barrier = threading.Barrier(thread_count + 1)
    errors: list[BaseException] = []
    lock = threading.Lock()

    def _worker() -> None:
        try:
            start_barrier.wait(timeout=30)
            runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
        except BaseException as exc:
            with lock:
                errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(thread_count)]
    for thread in threads:
        thread.start()
    start_barrier.wait(timeout=30)
    for thread in threads:
        thread.join(timeout=30)

    assert len(errors) == thread_count
    assert all(isinstance(exc, WorldGraphProjectionError) for exc in errors)
    assert runtime.resident_count() == 0

    graph_path.write_bytes(original_bytes)
    repaired = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    assert runtime.resident_count() == 1
    assert repaired.key.revision_id == revision_id


def test_head_advance_while_revision_load_blocked(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    init_result = _initialize(tmp_path, loaded_bundle)
    revision_a = init_result.current_head_revision_id
    runtime = _fresh_runtime()

    load_started = threading.Event()
    release_load = threading.Event()
    original_integrity = _load_revision_store_with_integrity

    def _blocking_integrity(*args, **kwargs):
        if args[2] == revision_a:
            load_started.set()
            assert release_load.wait(timeout=30)
        return original_integrity(*args, **kwargs)

    blocked_error: list[BaseException] = []

    def _load_a() -> None:
        try:
            runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_a)
        except BaseException as exc:
            blocked_error.append(exc)

    loader = threading.Thread(target=_load_a)
    with patch(
        "graph_memory.kernel.world_read_runtime._load_revision_store_with_integrity",
        side_effect=_blocking_integrity,
    ):
        loader.start()
        assert load_started.wait(timeout=30)

        head, _revision, store = kernel.open_current_world_graph(tmp_path, WORLD_ID)
        published = kernel.publish_world_revision(
            tmp_path,
            WORLD_ID,
            store,
            operation_ids=["op:test-head-advance-blocked-load"],
            expected_parent_revision_id=revision_a,
        )
        revision_b = published.revision.revision_id
        assert revision_b != revision_a

        unpinned = runtime.resolve_projection_read_context(tmp_path, _request())
        assert unpinned.head_revision_id == revision_b
        assert unpinned.selected_revision_id == revision_b
        assert unpinned.selected.key.revision_id == revision_b

        release_load.set()
        loader.join(timeout=30)

    assert not blocked_error
    pinned_a = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_a)
    assert pinned_a.key.revision_id == revision_a
    assert runtime.resident_count() >= 2


def test_scrub_detects_backing_corruption_without_mutating_resident(
    tmp_path: Path,
    loaded_bundle,
) -> None:
    result = _initialize(tmp_path, loaded_bundle)
    revision_id = result.current_head_revision_id
    runtime = _fresh_runtime()

    resident = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    generation = resident.generation

    graph_path = _revision_graph_path(tmp_path, revision_id)
    payload = json.loads(graph_path.read_text(encoding="utf-8"))
    payload["campaign_id"] = "tampered-campaign-id"
    graph_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    contrib_path = _contribution_path(tmp_path, TRIPOD_CONTRIBUTION_ID)
    contrib_payload = json.loads(contrib_path.read_text(encoding="utf-8"))
    contrib_payload["accepted_assertions"][0]["label"] = "tampered-contribution"
    contrib_path.write_text(
        json.dumps(contrib_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    warm = runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    assert warm.generation == generation

    scrub = runtime.scrub_resident(tmp_path, WORLD_ID, revision_id)
    assert scrub["status"] == "unhealthy"

    runtime.clear()
    with pytest.raises(WorldGraphProjectionError) as exc_info:
        runtime.get_or_load_resident(tmp_path, WORLD_ID, revision_id)
    assert exc_info.value.code == "projection_integrity_error"
