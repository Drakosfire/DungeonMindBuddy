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
    save_contribution_index,
    upsert_contribution_in_index,
    write_contribution_record,
)
from scripts import heal_eldyrwild_contribution_integrity as heal

WORLD_ID = "eldyrwild"
D = "contribution:d3d244474789879c"
A = "contribution:2807888820d76c78"
X = "assertion:134135a4f3a2487b"
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


def _assertion_semantic(payload: dict) -> dict:
    """Compare assertions after contribution_id rebinding A→D."""
    out = dict(payload)
    out["contribution_id"] = D
    return out


def test_recovery_artifact_hashes_to_immutable_E() -> None:
    dstar, digest, _raw = heal._load_dstar()
    assert dstar.contribution_id == D
    assert digest == E
    assert dstar.produced_at == "2026-07-29T03:31:24Z"
    assert dstar.supersedes_contribution_id == A
    assert dstar.authored_by == "operator:graph-v1-projection-repair"
    x = next(a for a in dstar.rejected_assertions if a.assertion_id == X)
    assert x.acceptance_state == "rejected"
    assert all(a.contribution_id == D for a in dstar.accepted_assertions)
    assert all(a.contribution_id == D for a in dstar.rejected_assertions)


def test_dstar_transform_matches_parent_a_after_rebinding() -> None:
    """Handoff §B: accepted/rejected sets equal A after A→D contribution_id rebinding."""
    root = world_graph_root()
    parent = load_contribution_record(root, WORLD_ID, A)
    dstar, digest, _ = heal._load_dstar()
    assert digest == E

    expected_accepted_ids = {
        a.assertion_id for a in parent.accepted_assertions if a.assertion_id != X
    }
    expected_rejected_ids = {a.assertion_id for a in parent.rejected_assertions} | {X}
    actual_accepted_ids = {a.assertion_id for a in dstar.accepted_assertions}
    actual_rejected_ids = {a.assertion_id for a in dstar.rejected_assertions}
    assert actual_accepted_ids == expected_accepted_ids
    assert actual_rejected_ids == expected_rejected_ids
    assert X not in actual_accepted_ids

    parent_accepted = {
        a.assertion_id: _assertion_semantic(a.model_dump(mode="json"))
        for a in parent.accepted_assertions
        if a.assertion_id != X
    }
    for assertion in dstar.accepted_assertions:
        assert assertion.model_dump(mode="json") == parent_accepted[assertion.assertion_id]

    parent_rejected = {
        a.assertion_id: _assertion_semantic(a.model_dump(mode="json"))
        for a in parent.rejected_assertions
    }
    x_from_parent = next(a for a in parent.accepted_assertions if a.assertion_id == X)
    parent_rejected[X] = _assertion_semantic(
        x_from_parent.model_dump(mode="json")
        | {"acceptance_state": "rejected"}
    )
    for assertion in dstar.rejected_assertions:
        assert assertion.model_dump(mode="json") == parent_rejected[assertion.assertion_id]

    # Source/campaign fields preserved from A; repair metadata differs by design.
    assert dstar.source_kind == parent.source_kind
    assert dstar.source_artifact_id == parent.source_artifact_id
    assert dstar.source_revision_id == parent.source_revision_id
    assert dstar.extraction_profile == parent.extraction_profile
    assert dstar.campaign_scope == parent.campaign_scope
    assert len(dstar.unresolved_mentions) == len(parent.unresolved_mentions)
    for left, right in zip(
        dstar.unresolved_mentions, parent.unresolved_mentions, strict=True
    ):
        assert left.model_dump(mode="json") == right.model_dump(mode="json")


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
    assert report["reasons"] == ["known_corrupt_state"]
    assert report["E"] == E
    assert report["A_now"] != E
    assert report["ledger_status"] == "failed"
    assert report["index_bucket"] == "failed"
    assert report["L_head"] == "active"
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


