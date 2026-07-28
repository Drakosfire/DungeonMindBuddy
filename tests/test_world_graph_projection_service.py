"""Service-boundary tests for PR007A world graph projection."""

from __future__ import annotations

import json
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
from graph_memory.world_projection_cache import (
    clear_projection_cache,
    make_projection_cache_key,
    projection_cache_stats,
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
ORDERED_CONTRIBUTION_IDS = [
    "contribution:82f23934d8eaca8a",
    "contribution:43782369bd717d32",
    "contribution:33d7cdb0ff623f28",
    "contribution:c086a0b72324ff16",
    "contribution:1227841724520c18",
    "contribution:022187fdefdf4557",
]


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


def _request() -> WorldGraphProjectionRequest:
    return WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
    )


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


def test_service_caches_warm_projection_hits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)

    first = project_world_graph(_request(), root=tmp_path)
    stats_after_first = projection_cache_stats()
    second = project_world_graph(_request(), root=tmp_path)
    stats_after_second = projection_cache_stats()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is second
    assert stats_after_first["misses"] >= 1
    assert stats_after_second["hits"] >= 1
    clear_projection_cache()


def test_service_cache_disabled_by_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", "0")
    clear_projection_cache()
    _initialize(tmp_path)

    first = project_world_graph(_request(), root=tmp_path)
    second = project_world_graph(_request(), root=tmp_path)
    stats = projection_cache_stats()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is not second
    assert stats["hits"] == 0
    assert stats["size"] == 0
    clear_projection_cache()


def test_service_cache_skips_query_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)

    request = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        query_text="Glowkindle",
    )
    first = project_world_graph(request, root=tmp_path)
    second = project_world_graph(request, root=tmp_path)
    stats = projection_cache_stats()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is not second
    assert stats["hits"] == 0
    assert stats["size"] == 0
    clear_projection_cache()


def test_service_cache_misses_after_ledger_fingerprint_change(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)

    first = project_world_graph(_request(), root=tmp_path)
    contrib_dir = tmp_path / "graph_memory" / "worlds" / WORLD_ID / "contributions"
    assert contrib_dir.is_dir()
    # Fingerprint digests every contribution filename + bytes; adding a file
    # must miss the warm cache without mutating the contribution index JSON.
    (contrib_dir / "contribution:cache-bust-probe.json").write_text("{}\n", encoding="utf-8")

    second = project_world_graph(_request(), root=tmp_path)
    stats = projection_cache_stats()

    assert first.snapshot.revision_id == second.snapshot.revision_id
    assert first is not second
    assert stats["misses"] >= 2
    clear_projection_cache()


def test_service_cache_keys_revision_pin_separately(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)

    head_projection = project_world_graph(_request(), root=tmp_path)
    pinned_request = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        revision_pin=head.head_revision_id,
    )
    pinned_key = make_projection_cache_key(
        tmp_path,
        pinned_request,
        revision_id=head.head_revision_id,
        head_revision_id=head.head_revision_id,
    )
    head_key = make_projection_cache_key(
        tmp_path,
        _request(),
        revision_id=head.head_revision_id,
        head_revision_id=head.head_revision_id,
    )
    assert pinned_key == head_key

    pinned = project_world_graph(pinned_request, root=tmp_path)
    stats = projection_cache_stats()
    assert pinned is head_projection
    assert stats["hits"] >= 1
    clear_projection_cache()


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


def _revision_manifest_path(root: Path, revision_id: str) -> Path:
    return (
        root
        / "graph_memory"
        / "worlds"
        / WORLD_ID
        / "revisions"
        / revision_id
        / "revision.json"
    )


def _head_path(root: Path) -> Path:
    return root / "graph_memory" / "worlds" / WORLD_ID / "head.json"


