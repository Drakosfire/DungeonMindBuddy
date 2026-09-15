"""Deterministic owning-boundary tests for current-corpus admission acceptance."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from evals.graph_memory_layer.run_current_corpus_admission_acceptance import (
    AcceptanceSeams,
    AcceptanceStop,
    DATABASE_NAME,
    EXPECTED_HOST,
    EXPECTED_PORT,
    assert_runtime_dsn,
    freeze_current_corpus_manifest,
    run_execute,
    run_preflight,
    verify_entry_source_bytes,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _normalized_doc(
    *,
    campaign_id: str,
    session: int,
    title: str,
    normalized_from: str,
) -> str:
    return (
        "---\n"
        f"title: Session {session} - {title}\n"
        "document_class: play\n"
        "canon_layer: campaign\n"
        f"campaign_id: {campaign_id}\n"
        "temporal_scope: session_specific\n"
        f"session: {session}\n"
        f"origin_session: {session}\n"
        f"last_updated_session: {session}\n"
        "source_class: observed_session_recap\n"
        f"normalized_from: {normalized_from}\n"
        "normalization_schema: dmb_recap_normalized_v1\n"
        "---\n"
        f"Body for session {session}.\n"
    )


def _seed_campaign(
    repo: Path,
    *,
    campaign_number: int,
    sessions: list[int],
) -> None:
    campaign_id = f"longmont-c{campaign_number}"
    prefix = f"Longmont Campaign/Campaign {campaign_number}/Session Recaps"
    corpus = repo / "corpus" / "eldyrwild-markdown"
    for session in sessions:
        original_rel = f"{prefix}/Session {session} - Recap.md"
        original = corpus / original_rel
        _write(original, f"Original session {session} bytes.\n")
        normalized = (
            corpus
            / prefix
            / "_normalized"
            / f"Session {session:02d} - Title {session}.md"
        )
        _write(
            normalized,
            _normalized_doc(
                campaign_id=campaign_id,
                session=session,
                title=f"Title {session}",
                normalized_from=original_rel,
            ),
        )


@pytest.fixture
def seeded_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_campaign(repo, campaign_number=1, sessions=[1, 2])
    _seed_campaign(repo, campaign_number=2, sessions=[1])
    monkeypatch.setattr(
        "src.live_play.recap_stage_paths.corpus_root",
        lambda: repo / "corpus" / "eldyrwild-markdown",
    )
    monkeypatch.setattr(
        "evals.graph_memory_layer.run_current_corpus_admission_acceptance.git_head",
        lambda _root: "deadbeef" * 5,
    )
    monkeypatch.setattr(
        "evals.graph_memory_layer.run_current_corpus_admission_acceptance.model_policy_digest",
        lambda _root=None: "policy" * 10 + "aa",
    )
    monkeypatch.setattr(
        "evals.graph_memory_layer.run_current_corpus_admission_acceptance.resolved_production_model_id",
        lambda: "gpt-test-mini",
    )
    monkeypatch.setattr(
        "src.bootstrap_env.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )
    return repo


def test_manifest_sort_and_digest_stable(seeded_repo: Path) -> None:
    first = freeze_current_corpus_manifest(seeded_repo)
    second = freeze_current_corpus_manifest(seeded_repo)
    assert first.count == 3
    assert [e.session_id for e in first.entries] == [
        "session-1",
        "session-2",
        "session-1",
    ]
    assert [e.campaign_id for e in first.entries] == [
        "longmont-c1",
        "longmont-c1",
        "longmont-c2",
    ]
    assert first.digest == second.digest
    assert first.as_dict() == second.as_dict()


def test_duplicate_and_gapped_lineage_rejected(
    seeded_repo: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    corpus = seeded_repo / "corpus" / "eldyrwild-markdown"
    # Gap: remove C1 S2 normalized file after creating S3.
    _seed_campaign(seeded_repo, campaign_number=1, sessions=[3])
    (corpus / "Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 02 - Title 2.md").unlink()
    with pytest.raises(AcceptanceStop, match="non-contiguous"):
        freeze_current_corpus_manifest(seeded_repo)


def test_normalized_from_escape_rejected(seeded_repo: Path) -> None:
    path = (
        seeded_repo
        / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/_normalized/Session 01 - Title 1.md"
    )
    text = path.read_text(encoding="utf-8").replace(
        "Longmont Campaign/Campaign 1/Session Recaps/Session 1 - Recap.md",
        "../../etc/passwd",
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(AcceptanceStop, match="escapes repository|original source missing"):
        freeze_current_corpus_manifest(seeded_repo)


def test_source_drift_rejected_before_extraction(seeded_repo: Path) -> None:
    manifest = freeze_current_corpus_manifest(seeded_repo)
    entry = manifest.entries[0]
    original = seeded_repo / entry.original_path
    original.write_text("drifted bytes\n", encoding="utf-8")
    with pytest.raises(AcceptanceStop, match="drifted") as exc:
        verify_entry_source_bytes(seeded_repo, entry)
    assert exc.value.boundary == "manifest_source_guard"


def test_runtime_dsn_refusal() -> None:
    assert_runtime_dsn(
        f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}"
    )
    with pytest.raises(AcceptanceStop, match="database must be"):
        assert_runtime_dsn(
            f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/wrong_db"
        )
    with pytest.raises(AcceptanceStop, match="port must be"):
        assert_runtime_dsn(
            f"postgresql://dungeonmind:x@{EXPECTED_HOST}:54331/{DATABASE_NAME}"
        )


def test_non_pristine_world_refusal(seeded_repo: Path) -> None:
    seams = AcceptanceSeams(
        probe_world=lambda _world_id: SimpleNamespace(state="initialized")
    )
    with pytest.raises(AcceptanceStop, match="not pristine") as exc:
        run_preflight(
            repo_root=seeded_repo,
            dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
            seams=seams,
        )
    assert exc.value.boundary == "recap_genesis_probe"


@dataclass
class _FakePrepare:
    review_package: dict[str, Any]
    confirmable: bool = True
    proposal_digest: str = "proposal-digest"


def _candidate(node_id: str = "candidate:a") -> dict[str, Any]:
    return {
        "schema": "dmb_candidate_graph_preview_v0",
        "version": "0.1",
        "preview_id": "preview:test",
        "nodes": [{"node_id": node_id, "node_type": "character"}],
        "edges": [],
        "beats": [],
        "proposed_writes": [],
    }


def _success_seams(*, fail_at: str | None = None) -> tuple[AcceptanceSeams, dict[str, int]]:
    heads = {"value": "rev:d0"}
    calls = {"extract": 0, "confirm": 0, "prepare": 0}

    def probe(_world_id: str) -> Any:
        return SimpleNamespace(state="uninitialized")

    def prepare_genesis(req, **_kwargs):
        return SimpleNamespace(
            world_id=req.world_id,
            pc_object_ids=tuple(f"node:pc{i}" for i in range(6)),
        )

    def confirm_genesis(_req, **_kwargs):
        return SimpleNamespace(
            published_revision_id="rev:d0",
            parent_revision_id=None,
            pc_object_ids=tuple(f"node:pc{i}" for i in range(6)),
        )

    def extract_session(*, repo_root: Path, entry: Any, output_dir: Path) -> dict[str, Any]:
        calls["extract"] += 1
        if fail_at == "extract" and calls["extract"] == 1:
            raise AcceptanceStop(
                "synthetic extraction failure",
                boundary="production_extraction",
                campaign_id=entry.campaign_id,
                session_id=entry.session_id,
            )
        if fail_at == "extract_second" and calls["extract"] == 2:
            raise AcceptanceStop(
                "synthetic second-session failure",
                boundary="production_extraction",
                campaign_id=entry.campaign_id,
                session_id=entry.session_id,
            )
        graph = _candidate(f"candidate:{entry.session_id}")
        return {
            "run_id": f"run-{entry.session_id}",
            "status": "reviewable",
            "model_id": "gpt-test-mini",
            "candidate_graph": graph,
            "source_uri": f"repo://{entry.original_path}",
            "source_revision_id": f"sha256:{entry.original_sha256}",
            "source_artifact_id": entry.source_artifact_id,
        }

    def load_context(_world_id: str, *, dsn: str, prior_head: str):
        return SimpleNamespace(revision_id=prior_head)

    def prepare_admission(**kwargs):
        calls["prepare"] += 1
        candidate = kwargs["candidate_graph"]
        if fail_at == "nonconfirmable":
            package = {
                "proposal_id": "p1",
                "proposal_digest": "pd1",
                "effect": {
                    "accepted_proposals": [],
                    "candidate_admission": {
                        "candidate_digest": hashlib.sha256(
                            json.dumps(candidate, sort_keys=True).encode()
                        ).hexdigest(),
                        "confirmable": False,
                        "dispositions": [
                            {
                                "item_id": "candidate:x",
                                "reason": "unsupported_node_type",
                            }
                        ],
                    },
                },
            }
            # Force digest match with canonical helper by importing it.
            from apps.live_control_server.services.candidate_graph_admission import (
                canonical_candidate_digest,
            )

            package["effect"]["candidate_admission"]["candidate_digest"] = (
                canonical_candidate_digest(candidate)
            )
            return _FakePrepare(review_package=package, confirmable=False)

        if fail_at == "stale_before_confirm" and calls["prepare"] == 1:
            from apps.live_control_server.services.candidate_graph_admission import (
                canonical_candidate_digest,
            )

            package = {
                "proposal_id": "p1",
                "proposal_digest": "pd1",
                "effect": {
                    "accepted_proposals": [{"assertion_id": "a1"}],
                    "candidate_admission": {
                        "candidate_digest": canonical_candidate_digest(candidate),
                        "confirmable": True,
                        "dispositions": [
                            {
                                "item_id": "candidate:medical-wing",
                                "reason": "unsupported_node_type",
                            }
                        ],
                    },
                },
            }
            # Flip head after prepare succeeds so confirm path sees stale parent.
            heads["value"] = "rev:external"
            return _FakePrepare(review_package=package, confirmable=True)

        from apps.live_control_server.services.candidate_graph_admission import (
            canonical_candidate_digest,
        )

        package = {
            "proposal_id": "p1",
            "proposal_digest": "pd1",
            "effect": {
                "accepted_proposals": [{"assertion_id": f"a-{calls['prepare']}"}],
                "candidate_admission": {
                    "candidate_digest": canonical_candidate_digest(candidate),
                    "confirmable": True,
                    "dispositions": (
                        [
                            {
                                "item_id": "candidate:medical-wing",
                                "reason": "unsupported_node_type",
                            }
                        ]
                        if fail_at == "eligibility_ok"
                        else []
                    ),
                },
            },
        }
        return _FakePrepare(review_package=package, confirmable=True)

    def confirm_admission(
        *,
        review_package: dict[str, Any],
        candidate_graph: dict[str, Any],
        prior_head: str,
        assertion_ids: list[str],
        dsn: str,
    ):
        calls["confirm"] += 1
        child = f"rev:d{calls['confirm']}"
        heads["value"] = child
        return {
            "committed_revision_id": child,
            "parent_revision_id": prior_head,
            "accepted_assertion_ids": assertion_ids,
        }

    def current_head(_world_id: str) -> str:
        return heads["value"]

    def read_parent(_world_id: str, child: str) -> str | None:
        # parent of rev:dN is prior
        if child == "rev:d1":
            return "rev:d0"
        if child.startswith("rev:d"):
            n = int(child.split("d")[-1])
            return f"rev:d{n-1}" if n > 1 else "rev:d0"
        return None

    return AcceptanceSeams(
        probe_world=probe,
        prepare_genesis=prepare_genesis,
        confirm_genesis=confirm_genesis,
        extract_session=extract_session,
        load_mutation_context=load_context,
        prepare_admission=prepare_admission,
        confirm_admission=confirm_admission,
        current_head=current_head,
        read_revision_parent=read_parent,
    ), calls


def test_preflight_is_zero_mutation(seeded_repo: Path) -> None:
    seams, _calls = _success_seams()
    state = run_preflight(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert state.model_calls == 0
    assert state.graph_writes == 0
    assert state.manifest is not None
    assert state.manifest.count == 3
    assert state.structural_acceptance == "HOLD"


def test_exact_candidate_forwarded_without_mutation(seeded_repo: Path) -> None:
    seams, calls = _success_seams()
    seen: list[dict[str, Any]] = []
    real_prepare = seams.prepare_admission
    assert real_prepare is not None

    def prepare_admission(**kwargs):
        seen.append(copy.deepcopy(kwargs["candidate_graph"]))
        return real_prepare(**kwargs)

    seams = replace(seams, prepare_admission=prepare_admission)
    state = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert state.structural_acceptance == "PASS"
    assert len(seen) == 3
    assert calls["confirm"] == 3
    for graph in seen:
        assert "nodes" in graph
        assert graph == copy.deepcopy(graph)


def test_eligibility_disposition_does_not_repair(seeded_repo: Path) -> None:
    seams, _calls = _success_seams(fail_at="eligibility_ok")
    state = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert state.structural_acceptance == "PASS"
    assert any(
        any(d.get("reason") == "unsupported_node_type" for d in row["admission_dispositions"])
        for row in state.session_ledger
    )


def test_nonconfirmable_stops_before_confirm(seeded_repo: Path) -> None:
    seams, calls = _success_seams(fail_at="nonconfirmable")
    state = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert state.structural_acceptance == "HOLD"
    assert state.stop is not None
    assert state.stop["boundary"] == "candidate_graph_admission"
    assert calls["confirm"] == 0
    assert state.session_ledger == []


def test_first_failure_prevents_later_sessions(seeded_repo: Path) -> None:
    seams, calls = _success_seams(fail_at="extract")
    state = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert state.structural_acceptance == "HOLD"
    assert calls["extract"] == 1
    assert state.stop is not None
    assert "longmont-c1/session-2" in state.stop["sessions_not_attempted"]
    assert "longmont-c2/session-1" in state.stop["sessions_not_attempted"]


def test_stale_head_stops_without_reprepare(seeded_repo: Path) -> None:
    seams, calls = _success_seams(fail_at="stale_before_confirm")
    state = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert state.structural_acceptance == "HOLD"
    assert state.stop is not None
    assert state.stop["boundary"] == "governed_write_seam"
    assert calls["confirm"] == 0
    assert calls["prepare"] == 1


def test_parent_head_chain_matches_receipts(seeded_repo: Path) -> None:
    seams, _calls = _success_seams()
    state = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert state.structural_acceptance == "PASS"
    assert state.genesis_d0 == "rev:d0"
    parents = [row["sealed_parent_revision"] for row in state.session_ledger]
    children = [row["receipt_child_revision"] for row in state.session_ledger]
    assert parents[0] == "rev:d0"
    assert children == ["rev:d1", "rev:d2", "rev:d3"]
    assert parents[1:] == children[:-1]
    assert state.terminal_head == children[-1]


def test_no_resume_path_on_incomplete_run(seeded_repo: Path) -> None:
    """An incomplete run cannot be continued; a new execute must start fresh."""
    seams, _calls = _success_seams(fail_at="extract")
    first = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=seams,
    )
    assert first.structural_acceptance == "HOLD"
    assert first.run_id.startswith("execute-")
    # Second run gets a new run id and still requires pristine probe.
    second_seams, _ = _success_seams()
    second = run_execute(
        repo_root=seeded_repo,
        dsn=f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
        seams=second_seams,
    )
    assert second.run_id != first.run_id
    assert second.structural_acceptance == "PASS"
