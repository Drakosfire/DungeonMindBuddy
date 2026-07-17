"""Tests for HermesSessionPointerStore concurrency and persistence."""

from __future__ import annotations

import concurrent.futures
import json
from pathlib import Path

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
