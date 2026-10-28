"""Independent immutable Play source owner; never current Run or history reads."""
from hashlib import sha256

from psycopg.rows import dict_row

from . import types as t


def read_native_play_current_moment(conn, basis: t.PlayRunTurnContextReceiptV2) -> str:
    """Read one accepted body and derive its moment with the existing v2 owner."""
    with conn.cursor(row_factory=dict_row) as cur:
        if basis.edition_revision == 0:
            cur.execute("""SELECT w.world_id,o.world_id AS object_world,w.work_object_id,
                w.work_revision_id,w.revision_n,w.content_sha256,
                CASE WHEN octet_length(w.markdown)<=1048576 THEN w.markdown END AS markdown
                FROM content.work_revision w JOIN content.work_object o ON o.work_object_id=w.work_object_id
                WHERE w.work_revision_id=%s""",(basis.runbook_work_revision_id,))
            row=cur.fetchone()
            valid=(row is not None and row['world_id']==basis.world_id and row['object_world']==basis.world_id
                and str(row['work_object_id'])==basis.runbook_object_id
                and row['revision_n']==basis.runbook_revision_n and row['content_sha256']==basis.content_sha256)
        else:
            cur.execute("""SELECT e.world_id,e.origin_artifact_id,e.origin_work_revision_id,e.origin_revision_n,
                e.origin_content_sha256,r.content_sha256,r.revision_id,
                CASE WHEN octet_length(r.markdown)<=1048576 THEN r.markdown END AS markdown
                FROM play.run_edition e JOIN play.run_edition_revision r ON r.run_id=e.run_id
                WHERE e.run_id=%s AND r.revision_n=%s""",(basis.run_id,basis.edition_revision))
            row=cur.fetchone()
            valid=(row is not None and row['world_id']==basis.world_id
                and str(row['origin_artifact_id'])==basis.runbook_object_id
                and row['origin_work_revision_id']==basis.runbook_work_revision_id
                and row['origin_revision_n']==basis.runbook_revision_n
                and row['origin_content_sha256']==basis.runbook_content_sha256
                and row['revision_id']==basis.edition_revision_id and row['content_sha256']==basis.content_sha256)
    if (not valid or row['markdown'] is None
            or sha256(row['markdown'].encode('utf-8')).hexdigest()!=basis.content_sha256):
        raise ValueError('Native Play immutable source identity/body is unavailable or inconsistent')
    from apps.live_control_server.services.agent_play_surface_context import (
        extract_v2_play_authored_slices,_world_play_turn_context,render_agent_play_surface_context,
    )
    from apps.live_control_server.services.play_run_reference_manifest import derive_play_run_reference_elements_v2
    membership=derive_play_run_reference_elements_v2(row['markdown'])
    if (not any(b.beat_id==basis.beat_id for b in membership.beats)
            or basis.scene_id is not None and not any(s.scene_id==basis.scene_id and s.beat_id==basis.beat_id for s in membership.scenes)):
        raise ValueError('Native Play source target is absent from its accepted edition')
    slices=extract_v2_play_authored_slices(row['markdown'],include_nested=True)
    beat=slices.get(basis.beat_id);scene=slices.get(basis.scene_id) if basis.scene_id is not None else None
    if beat is None or beat.kind!='beat' or basis.scene_id is not None and (scene is None or scene.kind!='scene'):
        raise ValueError('Native Play source target has no authored body')
    context=_world_play_turn_context(basis.world_id,basis.world_id,basis,beat,scene,
        edition_revision=basis.edition_revision,scene_note=None)
    text=render_agent_play_surface_context(context)
    if not isinstance(text,str) or len(text.encode('utf-8'))>32768:
        raise ValueError('Native Play moment exceeds its source budget')
    return text


def resolve_native_play_source_owner(conn, turn: t.Turn, frame: t.PlaySourceFrameV1) -> str | None:
    moment=next((s.text for s in frame.sources if s.source_kind=='current_moment'),None)
    if moment is None:
        return None  # Saved note authority is already exact in the accepted receipt.
    receipt=turn.graph_context_receipt
    # Only the proof-aware APP append can create this witness. Its immutable
    # frame hash proves source identity; each new request still proves exposure.
    if any(isinstance(e,t.PlaySourceProviderInclusionV1)
            and e.context_receipt_sha256==receipt.context_receipt_sha256
            and e.source_frame_sha256==receipt.play_source_frame_sha256
            and e.source_ids==[entry.source_id for entry in receipt.play_sources.entries]
            for e in turn.graph_context_execution.events):
        return moment
    return read_native_play_current_moment(conn,receipt.play_basis)


def resolve_native_play_sessions(conn, turn, sessions):
    from .play_session_input import validate_turn_packets
    from application_state.play.session_evidence import evidence
    validate_turn_packets(turn,sessions)
    for packet in sessions:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""SELECT e.payload FROM play.session_review_revision e
                JOIN play.run r USING(run_id) WHERE r.world_id=%s AND e.run_id=%s AND e.revision_n=%s""",
                (turn.world_id,packet['run_id'],packet['review_revision']))
            row=cur.fetchone()
        if row is None or evidence(row['payload'],turn.world_id,packet['run_id'],packet['review_revision']) != packet:
            raise ValueError('Play packet differs from its immutable review owner')
