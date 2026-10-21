"""One durable request identity; a replay observes the original run without inference."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

from apps.live_control_server.models.build_recap_launch import BuildRecapLaunchRequest
from apps.live_control_server.services.build_recap_source import register_build_recap_source, frozen_build_recap_configuration
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError, create_extraction_run, get_extraction_run
from apps.live_control_server.services.graph_preview_runner import run_recap_production_extraction
from apps.live_control_server.services.recap_ingest_context import read_recap_ingest_context
from src.graph_memory.extraction.bounded_recap_execution import DEEPSEEK_MODEL
from src.graph_memory.extraction.recap_extraction_profile import resolve_legacy_graph_extraction_profile

_NAMESPACE = UUID("b4c1d0a6-c412-4c42-ad34-8e513ac6de1d")


def _identity(request_id: UUID) -> str:
    return str(uuid5(_NAMESPACE, str(request_id)))


def recover_build_recap_launch(root: Path, *, request_id: UUID, document_id: UUID, managed_world_id: str):
    run = get_extraction_run(root,_identity(request_id))
    launch = run.lineage.get("build_launch", {})
    request = launch.get("request", {})
    if (launch.get("schema") != "dmb_build_recap_launch_v1" or request.get("request_id") != str(request_id)
            or request.get("document_id") != str(document_id) or request.get("managed_world_id") != managed_world_id):
        raise GraphRunRegistryError("Build launch does not match this document and World",status_code=409)
    return run


def launch_build_recap(root: Path, body: BuildRecapLaunchRequest, *, category_client: Any | None = None):
    request = body.model_dump(mode="json")
    fingerprint = hashlib.sha256(json.dumps(request,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    run_id = _identity(body.request_id)

    def existing():
        try:
            run = recover_build_recap_launch(root,request_id=body.request_id,document_id=body.document_id,managed_world_id=body.managed_world_id)
        except GraphRunRegistryError as exc:
            if exc.status_code == 404: return None
            raise
        if run.lineage["build_launch"].get("request_sha256") != fingerprint:
            raise GraphRunRegistryError("Build launch request identity was reused with different configuration",status_code=409)
        return run

    prior = existing()
    if prior is not None: return prior
    context = read_recap_ingest_context(managed_world_id=body.managed_world_id,campaign_id=body.campaign_id)
    supplement = None
    if body.session_evidence:
        from apps.live_control_server.services.session_evidence import resolve_evidence_refs
        supplement = resolve_evidence_refs(body.managed_world_id,[ref.model_dump() for ref in body.session_evidence])
    artifact = register_build_recap_source(root,document_id=str(body.document_id),expected_revision=body.expected_revision,
        expected_content_sha256=body.expected_content_sha256,session_id=f"session-{body.session}",ingest_context=context)
    profile_id,profile_version = resolve_legacy_graph_extraction_profile("category_baseline")
    frozen = frozen_build_recap_configuration(root,source_artifact_id=artifact.source_artifact_id,campaign_id=body.campaign_id,
        session_id=f"session-{body.session}",context=context.as_lineage(),profile_id=profile_id,profile_version=profile_version,supplemental_evidence=supplement)
    lineage = {"world_campaign_ingest_context":context.as_lineage(),"build_document_ingest":frozen,
        "build_launch":{"schema":"dmb_build_recap_launch_v1","request":request,"request_sha256":fingerprint,
            "server_configuration":{"profile_id":profile_id,"profile_version":profile_version,
                "provider":"openrouter","model":DEEPSEEK_MODEL,"route":"ordinary_recap_generation_engine_v1",
                "enable_node_vocabulary_packet":False,"enable_edge_vocabulary_packet":False}}}
    try:
        reserved = create_extraction_run(root,run_id=run_id,source_artifact_id=artifact.source_artifact_id,source_domain="recap",
            campaign_id=body.campaign_id,session_id=f"session-{body.session}",profile_id=f"{profile_id}@{profile_version}",lineage=lineage)
    except GraphRunRegistryError as exc:
        if exc.status_code != 409: raise
        winner = existing()
        if winner is None: raise
        return winner
    # Only the unique reservation winner enters the production controller.
    # A crashed/unknown attempt is recovered as-is, never silently re-executed.
    result = run_recap_production_extraction(repo_root=root,campaign_id=body.campaign_id,session_id=f"session-{body.session}",
        build_source_artifact_id=artifact.source_artifact_id,profile="category_baseline",allow_llm=True,model_id=DEEPSEEK_MODEL,category_client=category_client,
        ingest_context=context,supplemental_evidence=supplement,reserved_run=reserved,
        output_dir=Path("out")/"graph_memory"/"runs"/"extraction"/f"build-recap-{run_id}")
    return result.run
