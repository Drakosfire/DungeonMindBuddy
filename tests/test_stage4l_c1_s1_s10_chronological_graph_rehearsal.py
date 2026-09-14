from __future__ import annotations

import importlib.util
import json
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


def test_world_context_maps_dungeonmind_player_character_to_pc() -> None:
    context = SimpleNamespace(
        objects={
            "node:caelynn": SimpleNamespace(
                object_id="node:caelynn",
                label="Caelynn",
                kind="player_character",
                aliases=("Caelynn",),
            )
        }
    )

    rows = stage4l._known_entities(context)

    assert [(row.canonical_entity_id, row.kind) for row in rows] == [
        ("node:caelynn", "pc")
    ]


def test_runner_pins_checkout_src_before_environment_paths() -> None:
    assert sys.path[:2] == [str(stage4l.REPO_ROOT), str(stage4l.SRC_ROOT)]


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


def _paid_receipt_stub(
    *,
    session: int,
    run_id: str,
    source_sha: str,
    candidate_sha: str,
    prior: str,
    child: str,
    context: dict,
) -> dict:
    return {
        "schema": "dmb_stage4l_session_receipt_v1",
        "session": session,
        "replay": False,
        "run_id": run_id,
        "source": {"sha256": source_sha},
        "candidate_sha256": candidate_sha,
        "candidate_graph_path": f"session_{session:02d}/{run_id}/candidate_graph.json",
        "context": context,
        "publication": {
            "parent_revision_id": prior,
            "committed_revision_id": child,
            "publication_mode": "node_object_partial",
            "edge_funnel": {"extracted": 0, "published": 0},
        },
        "lineage": {"kind": "paid", "sealed": True},
        "model_calls": 8,
        "cost_usd": 0.01,
    }


def test_candidate_path_exact_run_does_not_glob_fallback(tmp_path: Path) -> None:
    session_dir = tmp_path / "session_01"
    (session_dir / "wrong-run").mkdir(parents=True)
    (session_dir / "wrong-run" / "candidate_graph.json").write_text("{}", encoding="utf-8")
    with pytest.raises(stage4l.Stage4LError, match="durable candidate missing"):
        stage4l._candidate_path(tmp_path, 1, "expected-run", exact_run=True)


def test_replay_fails_closed_on_candidate_digest_drift(tmp_path: Path) -> None:
    source = stage4l._source_ref(1)
    run_id = "run-a"
    candidate = tmp_path / "session_01" / run_id / "candidate_graph.json"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b'{"nodes":[]}')
    context = {
        "prior_world_revision_id": "rev:parent",
        "party_registry": {"fingerprint": "party", "count": 6},
        "world_known_entities": {"fingerprint": "known", "count": 0},
    }
    saved = _paid_receipt_stub(
        session=1,
        run_id=run_id,
        source_sha=source.sha256,
        candidate_sha="deadbeef",
        prior="rev:parent",
        child="rev:child",
        context=context,
    )
    with pytest.raises(stage4l.Stage4LError, match="candidate digest drift"):
        stage4l._assert_replay_seals(
            saved=saved,
            source=source,
            prior_revision="rev:parent",
            live_context=context,
            candidate_path=candidate,
        )


def test_replay_fails_closed_on_context_fingerprint_drift(tmp_path: Path) -> None:
    source = stage4l._source_ref(1)
    run_id = "run-a"
    candidate = tmp_path / "session_01" / run_id / "candidate_graph.json"
    candidate.parent.mkdir(parents=True)
    payload = b'{"nodes":[]}'
    candidate.write_bytes(payload)
    saved_context = {
        "prior_world_revision_id": "rev:parent",
        "party_registry": {"fingerprint": "party", "count": 6},
        "world_known_entities": {"fingerprint": "known-a", "count": 0},
    }
    live_context = {
        "prior_world_revision_id": "rev:parent",
        "party_registry": {"fingerprint": "party", "count": 6},
        "world_known_entities": {"fingerprint": "known-b", "count": 1},
    }
    saved = _paid_receipt_stub(
        session=1,
        run_id=run_id,
        source_sha=source.sha256,
        candidate_sha=stage4l._sha_bytes(payload),
        prior="rev:parent",
        child="rev:child",
        context=saved_context,
    )
    with pytest.raises(stage4l.Stage4LError, match="context fingerprint drift"):
        stage4l._assert_replay_seals(
            saved=saved,
            source=source,
            prior_revision="rev:parent",
            live_context=live_context,
            candidate_path=candidate,
        )


