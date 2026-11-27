"""Capture the registered recap input at the extraction handoff, before dispatch."""

from hashlib import sha256
import json
from contextlib import contextmanager
from unittest.mock import patch

from .artifacts import immutable_save


HANDOFF_STOP = "Benchmark stopped at the registered extraction handoff"


class NameReviewCaptureComplete(ValueError):
    """Deliberately stop before the extraction provider can be called."""


@contextmanager
def capture_extraction_handoff(directory):
    from apps.live_control_server.services import recap_graph_preview_ingest as owner
    from apps.live_control_server.services.source_artifact_registry import (
        load_registered_source_artifact_bytes,
    )

    handoff = []

    def stop(*, repo_root, campaign_id, session_id, source_artifact_id,
             name_review_record, **_):
        if handoff:
            raise ValueError("Benchmark received more than one extraction handoff")
        handoff.append(None)
        if not name_review_record:
            raise ValueError("Extraction handoff is missing reviewed name decisions")

        original_id = name_review_record["original_source_artifact_id"]
        sources = {}
        for label, artifact_id in (("original", original_id), ("effective", source_artifact_id)):
            artifact, body = load_registered_source_artifact_bytes(repo_root, artifact_id)
            sources[label] = {
                "artifact_id": artifact_id,
                "sha256": artifact.content_sha256,
                "text": body.decode("utf-8"),
            }
        handoff[0] = {
            "campaign_id": campaign_id,
            "session_id": session_id,
            "sources": sources,
            "name_review": name_review_record,
        }
        immutable_save(directory, "extraction-handoff", handoff[0])
        raise NameReviewCaptureComplete(HANDOFF_STOP)

    with patch.object(owner, "run_recap_production_extraction", stop):
        yield handoff


def validate_pin(pin):
    fields = {"campaign_id", "session", "original", "expected_effective",
              "corrections"}
    if not isinstance(pin, dict) or set(pin) - {"edited_original"} != fields:
        raise ValueError("Ingest name review needs one exact recap and correction pin")
    if type(pin["session"]) is not int or pin["session"] < 1:
        raise ValueError("Ingest name review requires a positive session number")
    if any(not isinstance(value, str) or not value.strip()
           for key, value in pin.items() if key not in {"session", "corrections"}):
        raise ValueError("Ingest name review text pins must be nonempty")
    corrections = pin["corrections"]
    fields = {"correction_label", "context_label", "replacement", "expected_context"}
    if (not isinstance(corrections, list) or not corrections
            or any(not isinstance(row, dict) or set(row) != fields
                   or any(not isinstance(value, str) or not value.strip() for value in row.values())
                   for row in corrections)
            or len({row["correction_label"] for row in corrections}) != len(corrections)
            or any(row["expected_context"] not in pin.get("edited_original", pin["original"])
                   for row in corrections)):
        raise ValueError("Ingest name review requires distinct exact occurrence corrections")
    if pin.get("edited_original") == pin["original"]:
        raise ValueError("Stale review control requires a changed recap")


def record_result(directory, output, pin, handoff, driver_failed, rejected_writes, graph_reads):
    from apps.live_control_server.services.source_artifact_registry import _normalize_source_text

    path = output / "browser-timing.json"
    observed = json.loads(path.read_bytes()).get("ingest_name_review", {}) if path.is_file() else {}
    owner = (handoff[0] if handoff else None) or {}
    sources = owner.get("sources", {})
    original = pin.get("edited_original", pin["original"])
    checks = {
        "mounted_occurrence": observed.get("displayed_context") == [
            row["expected_context"] for row in pin["corrections"]
        ] and not observed.get("error"),
        "stale_review_invalidated": "edited_original" not in pin or (
            observed.get("stale_controls_hidden") is True
            and observed.get("extractions_before_fresh_review") == 0
            and bool(observed.get("fresh_review_id"))
            and observed["fresh_review_id"] != observed.get("initial_review_id")),
        "exact_scope": owner.get("campaign_id") == pin["campaign_id"]
            and owner.get("session_id") == f"session-{pin['session']}",
        "original_preserved": sources.get("original", {}).get("text") == _normalize_source_text(original),
        "effective_text_matches": sources.get("effective", {}).get("text") == pin["expected_effective"],
        "single_extraction": len(handoff) == 1 and observed.get("extraction_posts") == 1
            and observed.get("extraction_status") == 422 and observed.get("extraction_detail") == HANDOFF_STOP,
        "review_count": observed.get("review_posts") == (2 if "edited_original" in pin else 1),
        "no_other_writes": not rejected_writes and observed.get("turn_posts") == 0,
    }
    evidence = {}
    for name, witness in (("mounted", path), ("owner", directory / "extraction-handoff.json")):
        if witness.is_file():
            evidence[name] = {"path": str(witness), "sha256": sha256(witness.read_bytes()).hexdigest()}
    immutable_save(directory, "fixture-result", {
        "status": "observed" if all(checks.values()) and not driver_failed else "incomplete",
        "checks": checks, "browser": observed, "rejected_writes": rejected_writes,
        "mounted_graph_reads": graph_reads, "evidence": evidence,
        "extraction_boundary": "provider_free_registered_input",
    })


def allowed_request(payload, path, world, pin):
    if not isinstance(payload, dict):
        return False
    if path == "/api/live/native-graph-explorer/graph":
        return payload.get("managed_world_id") == world
    if (
        payload.get("operation"), payload.get("managed_world_id"),
        payload.get("campaign_id"), payload.get("session"),
    ) != ("generate_recap_memory", world, pin["campaign_id"], pin["session"]):
        return False
    original = pin.get("edited_original", pin["original"])
    if path == "/api/live/recap-name-review":
        return payload.get("raw_text") in (pin["original"], original)
    return (path == "/api/live/recap-ingest" and payload.get("raw_text") == original
            and payload.get("include_graph_extraction") is True and bool(payload.get("name_review"))
            and not any(payload.get(field) for field in (
                "native_recap_run_id", "native_recap_resume", "session_evidence",
            )))