def test_service_cache_cannot_hide_graph_payload_integrity_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Warm hit must not survive graph.json mutation under a stable revision id."""
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)

    warm = project_world_graph(_request(), root=tmp_path)
    hits_before = projection_cache_stats()["hits"]
    graph_path = _revision_graph_path(tmp_path, warm.snapshot.revision_id)
    graph_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "projection_integrity_error"
    assert exc_info.value.status_code == 409
    assert projection_cache_stats()["hits"] == hits_before
    clear_projection_cache()


def test_service_cache_cannot_hide_revision_manifest_integrity_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)

    warm = project_world_graph(_request(), root=tmp_path)
    hits_before = projection_cache_stats()["hits"]
    manifest_path = _revision_manifest_path(tmp_path, warm.snapshot.revision_id)
    manifest_path.write_text("{not-valid-json", encoding="utf-8")

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "projection_integrity_error"
    assert exc_info.value.status_code == 409
    assert projection_cache_stats()["hits"] == hits_before
    clear_projection_cache()


def test_service_cache_cannot_hide_head_integrity_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Integrity-relevant head mutation must miss cache even when head still parses."""
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)

    project_world_graph(_request(), root=tmp_path)
    hits_before = projection_cache_stats()["hits"]
    head_path = _head_path(tmp_path)
    head_payload = json.loads(head_path.read_text(encoding="utf-8"))
    # Keep head_revision_id stable so a revision-id-only key would still hit.
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
    clear_projection_cache()


def test_service_cache_cannot_hide_head_revision_corruption_for_pinned_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pinned warm hit must not survive corruption of the head's target revision.

    The kernel validates head.head_revision_id even for pinned requests
    (headRevisionId / isHead metadata trusts it), so a cache key that
    fingerprints only the pinned revision would return the cached projection
    where the kernel would raise projection_integrity_error.
    """
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)
    head = kernel.open_world_graph_head(tmp_path, WORLD_ID)
    revisions_dir = tmp_path / "graph_memory" / "worlds" / WORLD_ID / "revisions"
    # Initialization publishes a revision chain; pick any provably historical
    # revision rather than assuming an ordering of content-addressed ids.
    pinned = next(
        path.name
        for path in sorted(revisions_dir.iterdir())
        if path.is_dir() and path.name != head.head_revision_id
    )
    pinned_request = WorldGraphProjectionRequest(
        schema=PROJECTION_REQUEST_SCHEMA,
        world_id=WORLD_ID,
        campaign_id=CAMPAIGN_ID,
        revision_pin=pinned,
    )

    warm = project_world_graph(pinned_request, root=tmp_path)
    assert warm.snapshot.revision_id == pinned
    hits_before = projection_cache_stats()["hits"]
    # Corrupt the head's target revision while leaving head.json unchanged.
    _revision_graph_path(tmp_path, head.head_revision_id).write_text(
        "{not-valid-json", encoding="utf-8"
    )

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(pinned_request, root=tmp_path)
    assert exc_info.value.code == "projection_integrity_error"
    assert exc_info.value.status_code == 409
    assert projection_cache_stats()["hits"] == hits_before
    clear_projection_cache()


def test_service_cache_cannot_hide_contribution_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Renaming a referenced contribution file must miss the warm cache.

    os.rename preserves both the file count and every file mtime, so an
    aggregate count + newest-mtime fingerprint stays stable; the kernel still
    fails integrity when the id-derived record path goes missing.
    """
    monkeypatch.delenv("DMB_WORLD_GRAPH_PROJECTION_CACHE", raising=False)
    clear_projection_cache()
    _initialize(tmp_path)

    project_world_graph(_request(), root=tmp_path)
    hits_before = projection_cache_stats()["hits"]
    contrib_dir = tmp_path / "graph_memory" / "worlds" / WORLD_ID / "contributions"
    referenced = sorted(contrib_dir.glob("*.json"))
    assert referenced
    metadata_before = (len(referenced), max(p.stat().st_mtime_ns for p in referenced))
    renamed = referenced[0].with_name("contribution__renamed_under_stable_metadata.json")
    referenced[0].rename(renamed)
    after = sorted(contrib_dir.glob("*.json"))
    # Prove the rename kept aggregate metadata stable: a count + newest-mtime
    # fingerprint would not have detected it.
    assert (len(after), max(p.stat().st_mtime_ns for p in after)) == metadata_before

    with pytest.raises(WorldGraphProjectionServiceError) as exc_info:
        project_world_graph(_request(), root=tmp_path)
    assert exc_info.value.code == "projection_integrity_error"
    assert exc_info.value.status_code == 409
    assert projection_cache_stats()["hits"] == hits_before
    clear_projection_cache()
