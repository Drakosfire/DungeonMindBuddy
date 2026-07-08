"""Tests for authored graph overlay file-backed store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from apps.live_control_server.models.graph_authoring_overlay import (
    UnsafeCampaignIdError,
    UnsafeCampaignRelError,
    create_empty_authored_graph_overlay,
    default_graph_authoring_provenance,
)
from apps.live_control_server.services.graph_authoring_overlay_store import (
    BACKUPS_DIR,
    EVENTS_DIR,
    GRAPH_AUTHORING_DIR,
    OVERLAYS_DIR,
    OVERLAY_FILENAME,
    GraphAuthoringOverlayStore,
)
from tests.test_graph_authoring_overlay_models import (
    CAMPAIGN_ID,
    STAMP,
    link_existing_assertion,
    object_assertion,
    relationship_assertion,
)

TEST_CAMPAIGN_REL = "Test Campaign/A4"


@pytest.fixture
def corpus_root(tmp_path: Path) -> Path:
    return tmp_path / "corpus"


@pytest.fixture
def store(corpus_root: Path) -> GraphAuthoringOverlayStore:
    return GraphAuthoringOverlayStore(corpus_root)


def test_overlay_path_is_under_graph_authoring_root(store: GraphAuthoringOverlayStore) -> None:
    path = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert GRAPH_AUTHORING_DIR in path.parts
    assert OVERLAYS_DIR in path.parts
    assert path.name == OVERLAY_FILENAME
    expected_root = store.corpus_root / TEST_CAMPAIGN_REL / GRAPH_AUTHORING_DIR
    assert path.is_relative_to(expected_root)


def test_events_and_backups_path_helpers(store: GraphAuthoringOverlayStore) -> None:
    root = store.campaign_graph_authoring_root(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert store.events_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL) == root / EVENTS_DIR / "graph_authoring_events.jsonl"
    assert store.backups_dir(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL) == root / BACKUPS_DIR


def test_missing_overlay_loads_as_empty_valid_overlay(
    store: GraphAuthoringOverlayStore,
) -> None:
    overlay = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert overlay.campaign_id == CAMPAIGN_ID
    assert overlay.assertions == []
    assert overlay.schema_version == "dmb.authored_graph_overlay.v1"


def test_overlay_save_load_roundtrip(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP)
    overlay = overlay.model_copy(
        update={
            "assertions": [
                object_assertion(),
                link_existing_assertion(),
                relationship_assertion(),
            ]
        }
    )
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    loaded = store.load_overlay(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert len(loaded.assertions) == 3
    assert loaded.model_dump(mode="json") == overlay.model_dump(mode="json")


def test_append_assertions_preserves_existing_assertions(
    store: GraphAuthoringOverlayStore,
) -> None:
    first = object_assertion(assertion_id="assert-object-1")
    second = link_existing_assertion(assertion_id="assert-link-2")
    store.append_assertions(CAMPAIGN_ID, [first], campaign_rel=TEST_CAMPAIGN_REL)
    updated = store.append_assertions(CAMPAIGN_ID, [second], campaign_rel=TEST_CAMPAIGN_REL)
    assert len(updated.assertions) == 2
    assert updated.assertions[0].assertion_id == "assert-object-1"
    assert updated.assertions[1].assertion_id == "assert-link-2"


def test_append_assertions_upserts_same_assertion_id(
    store: GraphAuthoringOverlayStore,
) -> None:
    original = object_assertion(assertion_id="assert-object-1")
    original.object_ref = original.object_ref.model_copy(update={"label": "Heroes"})
    revised = object_assertion(assertion_id="assert-object-1")
    revised.object_ref = revised.object_ref.model_copy(update={"label": "The Heroes"})
    store.append_assertions(CAMPAIGN_ID, [original], campaign_rel=TEST_CAMPAIGN_REL)
    updated = store.append_assertions(CAMPAIGN_ID, [revised], campaign_rel=TEST_CAMPAIGN_REL)
    assert len(updated.assertions) == 1
    assert updated.assertions[0].object_ref.label == "The Heroes"


def test_list_assertions_returns_overlay_assertions(store: GraphAuthoringOverlayStore) -> None:
    assertion = relationship_assertion()
    store.append_assertions(CAMPAIGN_ID, [assertion], campaign_rel=TEST_CAMPAIGN_REL)
    listed = store.list_assertions(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert len(listed) == 1
    assert listed[0].assertion_id == assertion.assertion_id


def test_save_creates_parent_directories(store: GraphAuthoringOverlayStore) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP)
    path = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    assert not path.parent.is_dir()
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    assert path.is_file()


@pytest.mark.parametrize(
    "unsafe_id",
    [
        "../longmont-c1",
        "/longmont-c1",
        "longmont/c1",
        "..",
        "",
        "   ",
    ],
)
def test_unsafe_campaign_ids_are_rejected(
    store: GraphAuthoringOverlayStore,
    unsafe_id: str,
) -> None:
    with pytest.raises(UnsafeCampaignIdError):
        store.overlay_path(unsafe_id, campaign_rel=TEST_CAMPAIGN_REL)


@pytest.mark.parametrize(
    "unsafe_rel",
    [
        "../outside",
        "/absolute/campaign",
        "Test Campaign/../../outside",
        "..",
        "",
        "   ",
        "file:///tmp/evil",
    ],
)
def test_unsafe_campaign_rel_values_are_rejected(
    store: GraphAuthoringOverlayStore,
    unsafe_rel: str,
) -> None:
    with pytest.raises(UnsafeCampaignRelError):
        store.overlay_path(CAMPAIGN_ID, campaign_rel=unsafe_rel)


def test_save_overlay_rejects_campaign_rel_that_escapes_corpus_root(
    store: GraphAuthoringOverlayStore,
    tmp_path: Path,
) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP)
    # Symlink-style escape: rel resolves outside corpus_root when joined.
    outside = tmp_path / "outside"
    outside.mkdir()
    evil_rel = "../outside"
    with pytest.raises(UnsafeCampaignRelError):
        store.save_overlay(overlay, campaign_rel=evil_rel)


def test_atomic_write_leaves_valid_json_on_happy_path(
    store: GraphAuthoringOverlayStore,
) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP)
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    path = store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "dmb.authored_graph_overlay.v1"
    assert not path.with_name(f".{path.name}.tmp").exists()


def test_store_uses_temp_directory_not_real_corpus(
    store: GraphAuthoringOverlayStore,
    corpus_root: Path,
) -> None:
    overlay = create_empty_authored_graph_overlay(CAMPAIGN_ID, created_at=STAMP)
    store.save_overlay(overlay, campaign_rel=TEST_CAMPAIGN_REL)
    assert store.overlay_path(CAMPAIGN_ID, campaign_rel=TEST_CAMPAIGN_REL).is_relative_to(corpus_root)


def test_append_rejects_mismatched_assertion_campaign_id(
    store: GraphAuthoringOverlayStore,
) -> None:
    assertion = object_assertion(campaign_id="longmont-c2")
    with pytest.raises(ValueError, match="campaign_id must match"):
        store.append_assertions(CAMPAIGN_ID, [assertion], campaign_rel=TEST_CAMPAIGN_REL)


def test_provenance_factory_defaults() -> None:
    provenance = default_graph_authoring_provenance()
    assert provenance.origin == "human_authored"
    assert provenance.authoring_surface == "memory_ingest_graph_authoring"
    assert provenance.created_at.endswith("Z")
