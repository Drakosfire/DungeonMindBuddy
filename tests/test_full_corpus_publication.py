from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import sys
from pathlib import Path

import pytest

from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("full_corpus_publication", ROOT / "tools" / "publish_full_corpus_world_graph.py")
assert spec and spec.loader
pub = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pub
spec.loader.exec_module(pub)


def test_jobs_are_the_frozen_42_session_corpus() -> None:
    assert pub.jobs() == [("longmont-c1", n) for n in range(1, 18)] + [("longmont-c2", n) for n in range(1, 26)]
    assert ("longmont-c2", 26) not in pub.jobs()
    assert ("longmont-c2", 27) not in pub.jobs()


def test_both_candidate_arms_match_the_frozen_acceptance_manifest() -> None:
    frozen = pub.load_acceptance_manifest()
    assert frozen["reviewed_notebook_head"] == pub.REVIEWED_NOTEBOOK_HEAD
    assert frozen["experiment_claim"] == pub.EXPERIMENT_CLAIM
    for arm in pub.ARMS:
        seal = pub.verify_seal(arm)
        assert seal["candidate_count"] == 42
        assert seal["model_calls"] == 0
        assert seal["sessions"] == frozen["arms"][arm]["sessions"]
        assert [(row["campaign"], row["session"]) for row in seal["sessions"]] == pub.jobs()
        live = pub.inspect_live_arm_rows(arm)
        assert live == frozen["arms"][arm]["sessions"]


