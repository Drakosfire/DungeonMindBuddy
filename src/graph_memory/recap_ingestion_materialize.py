from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import blake2s
from pathlib import Path
from typing import Any, Sequence

SCHEMA = "dmb_recap_ingestion_source_artifact_materialization_v0"
VERSION = "0.1"
SOURCE_FAMILY = "recap_ingestion_source_artifacts"
CREATED_BY = "recap_ingestion_source_artifact_materializer_v0"
INPUT_MODE = "explicit_paths_only"
REPO_ROOT = Path(__file__).resolve().parents[2]
FAMILY_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_family_gate.json"
MATERIALIZER_GATE_PATH = REPO_ROOT / "evals" / "graph_memory_layer" / "recap_ingestion_source_artifact_materializer_gate.json"

ANCHOR_UNIT_KIND = {
    "normalized_recap_markdown": ("document_anchor", "document_source_unit", "Synthetic normalized recap source artifact."),
    "breadcrumbed_recap_markdown": ("breadcrumb_reference_anchor", "navigation_reference_source_unit", "Synthetic breadcrumbed recap navigation artifact."),
    "frontmatter_seed_markdown": ("frontmatter_field_anchor", "candidate_seed_source_unit", "Synthetic frontmatter seed diagnostic artifact."),
    "session_memory_jsonl_meta": ("metadata_anchor", "diagnostic_source_unit", "Synthetic session memory metadata diagnostic artifact."),
    "corpus_impact_proof": ("proof_anchor", "diagnostic_proof_source_unit", "Synthetic corpus impact proof diagnostic artifact."),
}


@dataclass(frozen=True)
class RecapIngestionMaterializerInput:
    admitted_artifact_id: str
    path: Path


@dataclass(frozen=True)
class RecapIngestionSourceArtifact:
    artifact_id: str
    admitted_artifact_id: str
    artifact_kind: str
    source_layer: str
    label: str
    canon_state: str
    lifecycle_state: str
    evidence_role: str
    authority_state: str
    visibility_state: str
    locator: dict[str, object]


@dataclass(frozen=True)
class RecapIngestionSourceAnchor:
    source_anchor_id: str
    source_artifact_id: str
    anchor_kind: str
    label: str
    locator: dict[str, object]


@dataclass(frozen=True)
class RecapIngestionSourceUnit:
    source_unit_id: str
    source_artifact_id: str
    source_anchor_id: str
    unit_kind: str
    label: str
    display_summary: str
    source_ref: dict[str, object]
    provenance: tuple[dict[str, object], ...]
    canon_state: str
    lifecycle_state: str
    evidence_role: str
    authority_state: str
    visibility_state: str
    diagnostics: dict[str, object]


@dataclass(frozen=True)
class RecapIngestionMaterialization:
    schema: str
    version: str
    source_family: str
    created_by: str
    input_mode: str
    artifacts: tuple[RecapIngestionSourceArtifact, ...]
    anchors: tuple[RecapIngestionSourceAnchor, ...]
    units: tuple[RecapIngestionSourceUnit, ...]
    diagnostics: tuple[dict[str, object], ...]


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return data


def _gate_artifacts() -> dict[str, dict[str, Any]]:
    family = _load_json(FAMILY_GATE_PATH)
    gate = _load_json(MATERIALIZER_GATE_PATH)
    if family.get("source_family") != SOURCE_FAMILY or gate.get("source_family") != SOURCE_FAMILY:
        raise ValueError("recap-ingestion source family gate mismatch")
    family_by_id = {item["id"]: item for item in family.get("admitted_artifacts", [])}
    allowed: dict[str, dict[str, Any]] = {}
    for item in gate.get("allowed_input_artifacts", []):
        artifact_id = item.get("admitted_artifact_id")
        if artifact_id not in family_by_id:
            raise ValueError(f"materializer gate artifact is not family-admitted: {artifact_id}")
        merged = dict(family_by_id[artifact_id])
        merged.update(item)
        allowed[artifact_id] = merged
    return allowed


def _safe_id(prefix: str, admitted_artifact_id: str, path: Path) -> str:
    digest = blake2s(f"{admitted_artifact_id}|{path.name}".encode("utf-8"), digest_size=8).hexdigest()
    return f"{prefix}:{admitted_artifact_id}:{digest}"


def _locator(admitted_artifact_id: str, path: Path, fragment: str | None = None) -> dict[str, object]:
    value = f"explicit-input://recap-ingestion/{admitted_artifact_id}/{path.name}"
    if fragment:
        value = f"{value}#{fragment}"
    return {"scheme": "explicit-input", "value": value, "admitted_artifact_id": admitted_artifact_id, "file_name": path.name}


