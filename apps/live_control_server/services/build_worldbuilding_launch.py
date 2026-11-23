"""Reserve one exact Build Worldbuilding request before model dispatch."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Callable
from uuid import UUID, uuid5

from apps.live_control_server.models.build_worldbuilding_launch import BuildWorldbuildingLaunchRequest
from apps.live_control_server.services.graph_run_registry import GraphRunRegistryError, create_extraction_run, get_extraction_run
from apps.live_control_server.services.source_artifact_registry import create_source_artifact_from_workspace_document
from apps.live_control_server.services.workspace_document_registry import get_workspace_document
from graph_memory.extraction.worldbuilding_profile_catalog import PUBLISHABLE_WORLDBUILDING_PROFILES
from graph_memory.extraction.worldbuilding_plumbing_profile import WORLDBUILDING_PLUMBING_PROFILE_ID, WORLDBUILDING_PLUMBING_PROFILE_VERSION

_NAMESPACE = UUID('d0813ec5-2f21-4c44-9e6c-0d0fb781f0ec')
_SCHEMA = 'dmb_build_worldbuilding_launch_v1'


def _identity(request_id: UUID) -> str:
    return str(uuid5(_NAMESPACE, str(request_id)))


def recover_build_worldbuilding_launch(*, request_id: UUID, document_id: UUID, managed_world_id: str):
    run = get_extraction_run(_identity(request_id))
    launch = run.lineage.get('build_launch', {})
    request = launch.get('request', {})
    if (launch.get('schema') != _SCHEMA or request.get('request_id') != str(request_id)
        or request.get('document_id') != str(document_id) or request.get('managed_world_id') != managed_world_id):
        raise GraphRunRegistryError('Build launch does not match this document and World', status_code=409)
    return run


def launch_build_worldbuilding(root: Path, body: BuildWorldbuildingLaunchRequest, *,
                               authorize: Callable[[], None] | None = None):
    request = body.model_dump(mode='json')
    fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()
    allowed = {*(tuple(key.split('@')) for key in PUBLISHABLE_WORLDBUILDING_PROFILES),
               (WORLDBUILDING_PLUMBING_PROFILE_ID, WORLDBUILDING_PLUMBING_PROFILE_VERSION)}
    if (body.profile_id, body.profile_version) not in allowed:
        raise GraphRunRegistryError('Unsupported Worldbuilding profile', status_code=422)

    def existing():
        try:
            run = recover_build_worldbuilding_launch(request_id=body.request_id, document_id=body.document_id,
                                                     managed_world_id=body.managed_world_id)
        except GraphRunRegistryError as exc:
            if exc.status_code == 404:
                return None
            raise
        if run.lineage['build_launch'].get('request_sha256') != fingerprint:
            raise GraphRunRegistryError('Build launch request identity was reused with different configuration', status_code=409)
        return run

    prior = existing()
    if prior is not None:
        return prior
    record = get_workspace_document(root, str(body.document_id))
    if record.world_id != body.managed_world_id:
        raise GraphRunRegistryError('Build source belongs to another World', status_code=409)
    if authorize is not None:
        authorize()
    def authorize_source(world: str | None) -> None:
        if world != body.managed_world_id:
            raise GraphRunRegistryError('Build source belongs to another World', status_code=409)
        if authorize is not None:
            authorize()
    artifact = create_source_artifact_from_workspace_document(root, document_id=str(body.document_id),
        expected_revision=body.expected_revision, expected_content_sha256=body.expected_content_sha256,
        authorize_world=authorize_source)
    if artifact.world_id != body.managed_world_id:
        raise GraphRunRegistryError('Build source belongs to another World', status_code=409)
    lineage = {'build_launch': {'schema': _SCHEMA, 'request': request, 'request_sha256': fingerprint}}
    if authorize is not None:
        authorize()
    try:
        reserved = create_extraction_run(root, run_id=_identity(body.request_id), source_artifact_id=artifact.source_artifact_id,
            source_domain='worldbuilding', campaign_id=artifact.campaign_id, session_id=artifact.session_id,
            profile_id=f'{body.profile_id}@{body.profile_version}', lineage=lineage)
    except GraphRunRegistryError as exc:
        if exc.status_code != 409:
            raise
        winner = existing()
        if winner is None:
            raise
        return winner
    if body.profile_id == 'worldbuilding_gazetteer_v1' and body.profile_version in {'1.5', '1.6', '1.7', '1.8', '1.9', '1.10'}:
        from apps.live_control_server.services.worldbuilding_ge_execution import run_gazetteer_with_generation_engine
        result = run_gazetteer_with_generation_engine(repo_root=root, source_artifact_id=artifact.source_artifact_id,
            document_id=record.document_id, document_revision=record.revision,
            expected_content_sha256=body.expected_content_sha256, profile_version=body.profile_version, reserved_run=reserved)
    else:
        from apps.live_control_server.services.graph_preview_runner import run_worldbuilding_production_extraction
        result = run_worldbuilding_production_extraction(repo_root=root, source_artifact_id=artifact.source_artifact_id,
            profile_id=body.profile_id, profile_version=body.profile_version, allow_llm=True, reserved_run=reserved)
    return result.run
