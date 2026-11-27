"""Offline report on retained ordinary Build artifacts; no provider calls."""
from hashlib import sha256
import json
import math
from pathlib import Path

from .assessment import REPORT_SCHEMA, assess, rubric_sha256
from .capture_observation import _body, observe
from .related_page_probe import acquisition_labels, catalog_discovery_count, fixture_related_labels
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


def response_latency(answer):
    """Report the ordinary capture's dispatch-to-response clock, if retained."""
    if "elapsed_ms" not in answer:
        return None
    value = answer["elapsed_ms"]
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError("Invalid response latency")
    return {"elapsed_ms": value, "basis": "ordinary capture request cycle through response envelope processing",
            "scope": "includes any context wrapper; excludes later history, trace and review"}


def read_semantic_review(path, expected_sha256, *, case_id, rubric, fixture_sha256, artifact_hashes):
    """Bind reviewer assertions to exact evidence; identity/independence are not verified."""
    if (not isinstance(expected_sha256, str) or len(expected_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_sha256)):
        raise ValueError("A frozen semantic review digest is required")
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("Semantic review differs from its frozen digest")
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("Semantic review contains duplicate keys")
            result[key] = value
        return result
    review = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(review, dict) or set(review) != {"schema", "case_id", "rubric_sha256", "fixture_set_sha256", "reviewer", "artifacts", "judgments"}:
        raise ValueError("Malformed semantic review")
    if (review["schema"] != "dmb_negative_retrieval_semantic_review_v1"
            or review["case_id"] != case_id or review["rubric_sha256"] != rubric_sha256(rubric)
            or not isinstance(fixture_sha256, str) or review["fixture_set_sha256"] != fixture_sha256
            or not isinstance(review["reviewer"], str) or not review["reviewer"].strip()):
        raise ValueError("Semantic review case, rubric, fixture or reviewer differs")
    required = {"request", "answer-http", "history-after", "context-trace", "fixture-sources", "fixture-pin"}
    prior_histories = {name for name in ("history-before", "fresh-history") if name in artifact_hashes}
    required |= prior_histories
    pinned = review["artifacts"]
    if (not isinstance(pinned, dict) or not prior_histories or not required <= set(pinned)
            or any(name not in artifact_hashes or digest != artifact_hashes[name] for name, digest in pinned.items())):
        raise ValueError("Semantic review does not bind the captured artifacts")
    judgments = review["judgments"]
    if not isinstance(judgments, dict) or set(judgments) != {"semantic_quality", "required_support"}:
        raise ValueError("Semantic review judgments are malformed")
    projected = {}
    for name, judgment in judgments.items():
        if judgment is None:
            projected[name] = None
        elif (not isinstance(judgment, dict) or set(judgment) != {"value", "rationale"}
              or type(judgment["value"]) is not bool or not isinstance(judgment["rationale"], str)
              or not judgment["rationale"].strip()):
            raise ValueError("Semantic review judgment requires a boolean and rationale")
        else:
            projected[name] = judgment["value"]
    if not rubric["required_reads"] and projected["required_support"] is not None:
        raise ValueError("Source-support judgment requires a source-required case")
    return {"sha256": expected_sha256, "reviewer": review["reviewer"],
            "independence": "unverified", "judgments": projected}


