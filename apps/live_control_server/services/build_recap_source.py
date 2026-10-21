"""Exact Build-document adapter into the existing Recap source/run authority."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from apps.live_control_server.services.source_artifact_registry import (
    SourceArtifactRegistryError, create_recap_source_artifact_from_workspace_document,
    get_source_artifact,
)


def _sha(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def register_build_recap_source(root: Path, *, document_id: str, expected_revision: int,
    expected_content_sha256: str, session_id: str, ingest_context: Any):
    # Same verified context requirement as ordinary Recap execution; no campaign inference.
    from apps.live_control_server.services.graph_preview_runner import _verified_ingest_context_lineage
    campaign_id = getattr(ingest_context, "campaign_id", None)
    native_world, context = _verified_ingest_context_lineage(ingest_context, campaign_id=campaign_id)
    return create_recap_source_artifact_from_workspace_document(root,
        document_id=document_id, expected_revision=expected_revision,
        expected_content_sha256=expected_content_sha256, managed_world_id=context["managed_world_id"],
        native_world_id=native_world, campaign_id=context["campaign_id"], session_id=session_id)


def frozen_build_recap_configuration(root: Path, *, source_artifact_id: str,
    campaign_id: str, session_id: str, context: dict[str, Any], profile_id: str,
    profile_version: str, supplemental_evidence: dict[str, Any] | None) -> dict[str, Any]:
    artifact = get_source_artifact(root, source_artifact_id)
    binding = artifact.lineage.get("build_recap_source")
    if (not isinstance(binding, dict) or binding.get("schema") != "dmb_build_recap_source_v1"
            or binding.get("mode") != "recap" or artifact.source_domain != "recap"
            or not artifact.workspace_document_id or not artifact.workspace_document_revision
            or artifact.world_id != context["native_world_id"] or artifact.campaign_id != campaign_id
            or artifact.session_id != session_id or binding.get("native_world_id") != artifact.world_id
            or binding.get("managed_world_id") != context["managed_world_id"]
            or binding.get("campaign_id") != campaign_id or binding.get("session_id") != session_id
            or binding.get("document_id") != artifact.workspace_document_id
            or binding.get("document_revision") != artifact.workspace_document_revision
            or binding.get("content_sha256") != artifact.content_sha256
            or artifact.lineage.get("binding_sha256") != _sha(binding)
            or artifact.source_artifact_id != f"artifact:recap:build:{artifact.workspace_document_id}:r{artifact.workspace_document_revision}:{_sha(binding)}"):
        raise SourceArtifactRegistryError("registered Build recap source does not match the frozen document and World/session binding", status_code=409)
    configuration = {"schema": "dmb_build_recap_configuration_v1", "mode": "recap",
        "source": binding, "source_artifact_id": artifact.source_artifact_id,
        "profile_id": profile_id, "profile_version": profile_version,
        "world_context": context,
        "session_evidence": None if supplemental_evidence is None else {
            "sha256": supplemental_evidence["sha256"],
            "sources": [{key: item[key] for key in ("run_id", "review_revision", "sha256")}
                for item in supplemental_evidence["sessions"]]}}
    return {"configuration": configuration, "configuration_sha256": _sha(configuration)}
