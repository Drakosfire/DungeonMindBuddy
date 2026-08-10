"""Owning tests for Eldyrwild contribution:d3d244474789879c integrity heal."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest

import graph_memory.kernel as kernel
from apps.live_control_server.config import world_graph_root
from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.contributions import compute_contribution_source_payload_sha256
from graph_memory.world_supergraph import paths as world_paths
from graph_memory.world_supergraph.contribution_store import (
    load_contribution_index,
    load_contribution_record,
    write_contribution_record,
)
from scripts import heal_eldyrwild_contribution_integrity as heal

WORLD_ID = "eldyrwild"
D = "contribution:d3d244474789879c"
E = "f312aa5895c9d9a8bfd77b815f47278a4abaffbe699fd6c401adf723fefaf1e5"
HIST = (
    "rev:4d0636a05841efd6958014b655ccf40e",
    "rev:bbf29b974f0162dc8b8fbe080d93ae00",
    "rev:a3262c8102f61f490e11444d9fc28068",
)


def _clone_eldyrwild(tmp_path: Path) -> Path:
    src_root = world_graph_root()
    eldyrwild_src = src_root / "graph_memory" / "worlds" / "eldyrwild"
    assert eldyrwild_src.is_dir(), f"missing Eldyrwild store at {eldyrwild_src}"
    (tmp_path / "graph_memory" / "worlds").mkdir(parents=True)
    shutil.copytree(eldyrwild_src, tmp_path / "graph_memory" / "worlds" / "eldyrwild")
    runs = src_root / "graph_memory" / "runs"
    if runs.is_dir():
        os.symlink(runs, tmp_path / "graph_memory" / "runs")
    return tmp_path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _non_d_hashes(root: Path) -> dict[str, str]:
    contrib_dir = world_paths.world_dir(root, WORLD_ID) / "contributions"
    out: dict[str, str] = {}
    for path in sorted(contrib_dir.glob("contribution__*.json")):
        if path.name == "contribution__d3d244474789879c.json":
            continue
        out[path.name] = _sha(path)
    return out


def _rev_tree_digest(root: Path) -> str:
    rev_root = world_paths.world_dir(root, WORLD_ID) / "revisions"
    h = hashlib.sha256()
    for path in sorted(rev_root.rglob("*")):
        if path.is_file():
            h.update(path.relative_to(rev_root).as_posix().encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def test_recovery_artifact_hashes_to_immutable_E() -> None:
    dstar, digest, _raw = heal._load_dstar()
    assert dstar.contribution_id == D
    assert digest == E
    assert dstar.produced_at == "2026-07-29T03:31:24Z"
    assert dstar.supersedes_contribution_id == "contribution:2807888820d76c78"
    assert dstar.authored_by == "operator:graph-v1-projection-repair"
    x = next(
        a
        for a in dstar.rejected_assertions
        if a.assertion_id == "assertion:134135a4f3a2487b"
    )
    assert x.acceptance_state == "rejected"
    assert all(a.contribution_id == D for a in dstar.accepted_assertions)
    assert all(a.contribution_id == D for a in dstar.rejected_assertions)


def test_historical_digests_agree_on_E() -> None:
    root = world_graph_root()
    digests = []
    for rid in HIST:
        store = kernel.load_world_graph_revision(root, WORLD_ID, rid)
        digests.append((store.contribution_source_payload_sha256 or {}).get(D))
    assert digests and all(d == E for d in digests)


def test_status_read_only_on_real_clone(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    before_tree = _rev_tree_digest(root)
    before_ledgers = _non_d_hashes(root)
    before_d = _sha(world_paths.contribution_path(root, WORLD_ID, D))
    before_index = _sha(world_paths.contribution_index_path(root, WORLD_ID))

    report = heal.status(root=root)
    assert report["state"] == "eligible"
    assert report["E"] == E
    assert report["A_now"] != E
    assert report["historical"]["digest_coherent"] is True

    assert _rev_tree_digest(root) == before_tree
    assert _non_d_hashes(root) == before_ledgers
    assert _sha(world_paths.contribution_path(root, WORLD_ID, D)) == before_d
    assert _sha(world_paths.contribution_index_path(root, WORLD_ID)) == before_index


def test_stale_head_apply_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    before_d = world_paths.contribution_path(root, WORLD_ID, D).read_bytes()
    before_index = world_paths.contribution_index_path(root, WORLD_ID).read_bytes()

    # Advance clone head with unrelated publish.
    store = kernel.load_world_graph_revision(root, WORLD_ID, head)
    kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=["op:heal-stale-head-fence"],
        expected_parent_revision_id=head,
    )
    new_head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    assert new_head != head

    with pytest.raises(heal.HealError) as exc:
        heal.apply(expected_head_revision_id=head, root=root)
    assert exc.value.code == "stale_head"
    assert world_paths.contribution_path(root, WORLD_ID, D).read_bytes() == before_d
    assert (
        world_paths.contribution_index_path(root, WORLD_ID).read_bytes() == before_index
    )


def test_canonical_root_requires_live_opt_in(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Point live root at a temp path equal to resolved root without allow flag.
    root = _clone_eldyrwild(tmp_path)
    monkeypatch.setattr(heal, "live_world_graph_root", lambda: root)
    monkeypatch.setattr(heal, "world_graph_root", lambda: root)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    with pytest.raises(heal.HealError) as exc:
        heal.apply(expected_head_revision_id=head, root=root, allow_live_world=False)
    assert exc.value.code == "live_world_opt_in_required"


def test_artifact_tamper_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    # Point recovery artifact at a tampered copy.
    src = heal._recovery_artifact_path()
    tampered = tmp_path / "tampered.json"
    payload = json.loads(src.read_text())
    payload["produced_at"] = "2099-01-01T00:00:00Z"
    tampered.write_text(json.dumps(payload))
    monkeypatch.setattr(heal, "_recovery_artifact_path", lambda: tampered)
    with pytest.raises(heal.HealError):
        heal.apply(expected_head_revision_id=head, root=root)


def test_real_clone_heal_preserves_head_and_rebuilds(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    before_tree = _rev_tree_digest(root)
    before_others = _non_d_hashes(root)
    before_index = load_contribution_index(root, WORLD_ID)
    before_all = list(before_index.all_contribution_ids)
    before_baseline = before_index.baseline_revision_id

    st = heal.status(root=root)
    assert st["state"] == "eligible"
    assert st["A_now"] != E

    result = heal.apply(expected_head_revision_id=head, root=root)
    assert result["applied"] is True
    assert result["head_revision_id"] == head
    assert result["A_now"] == E
    assert result["index_bucket"] == "active"
    assert _rev_tree_digest(root) == before_tree
    assert _non_d_hashes(root) == before_others
    assert "rebuild_equivalent_to_pinned_revision" in result["pinned_rebuild_diagnostics"]
    assert "rebuild_equivalent_to_head" in result["unpinned_rebuild_diagnostics"]

    after_index = load_contribution_index(root, WORLD_ID)
    assert list(after_index.all_contribution_ids) == before_all
    assert after_index.baseline_revision_id == before_baseline
    assert D in after_index.active_contribution_ids
    assert D not in after_index.failed_contribution_ids

    ledger = load_contribution_record(root, WORLD_ID, D)
    assert compute_contribution_source_payload_sha256(ledger) == E
    assert ledger.status == "active"

    healed_ledger = world_paths.contribution_path(root, WORLD_ID, D).read_bytes()
    healed_index = world_paths.contribution_index_path(root, WORLD_ID).read_bytes()

    # exact retry — no byte churn
    retry = heal.apply(expected_head_revision_id=head, root=root)
    assert retry["result"] == "already_healed"
    assert retry["applied"] is False
    assert world_paths.contribution_path(root, WORLD_ID, D).read_bytes() == healed_ledger
    assert (
        world_paths.contribution_index_path(root, WORLD_ID).read_bytes() == healed_index
    )

    # different-source collision against healed clone
    colliding = GraphContribution.model_validate_json(healed_ledger).model_copy(
        update={"produced_at": "2099-01-01T00:00:00Z"}
    )
    before = {
        "head": kernel.open_world_graph_head(root, WORLD_ID).head_revision_id,
        "ledger": world_paths.contribution_path(root, WORLD_ID, D).read_bytes(),
        "index": world_paths.contribution_index_path(root, WORLD_ID).read_bytes(),
    }
    collision = kernel.supersede_graph_contribution(
        root,
        world_id=WORLD_ID,
        new_contribution=colliding,
        superseded_contribution_id="contribution:2807888820d76c78",
    )
    assert collision.published is False
    assert collision.failure_code == "source_bound_digest_collision"
    assert kernel.open_world_graph_head(root, WORLD_ID).head_revision_id == before["head"]
    assert (
        world_paths.contribution_path(root, WORLD_ID, D).read_bytes() == before["ledger"]
    )
    assert (
        world_paths.contribution_index_path(root, WORLD_ID).read_bytes()
        == before["index"]
    )


def test_partial_state_index_stale_converges(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    dstar, _, _ = heal._load_dstar()
    # Simulate crash after ledger write, before index update.
    write_contribution_record(
        root, WORLD_ID, dstar.model_copy(update={"status": "active"})
    )
    st = heal.status(root=root)
    assert st["state"] == "eligible"
    assert "partial_state:ledger_healed_index_stale" in st["reasons"]

    result = heal.apply(expected_head_revision_id=head, root=root)
    assert result["applied"] is True
    assert result["A_now"] == E
    assert result["index_bucket"] == "active"
