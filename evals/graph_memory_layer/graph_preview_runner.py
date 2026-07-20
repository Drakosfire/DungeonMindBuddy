from __future__ import annotations

import hashlib
import json
import logging
import re
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from src.graph_memory.extraction.category_candidate_graph_extractor import (
    CategoryGraphExtractionError,
    CategoryGraphExtractionOptions,
    CategoryGraphPassClient,
    FixtureCategoryGraphPassClient,
    OpenAICategoryGraphPassClient,
    PASS_PROGRESS_LABELS,
    extract_category_candidate_graph,
    resolve_category_graph_model,
)
from src.graph_memory.vocabulary.model import ContextVocabularyPacket

from graph_memory.ingestion import (
    GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
    GRAPH_INGEST_RUN_MANIFEST_VERSION,
    GraphIngestArtifactKind,
    GraphIngestArtifactRef,
    GraphIngestDiagnostics,
    GraphIngestHealth,
    GraphIngestRunManifest,
    GraphIngestRunStatus,
    GraphIngestSource,
    GraphIngestStepState,
    GraphIngestStepStatus,
)

ComparisonMode = Literal["none", "gold_if_available", "required_gold"]
GraphExtractionProfile = Literal[
    "current_default",
    "category_baseline",
    "category_encounter_job_preview",
]

_GRAPH_EXTRACTION_PROFILE_OPTIONS: dict[GraphExtractionProfile, dict[str, bool]] = {
    "current_default": {
        "enable_encounter_job_pass": False,
        "enable_party_participation_attachment": False,
        "enable_encounter_job_edge_guidance": False,
        "enable_dynamic_node_vocabulary_packet": False,
    },
    "category_baseline": {
        "enable_encounter_job_pass": False,
        "enable_party_participation_attachment": False,
        "enable_encounter_job_edge_guidance": False,
        "enable_dynamic_node_vocabulary_packet": False,
    },
    "category_encounter_job_preview": {
        "enable_encounter_job_pass": True,
        "enable_party_participation_attachment": True,
        "enable_encounter_job_edge_guidance": True,
        "enable_dynamic_node_vocabulary_packet": False,
    },
}
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GraphPreviewRunnerOptions:
    campaign_id: str
    session_id: str
    normalized_recap_path: Path
    output_dir: Path
    source_label: str | None = None
    model_id: str | None = None
    reasoning_effort: str | None = None
    allow_llm: bool = False
    comparison_mode: ComparisonMode = "none"
    gold_path: Path | None = None
    source_domain: str = "recap"
    run_id: str | None = None
    candidate_graph_path: Path | None = None
    category_client: CategoryGraphPassClient | None = None
    input_path_record: str | None = None
    graph_extraction_profile: GraphExtractionProfile | str | None = None
    context_vocabulary_packet: ContextVocabularyPacket | None = None
    enable_node_vocabulary_packet: bool = False
    enable_edge_vocabulary_packet: bool = False


@dataclass(frozen=True)
class GraphPreviewRunnerResult:
    manifest_path: Path
    candidate_graph_path: Path | None
    validation_report_path: Path | None
    source_span_bundle_dir: Path | None
    output_dir: Path
    status: GraphIngestRunStatus


@dataclass(frozen=True)
class CandidateValidationResult:
    path: Path
    valid: bool
    errors: list[str]
    warnings: list[str]


def normalize_graph_extraction_profile(value: str | None) -> GraphExtractionProfile:
    if value is None:
        return "current_default"
    if value in _GRAPH_EXTRACTION_PROFILE_OPTIONS:
        return value  # type: ignore[return-value]
    raise ValueError(f"unsupported graph_extraction_profile: {value}")


def graph_extraction_profile_options(profile: GraphExtractionProfile) -> dict[str, bool]:
    return dict(_GRAPH_EXTRACTION_PROFILE_OPTIONS[profile])


