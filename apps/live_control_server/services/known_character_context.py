"""Read identity-only hints from Core's admitted immutable campaign context."""
from collections import defaultdict
from dungeonmind.application.vnext import EntityReadService
from apps.live_control_server.integrations.dungeonmind import native_registry_source as native


def read_known_character_catalog(managed_world_id: str, campaign_id: str) -> dict:
    try:
        bound = native.binding(managed_world_id)
    except Exception as exc:
        if getattr(exc, 'code', None) != 'native_graph_provisioning_pending':
            raise
        # Reserved source ownership grants no Graph read access yet.
        from apps.live_control_server.services.managed_world_graph_projection import resolve_managed_source_identity
        identity = resolve_managed_source_identity(managed_world_id)
        return {'status': 'native_graph_provisioning', 'entities': [],
                'native_pin': {'managed_world_id': identity.managed_world_id,
                               'native_world_id': identity.native_world_id,
                               'binding_version': identity.binding_version}}

    repo = native.read_repository()
    head = repo.get_head(bound['native_world_id'])
    if head is None:
        if native.binding(managed_world_id) != bound:
            raise ValueError('Known character World binding changed')
        return {'status': 'no_native_head', 'entities': [], 'native_pin': bound}
    read, access, _, _ = native.read_context(repo, bound['native_world_id'], head.head_revision_id, campaign_id, 'gm')
    service = EntityReadService()
    listing = service.list_entities(read)
    if listing.completeness.status != 'complete':
        raise ValueError('Known character catalog is incomplete')
    names, ids, refs = defaultdict(set), set(), defaultdict(set)
    # Only assertions Core actually admitted in this exact campaign context.
    for aid in listing.admitted_assertion_ids:
        assertion = access.parsed.get_assertion(aid)
        value = assertion.value
        eid = assertion.subject_entity_id
        if assertion.predicate == 'dnd5e:classification' and getattr(value, 'term', None) == 'dungeonbuddy:character':
            ids.add(eid)
            refs[eid].add(aid)
        if assertion.predicate == 'dnd5e:name' and isinstance(getattr(value, 'value', None), str) and value.value.strip():
            names[eid].add(value.value)
            refs[eid].add(aid)
    from src.graph_memory.extraction.known_entity_registry import normalize_match_surface
    name_owners = defaultdict(set)
    for eid, surfaces in names.items():
        for surface in surfaces:
            name_owners[normalize_match_surface(surface)].add(eid)
    aliases_by_entity = {}
    # Raw alias presence is used only to schedule an admitted Core read; no raw
    # alias text or standing is copied. Include non-character owners so their
    # aliases cannot make a character surface falsely unique.
    for entity in listing.entities:
        eid = entity.entity_id
        if not access.parsed.get_entity_aliases(eid):
            continue
        complete = service.get_complete_entity(read, eid)
        if not complete.found or complete.completeness.status != 'complete':
            raise ValueError('Known identity alias ownership is incomplete')
        aliases_by_entity[eid] = complete.aliases
        for alias in complete.aliases:
            name_owners[normalize_match_surface(alias.alias_text)].add(eid)
    entities = []
    for eid in sorted(ids & names.keys()):
        aliases = aliases_by_entity.get(eid, ())
        terms = sorted(names[eid] | {a.alias_text for a in aliases if a.alias_text.strip()}, key=lambda n: (len(n), n))
        entities.append({'entity_id': eid, 'label': min(names[eid], key=lambda n: (len(n), n)),
                         'names': terms, 'assertion_ids': sorted(refs[eid]),
                         'alias_ids': sorted(a.alias_id for a in aliases)})
    if native.binding(managed_world_id) != bound:
        raise ValueError('Known character World binding changed')
    return {'status': 'available', 'entities': entities,
            'ambiguous_names': sorted(n for n, owners in name_owners.items() if len(owners) > 1),
            'native_pin': {**bound, 'campaign_id': campaign_id, 'revision_id': head.head_revision_id,
                           'graph_sha256': access.parsed.graph_payload_sha256,
                           'catalog_digest': listing.result_digest}}
