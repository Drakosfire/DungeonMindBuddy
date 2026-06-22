from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from scripts.build_ingested_corpus_library import build_library


class OpaqueLocator(BaseModel):
    locatorId: str
    scheme: Literal["corpus_path", "artifact_path", "impact_proof", "unknown"]
    value: str
    anchor: str | None = None


class SourceArtifact(BaseModel):
    artifactId: str
    kind: str
    layer: str
    label: str
    campaignId: str | None = None
    sessionId: str | None = None
    sessionNumber: int | None = None
    canonState: str
    lifecycleState: str
    evidenceRole: str
    authorityState: str
    visibilityState: str = "gm_private"
    primaryLocator: OpaqueLocator
    relatedLocators: list[OpaqueLocator] = Field(default_factory=list)
    displaySummary: str | None = None
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)
    producedBy: str = "ingested_corpus_library_adapter"
    producedAt: str | None = None


class SourceAnchor(BaseModel):
    anchorId: str
    artifactId: str
    label: str
    anchorKind: str
    locator: OpaqueLocator
    canonState: str
    lifecycleState: str
    evidenceRole: str
    authorityState: str
    visibilityState: str = "gm_private"
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)


class SourceUnit(BaseModel):
    unitId: str
    artifactId: str
    anchorId: str
    unitKind: str
    label: str
    displaySummary: str | None = None
    fields: dict[str, str | int | bool | None] = Field(default_factory=dict)
    sourceAnchor: SourceAnchor
    canonState: str
    lifecycleState: str
    evidenceRole: str
    authorityState: str
    visibilityState: str = "gm_private"
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class IngestionSourceBundle(BaseModel):
    schema_version: Literal["dmb_ingestion_source_bundle_v1"] = "dmb_ingestion_source_bundle_v1"
    bundle_id: str
    scope: str
    generated_at: str | None
    corpus_root: str
    artifacts: list[SourceArtifact]
    anchors: list[SourceAnchor]
    units: list[SourceUnit]
    coverage: dict[str, Any]
    diagnostics: list[str] = Field(default_factory=list)


_STAGE_KIND = {
    "canon_recap": ("unknown", "raw_source", "recap_document"),
    "normalized": ("normalized_recap", "normalized_source", "recap_document"),
    "breadcrumbed": ("breadcrumbed_recap", "breadcrumb_layer", "recap_document"),
    "frontmatter_seed": ("frontmatter_seed", "breadcrumb_layer", "frontmatter_seed"),
    "session_memory_jsonl": ("session_memory_recordset", "memory_layer", "diagnostic_record"),
    "session_memory_meta": ("session_memory_meta", "memory_layer", "diagnostic_record"),
    "ingest_staging": ("unknown", "raw_source", "diagnostic_record"),
}


def _safe_id(value: str) -> str:
    out = []
    for char in value.lower():
        out.append(char if char.isalnum() else "-")
    return "-".join("".join(out).strip("-").split("-"))[:180] or "unknown"


def _locator_for_route(route: str, *, corpus_root: str) -> OpaqueLocator:
    if route.startswith(f"{corpus_root}/"):
        value = route[len(corpus_root) + 1 :]
        scheme: Literal["corpus_path", "artifact_path", "impact_proof", "unknown"] = "corpus_path"
    elif route.startswith("corpus/"):
        parts = route.split("/", 2)
        value = parts[2] if len(parts) == 3 else route
        scheme = "corpus_path"
    elif route.startswith("evals/") or route.startswith("Docs/"):
        value = route
        scheme = "artifact_path"
    else:
        value = route
        scheme = "corpus_path"
    return OpaqueLocator(locatorId=f"loc-{_safe_id(route)}", scheme=scheme, value=value)


def _authority_for_stage(stage: str) -> tuple[str, str, str, str]:
    if stage == "ingest_staging":
        return ("candidate_extraction", "candidate", "not_evidence", "user_generated")
    if stage in {"canon_recap", "normalized", "breadcrumbed"}:
        return ("played_canon", "ingested", "source_evidence", "played_truth")
    if stage in {"session_memory_jsonl", "session_memory_meta"}:
        return ("played_canon", "indexed", "navigation_hint", "system_derived")
    if stage == "frontmatter_seed":
        return ("candidate_extraction", "candidate", "navigation_hint", "system_derived")
    return ("unknown", "ingested", "diagnostic_only", "unknown")


