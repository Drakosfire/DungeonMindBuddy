"""Exact selected-Run session packets in the current Play carrier.

Projection is not admission: APP independently resolves immutable review bytes
before authorization; acceptance joins these bytes to frozen turn references.
"""
from copy import deepcopy

from .rules_authority_types import canonical_sha256
from .surface_evidence_answer import session_sources
from .authored_excerpt_blocks import selection_catalog, project_selection_blocks, restore_selection_blocks


def validate_packets(sessions, *, world_id=None, run_id=None, frozen=None):
    if not isinstance(sessions, list) or len(sessions) > 1:
        raise ValueError('Play admits only its selected Run review')
    supplied = {}
    for packet in sessions:
        if (not isinstance(packet, dict) or packet.get('schema_version') != 'dmb_session_evidence_v1'
                or world_id is not None and packet.get('world_id') != world_id
                or run_id is not None and packet.get('run_id') != run_id):
            raise ValueError('Play session evidence has a foreign owner')
        key = (packet.get('run_id'), str(packet.get('review_revision')))
        if (key in supplied or packet.get('sha256') != canonical_sha256({k:v for k,v in packet.items() if k != 'sha256'})):
            raise ValueError('Play session packet bytes changed')
        supplied[key] = packet['sha256']
    if frozen is not None and supplied != frozen:
        raise ValueError('Play session evidence differs from frozen provenance')
    return supplied


def packet_sources(sessions):
    return session_sources(sessions, validate_packets(sessions), block_policy=True)


def pack(frame, scope, sessions):
    from .play_graph_input import pack_selector_play_frame
    sources = packet_sources(sessions)
    extras = [(s.handle,s.text) for s in sources]
    catalog = selection_catalog([(e.source_id,s.text) for s,e in zip(frame.sources,frame.manifest.entries,strict=True)] + extras, str(scope))
    wire = deepcopy(sessions)
    remaining = iter(sources)
    for packet in wire:
        for entry in packet['sources']:
            text = entry.pop('text')
            if text.strip():
                source = next(remaining)
                entry['text_blocks'] = project_selection_blocks(text,source.handle,catalog)
            else:
                entry['text_blocks'] = []
    return pack_selector_play_frame(frame,scope,extras), wire


def restore(wire):
    sessions = deepcopy(wire)
    for packet in sessions:
        for source in packet['sources']:
            source['text'] = restore_selection_blocks(source.pop('text_blocks'))
    validate_packets(sessions)
    return sessions


def validate_turn_packets(turn, sessions):
    basis = turn.graph_context_receipt.play_basis
    frozen = {(r.object_id,r.revision):r.content_sha256 for r in turn.provenance.supporting_work if r.kind == 'session_evidence_v1'}
    validate_packets(sessions,world_id=turn.world_id,run_id=basis.run_id,frozen=frozen)
    for packet in sessions:
        if (packet['checkpoint_run_revision'] != basis.run_revision
                or packet['session_content_sha256'] != basis.content_sha256):
            raise ValueError('Play session checkpoint differs from its frozen Run edition')
