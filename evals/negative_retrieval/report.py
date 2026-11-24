"""Offline report on retained ordinary Build artifacts; no provider calls."""
from hashlib import sha256
import json
from pathlib import Path

from .assessment import REPORT_SCHEMA, assess
from .capture_observation import _body, observe
from .related_page_probe import acquisition_labels, catalog_discovery_count


def verify_fixture_pin(fixture, record, expected_fixture_sha256, fixture_set):
    """Check case membership in the independently pinned fixture mapping."""
    from .capture import fixture_sha256

    if (not isinstance(expected_fixture_sha256, str) or len(expected_fixture_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_fixture_sha256)
            or not isinstance(fixture_set, dict)
            or fixture_sha256(fixture_set) != expected_fixture_sha256
            or fixture_set.get(fixture.get("id")) != fixture
            or not isinstance(record, dict)
            or record.get("schema") != "dmb_negative_retrieval_fixture_pin_v1"
            or record.get("case_id") != fixture.get("id")
            or record.get("fixture_set_sha256") != expected_fixture_sha256
            or record.get("case_sha256") != fixture_sha256({fixture["id"]: fixture})):
        raise ValueError("Fixture pin does not bind this case to the frozen set")
    return True


def report_case(directory, fixture, rubric, *, expected_fixture_sha256=None, fixture_set=None):
    """Report only what the bound capture proves; never infer semantic grades."""
    directory = Path(directory)
    names = ("request", "history-after", "context-trace", "answer-http", "related-page-probe")
    paths = {name: directory / (name + ".json") for name in names}
    for name in ("history-before", "fresh-history", "fixture-sources", "fixture-pin"):
        paths[name] = directory / (name + ".json")
    present = {name: path for name, path in paths.items() if path.is_file()}
    hashes = {name: sha256(path.read_bytes()).hexdigest() for name, path in present.items()}
    missing = [name for name in names if name not in present]
    if missing:
        return {"schema": REPORT_SCHEMA, "case_id": fixture["id"], "status": "unproven", "missing_artifacts": missing,
                "artifact_sha256": hashes}
    rows = {name: json.loads(path.read_text()) for name, path in present.items()}
    if rows["request"].get("message") != fixture["request"]:
        raise ValueError("Capture request differs from the fixture")
    probe = rows["related-page-probe"]
    if (probe.get("schema") != "dmb_negative_retrieval_related_page_probe_v1"
            or probe.get("coverage") != "partial" or probe.get("case_id") != fixture["id"]):
        raise ValueError("Related-page probe belongs to another case")
    from .fixture_sources import related_trace_labels, verify_related_record
    related_bound = None
    binding_error = None
    related_labels = {}
    label_by_document = {}
    pin_bound = None
    if "fixture-pin" in rows:
        try:
            verify_fixture_pin(fixture, rows["fixture-pin"], expected_fixture_sha256, fixture_set)
            pin_bound = True
        except (ValueError, KeyError, TypeError) as exc:
            binding_error = type(exc).__name__
    if "fixture-sources" in rows:
        try:
            verify_related_record(rows["request"], fixture, rows["fixture-sources"])
            related_bound = True
            inventory = rows["fixture-sources"]["before"]
            related_labels = related_trace_labels(_body(rows["context-trace"]), rows["fixture-sources"])
            label_by_document = {row["document_id"]: row["label"] for row in inventory}
        except (ValueError, KeyError, TypeError) as exc:
            binding_error = type(exc).__name__
    observed = observe(rows["request"], rows["history-after"], rows["context-trace"], rows["answer-http"],
                       related_labels=related_labels)
    observed["reads"] += acquisition_labels(probe.get("records"), label_by_document=label_by_document)
    observed["catalog_discoveries"] = catalog_discovery_count(probe.get("records"))
    observed["catalog_journal_complete"] = None
    grade = assess(rubric, observed)
    # Use the history belonging to the request, not a previous active conversation.
    # A failed/missing binding is unqualified, even if a violation was observed.
    from .fixture_binding import verify_fixture
    primary_bound = None
    for name in ("fresh-history", "history-before"):
        if name not in rows:
            continue
        try:
            verify_fixture(fixture, rows["request"], rows[name], rows["history-after"])
            primary_bound = True
            break
        except (ValueError, KeyError, TypeError) as exc:
            binding_error = type(exc).__name__
    fixture_bound = True if primary_bound and related_bound and pin_bound else None
    return {**grade, "schema": REPORT_SCHEMA, "case_id": fixture["id"], "status": "unproven",
            "observation_status": grade["status"], "primary_context_verified": primary_bound,
            "related_context_verified": related_bound, "fixture_context_verified": fixture_bound,
            "fixture_pin_verified": pin_bound,
            "capture_environment_verified": None,
            "fixture_binding_error": binding_error if not fixture_bound else None,
            "artifact_sha256": hashes,
            "http_status": observed["http_status"], "terminal_status": observed["terminal_status"],
            "trace_capture_status": observed["trace_capture_status"],
            "trace_acquisitions": observed["observed_acquisitions"],
            "decision_observations": observed["decision_observations"],
            "related_page_probe": probe["records"],
            "limits": ["Probe and trace are a partial acquisition journal.",
                       "Capture environment and prior citations are not independently verified here.",
                       "Semantic, mutation, inline delivery, continuation and reopen evidence are not assessed here."]}
