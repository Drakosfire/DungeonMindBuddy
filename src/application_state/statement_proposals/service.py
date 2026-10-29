"""Transactional proposal claims and immutable output/review acknowledgments."""
from copy import deepcopy
from uuid import UUID
from psycopg.types.json import Jsonb
from application_state.cli import assert_at_head
from application_state.config import load_runtime_dsn
from application_state.unit_of_work import unit_of_work
from application_state.errors import ApplicationStateConflictError, ApplicationStateIntegrityError
from graph_memory.extraction.qualified_statement_proposals import digest


def _dsn():
    dsn = load_runtime_dsn()
    assert_at_head(dsn=dsn)
    return dsn


def _load(row):
    if row is None:
        return None
    payload = row[0]
    try:
        if set(payload) != {"operation_id", "owner", "intent", "intent_digest", "input", "state", "revision", "wire", "wire_digest", "raw_output", "result", "failure", "reviews", "lifecycle"}:
            raise ValueError("Unexpected proposal work fields")
        UUID(payload["operation_id"])
        if digest(payload["intent"]) != payload["intent_digest"] or payload["revision"] < 1 or not payload["owner"]:
            raise ValueError("Invalid proposal intent")
        if payload["state"] not in {"claimed", "entered", "completed", "failed"}:
            raise ValueError("Invalid proposal state")
        if (payload["wire"] is None) != (payload["wire_digest"] is None):
            raise ValueError("Incomplete prepared request")
        if payload["wire"] is not None:
            from hashlib import sha256
            if sha256(payload["wire"].encode()).hexdigest() != payload["wire_digest"]:
                raise ValueError("Prepared request drift")
        if payload["state"] == "completed" and (payload["result"] is None or payload["raw_output"] is None or not payload["lifecycle"] or payload["lifecycle"][-1]["outcome"] != "response_received"):
            raise ValueError("Incomplete proposal result")
        outcomes = [e["outcome"] for e in payload["lifecycle"]]
        if outcomes not in [[], ["sending"], ["known_not_sent"], ["sending", "known_not_sent"], ["sending", "response_received"], ["sending", "outcome_unknown"]]:
            raise ValueError("Invalid dispatch history")
        if payload["state"] == "entered" and payload["wire"] is None:
            raise ValueError("Missing prepared request")
        if payload["state"] != "completed" and (payload["result"] is not None or payload["reviews"]):
            raise ValueError("Uncompleted work cannot carry a result or reviews")
        keys = [r["decision_id"] for r in payload["reviews"]]
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate review decision")
        for review in payload["reviews"]:
            if digest(review["intent"]) != review["intent_digest"] or digest(review["prepared_packet"]) != review["packet_digest"]:
                raise ValueError("Review intent drift")
        return payload
    except (ValueError, KeyError, TypeError) as exc:
        raise ApplicationStateIntegrityError("Stored proposal work is invalid") from exc


def _read(conn, key, lock=False):
    return _load(conn.execute("SELECT payload FROM ingest.statement_proposal_operation WHERE operation_id=%s" + (" FOR UPDATE" if lock else ""), (key,)).fetchone())


def _owned(record, owner, world):
    if record and (record["owner"] != owner or record["intent"]["managed_world_id"] != world):
        raise ApplicationStateConflictError("Proposal operation belongs to another owner/World")
    return record


def read(key, owner, world):
    with unit_of_work(_dsn()) as conn:
        return _owned(_read(conn, key), owner, world)


def claim(key, owner, intent, input_packet):
    record = {"operation_id": str(key), "owner": owner, "intent": intent, "intent_digest": digest(intent),
              "input": input_packet, "state": "claimed", "revision": 1, "wire": None, "wire_digest": None,
              "raw_output": None, "result": None, "failure": None, "reviews": [], "lifecycle": []}
    _load((record,))
    with unit_of_work(_dsn()) as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", ("statement-proposal:" + str(key),))
        old = _owned(_read(conn, key), owner, intent["managed_world_id"])
        if old:
            if old["intent_digest"] != record["intent_digest"] or old["input"] != input_packet:
                raise ApplicationStateConflictError("Proposal key has a different intent")
            return old, False
        conn.execute("INSERT INTO ingest.statement_proposal_operation(operation_id,owner,world_id,payload) VALUES(%s,%s,%s,%s)",
                     (key, owner, intent["managed_world_id"], Jsonb(record)))
        return record, True


def change(record, *, state=None, wire=None, raw_output=None, result=None, failure=None, review=None, event=None):
    """Exact CAS; an unsaved packet or output is never acknowledged."""
    with unit_of_work(_dsn()) as conn:
        current = _owned(_read(conn, record["operation_id"], True), record["owner"], record["intent"]["managed_world_id"])
        if current is None or current["revision"] != record["revision"]:
            raise ApplicationStateConflictError("Proposal work revision changed")
        updated = deepcopy(current)
        if event is not None:
            if current["state"] != "entered" or event["outcome"] not in {"sending", "known_not_sent", "response_received", "outcome_unknown"}:
                raise ApplicationStateConflictError("Invalid dispatch lifecycle")
            if any(e["outcome"] == event["outcome"] for e in current["lifecycle"]):
                raise ApplicationStateConflictError("Repeated dispatch lifecycle")
            updated["lifecycle"].append(event)
        elif review is not None:
            if current["state"] != "completed":
                raise ApplicationStateConflictError("Only completed proposals can be reviewed")
            if any(r["decision_id"] == review["decision_id"] for r in current["reviews"]):
                raise ApplicationStateConflictError("Review decision is already recorded")
            updated["reviews"].append(review)
        elif state == "entered" and current["state"] == "claimed" and wire is not None:
            from hashlib import sha256
            updated.update(state=state, wire=wire, wire_digest=sha256(wire.encode()).hexdigest())
        elif state in {"completed", "failed"} and current["state"] in {"claimed", "entered"}:
            if state == "completed" and current["state"] != "entered":
                raise ApplicationStateConflictError("No acknowledged dispatch")
            updated.update(state=state, raw_output=raw_output, result=result, failure=failure)
        else:
            raise ApplicationStateConflictError("Invalid proposal transition")
        updated["revision"] += 1
        _load((updated,))
        conn.execute("UPDATE ingest.statement_proposal_operation SET payload=%s WHERE operation_id=%s", (Jsonb(updated), record["operation_id"]))
        return updated
