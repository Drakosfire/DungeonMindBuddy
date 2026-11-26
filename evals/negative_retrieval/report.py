"""Offline report on retained ordinary Build artifacts; no provider calls."""
from hashlib import sha256
import json
from pathlib import Path

from .assessment import REPORT_SCHEMA, assess, rubric_sha256
from .capture_observation import _body, observe
from .related_page_probe import acquisition_labels, catalog_discovery_count
from .native_graph_probe import summarize_records
from .trace_observation import UNKNOWN


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
    for name in ("history-before", "fresh-history", "fixture-sources", "fixture-pin", "terminal", "native-graph-probe"):
        paths[name] = directory / (name + ".json")
    present = {name: path for name, path in paths.items() if path.is_file()}
    hashes = {name: sha256(path.read_bytes()).hexdigest() for name, path in present.items()}
    rows = {name: json.loads(path.read_text()) for name, path in present.items()}
    native_probe = None
    if "native-graph-probe" in rows:
        value = rows["native-graph-probe"]
        if (not isinstance(value, dict) or value.get("schema") != "dmb_negative_retrieval_native_graph_probe_v1"
                or value.get("coverage") != "partial" or value.get("case_id") != fixture["id"]
                or not isinstance(value.get("status"), str)
                or value.get("status") not in {"observed", "not_started"}
                or (value.get("status") == "not_started" and value.get("records") != [])):
            raise ValueError("Native Graph probe is malformed or belongs to another case")
        native_probe = {"status": value["status"], "counts": summarize_records(value.get("records"))}
    probe = rows.get("related-page-probe")
    partial_probe = None
    if "related-page-probe" in rows:
        if (not isinstance(probe, dict) or probe.get("schema") != "dmb_negative_retrieval_related_page_probe_v1"
                or probe.get("coverage") != "partial" or probe.get("case_id") != fixture["id"]):
            raise ValueError("Related-page probe belongs to another case")
        records = probe.get("records")
        partial_probe = {"catalog_discoveries": catalog_discovery_count(records),
                         "materialization_attempts": len(acquisition_labels(records)),
                         "raised_discoveries": sum(row["state"] == "raised" and row["owner"] == "related_catalog_discovery"
                                                   for row in records),
                         "raised_materializations": sum(row["state"] == "raised" and row["owner"] == "related_page_materialization"
                                                        for row in records)}
    terminal = rows.get("terminal")
    if "terminal" in rows:
        if (not isinstance(terminal, dict) or terminal.get("status") not in {"observed", "outcome_unknown"}
                or (terminal.get("error_type") is not None and not isinstance(terminal["error_type"], str))):
            raise ValueError("Invalid capture terminal record")
        terminal = {"status": terminal["status"], "error_type": terminal.get("error_type")}
    missing = [name for name in names if name not in present]
    if missing:
        return {"schema": REPORT_SCHEMA, "case_id": fixture["id"], "rubric_sha256": rubric_sha256(rubric),
                "status": "unproven", "missing_artifacts": missing,
                "artifact_sha256": hashes, "partial_probe": partial_probe, "partial_native_graph_probe": native_probe,
                "capture_terminal": terminal}
    if rows["request"].get("message") != fixture["request"]:
        raise ValueError("Capture request differs from the fixture")
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
    # The native probe cannot identify a source. A selected or authored read
    # attempt nevertheless proves acquisition for a source-free case; it must
    # not be silently omitted from the assessment. Query preparation alone is
    # not evidence that a source was read.
    if native_probe is not None:
        for owner in ("native_graph_selected_read", "native_graph_authored_reference_read",
                      "native_corpus_authored_source_read", "native_corpus_member_read", "native_corpus_direct_read",
                      "native_corpus_body_open"):
            counts = native_probe["counts"][owner]
            observed["reads"].extend([UNKNOWN] * sum(counts.values()))
    observed["catalog_discoveries"] = catalog_discovery_count(probe.get("records"))
    if native_probe is not None:
        observed["catalog_discoveries"] += sum(native_probe["counts"]["native_corpus_discovery"].values())
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
    return {**grade, "schema": REPORT_SCHEMA, "case_id": fixture["id"], "rubric_sha256": rubric_sha256(rubric),
            "status": "unproven",
            "observation_status": grade["status"], "primary_context_verified": primary_bound,
            "related_context_verified": related_bound, "fixture_context_verified": fixture_bound,
            "fixture_pin_verified": pin_bound,
            "capture_environment_verified": None,
            "capture_terminal": terminal, "partial_probe": partial_probe, "partial_native_graph_probe": native_probe,
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
