"""Bounded Run-first native admission metadata. No Markdown/history reads."""
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.errors import ApplicationStateConflictError, ApplicationStateNotFoundError, ApplicationStateIntegrityError
from .types import PlayRunTurnContextReceiptV2


def lock_and_validate_native_play_basis(conn, receipt: PlayRunTurnContextReceiptV2) -> None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute("""SELECT r.world_id,r.lifecycle_status,r.run_revision,
            jsonb_typeof(r.progress->'notes_by_element_id') AS notes_type,
            octet_length(r.progress->'notes_by_element_id'->>%s::text) AS note_bytes,
            CASE WHEN octet_length(r.progress->'notes_by_element_id'->>%s::text)<=32768
                THEN r.progress->'notes_by_element_id'->%s::text END AS selected_note,
            r.playable_work_object_id,r.playable_work_revision_id,r.playable_revision_n,r.playable_content_sha256,
            w.world_id AS source_revision_world,o.world_id AS source_object_world
            FROM play.run r JOIN content.work_revision w ON w.work_revision_id=r.playable_work_revision_id
            JOIN content.work_object o ON o.work_object_id=r.playable_work_object_id
            WHERE r.run_id=%s FOR UPDATE OF r""",(receipt.scene_id,receipt.scene_id,receipt.scene_id,receipt.run_id))
        run=cur.fetchone()
        if run is None or run['world_id']!=receipt.world_id:
            raise ApplicationStateNotFoundError('Play session is unavailable in this World')
        if run['lifecycle_status']!='active':
            raise ApplicationStateConflictError('Play session is in Trash')
        if (run['source_revision_world']!=receipt.world_id or run['source_object_world']!=receipt.world_id
                or run['run_revision']!=receipt.run_revision
                or str(run['playable_work_object_id'])!=receipt.runbook_object_id
                or run['playable_work_revision_id']!=receipt.runbook_work_revision_id
                or run['playable_revision_n']!=receipt.runbook_revision_n
                or run['playable_content_sha256']!=receipt.runbook_content_sha256):
            raise ApplicationStateConflictError('Native Play Run revision/origin changed before admission')
        if run['notes_type']!='object':
            raise ApplicationStateIntegrityError('Native Play saved notes are malformed')
        if run['note_bytes'] is not None and run['note_bytes']>32768:
            raise ApplicationStateConflictError('Native Play saved note exceeds its source budget')
        if run['selected_note']!=receipt.scene_note:
            raise ApplicationStateConflictError('Native Play saved note changed before admission')
        # Stored structure membership is immutable across Run-local editions.
        # Return booleans/identity only, never transfer the full manifest/document.
        cur.execute("""SELECT manifest->>'schema_version' AS schema,
            manifest->>'playable_artifact_id' AS artifact,
            manifest->>'playable_revision' AS origin_revision,
            manifest->>'playable_content_sha256' AS origin_sha,
            jsonb_path_exists(manifest,'$.beats[*] ? (@.beat_id == $beat)',%s) AS beat_found,
            jsonb_path_exists(manifest,'$.scenes[*] ? (@.scene_id == $scene && @.beat_id == $beat)',%s) AS scene_found
            FROM play.run_manifest WHERE run_id=%s""",
            (Jsonb({'beat':receipt.beat_id}),Jsonb({'beat':receipt.beat_id,'scene':receipt.scene_id}),receipt.run_id))
        manifest=cur.fetchone()
        if (manifest is None or manifest['schema']!='dmb_play_run_reference_manifest_v2'
                or manifest['artifact']!=receipt.runbook_object_id
                or manifest['origin_revision']!=str(receipt.runbook_revision_n)
                or manifest['origin_sha']!=receipt.runbook_content_sha256
                or not manifest['beat_found'] or (receipt.scene_id is not None and not manifest['scene_found'])):
            raise ApplicationStateConflictError('Native Play target is not in the sealed Run structure')
        cur.execute("""SELECT e.world_id,e.origin_artifact_id,e.origin_revision_n,e.origin_work_revision_id,
            e.origin_content_sha256,e.head_revision,r.revision_id,r.content_sha256
            FROM play.run_edition e LEFT JOIN play.run_edition_revision r
            ON r.run_id=e.run_id AND r.revision_n=e.head_revision WHERE e.run_id=%s""",(receipt.run_id,))
        edition=cur.fetchone()
        if edition is None:
            matches=(receipt.edition_revision==0 and receipt.edition_revision_id is None
                and receipt.content_sha256==receipt.runbook_content_sha256)
        else:
            matches=(edition['world_id']==receipt.world_id and str(edition['origin_artifact_id'])==receipt.runbook_object_id
                and edition['origin_revision_n']==receipt.runbook_revision_n
                and edition['origin_work_revision_id']==receipt.runbook_work_revision_id
                and edition['origin_content_sha256']==receipt.runbook_content_sha256
                and edition['head_revision']==receipt.edition_revision and edition['revision_id']==receipt.edition_revision_id
                and edition['content_sha256']==receipt.content_sha256)
        if not matches:
            raise ApplicationStateConflictError('Native Play edition changed before admission')
