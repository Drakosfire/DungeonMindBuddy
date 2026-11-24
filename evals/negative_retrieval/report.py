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
    present = {name: path for name, path in paths.items() if path.is_file()}
    hashes = {name: sha256(path.read_bytes()).hexdigest() for name, path in present.items()}
    missing = [name for name in names if name not in present]
    if missing:
        return {"case_id": fixture["id"], "status": "unproven", "missing_artifacts": missing,
                "artifact_sha256": hashes}
    rows = {name: json.loads(path.read_text()) for name, path in paths.items()}
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
    # Request text alone does not prove the frozen page and conversation prefix.
    # Preserve observed violations, but do not grade the case until a future
    # fixture-bound verifier independently establishes that precondition.
    return {"case_id": fixture["id"], **grade, "status": "unproven",
            "observation_status": grade["status"], "fixture_context_verified": None,
            "artifact_sha256": hashes,
            "http_status": observed["http_status"], "terminal_status": observed["terminal_status"],
            "trace_capture_status": observed["trace_capture_status"],
            "trace_acquisitions": observed["observed_acquisitions"],
            "related_page_probe": probe["records"],
            "limits": ["Probe and trace are a partial acquisition journal.",
                       "Frozen page and conversation-prefix binding are not verified here.",
                       "Semantic, mutation, inline delivery, continuation and reopen evidence are not assessed here."]}
