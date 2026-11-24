"""Offline report on retained ordinary Build artifacts; no provider calls."""
from hashlib import sha256
import json
from pathlib import Path

from .assessment import assess
from .capture_observation import observe
from .related_page_probe import acquisition_labels


def report_case(directory, fixture, rubric, *, related_labels=None, source_labels=None):
    """Report only what the bound capture proves; never infer semantic grades."""
    directory = Path(directory)
    names = ("request", "history-after", "context-trace", "answer-http", "related-page-probe")
    paths = {name: directory / (name + ".json") for name in names}
    for name in ("history-before", "fresh-history", "fixture-sources"):
        paths[name] = directory / (name + ".json")
    present = {name: path for name, path in paths.items() if path.is_file()}
    hashes = {name: sha256(path.read_bytes()).hexdigest() for name, path in present.items()}
    missing = [name for name in names if name not in present]
    if missing:
        return {"case_id": fixture["id"], "status": "unproven", "missing_artifacts": missing,
                "artifact_sha256": hashes}
    rows = {name: json.loads(path.read_text()) for name, path in present.items()}
    if rows["request"].get("message") != fixture["request"]:
        raise ValueError("Capture request differs from the fixture")
    probe = rows["related-page-probe"]
    if (probe.get("schema") != "dmb_negative_retrieval_related_page_probe_v1"
            or probe.get("coverage") != "partial" or probe.get("case_id") != fixture["id"]):
        raise ValueError("Related-page probe belongs to another case")
    observed = observe(rows["request"], rows["history-after"], rows["context-trace"], rows["answer-http"],
                       related_labels=related_labels, source_labels=source_labels)
    observed["reads"] += acquisition_labels(probe.get("records"))
    grade = assess(rubric, observed)
    # Use the history belonging to the request, not a previous active conversation.
    # A failed/missing binding is unqualified, even if a violation was observed.
    from .fixture_binding import verify_fixture
    primary_bound = None
    binding_error = None
    for name in ("fresh-history", "history-before"):
        if name not in rows:
            continue
        try:
            verify_fixture(fixture, rows["request"], rows[name], rows["history-after"])
            primary_bound = True
            break
        except (ValueError, KeyError, TypeError) as exc:
            binding_error = type(exc).__name__
    from .fixture_sources import verify_related_record
    related_bound = None
    if "fixture-sources" in rows:
        try:
            verify_related_record(rows["request"], fixture, rows["fixture-sources"])
            related_bound = True
        except (ValueError, KeyError, TypeError) as exc:
            binding_error = type(exc).__name__
    fixture_bound = True if primary_bound and related_bound else None
    return {"case_id": fixture["id"], **grade, "status": "unproven",
            "observation_status": grade["status"], "primary_context_verified": primary_bound,
            "related_context_verified": related_bound, "fixture_context_verified": fixture_bound,
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