def category_options_for_graph_extraction_profile(
    *,
    profile: GraphExtractionProfile,
    campaign_id: str,
    session_id: str,
    session_number: int,
    source_span_index: dict[str, Any],
    model_id: str,
    context_vocabulary_packet: ContextVocabularyPacket | None = None,
    enable_node_vocabulary_packet: bool = False,
    enable_edge_vocabulary_packet: bool = False,
) -> tuple[CategoryGraphExtractionOptions, dict[str, Any]]:
    profile_options = graph_extraction_profile_options(profile)
    # Independent of the profile's own `enable_dynamic_node_vocabulary_packet` flag
    # (a separate, session-graph-derived vocabulary feature): this is the static,
    # corpus/registry-derived context vocabulary packet used by the vocabulary
    # ablation dogfood, opt-in here so any profile can be run with or without it.
    enable_node_vocabulary_packet = enable_node_vocabulary_packet and context_vocabulary_packet is not None
    enable_edge_vocabulary_packet = enable_edge_vocabulary_packet and context_vocabulary_packet is not None
    return (
        CategoryGraphExtractionOptions(
            campaign_id=campaign_id,
            session_id=session_id,
            session_number=session_number,
            source_span_index=source_span_index,
            model_id=model_id,
            enable_node_vocabulary_packet=enable_node_vocabulary_packet,
            node_vocabulary_packet=context_vocabulary_packet if enable_node_vocabulary_packet else None,
            enable_edge_vocabulary_packet=enable_edge_vocabulary_packet,
            edge_vocabulary_packet=context_vocabulary_packet if enable_edge_vocabulary_packet else None,
            **profile_options,
        ),
        {
            "graph_extraction_profile": profile,
            "graph_extraction_profile_options": profile_options,
            "context_vocabulary_packet_id": context_vocabulary_packet.packet_id if context_vocabulary_packet else None,
            "enable_node_vocabulary_packet": enable_node_vocabulary_packet,
            "enable_edge_vocabulary_packet": enable_edge_vocabulary_packet,
        },
    )

def compute_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _repo_root() -> Path:
    # TODO: add an explicit repo_root option before wiring this runner into runtime/API paths.
    return Path.cwd().resolve()


def _validate_safe_relative_path(path: Path, *, field_name: str) -> None:
    if path.is_absolute():
        raise ValueError(f"{field_name} must be repo-relative, not absolute: {path}")
    if ".." in PurePosixPath(path.as_posix()).parts:
        raise ValueError(f"{field_name} must not contain path traversal: {path}")


def safe_relative_artifact_uri(path: Path, repo_root: Path | None = None) -> str:
    root = (repo_root or _repo_root()).resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"artifact path is outside repository root: {path}") from exc
    _validate_safe_relative_path(relative, field_name="artifact uri")
    return relative.as_posix()


def ensure_output_dir(path: Path) -> Path:
    _validate_safe_relative_path(path, field_name="output_dir")
    output_dir = (_repo_root() / path).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def _now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    if not slug:
        raise ValueError("campaign_id and session_id must not be blank")
    return slug


def _copy_source_recap(source: Path, output_dir: Path) -> Path:
    target = output_dir / "normalized_recap_source.md"
    if source.resolve() != target.resolve():
        shutil.copyfile(source, target)
    return target



def _line_number_at(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _split_recap_paragraph_spans(recap_text: str) -> list[dict[str, Any]]:
    spans: list[dict[str, Any]] = []
    # The lookahead must accept the *actual* end of the paragraph even when the
    # source file ends with a single trailing newline (the normal case for any
    # saved Markdown file) — `\Z` alone only matches with zero trailing chars,
    # so a lone trailing "\n" silently swallowed the final paragraph. `\s*\Z`
    # allows any trailing whitespace before end-of-string.
    for match in re.finditer(r"\S(?:.*?\S)?(?=\n\s*\n|\s*\Z)", recap_text, flags=re.DOTALL):
        paragraph = match.group(0).strip("\n")
        if not paragraph.strip():
            continue
        start = match.start() + (len(match.group(0)) - len(match.group(0).lstrip("\n")))
        end = start + len(paragraph)
        spans.append(
            {
                "ordinal": len(spans) + 1,
                "text": paragraph,
                "char_start": start,
                "char_end": end,
                "line_start": _line_number_at(recap_text, start),
                "line_end": _line_number_at(recap_text, max(start, end - 1)),
            }
        )
    return spans

def _write_source_span_bundle(
    *,
    recap_text: str,
    output_dir: Path,
    campaign_id: str,
    session_id: str,
    source_uri: str,
    source_sha256: str,
) -> tuple[Path, Path, Path, int]:
    source_spans_dir = output_dir / "source_spans"
    source_spans_dir.mkdir(parents=True, exist_ok=True)
    source_span_path = source_spans_dir / "recap_full_text.md"
    source_span_path.write_text(recap_text)
    source_artifact_id = f"artifact:recap:{campaign_id}:{session_id}"

    spans: list[dict[str, Any]] = [
        {
            "span_id": f"{session_id}:recap:full_text",
            "source_span_ref_id": f"{session_id}:recap:full_text",
            "source_artifact_id": source_artifact_id,
            "kind": "full_text",
            "ordinal": 0,
            "source_uri": source_uri,
            "local_uri": safe_relative_artifact_uri(source_span_path),
            "char_start": 0,
            "char_end": len(recap_text),
            "line_start": 1,
            "line_end": max(1, len(recap_text.splitlines())),
            "text_excerpt": recap_text[:240],
            "preview_only": True,
        }
    ]
    for paragraph in _split_recap_paragraph_spans(recap_text):
        paragraph_path = source_spans_dir / f"recap_paragraph_{paragraph['ordinal']:03d}.md"
        paragraph_path.write_text(str(paragraph["text"]))
        spans.append(
            {
                "span_id": f"{session_id}:recap:paragraph:{paragraph['ordinal']:03d}",
                "source_span_ref_id": f"{session_id}:recap:paragraph:{paragraph['ordinal']:03d}",
                "source_artifact_id": source_artifact_id,
                "kind": "paragraph",
                "ordinal": paragraph["ordinal"],
                "source_uri": source_uri,
                "local_uri": safe_relative_artifact_uri(paragraph_path),
                "char_start": paragraph["char_start"],
                "char_end": paragraph["char_end"],
                "line_start": paragraph["line_start"],
                "line_end": paragraph["line_end"],
                "text": paragraph["text"],
                "text_excerpt": str(paragraph["text"])[:240],
                "preview_only": True,
            }
        )

    source_span_index = {
        "schema": "dmb_source_span_index_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_sha256": source_sha256,
        "paragraph_span_count": len(spans) - 1,
        "spans": spans,
    }
    source_span_index_path = output_dir / "source_span_index.json"
    write_json(source_span_index_path, source_span_index)

    provenance_index = {
        "schema": "dmb_source_provenance_index_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "source_artifacts": [
            {
                "artifact_id": source_artifact_id,
                "uri": source_uri,
                "sha256": source_sha256,
                "preview_only": True,
            }
        ],
    }
    provenance_index_path = output_dir / "provenance_index.json"
    write_json(provenance_index_path, provenance_index)
    return source_spans_dir, source_span_index_path, provenance_index_path, len(spans) - 1