def test_already_healed_still_fences_stale_expected_head(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    heal.apply(expected_head_revision_id=head, root=root)
    assert heal.status(root=root)["state"] == "already_healed"

    store = kernel.load_world_graph_revision(root, WORLD_ID, head)
    kernel.publish_world_revision(
        root,
        WORLD_ID,
        store,
        operation_ids=["op:heal-already-healed-stale-fence"],
        expected_parent_revision_id=head,
    )
    new_head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    assert new_head != head

    with pytest.raises(heal.HealError) as exc:
        heal.apply(expected_head_revision_id=head, root=root)
    assert exc.value.code == "stale_head"


def test_canonical_root_requires_live_opt_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_eldyrwild(tmp_path)
    monkeypatch.setattr(heal, "live_world_graph_root", lambda: root)
    monkeypatch.setattr(heal, "world_graph_root", lambda: root)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    with pytest.raises(heal.HealError) as exc:
        heal.apply(expected_head_revision_id=head, root=root, allow_live_world=False)
    assert exc.value.code == "live_world_opt_in_required"


def test_artifact_tamper_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    src = heal._recovery_artifact_path()
    tampered = tmp_path / "tampered.json"
    payload = json.loads(src.read_text())
    payload["produced_at"] = "2099-01-01T00:00:00Z"
    tampered.write_text(json.dumps(payload))
    monkeypatch.setattr(heal, "_recovery_artifact_path", lambda: tampered)
    with pytest.raises(heal.HealError):
        heal.apply(expected_head_revision_id=head, root=root)


def test_lifecycle_only_mismatch_is_not_already_healed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    dstar, _, _ = heal._load_dstar()
    # Exact source bytes, but ledger lifecycle still failed while index is active.
    write_contribution_record(
        root, WORLD_ID, dstar.model_copy(update={"status": "failed"})
    )
    index = load_contribution_index(root, WORLD_ID)
    index = upsert_contribution_in_index(
        index, dstar.model_copy(update={"status": "active"})
    )
    save_contribution_index(root, WORLD_ID, index)

    st = heal.status(root=root)
    assert st["state"] == "eligible"
    assert "partial_state:ledger_lifecycle_stale" in st["reasons"]
    assert st["state"] != "already_healed"


def test_unknown_d_drift_fails_closed(tmp_path: Path) -> None:
    root = _clone_eldyrwild(tmp_path)
    corrupt = load_contribution_record(root, WORLD_ID, D)
    # Unrelated future drift: wrong digest + active ledger while index stays failed.
    # Not known_corrupt (failed/failed) and not index_ok_ledger_corrupt (index != L_head).
    drifted = corrupt.model_copy(
        update={"produced_at": "2099-06-01T00:00:00Z", "status": "active"}
    )
    write_contribution_record(root, WORLD_ID, drifted)

    st = heal.status(root=root)
    assert st["ledger_status"] == "active"
    assert st["index_bucket"] == "failed"
    assert st["state"] == "integrity_failure"
    assert "unknown_d_drift" in st["reasons"]
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    with pytest.raises(heal.HealError) as exc:
        heal.apply(expected_head_revision_id=head, root=root)
    assert exc.value.code == "integrity_failure"


def test_post_write_rebuild_failure_rolls_back_under_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    before_d = world_paths.contribution_path(root, WORLD_ID, D).read_bytes()
    before_index = world_paths.contribution_index_path(root, WORLD_ID).read_bytes()

    real_rebuild = heal.rebuild_from_contributions

    def _boom(*args, **kwargs):
        raise heal.HealError("pinned_rebuild_failed", "injected rebuild failure")

    monkeypatch.setattr(heal, "rebuild_from_contributions", _boom)
    with pytest.raises(heal.HealError) as exc:
        heal.apply(expected_head_revision_id=head, root=root)
    assert exc.value.code == "pinned_rebuild_failed"
    assert world_paths.contribution_path(root, WORLD_ID, D).read_bytes() == before_d
    assert (
        world_paths.contribution_index_path(root, WORLD_ID).read_bytes() == before_index
    )
    monkeypatch.setattr(heal, "rebuild_from_contributions", real_rebuild)


def test_index_save_failure_after_ledger_write_rolls_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ledger written then index save raises: restore both pre-heal byte sequences."""
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    before_d = world_paths.contribution_path(root, WORLD_ID, D).read_bytes()
    before_index = world_paths.contribution_index_path(root, WORLD_ID).read_bytes()

    def _boom(*args, **kwargs):
        raise RuntimeError("injected index save failure")

    monkeypatch.setattr(heal, "save_contribution_index", _boom)
    with pytest.raises(RuntimeError, match="injected index save failure"):
        heal.apply(expected_head_revision_id=head, root=root)
    assert world_paths.contribution_path(root, WORLD_ID, D).read_bytes() == before_d
    assert (
        world_paths.contribution_index_path(root, WORLD_ID).read_bytes() == before_index
    )


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
    assert st["reasons"] == ["known_corrupt_state"]
    assert st["A_now"] != E

    result = heal.apply(expected_head_revision_id=head, root=root)
    assert result["applied"] is True
    assert result["head_revision_id"] == head
    assert result["A_now"] == E
    assert result["index_bucket"] == "active"
    assert result["ledger_status"] == "active"
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

    retry = heal.apply(expected_head_revision_id=head, root=root)
    assert retry["result"] == "already_healed"
    assert retry["applied"] is False
    assert world_paths.contribution_path(root, WORLD_ID, D).read_bytes() == healed_ledger
    assert (
        world_paths.contribution_index_path(root, WORLD_ID).read_bytes() == healed_index
    )

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
        superseded_contribution_id=A,
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
    assert result["ledger_status"] == "active"


def test_partial_state_index_ok_ledger_corrupt_converges(tmp_path: Path) -> None:
    """Inverse crash path: index already at L_head, ledger still corrupt."""
    root = _clone_eldyrwild(tmp_path)
    head = kernel.open_world_graph_head(root, WORLD_ID).head_revision_id
    corrupt = load_contribution_record(root, WORLD_ID, D)
    assert compute_contribution_source_payload_sha256(corrupt) != E

    # Leave corrupt ledger bytes; move index bucket to active (L_head).
    index = upsert_contribution_in_index(
        load_contribution_index(root, WORLD_ID),
        corrupt.model_copy(update={"status": "active"}),
    )
    save_contribution_index(root, WORLD_ID, index)

    st = heal.status(root=root)
    assert st["state"] == "eligible"
    assert "partial_state:index_ok_ledger_corrupt" in st["reasons"]
    assert st["A_now"] != E
    assert st["index_bucket"] == "active"

    result = heal.apply(expected_head_revision_id=head, root=root)
    assert result["applied"] is True
    assert result["A_now"] == E
    assert result["index_bucket"] == "active"
    assert result["ledger_status"] == "active"
