from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "frozen_42_session_acceptance", ROOT / "tools" / "run_frozen_42_session_acceptance.py"
)
assert spec and spec.loader
acc = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = acc
spec.loader.exec_module(acc)

NOTEBOOK_FIXTURE = Path(
    os.environ.get(
        "DMB_FROZEN_NOTEBOOK_ROOT",
        "/tmp/DungeonMindBuddy-full-corpus-world-graph-ingestion-v1",
    )
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _arm_tree(tmp_path: Path, arm: str = "openai-gpt-5.4-mini") -> tuple[Path, Path, dict[str, object]]:
    notebook = tmp_path / "notebook"
    production = tmp_path / "production"
    sessions_by_arm: dict[str, list[dict[str, object]]] = {name: [] for name in acc.ARMS}
    for campaign, session in acc.jobs():
        recap = f"# {campaign} session {session}\n\nObserved.\n"
        historical = f"full-corpus:{campaign}:session-{session}:{'a' * 12}"
        _write(notebook / f"corpus/eldyrwild-markdown/{campaign}/session-{session}.md", recap)
        _write(production / f"corpus/eldyrwild-markdown/{campaign}/session-{session}.md", recap)
        rel_src = f"corpus/eldyrwild-markdown/{campaign}/session-{session}.md"
        for name in acc.ARMS:
            rel_cand = (
                f"out/full_corpus_world_graph_ingestion/{name}/runs/{campaign}/"
                f"session-{session:02d}/candidate_graph.json"
            )
            candidate = {
                "nodes": [{"id": f"{name}-{session}", "kind": "npc"}],
                "edges": [],
                "source_artifact_ids": [historical],
            }
            _write(notebook / rel_cand, json.dumps(candidate))
            sessions_by_arm[name].append(
                {
                    "campaign": campaign,
                    "session": session,
                    "candidate_sha256": _sha(json.dumps(candidate)),
                    "source_sha256": _sha(recap),
                    "source_artifact_id": historical,
                    "candidate_path": rel_cand,
                    "source_path": rel_src,
                }
            )
    manifest = {
        "schema": "dmb_full_corpus_acceptance_manifest_v1",
        "reviewed_notebook_head": acc.CANDIDATE_FROZEN_HEAD,
        "corpus": "frozen_42_session",
        "corpus_sessions": "C1 S1-17 + C2 S1-25",
        "do_not_merge": True,
        "experiment_claim": acc.EXPERIMENT_CLAIM,
        "arms": {
            name: {"candidate_count": 42, "sessions": sessions_by_arm[name]}
            for name in acc.ARMS
        },
    }
    _write(notebook / acc.MANIFEST_REL, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return notebook, production, manifest


def _patch_git(
    monkeypatch: pytest.MonkeyPatch,
    *,
    notebook_head: str | None = None,
    dirty: bool = False,
    ancestor: bool = True,
) -> None:
    def fake_head(root: Path) -> str:
        if "notebook" in Path(root).as_posix():
            return acc.NOTEBOOK_HEAD if notebook_head is None else notebook_head
        return acc.GENESIS_MERGE_SHA

    monkeypatch.setattr(acc, "git_head", fake_head)
    monkeypatch.setattr(
        acc,
        "git_status_porcelain",
        lambda root: " M dirty" if dirty and "notebook" in Path(root).as_posix() else "",
    )
    monkeypatch.setattr(acc, "git_is_ancestor", lambda root, ancestor_sha, head="HEAD": ancestor)


def test_jobs_are_the_frozen_42_session_corpus() -> None:
    assert acc.jobs() == [("longmont-c1", n) for n in range(1, 18)] + [("longmont-c2", n) for n in range(1, 26)]
    assert ("longmont-c2", 26) not in acc.jobs()
    assert ("longmont-c2", 27) not in acc.jobs()
    assert len(acc.jobs()) == 42


def test_world_id_is_derived_from_arm() -> None:
    assert acc.derived_world_id("openai-gpt-5.4-mini") == "dogfood-frozen42-openai-v1"
    assert acc.derived_world_id("deepseek-v4.1-flash") == "dogfood-frozen42-deepseek-v1"
    assert "world_id" not in inspect.signature(acc.run_arm).parameters


def test_exact_notebook_head_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, _production, _manifest = _arm_tree(tmp_path)
    _patch_git(monkeypatch)
    assert acc.assert_notebook_checkout(notebook)["notebook_head"] == acc.NOTEBOOK_HEAD


def test_wrong_notebook_head_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, _production, _manifest = _arm_tree(tmp_path)
    _patch_git(monkeypatch, notebook_head="deadbeef" * 5)
    with pytest.raises(acc.AcceptanceError, match="notebook HEAD"):
        acc.assert_notebook_checkout(notebook)


def test_dirty_notebook_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, _production, _manifest = _arm_tree(tmp_path)
    _patch_git(monkeypatch, dirty=True)
    with pytest.raises(acc.AcceptanceError, match="dirty"):
        acc.assert_notebook_checkout(notebook)


def test_frozen_manifest_accepted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, production, _manifest = _arm_tree(tmp_path)
    _patch_git(monkeypatch)
    seal = acc.verify_frozen_inputs(
        "openai-gpt-5.4-mini", notebook_root=notebook, production_root=production
    )
    assert seal["candidate_count"] == 42
    assert seal["model_calls"] == 0
    assert [(row["campaign"], row["session"]) for row in seal["sessions"]] == acc.jobs()


def test_manifest_candidate_drift_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, production, _manifest = _arm_tree(tmp_path)
    path = notebook / acc.MANIFEST_REL
    frozen = json.loads(path.read_text(encoding="utf-8"))
    frozen["arms"]["openai-gpt-5.4-mini"]["sessions"][0]["candidate_sha256"] = "0" * 64
    path.write_text(json.dumps(frozen, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _patch_git(monkeypatch)
    with pytest.raises(acc.AcceptanceError, match="candidate_sha256"):
        acc.verify_frozen_inputs(
            "openai-gpt-5.4-mini", notebook_root=notebook, production_root=production
        )


def test_production_source_mismatch_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, production, manifest = _arm_tree(tmp_path)
    source = production / str(manifest["arms"]["openai-gpt-5.4-mini"]["sessions"][0]["source_path"])
    source.write_text("# drifted canonical source\n", encoding="utf-8")
    _patch_git(monkeypatch)
    with pytest.raises(acc.AcceptanceError, match="current-main source hash mismatch"):
        acc.verify_frozen_inputs(
            "openai-gpt-5.4-mini", notebook_root=notebook, production_root=production
        )


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://x@localhost/full_corpus_live",
        "postgresql://x@localhost/eldyrwild_full_corpus",
        "postgresql://x@localhost/unlabelled",
        "postgresql://x@127.0.0.1:54329/dungeonmind_full_corpus_openai",
        "postgresql://x@127.0.0.1:54331/dmb_full_corpus_openai",
        "postgresql://x@127.0.0.1:54330/dmb_full_corpus_deepseek",
        "postgresql://x@example.com:54329/dmb_full_corpus_openai",
        "postgresql://x@10.0.0.5:54329/dmb_full_corpus_deepseek",
        "postgresql://x@localhost/dmb_full_corpus_openai",
    ],
)
def test_isolation_guard_refuses_non_rehearsal_authority(dsn: str) -> None:
    with pytest.raises(acc.AcceptanceError):
        acc.assert_isolated_dsn(dsn)


@pytest.mark.parametrize(
    "dsn",
    [
        "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai",
        "postgresql://x@localhost:54329/dmb_full_corpus_deepseek",
    ],
)
def test_isolation_guard_accepts_exact_loopback_rehearsal_targets(dsn: str) -> None:
    acc.assert_isolated_dsn(dsn)


@pytest.mark.parametrize(
    "arm,dsn",
    [
        ("openai-gpt-5.4-mini", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai"),
        ("deepseek-v4.1-flash", "postgresql://x@localhost:54329/dmb_full_corpus_deepseek"),
    ],
)
def test_arm_authority_accepts_designated_pairings(arm: str, dsn: str) -> None:
    acc.assert_arm_authority(arm, dsn)


@pytest.mark.parametrize(
    "arm,dsn",
    [
        ("openai-gpt-5.4-mini", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_deepseek"),
        ("deepseek-v4.1-flash", "postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai"),
    ],
)
def test_arm_authority_rejects_swapped_rehearsal_databases(arm: str, dsn: str) -> None:
    with pytest.raises(acc.AcceptanceError, match="must use rehearsal database"):
        acc.assert_arm_authority(arm, dsn)


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

    def fake_notebook(root: Path) -> dict[str, str]:
        called.append("notebook")
        raise RuntimeError("stop after arm authority")

    monkeypatch.setattr(acc, "assert_notebook_checkout", fake_notebook)
    with pytest.raises(RuntimeError, match="stop after arm authority"):
        acc.run_arm(
            arm=arm,
            dsn=dsn,
            notebook_root=tmp_path,
            production_root=tmp_path,
            output=tmp_path,
        )
    assert called == ["notebook"]


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
    def boom(root: Path) -> dict[str, str]:
        raise AssertionError("must not inspect notebook for mismatched arm")

    monkeypatch.setattr(acc, "assert_notebook_checkout", boom)
    monkeypatch.setattr(
        acc,
        "inspect_authority_counts",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not touch DB")),
    )
    with pytest.raises(acc.AcceptanceError, match="must use rehearsal database"):
        acc.run_arm(
            arm=arm,
            dsn=dsn,
            notebook_root=tmp_path,
            production_root=tmp_path,
            output=tmp_path,
        )


def test_path_containment_rejects_files_outside_the_repo(tmp_path: Path) -> None:
    outsider = tmp_path / "escape.md"
    outsider.write_text("not in repo\n", encoding="utf-8")
    with pytest.raises(acc.AcceptanceError, match="contained"):
        acc._contained_file(ROOT, outsider)


def test_path_containment_rejects_sibling_prefix_escape() -> None:
    decoy_root = Path(str(ROOT) + "-evil")
    with pytest.raises(acc.AcceptanceError, match="contained"):
        acc._contained_file(ROOT, decoy_root / "candidate_graph.json")


def test_missing_candidate_never_invokes_extraction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    notebook, production, _manifest = _arm_tree(tmp_path)
    first = acc.jobs()[0]
    candidate = (
        notebook
        / "out/full_corpus_world_graph_ingestion/openai-gpt-5.4-mini/runs"
        / first[0]
        / f"session-{first[1]:02d}"
        / "candidate_graph.json"
    )
    candidate.unlink()
    _patch_git(monkeypatch)

    def boom(*args: object, **kwargs: object) -> None:
        raise AssertionError("extraction/prepare must not run for a missing candidate")

    monkeypatch.setattr(acc, "_prepare_extract_promote", boom)
    with pytest.raises(acc.AcceptanceError, match="missing repository file"):
        acc.verify_frozen_inputs(
            "openai-gpt-5.4-mini", notebook_root=notebook, production_root=production
        )


def test_runner_does_not_own_extraction_or_model_clients() -> None:
    assert acc.runner_owns_forbidden_imports() == []


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


def test_runner_binds_world_id_before_admission_without_changing_production_creator(
    tmp_path: Path,
) -> None:
    recap = tmp_path / "recap.md"
    recap.write_text("# Recap\n\nObserved.\n", encoding="utf-8")
    canonical = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c1",
        session_id="session-1",
        recap_path=recap,
    )
    assert canonical.world_id is None
    bound = acc.bind_artifact_world(canonical, world_id="dogfood-frozen42-openai-v1")
    assert bound.world_id == "dogfood-frozen42-openai-v1"
    assert canonical.world_id is None


def test_accepted_proposals_reads_v2_flat_effect() -> None:
    package = {
        "effect": {
            "accepted_proposals": [
                {
                    "assertion_id": "assertion:loc",
                    "assertion_kind": "node",
                    "subject_node_id": "loc:river-edge-pub",
                    "identity_resolution_outcome": "created_new",
                },
                {
                    "assertion_id": "assertion:edge",
                    "assertion_kind": "edge",
                    "predicate": "located_in",
                    "subject_node_id": "npc:pippa",
                    "target_node_id": "loc:river-edge-pub",
                },
            ]
        }
    }
    proposals = acc.accepted_proposals(package)
    assert set(proposals) == {"assertion:loc", "assertion:edge"}
    assert proposals["assertion:edge"]["predicate"] == "located_in"


def test_created_new_existing_object_is_rejected_before_confirm() -> None:
    context = SimpleNamespace(
        objects={"loc:river-edge-pub": SimpleNamespace(kind="location", label="The River's Edge Pub")}
    )
    selectable, rejected, published_edges = acc.select_confirmable_assertions(
        [
            {
                "selectable": True,
                "kind": "object",
                "identity_outcome": "created_new",
                "assertion_id": "assertion:loc",
                "slice_qualified_id": "0::assertion:loc",
            },
            {
                "selectable": True,
                "kind": "object",
                "identity_outcome": "created_new",
                "assertion_id": "assertion:new",
                "slice_qualified_id": "0::assertion:new",
            },
            {
                "selectable": True,
                "kind": "object",
                "identity_outcome": "created_new",
                "assertion_id": "assertion:warning",
                "slice_qualified_id": "0::assertion:warning",
            },
            {
                "selectable": True,
                "kind": "relationship",
                "assertion_id": "assertion:edge",
                "slice_qualified_id": "0::assertion:edge",
            },
        ],
        assertions={
            "assertion:loc": {
                "assertion_id": "assertion:loc",
                "subject_node_id": "loc:river-edge-pub",
                "identity_resolution_outcome": "created_new",
            },
            "assertion:new": {
                "assertion_id": "assertion:new",
                "subject_node_id": "npc:new-person",
                "identity_resolution_outcome": "created_new",
                "value": {"kind": "npc"},
            },
            "assertion:warning": {
                "assertion_id": "assertion:warning",
                "subject_node_id": "note:warning",
                "identity_resolution_outcome": "created_new",
                "value": {"kind": "warning"},
            },
            "assertion:edge": {
                "assertion_id": "assertion:edge",
                "predicate": "located_in",
                "subject_node_id": "npc:new-person",
                "target_node_id": "loc:river-edge-pub",
            },
        },
        context=context,
        candidate={
            "nodes": [
                {"id": "loc:river-edge-pub", "kind": "location"},
                {"id": "npc:new-person", "kind": "npc"},
            ]
        },
    )
    assert "0::assertion:loc" not in selectable
    assert "0::assertion:new" in selectable
    assert "0::assertion:warning" not in selectable
    assert rejected["parent_binding_mismatch"] == 1
    assert rejected["unmapped_kind"] == 1
    assert published_edges == 1
    assert "0::assertion:edge" in selectable


def test_historical_source_rebinding_remains_runner_private(tmp_path: Path) -> None:
    recap = tmp_path / "recap.md"
    recap.write_text("# Recap\n\nObserved.\n", encoding="utf-8")
    canonical = create_recap_source_artifact(
        tmp_path,
        campaign_id="longmont-c1",
        session_id="session-1",
        recap_path=recap,
    )
    historical = "full-corpus:longmont-c1:session-1:verified"
    aliased = acc.register_verified_historical_recap(
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
    assert aliased.lineage["acceptance_notebook"] == "pr715-frozen-42-session"


def test_wrong_parent_refuses_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, production, manifest = _arm_tree(tmp_path)
    seal = manifest["arms"]["openai-gpt-5.4-mini"]["sessions"][0]
    monkeypatch.setattr(
        acc,
        "_load_mutation_context",
        lambda *args, **kwargs: SimpleNamespace(revision_id="rev:other", head_revision_id="rev:other", objects={}),
    )
    monkeypatch.setattr(
        acc,
        "_prepare_extract_promote",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not prepare wrong parent")),
    )
    with pytest.raises(acc.AcceptanceError, match="chronology drift"):
        acc.publish_session(
            dsn="postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai",
            world_id="dogfood-frozen42-openai-v1",
            seal=seal,
            expected_parent="rev:d0",
            notebook_root=notebook,
            production_root=production,
        )


def test_wrong_frozen_digest_refuses_publication(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    notebook, production, manifest = _arm_tree(tmp_path)
    seal = dict(manifest["arms"]["openai-gpt-5.4-mini"]["sessions"][0])
    seal["candidate_sha256"] = "0" * 64
    monkeypatch.setattr(
        acc,
        "_prepare_extract_promote",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not prepare drifted candidate")),
    )
    with pytest.raises(acc.AcceptanceError, match="candidate digest drift"):
        acc.publish_session(
            dsn="postgresql://x@127.0.0.1:54329/dmb_full_corpus_openai",
            world_id="dogfood-frozen42-openai-v1",
            seal=seal,
            expected_parent="rev:d0",
            notebook_root=notebook,
            production_root=production,
        )


def test_sanitize_keeps_first_duplicate_and_drops_invalid_node_types() -> None:
    payload = {
        "nodes": [
            {"node_id": "candidate:shop", "node_type": "location", "label": "Shop"},
            {"node_id": "candidate:shop", "node_type": "organization", "label": "Shop"},
            {"node_id": "candidate:wing", "node_type": "sublocation", "label": "Wing"},
            {"node_id": "candidate:ok", "node_type": "character", "label": "Ok"},
        ],
        "edges": [
            {"edge_id": "e-wing", "from_node_id": "candidate:ok", "to_node_id": "candidate:wing"},
            {"edge_id": "e-shop", "from_node_id": "candidate:ok", "to_node_id": "candidate:shop"},
        ],
        "beats": [
            {
                "beat_id": "b1",
                "involved_node_ids": ["candidate:wing", "candidate:ok"],
                "unresolved_thread_node_ids": [],
            }
        ],
        "proposed_writes": [
            {"write_id": "w-wing", "target_id": "candidate:wing"},
            {"write_id": "w-shop", "target_id": "candidate:shop"},
        ],
    }
    sanitized, rejected = acc.sanitize_candidate_for_load(payload)
    kept_ids = [node["node_id"] for node in sanitized["nodes"]]
    assert kept_ids == ["candidate:shop", "candidate:ok"]
    assert sanitized["nodes"][0]["node_type"] == "location"
    assert [edge["edge_id"] for edge in sanitized["edges"]] == ["e-shop"]
    assert sanitized["beats"][0]["involved_node_ids"] == ["candidate:ok"]
    assert [write["write_id"] for write in sanitized["proposed_writes"]] == ["w-shop"]
    assert rejected == {
        "duplicate_node_id": 1,
        "invalid_node_type": 1,
        "missing_edge_endpoint": 1,
        "missing_beat_node": 1,
        "missing_write_target": 1,
    }
    unchanged, empty = acc.sanitize_candidate_for_load(
        {"nodes": [{"node_id": "candidate:ok", "node_type": "character"}], "edges": []}
    )
    assert empty == {}
    assert len(unchanged["nodes"]) == 1


def test_semantic_benchmark_remains_hold_after_bounded_discovery() -> None:
    assert acc.SEMANTIC_BENCHMARK_DISCOVERY["selected"] is None
    assert acc.SEMANTIC_BENCHMARK_DISCOVERY["verdict"] == "SEMANTIC MODEL SELECTION HOLD"
    assert len(acc.SEMANTIC_BENCHMARK_DISCOVERY["inspected"]) == 3


def _notebook_is_reviewed_head() -> bool:
    if not (NOTEBOOK_FIXTURE / ".git").exists():
        return False
    try:
        return acc.git_head(NOTEBOOK_FIXTURE) == acc.NOTEBOOK_HEAD
    except acc.AcceptanceError:
        return False


@pytest.mark.skipif(not _notebook_is_reviewed_head(), reason="reviewed #715 notebook checkout is not mounted")
def test_real_notebook_and_current_main_sources_match_frozen_manifest() -> None:
    status = acc.git_status_porcelain(NOTEBOOK_FIXTURE)
    assert status.strip() == ""
    for arm in acc.ARMS:
        seal = acc.verify_frozen_inputs(arm, notebook_root=NOTEBOOK_FIXTURE, production_root=ROOT)
        assert seal["candidate_count"] == 42
        assert seal["model_calls"] == 0
        assert ("longmont-c2", 26) not in [(row["campaign"], row["session"]) for row in seal["sessions"]]
        assert ("longmont-c2", 27) not in [(row["campaign"], row["session"]) for row in seal["sessions"]]


@pytest.mark.skipif(not _notebook_is_reviewed_head(), reason="reviewed #715 notebook checkout is not mounted")
def test_sanitize_makes_deepseek_duplicate_graphs_loadable() -> None:
    from graph_memory.candidate_graph_to_contribution import (
        CandidateGraphMappingError,
        load_typed_candidate_graph,
    )

    notebook = NOTEBOOK_FIXTURE / "out/full_corpus_world_graph_ingestion/deepseek-v4.1-flash/runs"
    for rel, expected in (
        ("longmont-c2/session-09/candidate_graph.json", {"duplicate_node_id": 3, "invalid_node_type": 1}),
        ("longmont-c2/session-12/candidate_graph.json", {"duplicate_node_id": 1}),
    ):
        raw = json.loads((notebook / rel).read_text(encoding="utf-8"))
        with pytest.raises(CandidateGraphMappingError):
            load_typed_candidate_graph(raw)
        sanitized, rejected = acc.sanitize_candidate_for_load(raw)
        load_typed_candidate_graph(sanitized)
        for key, count in expected.items():
            assert rejected.get(key, 0) == count, (rel, rejected)