def test_replay_writes_sidecar_and_does_not_overwrite_paid(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = stage4l._source_ref(1)
    run_id = "run-a"
    candidate = tmp_path / "session_01" / run_id / "candidate_graph.json"
    candidate.parent.mkdir(parents=True)
    payload = b'{"nodes":[],"edges":[],"source_artifact_ids":["artifact:x"]}'
    candidate.write_bytes(payload)
    party = stage4l._known_receipt(
        stage4l.build_known_entity_registry(stage4l.CAMPAIGN_ID, 1).entities
    )
    known = stage4l._known_receipt([])
    context = {
        "prior_world_revision_id": "rev:parent",
        "world_head_revision_id": "rev:parent",
        "party_registry": party,
        "world_known_entities": known,
    }
    paid = _paid_receipt_stub(
        session=1,
        run_id=run_id,
        source_sha=source.sha256,
        candidate_sha=stage4l._sha_bytes(payload),
        prior="rev:parent",
        child="rev:paid-child",
        context=context,
    )
    paid_path = stage4l._paid_receipt_path(tmp_path, 1)
    stage4l._write_json(paid_path, paid)
    before = paid_path.read_text(encoding="utf-8")

    world = SimpleNamespace(
        revision_id="rev:parent",
        head_revision_id="rev:parent",
        objects={},
    )
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    monkeypatch.setattr(
        world_graph_writes,
        "load_production_mutation_context",
        lambda *_a, **_k: world,
    )
    monkeypatch.setattr(
        stage4l,
        "_publish",
        lambda **_k: {
            "parent_revision_id": "rev:parent",
            "committed_revision_id": "rev:replay-child",
            "publication_mode": "node_object_partial",
            "edge_funnel": {"extracted": 0, "published": 0},
            "review_package": {"ok": True},
        },
    )
    monkeypatch.setattr(stage4l, "DeepSeekCategoryGraphPassClient", lambda *_a, **_k: None)

    result = stage4l.run_session(
        1,
        root=tmp_path,
        dsn="postgresql://x@127.0.0.1:54329/dungeonmind_stage4l_c1_rehearsal",
        execute=False,
        replay=True,
    )
    assert result["replay"] is True
    assert result["publication"]["committed_revision_id"] == "rev:replay-child"
    assert paid_path.read_text(encoding="utf-8") == before
    sidecar = stage4l._replay_receipt_path(tmp_path, 1)
    assert sidecar.is_file()
    assert json.loads(sidecar.read_text(encoding="utf-8"))["replay"] is True


def test_resume_requires_contiguous_verified_paid_chain(tmp_path: Path) -> None:
    with pytest.raises(stage4l.Stage4LError, match="contiguous"):
        stage4l._verify_paid_chain(
            tmp_path,
            [
                _paid_receipt_stub(
                    session=2,
                    run_id="x",
                    source_sha="a",
                    candidate_sha="b",
                    prior="rev:p",
                    child="rev:c",
                    context={
                        "prior_world_revision_id": "rev:p",
                        "party_registry": {"fingerprint": "p"},
                        "world_known_entities": {"fingerprint": "k", "count": 0},
                    },
                )
            ],
        )


def test_manifest_records_source_candidate_context_and_lineage(tmp_path: Path) -> None:
    source = stage4l._source_ref(1)
    run_id = "run-a"
    candidate = tmp_path / "session_01" / run_id / "candidate_graph.json"
    candidate.parent.mkdir(parents=True)
    payload = b'{"nodes":[]}'
    candidate.write_bytes(payload)
    context = {
        "prior_world_revision_id": "rev:parent",
        "party_registry": {"fingerprint": "party", "count": 6},
        "world_known_entities": {"fingerprint": "known", "count": 0},
    }
    receipt = _paid_receipt_stub(
        session=1,
        run_id=run_id,
        source_sha=source.sha256,
        candidate_sha=stage4l._sha_bytes(payload),
        prior="rev:parent",
        child="rev:child",
        context=context,
    )
    stage4l._write_json(stage4l._paid_receipt_path(tmp_path, 1), receipt)
    payload_json = stage4l.render_manifest(tmp_path)
    row = payload_json["sessions"][0]
    for key in (
        "source_sha256",
        "candidate_sha256",
        "run_id",
        "context_fingerprint",
        "parent_revision_id",
        "committed_revision_id",
        "publication_mode",
        "lineage",
    ):
        assert row[key]
    assert row["lineage"] == "paid"
    assert (tmp_path / "MANIFEST.json").is_file()