def _first_heading_or_key(path: Path, admitted_artifact_id: str) -> str | None:
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".md", ".markdown"}:
        for line in text.splitlines()[:20]:
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()[:80]
        if admitted_artifact_id == "frontmatter_seed_markdown" and text.startswith("---"):
            return "frontmatter"
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(data, dict) and data:
        return sorted(str(key) for key in data.keys())[0][:80]
    return None


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def materialize_recap_ingestion_source_artifacts(
    inputs: Sequence[RecapIngestionMaterializerInput],
) -> RecapIngestionMaterialization:
    if not inputs:
        raise ValueError("recap-ingestion materializer requires at least one explicit input")
    allowed = _gate_artifacts()
    seen: set[str] = set()
    artifacts: list[RecapIngestionSourceArtifact] = []
    anchors: list[RecapIngestionSourceAnchor] = []
    units: list[RecapIngestionSourceUnit] = []
    diagnostics: list[dict[str, object]] = []

    for explicit_input in inputs:
        admitted_id = explicit_input.admitted_artifact_id
        path = explicit_input.path
        if admitted_id not in allowed:
            raise ValueError(f"unknown or unadmitted recap-ingestion artifact id: {admitted_id}")
        if admitted_id in seen:
            raise ValueError(f"duplicate recap-ingestion artifact id is not supported: {admitted_id}")
        seen.add(admitted_id)
        if path is None:
            raise ValueError(f"missing explicit path for {admitted_id}")
        if path.is_dir():
            raise ValueError(f"directory input is forbidden for {admitted_id}")
        if not path.is_file():
            raise ValueError(f"explicit input path is not a file for {admitted_id}")
        gate = allowed[admitted_id]
        if gate.get("input_contract") != "explicit_file_path":
            raise ValueError(f"unsupported artifact input contract for {admitted_id}")
        anchor_kind, unit_kind, summary = ANCHOR_UNIT_KIND[admitted_id]
        artifact_id = _safe_id("source-artifact", admitted_id, path)
        anchor_id = _safe_id("source-anchor", admitted_id, path)
        unit_id = _safe_id("source-unit", admitted_id, path)
        heading = _first_heading_or_key(path, admitted_id)
        artifact_locator = _locator(admitted_id, path)
        artifact = RecapIngestionSourceArtifact(
            artifact_id=artifact_id,
            admitted_artifact_id=admitted_id,
            artifact_kind=str(gate["artifact_kind"]),
            source_layer=str(gate["source_layer"]),
            label=f"{gate['artifact_kind']} explicit input",
            canon_state=str(gate["default_canon_state"]),
            lifecycle_state=str(gate["default_lifecycle_state"]),
            evidence_role=str(gate["default_evidence_role"]),
            authority_state=str(gate["default_authority_state"]),
            visibility_state=str(gate["default_visibility_state"]),
            locator=artifact_locator,
        )
        anchor = RecapIngestionSourceAnchor(
            source_anchor_id=anchor_id,
            source_artifact_id=artifact_id,
            anchor_kind=anchor_kind,
            label=heading or f"{gate['artifact_kind']} anchor",
            locator=_locator(admitted_id, path, anchor_kind),
        )
        unit = RecapIngestionSourceUnit(
            source_unit_id=unit_id,
            source_artifact_id=artifact_id,
            source_anchor_id=anchor_id,
            unit_kind=unit_kind,
            label=f"{gate['artifact_kind']} source unit",
            display_summary=summary,
            source_ref={"source_artifact_id": artifact_id, "source_anchor_id": anchor_id, "locator": anchor.locator},
            provenance=({"created_by": CREATED_BY, "input_mode": INPUT_MODE, "admitted_artifact_id": admitted_id},),
            canon_state=artifact.canon_state,
            lifecycle_state=artifact.lifecycle_state,
            evidence_role=artifact.evidence_role,
            authority_state=artifact.authority_state,
            visibility_state=artifact.visibility_state,
            diagnostics={"file_name": path.name, "line_count": _line_count(path), "display_summary_is_evidence": False},
        )
        artifacts.append(artifact)
        anchors.append(anchor)
        units.append(unit)
        diagnostics.append({"admitted_artifact_id": admitted_id, "status": "materialized", "file_name": path.name})

    return RecapIngestionMaterialization(SCHEMA, VERSION, SOURCE_FAMILY, CREATED_BY, INPUT_MODE, tuple(artifacts), tuple(anchors), tuple(units), tuple(diagnostics))


def recap_ingestion_materialization_to_dict(materialization: RecapIngestionMaterialization) -> dict[str, object]:
    return asdict(materialization)


def render_recap_ingestion_materialization_report(materialization: RecapIngestionMaterialization) -> str:
    unit_counts = {artifact.artifact_id: 0 for artifact in materialization.artifacts}
    for unit in materialization.units:
        unit_counts[unit.source_artifact_id] = unit_counts.get(unit.source_artifact_id, 0) + 1
    lines = [
        "# Recap-Ingestion Source Artifact Materializer Report",
        "",
        "## Summary",
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Input artifacts | {len(materialization.artifacts)} |",
        f"| Source artifacts | {len(materialization.artifacts)} |",
        f"| Source anchors | {len(materialization.anchors)} |",
        f"| Source units | {len(materialization.units)} |",
        f"| Diagnostics | {len(materialization.diagnostics)} |",
        "",
        "## Artifact Counts",
        "",
        "| Admitted Artifact | Artifact Kind | Units | Evidence Role | Canon State | Lifecycle |",
        "|---|---|---:|---|---|---|",
    ]
    for artifact in materialization.artifacts:
        lines.append(f"| {artifact.admitted_artifact_id} | {artifact.artifact_kind} | {unit_counts[artifact.artifact_id]} | {artifact.evidence_role} | {artifact.canon_state} | {artifact.lifecycle_state} |")
    lines.extend(["", "## Diagnostics", ""])
    for diagnostic in materialization.diagnostics:
        lines.append(f"- {diagnostic['admitted_artifact_id']}: {diagnostic['status']}")
    lines.extend(["", "`display_summary` is not evidence.", "The output is not a production surface adapter contract."])
    return "\n".join(lines) + "\n"