def _route_in_activation(route: str, routes: set[str], *, corpus_root: str) -> bool:
    return route in routes or f"{corpus_root}/{route}" in routes


def _make_unit(artifact: SourceArtifact, anchor: SourceAnchor, *, stage: str) -> SourceUnit:
    return SourceUnit(
        unitId=f"unit-{artifact.artifactId}",
        artifactId=artifact.artifactId,
        anchorId=anchor.anchorId,
        unitKind=_STAGE_KIND.get(stage, ("unknown", "diagnostic_layer", "diagnostic_record"))[2],
        label=artifact.label,
        displaySummary=artifact.displaySummary,
        fields={
            "campaignId": artifact.campaignId,
            "sessionNumber": artifact.sessionNumber,
            "sourceKind": stage,
            **artifact.metadata,
        },
        sourceAnchor=anchor,
        canonState=artifact.canonState,
        lifecycleState=artifact.lifecycleState,
        evidenceRole=artifact.evidenceRole,
        authorityState=artifact.authorityState,
        visibilityState=artifact.visibilityState,
        provenance=[
            {
                "provenanceId": f"prov-{artifact.artifactId}",
                "artifactId": artifact.artifactId,
                "anchorId": anchor.anchorId,
                "locator": anchor.locator.model_dump(mode="json"),
                "role": artifact.evidenceRole,
            }
        ],
        diagnostics={"sourceFamily": "ingested_corpus_library", "producedBy": artifact.producedBy},
    )


def build_ingestion_source_bundle(
    *,
    root: Path | None = None,
    scope: str = "campaign-ingested",
    campaign_id: str | None = None,
) -> IngestionSourceBundle:
    """Map the ingested corpus library into the SourceUnit contract without reading corpus bodies."""
    repo_root = root or Path(__file__).resolve().parents[2]
    library = build_library(root=repo_root)
    corpus_root = str(library["corpus_root"])
    activation = library.get("retrieval_activation", {})
    slim_routes = set(activation.get("c2s23_planning_manifest", {}).get("routes", []))
    dogfood_routes = set(activation.get("c2s23_dogfood_full_manifest", {}).get("routes", []))

    artifacts: list[SourceArtifact] = []
    anchors: list[SourceAnchor] = []
    units: list[SourceUnit] = []
    tier_counts: Counter[str] = Counter()

    for campaign in library.get("campaigns", []):
        current_campaign = str(campaign.get("campaign_id") or "")
        if campaign_id and current_campaign != campaign_id:
            continue
        for session in campaign.get("sessions", []):
            session_number = int(session.get("session") or 0)
            tier_counts[str(session.get("pipeline_tier") or "unknown")] += 1
            for stage, record in sorted((session.get("stages") or {}).items()):
                if not isinstance(record, dict) or not record.get("exists"):
                    continue
                route = str(record.get("route") or "")
                if not route:
                    continue
                kind, layer, _unit_kind = _STAGE_KIND.get(
                    stage, ("unknown", "diagnostic_layer", "diagnostic_record")
                )
                canon, lifecycle, evidence, authority = _authority_for_stage(stage)
                artifact_id = f"artifact-{_safe_id(current_campaign)}-s{session_number}-{_safe_id(stage)}"
                locator = _locator_for_route(route, corpus_root=corpus_root)
                artifact = SourceArtifact(
                    artifactId=artifact_id,
                    kind=kind,
                    layer=layer,
                    label=f"{current_campaign} Session {session_number}: {stage.replace('_', ' ')}",
                    campaignId=current_campaign,
                    sessionId=f"{current_campaign}:session:{session_number}",
                    sessionNumber=session_number,
                    canonState=canon,
                    lifecycleState=lifecycle,
                    evidenceRole=evidence,
                    authorityState=authority,
                    primaryLocator=locator,
                    displaySummary=(
                        f"{stage.replace('_', ' ').title()} artifact for Session {session_number}; "
                        "locator only, corpus body not embedded."
                    ),
                    metadata={
                        "sizeBytes": record.get("size_bytes"),
                        "activatedInC2S23Slim": _route_in_activation(
                            route, slim_routes, corpus_root=corpus_root
                        ),
                        "activatedInDogfoodFull": _route_in_activation(
                            route, dogfood_routes, corpus_root=corpus_root
                        ),
                    },
                    producedAt=library.get("generated_at"),
                )
                anchor = SourceAnchor(
                    anchorId=f"anchor-{artifact_id}",
                    artifactId=artifact.artifactId,
                    label=artifact.label,
                    anchorKind="document",
                    locator=locator,
                    canonState=artifact.canonState,
                    lifecycleState=artifact.lifecycleState,
                    evidenceRole=artifact.evidenceRole,
                    authorityState=artifact.authorityState,
                    metadata=artifact.metadata,
                )
                artifacts.append(artifact)
                anchors.append(anchor)
                units.append(_make_unit(artifact, anchor, stage=stage))

    manifest_units = [
        _manifest_artifact(
            activation.get("c2s23_planning_manifest", {}),
            manifest_key="c2s23_planning_manifest",
            label="C2S23 slim planning manifest",
            corpus_root=corpus_root,
            generated_at=library.get("generated_at"),
        ),
        _manifest_artifact(
            activation.get("c2s23_dogfood_full_manifest", {}),
            manifest_key="c2s23_dogfood_full_manifest",
            label="C2S23 dogfood-full manifest",
            corpus_root=corpus_root,
            generated_at=library.get("generated_at"),
        ),
    ]
    for artifact, anchor, unit in manifest_units:
        if artifact is None:
            continue
        artifacts.append(artifact)
        anchors.append(anchor)
        units.append(unit)

    return IngestionSourceBundle(
        bundle_id=f"source-bundle-{_safe_id(scope)}",
        scope=scope,
        generated_at=library.get("generated_at"),
        corpus_root=corpus_root,
        artifacts=artifacts,
        anchors=anchors,
        units=units,
        coverage={
            "campaignCount": library.get("summary", {}).get("campaign_count"),
            "totalCorpusMarkdownFiles": library.get("summary", {}).get("total_corpus_md_files"),
            "sessionPipelineTiers": dict(tier_counts),
            "ingestRoutesOnDisk": activation.get("ingest_routes_on_disk"),
            "ingestRoutesInC2S23Manifest": activation.get("ingest_routes_in_c2s23_manifest"),
            "ingestRoutesNotInC2S23Manifest": activation.get("ingest_routes_not_in_c2s23_manifest"),
            "ingestRoutesInDogfoodFullManifest": activation.get("ingest_routes_in_dogfood_full_manifest"),
            "ingestRoutesNotInDogfoodFullManifest": activation.get(
                "ingest_routes_not_in_dogfood_full_manifest"
            ),
            "artifactCount": len(artifacts),
            "unitCount": len(units),
        },
        diagnostics=[
            "read_only_adapter",
            "corpus_bodies_not_embedded",
            "source_units_derived_from_ingested_corpus_library",
        ],
    )


