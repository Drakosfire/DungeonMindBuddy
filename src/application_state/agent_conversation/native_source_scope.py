"""Source ownership within one receipt-bound managed/native World identity."""

from application_state.source.identity import canonical_source_domain_key

SCOPE_FIELDS = frozenset({'world_id','source_domain','campaign_id','session_id'})


def source_scope_matches(scope, artifact, authority):
    key = canonical_source_domain_key(scope["source_domain"])
    if not key or key != canonical_source_domain_key(artifact.get("source_domain_key")):
        return False
    if key in {"session_recap", "worldbuilding"} and artifact.get("source_domain") != key:
        return False
    managed_world_id = authority.managed_world_id
    native_world_id = authority.native_world_id
    if artifact.get("world_id") != native_world_id:
        return False
    if scope["world_id"] == native_world_id and native_world_id != managed_world_id:
        return all(scope[key] == artifact.get(key) for key in ("campaign_id", "session_id"))
    if (scope['world_id'] != managed_world_id
            or scope['session_id'] != artifact.get('session_id')):
        return False
    if scope['campaign_id'] == artifact.get('campaign_id'):
        return True
    # worldbuilding_graph_publication projects a registered Build envelope's
    # managed owner to native World scope. Genuine campaign/session ownership
    # is never projected. Exact document lineage is checked against body storage
    # by both callers after this metadata-only admission check.
    ref = artifact.get('workspace_document_ref')
    return (artifact['source_domain'] == 'worldbuilding'
        and artifact.get('campaign_id') is None and artifact.get('session_id') is None
        and scope['campaign_id'] in ('',managed_world_id)
        and isinstance(ref,dict) and isinstance(ref.get('document_id'),str)
        and bool(ref['document_id']) and type(ref.get('revision')) is int and ref['revision'] > 0)
