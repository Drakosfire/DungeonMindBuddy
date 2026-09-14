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


def _candidate_path(root: Path, session: int, run_id: str | None = None) -> Path:
    session_dir = root / f"session_{session:02d}"
    candidates = []
    if run_id:
        candidates.append(session_dir / run_id / "candidate_graph.json")
    candidates.extend([session_dir / "candidate_graph.json"])
    candidates.extend(sorted(session_dir.glob("*/candidate_graph.json")))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise Stage4LError(f"durable candidate missing for Session {session}")


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


def _edge_funnel(
    candidate: Mapping[str, Any], review_items: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    edges = list(candidate.get("edges") or [])
    canonical = [
        edge for edge in edges if edge.get("from_node_id") and edge.get("to_node_id")
    ]
    selectable = [
        item
        for item in review_items
        if item.get("selectable")
        and str(item.get("kind") or "").lower() in {"edge", "relationship"}
    ]
    return {
        "extracted": len(edges),
        "canonical_endpoints": len(canonical),
        "admitted_predicates": len(selectable),
        "publishable": len(selectable),
        "published": 0,
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
    selected_all = _select(items, edges=True)
    funnel = _edge_funnel(candidate, items)
    if not selected_all:
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

    mode = "all"
    edge_error = None
    try:
        confirmed = confirm(selected_all)
        funnel["published"] = funnel["publishable"]
    except Exception as exc:  # explicit experimental partial, never hidden as success
        selected_nodes = _select(items, edges=False)
        if not selected_nodes:
            raise
        edge_error = f"{type(exc).__name__}: {exc}"
        confirmed = confirm(selected_nodes)
        mode = "node_object_partial"
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
            selected_all if mode == "all" else _select(items, edges=False)
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
        receipt_path = root / "receipts" / f"session_{session:02d}.json"
        old = json.loads(receipt_path.read_text(encoding="utf-8"))
        if old["source"]["sha256"] != source.sha256:
            raise Stage4LError("saved candidate source digest drift")
        if old["context"]["prior_world_revision_id"] != prior_revision:
            raise Stage4LError("saved candidate prior World revision drift")
        candidate_path = _candidate_path(root, session, old.get("run_id"))
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
        "candidate_graph_path": candidate_path.relative_to(REPO_ROOT).as_posix(),
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
    }
    _write_json(root / "receipts" / f"session_{session:02d}.json", receipt)
    _write_json(
        root / f"session_{session:02d}" / "review_package.json",
        publication["review_package"],
    )
    return receipt


def _completed_receipts(root: Path) -> list[dict[str, Any]]:
    receipts = []
    for path in sorted((root / "receipts").glob("session_[0-9][0-9].json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if value.get("schema") == "dmb_stage4l_session_receipt_v1":
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
    next_session = len(existing) + 1
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
