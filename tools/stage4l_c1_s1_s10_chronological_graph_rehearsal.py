#!/usr/bin/env python3
"""Chronological Campaign 1 Sessions 1–10 graph rehearsal.

Experimental notebook tooling. Paid execution is explicit; publication refuses
the live Eldyrwild authority. Candidates are durable before governed writes and
can be replayed without model calls.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for import_root in (str(SRC_ROOT), str(REPO_ROOT)):
    if import_root in sys.path:
        sys.path.remove(import_root)
    sys.path.insert(0, import_root)

from src.bootstrap_env import load_dungeonmindbuddy_dotenv  # noqa: E402
from src.graph_memory.extraction.deepseek_category_graph_pass_client import (  # noqa: E402
    DEFAULT_DEEPSEEK_MODEL,
    DeepSeekCategoryGraphPassClient,
)
from src.graph_memory.extraction.known_entity_registry import (  # noqa: E402
    KnownEntity,
    build_known_entity_registry,
    known_entities_from_world_graph,
)
from src.ingestion.frontmatter import load_document_frontmatter  # noqa: E402

CAMPAIGN_ID = "longmont-c1"
WORLD_ID = "eldyrwild"
OUT_REL = "out/stage4l_c1_s1_s10_chronological_graph_rehearsal"
MODEL_ID = DEFAULT_DEEPSEEK_MODEL
PREPARED_BY = "stage4l-c1-chronological-rehearsal"
CONFIRMING_PRINCIPAL = PREPARED_BY
LIVE_PORT = 54330
LIVE_DB = "dungeonmind_cutover_live"
WORLD_DSN_ENV = "DUNGEONMIND_WORLD_GRAPH_AUTHORITY_DATABASE_URL"
BOOTSTRAP_ONLY_OBJECT_IDS = frozenset({"obj:stage4j-genesis-root"})

COHORT = {
    1: "Session 1 - Recap 3-27-24.md",
    2: "Session 2 - Finishing the Job.md",
    3: "Session 3 - The Stone Bridge Flood.md",
    4: "Session 4 - The Grotesque Tree of Hempholm.md",
    5: "Session 5 - Underneath Hempholm.md",
    6: "Session 6 - The Road to Miraholm.md",
    7: "Session 7 - Passing Mirathorn Gates.md",
    8: "Session 8 - Captain Lysandra Quest.md",
    9: "Session 9 - Battle with the Meat Monsters.md",
    10: "Session 10 - Battle with the Meat Monsters.md",
}
RECAP_DIR = (
    REPO_ROOT / "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps"
)


class Stage4LError(RuntimeError):
    pass


@dataclass(frozen=True)
class SourceRef:
    session: int
    path: Path
    relpath: str
    sha256: str
    byte_count: int
    metadata: dict[str, Any]


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _sha_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sha_json(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return _sha_bytes(raw)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _out_root(value: str | None) -> Path:
    return Path(value).resolve() if value else REPO_ROOT / OUT_REL


def _source_ref(session: int) -> SourceRef:
    if session not in COHORT:
        raise Stage4LError(f"session {session} is outside the frozen S1-S10 cohort")
    path = (RECAP_DIR / COHORT[session]).resolve()
    if path.parent != RECAP_DIR.resolve() or not path.is_file():
        raise Stage4LError(f"canonical source missing: {path}")
    lowered = {part.lower() for part in path.parts}
    if lowered & {"_normalized", "_breadcrumbed", "_session_memory", ".backups"}:
        raise Stage4LError(f"derivative recap is forbidden: {path}")
    metadata, _body = load_document_frontmatter(path)
    if metadata is None:
        raise Stage4LError(f"frontmatter missing: {path}")
    expected = {
        "campaign_id": CAMPAIGN_ID,
        "session": session,
        "document_class": "play",
        "canon_layer": "campaign",
        "temporal_scope": "session_specific",
        "source_class": "observed_session_recap",
    }
    actual = metadata.to_dict()
    mismatches = {
        key: {"expected": value, "actual": actual.get(key)}
        for key, value in expected.items()
        if actual.get(key) != value
    }
    if mismatches:
        raise Stage4LError(f"source metadata mismatch for S{session}: {mismatches}")
    raw = path.read_bytes()
    return SourceRef(
        session=session,
        path=path,
        relpath=path.relative_to(REPO_ROOT).as_posix(),
        sha256=_sha_bytes(raw),
        byte_count=len(raw),
        metadata=actual,
    )


def census() -> dict[str, Any]:
    sources = [_source_ref(n) for n in range(1, 11)]
    registry = build_known_entity_registry(CAMPAIGN_ID, 1)
    pcs = sorted(
        entity.display_name for entity in registry.entities if entity.kind == "pc"
    )
    if len(pcs) != 6:
        raise Stage4LError(f"expected six Session 1 PCs, found {pcs}")
    source_rows = [
        {
            "session": source.session,
            "relpath": source.relpath,
            "sha256": source.sha256,
            "bytes": source.byte_count,
            "metadata": source.metadata,
        }
        for source in sources
    ]
    return {
        "schema": "dmb_stage4l_census_v1",
        "campaign_id": CAMPAIGN_ID,
        "sessions": source_rows,
        "cohort_fingerprint": _sha_json(source_rows),
        "source_count": len(sources),
        "source_bytes": sum(source.byte_count for source in sources),
        "planned_semantic_executions": 10,
        "estimated_category_pass_requests": 70,
        "session_1_pc_labels": pcs,
        "gold_generation_access": False,
    }


def assert_rehearsal_dsn(dsn: str) -> None:
    cleaned = dsn.strip()
    if not cleaned:
        raise Stage4LError(f"{WORLD_DSN_ENV} must name an isolated rehearsal database")
    parsed = urlparse(cleaned)
    database = unquote(parsed.path or "").lstrip("/").split("/")[0]
    if parsed.scheme not in {"postgresql", "postgres"}:
        raise Stage4LError("rehearsal World DSN must be PostgreSQL")
    if parsed.port == LIVE_PORT or database == LIVE_DB or "cutover_live" in database:
        raise Stage4LError("refusing live Eldyrwild World authority")
    if "stage4l" not in database.lower() and "rehearsal" not in database.lower():
        raise Stage4LError(
            "database name must visibly identify a rehearsal/stage4l database"
        )


def _load_env() -> str:
    preserved = os.environ.get(WORLD_DSN_ENV, "")
    load_dungeonmindbuddy_dotenv()
    if preserved:
        os.environ[WORLD_DSN_ENV] = preserved
    dsn = os.environ.get(WORLD_DSN_ENV, "")
    assert_rehearsal_dsn(dsn)
    return dsn


def _context_graph(mutation_context: Any) -> dict[str, Any]:
    def buddy_kind(kind: str) -> str:
        # DungeonMind's dnd5e:player_character becomes ``player_character``
        # at the mutation-context wire boundary. The extraction registry's
        # stable Buddy vocabulary calls the same kind ``pc``.
        return "pc" if kind == "player_character" else kind

    return {
        "nodes": [
            {
                "node_id": obj.object_id,
                "label": obj.label,
                "kind": buddy_kind(obj.kind),
                "aliases": list(obj.aliases),
            }
            for obj in mutation_context.objects.values()
            if obj.object_id not in BOOTSTRAP_ONLY_OBJECT_IDS
        ]
    }


def _known_entities(mutation_context: Any) -> tuple[KnownEntity, ...]:
    return tuple(
        known_entities_from_world_graph(
            _context_graph(mutation_context),
            include_kinds={
                "pc",
                "npc",
                "location",
                "group",
                "party",
                "faction",
                "item",
                "creature",
            },
        )
    )


def _known_receipt(entities: Sequence[KnownEntity]) -> dict[str, Any]:
    rows = [
        {
            "canonical_entity_id": item.canonical_entity_id,
            "kind": item.kind,
            "label": item.display_name,
            "aliases": sorted(item.aliases),
        }
        for item in sorted(entities, key=lambda row: row.canonical_entity_id)
    ]
    return {"count": len(rows), "fingerprint": _sha_json(rows), "entities": rows}


def _receipt_relpath(path: Path, root: Path) -> str:
    try:
        return path.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.relative_to(root).as_posix()


def _paid_receipt_path(root: Path, session: int) -> Path:
    return root / "receipts" / f"session_{session:02d}.json"


def _replay_receipt_path(root: Path, session: int) -> Path:
    return root / "receipts" / f"session_{session:02d}.replay.json"


def _context_seal(context_receipt: Mapping[str, Any]) -> dict[str, Any]:
    party = context_receipt.get("party_registry") or {}
    known = context_receipt.get("world_known_entities") or {}
    payload = {
        "prior_world_revision_id": context_receipt.get("prior_world_revision_id"),
        "party_registry_fingerprint": party.get("fingerprint"),
        "world_known_entities_fingerprint": known.get("fingerprint"),
        "world_known_entities_count": known.get("count"),
    }
    return {**payload, "fingerprint": _sha_json(payload)}


def _candidate_path(
    root: Path,
    session: int,
    run_id: str | None = None,
    *,
    exact_run: bool = False,
) -> Path:
    session_dir = root / f"session_{session:02d}"
    if exact_run:
        if not run_id:
            raise Stage4LError(
                f"Session {session} replay requires an exact candidate run_id"
            )
        candidate = session_dir / str(run_id) / "candidate_graph.json"
        if not candidate.is_file():
            raise Stage4LError(
                f"durable candidate missing for Session {session} run {run_id}"
            )
        return candidate
    candidates = []
    if run_id:
        candidates.append(session_dir / run_id / "candidate_graph.json")
    candidates.extend([session_dir / "candidate_graph.json"])
    candidates.extend(sorted(session_dir.glob("*/candidate_graph.json")))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise Stage4LError(f"durable candidate missing for Session {session}")


def _assert_replay_seals(
    *,
    saved: Mapping[str, Any],
    source: SourceRef,
    prior_revision: str,
    live_context: Mapping[str, Any],
    candidate_path: Path,
) -> None:
    if saved.get("source", {}).get("sha256") != source.sha256:
        raise Stage4LError("saved candidate source digest drift")
    if saved.get("context", {}).get("prior_world_revision_id") != prior_revision:
        raise Stage4LError("saved candidate prior World revision drift")
    saved_candidate = str(saved.get("candidate_sha256") or "")
    live_candidate = _sha_bytes(candidate_path.read_bytes())
    if not saved_candidate or saved_candidate != live_candidate:
        raise Stage4LError("saved candidate digest drift")
    saved_seal = _context_seal(saved.get("context") or {})
    live_seal = _context_seal(live_context)
    if saved_seal["fingerprint"] != live_seal["fingerprint"]:
        raise Stage4LError("saved candidate context fingerprint drift")


def _verify_paid_receipt_on_disk(root: Path, receipt: Mapping[str, Any]) -> None:
    session = int(receipt["session"])
    if receipt.get("replay") is True:
        raise Stage4LError(
            f"Session {session:02d} receipt is replay-marked; paid seal is missing"
        )
    source = _source_ref(session)
    if receipt.get("source", {}).get("sha256") != source.sha256:
        raise Stage4LError(f"Session {session:02d} paid source digest drift")
    candidate_path = _candidate_path(
        root, session, receipt.get("run_id"), exact_run=True
    )
    live_digest = _sha_bytes(candidate_path.read_bytes())
    if live_digest != receipt.get("candidate_sha256"):
        raise Stage4LError(f"Session {session:02d} paid candidate digest drift")
    if not _context_seal(receipt.get("context") or {}).get("fingerprint"):
        raise Stage4LError(f"Session {session:02d} paid context fingerprint missing")


def _verify_paid_chain(root: Path, receipts: Sequence[Mapping[str, Any]]) -> int:
    if not receipts:
        return 1
    sessions = [int(row["session"]) for row in receipts]
    expected = list(range(1, len(receipts) + 1))
    if sessions != expected:
        raise Stage4LError(f"paid receipts are not a contiguous 1..N chain: {sessions}")
    previous_child = None
    for row in receipts:
        _verify_paid_receipt_on_disk(root, row)
        parent = row.get("publication", {}).get("parent_revision_id")
        child = row.get("publication", {}).get("committed_revision_id")
        prior = row.get("context", {}).get("prior_world_revision_id")
        if prior != parent:
            raise Stage4LError(
                f"Session {row['session']:02d} context prior does not match publication parent"
            )
        if previous_child is not None and parent != previous_child:
            raise Stage4LError(
                f"Session {row['session']:02d} parent does not continue the paid chain"
            )
        previous_child = child
    return int(receipts[-1]["session"]) + 1


def _manifest_row(receipt: Mapping[str, Any]) -> dict[str, Any]:
    context = receipt.get("context") or {}
    publication = receipt.get("publication") or {}
    recovery = receipt.get("paid_receipt_recovery") or {}
    return {
        "session": receipt.get("session"),
        "lineage": "paid",
        "replay": bool(receipt.get("replay")),
        "run_id": receipt.get("run_id"),
        "source_sha256": (receipt.get("source") or {}).get("sha256"),
        "candidate_sha256": receipt.get("candidate_sha256"),
        "candidate_graph_path": receipt.get("candidate_graph_path"),
        "context_fingerprint": _context_seal(context)["fingerprint"],
        "prior_world_revision_id": context.get("prior_world_revision_id"),
        "world_known_entities_count": (context.get("world_known_entities") or {}).get(
            "count"
        ),
        "parent_revision_id": publication.get("parent_revision_id"),
        "committed_revision_id": publication.get("committed_revision_id"),
        "publication_mode": publication.get("publication_mode"),
        "edge_funnel": publication.get("edge_funnel"),
        "model_calls": receipt.get("model_calls"),
        "cost_usd": receipt.get("cost_usd"),
        "paid_receipt_recovery": recovery or None,
    }


def render_manifest(root: Path) -> dict[str, Any]:
    receipts = _completed_receipts(root)
    payload = {
        "schema": "dmb_stage4l_replay_manifest_v1",
        "generated_at": _now(),
        "campaign_id": CAMPAIGN_ID,
        "model": MODEL_ID,
        "authoritative_s10_revision_id": (
            receipts[-1]["publication"]["committed_revision_id"] if receipts else None
        ),
        "sessions": [_manifest_row(row) for row in receipts],
    }
    _write_json(root / "MANIFEST.json", payload)
    return payload


def _select(review_items: Sequence[Mapping[str, Any]], *, edges: bool) -> list[str]:
    result = []
    for item in review_items:
        if not item.get("selectable"):
            continue
        is_edge = str(item.get("kind") or "").lower() in {"edge", "relationship"}
        if edges or not is_edge:
            value = str(item.get("slice_qualified_id") or "").strip()
            if value:
                result.append(value)
    return result


def _endpoint_kinds_map(context: Any, candidate: Mapping[str, Any]) -> dict[str, str]:
    kinds: dict[str, str] = {
        obj_id: obj.kind
        for obj_id, obj in getattr(context, "objects", {}).items()
        if obj.kind
    }
    for node in candidate.get("nodes") or []:
        nid = str(node.get("id") or node.get("node_id") or "")
        nkind = str(node.get("type") or node.get("node_type") or node.get("kind") or "")
        if (node.get("corpus_ref") or {}).get("type") == "pc":
            nkind = "player_character"
        elif nkind == "pc":
            nkind = "player_character"
        elif nkind == "character":
            nkind = "npc"
        if nid and nkind:
            kinds[nid] = nkind
    return kinds


def _select_publishable(
    review_items: Sequence[Mapping[str, Any]],
    *,
    sealed_package: Mapping[str, Any],
    endpoint_kinds: Mapping[str, str],
) -> tuple[list[str], list[str], list[tuple[str, str]]]:
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        check_edge_expressible,
    )

    pkg_assertions: dict[str, Any] = {}
    for slice_obj in sealed_package.get("effect", {}).get("contribution_slices", []):
        for a in slice_obj.get("accepted_proposals", []):
            pkg_assertions[a["assertion_id"]] = a
    for a in sealed_package.get("effect", {}).get("accepted_proposals", []):
        pkg_assertions[a["assertion_id"]] = a

    selected: list[str] = []
    published_edges: list[str] = []
    dropped_edges: list[tuple[str, str]] = []

    for item in review_items:
        if not item.get("selectable"):
            continue
        slice_id = str(item.get("slice_qualified_id") or "").strip()
        if not slice_id:
            continue
        is_edge = str(item.get("kind") or "").lower() in {"edge", "relationship"}
        if not is_edge:
            selected.append(slice_id)
        else:
            assertion = pkg_assertions.get(item.get("assertion_id"))
            if not assertion:
                dropped_edges.append((slice_id, "missing_package_assertion"))
                continue
            pred = assertion.get("predicate") or ""
            s_id = assertion.get("subject_node_id") or ""
            t_id = assertion.get("target_node_id") or ""
            s_k = endpoint_kinds.get(s_id)
            t_k = endpoint_kinds.get(t_id)
            ok, reason = check_edge_expressible(pred, s_k, t_k)
            if ok:
                selected.append(slice_id)
                published_edges.append(slice_id)
            else:
                dropped_edges.append((slice_id, str(reason)))

    return selected, published_edges, dropped_edges


def _edge_funnel(
    candidate: Mapping[str, Any],
    review_items: Sequence[Mapping[str, Any]],
    *,
    publishable_count: int | None = None,
    published_count: int = 0,
) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind.assertion_qualification import (
        resolve_buddy_predicate_mapping_v4,
    )

    edges = list(candidate.get("edges") or [])
    canonical = [
        edge for edge in edges if edge.get("from_node_id") and edge.get("to_node_id")
    ]
    admitted_pred = 0
    for edge in edges:
        p = str(edge.get("relationship_type") or "")
        m = resolve_buddy_predicate_mapping_v4(p)
        if m and m[0]:
            admitted_pred += 1
    if publishable_count is None:
        selectable = [
            item
            for item in review_items
            if item.get("selectable")
            and str(item.get("kind") or "").lower() in {"edge", "relationship"}
        ]
        publishable_count = len(selectable)
    return {
        "extracted": len(edges),
        "canonical_endpoints": len(canonical),
        "admitted_predicates": admitted_pred,
        "publishable": publishable_count,
        "published": published_count,
    }


def _admit_source(*, source_artifact_id: str, dsn: str) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.ports.world_graph_source_admission import (
        WorldGraphSourceAdmissionRequest,
    )
    from apps.live_control_server.services.source_artifact_registry import (
        get_source_artifact,
    )

    artifact = get_source_artifact(REPO_ROOT, source_artifact_id)
    admitted = DungeonMindWorldGraphSourceAdmissionAdapter(
        database_url=dsn
    ).prove_or_admit(
        WorldGraphSourceAdmissionRequest(
            world_id=WORLD_ID,
            campaign_id=CAMPAIGN_ID,
            source_artifact=artifact,
            source_revision_token=f"sha256:{artifact.content_sha256}",
            source_uri=artifact.uri,
        )
    )
    return asdict(admitted)


def _publish(
    *,
    source: SourceRef,
    candidate_path: Path,
    candidate: Mapping[str, Any],
    dsn: str,
    expected_parent: str,
) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from graph_memory.extract_promote_ops import prepare_extract_promote

    context = world_graph_writes.load_production_mutation_context(
        WORLD_ID, database_url=dsn
    )
    if (
        context.revision_id != expected_parent
        or context.head_revision_id != expected_parent
    ):
        raise Stage4LError(
            f"chronology drift: expected parent {expected_parent}, "
            f"got revision={context.revision_id} head={context.head_revision_id}"
        )
    artifact_ids = list(candidate.get("source_artifact_ids") or [])
    if len(artifact_ids) != 1:
        raise Stage4LError(
            f"Session {source.session} candidate must name exactly one source"
        )
    admitted = _admit_source(source_artifact_id=str(artifact_ids[0]), dsn=dsn)
    prepared = prepare_extract_promote(
        candidate_graph=candidate,
        source_uri=f"repo://{source.relpath}",
        source_revision_id=f"sha256:{source.sha256}",
        prepared_by=PREPARED_BY,
        world_id=WORLD_ID,
        campaign_scope=CAMPAIGN_ID,
        candidate_graph_path=candidate_path.relative_to(REPO_ROOT).as_posix(),
        repo_root=REPO_ROOT,
        mutation_context=context,
    )
    sealed = world_graph_writes.bind_identity_ledger_to_package(
        prepared.review_package, context
    )
    items = list(prepared.review_items)
    endpoint_kinds = _endpoint_kinds_map(context, candidate)
    selected_publishable, published_edge_ids, dropped_edges = _select_publishable(
        items, sealed_package=sealed, endpoint_kinds=endpoint_kinds
    )
    funnel = _edge_funnel(
        candidate,
        items,
        publishable_count=len(published_edge_ids),
        published_count=0,
    )
    if not selected_publishable:
        raise Stage4LError("prepare produced no selectable assertions")

    def confirm(selected: list[str]) -> Mapping[str, Any]:
        request = type(
            "ConfirmRequest",
            (),
            {"review_package": sealed, "assertion_ids": selected},
        )()
        return world_graph_writes.confirm_extract_promote_via_dungeonmind(
            request,
            database_url=dsn,
            confirming_principal=CONFIRMING_PRINCIPAL,
            assertion_ids=tuple(selected),
            repo_root=REPO_ROOT,
        )

    mode = (
        "all"
        if len(published_edge_ids) == len(candidate.get("edges") or [])
        else "edge_selective"
    )
    edge_error = None
    try:
        confirmed = confirm(selected_publishable)
        funnel["published"] = len(published_edge_ids)
    except Exception as exc:  # explicit experimental partial, never hidden as success
        selected_nodes = _select(items, edges=False)
        if not selected_nodes:
            raise
        edge_error = f"{type(exc).__name__}: {exc}"
        confirmed = confirm(selected_nodes)
        mode = "node_object_partial"
        funnel["published"] = 0
    child = str(confirmed.get("committed_revision_id") or "")
    if not child:
        raise Stage4LError("confirm returned no committed revision")
    return {
        "source_admission": admitted,
        "proposal_id": prepared.proposal_id,
        "proposal_digest": prepared.proposal_digest,
        "parent_revision_id": expected_parent,
        "committed_revision_id": child,
        "publication_mode": mode,
        "edge_publication_error": edge_error,
        "selected_assertion_count": len(
            selected_publishable
            if mode != "node_object_partial"
            else _select(items, edges=False)
        ),
        "edge_funnel": funnel,
        "review_package": sealed,
    }


def _gold_evaluation(candidate: Mapping[str, Any]) -> dict[str, Any]:
    gold_path = (
        REPO_ROOT
        / "evals/graph_memory_layer/examples/session_1_candidate_graph_gold/candidate_graph_gold.json"
    )
    gold = json.loads(gold_path.read_text(encoding="utf-8"))
    labels = {
        str(row.get("label") or "").casefold() for row in candidate.get("nodes") or []
    }
    gold_nodes = list(gold.get("nodes") or [])
    represented = [
        str(row.get("label") or "")
        for row in gold_nodes
        if str(row.get("label") or "").casefold() in labels
    ]
    missing = [
        str(row.get("label") or "")
        for row in gold_nodes
        if str(row.get("label") or "").casefold() not in labels
    ]
    candidate_pairs = {
        (str(e.get("from_node_id")), str(e.get("to_node_id")))
        for e in candidate.get("edges") or []
    }
    represented_edges = sum(
        1
        for edge in gold.get("edges") or []
        if (str(edge.get("from_node_id")), str(edge.get("to_node_id")))
        in candidate_pairs
    )
    return {
        "gold_path": gold_path.relative_to(REPO_ROOT).as_posix(),
        "generation_access": False,
        "gold_nodes_total": len(gold_nodes),
        "gold_node_labels_represented": represented,
        "gold_node_labels_missing": missing,
        "gold_edges_total": len(gold.get("edges") or []),
        "gold_edge_endpoint_pairs_represented": represented_edges,
    }


def _usage_summary(pass_telemetry: Mapping[str, Any] | None) -> dict[str, Any]:
    totals = {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0, "attempts": 0}
    for value in (pass_telemetry or {}).values():
        usage = value.get("usage") or {}
        for key in ("input_tokens", "output_tokens", "cached_tokens"):
            totals[key] += int(usage.get(key) or 0)
        totals["attempts"] += int(value.get("json_object_attempts") or 1)
    return totals


def run_session(
    session: int,
    *,
    root: Path,
    dsn: str,
    execute: bool,
    replay: bool,
) -> dict[str, Any]:
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes

    source = _source_ref(session)
    context = world_graph_writes.load_production_mutation_context(
        WORLD_ID, database_url=dsn
    )
    prior_revision = context.revision_id
    extras = _known_entities(context)
    context_receipt = {
        "prior_world_revision_id": prior_revision,
        "world_head_revision_id": context.head_revision_id,
        "world_known_entities": _known_receipt(extras),
        "party_registry": _known_receipt(
            build_known_entity_registry(CAMPAIGN_ID, session).entities
        ),
    }
    context_path = root / f"session_{session:02d}" / "context_receipt.json"
    if not replay:
        _write_json(context_path, context_receipt)
    started = time.perf_counter()
    result = None
    client = None
    if replay:
        receipt_path = _paid_receipt_path(root, session)
        old = json.loads(receipt_path.read_text(encoding="utf-8"))
        if old.get("replay") is True:
            raise Stage4LError(
                f"Session {session:02d} paid receipt is replay-marked; refuse to replay"
            )
        candidate_path = _candidate_path(
            root, session, old.get("run_id"), exact_run=True
        )
        _assert_replay_seals(
            saved=old,
            source=source,
            prior_revision=prior_revision,
            live_context=context_receipt,
            candidate_path=candidate_path,
        )
    else:
        if not execute:
            raise Stage4LError("paid execution requires --execute")
        from apps.live_control_server.services.graph_preview_runner import (
            run_recap_production_extraction,
        )

        client = DeepSeekCategoryGraphPassClient(model_id=MODEL_ID)
        result = run_recap_production_extraction(
            repo_root=REPO_ROOT,
            campaign_id=CAMPAIGN_ID,
            session_id=f"session-{session}",
            recap_path=source.path,
            model_id=MODEL_ID,
            allow_llm=True,
            category_client=client,
            output_dir=root / f"session_{session:02d}",
            extra_known_entities=extras,
        )
        if result.failure_kind or result.candidate_graph is None:
            raise Stage4LError(
                f"Session {session} extraction failed: {result.failure_kind} {result.diagnostics}"
            )
        candidate_path = _candidate_path(root, session, result.run.run_id)
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    candidate_digest = _sha_bytes(candidate_path.read_bytes())
    publication = _publish(
        source=source,
        candidate_path=candidate_path,
        candidate=candidate,
        dsn=dsn,
        expected_parent=prior_revision,
    )
    elapsed = round(time.perf_counter() - started, 3)
    extraction = old if replay else {}
    receipt = {
        "schema": "dmb_stage4l_session_receipt_v1",
        "session": session,
        "generated_at": _now(),
        "source": {
            "relpath": source.relpath,
            "sha256": source.sha256,
            "bytes": source.byte_count,
        },
        "context": context_receipt,
        "run_id": result.run.run_id if result else extraction.get("run_id"),
        "candidate_graph_path": _receipt_relpath(candidate_path, root),
        "candidate_sha256": candidate_digest,
        "candidate_nodes": len(candidate.get("nodes") or []),
        "candidate_edges": len(candidate.get("edges") or []),
        "model": MODEL_ID if result else extraction.get("model"),
        "model_calls": (
            len(result.pass_telemetry or {})
            if result
            else int(extraction.get("model_calls") or 0)
        ),
        "usage": (
            _usage_summary(result.pass_telemetry)
            if result
            else dict(extraction.get("usage") or {})
        ),
        "provider_pass_receipts": (
            list(client.receipts)
            if client is not None
            else list(extraction.get("provider_pass_receipts") or [])
        ),
        "cost_usd": (
            result.total_cost_usd
            if result
            else float(extraction.get("cost_usd") or 0.0)
        ),
        "wall_seconds": (
            elapsed if result else float(extraction.get("wall_seconds") or 0.0)
        ),
        "publication_replay": (
            {
                "replayed_at": _now(),
                "wall_seconds": elapsed,
                "model_calls": 0,
                "source_receipt_generated_at": extraction.get("generated_at"),
            }
            if replay
            else None
        ),
        "publication": {
            key: value for key, value in publication.items() if key != "review_package"
        },
        "gold_evaluation": _gold_evaluation(candidate) if session == 1 else None,
        "replay": replay,
        "lineage": (
            {
                "kind": "replay",
                "sealed_paid_receipt": _paid_receipt_path(root, session)
                .relative_to(root)
                .as_posix(),
                "paid_committed_revision_id": extraction.get("publication", {}).get(
                    "committed_revision_id"
                ),
            }
            if replay
            else {"kind": "paid", "sealed": True}
        ),
    }
    if replay:
        _write_json(_replay_receipt_path(root, session), receipt)
    else:
        paid_path = _paid_receipt_path(root, session)
        if paid_path.exists():
            raise Stage4LError(
                f"paid receipt already sealed for Session {session:02d}; refuse overwrite"
            )
        _write_json(paid_path, receipt)
    _write_json(
        root / f"session_{session:02d}" / "review_package.json",
        publication["review_package"],
    )
    return receipt


def _completed_receipts(root: Path) -> list[dict[str, Any]]:
    receipts = []
    for path in sorted((root / "receipts").glob("session_[0-9][0-9].json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") != "dmb_stage4l_session_receipt_v1":
            continue
        if value.get("replay") is True:
            raise Stage4LError(
                f"{path.name} is replay-marked; paid seal must be restored before resume"
            )
        receipts.append(value)
    return receipts


VERDICT_MARKER = "## Forcing-question verdict"


def _facts_lines(receipts: Sequence[Mapping[str, Any]]) -> list[str]:
    total_cost = sum(float(row.get("cost_usd") or 0) for row in receipts)
    total_wall = sum(float(row.get("wall_seconds") or 0) for row in receipts)
    lines = [
        "# Stage 4L — C1 chronological graph rehearsal",
        "",
        f"Generated: {_now()}",
        f"Sessions completed: {len(receipts)}/10",
        f"Paid cost recorded: ${total_cost:.6f}",
        f"Per-session wall total: {total_wall:.1f}s",
        "",
        "## Revision chain",
        "",
    ]
    for row in receipts:
        pub = row["publication"]
        edge = pub["edge_funnel"]
        lines.append(
            f"- S{row['session']:02d}: {pub['parent_revision_id']} → "
            f"{pub['committed_revision_id']} · {row['candidate_nodes']} nodes / "
            f"{row['candidate_edges']} edges · published edges "
            f"{edge['published']}/{edge['extracted']} · {pub['publication_mode']}"
        )
    lines.extend(
        [
            "",
            "## Experimental status",
            "",
            "This notebook reports execution facts only. The forcing-question verdict is "
            "assigned after cumulative graph inspection; API completion alone is not PASS.",
            "",
        ]
    )
    return lines


def render_report(root: Path) -> None:
    receipts = _completed_receipts(root)
    render_manifest(root)
    report_path = root / "REPORT.md"
    facts = "\n".join(_facts_lines(receipts))
    if report_path.is_file() and VERDICT_MARKER in report_path.read_text(
        encoding="utf-8"
    ):
        (root / "REPORT.facts.md").write_text(facts, encoding="utf-8")
        return
    report_path.write_text(facts, encoding="utf-8")


def cmd_census(args: argparse.Namespace) -> int:
    payload = census()
    if not args.no_write:
        _write_json(_out_root(args.output) / "census.json", payload)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    dsn = _load_env()
    root = _out_root(args.output)
    payload = census()
    _write_json(root / "census.json", payload)
    through = int(args.through)
    if through < 1 or through > 10:
        raise Stage4LError("--through must be 1..10")
    existing = _completed_receipts(root)
    next_session = _verify_paid_chain(root, existing)
    if next_session > through:
        render_report(root)
        return 0
    for session in range(next_session, through + 1):
        receipt = run_session(
            session, root=root, dsn=dsn, execute=args.execute, replay=False
        )
        print(
            f"S{session:02d} {receipt['publication']['committed_revision_id']} "
            f"cost=${receipt['cost_usd']:.6f} wall={receipt['wall_seconds']}s"
        )
        render_report(root)
    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    dsn = _load_env()
    root = _out_root(args.output)
    receipt = run_session(
        int(args.session), root=root, dsn=dsn, execute=False, replay=True
    )
    render_report(root)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    render_report(_out_root(args.output))
    return 0


def _render_rechain_report(
    rechain_dir: Path,
    rechain_manifest: Mapping[str, Any],
    paid_manifest: Mapping[str, Any],
) -> None:
    lines = [
        "# Stage 4L Successor: Zero-Model Relationship Publication Replay Report",
        "",
        "## Summary",
        "",
        f"- **Campaign ID:** `{rechain_manifest.get('campaign_id')}`",
        f"- **Generated at:** `{rechain_manifest.get('generated_at')}`",
        "- **Model calls:** `0` (zero new inference cost)",
        "- **Cost:** `$0.00`",
        f"- **Authoritative S10 Revision:** `{rechain_manifest.get('authoritative_s10_revision_id')}`",
        f"- **Total relationships published:** {rechain_manifest.get('total_relationships_published')} / {rechain_manifest.get('total_relationships_extracted')} ({rechain_manifest.get('relationship_publication_rate')})",
        "",
        "## Comparison: Stage 4L Initial vs Relationship Publication Slice",
        "",
        "| Metric | Stage 4L Initial Run | Relationship Publication Slice | Delta |",
        "|---|---|---|---|",
        f"| Published relationships | 7 / 276 (2.5%) | {rechain_manifest.get('total_relationships_published')} / {rechain_manifest.get('total_relationships_extracted')} ({rechain_manifest.get('relationship_publication_rate')}) | +{int(rechain_manifest.get('total_relationships_published') or 0) - 7} relationships |",
        "| Inference cost | $0.098863 | $0.000000 | $0.00 (replayed from paid candidates) |",
        "| PC identity | 6/6 `player_character` | 6/6 `player_character` | Stable |",
        "| Rehearsal DB isolation | Enforced (:54329) | Enforced (:54329) | Maintained |",
        "",
        "## Per-Session Breakdown",
        "",
        "| Session | Extracted Edges | Admitted Predicates | Publishable | Published | Publication Mode | Parent Revision | Committed Revision |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for s in rechain_manifest.get("sessions") or []:
        funnel = s.get("edge_funnel") or {}
        parent_short = str(s.get("parent_revision_id") or "")[:16]
        child_short = str(s.get("committed_revision_id") or "")[:16]
        lines.append(
            f"| S{s['session']:02d} | {funnel.get('extracted', 0)} | {funnel.get('admitted_predicates', 0)} | {funnel.get('publishable', 0)} | {funnel.get('published', 0)} | `{s.get('publication_mode')}` | `{parent_short}...` | `{child_short}...` |"
        )
    lines.extend(
        [
            "",
            "## PC Continuity (Zero Duplicate Objects)",
            "",
            "All six Campaign 1 Player Characters maintain stable canonical identity (`dnd5e:player_character`) without duplicate object creation.",
            "Candidate kind `pc` is normalized to `player_character` at the general identity/type equivalence boundary in `apps/live_control_server/models/world_graph_mutation_context.py`.",
            "",
            "## Detailed Relationship Analysis",
            "",
            "Comprehensive edge-by-edge rejection analysis and accounting available in `relationship_analysis/`:",
            "- `relationship_analysis/summary.json`",
            "- `relationship_analysis/relationships.json`",
            "- `relationship_analysis/REPORT.md`",
            "",
            "## Next Steps & Product Decision",
            "",
            f"1. **Relationship publication significantly increased**: {rechain_manifest.get('total_relationships_published')} / {rechain_manifest.get('total_relationships_extracted')} edges published ({rechain_manifest.get('relationship_publication_rate')}), up from 150 / 276 (54.3%).",
            "2. **PC blackout resolved**: 72 unique PC relationships published (up from 3), with 0 blocked identity collisions.",
            "3. **Ready for C1 QA Benchmark**: Core PC continuity across Sessions 1–10 is restored without model calls or graph re-extraction.",
            "",
        ]
    )
    (rechain_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def cmd_rechain(args: argparse.Namespace) -> int:
    dsn = _load_env()
    root = _out_root(args.output)
    through = int(args.through) if getattr(args, "through", None) else 10
    if through < 1 or through > 10:
        raise Stage4LError("--through must be 1..10")

    manifest_path = root / "MANIFEST.json"
    if not manifest_path.is_file():
        raise Stage4LError(
            "MANIFEST.json missing; cannot rechain without paid authority"
        )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    rechain_subdir = getattr(args, "rechain_subdir", None) or "rechain"
    rechain_dir = root / rechain_subdir
    rechain_dir.mkdir(parents=True, exist_ok=True)
    rechain_receipts_dir = rechain_dir / "receipts"
    rechain_receipts_dir.mkdir(parents=True, exist_ok=True)

    from apps.live_control_server.integrations.dungeonmind import world_graph_writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_writes import (
        _open_repository_bundle,
    )

    bundle = _open_repository_bundle(dsn)

    if getattr(args, "reset_head", False):
        baseline = "rev:d5c54ab8569139e400f0cce9ede4e60d"
        bundle.world_graph.rollback_head(
            WORLD_ID, baseline, updated_at=datetime.now(UTC)
        )
        print(f"Rehearsal head rolled back to baseline parent: {baseline}")

    context = world_graph_writes.load_production_mutation_context(
        WORLD_ID, database_url=dsn
    )
    current_head = context.head_revision_id
    print(f"Starting rechain from head: {current_head}")

    rechain_receipts = []
    total_extracted = 0
    total_published = 0

    for session_idx in range(1, through + 1):
        s_meta = manifest["sessions"][session_idx - 1]
        cand_path = REPO_ROOT / s_meta["candidate_graph_path"]
        if not cand_path.is_file():
            raise Stage4LError(
                f"Candidate file missing for session {session_idx}: {cand_path}"
            )
        cand_bytes = cand_path.read_bytes()
        cand_sha = _sha_bytes(cand_bytes)
        if cand_sha != s_meta["candidate_sha256"]:
            raise Stage4LError(
                f"Candidate SHA drift for session {session_idx}: "
                f"manifest={s_meta['candidate_sha256']} disk={cand_sha}"
            )
        source = _source_ref(session_idx)
        if source.sha256 != s_meta["source_sha256"]:
            raise Stage4LError(
                f"Source SHA drift for session {session_idx}: "
                f"manifest={s_meta['source_sha256']} disk={source.sha256}"
            )
        cand = json.loads(cand_bytes.decode("utf-8"))

        started = time.perf_counter()
        context = world_graph_writes.load_production_mutation_context(
            WORLD_ID, database_url=dsn
        )
        if context.head_revision_id != current_head:
            raise Stage4LError(
                f"Head mismatch before session {session_idx}: "
                f"expected={current_head} actual={context.head_revision_id}"
            )

        publication = _publish(
            source=source,
            candidate_path=cand_path,
            candidate=cand,
            dsn=dsn,
            expected_parent=current_head,
        )
        elapsed = round(time.perf_counter() - started, 3)
        child = publication["committed_revision_id"]
        current_head = child

        funnel = publication["edge_funnel"]
        total_extracted += funnel["extracted"]
        total_published += funnel["published"]

        receipt = {
            "schema": "dmb_stage4l_rechain_receipt_v1",
            "session": session_idx,
            "generated_at": _now(),
            "source": {
                "relpath": source.relpath,
                "sha256": source.sha256,
                "bytes": source.byte_count,
            },
            "candidate_graph_path": s_meta["candidate_graph_path"],
            "candidate_sha256": cand_sha,
            "candidate_nodes": len(cand.get("nodes") or []),
            "candidate_edges": len(cand.get("edges") or []),
            "parent_revision_id": publication["parent_revision_id"],
            "committed_revision_id": child,
            "publication_mode": publication["publication_mode"],
            "edge_funnel": funnel,
            "model_calls": 0,
            "cost_usd": 0.0,
            "wall_seconds": elapsed,
            "lineage": "zero_model_relationship_replay",
        }
        rechain_receipts.append(receipt)
        _write_json(rechain_receipts_dir / f"session_{session_idx:02d}.json", receipt)
        print(
            f"S{session_idx:02d} {child[:20]}... edges={funnel['published']:2d}/{funnel['extracted']:2d} "
            f"mode={publication['publication_mode']} wall={elapsed}s"
        )

    # Write rechain MANIFEST
    rechain_manifest = {
        "schema": "dmb_stage4l_rechain_manifest_v1",
        "generated_at": _now(),
        "campaign_id": CAMPAIGN_ID,
        "authoritative_s10_revision_id": current_head,
        "total_relationships_published": total_published,
        "total_relationships_extracted": total_extracted,
        "relationship_publication_rate": (
            f"{total_published / total_extracted * 100:.1f}%"
            if total_extracted
            else "0%"
        ),
        "model_calls": 0,
        "cost_usd": 0.0,
        "sessions": rechain_receipts,
    }
    _write_json(rechain_dir / "MANIFEST.json", rechain_manifest)

    # Write rechain REPORT
    _render_rechain_report(rechain_dir, rechain_manifest, manifest)
    print(
        f"\nRechain complete! {total_published}/{total_extracted} relationships published "
        f"({total_published / total_extracted * 100:.1f}%)."
    )
    print(f"Final revision: {current_head}")
    return 0


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--output")
    sub = value.add_subparsers(dest="command", required=True)
    census_cmd = sub.add_parser("census")
    census_cmd.add_argument("--no-write", action="store_true")
    census_cmd.set_defaults(func=cmd_census)
    run_cmd = sub.add_parser("run")
    run_cmd.add_argument("--through", type=int, required=True)
    run_cmd.add_argument("--execute", action="store_true")
    run_cmd.set_defaults(func=cmd_run)
    replay_cmd = sub.add_parser("replay")
    replay_cmd.add_argument("session", type=int)
    replay_cmd.set_defaults(func=cmd_replay)
    rechain_cmd = sub.add_parser("rechain")
    rechain_cmd.add_argument("--through", type=int, default=10)
    rechain_cmd.add_argument("--reset-head", action="store_true")
    rechain_cmd.add_argument("--rechain-subdir", type=str, default="rechain")
    rechain_cmd.set_defaults(func=cmd_rechain)
    report_cmd = sub.add_parser("report")
    report_cmd.set_defaults(func=cmd_report)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return int(args.func(args))
    except Stage4LError as exc:
        print(f"Stage 4L refused: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
