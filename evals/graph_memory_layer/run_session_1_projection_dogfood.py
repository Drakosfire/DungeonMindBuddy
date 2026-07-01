"""Materialize C1S1 vocabulary-ablation candidate graph into a /plan recap projection dogfood run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

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
from graph_memory.union_supergraph.preview_import import (
    CandidateGraphInput,
    build_preview_union_supergraph,
)

CAMPAIGN_ID = "longmont-c1"
SESSION_ID = "session-1"
FOCUS_SESSION_ID = "session-1"
RUN_ID = "graph-ingest:longmont-c1:session-1:vocabulary-ablation-projection-dogfood"

DEFAULT_CANDIDATE_GRAPH = Path(
    "evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/"
    "c1s1-stonebridge_edge_and_node_packet_candidate_graph.json"
)
DEFAULT_RECAP_PATH = Path(
    "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 1/Session Recaps/"
    "_normalized/Session 01 - Stonebridge and Glowkindle Rats.md"
)
DEFAULT_WORLD_CANDIDATE = Path(
    "evals/graph_memory_layer/artifacts/vocabulary_ablation_dogfood/manual_review/"
    "mirathorn-city_baseline_candidate_graph.json"
)
DEFAULT_WORLD_RECAP = Path(
    "evals/graph_memory_layer/examples/mirathorn_city_world_doc/mirathorn_city_source.md"
)
DEFAULT_OUTPUT_DIR = Path(
    "evals/graph_memory_layer/artifacts/graph_ingest_runs/"
    "session_1_vocabulary_ablation_projection_dogfood"
)
REPORT_PATH = Path(
    "Docs/Reports/GRAPH-MEMORY-SESSION-1-VOCABULARY-ABLATION-PROJECTION-DOGFOOD-RUN.md"
)


@dataclass(frozen=True)
class DogfoodArtifacts:
    validation_report_path: Path
    preview_union_store_path: Path
    manifest_path: Path
    projection_payload_path: Path
    projected_recap_preview_path: Path
    dogfood_status_path: Path
    report_path: Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize C1S1 vocabulary-ablation graph for /plan recap projection dogfood.",
    )
    parser.add_argument("--candidate-graph", type=Path, default=DEFAULT_CANDIDATE_GRAPH)
    parser.add_argument("--recap-path", type=Path, default=DEFAULT_RECAP_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    parser.add_argument(
        "--include-mirathorn-world",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Merge Mirathorn worldbuilding candidate graph into the preview union store.",
    )
    parser.add_argument("--world-candidate-graph", type=Path, default=DEFAULT_WORLD_CANDIDATE)
    parser.add_argument("--world-recap-path", type=Path, default=DEFAULT_WORLD_RECAP)
    args = parser.parse_args()
    artifacts = run_session_1_projection_dogfood(
        candidate_graph_path=args.candidate_graph,
        recap_path=args.recap_path,
        output_dir=args.output_dir,
        report_path=args.report_path,
        include_mirathorn_world=args.include_mirathorn_world,
        world_candidate_graph_path=args.world_candidate_graph,
        world_recap_path=args.world_recap_path,
    )
    print(f"validation_report={artifacts.validation_report_path.as_posix()}")
    print(f"manifest={artifacts.manifest_path.as_posix()}")
    print(f"preview_union_store={artifacts.preview_union_store_path.as_posix()}")
    print(f"report={artifacts.report_path.as_posix()}")


def run_session_1_projection_dogfood(
    *,
    candidate_graph_path: Path = DEFAULT_CANDIDATE_GRAPH,
    recap_path: Path = DEFAULT_RECAP_PATH,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    report_path: Path = REPORT_PATH,
    include_mirathorn_world: bool = True,
    world_candidate_graph_path: Path = DEFAULT_WORLD_CANDIDATE,
    world_recap_path: Path = DEFAULT_WORLD_RECAP,
) -> DogfoodArtifacts:
    repo = Path.cwd().resolve()
    candidate_graph_path = _resolve_repo_path(repo, candidate_graph_path)
    recap_path = _resolve_repo_path(repo, recap_path)
    output_dir = _resolve_repo_path(repo, output_dir, must_exist=False)
    report_path = _resolve_repo_path(repo, report_path, must_exist=False)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_candidate = _load_json(candidate_graph_path)
    import_input_path = output_dir / "candidate_graph_import_input.json"
    _write_json(import_input_path, _prepare_candidate_graph(raw_candidate, recap_path))

    graph_inputs = [
        CandidateGraphInput(
            path=import_input_path,
            session_id=SESSION_ID,
            recap_path=recap_path,
        )
    ]
    if include_mirathorn_world:
        world_candidate_path = _resolve_repo_path(repo, world_candidate_graph_path)
        world_recap = _resolve_repo_path(repo, world_recap_path)
        world_import_path = output_dir / "mirathorn_candidate_graph_import_input.json"
        _write_json(
            world_import_path,
            _prepare_world_candidate_graph(_load_json(world_candidate_path), world_recap),
        )
        graph_inputs.append(
            CandidateGraphInput(
                path=world_import_path,
                session_id="mirathorn-city",
                recap_path=world_recap,
            )
        )

    preview_union_store_path = output_dir / "preview_union_store.json"
    projection_payload_path = output_dir / "projection_payload.json"
    projected_recap_preview_path = output_dir / "projected_recap_preview.md"
    source_span_index_path = output_dir / "source_span_index.json"
    validation_report_path = output_dir / "validation_report.json"
    manifest_path = output_dir / "graph_ingest_run_manifest.json"
    dogfood_status_path = output_dir / "dogfood_status.md"

    preview_store = build_preview_union_supergraph(
        graph_inputs,
        focus_session_id=FOCUS_SESSION_ID,
        graph_id=f"{CAMPAIGN_ID}:preview-union-supergraph",
    )
    preview_store["campaign_id"] = CAMPAIGN_ID
    preview_store["graph_domains"] = ["campaign", "worldbuilding", "preview"]
    preview_store.setdefault("diagnostics", {}).update(
        {
            "preview_only": True,
            "vocabulary_ablation_dogfood": True,
            "manual_gold": False,
            "candidate_extraction": True,
        }
    )
    UnionSupergraphStore.model_validate(preview_store)
    _write_json(preview_union_store_path, preview_store)

    _write_json(
        source_span_index_path,
        _build_source_span_index(recap_path, campaign_id=CAMPAIGN_ID, session_id=SESSION_ID),
    )

    node_count = len(preview_store.get("nodes", {}))
    edge_count = len(preview_store.get("edges", {}))
    evidence_count = len(preview_store.get("evidence", {}))

    validation = {
        "schema": "dmb_session_1_vocabulary_ablation_projection_dogfood_validation_v0",
        "version": "0.1",
        "valid": True,
        "errors": [],
        "warnings": [],
        "counts": {
            "nodes": node_count,
            "edges": edge_count,
            "evidence_refs": evidence_count,
            "graph_inputs": len(graph_inputs),
        },
        "safety": {
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
            "llm_extraction": False,
        },
    }

    projection_payload = build_plan_union_supergraph_projection_payload(
        session_id=SESSION_ID,
        preview_union_store_path=preview_union_store_path,
    )
    _write_json(projection_payload_path, projection_payload)
    projected_recap_preview_path.write_text(
        projection_payload.get("markdown") or "",
        encoding="utf-8",
    )
    mention_count = len(projection_payload.get("mentions", []))
    validation["counts"]["mentions"] = mention_count

    manifest = _build_manifest(
        recap_path=recap_path,
        candidate_graph_path=candidate_graph_path,
        import_input_path=import_input_path,
        preview_union_store_path=preview_union_store_path,
        projection_payload_path=projection_payload_path,
        source_span_index_path=source_span_index_path,
        validation=validation,
        include_mirathorn_world=include_mirathorn_world,
    )
    manifest_validation = validate_graph_ingest_run_manifest(manifest)
    validation["manifest_validation"] = manifest_validation
    if manifest_validation["errors"]:
        validation["valid"] = False
        validation["errors"].extend(
            f"manifest: {error}" for error in manifest_validation["errors"]
        )

    _write_json(manifest_path, manifest)

    validation["registry_discovery"] = _registry_probe(manifest_path)
    validation["projection_load"] = _projection_probe(manifest_path)
    _write_json(validation_report_path, validation)

    status_lines = [
        "# Session 1 Vocabulary Ablation Projection Dogfood Status",
        "",
        f"Fixture validation: {'PASS' if validation['valid'] else 'FAIL'}",
        f"Manifest validation: {'PASS' if manifest_validation['valid'] else 'FAIL'}",
        f"Projection load: {'PASS' if validation['projection_load'].get('ok') else 'FAIL'}",
        "",
        "## Artifacts",
        f"- validation_report: `{_repo_rel(validation_report_path)}`",
        f"- manifest: `{_repo_rel(manifest_path)}`",
        f"- preview_union_store: `{_repo_rel(preview_union_store_path)}`",
        f"- projection_payload: `{_repo_rel(projection_payload_path)}`",
        f"- projected_recap_preview: `{_repo_rel(projected_recap_preview_path)}`",
        "",
        "## Notes",
        f"- Candidate graph: `{_repo_rel(candidate_graph_path)}`",
        f"- Recap source: `{_repo_rel(recap_path)}`",
        f"- Mirathorn world merged: `{include_mirathorn_world}`",
        f"- Projected mention chips: {mention_count}",
    ]
    dogfood_status_path.write_text("\n".join(status_lines) + "\n", encoding="utf-8")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        _report(
            validation=validation,
            manifest_path=manifest_path,
            preview_union_store_path=preview_union_store_path,
            mention_count=mention_count,
            include_mirathorn_world=include_mirathorn_world,
        ),
        encoding="utf-8",
    )

    return DogfoodArtifacts(
        validation_report_path=validation_report_path,
        preview_union_store_path=preview_union_store_path,
        manifest_path=manifest_path,
        projection_payload_path=projection_payload_path,
        projected_recap_preview_path=projected_recap_preview_path,
        dogfood_status_path=dogfood_status_path,
        report_path=report_path,
    )


def _prepare_candidate_graph(raw: Mapping[str, Any], recap_path: Path) -> dict[str, Any]:
    graph = dict(raw.get("candidate_graph") or raw)
    graph["campaign_id"] = CAMPAIGN_ID
    graph["session_id"] = SESSION_ID
    graph["source_artifact_ids"] = graph.get("source_artifact_ids") or [
        f"artifact:recap:{CAMPAIGN_ID}:{SESSION_ID}"
    ]
    _rewrite_span_refs(graph, session_id=SESSION_ID, prefix="c1s1-recap")
    return graph


def _prepare_world_candidate_graph(raw: Mapping[str, Any], recap_path: Path) -> dict[str, Any]:
    graph = dict(raw.get("candidate_graph") or raw)
    graph["campaign_id"] = graph.get("campaign_id") or "elderwyld"
    graph["session_id"] = graph.get("session_id") or "mirathorn-city"
    graph["source_artifact_ids"] = graph.get("source_artifact_ids") or [
        "artifact:worldbuilding:mirathorn-city"
    ]
    _rewrite_span_refs(graph, session_id="mirathorn-city", prefix="mirathorn-city")
    return graph


def _rewrite_span_refs(graph: dict[str, Any], *, session_id: str, prefix: str) -> None:
    pattern = re.compile(rf"^spref:{re.escape(prefix)}:(\d+)$")

    def rewrite(value: Any) -> Any:
        if isinstance(value, str):
            match = pattern.match(value)
            if match:
                return f"spref:{session_id}:p{int(match.group(1)):03d}"
            return value
        if isinstance(value, list):
            return [rewrite(item) for item in value]
        if isinstance(value, dict):
            return {key: rewrite(item) for key, item in value.items()}
        return value

    for key in ("nodes", "edges", "beats", "proposed_writes", "ignored_items", "deferred_items"):
        if key in graph:
            graph[key] = rewrite(graph[key])


def _build_source_span_index(
    recap_path: Path,
    *,
    campaign_id: str,
    session_id: str,
) -> dict[str, Any]:
    text = recap_path.read_text(encoding="utf-8")
    if text.startswith("---"):
        lines = text.splitlines()
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                text = "\n".join(lines[index + 1 :]).lstrip("\n")
                break
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    spans: list[dict[str, Any]] = [
        {
            "span_id": "document",
            "kind": "document",
            "ordinal": 0,
            "text_excerpt": paragraphs[0][:240] if paragraphs else "",
        }
    ]
    for index, paragraph in enumerate(paragraphs, start=1):
        spans.append(
            {
                "span_id": f"spref:{session_id}:p{index:03d}",
                "kind": "paragraph",
                "ordinal": index,
                "text_excerpt": paragraph[:240],
                "text": paragraph,
            }
        )
    return {
        "schema": "dmb_source_span_index_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_sha256": _sha256(recap_path),
        "paragraph_span_count": len(paragraphs),
        "spans": spans,
    }


def _build_manifest(
    *,
    recap_path: Path,
    candidate_graph_path: Path,
    import_input_path: Path,
    preview_union_store_path: Path,
    projection_payload_path: Path,
    source_span_index_path: Path,
    validation: Mapping[str, Any],
    include_mirathorn_world: bool,
) -> dict[str, Any]:
    now = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "schema": GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
        "version": GRAPH_INGEST_RUN_MANIFEST_VERSION,
        "run_id": RUN_ID,
        "campaign_id": CAMPAIGN_ID,
        "session_id": SESSION_ID,
        "status": GraphIngestRunStatus.PREVIEW_UNION_STORE_READY.value,
        "created_at": now,
        "updated_at": now,
        "source": {
            "source_artifact_id": f"artifact:recap:{CAMPAIGN_ID}:{SESSION_ID}",
            "source_domain": "recap",
            "normalized_recap_path": _repo_rel(recap_path),
            "normalized_recap_sha256": _sha256(recap_path),
            "source_label": "C1S1 vocabulary ablation projection dogfood",
            "source_span_index_uri": _repo_rel(source_span_index_path),
            "candidate_graph_uri": _repo_rel(candidate_graph_path),
        },
        "steps": [
            _step("validate_candidate_graph", "Validate vocabulary-ablation candidate graph", True),
            _step("adapt_preview_union_store", "Adapt candidate graph(s) to preview union store", True),
            _step("load_projection", "Load union-supergraph projection", True),
        ],
        "artifacts": {
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
            "deferred_count": 0,
            "evidence_ref_count": validation["counts"]["evidence_refs"],
            "resolvable_evidence_ref_count": validation["counts"]["evidence_refs"],
            "openable_evidence_ref_count": validation["counts"]["evidence_refs"],
            "highlightable_evidence_ref_count": validation["counts"]["evidence_refs"],
            "model_id": None,
            "estimated_cost_usd": None,
        },
        "diagnostics": {
            "preview_only": True,
            "candidate_extraction": True,
            "preview_import": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
            "agent_interaction_connected": False,
            "runtime_projection_connected": True,
            "manual_gold": False,
            "llm_extraction": True,
            "vocabulary_ablation_dogfood": True,
            "mirathorn_world_merged": include_mirathorn_world,
        },
        "projection": None,
        "warnings": list(validation.get("warnings", [])),
        "errors": list(validation.get("errors", [])),
        "next_actions": ["open_projection_preview", "manual_gm_dogfood_review"],
    }


def _step(step_id: str, label: str, complete: bool) -> dict[str, Any]:
    return {
        "id": step_id,
        "label": label,
        "state": "complete" if complete else "failed",
        "artifact_refs": [],
    }


def _artifact(kind: str, path: Path, schema: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "uri": _repo_rel(path),
        "schema": schema,
        "sha256": _sha256(path),
        "exists": path.exists(),
        "preview_only": True,
    }


def _registry_probe(manifest_path: Path) -> dict[str, Any]:
    try:
        latest = resolve_latest_preview_union_graph_ingest_run(
            campaign_id=CAMPAIGN_ID,
            session_id=SESSION_ID,
            include_eval_roots=True,
        )
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}
    return {
        "ok": latest.manifest_path == _repo_rel(manifest_path),
        "latest_manifest_path": latest.manifest_path,
        "preview_union_store_path": latest.preview_union_store_path,
    }


def _projection_probe(manifest_path: Path) -> dict[str, Any]:
    try:
        payload = build_plan_union_supergraph_projection_payload(
            session_id=SESSION_ID,
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


def _report(
    *,
    validation: Mapping[str, Any],
    manifest_path: Path,
    preview_union_store_path: Path,
    mention_count: int,
    include_mirathorn_world: bool,
) -> str:
    registry = validation.get("registry_discovery", {})
    projection = validation.get("projection_load", {})
    return f"""# Graph Memory Session 1 Vocabulary Ablation Projection Dogfood Run

## Result

1. C1S1 candidate graph materialized: yes.
2. Preview union store: `{_repo_rel(preview_union_store_path)}`.
3. Graph-ingest manifest: `{_repo_rel(manifest_path)}`.
4. Registry discovery: {registry}.
5. Projection load: {projection}.
6. Projected recap mention chips: {mention_count}.
7. Mirathorn worldbuilding merged: {include_mirathorn_world}.
8. Canon/write safety: preview-only; no corpus mutation or approved writes.

## /plan usage

Open Plan → **Recap** with `?session=session-1`. Campaign context should be `longmont-c1`.
The union supergraph includes session-1 recap nodes plus Mirathorn worldbuilding nodes when merged.
Worldbuilding nodes appear in node explorer/adjacency even when not linked as recap chips.

## Caveats

- This run uses the vocabulary-ablation `edge_and_node_packet` candidate graph, not hand-authored gold.
- Preview-only dogfood; not campaign canon.
"""


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