def _manifest_artifact(
    manifest: dict[str, Any],
    *,
    manifest_key: str,
    label: str,
    corpus_root: str,
    generated_at: str | None,
) -> tuple[SourceArtifact | None, SourceAnchor, SourceUnit] | tuple[None, None, None]:
    if not manifest.get("exists"):
        return None, None, None
    route = str(manifest.get("manifest_path") or "")
    locator = _locator_for_route(route, corpus_root=corpus_root)
    artifact_id = f"artifact-{_safe_id(manifest_key)}"
    artifact = SourceArtifact(
        artifactId=artifact_id,
        kind="reference_index",
        layer="reference_layer",
        label=label,
        campaignId="longmont-c2",
        sessionId=f"longmont-c2:planning:{manifest.get('planning_session')}",
        sessionNumber=manifest.get("planning_session"),
        canonState="reference_only",
        lifecycleState="indexed",
        evidenceRole="reference_tool",
        authorityState="system_derived",
        visibilityState="gm_private",
        primaryLocator=locator,
        displaySummary=(
            f"{manifest.get('entry_count')} activated routes; source sessions "
            f"{', '.join(str(v) for v in manifest.get('source_sessions', []))}."
        ),
        metadata={
            "entryCount": manifest.get("entry_count"),
            "sourceSessionCount": len(manifest.get("source_sessions", [])),
        },
        producedAt=generated_at,
    )
    anchor = SourceAnchor(
        anchorId=f"anchor-{artifact_id}",
        artifactId=artifact.artifactId,
        label=artifact.label,
        anchorKind="reference",
        locator=locator,
        canonState=artifact.canonState,
        lifecycleState=artifact.lifecycleState,
        evidenceRole=artifact.evidenceRole,
        authorityState=artifact.authorityState,
        visibilityState=artifact.visibilityState,
        metadata=artifact.metadata,
    )
    unit = _make_unit(artifact, anchor, stage="manifest")
    return artifact, anchor, unit
