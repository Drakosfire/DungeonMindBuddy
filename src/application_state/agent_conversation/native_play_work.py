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
    moment=read_native_play_current_moment(conn,work.play_basis)
    validate_play_source_owner_join(frame,work.play_basis,
        owner_resolved_current_moment_text=moment)
    resolve_play_work_sessions(conn,work.play_basis,provenance.supporting_work,
        sessions,world_id=provenance.world_id)
