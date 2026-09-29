"""Tests for HermesSessionPointerStore concurrency and persistence."""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path

import pytest

from apps.live_control_server.services.hermes_session_store import HermesSessionPointerStore
from src.live_play.live_store import write_json


def test_write_json_uses_unique_temp_filenames(tmp_path: Path) -> None:
    target = tmp_path / "store.json"
    write_json(target, {"schema": "test", "value": 1})
    write_json(target, {"schema": "test", "value": 2})
    temps = list(tmp_path.glob(".*.tmp"))
    assert len(temps) == 0
    assert json.loads(target.read_text(encoding="utf-8"))["value"] == 2


def test_concurrent_upsert_from_two_instances_preserves_both_bindings(
    tmp_path: Path,
) -> None:
    base = tmp_path / "live-session"
    store_a = HermesSessionPointerStore(base)
    store_b = HermesSessionPointerStore(base)

    def upsert_a() -> None:
        for _ in range(20):
            store_a.upsert_after_turn(
                campaign_id="campaign:c1",
                agent_thread_id="thread-a",
                hermes_session_id="hermes-a",
            )

    def upsert_b() -> None:
        for _ in range(20):
            store_b.upsert_after_turn(
                campaign_id="campaign:c1",
                agent_thread_id="thread-b",
                hermes_session_id="hermes-b",
            )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(upsert_a),
            executor.submit(upsert_b),
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()

    store = HermesSessionPointerStore(base)
    binding_a = store.get_for_thread(
        campaign_id="campaign:c1",
        agent_thread_id="thread-a",
    )
    binding_b = store.get_for_thread(
        campaign_id="campaign:c1",
        agent_thread_id="thread-b",
    )
    assert binding_a is not None
    assert binding_b is not None
    assert binding_a.hermes_session_id == "hermes-a"
    assert binding_b.hermes_session_id == "hermes-b"


def test_structured_pointer_continuity_is_keyed_by_owner_work_and_thread(
    tmp_path: Path,
) -> None:
    base = tmp_path / "live-session"
    store = HermesSessionPointerStore(base)
    legacy = store.upsert_after_turn(
        campaign_id="campaign:c1",
        agent_thread_id="thread-1",
        hermes_session_id="legacy-session",
    )
    raw_before = json.loads((base / "hermes_thread_pointers.json").read_text())
    legacy_payload = raw_before["bindings"]["campaign:c1::thread-1"]

    first = store.upsert_structured_after_turn(
        owner_kind="world",
        owner_id="world:one",
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        hermes_session_id="structured-session-1",
    )
    assert first.pointer_id
    resolved = store.resolve_structured_for_request(
        owner_kind="world",
        owner_id="world:one",
        work_kind="plan",
        work_id="plan:one",
        agent_thread_id="thread-1",
        pointer_id=first.pointer_id,
    )
    assert resolved.continuity_session_id == "structured-session-1"
    assert resolved.pointer_status == "accepted"
    assert resolved.pointer_id == first.pointer_id

    wrong_work = store.resolve_structured_for_request(
        owner_kind="world",
        owner_id="world:one",
        work_kind="plan",
        work_id="plan:two",
        agent_thread_id="thread-1",
        pointer_id=first.pointer_id,
    )
    assert wrong_work.continuity_session_id is None
    assert wrong_work.pointer_status == "recovered"

    raw_after = json.loads((base / "hermes_thread_pointers.json").read_text())
    assert raw_after["bindings"]["campaign:c1::thread-1"] == legacy_payload
    assert store.get_for_thread(
        campaign_id="campaign:c1", agent_thread_id="thread-1"
    ) == legacy


def test_structured_binding_reuses_exact_key_and_returns_pointer_without_echo(
    tmp_path: Path,
) -> None:
    store = HermesSessionPointerStore(tmp_path / "live-session")
    created = store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind=None,
        work_id=None,
        agent_thread_id="thread-index",
        hermes_session_id="provider-session-1",
    )
    resolved = store.resolve_structured_for_request(
        owner_kind=None,
        owner_id=None,
        work_kind=None,
        work_id=None,
        agent_thread_id="thread-index",
        pointer_id=None,
    )
    assert resolved.continuity_session_id == "provider-session-1"
    assert resolved.pointer_status == "absent"
    assert resolved.pointer_id == created.pointer_id
    updated = store.upsert_structured_after_turn(
        owner_kind=None,
        owner_id=None,
        work_kind=None,
        work_id=None,
        agent_thread_id="thread-index",
        hermes_session_id="provider-session-2",
    )
    assert updated.pointer_id == created.pointer_id


@pytest.mark.parametrize(
    ("field", "tampered_value"),
    [
        ("schema", "dmb_hermes_structured_session_pointer_binding_v0"),
        ("agent_thread_id", "thread-other"),
        ("owner_kind", "campaign"),
        ("owner_id", "world:other"),
        ("work_kind", "build"),
        ("work_id", "plan:other"),
    ],
)
def test_structured_pointer_rejects_stored_schema_or_identity_drift(
    tmp_path: Path, field: str, tampered_value: str
) -> None:
    base = tmp_path / "live-session"
    store = HermesSessionPointerStore(base)
    identity = {
        "owner_kind": "world",
        "owner_id": "world:one",
        "work_kind": "plan",
        "work_id": "plan:one",
        "agent_thread_id": "thread-one",
    }
    original = store.upsert_structured_after_turn(
        **identity,
        hermes_session_id="session-original",
    )
    path = base / "hermes_thread_pointers.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    key = next(iter(payload["structured_bindings"]))
    payload["structured_bindings"][key][field] = tampered_value
    path.write_text(json.dumps(payload), encoding="utf-8")

    recovered = store.resolve_structured_for_request(
        **identity,
        pointer_id=original.pointer_id,
    )
    assert recovered.continuity_session_id is None
    assert recovered.pointer_status == "recovered"
    assert recovered.pointer_id is None

    fresh = store.upsert_structured_after_turn(
        **identity,
        hermes_session_id="session-fresh",
    )
    assert fresh.pointer_id != original.pointer_id
    assert fresh.hermes_session_id == "session-fresh"
    corrected = store.resolve_structured_for_request(
        **identity,
        pointer_id=fresh.pointer_id,
    )
    assert corrected.continuity_session_id == "session-fresh"
