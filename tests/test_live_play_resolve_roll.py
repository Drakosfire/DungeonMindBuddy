from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.live_play.resolve_roll import RollResolveError, resolve_roll_from_packet
from src.live_play.roll_table_registry import RollTableRegistry

ROOT = Path(__file__).resolve().parents[1]
PACKET_PATH = ROOT / "evals/c2_live_prep/live/session_22/live_packet.json"
EVENT_LOG = ROOT / "evals/c2_live_prep/live/session_22/event_log.jsonl"
JOB_QUEUE = ROOT / "evals/c2_live_prep/live/session_22/job_queue.jsonl"


@pytest.fixture
def packet() -> dict:
    return json.loads(PACKET_PATH.read_text(encoding="utf-8"))


def test_weather_7_resolves_t_wx_hail_dent(packet: dict) -> None:
    resolved = resolve_roll_from_packet(packet, "Weather 7.", root=ROOT)
    assert resolved.table_id == "T-WX"
    assert resolved.roll == 7
    assert "Hail dent" in resolved.row_text
    assert not resolved.row_text.endswith("|")
    assert resolved.row_locator == "pipe_row:d20=7"


def test_weather_7_without_period(packet: dict) -> None:
    resolved = resolve_roll_from_packet(packet, "Weather 7", root=ROOT)
    assert resolved.roll == 7
    assert not resolved.row_text.endswith("|")


def test_weather_16_resolves_t_wx_fixed_distance_front(packet: dict) -> None:
    resolved = resolve_roll_from_packet(packet, "Weather 16.", root=ROOT)
    assert resolved.table_id == "T-WX"
    assert resolved.roll == 16
    assert "Fixed-distance front" in resolved.row_text


def test_r5_54_resolves_band_crowd_hums(packet: dict) -> None:
    resolved = resolve_roll_from_packet(packet, "R5 54.", root=ROOT)
    assert resolved.table_id == "R5"
    assert resolved.roll == 54
    assert "Crowd hums one note" in resolved.row_text
    assert resolved.row_locator == "band:51-60:item=54"


def test_out_of_range_weather_returns_diagnostic(packet: dict) -> None:
    registry = RollTableRegistry.from_packet(packet, ROOT)
    with pytest.raises(RollResolveError) as exc_info:
        resolve_roll_from_packet(packet, "Weather 99.", root=ROOT)
    assert exc_info.value.diagnostic.code == "resolve_failed"


def test_unknown_table_returns_diagnostic(packet: dict) -> None:
    with pytest.raises(RollResolveError) as exc_info:
        resolve_roll_from_packet(packet, "T-UNKNOWN 5.", root=ROOT)
    assert exc_info.value.diagnostic.code == "unknown_table"


def test_resolver_does_not_mutate_committed_jsonl(packet: dict) -> None:
    before_event = EVENT_LOG.read_bytes()
    before_job = JOB_QUEUE.read_bytes()
    resolve_roll_from_packet(packet, "Weather 7.", root=ROOT)
    assert EVENT_LOG.read_bytes() == before_event
    assert JOB_QUEUE.read_bytes() == before_job