def test_verify_seal_rejects_candidate_digest_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    frozen = json.loads(pub.ACCEPTANCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    frozen["arms"]["openai-gpt-5.4-mini"]["sessions"][0]["candidate_sha256"] = "0" * 64
    fake = tmp_path / "ACCEPTANCE_MANIFEST.json"
    fake.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    monkeypatch.setattr(pub, "ACCEPTANCE_MANIFEST_PATH", fake)
    with pytest.raises(pub.PublicationError, match="candidate_sha256"):
        pub.verify_seal("openai-gpt-5.4-mini")


def test_freeze_refuses_to_overwrite_existing_acceptance_manifest() -> None:
    with pytest.raises(pub.PublicationError, match="already frozen"):
        pub.freeze_acceptance_manifest()


@pytest.mark.parametrize("dsn", [
    "postgresql://x@localhost/full_corpus_live",
    "postgresql://x@localhost/eldyrwild_full_corpus",
    "postgresql://x@localhost/unlabelled",
    "postgresql://x@localhost/dungeonmind_full_corpus_openai",
    "postgresql://x@127.0.0.1:54329/dungeonmind_full_corpus_openai",
    "postgresql://x@127.0.0.1:54331/dmb_full_corpus_openai",
    "postgresql://x@127.0.0.1:54330/dmb_full_corpus_deepseek",
    "postgresql://x@example.com:54329/dmb_full_corpus_openai",
    "postgresql://x@10.0.0.5:54329/dmb_full_corpus_deepseek",
    "postgresql://x@localhost/dmb_full_corpus_openai",
])
def test_isolation_guard_refuses_non_rehearsal_authority(dsn: str) -> None:
    with pytest.raises(pub.PublicationError):
        pub.assert_isolated_dsn(dsn)


@pytest.mark.parametrize("dsn", [
    "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai",
    "postgresql://x@localhost:54329/dmb_full_corpus_deepseek",
])
def test_isolation_guard_accepts_exact_loopback_rehearsal_targets(dsn: str) -> None:
    pub.assert_isolated_dsn(dsn)


@pytest.mark.parametrize(
    "arm,dsn",
    [
        ("openai-gpt-5.4-mini", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai"),
        ("deepseek-v4.1-flash", "postgresql://x@localhost:54329/dmb_full_corpus_deepseek"),
    ],
)
def test_arm_authority_accepts_designated_pairings(arm: str, dsn: str) -> None:
    pub.assert_arm_authority(arm, dsn)


@pytest.mark.parametrize(
    "arm,dsn",
    [
        ("openai-gpt-5.4-mini", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_deepseek"),
        ("deepseek-v4.1-flash", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai"),
    ],
)
def test_arm_authority_rejects_swapped_rehearsal_databases(arm: str, dsn: str) -> None:
    with pytest.raises(pub.PublicationError, match="must use rehearsal database"):
        pub.assert_arm_authority(arm, dsn)


@pytest.mark.parametrize(
    "arm,dsn",
    [
        ("openai-gpt-5.4-mini", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai"),
        ("deepseek-v4.1-flash", "postgresql://x@localhost:54329/dmb_full_corpus_deepseek"),
    ],
)
def test_run_arm_checks_designated_authority_before_seal(
    arm: str, dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    called: list[str] = []

    def fake_verify(seal_arm: str) -> dict:
        called.append(seal_arm)
        raise RuntimeError("stop after arm authority")

    monkeypatch.setattr(pub, "verify_seal", fake_verify)
    with pytest.raises(RuntimeError, match="stop after arm authority"):
        pub.run_arm(arm=arm, dsn=dsn, world_id="world-test", output=tmp_path)
    assert called == [arm]


@pytest.mark.parametrize(
    "arm,dsn",
    [
        ("openai-gpt-5.4-mini", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_deepseek"),
        ("deepseek-v4.1-flash", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai"),
    ],
)
def test_run_arm_rejects_swapped_authority_before_seal(
    arm: str, dsn: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(seal_arm: str) -> dict:
        raise AssertionError(f"must not verify seal for mismatched arm {seal_arm}")

    monkeypatch.setattr(pub, "verify_seal", boom)
    with pytest.raises(pub.PublicationError, match="must use rehearsal database"):
        pub.run_arm(arm=arm, dsn=dsn, world_id="world-test", output=tmp_path)


def test_path_containment_rejects_files_outside_the_repo(tmp_path: Path) -> None:
    outsider = tmp_path / "escape.md"
    outsider.write_text("not in repo\n", encoding="utf-8")
    with pytest.raises(pub.PublicationError, match="contained"):
        pub._contained_file(outsider)


def test_path_containment_rejects_sibling_prefix_escape(tmp_path: Path) -> None:
    decoy_root = Path(str(pub.ROOT) + "-evil")
    if decoy_root.exists():
        pytest.skip("decoy sibling path already exists")
    with pytest.raises(pub.PublicationError, match="contained"):
        pub._contained_file(decoy_root / "candidate_graph.json")


def test_production_recap_creator_does_not_accept_caller_selected_identity(tmp_path: Path) -> None:
    recap = tmp_path / "recap.md"
    recap.write_text("# Recap\n\nObserved.\n", encoding="utf-8")
    assert "source_artifact_id" not in inspect.signature(create_recap_source_artifact).parameters
    with pytest.raises(TypeError):
        create_recap_source_artifact(
            tmp_path,
            campaign_id="longmont-c1",
            session_id="session-1",
            recap_path=recap,
            source_artifact_id="full-corpus:longmont-c1:session-1:verified",
        )
    artifact = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c1",
        session_id="session-1",
        recap_path=recap,
    )
    digest = hashlib.sha256(recap.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
    assert artifact.source_artifact_id == f"artifact:recap:longmont-c1:session-1:{digest[:12]}"
    assert artifact.content_sha256 == digest


def test_acceptance_harness_binds_historical_id_after_canonical_registration(tmp_path: Path) -> None:
    recap = tmp_path / "recap.md"
    recap.write_text("# Recap\n\nObserved.\n", encoding="utf-8")
    canonical = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c1",
        session_id="session-1",
        recap_path=recap,
    )
    historical = "full-corpus:longmont-c1:session-1:verified"
    aliased = pub.register_verified_historical_recap(
        tmp_path,
        campaign_id="longmont-c1",
        session_id="session-1",
        recap_path=recap,
        expected_content_sha256=canonical.content_sha256,
        historical_source_artifact_id=historical,
    )
    assert aliased.source_artifact_id == historical
    assert aliased.content_sha256 == canonical.content_sha256
    assert aliased.lineage["canonical_derived_source_artifact_id"] == canonical.source_artifact_id
