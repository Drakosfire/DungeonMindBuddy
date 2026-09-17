"""Deterministic regressions for current-corpus candidate replay."""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from collections.abc import Mapping
from typing import Any

import pytest

from evals.graph_memory_layer.run_current_corpus_candidate_replay_acceptance import (
    ACCEPTED_MANIFEST_SCHEMA,
    DATABASE_NAME,
    EXPECTED_HOST,
    EXPECTED_PORT,
    HISTORICAL_DATABASE_NAME,
    ReplaySeams,
    ReplayStop,
    assert_runtime_dsn,
    load_accepted_cohort,
    run_execute,
    run_preflight,
    run_product_smoke,
    run_product_smoke_from_run,
    verify_entry_source_bytes,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalized_doc(*, campaign_id: str, session: int, original_rel: str) -> str:
    return (
        "---\n"
        f"title: Session {session}\n"
        "document_class: play\n"
        f"campaign_id: {campaign_id}\n"
        f"session: {session}\n"
        f"normalized_from: {original_rel}\n"
        "normalization_schema: dmb_recap_normalized_v1\n"
        "---\n"
        f"Body for session {session}.\n"
    )


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


def _canonical_digest(candidate: Mapping[str, Any]) -> str:
    from apps.live_control_server.services.candidate_graph_admission import (
        canonical_candidate_digest,
    )

    return canonical_candidate_digest(candidate)


def _manifest_digest(entries: list[dict[str, Any]]) -> str:
    payload = {"schema": ACCEPTED_MANIFEST_SCHEMA, "entries": entries}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _seed_session(
    repo: Path,
    artifact_root: Path,
    *,
    ordinal: int,
    campaign_number: int,
    session: int,
) -> dict[str, Any]:
    campaign_id = f"longmont-c{campaign_number}"
    session_id = f"session-{session}"
    prefix = f"Longmont Campaign/Campaign {campaign_number}/Session Recaps"
    original_rel = f"corpus/eldyrwild-markdown/{prefix}/Session {session} - Recap.md"
    original = repo / original_rel
    original_text = f"Original {campaign_id} {session_id} bytes.\n"
    _write(original, original_text)
    normalized_rel = (
        f"corpus/eldyrwild-markdown/{prefix}/_normalized/Session {session:02d} - Title.md"
    )
    _write(repo / normalized_rel, _normalized_doc(campaign_id=campaign_id, session=session, original_rel=original_rel))
    original_sha = _sha256_text(original_text)
    normalized_sha = _sha256_file_path(repo / normalized_rel)
    source_artifact_id = f"artifact:recap:{campaign_id}:{session_id}:{original_sha[:12]}"
    graph = _candidate(f"candidate:{campaign_id}:{session_id}")
    locator_name = f"{campaign_id}-{session_id}.json"
    candidate_path = artifact_root / "candidates" / locator_name
    _write(candidate_path, json.dumps(graph, indent=2, sort_keys=True) + "\n")
    digest = _canonical_digest(graph)
    entry = {
        "ordinal": ordinal,
        "campaign_id": campaign_id,
        "campaign_number": campaign_number,
        "session": session,
        "session_id": session_id,
        "normalized_path": normalized_rel,
        "normalized_sha256": normalized_sha,
        "original_path": original_rel,
        "original_sha256": original_sha,
        "source_artifact_id": source_artifact_id,
    }
    ledger = {
        **entry,
        "candidate_locator": f"candidates/{locator_name}",
        "candidate_digest": digest,
        "source_revision_id": f"sha256:{original_sha}",
    }
    return {"entry": entry, "ledger": ledger, "graph": graph}


def _sha256_file_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_cohort(artifact_root: Path, rows: list[dict[str, Any]]) -> str:
    entries = [row["entry"] for row in rows]
    digest = _manifest_digest(entries)
    _write(
        artifact_root / "manifest.json",
        json.dumps(
            {
                "schema": ACCEPTED_MANIFEST_SCHEMA,
                "count": len(entries),
                "digest": digest,
                "entries": entries,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )
    _write(
        artifact_root / "session_ledger.json",
        json.dumps({"sessions": [row["ledger"] for row in rows]}, indent=2, sort_keys=True)
        + "\n",
    )
    return digest


@pytest.fixture
def seeded(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    repo = tmp_path / "repo"
    artifact_root = tmp_path / "accepted" / "execute-fake"
    artifact_root.mkdir(parents=True)
    rows = [
        _seed_session(repo, artifact_root, ordinal=1, campaign_number=1, session=1),
        _seed_session(repo, artifact_root, ordinal=2, campaign_number=2, session=1),
    ]
    digest = _write_cohort(artifact_root, rows)
    monkeypatch.setattr(
        "evals.graph_memory_layer.run_current_corpus_candidate_replay_acceptance.git_head",
        lambda _root: "deadbeef" * 5,
    )
    monkeypatch.setattr(
        "src.bootstrap_env.load_dungeonmindbuddy_dotenv",
        lambda: None,
    )
    return {
        "repo": repo,
        "artifact_root": artifact_root,
        "digest": digest,
        "rows": rows,
        "count": 2,
        "dsn": f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{DATABASE_NAME}",
    }


@dataclass
class _FakePrepare:
    review_package: dict[str, Any]
    confirmable: bool = True
    proposal_digest: str = "proposal-digest"


def _source_artifact(entry: Any) -> SimpleNamespace:
    return SimpleNamespace(
        source_artifact_id=entry.source_artifact_id,
        source_domain="recap",
        campaign_id=entry.campaign_id,
        session_id=entry.session_id,
        uri=f"repo://{entry.original_path}",
        content_sha256=entry.original_sha256,
    )


def _success_seams(*, fail_at: str | None = None) -> tuple[ReplaySeams, dict[str, Any]]:
    heads = {"value": "rev:d0"}
    world_state = {"state": "uninitialized"}
    calls = {"confirm": 0, "prepare": 0, "extract": 0}

    def probe(_world_id: str) -> Any:
        return SimpleNamespace(state=world_state["state"])

    def prepare_genesis(req, **_kwargs):
        return SimpleNamespace(
            world_id=req.world_id,
            pc_object_ids=tuple(f"node:pc{i}" for i in range(6)),
        )

    def confirm_genesis(_req, **_kwargs):
        world_state["state"] = "initialized"
        return SimpleNamespace(
            published_revision_id="rev:d0",
            parent_revision_id=None,
            pc_object_ids=tuple(f"node:pc{i}" for i in range(6)),
        )

    def load_source_artifact(*, repo_root: Path, entry: Any):
        return _source_artifact(entry)

    def load_context(_world_id: str, *, dsn: str, prior_head: str):
        return SimpleNamespace(revision_id=prior_head)

    def prepare_admission(**kwargs):
        calls["prepare"] += 1
        candidate = kwargs["candidate_graph"]
        digest = _canonical_digest(candidate)
        source_admission = {
            "source_artifact_id": kwargs["source_artifact_id"],
            "source_revision_id": kwargs["source_revision_id"],
            "buddy_source_revision_id": kwargs["source_revision_id"],
            "content_sha256": kwargs["source_revision_id"].removeprefix("sha256:"),
        }
        if fail_at == "nonconfirmable":
            return _FakePrepare(
                review_package={
                    "proposal_id": "p1",
                    "proposal_digest": "pd1",
                    "effect": {
                        "accepted_proposals": [],
                        "candidate_admission": {
                            "candidate_digest": digest,
                            "confirmable": False,
                            "dispositions": [{"item_id": "n1", "reason": "unsupported_node_type"}],
                        },
                        "source_admission": source_admission,
                    },
                },
                confirmable=False,
            )
        if fail_at == "stale_before_confirm" and calls["prepare"] == 1:
            heads["value"] = "rev:external"
        package = {
            "proposal_id": "p1",
            "proposal_digest": "pd1",
            "effect": {
                "accepted_proposals": [{"assertion_id": f"a-{calls['prepare']}"}],
                "candidate_admission": {
                    "candidate_digest": digest,
                    "confirmable": True,
                    "dispositions": [],
                },
                "source_admission": source_admission,
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
        if fail_at == "later_session" and calls["confirm"] == 2:
            raise ReplayStop(
                "synthetic later-session failure",
                boundary="dungeonmind_write",
            )
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
        if child == "rev:d1":
            return "rev:d0"
        if child.startswith("rev:d"):
            n = int(child.split("d")[-1])
            return f"rev:d{n - 1}" if n > 1 else "rev:d0"
        return None

    return (
        ReplaySeams(
            probe_world=probe,
            prepare_genesis=prepare_genesis,
            confirm_genesis=confirm_genesis,
            load_source_artifact=load_source_artifact,
            load_mutation_context=load_context,
            prepare_admission=prepare_admission,
            confirm_admission=confirm_admission,
            current_head=current_head,
            read_revision_parent=read_parent,
        ),
        {"calls": calls, "world_state": world_state, "heads": heads},
    )


def _product_node(node_id: str, label: str) -> SimpleNamespace:
    return SimpleNamespace(
        node_id=node_id,
        label=label,
        aliases=[label],
        kind="character" if "character" in node_id else "location",
    )


def _product_projection(*, revision_id: str, nodes: list[SimpleNamespace]) -> SimpleNamespace:
    return SimpleNamespace(
        nodes=nodes,
        relationships=[],
        diagnostics=[],
        snapshot=SimpleNamespace(revision_id=revision_id, head_revision_id=revision_id),
        summary=SimpleNamespace(node_count=len(nodes), relationship_count=0),
    )


def _attach_product_seams(
    seams: ReplaySeams,
    *,
    terminal: str = "rev:d2",
    fail: str | None = None,
) -> ReplaySeams:
    c1s10 = "rev:d1"
    c2s22 = "rev:d2"
    mireward = "node:location:mireward"
    torbin = "node:character:torbin"

    def project_campaign(*, campaign_id: str, revision_pin: str, **_kwargs):
        if fail == "pin_leak" and revision_pin == c1s10:
            return _product_projection(
                revision_id=terminal,
                nodes=[_product_node(torbin, "Torbin")],
            )
        if campaign_id == "longmont-c2":
            return _product_projection(
                revision_id=revision_pin,
                nodes=[_product_node(mireward, "Mireward")],
            )
        return _product_projection(
            revision_id=revision_pin,
            nodes=[_product_node(torbin, "Torbin")],
        )

    def get_object(*, node_id: str, revision_pin: str, **_kwargs):
        if fail == "missing_object":
            return SimpleNamespace(outcome="empty", resolved_node_id=None, snapshot=None)
        return SimpleNamespace(
            outcome="enough",
            resolved_node_id=node_id,
            snapshot=SimpleNamespace(revision_id=revision_pin),
        )

    def get_complete_object(*, node_id: str, **_kwargs):
        return SimpleNamespace(found=True, requested_node_id=node_id)

    def get_neighborhood(*, node_id: str, **_kwargs):
        return SimpleNamespace(
            outcome="enough",
            nodes=[SimpleNamespace(node_id=node_id)],
            coverage=SimpleNamespace(missing_seed_node_ids=[]),
        )

    def get_evidence(*, node_id: str, revision_pin: str, **_kwargs):
        if fail == "unresolved_source" and node_id == mireward:
            return SimpleNamespace(outcome="enough", source_anchors=[], snapshot=None)
        return SimpleNamespace(
            outcome="enough",
            source_anchors=[SimpleNamespace(anchor_id=f"source-anchor:v1:{node_id}")],
            snapshot=SimpleNamespace(revision_id=revision_pin),
        )

    def read_source(*, anchor_id: str, revision_pin: str, **_kwargs):
        if fail == "unresolved_source":
            return SimpleNamespace(outcome="unavailable", content_sha256=None, snapshot=None)
        if fail == "partial_source":
            return SimpleNamespace(
                outcome="partial",
                content_sha256=None,
                locator_kind="unsupported",
                snapshot=SimpleNamespace(revision_id=revision_pin),
                diagnostics=[
                    SimpleNamespace(
                        code="unsupported_locator",
                        message="This source anchor's locator/URI scheme is not supported for reading.",
                    )
                ],
            )
        return SimpleNamespace(
            outcome="enough",
            content_sha256="abc123",
            locator_kind="heading",
            snapshot=SimpleNamespace(revision_id=revision_pin),
            anchor_id=anchor_id,
        )

    def read_parent(_world_id: str, child: str) -> str | None:
        if child == terminal:
            return c1s10
        if child == c2s22:
            return c1s10
        if child == c1s10:
            return "rev:d0"
        return None

    return replace(
        seams,
        project_campaign=project_campaign,
        get_object=get_object,
        get_complete_object=get_complete_object,
        get_neighborhood=get_neighborhood,
        get_evidence=get_evidence,
        read_source=read_source,
        read_revision_parent=read_parent,
    )


def test_missing_artifact_root_stops_before_genesis(seeded: dict[str, Any]) -> None:
    seams, ctx = _success_seams()
    with pytest.raises(ReplayStop, match="artifact root missing") as exc:
        run_preflight(
            accepted_artifact_root=seeded["artifact_root"] / "missing",
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            seams=seams,
            expected_count=seeded["count"],
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "replay_artifact_unavailable"
    assert ctx["calls"]["confirm"] == 0
    assert ctx["world_state"]["state"] == "uninitialized"


def test_manifest_digest_mismatch_stops(seeded: dict[str, Any]) -> None:
    manifest = json.loads((seeded["artifact_root"] / "manifest.json").read_text())
    manifest["digest"] = "0" * 64
    (seeded["artifact_root"] / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ReplayStop, match="digest mismatch") as exc:
        load_accepted_cohort(
            artifact_root=seeded["artifact_root"],
            repo_root=seeded["repo"],
            expected_count=2,
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "replay_artifact_drift"


def test_duplicate_and_out_of_order_ledger_stop(seeded: dict[str, Any]) -> None:
    ledger = json.loads((seeded["artifact_root"] / "session_ledger.json").read_text())
    ledger["sessions"] = [ledger["sessions"][1], ledger["sessions"][0]]
    (seeded["artifact_root"] / "session_ledger.json").write_text(json.dumps(ledger))
    with pytest.raises(ReplayStop, match="out of order") as exc:
        load_accepted_cohort(
            artifact_root=seeded["artifact_root"],
            repo_root=seeded["repo"],
            expected_count=2,
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "replay_artifact_drift"


def test_candidate_path_escape_stops(seeded: dict[str, Any]) -> None:
    ledger = json.loads((seeded["artifact_root"] / "session_ledger.json").read_text())
    ledger["sessions"][0]["candidate_locator"] = "/etc/passwd"
    (seeded["artifact_root"] / "session_ledger.json").write_text(json.dumps(ledger))
    with pytest.raises(ReplayStop, match="escapes artifact root|missing") as exc:
        load_accepted_cohort(
            artifact_root=seeded["artifact_root"],
            repo_root=seeded["repo"],
            expected_count=2,
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "replay_artifact_unavailable"


def test_candidate_missing_stops(seeded: dict[str, Any]) -> None:
    path = seeded["artifact_root"] / "candidates" / "longmont-c1-session-1.json"
    path.unlink()
    with pytest.raises(ReplayStop, match="candidate file missing") as exc:
        load_accepted_cohort(
            artifact_root=seeded["artifact_root"],
            repo_root=seeded["repo"],
            expected_count=2,
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "replay_artifact_unavailable"


def test_candidate_digest_mismatch_stops(seeded: dict[str, Any]) -> None:
    path = seeded["artifact_root"] / "candidates" / "longmont-c1-session-1.json"
    path.write_text(json.dumps(_candidate("candidate:mutated"), indent=2, sort_keys=True))
    with pytest.raises(ReplayStop, match="digest mismatch") as exc:
        load_accepted_cohort(
            artifact_root=seeded["artifact_root"],
            repo_root=seeded["repo"],
            expected_count=2,
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "replay_artifact_drift"


def test_source_byte_drift_stops(seeded: dict[str, Any]) -> None:
    manifest, _ledger = load_accepted_cohort(
        artifact_root=seeded["artifact_root"],
        repo_root=seeded["repo"],
        expected_count=2,
        expected_digest=seeded["digest"],
    )
    original = seeded["repo"] / manifest.entries[0].original_path
    original.write_text("drifted bytes\n")
    with pytest.raises(ReplayStop, match="drifted") as exc:
        verify_entry_source_bytes(seeded["repo"], manifest.entries[0])
    assert exc.value.boundary == "replay_artifact_drift"


def test_replay_never_calls_extraction_or_model_policy(
    seeded: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("extraction/model seam called")

    monkeypatch.setattr(
        "src.graph_memory.extraction.graph_preview_runner.run_production_extraction",
        boom,
    )
    monkeypatch.setattr(
        "src.graph_memory.extraction.category_candidate_graph_extractor.resolve_category_graph_model",
        boom,
    )
    seams, calls = _success_seams()
    state = run_execute(
        accepted_artifact_root=seeded["artifact_root"],
        repo_root=seeded["repo"],
        dsn=seeded["dsn"],
        seams=seams,
        expected_count=2,
        expected_digest=seeded["digest"],
    )
    assert state.replay_acceptance == "PASS"
    assert state.model_calls == 0
    assert state.candidate_regenerations == 0
    assert state.candidate_rewrites == 0
    assert calls["calls"]["extract"] == 0


def test_non_pristine_world_refused_without_reset(seeded: dict[str, Any]) -> None:
    seams = ReplaySeams(probe_world=lambda _world_id: SimpleNamespace(state="initialized"))
    with pytest.raises(ReplayStop, match="not pristine") as exc:
        run_preflight(
            accepted_artifact_root=seeded["artifact_root"],
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            seams=seams,
            expected_count=2,
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "recap_genesis_probe"
    assert "No reset" in str(exc.value)


def test_historical_world_and_database_rejected(seeded: dict[str, Any]) -> None:
    assert_runtime_dsn(seeded["dsn"])
    with pytest.raises(ReplayStop, match="historical database") as exc:
        assert_runtime_dsn(
            f"postgresql://dungeonmind:x@{EXPECTED_HOST}:{EXPECTED_PORT}/{HISTORICAL_DATABASE_NAME}"
        )
    assert exc.value.boundary == "runtime_guard"
    with pytest.raises(ReplayStop, match="port must be"):
        assert_runtime_dsn(
            f"postgresql://dungeonmind:x@{EXPECTED_HOST}:54329/{DATABASE_NAME}"
        )


def test_exact_candidate_forwarded_unchanged(seeded: dict[str, Any]) -> None:
    seams, _ctx = _success_seams()
    seen: list[dict[str, Any]] = []
    real_prepare = seams.prepare_admission
    assert real_prepare is not None

    def prepare_admission(**kwargs):
        seen.append(copy.deepcopy(kwargs["candidate_graph"]))
        artifact = kwargs["source_artifact"]
        assert getattr(artifact, "world_id") == "dogfood-current-corpus-replay-v1"
        return real_prepare(**kwargs)

    state = run_execute(
        accepted_artifact_root=seeded["artifact_root"],
        repo_root=seeded["repo"],
        dsn=seeded["dsn"],
        seams=replace(seams, prepare_admission=prepare_admission),
        expected_count=2,
        expected_digest=seeded["digest"],
    )
    assert state.replay_acceptance == "PASS"
    assert len(seen) == 2
    expected = [row["graph"] for row in seeded["rows"]]
    assert seen == expected


def test_nonconfirmable_stops_before_later_sessions(seeded: dict[str, Any]) -> None:
    seams, ctx = _success_seams(fail_at="nonconfirmable")
    state = run_execute(
        accepted_artifact_root=seeded["artifact_root"],
        repo_root=seeded["repo"],
        dsn=seeded["dsn"],
        seams=seams,
        expected_count=2,
        expected_digest=seeded["digest"],
    )
    assert state.replay_acceptance == "HOLD"
    assert state.stop is not None
    assert state.stop["boundary"] == "candidate_graph_admission"
    assert ctx["calls"]["confirm"] == 0
    assert "longmont-c2/session-1" in state.stop["sessions_not_attempted"]


def test_stale_parent_stops_without_confirm(seeded: dict[str, Any]) -> None:
    seams, ctx = _success_seams(fail_at="stale_before_confirm")
    state = run_execute(
        accepted_artifact_root=seeded["artifact_root"],
        repo_root=seeded["repo"],
        dsn=seeded["dsn"],
        seams=seams,
        expected_count=2,
        expected_digest=seeded["digest"],
    )
    assert state.replay_acceptance == "HOLD"
    assert state.stop is not None
    assert state.stop["boundary"] == "governed_write_seam"
    assert ctx["calls"]["confirm"] == 0
    assert ctx["calls"]["prepare"] == 1


def test_successful_row_records_source_admission_and_child_continuity(
    seeded: dict[str, Any],
) -> None:
    seams, _ctx = _success_seams()
    state = run_execute(
        accepted_artifact_root=seeded["artifact_root"],
        repo_root=seeded["repo"],
        dsn=seeded["dsn"],
        seams=seams,
        expected_count=2,
        expected_digest=seeded["digest"],
    )
    assert state.replay_acceptance == "PASS"
    assert state.genesis_d0 == "rev:d0"
    parents = [row["sealed_parent_revision"] for row in state.replay_ledger]
    children = [row["receipt_child_revision"] for row in state.replay_ledger]
    assert parents == ["rev:d0", "rev:d1"]
    assert children == ["rev:d1", "rev:d2"]
    for row, seeded_row in zip(state.replay_ledger, seeded["rows"], strict=True):
        proof = row["source_admission"]
        assert proof["source_artifact_id"] == seeded_row["entry"]["source_artifact_id"]
        assert proof["source_revision_id"]
        assert proof["content_sha256"]
        assert row["predecessor_candidate_digest"] == seeded_row["ledger"]["candidate_digest"]


def test_emitted_id_that_cannot_reopen_fails_loadability(seeded: dict[str, Any]) -> None:
    seams, _ctx = _success_seams()
    seams = _attach_product_seams(seams, fail="missing_object")
    with pytest.raises(ReplayStop, match="could not reopen") as exc:
        run_product_smoke(
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            terminal_head="rev:d2",
            replay_ledger=[
                {
                    "campaign_id": "longmont-c1",
                    "session_id": "session-10",
                    "receipt_child_revision": "rev:d1",
                },
                {
                    "campaign_id": "longmont-c2",
                    "session_id": "session-22",
                    "receipt_child_revision": "rev:d2",
                },
            ],
            seams=seams,
        )
    assert exc.value.boundary == "product_loadability"


def test_mireward_fails_when_source_unresolved(seeded: dict[str, Any]) -> None:
    seams, _ctx = _success_seams()
    seams = _attach_product_seams(seams, fail="unresolved_source")
    with pytest.raises(ReplayStop, match="unresolved|dead-ended|no source anchors") as exc:
        run_product_smoke(
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            terminal_head="rev:d2",
            replay_ledger=[
                {
                    "campaign_id": "longmont-c1",
                    "session_id": "session-10",
                    "receipt_child_revision": "rev:d1",
                },
                {
                    "campaign_id": "longmont-c2",
                    "session_id": "session-22",
                    "receipt_child_revision": "rev:d2",
                },
            ],
            seams=seams,
        )
    assert exc.value.boundary == "product_loadability"


def test_mireward_fails_when_source_read_is_partial(seeded: dict[str, Any]) -> None:
    seams, _ctx = _success_seams()
    seams = _attach_product_seams(seams, fail="partial_source")
    with pytest.raises(ReplayStop, match="dead-ended|digest") as exc:
        run_product_smoke(
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            terminal_head="rev:d2",
            replay_ledger=[
                {
                    "campaign_id": "longmont-c1",
                    "session_id": "session-10",
                    "receipt_child_revision": "rev:d1",
                },
                {
                    "campaign_id": "longmont-c2",
                    "session_id": "session-22",
                    "receipt_child_revision": "rev:d2",
                },
            ],
            seams=seams,
        )
    assert exc.value.boundary == "product_loadability"
    assert any("unsupported_locator" in item for item in exc.value.diagnostics)


def test_historical_pin_rejects_terminal_head_leakage(seeded: dict[str, Any]) -> None:
    seams, _ctx = _success_seams()
    seams = _attach_product_seams(seams, fail="pin_leak")
    with pytest.raises(ReplayStop, match="leaked revision|fell forward") as exc:
        run_product_smoke(
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            terminal_head="rev:d2",
            replay_ledger=[
                {
                    "campaign_id": "longmont-c1",
                    "session_id": "session-10",
                    "receipt_child_revision": "rev:d1",
                },
                {
                    "campaign_id": "longmont-c2",
                    "session_id": "session-22",
                    "receipt_child_revision": "rev:d2",
                },
            ],
            seams=seams,
        )
    assert exc.value.boundary == "product_loadability"


def test_partial_stop_cannot_resume_as_pass(seeded: dict[str, Any], tmp_path: Path) -> None:
    seams, ctx = _success_seams(fail_at="nonconfirmable")
    first = run_execute(
        accepted_artifact_root=seeded["artifact_root"],
        repo_root=seeded["repo"],
        dsn=seeded["dsn"],
        seams=seams,
        expected_count=2,
        expected_digest=seeded["digest"],
    )
    assert first.replay_acceptance == "HOLD"
    assert ctx["world_state"]["state"] == "initialized"
    second_seams, _ = _success_seams()
    second_seams = replace(
        second_seams,
        probe_world=lambda _world_id: SimpleNamespace(state=ctx["world_state"]["state"]),
    )
    with pytest.raises(ReplayStop, match="not pristine") as exc:
        run_execute(
            accepted_artifact_root=seeded["artifact_root"],
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            seams=second_seams,
            expected_count=2,
            expected_digest=seeded["digest"],
        )
    assert exc.value.boundary == "recap_genesis_probe"

    run_root = tmp_path / "partial-run"
    run_root.mkdir()
    report = {
        "replay_acceptance": "HOLD",
        "terminal_head": None,
        "stop": first.stop,
        "replay_ledger": first.replay_ledger,
        "model_calls": 0,
        "git_head": "deadbeef" * 5,
    }
    (run_root / "replay_report.json").write_text(json.dumps(report))
    with pytest.raises(ReplayStop, match="refuses a non-PASS"):
        run_product_smoke_from_run(
            completed_replay_run_root=run_root,
            repo_root=seeded["repo"],
            dsn=seeded["dsn"],
            seams=_attach_product_seams(second_seams),
        )


def test_product_smoke_pass_on_injected_reads(seeded: dict[str, Any]) -> None:
    seams, _ctx = _success_seams()
    seams = _attach_product_seams(seams)
    result = run_product_smoke(
        repo_root=seeded["repo"],
        dsn=seeded["dsn"],
        terminal_head="rev:d2",
        replay_ledger=[
            {
                "campaign_id": "longmont-c1",
                "session_id": "session-10",
                "receipt_child_revision": "rev:d1",
            },
            {
                "campaign_id": "longmont-c2",
                "session_id": "session-22",
                "receipt_child_revision": "rev:d2",
            },
        ],
        seams=seams,
        genesis_d0="rev:d0",
    )
    assert result["product_loadability"] == "PASS"
    assert result["mireward"]["node_id"] == "node:location:mireward"
    assert result["mireward"]["source"]["content_sha256"] == "abc123"
    assert result["c1s10_benchmark_pin"]["revision_id"] == "rev:d1"
