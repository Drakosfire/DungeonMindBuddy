"""Native registry identity discovery; not Graph projection or a body reader."""
from datetime import datetime, timezone
import re
from dungeonmind.contracts.evidence import SourceArtifactV2
from dungeonmind.domain.canonical import canonical_json


def collect_source_view(services, *, native_world_id):
    if services.binding.world_id != native_world_id:
        raise ValueError('Corpus native World differs from managed binding')
    started = datetime.now(timezone.utc).isoformat()
    repository = services.bundle.sources
    artifacts = repository.list_artifacts_for_world(native_world_id)
    ids, revisions, listed, revision_owners = set(), set(), {}, {}
    gaps = []
    for artifact in artifacts:
        if artifact.world_id != native_world_id:
            raise ValueError('Corpus enumeration returned foreign World metadata')
        identity = artifact.source_artifact_id
        if identity in ids:
            raise ValueError('Corpus enumeration repeated an artifact')
        ids.add(identity)
        for revision in repository.list_revisions(identity):
            if revision.source_artifact_id != identity or revision.source_revision_id in revisions:
                raise ValueError('Corpus enumeration returned inconsistent revision ownership')
            revisions.add(revision.source_revision_id)
            revision_owners[revision.source_revision_id] = identity
        listed[identity] = artifact.model_dump(mode='json')
    snapshot = repository.get_provenance_snapshot(artifact_ids=sorted(ids), revision_ids=sorted(revisions))
    members = []
    revision_records = {r: snapshot.get_revision(r) for r in sorted(revisions)}
    for identity, record in list(revision_records.items()):
        if record is not None and (record.source_revision_id != identity
                or record.source_artifact_id != revision_owners[identity]):
            gaps.append({'source_revision_id': identity, 'code': 'source_revision_identity_mismatch'})
            revision_records[identity] = None
    for identity in sorted(ids):
        artifact = snapshot.get_artifact(identity)
        if artifact is None:
            gaps.append({'source_artifact_id': identity, 'code': 'source_metadata_missing'})
            continue
        raw = artifact.model_dump(mode='json')
        if raw != listed[identity]:
            gaps.append({'source_artifact_id': identity, 'code': 'source_metadata_drift'})
            continue
        if (not isinstance(artifact, SourceArtifactV2) or artifact.world_id != native_world_id
                or raw.get('status') != 'active' or raw.get('visibility') not in {'gm', 'player'}
                or raw.get('source_domain') not in {'worldbuilding', 'session_recap'}):
            gaps.append({'source_artifact_id': identity, 'code': 'source_policy_unavailable'})
            continue
        owned = [r for r in revision_records.values() if r is not None and r.source_artifact_id == identity]
        if not owned:
            gaps.append({'source_artifact_id': identity, 'code': 'source_revision_missing'})
        for revision in owned:
            if not re.fullmatch('[0-9a-f]{64}', revision.content_sha256):
                gaps.append({'source_revision_id': revision.source_revision_id, 'code': 'source_digest_unavailable'})
                continue
            members.append({'artifact': raw, 'revision': revision.model_dump(mode='json')})
    for identity in sorted(revisions):
        if snapshot.get_revision(identity) is None:
            gaps.append({'source_revision_id': identity, 'code': 'source_revision_missing'})
    members.sort(key=lambda r: (r['artifact']['source_artifact_id'], r['revision']['source_revision_id']))
    return {'schema': 'dmb_corpus_source_view_v1', 'native_world_id': native_world_id,
        'scope': {'admissibility': 'gm', 'scope_mode': 'world_cross_campaign', 'campaign_id': None,
                  'focus': {'kind': 'none', 'session_id': None}},
        'started_at': started, 'finished_at': datetime.now(timezone.utc).isoformat(),
        'snapshot_fingerprint': snapshot.fingerprint, 'members': members, 'gaps': gaps}


def verify_registry_source_origin(services, *, native_world_id, proof):
    """Fresh access check over exact native metadata; never a locator or latest read."""
    from .source_origin import NativeSourceOrigin
    if services.binding.world_id != native_world_id:
        raise ValueError('Registry source World binding changed')
    artifact, revision = proof['artifact'], proof['revision']
    snapshot = services.bundle.sources.get_provenance_snapshot(
        artifact_ids=[artifact['source_artifact_id']], revision_ids=[revision['source_revision_id']])
    current = snapshot.get_artifact(artifact['source_artifact_id'])
    observed = snapshot.get_revision(revision['source_revision_id'])
    current_raw = current.model_dump(mode='json') if current is not None else {}
    scope_fields = ('schema_version', 'source_artifact_id', 'source_domain_key', 'source_domain',
                    'world_id', 'campaign_id', 'session_id', 'authority', 'visibility', 'status')
    old_ref, new_ref = artifact.get('workspace_document_ref'), current_raw.get('workspace_document_ref')
    same_document = ((old_ref is None and new_ref is None) or
                     isinstance(old_ref, dict) and isinstance(new_ref, dict)
                     and old_ref.get('document_id') == new_ref.get('document_id'))
    if (not isinstance(current, SourceArtifactV2) or observed is None
            or any(current_raw.get(k) != artifact.get(k) for k in scope_fields)
            or not same_document or observed.model_dump(mode='json') != revision
            or artifact.get('world_id') != native_world_id or artifact.get('status') != 'active'
            or artifact.get('visibility') not in {'gm', 'player'}
            or artifact.get('source_domain') not in {'worldbuilding', 'session_recap'}
            or revision.get('source_artifact_id') != artifact['source_artifact_id']):
        raise ValueError('Registry source metadata or access policy changed')
    # No Graph donor is synthesized. The durable search event owns membership.
    return NativeSourceOrigin(None, artifact['source_artifact_id'], revision['source_revision_id'],
        revision['content_sha256'], canonical_json(proof))