def _session_number(session_id: str) -> int:
    match = re.match(r"session-(\d+)", session_id.strip())
    if not match:
        raise ValueError(f"session_id must look like session-N, got {session_id!r}")
    return int(match.group(1))


def _graph_list_fields(candidate_graph: dict[str, Any]) -> tuple[str, str, str]:
    if "nodes" in candidate_graph or "candidate_nodes" not in candidate_graph:
        return "nodes", "edges", "beats"
    return "candidate_nodes", "candidate_edges", "session_beats"


def _candidate_counts(
    candidate_graph: dict[str, Any],
    *,
    known_span_ids: set[str] | None = None,
    paragraph_span_count: int = 0,
) -> GraphIngestHealth:
    nodes_key, edges_key, beats_key = _graph_list_fields(candidate_graph)
    ignored = candidate_graph.get("ignored_items") or candidate_graph.get(
        "ignored_or_deferred_candidates", []
    )
    ignored_count = len(ignored) if isinstance(ignored, list) else 0
    deferred = candidate_graph.get("deferred_items", [])
    deferred_count = len(deferred) if isinstance(deferred, list) else 0
    evidence_ref_count = 0
    resolvable_count = 0
    paragraph_evidence_ref_count = 0
    full_text_fallback_ref_count = 0
    for key in (nodes_key, edges_key, beats_key):
        for obj in candidate_graph.get(key, []) if isinstance(candidate_graph.get(key), list) else []:
            if not isinstance(obj, dict):
                continue
            for ref in obj.get("evidence_refs", []) if isinstance(obj.get("evidence_refs"), list) else []:
                evidence_ref_count += 1
                if isinstance(ref, dict):
                    span_id = ref.get("span_id") or ref.get("source_span_ref_id")
                elif isinstance(ref, str):
                    span_id = ref
                else:
                    continue
                if isinstance(span_id, str) and (known_span_ids is None or span_id in known_span_ids):
                    resolvable_count += 1
                if isinstance(span_id, str) and ":recap:paragraph:" in span_id:
                    paragraph_evidence_ref_count += 1
                if isinstance(span_id, str) and span_id.endswith(":recap:full_text"):
                    full_text_fallback_ref_count += 1
    top_refs = candidate_graph.get("evidence_refs", [])
    if isinstance(top_refs, list):
        evidence_ref_count = max(evidence_ref_count, len(top_refs))
        for ref in top_refs:
            if not isinstance(ref, dict):
                continue
            span_id = ref.get("span_id") or ref.get("source_span_ref_id")
            if isinstance(span_id, str) and (known_span_ids is None or span_id in known_span_ids):
                resolvable_count += 1
            if isinstance(span_id, str) and ":recap:paragraph:" in span_id:
                paragraph_evidence_ref_count += 1
            if isinstance(span_id, str) and span_id.endswith(":recap:full_text"):
                full_text_fallback_ref_count += 1
    return GraphIngestHealth(
        candidate_graph_valid=True,
        node_count=len(candidate_graph.get(nodes_key, []))
        if isinstance(candidate_graph.get(nodes_key), list)
        else 0,
        edge_count=len(candidate_graph.get(edges_key, []))
        if isinstance(candidate_graph.get(edges_key), list)
        else 0,
        beat_count=len(candidate_graph.get(beats_key, []))
        if isinstance(candidate_graph.get(beats_key), list)
        else 0,
        ignored_count=ignored_count,
        deferred_count=deferred_count,
        evidence_ref_count=evidence_ref_count,
        resolvable_evidence_ref_count=resolvable_count if known_span_ids is not None else evidence_ref_count,
        openable_evidence_ref_count=resolvable_count if known_span_ids is not None else evidence_ref_count,
        highlightable_evidence_ref_count=paragraph_evidence_ref_count,
        paragraph_span_count=paragraph_span_count,
        paragraph_evidence_ref_count=paragraph_evidence_ref_count,
        full_text_fallback_ref_count=full_text_fallback_ref_count,
    )


