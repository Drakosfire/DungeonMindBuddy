"""APP ownership versus the current registered Build native publication scope."""

SCOPE_FIELDS = frozenset({'world_id','source_domain','campaign_id','session_id'})


def source_scope_matches(scope, artifact, managed_world_id):
    if (scope['world_id'] != managed_world_id
            or scope['source_domain'] != artifact['source_domain']
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
