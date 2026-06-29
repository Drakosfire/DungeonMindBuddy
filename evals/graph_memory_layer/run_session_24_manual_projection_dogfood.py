from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (REPO_ROOT, REPO_ROOT / "src"):
    value = str(_path)
    if value not in sys.path:
        sys.path.insert(0, value)

from apps.live_control_server.services.graph_ingest_run_registry import (
    resolve_latest_preview_union_graph_ingest_run,
)
from apps.live_control_server.services.union_supergraph_projection_adapter import (
    build_plan_union_supergraph_projection_payload,
)
from graph_memory.ingestion import (
    GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
    GRAPH_INGEST_RUN_MANIFEST_VERSION,
    GraphIngestArtifactKind,
    GraphIngestRunStatus,
    validate_graph_ingest_run_manifest,
)
from graph_memory.union_supergraph.model import UnionSupergraphStore

FIXTURE_DIR = Path("evals/graph_memory_layer/examples/session_24_manual_projection_dogfood")
DEFAULT_OUTPUT_DIR = Path(
    "evals/graph_memory_layer/artifacts/graph_ingest_runs/"
    "session_24_manual_projection_dogfood"
)
REPORT_PATH = Path("Docs/Reports/archive/2026-06-28/graph-memory/GRAPH-MEMORY-SESSION-24-MANUAL-PROJECTION-DOGFOOD-RUN.md")
REQUIRED_NODE_SAMPLE_IDS = [
    "pc_caelynn",
    "group_edge_refugees",
    "loc_north_wall",
    "threat_meat_goo_ground_sink",
    "threat_tripod_meat_monsters",
    "npc_grobnok",
    "thread_refugee_plan",
    "thread_rockie_talkie_bridge",
]
PRIORITY_QUESTION_IDS = [
    "q:s24-opening-state",
    "q:s24-refugee-problem",
    "q:s24-wall-risk",
    "q:s24-meat-goo",
    "q:s24-monster-mechanics",
    "q:s24-chip-caelynn",
    "q:s24-chip-refugees",
    "q:s24-chip-goo",
    "q:s24-chip-wall",
    "q:s24-high-risk",
    "q:s24-proposed-writes",
    "q:s24-adjacent-session-need",
    "q:s24-clean-control",
    "q:s24-unsafe-exact-counts",
    "q:s24-unsafe-refugee-taint",
    "q:s24-unsafe-grobnok-link",
    "q:s24-unsafe-goo-destroyed",
]
FORBIDDEN_FLAGS = (
    "canon_promotion",
    "approved_memory_write",
    "corpus_mutation",
    "production_retrieval",
)