def _write_validation_report(
    *,
    output_dir: Path,
    campaign_id: str,
    session_id: str,
    candidate_graph_path: Path,
    candidate_graph: dict[str, Any],
    source_span_index_path: Path | None = None,
) -> CandidateValidationResult:
    errors: list[str] = []
    warnings: list[str] = []
    if not candidate_graph_path.exists():
        errors.append("candidate graph file does not exist")
    nodes_key, edges_key, beats_key = _graph_list_fields(candidate_graph)
    for field in (nodes_key, edges_key, beats_key):
        if not isinstance(candidate_graph.get(field), list):
            errors.append(f"candidate graph field must be a list: {field}")
    if isinstance(candidate_graph.get("evidence_refs"), list):
        evidence_field = "evidence_refs"
    else:
        evidence_field = None
    has_candidates = bool(candidate_graph.get(nodes_key)) or bool(
        candidate_graph.get(edges_key)
    )
    if has_candidates and evidence_field and not candidate_graph.get(evidence_field):
        warnings.append("candidate graph has candidates but no evidence_refs section")
    known_span_ids: set[str] = set()
    if source_span_index_path is not None and source_span_index_path.exists():
        span_index = json.loads(source_span_index_path.read_text())
        known_span_ids = {
            str(span.get("span_id") or span.get("source_span_ref_id"))
            for span in span_index.get("spans", [])
            if isinstance(span, dict) and (span.get("span_id") or span.get("source_span_ref_id"))
        }
    known_evidence_ids = set()
    for ref in candidate_graph.get("evidence_refs", []) if isinstance(candidate_graph.get("evidence_refs"), list) else []:
        if not isinstance(ref, dict):
            continue
        ref_id = ref.get("id")
        span_id = ref.get("span_id") or ref.get("source_span_ref_id")
        if not isinstance(ref_id, str) or not ref_id:
            warnings.append("evidence ref missing id")
            continue
        known_evidence_ids.add(ref_id)
        if not isinstance(span_id, str) or not span_id:
            warnings.append(f"evidence ref {ref_id} missing span_id")
        elif known_span_ids and span_id not in known_span_ids:
            warnings.append(f"unresolved evidence ref span_id: {span_id}")
    for field in (nodes_key, edges_key, beats_key):
        for obj in candidate_graph.get(field, []) if isinstance(candidate_graph.get(field), list) else []:
            if not isinstance(obj, dict):
                continue
            refs = obj.get("evidence_refs", [])
            obj_id = obj.get("node_id") or obj.get("id") or obj.get("edge_id") or obj.get("summary") or field
            if isinstance(refs, list):
                for ref in refs:
                    if isinstance(ref, str) and known_evidence_ids and ref not in known_evidence_ids:
                        warnings.append(
                            f"candidate {field} {obj_id} references unknown evidence ref: {ref}"
                        )
                    if isinstance(ref, dict):
                        spref = ref.get("span_id") or ref.get("source_span_ref_id")
                        if known_span_ids and isinstance(spref, str) and spref not in known_span_ids:
                            warnings.append(f"unresolved evidence ref span_id: {spref}")
                        if spref and ":recap:paragraph:" not in str(spref):
                            warnings.append(f"candidate {field} {obj_id} has no paragraph-level evidence")
    diagnostics = candidate_graph.get("diagnostics", {})
    for flag in (
        "canon_promotion",
        "approved_memory_write",
        "corpus_mutation",
        "production_retrieval",
        # Typed PreviewDiagnostics dangerous flags (promote IR).
        "extraction_performed",
        "llm_used",
        "runtime_connected",
        "plan_connected",
        "agent_interaction_connected",
        "corpus_scanned",
        "corpus_mutated",
        "facts_promoted",
        "canon_promoted",
    ):
        if isinstance(diagnostics, dict) and diagnostics.get(flag):
            errors.append(f"forbidden lifecycle flag is true: {flag}")
    report = {
        "schema": "dmb_candidate_graph_validation_report_v0",
        "version": "0.1",
        "campaign_id": campaign_id,
        "session_id": session_id,
        "candidate_graph_path": safe_relative_artifact_uri(candidate_graph_path),
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "diagnostics": {
            "evidence_ref_count": len(candidate_graph.get("evidence_refs", [])) if isinstance(candidate_graph.get("evidence_refs"), list) else 0,
            "resolvable_evidence_ref_count": sum(1 for ref in candidate_graph.get("evidence_refs", []) if isinstance(ref, dict) and (not known_span_ids or (ref.get("span_id") or ref.get("source_span_ref_id")) in known_span_ids)),
            "paragraph_evidence_ref_count": sum(1 for ref in candidate_graph.get("evidence_refs", []) if isinstance(ref, dict) and ":recap:paragraph:" in str(ref.get("span_id") or ref.get("source_span_ref_id") or "")),
            "full_text_fallback_ref_count": sum(1 for ref in candidate_graph.get("evidence_refs", []) if isinstance(ref, dict) and str(ref.get("span_id") or ref.get("source_span_ref_id") or "").endswith(":recap:full_text")),
            "preview_only": True,
            "canon_promotion": False,
            "approved_memory_write": False,
            "corpus_mutation": False,
            "production_retrieval": False,
        },
    }
    report_path = output_dir / "candidate_validation_report.json"
    write_json(report_path, report)
    return CandidateValidationResult(
        path=report_path,
        valid=not errors,
        errors=errors,
        warnings=warnings,
    )


