#!/usr/bin/env python3
"""Replay sealed full-corpus candidates through the governed World write path.

No extraction client is imported or constructed.  Each invocation publishes one
arm into one explicitly named isolated DungeonMind World, in C1→C2 order.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]
OUT = ROOT / "out" / "full_corpus_world_graph_ingestion"
ARMS = ("openai-gpt-5.4-mini", "deepseek-v4.1-flash")
PREPARED_BY = "full-corpus-governed-publication"


class PublicationError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def jobs() -> list[tuple[str, int]]:
    return [("longmont-c1", n) for n in range(1, 18)] + [("longmont-c2", n) for n in range(1, 26)]


def candidate_path(arm: str, campaign: str, session: int) -> Path:
    return OUT / arm / "runs" / campaign / f"session-{session:02d}" / "candidate_graph.json"


def source_path(arm: str, campaign: str, session: int) -> Path:
    ingest = json.loads((OUT / arm / "INGEST.json").read_text(encoding="utf-8"))
    match = next((row for row in ingest.get("receipts") or [] if row.get("campaign_id") == campaign and int(row.get("session_number") or 0) == session), None)
    rel = str((match or {}).get("relpath") or "")
    path = (ROOT / "corpus" / "eldyrwild-markdown" / rel).resolve()
    if not str(path).startswith(str(ROOT)) or not path.is_file():
        raise PublicationError(f"candidate source is not an admitted repository file: {rel!r}")
    return path


def verify_seal(arm: str) -> dict[str, Any]:
    if arm not in ARMS:
        raise PublicationError(f"unknown arm {arm!r}")
    rows: list[dict[str, Any]] = []
    for campaign, session in jobs():
        path = candidate_path(arm, campaign, session)
        if not path.is_file():
            raise PublicationError(f"missing sealed candidate {path.relative_to(ROOT)}")
        try:
            candidate = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise PublicationError(f"unreadable candidate {path.relative_to(ROOT)}") from exc
        if not isinstance(candidate, dict) or not isinstance(candidate.get("nodes"), list):
            raise PublicationError(f"invalid candidate graph {path.relative_to(ROOT)}")
        source = source_path(arm, campaign, session)
        span_index = json.loads(path.with_name("source_span_index.json").read_text(encoding="utf-8"))
        expected = str(span_index.get("content_sha256") or "").removeprefix("sha256:")
        actual = _digest(source)
        if expected and expected != actual:
            raise PublicationError(f"source hash drift for {campaign}/session-{session:02d}")
        rows.append({"campaign": campaign, "session": session, "candidate_sha256": _digest(path), "source_sha256": actual, "source_artifact_id": str((candidate.get("source_artifact_ids") or [""])[0]), "candidate_path": path.relative_to(ROOT).as_posix(), "source_path": source.relative_to(ROOT).as_posix()})
    return {"schema": "dmb_full_corpus_candidate_seal_v1", "arm": arm, "candidate_count": len(rows), "model_calls": 0, "sessions": rows}


def assert_isolated_dsn(dsn: str) -> None:
    parsed = urlparse(dsn.strip())
    database = unquote(parsed.path or "").lstrip("/").split("/")[0].lower()
    if parsed.scheme not in {"postgres", "postgresql"} or not database:
        raise PublicationError("an isolated PostgreSQL DungeonMind DSN is required")
    if "live" in database or "eldyrwild" in database or "full_corpus" not in database:
        raise PublicationError("authority database name must be isolated and include full_corpus")


def _endpoint_kinds(context: Any, candidate: Mapping[str, Any]) -> dict[str, str]:
    kinds = {oid: obj.kind for oid, obj in context.objects.items() if obj.kind}
    for node in candidate.get("nodes") or []:
        node_id = str(node.get("id") or node.get("node_id") or "")
        kind = str(node.get("type") or node.get("node_type") or node.get("kind") or "")
        if (node.get("corpus_ref") or {}).get("type") == "pc" or kind == "pc":
            kind = "player_character"
        elif kind == "character":
            kind = "npc"
        if node_id and kind:
            kinds[node_id] = kind
    return kinds


def publish_session(*, dsn: str, world_id: str, seal: Mapping[str, Any], expected_parent: str) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import check_edge_expressible
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import DungeonMindWorldGraphSourceAdmissionAdapter
    from apps.live_control_server.ports.world_graph_source_admission import WorldGraphSourceAdmissionRequest
    from apps.live_control_server.services.source_artifact_registry import create_recap_source_artifact
    from graph_memory.extract_promote_ops import prepare_extract_promote

    candidate_file = ROOT / str(seal["candidate_path"])
    candidate = json.loads(candidate_file.read_text(encoding="utf-8"))
    context = world_graph_writes.load_production_mutation_context(world_id, database_url=dsn)
    if context.revision_id != expected_parent or context.head_revision_id != expected_parent:
        raise PublicationError("chronology drift: current authority head does not equal receipt parent")
    artifact_ids = list(candidate.get("source_artifact_ids") or [])
    if len(artifact_ids) != 1:
        raise PublicationError("candidate must have exactly one source artifact")
    if str(artifact_ids[0]) != str(seal["source_artifact_id"]):
        raise PublicationError("candidate artifact identity drift")
    artifact = create_recap_source_artifact(ROOT, campaign_id=str(seal["campaign"]), session_id=f"session-{int(seal['session'])}", recap_path=ROOT / str(seal["source_path"]), expected_content_sha256=str(seal["source_sha256"]), source_artifact_id=str(seal["source_artifact_id"]))
    admitted = DungeonMindWorldGraphSourceAdmissionAdapter(database_url=dsn).prove_or_admit(WorldGraphSourceAdmissionRequest(world_id=world_id, campaign_id=str(seal["campaign"]), source_artifact=artifact, source_revision_token=f"sha256:{seal['source_sha256']}", source_uri=artifact.uri))
    prepared = prepare_extract_promote(candidate_graph=candidate, source_uri=f"repo://{seal['source_path']}", source_revision_id=f"sha256:{seal['source_sha256']}", prepared_by=PREPARED_BY, world_id=world_id, campaign_scope=str(seal["campaign"]), candidate_graph_path=str(seal["candidate_path"]), repo_root=ROOT, mutation_context=context)
    package = world_graph_writes.bind_identity_ledger_to_package(prepared.review_package, context)
    assertions = {item["assertion_id"]: item for part in package.get("effect", {}).get("contribution_slices", []) for item in part.get("accepted_proposals", [])}
    selectable: list[str] = []
    rejected: dict[str, int] = {}
    published_edges = 0
    kinds = _endpoint_kinds(context, candidate)
    for item in prepared.review_items:
        if not item.get("selectable"):
            continue
        sid = str(item.get("slice_qualified_id") or "")
        if str(item.get("kind") or "").lower() not in {"edge", "relationship"}:
            selectable.append(sid); continue
        assertion = assertions.get(item.get("assertion_id"))
        ok, reason = check_edge_expressible(str((assertion or {}).get("predicate") or ""), kinds.get(str((assertion or {}).get("subject_node_id") or "")), kinds.get(str((assertion or {}).get("target_node_id") or "")))
        if ok:
            selectable.append(sid); published_edges += 1
        else:
            rejected[str(reason)] = rejected.get(str(reason), 0) + 1
    if not selectable:
        raise PublicationError("governed preparation produced no publishable assertions")
    request = type("ConfirmRequest", (), {"review_package": package, "assertion_ids": selectable})()
    confirmed = world_graph_writes.confirm_extract_promote_via_dungeonmind(request, database_url=dsn, confirming_principal=PREPARED_BY, assertion_ids=tuple(selectable), repo_root=ROOT)
    child = str(confirmed.get("committed_revision_id") or "")
    if not child:
        raise PublicationError("governed confirmation returned no child revision")
    return {"parent_world_revision": expected_parent, "child_world_revision": child, "source_admission": asdict(admitted), "candidate_nodes": len(candidate.get("nodes") or []), "candidate_relationships": len(candidate.get("edges") or []), "published_relationships": published_edges, "relationship_rejections": rejected, "model_calls": 0, "publication_mode": "governed_extract_promote"}


def run_arm(*, arm: str, dsn: str, world_id: str, output: Path) -> dict[str, Any]:
    seal = verify_seal(arm)
    _write(output / "SEAL.json", seal)
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    context = world_graph_writes.load_production_mutation_context(world_id, database_url=dsn)
    parent = context.head_revision_id
    receipts = []
    for row in seal["sessions"]:
        start = time.perf_counter()
        receipt = {**row, **publish_session(dsn=dsn, world_id=world_id, seal=row, expected_parent=parent), "arm": arm, "world_id": world_id, "wall_seconds": round(time.perf_counter() - start, 3), "errors": []}
        parent = receipt["child_world_revision"]
        receipts.append(receipt)
        _write(output / "receipts" / f"{row['campaign']}-session-{int(row['session']):02d}.json", receipt)
    manifest = {"schema": "dmb_full_corpus_governed_publication_v1", "generated_at": _now(), "arm": arm, "world_id": world_id, "model_calls": 0, "baseline_revision": context.head_revision_id, "terminal_revision": parent, "receipt_count": len(receipts), "receipts": receipts}
    _write(output / "MANIFEST.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", choices=ARMS, required=True)
    parser.add_argument("--verify-seal", action="store_true")
    parser.add_argument("--dsn", default=os.environ.get("DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"))
    parser.add_argument("--world-id")
    args = parser.parse_args()
    if args.verify_seal:
        print(json.dumps(verify_seal(args.arm), indent=2)); return 0
    if not args.dsn or not args.world_id:
        raise SystemExit("--dsn and --world-id are required for governed publication")
    assert_isolated_dsn(args.dsn)
    result = run_arm(arm=args.arm, dsn=args.dsn, world_id=args.world_id, output=OUT / "publication" / args.arm)
    print(json.dumps(result, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
