"""Shared Play work through the existing immutable Run and review owners.

Projection checks frozen commitments; only locked admission resolves ownership.
No current Run reads, alternate body store or invented Plan authority.
"""
from uuid import UUID
import json

from . import types as t
from .native_context import PlayWorkContextV1
from .play_graph_authority import validate_play_source_owner_join
from .play_session_input import pack, validate_work_packets
from .rules_authority_types import canonical_sha256

SCHEMA = 'dmb_native_play_work_v1'


def work_records(work, provenance, proof):
    """Check supplied bytes against the accepted work; this grants no authority."""
    if (type(work) is not PlayWorkContextV1 or type(provenance) is not t.TurnProvenance
            or not isinstance(proof,dict) or set(proof) != {'source_frame','session_evidence','dialogue'}):
        raise ValueError('Native Play requires its exact work and producer proof')
    frame=t.PlaySourceFrameV1.model_validate_json(json.dumps(proof['source_frame']))
    if (frame.manifest != work.play_sources or canonical_sha256(frame) != work.play_source_frame_sha256
            or provenance.world_id != work.play_basis.world_id or provenance.surface_id != 'play'):
        raise ValueError('Native Play frame differs from its accepted Run work')
    t.validate_play_context_receipt(work.play_basis,provenance.world_id,provenance)
    kinds={source.source_kind for source in frame.sources}
    expected={'current_moment'} | ({'scene_note'} if work.play_basis.scene_note is not None else set())
    if kinds != expected:
        raise ValueError('Native Play work must preserve its current moment and separate saved note')
    validate_work_packets(work.play_basis,provenance.supporting_work,
        proof['session_evidence'],world_id=provenance.world_id)
    dialogue=proof['dialogue']
    if (not isinstance(dialogue,list) or any(not isinstance(row,dict)
            or set(row) != {'role','content'} or row['role'] not in {'user','assistant'}
            or not isinstance(row['content'],str) for row in dialogue)):
        raise ValueError('Native Play dialogue differs from its exact message format')
    return frame,proof['session_evidence'],dialogue


def project_work(work, provenance, submission_id, proof):
    """Host reconstruction only; this frame must never be sent to a model."""
    if type(submission_id) is not UUID:
        raise ValueError('Native Play work requires its actual submission identity')
    frame,sessions,dialogue=work_records(work,provenance,proof)
    frame_wire,session_wire=pack(frame,str(submission_id),sessions)
    return dict(schema=SCHEMA,submission_id=str(submission_id),source_frame=frame_wire,
        session_evidence=session_wire,dialogue=dialogue)


def validate_owner_locked(conn, work, provenance, proof):
    """Independent APP owner check, required before acknowledging supplied input."""
    from .play_graph_source_owner import read_native_play_current_moment,resolve_play_work_sessions
    frame,sessions,_=work_records(work,provenance,proof)
    moment=read_native_play_current_moment(conn,work.play_basis,include_edition_revision=False)
    validate_play_source_owner_join(frame,work.play_basis,
        owner_resolved_current_moment_text=moment)
    resolve_play_work_sessions(conn,work.play_basis,provenance.supporting_work,
        sessions,world_id=provenance.world_id)


def semantic_frame(host):
    """Model input contains actual text and local selectors, never host identity."""
    from copy import deepcopy
    if (not isinstance(host,dict) or set(host) != {
            'schema','submission_id','source_frame','session_evidence','dialogue'}
            or host['schema'] != SCHEMA):
        raise ValueError('Semantic Play work requires its exact host reconstruction')
    aliases = {}
    def blocks(rows):
        result=[]
        for row in rows:
            if not isinstance(row,dict) or set(row) != {'selection_id','text'}:
                raise ValueError('Unclassified Play work block')
            original=row['selection_id']
            if original is None:
                if row['text'].strip():
                    raise ValueError('Nonblank Play work lacks its exact selector')
                alias=None
            else:
                if original in aliases:
                    raise ValueError('Play work repeats an authored selector')
                alias=aliases[original]=f'work{len(aliases)}'
            result.append(dict(selection_id=alias,text=row['text']))
        return result
    sources=[]
    for source in host['source_frame']['sources']:
        if source['source_kind'] not in {'current_moment','scene_note'}:
            raise ValueError('Unknown Play source role')
        sources.append(dict(source_kind=source['source_kind'],
            source_name='Saved Scene note' if source['source_kind']=='scene_note' else 'Current Play moment',
            text_blocks=blocks(source['text_blocks'])))
    sessions=[]
    for packet in host['session_evidence']:
        sessions.append({key:deepcopy(packet[key]) for key in ('title','ended_at') if key in packet}
            | {'sources':[dict(kind=entry['kind'],text_blocks=blocks(entry['text_blocks']))
                for entry in packet['sources']]})
    return dict(current_play=sources,session_evidence=sessions,
        dialogue_reference=deepcopy(host['dialogue']))


def is_semantic_frame(value):
    return isinstance(value,dict) and set(value) == {
        'current_play','session_evidence','dialogue_reference'}


def frame_in_request(body):
    """Select one explicit Play packet, never search inside authored text."""
    from .source_writer_output import strict_json
    candidates=[]
    for message in body.get('input',[]) if isinstance(body.get('input'),list) else []:
        if not isinstance(message,dict) or not isinstance(message.get('content'),str):
            continue
        try:
            value=strict_json(message['content'])
        except ValueError:
            continue
        if not isinstance(value,dict):
            continue
        if value.get('schema') == SCHEMA:
            raise ValueError('Host Play work must not enter provider input')
        if 'current_play' in value:
            if not is_semantic_frame(value) or message.get('role') != 'user':
                raise ValueError('Malformed semantic Play surface work')
            candidates.append(value)
    if len(candidates) != 1:
        raise ValueError('Native Play requires one exact semantic work packet')
    return candidates[0]


def proof_from_host(work,provenance,host,submission_id):
    """Restore the existing captured packet and prove its exact commitment."""
    from .play_session_input import restore,packet_sources
    from .play_graph_input import unpack_selector_play_frame
    if not isinstance(host,dict) or host.get('submission_id') != str(submission_id):
        raise ValueError('Play work changed its actual submission')
    sessions=restore(host['session_evidence'])
    session_supports=packet_sources(sessions)
    frame=unpack_selector_play_frame(host['source_frame'],str(submission_id),
        [(s.handle,s.text) for s in session_supports])
    proof=dict(source_frame=frame.model_dump(mode='json',by_alias=True),
        session_evidence=sessions,dialogue=host['dialogue'])
    if project_work(work,provenance,submission_id,proof) != host:
        raise ValueError('Play authored selectors differ from their frozen work')
    return frame,sessions,proof


def producing_authored_records(work,provenance,host,submission_id):
    """Resolve selectors through existing immutable Play and session owners."""
    from .surface_evidence_answer import AuthoredSupport
    from .play_session_input import packet_sources
    frame,sessions,_=proof_from_host(work,provenance,host,submission_id)
    sources=tuple(AuthoredSupport(entry.source_id,'play',
        'Saved scene note' if source.source_kind=='scene_note' else 'Saved Play scene',
        source.locator.run_id,str(source.locator.run_revision),entry.text_sha256,
        entry.payload_sha256,source.text)
        for source,entry in zip(frame.sources,frame.manifest.entries,strict=True))
    return sources + packet_sources(sessions)