def _artifact(
    kind: GraphIngestArtifactKind,
    path: Path,
    schema: str | None = None,
    sha256: str | None = None,
) -> GraphIngestArtifactRef:
    return GraphIngestArtifactRef(
        kind=kind,
        uri=safe_relative_artifact_uri(path),
        schema=schema,
        sha256=sha256,
        exists=path.exists(),
        preview_only=True,
    )


def run_graph_preview_extraction(
    options: GraphPreviewRunnerOptions,
) -> GraphPreviewRunnerResult:
    profile = normalize_graph_extraction_profile(options.graph_extraction_profile)
    profile_option_diagnostics = graph_extraction_profile_options(profile)
    vocabulary_option_diagnostics: dict[str, Any] = {
        "context_vocabulary_packet_id": None,
        "enable_node_vocabulary_packet": False,
        "enable_edge_vocabulary_packet": False,
    }
    campaign_id = _slug(options.campaign_id)
    session_id = _slug(options.session_id)
    if options.comparison_mode not in ("none", "gold_if_available", "required_gold"):
        raise ValueError(f"unsupported comparison_mode: {options.comparison_mode}")
    if options.comparison_mode == "required_gold" and (
        options.gold_path is None or not options.gold_path.exists()
    ):
        raise FileNotFoundError("required_gold mode requires an existing gold_path")
    normalized_recap_path = options.normalized_recap_path
    if not normalized_recap_path.exists():
        raise FileNotFoundError(
            f"normalized recap does not exist: {normalized_recap_path}"
        )

    output_dir = ensure_output_dir(options.output_dir)
    recap_text = normalized_recap_path.read_text()
    recap_sha256 = compute_sha256(normalized_recap_path)
    copied_recap_path = _copy_source_recap(normalized_recap_path, output_dir)
    copied_recap_sha256 = compute_sha256(copied_recap_path)
    source_uri = safe_relative_artifact_uri(copied_recap_path)
    source_spans_dir, source_span_index_path, provenance_index_path, paragraph_span_count = (
        _write_source_span_bundle(
            recap_text=recap_text,
            output_dir=output_dir,
            campaign_id=campaign_id,
            session_id=session_id,
            source_uri=source_uri,
            source_sha256=recap_sha256,
        )
    )

    artifacts: dict[str, GraphIngestArtifactRef] = {
        "normalized_recap": _artifact(
            GraphIngestArtifactKind.NORMALIZED_RECAP,
            copied_recap_path,
            "dmb_normalized_recap_v0",
            copied_recap_sha256,
        ),
        "source_span_bundle": _artifact(
            GraphIngestArtifactKind.SOURCE_SPAN_BUNDLE,
            source_spans_dir,
            "dmb_source_span_bundle_v0",
        ),
        "source_span_index": _artifact(
            GraphIngestArtifactKind.SOURCE_SPAN_INDEX,
            source_span_index_path,
            "dmb_source_span_index_v0",
        ),
        "provenance_index": _artifact(
            GraphIngestArtifactKind.PROVENANCE_INDEX,
            provenance_index_path,
            "dmb_source_provenance_index_v0",
        ),
    }
    status = GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
    candidate_graph_path: Path | None = None
    validation_report_path: Path | None = None
    health = GraphIngestHealth(paragraph_span_count=paragraph_span_count)
    candidate_extraction = False
    extraction_mode = "none"
    manifest_errors: list[str] = []
    next_actions = ["extract_candidate_graph"]
    candidate_validation_state = GraphIngestStepState.COMPLETE
    extraction_summary = "Existing candidate graph artifact wrapped for preview ingestion."
    raw_model_response_path: Path | None = None
    category_pass_steps: list[GraphIngestStepStatus] = []

    if options.candidate_graph_path is not None:
        if not options.candidate_graph_path.exists():
            raise FileNotFoundError(
                f"candidate graph does not exist: {options.candidate_graph_path}"
            )
        candidate_graph = json.loads(options.candidate_graph_path.read_text())
        candidate_graph_path = output_dir / "candidate_graph.json"
        write_json(candidate_graph_path, candidate_graph)
        validation = _write_validation_report(
            output_dir=output_dir,
            campaign_id=campaign_id,
            session_id=session_id,
            candidate_graph_path=candidate_graph_path,
            candidate_graph=candidate_graph,
            source_span_index_path=source_span_index_path,
        )
        validation_report_path = validation.path
        artifacts["candidate_graph"] = _artifact(
            GraphIngestArtifactKind.CANDIDATE_GRAPH,
            candidate_graph_path,
            "dmb_candidate_graph_preview_ir_v0",
        )
        artifacts["candidate_validation_report"] = _artifact(
            GraphIngestArtifactKind.CANDIDATE_VALIDATION_REPORT,
            validation_report_path,
            "dmb_candidate_graph_validation_report_v0",
        )
        known_span_ids = {str(sp.get("span_id") or sp.get("source_span_ref_id")) for sp in json.loads(source_span_index_path.read_text()).get("spans", []) if isinstance(sp, dict)}
        health = _candidate_counts(candidate_graph, known_span_ids=known_span_ids, paragraph_span_count=paragraph_span_count)
        candidate_extraction = True
        extraction_mode = "fixture"
        if validation.valid:
            status = GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
            health.candidate_graph_valid = True
            next_actions = ["materialize_preview_union_store"]
        else:
            status = GraphIngestRunStatus.FAILED
            health.candidate_graph_valid = False
            manifest_errors = validation.errors
            next_actions = ["fix_candidate_graph"]
            candidate_validation_state = GraphIngestStepState.FAILED

    elif options.allow_llm:
        model_id = resolve_category_graph_model(options.model_id)
        span_index = json.loads(source_span_index_path.read_text())
        session_number = _session_number(session_id)
        logger.info(
            "category graph extraction starting campaign=%s session=%s model_id=%s "
            "paragraph_span_count=%s output_dir=%s",
            campaign_id,
            session_id,
            model_id,
            paragraph_span_count,
            safe_relative_artifact_uri(output_dir),
        )
        try:
            # Promote-IR slice: do not pass reasoning_effort — OpenAICategoryGraphPassClient
            # on this branch has no such constructor arg (fat-tip contract stays out of scope).
            category_client = options.category_client or OpenAICategoryGraphPassClient()

            def _progress(pass_name: str, state: str) -> None:
                label = PASS_PROGRESS_LABELS.get(pass_name, pass_name)
                category_pass_steps.append(
                    GraphIngestStepStatus(
                        id=f"extract_{pass_name}",
                        label=label,
                        state=GraphIngestStepState.RUNNING
                        if state == "running"
                        else GraphIngestStepState.COMPLETE,
                        summary=f"{label} ({state})",
                    )
                )

            extraction_options, profile_diagnostics = category_options_for_graph_extraction_profile(
                profile=profile,
                campaign_id=campaign_id,
                session_id=session_id,
                session_number=session_number,
                source_span_index=span_index,
                model_id=model_id,
                context_vocabulary_packet=options.context_vocabulary_packet,
                enable_node_vocabulary_packet=options.enable_node_vocabulary_packet,
                enable_edge_vocabulary_packet=options.enable_edge_vocabulary_packet,
            )
            profile_option_diagnostics = dict(profile_diagnostics["graph_extraction_profile_options"])
            vocabulary_option_diagnostics = {
                "context_vocabulary_packet_id": profile_diagnostics["context_vocabulary_packet_id"],
                "enable_node_vocabulary_packet": profile_diagnostics["enable_node_vocabulary_packet"],
                "enable_edge_vocabulary_packet": profile_diagnostics["enable_edge_vocabulary_packet"],
            }
            extraction = extract_category_candidate_graph(
                extraction_options,
                client=category_client,
                progress_callback=_progress,
            )
            candidate_graph = extraction.candidate_graph
            candidate_graph_path = output_dir / "candidate_graph.json"
            write_json(candidate_graph_path, candidate_graph)
            pass_outputs_path = output_dir / "pass_outputs.json"
            write_json(pass_outputs_path, extraction.pass_outputs)
            pass_telemetry_path = output_dir / "pass_telemetry.json"
            write_json(pass_telemetry_path, extraction.pass_telemetry)
            consolidation_path = output_dir / "consolidation_diagnostics.json"
            write_json(consolidation_path, extraction.consolidation_diagnostics)
            validation = _write_validation_report(
                output_dir=output_dir,
                campaign_id=campaign_id,
                session_id=session_id,
                candidate_graph_path=candidate_graph_path,
                candidate_graph=candidate_graph,
                source_span_index_path=source_span_index_path,
            )
            validation_report_path = validation.path
            artifacts["candidate_graph"] = _artifact(
                GraphIngestArtifactKind.CANDIDATE_GRAPH,
                candidate_graph_path,
                "dmb_candidate_graph_preview_v0",
            )
            artifacts["candidate_validation_report"] = _artifact(
                GraphIngestArtifactKind.CANDIDATE_VALIDATION_REPORT,
                validation_report_path,
                "dmb_candidate_graph_validation_report_v0",
            )
            artifacts["pass_outputs"] = _artifact(
                GraphIngestArtifactKind.PASS_TELEMETRY,
                pass_outputs_path,
                "dmb_category_graph_pass_outputs_v0",
            )
            artifacts["pass_telemetry"] = _artifact(
                GraphIngestArtifactKind.PASS_TELEMETRY,
                pass_telemetry_path,
                "dmb_category_graph_pass_telemetry_v0",
            )
            artifacts["consolidation_diagnostics"] = _artifact(
                GraphIngestArtifactKind.PASS_TELEMETRY,
                consolidation_path,
                "dmb_category_graph_consolidation_diagnostics_v0",
            )
            known_span_ids = {
                str(sp.get("span_id") or sp.get("source_span_ref_id"))
                for sp in span_index.get("spans", [])
                if isinstance(sp, dict) and (sp.get("span_id") or sp.get("source_span_ref_id"))
            }
            health = _candidate_counts(
                candidate_graph,
                known_span_ids=known_span_ids,
                paragraph_span_count=paragraph_span_count,
            )
            health.model_id = extraction.model_id
            health.estimated_cost_usd = extraction.total_cost_usd
            candidate_extraction = True
            extraction_mode = "category_decomposed"
            extraction_summary = (
                "Category-decomposed candidate graph extracted "
                f"({len(extraction.pass_outputs)} passes, model {extraction.model_id})."
            )
            logger.info(
                "category graph extraction finished campaign=%s session=%s model_id=%s "
                "nodes=%s edges=%s beats=%s validation_valid=%s candidate_graph_path=%s",
                campaign_id,
                session_id,
                model_id,
                health.node_count,
                health.edge_count,
                health.beat_count,
                validation.valid,
                safe_relative_artifact_uri(candidate_graph_path),
            )
            if validation.valid:
                status = GraphIngestRunStatus.CANDIDATE_VALIDATION_READY
                health.candidate_graph_valid = True
                next_actions = ["materialize_preview_union_store"]
            else:
                status = GraphIngestRunStatus.FAILED
                health.candidate_graph_valid = False
                manifest_errors = validation.errors
                next_actions = ["fix_candidate_graph"]
                candidate_validation_state = GraphIngestStepState.FAILED
                logger.warning(
                    "category graph validation failed campaign=%s session=%s model_id=%s errors=%s warnings=%s",
                    campaign_id,
                    session_id,
                    model_id,
                    validation.errors,
                    validation.warnings,
                )
        except Exception as exc:
            status = GraphIngestRunStatus.SOURCE_SPAN_BUNDLE_READY
            health.candidate_graph_valid = False
            candidate_extraction = True
            extraction_mode = "llm_blocked"
            health.model_id = resolve_category_graph_model(options.model_id)
            manifest_errors = [str(exc)]
            next_actions = ["configure model", "supply candidate_graph_path"]
            candidate_validation_state = GraphIngestStepState.FAILED
            extraction_summary = f"Category graph extraction blocked: {exc}"
            if isinstance(exc, CategoryGraphExtractionError) and exc.raw_model_response:
                raw_model_response_path = output_dir / "raw_model_response.txt"
                raw_model_response_path.write_text(exc.raw_model_response)
                artifacts["raw_model_response"] = _artifact(
                    GraphIngestArtifactKind.PASS_TELEMETRY,
                    raw_model_response_path,
                    "text/plain",
                )
            logger.warning(
                "category graph extraction blocked campaign=%s session=%s model_id=%s error=%s raw_model_response_path=%s",
                campaign_id,
                session_id,
                health.model_id,
                exc,
                safe_relative_artifact_uri(raw_model_response_path)
                if raw_model_response_path is not None
                else None,
            )

    now = _now_iso()
    run_id = (
        options.run_id
        or f"graph-ingest:{campaign_id}:{session_id}:{now.replace('-', '').replace(':', '')}"
    )
    steps = [
        GraphIngestStepStatus(
            id="stage_or_select_source",
            label="Stage or select source",
            state=GraphIngestStepState.COMPLETE,
            started_at=now,
            completed_at=now,
            summary="Normalized recap source selected for parameterized preview ingestion.",
            artifact_refs=[artifacts["normalized_recap"]],
        ),
        GraphIngestStepStatus(
            id="build_source_span_bundle",
            label="Build source span bundle",
            state=GraphIngestStepState.COMPLETE,
            started_at=now,
            completed_at=now,
            summary="Lightweight source-span bundle generated from the normalized recap.",
            artifact_refs=[
                artifacts["source_span_bundle"],
                artifacts["source_span_index"],
                artifacts["provenance_index"],
            ],
        ),
    ]
    if candidate_graph_path is None:
        steps.append(
            GraphIngestStepStatus(
                id="extract_candidate_graph",
                label="Extract candidate graph",
                state=GraphIngestStepState.SKIPPED,
                summary=(
                    extraction_summary
                    if options.allow_llm
                    else "Skipped because allow_llm is false and no candidate graph fixture was supplied."
                ),
                artifact_refs=[artifacts["raw_model_response"]]
                if "raw_model_response" in artifacts
                else [],
            )
        )
    else:
        extract_artifact_refs = [artifacts["candidate_graph"]]
        for key in ("pass_outputs", "pass_telemetry", "consolidation_diagnostics", "raw_model_response"):
            if key in artifacts:
                extract_artifact_refs.append(artifacts[key])
        steps.extend(category_pass_steps)
        steps.extend(
            [
                GraphIngestStepStatus(
                    id="extract_candidate_graph",
                    label="Extract candidate graph",
                    state=GraphIngestStepState.COMPLETE,
                    started_at=now,
                    completed_at=now,
                    summary=extraction_summary,
                    artifact_refs=extract_artifact_refs,
                ),
                GraphIngestStepStatus(
                    id="validate_candidate_graph",
                    label="Validate candidate graph",
                    state=candidate_validation_state,
                    started_at=now,
                    completed_at=now,
                    summary="Shallow candidate graph validation report written.",
                    artifact_refs=[artifacts["candidate_validation_report"]],
                ),
            ]
        )

    manifest = GraphIngestRunManifest(
        schema=GRAPH_INGEST_RUN_MANIFEST_SCHEMA,
        version=GRAPH_INGEST_RUN_MANIFEST_VERSION,
        run_id=run_id,
        campaign_id=campaign_id,
        session_id=session_id,
        status=status,
        created_at=now,
        updated_at=now,
        source=GraphIngestSource(
            source_artifact_id=f"artifact:recap:{campaign_id}:{session_id}",
            source_domain=options.source_domain,
            input_path_record=options.input_path_record,
            normalized_recap_path=source_uri,
            normalized_recap_sha256=recap_sha256,
            source_label=options.source_label,
            source_span_bundle_uri=artifacts["source_span_bundle"].uri,
            source_span_index_uri=artifacts["source_span_index"].uri,
            provenance_index_uri=artifacts["provenance_index"].uri,
        ),
        steps=steps,
        artifacts=artifacts,
        health=health,
        diagnostics=GraphIngestDiagnostics(
            candidate_extraction=candidate_extraction,
            extraction_mode=extraction_mode,
            graph_extraction_profile=profile,
            graph_extraction_profile_options=profile_option_diagnostics,
            **vocabulary_option_diagnostics,
        ),
        projection=None,
        warnings=[]
        if options.comparison_mode != "gold_if_available"
        or (options.gold_path and options.gold_path.exists())
        else [
            "gold comparison skipped because gold_path was not supplied or does not exist"
        ],
        errors=manifest_errors,
        next_actions=next_actions,
    )
    manifest_path = output_dir / "graph_ingest_run_manifest.json"
    write_json(manifest_path, manifest.model_dump(mode="json", by_alias=True))
    return GraphPreviewRunnerResult(
        manifest_path=manifest_path,
        candidate_graph_path=candidate_graph_path,
        validation_report_path=validation_report_path,
        source_span_bundle_dir=source_spans_dir,
        output_dir=output_dir,
        status=status,
    )
