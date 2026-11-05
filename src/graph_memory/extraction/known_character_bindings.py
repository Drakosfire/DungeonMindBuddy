"""Pinned native names -> literal source mentions; no inferred presence or actions."""
from __future__ import annotations

import copy
import hashlib
import json
from collections import defaultdict
from src.graph_memory.extraction.known_entity_registry import KnownEntity, normalize_match_surface, is_unsafe_match_alias
from src.graph_memory.extraction.known_entity_mention_matcher import build_term_index, match_text_mentions


def bind_characters(catalog: dict, rows: list[dict], source_sha256: str) -> dict:
    entities = []
    for row in catalog.get('entities', []):
        terms = tuple((n, 'canonical') for n in row['names'] if n.strip() and not is_unsafe_match_alias(n))
        entities.append(KnownEntity(row['entity_id'], 'character', row['label'], row['entity_id'], (), '', False, {}, terms))
    index = build_term_index(entities)
    owners = defaultdict(set)
    for entry in index:
        owners[entry.normalized].add(entry.entity.canonical_entity_id)
    ambiguous = {n for n, ids in owners.items() if len(ids) != 1} | set(catalog.get('ambiguous_names', []))
    mentions, ignored = [], set()
    for row in rows:
        hits, conflicts = match_text_mentions(row['text'], source_span_ref_id=row['source_span_ref_id'], term_index=index, ambiguous_norms=ambiguous)
        ignored.update(conflicts)
        mentions.extend({'entity_id': h.canonical_entity_id, 'source_span_ref_id': h.source_span_ref_id,
                         'start_offset': h.start_offset, 'end_offset': h.end_offset, 'surface': h.surface_text} for h in hits)
    mentioned = {m['entity_id'] for m in mentions}
    selected = []
    for row in catalog.get('entities', []):
        if row['entity_id'] not in mentioned:
            continue
        safe_names = [name for name in row['names'] if not is_unsafe_match_alias(name)
                      and normalize_match_surface(name) not in ambiguous]
        if safe_names:
            selected.append({**row, 'names': safe_names, 'label': min(safe_names, key=lambda n: (len(n), n))})
    record = {'schema': 'dmb_known_character_bindings_v1', 'source_sha256': source_sha256,
              'native_pin': catalog.get('native_pin'), 'status': catalog.get('status', 'available'),
              'entities': selected,
              'mentions': mentions, 'ambiguous_surfaces': sorted(ignored)}
    record['sha256'] = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return record


def identity_prompt(context: dict) -> str:
    if not context.get('entities'):
        return ''
    rows = [{'label': e['label'], 'names': e['names'], 'source_spans': sorted({m['source_span_ref_id'] for m in context['mentions'] if m['entity_id'] == e['entity_id']})} for e in context['entities']]
    return ('\n\nKnown characters located deterministically in this source (identity hints only):\n' + json.dumps(rows, ensure_ascii=False) +
            '\nKeep these mentioned actors in observation_nodes, using a listed source name. Extract only actions supported by the current source. '
            'A name mention does not establish an action, role, PC status, or participation in other events. Do not invent aliases or copy historical facts.\n')


def candidate_bindings(nodes: list[dict], context: dict) -> dict[str, str]:
    """Unique candidate label -> unique admitted name. Never infer aliases from prose."""
    owners = defaultdict(set)
    for entity in context.get('entities', []):
        for name in entity['names']:
            owners[normalize_match_surface(name)].add(entity['entity_id'])
    matches = defaultdict(list)
    for node in nodes:
        if node.get('node_type') != 'character':
            continue
        ids = owners.get(normalize_match_surface(node.get('label', '')), set())
        if len(ids) == 1:
            matches[next(iter(ids))].append(node['node_id'])
    return {eid: ids[0] for eid, ids in matches.items() if len(ids) == 1}


def ensure_name_anchors(payload: dict, context: dict) -> dict:
    result = copy.deepcopy(payload)
    nodes = result.setdefault('observation_nodes', [])
    bound = candidate_bindings(nodes, context)
    # Any existing ambiguous candidate must be reviewed, not silently supplemented.
    labels = {normalize_match_surface(n.get('label', '')) for n in nodes}
    for entity in context.get('entities', []):
        if entity['entity_id'] in bound or any(normalize_match_surface(n) in labels for n in entity['names']):
            continue
        refs = {}
        for mention in context['mentions']:
            if mention['entity_id'] == entity['entity_id']:
                refs.setdefault(mention['source_span_ref_id'], set()).add(mention['surface'])
        node_id = 'known-character:' + hashlib.sha256(entity['entity_id'].encode()).hexdigest()[:24]
        if any(n.get('node_id') == node_id for n in nodes):
            raise ValueError('known character candidate ID collision')
        nodes.append({'node_id': node_id, 'label': entity['label'], 'node_type': 'character',
                      'description': None, 'importance': 'medium', 'confidence': 'high',
                      'warnings': ['Deterministic name mention only; no action or PC role inferred.'],
                      'evidence_refs': [{'source_span_ref_id': ref, 'anchor_quotes': sorted(quotes)} for ref, quotes in refs.items()]})
    return result
