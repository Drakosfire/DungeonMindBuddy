from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools/stage4l_c1_s1_s10_chronological_graph_rehearsal.py"
SPEC = importlib.util.spec_from_file_location("stage4l", TOOL)
assert SPEC and SPEC.loader
stage4l = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stage4l
SPEC.loader.exec_module(stage4l)


def test_census_freezes_exact_raw_cohort_and_six_pcs() -> None:
    payload = stage4l.census()
    assert payload["source_count"] == 10
    assert [row["session"] for row in payload["sessions"]] == list(range(1, 11))
    assert all("/_normalized/" not in row["relpath"] for row in payload["sessions"])
    assert all(
        row["metadata"]["source_class"] == "observed_session_recap"
        for row in payload["sessions"]
    )
    assert payload["session_1_pc_labels"] == [
        "Baergrom",
        "Bonogo",
        "Caelynn",
        "Ephanna",
        "Karsemine",
        "Stafl",
    ]
    assert payload["gold_generation_access"] is False


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://x@127.0.0.1:54330/dungeonmind_stage4l",
        "postgresql://x@127.0.0.1:54329/dungeonmind_cutover_live",
        "postgresql://x@127.0.0.1:54329/unlabeled",
    ],
)
def test_rehearsal_guard_refuses_live_or_unlabeled_targets(dsn: str) -> None:
    with pytest.raises(stage4l.Stage4LError):
        stage4l.assert_rehearsal_dsn(dsn)


def test_rehearsal_guard_accepts_isolated_stage4l_target() -> None:
    stage4l.assert_rehearsal_dsn(
        "postgresql://x@127.0.0.1:54329/dungeonmind_stage4l_c1_rehearsal"
    )


def test_world_context_contains_only_exact_context_objects() -> None:
    context = SimpleNamespace(
        objects={
            "pc:karsemine": SimpleNamespace(
                object_id="pc:karsemine",
                label="Karsemine",
                kind="pc",
                aliases=("Kar",),
            )
        }
    )
    rows = stage4l._known_entities(context)
    assert [(row.canonical_entity_id, row.kind) for row in rows] == [
        ("pc:karsemine", "pc")
    ]


def test_replay_path_never_constructs_deepseek_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("model client constructed during replay")

    monkeypatch.setattr(stage4l, "DeepSeekCategoryGraphPassClient", forbidden)
    # Replay fails before publication because no receipt exists, but must not
    # approach the model boundary.
    context = SimpleNamespace(revision_id="rev:a", head_revision_id="rev:a", objects={})
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    monkeypatch.setattr(
        world_graph_writes,
        "load_production_mutation_context",
        lambda *_a, **_k: context,
    )
    with pytest.raises(FileNotFoundError):
        stage4l.run_session(
            1,
            root=tmp_path,
            dsn="postgresql://x@127.0.0.1:54329/dungeonmind_stage4l",
            execute=False,
            replay=True,
        )