@dataclass(frozen=True)
class DogfoodArtifacts:
    validation_report_path: Path
    preview_union_store_path: Path
    manifest_path: Path
    projected_recap_preview_path: Path
    projection_payload_path: Path
    node_view_samples_path: Path
    question_review_stub_path: Path
    dogfood_status_path: Path
    report_path: Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the Session 24 manual projection dogfood rig."
    )
    parser.add_argument("--fixture-dir", type=Path, default=FIXTURE_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    args = parser.parse_args()
    artifacts = run_session_24_manual_projection_dogfood(
        fixture_dir=args.fixture_dir,
        output_dir=args.output_dir,
        report_path=args.report_path,
    )
    print(f"validation_report={artifacts.validation_report_path.as_posix()}")
    print(f"manifest={artifacts.manifest_path.as_posix()}")
    print(f"preview_union_store={artifacts.preview_union_store_path.as_posix()}")
    print(f"report={artifacts.report_path.as_posix()}")


def run_session_24_manual_projection_dogfood(
    *,
    fixture_dir: Path = FIXTURE_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = REPORT_PATH,
) -> DogfoodArtifacts:
    repo = Path.cwd().resolve()
    fixture_dir = _resolve_repo_path(repo, fixture_dir)
    output_dir = _resolve_repo_path(repo, output_dir, must_exist=False)
    report_path = _resolve_repo_path(repo, report_path, must_exist=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    gold_path = fixture_dir / "session_24_manual_gold_graph.json"
    questions_path = fixture_dir / "session_24_projection_questions.json"
    anchors_path = fixture_dir / "session_24_source_anchors.json"
    raw_recap_path = fixture_dir / "session_24_raw_recap_PLACEHOLDER.md"

    gold = _load_json(gold_path)
    questions = _load_json(questions_path)
    anchors = _load_json(anchors_path)
    raw_recap = raw_recap_path.read_text(encoding="utf-8")
    validation = _validate_fixture(gold, questions, anchors, raw_recap)

    source_span_bundle_path = output_dir / "source_span_bundle.json"
    preview_union_store_path = output_dir / "preview_union_store.json"
    projection_payload_path = output_dir / "projection_payload.json"
    projected_recap_preview_path = output_dir / "projected_recap_preview.md"
    node_view_samples_path = output_dir / "node_view_samples.json"
    question_review_stub_path = output_dir / "question_review_stub.md"
    dogfood_status_path = output_dir / "dogfood_status.md"
    validation_report_path = output_dir / "validation_report.json"
    manifest_path = output_dir / "graph_ingest_run_manifest.json"

    _write_json(source_span_bundle_path, _source_span_bundle(gold, anchors))
    preview_store = _build_preview_union_store(gold, anchors, raw_recap_path)
    UnionSupergraphStore.model_validate(preview_store)
    _write_json(preview_union_store_path, preview_store)

    projection_payload = build_plan_union_supergraph_projection_payload(
        session_id=gold["session_id"],
        preview_union_store_path=preview_union_store_path,
    )
    _write_json(projection_payload_path, projection_payload)
    projected_recap_preview_path.write_text(
        projection_payload.get("markdown") or "", encoding="utf-8"
    )

    _write_json(
        node_view_samples_path,
        _node_view_samples(
            projection_payload=projection_payload,
            graph=gold,
            required_node_ids=REQUIRED_NODE_SAMPLE_IDS,
        ),
    )
    question_review_stub_path.write_text(
        _question_review_stub(gold, questions, PRIORITY_QUESTION_IDS),
        encoding="utf-8",
    )

    manifest = _build_manifest(
        gold=gold,
        raw_recap_path=raw_recap_path,
        source_span_bundle_path=source_span_bundle_path,
        preview_union_store_path=preview_union_store_path,
        projection_payload_path=projection_payload_path,
        validation=validation,
        repo=repo,
    )
    manifest_validation = validate_graph_ingest_run_manifest(manifest)
    validation["manifest_validation"] = manifest_validation
    if manifest_validation["errors"]:
        validation["errors"].extend(
            f"manifest: {error}" for error in manifest_validation["errors"]
        )

    _write_json(manifest_path, manifest)
    validation["registry_discovery"] = _registry_probe(
        manifest_path=manifest_path,
        campaign_id=gold["campaign_id"],
        session_id=gold["session_id"],
    )
    _write_json(validation_report_path, validation)

    projection_load = _projection_probe(gold["session_id"], manifest_path)
    status_text = _dogfood_status(
        validation=validation,
        manifest_validation=manifest_validation,
        projection_load=projection_load,
        artifacts={
            "validation_report": validation_report_path,
            "manifest": manifest_path,
            "preview_union_store": preview_union_store_path,
            "projection_payload": projection_payload_path,
            "node_view_samples": node_view_samples_path,
            "question_review_stub": question_review_stub_path,
        },
    )
    dogfood_status_path.write_text(status_text, encoding="utf-8")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _report(
            validation=validation,
            manifest_validation=manifest_validation,
            projection_load=projection_load,
            projection_payload=projection_payload,
            node_samples_path=node_view_samples_path,
            question_stub_path=question_review_stub_path,
            manifest_path=manifest_path,
            preview_union_store_path=preview_union_store_path,
        ),
        encoding="utf-8",
    )
    return DogfoodArtifacts(
        validation_report_path=validation_report_path,
        preview_union_store_path=preview_union_store_path,
        manifest_path=manifest_path,
        projected_recap_preview_path=projected_recap_preview_path,
        projection_payload_path=projection_payload_path,
        node_view_samples_path=node_view_samples_path,
        question_review_stub_path=question_review_stub_path,
        dogfood_status_path=dogfood_status_path,
        report_path=report_path,
    )


def _validate_fixture(
    gold: Mapping[str, Any],
    questions: Mapping[str, Any],
    anchors: Mapping[str, Any],
    raw_recap: str,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    node_ids = {str(node["node_id"]) for node in gold.get("nodes", [])}
    evidence_ids = {str(ref["evidence_ref_id"]) for ref in gold.get("evidence_refs", [])}
    anchor_ids = {str(anchor["anchor_id"]) for anchor in anchors.get("anchors", [])}

    for ref in gold.get("evidence_refs", []):
        _require_id(ref.get("source_anchor_id"), anchor_ids, errors, "evidence source_anchor_id")
    for node in gold.get("nodes", []):
        _require_all(node.get("evidence_ref_ids", []), evidence_ids, errors, f"node {node.get('node_id')}")
    for edge in gold.get("edges", []):
        _require_id(edge.get("source_node_id"), node_ids, errors, f"edge {edge.get('edge_id')} source")
        _require_id(edge.get("target_node_id"), node_ids, errors, f"edge {edge.get('edge_id')} target")
        _require_all(edge.get("evidence_ref_ids", []), evidence_ids, errors, f"edge {edge.get('edge_id')}")
    for item in gold.get("deferred_items", []):
        _require_all(item.get("evidence_ref_ids", []), evidence_ids, errors, f"deferred {item.get('deferred_id')}")
    for item in gold.get("proposed_writes", []):
        _require_all(item.get("evidence_ref_ids", []), evidence_ids, errors, f"write {item.get('write_id')}")
        if str(item.get("status", "")).lower() == "approved":
            errors.append(f"proposed write is approved: {item.get('write_id')}")
        if item.get("allowed_in_this_fixture") is not False:
            errors.append(f"proposed write is allowed in fixture: {item.get('write_id')}")
    for chip in gold.get("expected_recap_chips", []):
        _require_id(chip.get("node_id"), node_ids, errors, f"expected chip {chip.get('text')}")
    for question in questions.get("questions", []):
        _require_all(question.get("required_nodes", []), node_ids, errors, f"question {question.get('question_id')} required_nodes")
        _require_all(question.get("expected_evidence_ref_ids", []), evidence_ids, errors, f"question {question.get('question_id')} evidence")

    safety = gold.get("safety", {})
    for flag in FORBIDDEN_FLAGS:
        if safety.get(flag) is not False:
            errors.append(f"safety flag is not false: {flag}")
    if safety.get("llm_extraction_required") is not False:
        errors.append("safety flag is not false: llm_extraction_required")
    if "PASTE RAW SESSION 24 RECAP HERE" in raw_recap:
        warnings.append("raw recap placeholder has not been populated; source-span text matching is blocked")

    return {
        "schema": "dmb_session_24_manual_projection_dogfood_validation_v0",
        "version": "0.1",
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "counts": {
            "nodes": len(node_ids),
            "edges": len(gold.get("edges", [])),
            "evidence_refs": len(evidence_ids),
            "deferred_items": len(gold.get("deferred_items", [])),
            "proposed_writes": len(gold.get("proposed_writes", [])),
            "questions": len(questions.get("questions", [])),
        },
        "safety": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
            "llm_extraction": False,
        },
    }


def _build_preview_union_store(
    graph: Mapping[str, Any],
    anchors: Mapping[str, Any],
    raw_recap_path: Path,
) -> dict[str, Any]:
    evidence = _evidence_map(graph, anchors)
    nodes = {
        node["node_id"]: {
            "node_id": node["node_id"],
            "label": node["label"],
            "kind": node["kind"],
            "role": node["kind"],
            "aliases": sorted(set([node["label"], *node.get("aliases", [])])),
            "source_domains": ["recap"],
            "evidence_ref_ids": list(node.get("evidence_ref_ids", [])),
            "state": {
                "memory_state": "preview_manual_gold",
                "canon_state": "non_canon",
                "approval_state": "not_approved",
            },
            "description": node.get("session_focus_summary"),
            "session_focus_summary": node.get("session_focus_summary"),
            **({"members": node["members"]} if "members" in node else {}),
        }
        for node in graph.get("nodes", [])
    }
    edges = {
        edge["edge_id"]: {
            "edge_id": edge["edge_id"],
            "source_node_id": edge["source_node_id"],
            "target_node_id": edge["target_node_id"],
            "predicate": edge["predicate"],
            "label": edge["label"],
            "direction": "directed",
            "source_domains": ["recap"],
            "session_ids": [graph["session_id"]],
            "evidence_ref_ids": list(edge.get("evidence_ref_ids", [])),
            "state": {
                "memory_state": "preview_manual_gold",
                "canon_state": "non_canon",
                "approval_state": "not_approved",
                "high_risk": bool(edge.get("high_risk", False)),
            },
        }
        for edge in graph.get("edges", [])
    }
    return {
        "schema": "dmb_union_supergraph_store_v0",
        "version": "0.1",
        "campaign_id": graph["campaign_id"],
        "graph_id": f"{graph['campaign_id']}:preview-union-supergraph",
        "graph_domains": ["manual_projection_dogfood"],
        "source_domains": ["recap"],
        "focus_session_id": graph["focus_session_id"],
        "nodes": nodes,
        "edges": edges,
        "evidence": evidence,
        "source_artifacts": {
            graph["source_artifact_id"]: {
                "source_artifact_id": graph["source_artifact_id"],
                "source_domain": "recap",
                "campaign_id": graph["campaign_id"],
                "session_id": graph["session_id"],
                "uri": _repo_rel(raw_recap_path),
                "recap_path": _repo_rel(raw_recap_path),
                "label": "Session 24 manual raw recap placeholder",
                "preview_only": True,
            }
        },
        "aliases": _alias_map(graph.get("nodes", [])),
        "adjacency": _adjacency(edges),
        "diagnostics": {
            "preview_only": True,
            "manual_gold": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
        "deferred_items": graph.get("deferred_items", []),
        "proposed_writes": graph.get("proposed_writes", []),
        "expected_recap_chips": graph.get("expected_recap_chips", []),
    }


def _evidence_map(graph: Mapping[str, Any], anchors: Mapping[str, Any]) -> dict[str, Any]:
    anchor_by_id = {anchor["anchor_id"]: anchor for anchor in anchors.get("anchors", [])}
    evidence: dict[str, Any] = {}
    for ref in graph.get("evidence_refs", []):
        anchor = anchor_by_id.get(ref["source_anchor_id"], {})
        evidence[ref["evidence_ref_id"]] = {
            "evidence_ref_id": ref["evidence_ref_id"],
            "source_artifact_id": graph["source_artifact_id"],
            "source_domain": ref.get("source_domain", "recap"),
            "evidence_role": anchor.get("evidence_role", "source_evidence"),
            "can_open_source": bool(ref.get("can_open_source", True)),
            "can_highlight_span": bool(ref.get("can_highlight_span", True)),
            "session_id": ref.get("session_id", graph["session_id"]),
            "source_span_ref_id": ref["source_anchor_id"],
            "source_locator": json.dumps(anchor.get("source_locator", {}), sort_keys=True),
            "label": anchor.get("label", ref["evidence_ref_id"]),
            "summary": anchor.get("summary"),
        }
    return evidence


def _alias_map(nodes: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for node in nodes:
        node_id = str(node["node_id"])
        for alias in [node["label"], *node.get("aliases", [])]:
            aliases.setdefault(str(alias), node_id)
    return aliases


def _adjacency(edges: Mapping[str, Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge_id, edge in edges.items():
        source = str(edge["source_node_id"])
        target = str(edge["target_node_id"])
        anchored = bool(edge.get("evidence_ref_ids"))
        adjacency.setdefault(source, []).append(
            {
                "edge_id": edge_id,
                "node_id": target,
                "direction": "outgoing",
                "label": edge["label"],
                "anchored_to_focus_session": anchored,
            }
        )
        adjacency.setdefault(target, []).append(
            {
                "edge_id": edge_id,
                "node_id": source,
                "direction": "incoming",
                "label": edge["label"],
                "anchored_to_focus_session": anchored,
            }
        )
    return {node_id: sorted(items, key=lambda item: item["node_id"]) for node_id, items in adjacency.items()}


def _source_span_bundle(graph: Mapping[str, Any], anchors: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema": "dmb_manual_projection_source_span_bundle_v0",
        "version": "0.1",
        "campaign_id": graph["campaign_id"],
        "session_id": graph["session_id"],
        "source_artifact_id": graph["source_artifact_id"],
        "source_artifact_path": graph["source_artifact_path"],
        "anchors": anchors.get("anchors", []),
        "preview_only": True,
    }


def _build_manifest(
    *,
    gold: Mapping[str, Any],
    raw_recap_path: Path,
    source_span_bundle_path: Path,
    preview_union_store_path: Path,
    projection_payload_path: Path,
    validation: Mapping[str, Any],
    repo: Path,
) -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema": GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
        "version": GRAPH_INGEST_RUN_MANIFEST_VERSION,
        "run_id": "graph-ingest:longmont-c2:session-24:manual-projection-dogfood",
        "campaign_id": gold["campaign_id"],
        "session_id": gold["session_id"],
        "status": GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value,
        "created_at": now,
        "updated_at": now,
        "source": {
            "source_artifact_id": gold["source_artifact_id"],
            "source_domain": "recap",
            "normalized_recap_path": _repo_rel(raw_recap_path),
            "normalized_recap_sha256": _sha256(repo / raw_recap_path),
            "source_label": "Session 24 manual projection dogfood fixture",
            "source_span_bundle_uri": _repo_rel(source_span_bundle_path),
        },
        "steps": [
            _step("validate_manual_fixture", "Validate manual Session 24 fixture", validation["valid"]),
            _step("adapt_preview_union_store", "Adapt manual graph to preview union store", True),
            _step("load_projection", "Load union-supergraph projection", True),
        ],
        "artifacts": {
            GraphIngestArtifactKind.SOURCE_SPAN_BUNDLE.value: _artifact(
                GraphIngestArtifactKind.SOURCE_SPAN_BUNDLE.value,
                source_span_bundle_path,
                "dmb_manual_projection_source_span_bundle_v0",
            ),
            GraphIngestArtifactKind.PREVIEW_UNION_STORE.value: _artifact(
                GraphIngestArtifactKind.PREVIEW_UNION_STORE.value,
                preview_union_store_path,
                "dmb_union_supergraph_store_v0",
            ),
            GraphIngestArtifactKind.PROJECTION_PAYLOAD.value: _artifact(
                GraphIngestArtifactKind.PROJECTION_PAYLOAD.value,
                projection_payload_path,
                "dmb_recap_graph_projection_v0",
            ),
        },
        "health": {
            "candidate_graph_valid": True,
            "preview_union_store_valid": validation["valid"],
            "node_count": validation["counts"]["nodes"],
            "edge_count": validation["counts"]["edges"],
            "deferred_count": validation["counts"]["deferred_items"],
            "evidence_ref_count": validation["counts"]["evidence_refs"],
            "resolvable_evidence_ref_count": validation["counts"]["evidence_refs"],
            "openable_evidence_ref_count": validation["counts"]["evidence_refs"],
            "highlightable_evidence_ref_count": validation["counts"]["evidence_refs"],
            "model_id": None,
            "estimated_cost_usd": None,
        },
        "diagnostics": {
            "preview_only": True,
            "candidate_extraction": False,
            "preview_import": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
            "agent_interaction_connected": False,
            "runtime_projection_connected": True,
            "manual_gold": True,
            "llm_extraction": False,
        },
        "projection": None,
        "warnings": list(validation["warnings"]),
        "errors": list(validation["errors"]),
        "next_actions": ["open_projection_preview", "manual_gm_dogfood_review"],
    }


def _step(step_id: str, label: str, complete: bool) -> dict[str, Any]:
    state = "complete" if complete else "failed"
    return {"id": step_id, "label": label, "state": state, "artifact_refs": []}


def _artifact(kind: str, path: Path, schema: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "uri": _repo_rel(path),
        "schema": schema,
        "sha256": _sha256(path),
        "exists": path.exists(),
        "preview_only": True,
    }


def _node_view_samples(
    *,
    projection_payload: Mapping[str, Any],
    graph: Mapping[str, Any],
    required_node_ids: Iterable[str],
) -> dict[str, Any]:
    node_views = projection_payload.get("node_views", {})
    deferred = graph.get("deferred_items", [])
    samples = {}
    for node_id in required_node_ids:
        view = dict(node_views[node_id])
        evidence_ids = {badge["evidence_ref_id"] for badge in view.get("evidence_badges", [])}
        view["deferred_or_high_risk_boundaries"] = [
            item for item in deferred if evidence_ids.intersection(item.get("evidence_ref_ids", []))
        ]
        samples[node_id] = view
    return {
        "schema": "dmb_session_24_manual_projection_node_view_samples_v0",
        "version": "0.1",
        "node_samples": samples,
    }


def _question_review_stub(
    graph: Mapping[str, Any],
    questions: Mapping[str, Any],
    priority_ids: Iterable[str],
) -> str:
    node_ids = {node["node_id"] for node in graph.get("nodes", [])}
    evidence_ids = {ref["evidence_ref_id"] for ref in graph.get("evidence_refs", [])}
    by_id = {question["question_id"]: question for question in questions.get("questions", [])}
    lines = ["# Session 24 Projection Question Review Stub", ""]
    for question_id in priority_ids:
        question = by_id[question_id]
        required = question.get("required_nodes", [])
        evidence = question.get("expected_evidence_ref_ids", [])
        supports = all(item in node_ids for item in required) and all(
            item in evidence_ids for item in evidence
        )
        lines.extend(
            [
                f"## {question_id}",
                "",
                f"Question: {question['question']}",
                "",
                f"Required nodes: {', '.join(required) or 'None'}",
                f"Expected evidence refs: {', '.join(evidence) or 'None'}",
                f"Must include: {'; '.join(question.get('must_include', [])) or 'None'}",
                f"Must not claim: {'; '.join(question.get('must_not_claim', [])) or 'None'}",
                f"Fixture graph supports it: {'yes' if supports else 'no'}",
                "Manual reviewer notes: TODO",
                "",
            ]
        )
    return "\n".join(lines)


def _registry_probe(manifest_path: Path, campaign_id: str, session_id: str) -> dict[str, Any]:
    if not manifest_path.exists():
        return {"ok": False, "detail": "manifest not written yet"}
    try:
        latest = resolve_latest_preview_union_graph_ingest_run(
            campaign_id=campaign_id,
            session_id=session_id,
        )
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}
    return {
        "ok": latest.manifest_path == _repo_rel(manifest_path),
        "latest_manifest_path": latest.manifest_path,
        "preview_union_store_path": latest.preview_union_store_path,
    }


def _projection_probe(session_id: str, manifest_path: Path) -> dict[str, Any]:
    try:
        payload = build_plan_union_supergraph_projection_payload(
            session_id=session_id,
            graph_run_manifest_path=manifest_path,
        )
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}
    return {
        "ok": True,
        "node_view_count": len(payload.get("node_views", {})),
        "mention_count": len(payload.get("mentions", [])),
        "graph_id": payload.get("graph_id"),
    }


def _dogfood_status(
    *,
    validation: Mapping[str, Any],
    manifest_validation: Mapping[str, Any],
    projection_load: Mapping[str, Any],
    artifacts: Mapping[str, Path],
) -> str:
    lines = [
        "# Session 24 Manual Projection Dogfood Status",
        "",
        f"Fixture validation: {'PASS' if validation['valid'] else 'FAIL'}",
        f"Manifest validation: {'PASS' if manifest_validation['valid'] else 'FAIL'}",
        f"Projection load: {'PASS' if projection_load['ok'] else 'FAIL'}",
        "",
        "## Artifacts",
    ]
    lines.extend(f"- {name}: `{_repo_rel(path)}`" for name, path in artifacts.items())
    if validation["warnings"]:
        lines.extend(["", "## Warnings", *[f"- {warning}" for warning in validation["warnings"]]])
    if validation["errors"]:
        lines.extend(["", "## Errors", *[f"- {error}" for error in validation["errors"]]])
    return "\n".join(lines) + "\n"


def _report(
    *,
    validation: Mapping[str, Any],
    manifest_validation: Mapping[str, Any],
    projection_load: Mapping[str, Any],
    projection_payload: Mapping[str, Any],
    node_samples_path: Path,
    question_stub_path: Path,
    manifest_path: Path,
    preview_union_store_path: Path,
) -> str:
    useful = ["pc_caelynn", "group_edge_refugees", "threat_meat_goo_ground_sink"]
    weak = ["projected recap chips: blocked until raw recap placeholder is populated", "cross-session/global context: Session 24 only", "source span highlighting: anchor ids only until raw recap text exists"]
    hooks = ["Edge refugee plan", "north wall structural integrity", "meat goo underground", "Grobnok callback", "Grobnok-Lysandra link"]
    latest_ready = validation["registry_discovery"].get("ok") is True
    projection_ready = projection_load.get("ok") is True
    load_verdict = "yes" if latest_ready and projection_ready else "blocked"
    chip_verdict = "blocked until the raw recap placeholder is populated"
    return f"""# Graph Memory Session 24 Manual Projection Dogfood Run

## Result

1. Session 24 fixture validates: {"yes" if validation["valid"] else "no"}.
2. Preview union store generated: `{_repo_rel(preview_union_store_path)}`.
3. Graph-ingest run manifest generated: `{_repo_rel(manifest_path)}`.
4. Registry latest discovery: {validation["registry_discovery"]}.
5. Projection path load: {projection_load}.
6. Useful chips: {", ".join(useful)}.
7. Missing or weak chips: {"; ".join(weak)}.
8. Unresolved hooks preserved: {", ".join(hooks)}.
9. Canon/write safety: no canon promotion, no corpus mutation, no approved writes, no production retrieval.
10. Ready for human `/plan` load proof: {load_verdict}. Ready for real markdown chip dogfood: {chip_verdict}.

## Evidence

- Validation report valid: `{validation["valid"]}`.
- Manifest validation valid: `{manifest_validation["valid"]}`.
- Projection node views: `{len(projection_payload.get("node_views", {}))}`.
- Projection mentions: `{len(projection_payload.get("mentions", []))}`.
- Node samples: `{_repo_rel(node_samples_path)}`.
- Question review stub: `{_repo_rel(question_stub_path)}`.

## Caveats

- The raw recap placeholder is not populated, so full source-span text matching and real recap chip density are blocked.
- This run is manual gold, preview-only, non-canon, and read-only. It does not run extraction or approve memory writes.
"""


def _require_id(value: Any, allowed: set[str], errors: list[str], context: str) -> None:
    if str(value) not in allowed:
        errors.append(f"{context} references missing id: {value}")


def _require_all(values: Iterable[Any], allowed: set[str], errors: list[str], context: str) -> None:
    for value in values:
        _require_id(value, allowed, errors, context)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _resolve_repo_path(repo: Path, path: Path, *, must_exist: bool = True) -> Path:
    candidate = path if path.is_absolute() else repo / path
    resolved = candidate.resolve()
    resolved.relative_to(repo)
    if must_exist and not resolved.exists():
        raise FileNotFoundError(path)
    return resolved


def _repo_rel(path: Path) -> str:
    return path.resolve().relative_to(Path.cwd().resolve()).as_posix()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


if __name__ == "__main__":
    main()
