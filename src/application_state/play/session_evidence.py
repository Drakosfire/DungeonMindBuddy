"""Read-only, immutable evidence derived from ended session review revisions."""
import hashlib
import json
import re
from urllib.parse import urlencode
from psycopg.rows import dict_row
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.errors import ApplicationStateNotFoundError, ApplicationStateValidationError
from application_state.play.service import _as_uuid, _require_world_id
from application_state.unit_of_work import unit_of_work

MAX_SESSION_EVIDENCE_INDEX_BYTES = 24 * 1024


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",", ":"),ensure_ascii=False).encode()).hexdigest()


def evidence(payload, world_id, run_id, revision):
    if payload.get("world_id")!=world_id or payload.get("run_id")!=str(run_id) or payload.get("revision")!=revision or payload.get("status")!="ended":
        raise ApplicationStateValidationError("Selected revision is not ended session evidence in this World")
    checkpoint=payload["checkpoint"]
    url="/play?"+urlencode({"world":world_id,"run":str(run_id),"evidence_revision":revision})
    sources=[]
    for element_id,text in checkpoint["progress"]["notes_by_element_id"].items():
        if text.strip():sources.append({"kind":"scene_note","element_id":element_id,"text":text,"sha256":hashlib.sha256(text.encode()).hexdigest(),"citation_url":url})
    thoughts=payload.get("final_thoughts", "")
    if thoughts.strip():sources.append({"kind":"closing_reflections","text":thoughts,"sha256":hashlib.sha256(thoughts.encode()).hexdigest(),"citation_url":url})
    heading=re.search(r"^# ([^\n]+)",checkpoint["content"]["markdown"],re.MULTILINE)
    title=heading.group(1).strip()[:240] if heading else "Played session"
    packet={"title":title,"schema_version":"dmb_session_evidence_v1","world_id":world_id,"run_id":str(run_id),"review_revision":revision,
            "ended_at":checkpoint["captured_at"],"checkpoint_run_revision":checkpoint["run_revision"],"session_content_sha256":checkpoint["content"]["content_sha256"],"citation_url":url,"sources":sources}
    return {**packet,"sha256":digest(packet)}


def read_session_evidence(*,world_id,run_id,revision):
    world_id=_require_world_id(world_id);run_id=_as_uuid(run_id,field_name="run_id")
    if type(revision) is not int or revision<1:raise ApplicationStateValidationError("Evidence revision must be positive")
    dsn=load_runtime_dsn();assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT e.payload FROM play.session_review_revision e JOIN play.run r USING(run_id) WHERE r.world_id=%s AND e.run_id=%s AND e.revision_n=%s",(world_id,run_id,revision));row=cur.fetchone()
        if not row:raise ApplicationStateNotFoundError("Session evidence not found in this World")
        return evidence(row["payload"],world_id,run_id,revision)


def recent_session_evidence(*,world_id,limit=3):
    world_id=_require_world_id(world_id)
    if type(limit) is not int or not 1<=limit<=20:raise ApplicationStateValidationError("Evidence limit must be 1 to20")
    dsn=load_runtime_dsn();assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""SELECT run_id,revision_n,payload FROM (
              SELECT DISTINCT ON (e.run_id) e.run_id,e.revision_n,e.payload
              FROM play.session_review_revision e JOIN play.run r USING(run_id)
              WHERE r.world_id=%s AND r.lifecycle_status='active' ORDER BY e.run_id,e.revision_n DESC
            ) heads WHERE payload->>'status'='ended' ORDER BY payload->'checkpoint'->>'captured_at' DESC,run_id LIMIT %s""",(world_id,limit))
            return [evidence(row["payload"],world_id,row["run_id"],row["revision_n"]) for row in cur.fetchall()]


def recent_session_evidence_index(*,world_id,limit=20):
    """Return bounded session metadata without reading note/reflection bodies into Python."""
    world_id = _require_world_id(world_id)
    if type(limit) is not int or not 1 <= limit <= 20:
        raise ApplicationStateValidationError("Evidence limit must be 1 to20")
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    with unit_of_work(dsn) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(r"""SELECT heads.run_id,heads.revision_n,
              COALESCE(NULLIF(btrim(substring(heads.payload->'checkpoint'->'content'->>'markdown' FROM '(?m)^# (.+)')),''),'Played session') AS title,
              heads.payload->'checkpoint'->>'captured_at' AS ended_at,
              COALESCE((SELECT count(*) FROM jsonb_each_text(
                COALESCE(heads.payload->'checkpoint'->'progress'->'notes_by_element_id','{}'::jsonb)
              ) AS note(element_id,note_text) WHERE btrim(note.note_text)<>''),0)
              + CASE WHEN btrim(COALESCE(heads.payload->>'final_thoughts',''))<>'' THEN 1 ELSE 0 END AS source_count
              FROM (
                SELECT DISTINCT ON (e.run_id) e.run_id,e.revision_n,e.payload
                FROM play.session_review_revision e JOIN play.run r USING(run_id)
                WHERE r.world_id=%s AND r.lifecycle_status='active'
                ORDER BY e.run_id,e.revision_n DESC
              ) heads
              WHERE heads.payload->>'status'='ended'
              ORDER BY heads.payload->'checkpoint'->>'captured_at' DESC,heads.run_id LIMIT %s""",
              (world_id, limit))
            rows = cur.fetchall()
    result = []
    for row in rows:
        run_id = str(row["run_id"])
        revision = row["revision_n"]
        result.append({
            "run_id": run_id,
            "review_revision": revision,
            "title": str(row["title"] or "Played session").strip()[:240] or "Played session",
            "ended_at": row["ended_at"],
            "source_count": row["source_count"],
            "citation_url": "/play?" + urlencode({
                "world": world_id,
                "run": run_id,
                "evidence_revision": revision,
            }),
        })
    return {
        "schema_version": "dmb_session_evidence_index_v1",
        "world_id": world_id,
        "sessions": result,
    }