def report_case(directory, fixture, rubric, *, expected_fixture_sha256=None, fixture_set=None,
                review_path=None, expected_review_sha256=None):
    """Report only what the bound capture proves; never infer semantic grades."""
    if (review_path is None) != (expected_review_sha256 is None):
        raise ValueError("Semantic review requires both a path and frozen digest")
    directory = Path(directory)
    names = ("request", "history-after", "context-trace", "answer-http", "related-page-probe")
    paths = {name: directory / (name + ".json") for name in names}
    for name in ("history-before", "fresh-history", "fixture-sources", "fixture-pin", "terminal", "native-graph-probe", "source-window-probe"):
        paths[name] = directory / (name + ".json")
    present = {name: path for name, path in paths.items() if path.is_file()}
    # Bind and parse the same immutable byte snapshot, not a second file read.
    raw_artifacts = {name: path.read_bytes() for name, path in present.items()}
    hashes = {name: sha256(raw).hexdigest() for name, raw in raw_artifacts.items()}
    rows = {name: json.loads(raw) for name, raw in raw_artifacts.items()}
    source_window = None
    if "source-window-probe" in rows:
        from .source_window import validate_artifact
        source_window = validate_artifact(rows["source-window-probe"], fixture["id"])
    native_probe = None
    if "native-graph-probe" in rows:
        value = rows["native-graph-probe"]
        if (not isinstance(value, dict) or value.get("schema") != "dmb_negative_retrieval_native_graph_probe_v1"
                or value.get("coverage") != "partial" or value.get("case_id") != fixture["id"]
                or value.get("window") not in (None, "turn_post_v1")
                or not isinstance(value.get("status"), str)
                or value.get("status") not in {"observed", "not_started", "dispatch_uncertain"}
                or (value.get("status") == "not_started" and value.get("records") != [])):
            raise ValueError("Native Graph probe is malformed or belongs to another case")
        native_probe = {"status": value["status"], "window": value.get("window"),
                        "counts": summarize_records(value.get("records"))}
    probe = rows.get("related-page-probe")
    partial_probe = None
    if "related-page-probe" in rows:
        if (not isinstance(probe, dict) or probe.get("schema") != "dmb_negative_retrieval_related_page_probe_v1"
                or probe.get("coverage") != "partial" or probe.get("case_id") != fixture["id"]):
            raise ValueError("Related-page probe belongs to another case")
        records = probe.get("records")
        status = probe.get("status")  # Legacy captures did not record the dispatch window.
        if (status not in (None, "observed", "not_started", "dispatch_uncertain")
                or probe.get("window") not in (None, "turn_post_v1")
                or (status == "not_started" and records != [])):
            raise ValueError("Invalid related-page probe status")
        partial_probe = {"status": status, "window": probe.get("window"),
                         "catalog_discoveries": catalog_discovery_count(records),
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
        if review_path is not None:
            raise ValueError("Semantic review cannot bind an incomplete capture")
        return {"schema": REPORT_SCHEMA, "case_id": fixture["id"], "rubric_sha256": rubric_sha256(rubric),
                "status": "unproven", "missing_artifacts": missing,
                "artifact_sha256": hashes, "partial_probe": partial_probe, "partial_native_graph_probe": native_probe, "partial_source_window": source_window,
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
    # Bind the primary page and retained dialogue before reporting any ID match.
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
    observed = observe(rows["request"], rows["history-after"], rows["context-trace"], rows["answer-http"],
                       related_labels=related_labels)
    # Only current POST-window probes can attribute observed activity to this
    # turn. Older broad-window records remain visible as diagnostics but can
    # include history/setup work; they cannot establish a turn violation.
    turn_window = (partial_probe is not None and native_probe is not None
        and partial_probe["window"] == native_probe["window"] == "turn_post_v1"
        and partial_probe["status"] == native_probe["status"]
        and native_probe["status"] in {"observed", "dispatch_uncertain"})
    related_turn = native_turn = turn_window
    primary = rows['request'].get('primary_work')
    primary_id = primary.get('object_id') if isinstance(primary, dict) else None
    primary_revision = primary.get('expected_revision') if isinstance(primary, dict) else None
    world = rows['request'].get('owner_scope')
    world_id = world.get('world_id') if isinstance(world, dict) else None
    primary_pointer = None
    if (fixture_bound is True and isinstance(primary_id, str) and primary_id
            and isinstance(world_id, str) and world_id and type(primary_revision) is int and primary_revision > 0
            and 'current-page' not in label_by_document.values()):
        primary_pointer = {'document_id': primary_id, 'world_id': world_id, 'registry_revision': primary_revision}
    primary_id_matches = None
    if fixture_bound is True and related_turn and isinstance(primary_id, str) and primary_id:
        primary_id_matches = sum(row.get('owner') == 'related_page_materialization'
            and row.get('document_id') == primary_id for row in probe['records'])
    # A read attempt can demonstrate unnecessary acquisition. Display-only
    # trace items and ID-only returns do not bind a body to the
    # fixture. Only an exact pointer and observed matching returned bytes do.
    observed["completed_reads"] = []
    if related_turn:
        inventory = rows["fixture-sources"]["before"] if fixture_bound is True else []
        for record in probe["records"]:
            if record["owner"] != "related_page_materialization":
                continue
            primary = acquisition_labels([record], primary_pointer=primary_pointer)
            observed["reads"] += (primary if primary == ["current-page"]
                                  else fixture_related_labels([record], inventory))
        if fixture_bound is True:
            # The current-page label is reserved for the primary work, never
            # credit a similarly labelled related page as the primary source.
            observed["completed_reads"] += [label for label in fixture_related_labels(
                probe["records"], inventory, completed_only=True) if label != "current-page"]
            # verify_fixture binds the clean primary snapshot and its hash to
            # the frozen case. Credit only a returned materialization whose
            # input pointer and returned bytes independently match that basis.
            page = fixture.get("page")
            work = rows["request"].get("primary_work")
            if (primary_pointer is not None and isinstance(page, str) and isinstance(work, dict)
                    and work.get("expected_content_sha256") == sha256(page.encode("utf-8")).hexdigest()):
                primary_inventory = [{**primary_pointer, "label": "current-page",
                                      "content_sha256": work["expected_content_sha256"]}]
                observed["completed_reads"] += fixture_related_labels(
                    probe["records"], primary_inventory, completed_only=True)
    if native_turn:
        for owner in ("native_graph_selected_read", "native_graph_authored_reference_read",
                      "native_corpus_authored_source_read", "native_corpus_member_read", "native_corpus_direct_read",
                      "native_corpus_body_open", "app_source_body_read", "app_source_body_read_batch",
                      "app_source_body_read_revision",
                      "native_graph_body_open", "native_graph_body_open_batch", "native_pdf_source_load"):
            counts = native_probe["counts"][owner]
            if counts is not None:
                observed["reads"].extend([UNKNOWN] * sum(counts.values()))
    related_discovery = catalog_discovery_count(probe.get("records")) if related_turn else 0
    native_discovery = (sum(native_probe["counts"]["native_corpus_discovery"].values()) if native_turn else 0)
    stage_counts = observed["native_activity"]["counts_by_policy"]
    search_stages = [stage_counts.get(f"native_source_search_progress_v{version}", {}).get(action, 0)
                     for version in (1, 2) for action in ("expanded", "retrieved", "retained")]
    # Trace events are not paired or proven unique, even within one stage.
    # Any such event proves at least one search activity, never multiple calls.
    # The owner probe records individual calls and may witness the same search.
    from .source_window import known_scoped_pdf_discovery
    pdf_discovery = (fixture_bound is True and observed["completed_turn"] is True
        and turn_window and native_probe["status"] == "observed"
        and terminal is not None and terminal["status"] == "observed" and terminal["error_type"] is None
        and known_scoped_pdf_discovery(source_window))
    search_lower_bound = max(native_discovery, int(any(search_stages)), int(pdf_discovery))
    observed["catalog_discoveries"] = (related_discovery + search_lower_bound
        if related_turn or native_turn or search_lower_bound else None)
    observed["catalog_journal_complete"] = None
    observed["graph_query_attempts"] = (sum(native_probe["counts"]["native_graph_query"].values())
                                          if native_turn else None)
    observed["graph_query_journal_complete"] = None
    # A recognized single-text entry or nonempty batch path proves an attempted read,
    # never a returned body. Require a bound, completed POST; old/unknown
    # implementations and all uncertain windows remain diagnostic only.
    from .source_window import known_scoped_text_attempt, known_scoped_app_attempt, known_scoped_pdf_attempt
    if (fixture_bound is True and observed["completed_turn"] is True
            and turn_window and native_probe["status"] == "observed"
            and terminal is not None and terminal["status"] == "observed" and terminal["error_type"] is None
            and (known_scoped_text_attempt(source_window) or known_scoped_app_attempt(source_window)
                 or known_scoped_pdf_attempt(source_window))
            and UNKNOWN not in observed["reads"]):
        observed["reads"].append(UNKNOWN)
    reviewed = None
    if review_path is not None:
        if fixture_bound is not True:
            raise ValueError("Semantic review requires a verified fixture binding")
        reviewed = read_semantic_review(review_path, expected_review_sha256, case_id=fixture["id"],
            rubric=rubric, fixture_sha256=expected_fixture_sha256, artifact_hashes=hashes)
        observed.update(reviewed["judgments"])
    grade = assess(rubric, observed)
    return {**grade, "schema": REPORT_SCHEMA, "case_id": fixture["id"], "rubric_sha256": rubric_sha256(rubric),
            "status": "unproven",
            "observation_status": grade["status"], "primary_context_verified": primary_bound,
            "related_context_verified": related_bound, "fixture_context_verified": fixture_bound,
            "fixture_pin_verified": pin_bound,
            "capture_environment_verified": None,
            "capture_terminal": terminal, "partial_probe": partial_probe, "partial_native_graph_probe": native_probe, "partial_source_window": source_window,
            "semantic_review": reviewed,
            "fixture_binding_error": binding_error if not fixture_bound else None,
            "artifact_sha256": hashes,
            "http_status": observed["http_status"], "response_latency": response_latency(rows["answer-http"]),
            "terminal_status": observed["terminal_status"],
            "trace_capture_status": observed["trace_capture_status"],
            "trace_acquisitions": observed["observed_acquisitions"],
            "decision_observations": observed["decision_observations"],
            "native_activity": observed["native_activity"],
            "primary_document_id_attempts_diagnostic": primary_id_matches,
            "current_page_metadata_attempts_diagnostic": (
                sum(row["owner"] == "current_page_metadata" for row in probe["records"])
                if related_turn and any(row["owner"] == "current_page_metadata" for row in probe["records"]) else None),
            "related_page_probe": probe["records"],
            "limits": ["Probe and trace are a partial acquisition journal.",
                       "Capture environment and prior citations are not independently verified here.",
                       "Semantic review independence is not verified; mutation, inline delivery, continuation and reopen evidence are not assessed here."]}
