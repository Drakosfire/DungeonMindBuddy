#!/usr/bin/env python3
"""Fixed-target heal for Eldyrwild contribution:d3d244474789879c replay integrity.

Restores only the mutable contribution ledger/index for D from the checked-in
recovery artifact so they match immutable revision-bound source digest E.
Does not publish a World Graph revision or rewrite revision files.

Usage:
  uv run python scripts/heal_eldyrwild_contribution_integrity.py status [--root PATH]
  uv run python scripts/heal_eldyrwild_contribution_integrity.py apply \\
      --expected-head-revision-id REV [--root PATH] [--allow-live-world]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Literal

_REPO_ROOT = Path(__file__).resolve().parents[1]
for _path in (str(_REPO_ROOT), str(_REPO_ROOT / "src")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from apps.live_control_server.config import (  # noqa: E402
    live_world_graph_root,
    world_graph_root,
)
from graph_memory.kernel.contribution_models import GraphContribution  # noqa: E402
from graph_memory.kernel.contributions import (  # noqa: E402
    compute_contribution_source_payload_sha256,
)
from graph_memory.kernel.contribution_rebuild import (  # noqa: E402
    rebuild_from_contributions,
)
from graph_memory.world_supergraph import paths as world_paths  # noqa: E402
from graph_memory.world_supergraph.contribution_store import (  # noqa: E402
    _exclusive_contribution_index_lock,
    load_contribution_index,
    load_contribution_record,
    save_contribution_index,
    upsert_contribution_in_index,
    write_contribution_record,
)
from graph_memory.world_supergraph.storage import (  # noqa: E402
    load_world_graph_revision,
    open_world_graph_head,
)

WORLD_ID = "eldyrwild"
CONTRIBUTION_ID = "contribution:d3d244474789879c"
HISTORICAL_REVISIONS = (
    "rev:4d0636a05841efd6958014b655ccf40e",
    "rev:bbf29b974f0162dc8b8fbe080d93ae00",
    "rev:a3262c8102f61f490e11444d9fc28068",
)
RECOVERY_ARTIFACT_REL = Path(
    "graph_data/maintenance/eldyrwild/recovered-contribution-d3d244474789879c.json"
)

HealStatusName = Literal[
    "eligible", "already_healed", "ineligible", "integrity_failure"
]


class HealError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def _repo_root() -> Path:
    return _REPO_ROOT


def _resolve_root(root: Path | None) -> Path:
    return (root if root is not None else world_graph_root()).resolve()


def _is_canonical_live_root(resolved: Path) -> bool:
    return resolved == live_world_graph_root().resolve()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _recovery_artifact_path() -> Path:
    return _repo_root() / RECOVERY_ARTIFACT_REL


def _load_dstar() -> tuple[GraphContribution, str, str]:
    path = _recovery_artifact_path()
    if not path.is_file():
        raise HealError("recovery_artifact_missing", f"missing recovery artifact: {path}")
    raw = path.read_bytes()
    contrib = GraphContribution.model_validate_json(raw)
    if contrib.contribution_id != CONTRIBUTION_ID:
        raise HealError(
            "recovery_artifact_identity",
            f"recovery artifact contribution_id {contrib.contribution_id!r} != {CONTRIBUTION_ID!r}",
        )
    digest = compute_contribution_source_payload_sha256(contrib)
    return contrib, digest, _sha256_bytes(raw)


def _bound_digest(store: Any, contribution_id: str) -> str | None:
    for entry in store.contribution_replay_manifest or []:
        if entry.contribution_id == contribution_id:
            return entry.source_payload_sha256
    return (store.contribution_source_payload_sha256 or {}).get(contribution_id)


def _manifest_lifecycle(store: Any, contribution_id: str) -> str | None:
    for entry in store.contribution_replay_manifest or []:
        if entry.contribution_id == contribution_id:
            return entry.status
    return None


def _historical_digest_report(root: Path) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    digests: list[str] = []
    for rid in HISTORICAL_REVISIONS:
        store = load_world_graph_revision(root, WORLD_ID, rid)
        e = (store.contribution_source_payload_sha256 or {}).get(CONTRIBUTION_ID)
        man = list(store.contribution_replay_manifest or [])
        entry = next((x for x in man if x.contribution_id == CONTRIBUTION_ID), None)
        digests.append(e or "")
        rows.append(
            {
                "revision_id": rid,
                "source_payload_sha256": e,
                "manifest_len": len(man),
                "digest_only": entry is None,
                "manifest_status": None if entry is None else entry.status,
            }
        )
    coherent = bool(digests) and all(d and d == digests[0] for d in digests)
    return {"revisions": rows, "digest_coherent": coherent, "E_historical": digests[0] if coherent else None}


def _ledger_path(root: Path) -> Path:
    return world_paths.contribution_path(root, WORLD_ID, CONTRIBUTION_ID)


def _index_path(root: Path) -> Path:
    return world_paths.contribution_index_path(root, WORLD_ID)


def _fingerprint_non_d_ledgers(root: Path) -> dict[str, str]:
    contrib_dir = world_paths.world_dir(root, WORLD_ID) / "contributions"
    out: dict[str, str] = {}
    if not contrib_dir.is_dir():
        return out
    for path in sorted(contrib_dir.glob("contribution__*.json")):
        if path.name == "contribution__d3d244474789879c.json":
            continue
        out[path.name] = _sha256_file(path)
    return out


def _revision_tree_digest(root: Path) -> str:
    rev_root = world_paths.world_dir(root, WORLD_ID) / "revisions"
    h = hashlib.sha256()
    if rev_root.is_dir():
        for path in sorted(rev_root.rglob("*")):
            if path.is_file():
                rel = path.relative_to(rev_root).as_posix()
                h.update(rel.encode())
                h.update(path.read_bytes())
    return h.hexdigest()


def status(*, root: Path | None = None) -> dict[str, Any]:
    resolved = _resolve_root(root)
    head = open_world_graph_head(resolved, WORLD_ID)
    store = load_world_graph_revision(resolved, WORLD_ID, head.head_revision_id)
    E_map = (store.contribution_source_payload_sha256 or {}).get(CONTRIBUTION_ID)
    L_head = _manifest_lifecycle(store, CONTRIBUTION_ID)
    E_manifest = _bound_digest(store, CONTRIBUTION_ID)
    historical = _historical_digest_report(resolved)

    ledger_path = _ledger_path(resolved)
    ledger_raw = _sha256_file(ledger_path) if ledger_path.is_file() else None
    A_now = None
    ledger_status = None
    if ledger_path.is_file():
        ledger = load_contribution_record(resolved, WORLD_ID, CONTRIBUTION_ID)
        A_now = compute_contribution_source_payload_sha256(ledger)
        ledger_status = ledger.status

    index = load_contribution_index(resolved, WORLD_ID)
    index_bucket = None
    if CONTRIBUTION_ID in index.active_contribution_ids:
        index_bucket = "active"
    elif CONTRIBUTION_ID in index.failed_contribution_ids:
        index_bucket = "failed"
    elif CONTRIBUTION_ID in index.superseded_contribution_ids:
        index_bucket = "superseded"
    elif CONTRIBUTION_ID in index.retracted_contribution_ids:
        index_bucket = "retracted"

    dstar_info: dict[str, Any] | None = None
    dstar_digest = None
    try:
        dstar, dstar_digest, dstar_raw = _load_dstar()
        dstar_info = {
            "raw_sha256": dstar_raw,
            "source_payload_sha256": dstar_digest,
            "produced_at": dstar.produced_at,
            "path": str(RECOVERY_ARTIFACT_REL),
        }
    except HealError as exc:
        dstar_info = {"error": exc.code, "message": str(exc)}

    state: HealStatusName = "ineligible"
    reasons: list[str] = []

    if not E_map or E_map != E_manifest:
        state = "integrity_failure"
        reasons.append("current_head_digest_map_manifest_disagree")
    elif not historical["digest_coherent"] or historical["E_historical"] != E_map:
        state = "integrity_failure"
        reasons.append("historical_digest_disagreement")
    elif L_head is None:
        state = "integrity_failure"
        reasons.append("current_head_missing_manifest_lifecycle")
    elif dstar_digest is None:
        state = "ineligible"
        reasons.append("dstar_unavailable")
    elif dstar_digest != E_map:
        state = "integrity_failure"
        reasons.append("dstar_digest_mismatch")
    elif A_now == E_map and index_bucket == L_head:
        state = "already_healed"
    elif A_now != E_map or index_bucket != L_head:
        # partial or corrupt
        if A_now == E_map and index_bucket != L_head:
            state = "eligible"  # converge partial
            reasons.append("partial_state:ledger_healed_index_stale")
        elif A_now != E_map and index_bucket == L_head:
            state = "eligible"
            reasons.append("partial_state:index_ok_ledger_corrupt")
        else:
            state = "eligible"
            reasons.append("corrupt_ledger_or_index")
    else:
        state = "ineligible"
        reasons.append("unrecognized_state")

    return {
        "world_id": WORLD_ID,
        "contribution_id": CONTRIBUTION_ID,
        "root": str(resolved),
        "canonical_live_root": _is_canonical_live_root(resolved),
        "head_revision_id": head.head_revision_id,
        "E": E_map,
        "E_manifest": E_manifest,
        "L_head": L_head,
        "historical": historical,
        "A_now": A_now,
        "ledger_raw_sha256": ledger_raw,
        "ledger_status": ledger_status,
        "index_bucket": index_bucket,
        "index_baseline_revision_id": index.baseline_revision_id,
        "D_star": dstar_info,
        "state": state,
        "reasons": reasons,
        "revision_tree_digest": _revision_tree_digest(resolved),
    }


def apply(
    *,
    expected_head_revision_id: str,
    root: Path | None = None,
    allow_live_world: bool = False,
) -> dict[str, Any]:
    resolved = _resolve_root(root)
    if _is_canonical_live_root(resolved) and not allow_live_world:
        raise HealError(
            "live_world_opt_in_required",
            "canonical live world root requires --allow-live-world",
        )

    pre = status(root=resolved)
    if pre["state"] == "already_healed":
        return {**pre, "applied": False, "result": "already_healed"}
    if pre["state"] != "eligible":
        raise HealError(pre["state"], f"heal not eligible: {pre['reasons']}")

    dstar, dstar_digest, _dstar_raw = _load_dstar()
    E = pre["E"]
    L_head = pre["L_head"]
    assert dstar_digest == E
    assert L_head in {"active", "superseded", "retracted"}

    ledger_path = _ledger_path(resolved)
    index_path = _index_path(resolved)
    pre_ledger = ledger_path.read_bytes() if ledger_path.is_file() else None
    pre_index = index_path.read_bytes() if index_path.is_file() else None
    pre_other = _fingerprint_non_d_ledgers(resolved)
    pre_tree = pre["revision_tree_digest"]
    pre_baseline = pre["index_baseline_revision_id"]
    pre_all_ids = list(load_contribution_index(resolved, WORLD_ID).all_contribution_ids)

    try:
        with _exclusive_contribution_index_lock(resolved, WORLD_ID):
            head = open_world_graph_head(resolved, WORLD_ID)
            if head.head_revision_id != expected_head_revision_id:
                raise HealError(
                    "stale_head",
                    f"stale head: expected {expected_head_revision_id!r}, "
                    f"head is {head.head_revision_id!r}",
                )
            store = load_world_graph_revision(
                resolved, WORLD_ID, head.head_revision_id
            )
            E_now = (store.contribution_source_payload_sha256 or {}).get(CONTRIBUTION_ID)
            L_now = _manifest_lifecycle(store, CONTRIBUTION_ID)
            if E_now != E or L_now != L_head:
                raise HealError(
                    "integrity_failure",
                    "head digest/lifecycle changed under lock",
                )

            healed = dstar.model_copy(update={"status": L_now})
            write_contribution_record(resolved, WORLD_ID, healed)
            index = load_contribution_index(resolved, WORLD_ID)
            index = upsert_contribution_in_index(index, healed)
            # preserve ordering: all_contribution_ids must remain equal
            if list(index.all_contribution_ids) != pre_all_ids:
                # upsert may append if missing; restore exact order
                if set(index.all_contribution_ids) == set(pre_all_ids):
                    index = index.model_copy(
                        update={"all_contribution_ids": list(pre_all_ids)}
                    )
                else:
                    raise HealError(
                        "integrity_failure",
                        "contribution index membership changed unexpectedly",
                    )
            if index.baseline_revision_id != pre_baseline:
                raise HealError(
                    "integrity_failure",
                    "baseline_revision_id changed unexpectedly",
                )
            save_contribution_index(resolved, WORLD_ID, index)
    except Exception:
        # best-effort restore on failure after capture
        if pre_ledger is not None:
            ledger_path.write_bytes(pre_ledger)
        if pre_index is not None:
            index_path.write_bytes(pre_index)
        raise

    post = status(root=resolved)
    if post["head_revision_id"] != expected_head_revision_id:
        raise HealError("integrity_failure", "head moved during heal")
    if post["revision_tree_digest"] != pre_tree:
        raise HealError("integrity_failure", "revision tree changed during heal")
    if post["A_now"] != E or post["index_bucket"] != L_head:
        raise HealError("integrity_failure", "post-heal digest/lifecycle mismatch")
    if _fingerprint_non_d_ledgers(resolved) != pre_other:
        raise HealError("integrity_failure", "non-D contribution records changed")

    pinned = rebuild_from_contributions(
        resolved,
        world_id=WORLD_ID,
        compare_revision_id=expected_head_revision_id,
        publish=False,
    )
    unpinned = rebuild_from_contributions(
        resolved,
        world_id=WORLD_ID,
        publish=False,
    )
    pinned_diag = list(getattr(pinned, "diagnostics", []) or [])
    unpinned_diag = list(getattr(unpinned, "diagnostics", []) or [])
    if "rebuild_equivalent_to_pinned_revision" not in pinned_diag:
        raise HealError(
            "pinned_rebuild_failed",
            f"pinned rebuild not equivalent: {pinned_diag}",
        )
    if "rebuild_equivalent_to_head" not in unpinned_diag and (
        "rebuild_equivalent_to_published_head" not in unpinned_diag
    ):
        raise HealError(
            "unpinned_rebuild_failed",
            f"unpinned rebuild not equivalent: {unpinned_diag}",
        )

    return {
        **post,
        "applied": True,
        "result": "healed",
        "pinned_rebuild_diagnostics": pinned_diag,
        "unpinned_rebuild_diagnostics": unpinned_diag,
        "expected_head_revision_id": expected_head_revision_id,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    st = sub.add_parser("status")
    st.add_argument("--root", type=Path)

    ap = sub.add_parser("apply")
    ap.add_argument("--root", type=Path)
    ap.add_argument("--expected-head-revision-id", required=True)
    ap.add_argument("--allow-live-world", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            print(json.dumps(status(root=args.root), indent=2, sort_keys=True))
            return 0
        print(
            json.dumps(
                apply(
                    expected_head_revision_id=args.expected_head_revision_id,
                    root=args.root,
                    allow_live_world=args.allow_live_world,
                ),
                indent=2,
                sort_keys=True,
            )
        )
        return 0
    except HealError as exc:
        print(
            json.dumps(
                {"code": exc.code, "message": str(exc)},
                indent=2,
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
