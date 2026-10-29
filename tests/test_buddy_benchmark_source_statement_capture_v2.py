"""Real pinned Core/WK lifecycle captures; synthetic meaning is independent gold."""

from copy import deepcopy
import hashlib

import pytest
from tests.test_source_statements import lane as native_lane, GM, BODY, service, advance
from apps.live_control_server.models.source_statements import ConfirmStatement
from evals.buddy_benchmark.source_statement_capture_v2 import (
    capture_native_lifecycle,
    evaluate_lifecycle,
    harness_statement,
    correspondence_key,
    native_publication_id,
    observe_lost_ack_retry,
)


@pytest.fixture
def lane(tmp_path, monkeypatch):
    return native_lane.__wrapped__(tmp_path, monkeypatch)


def lifecycle(lane, descendant=False, recovery=False):
    staged = service.prepare(lane.selection, GM)
    # Independently reviewed synthetic meaning and exact source witness, not a
    # copy of the producer's selected/published/read payload.
    receipt = lane.repo.get_native_source_admission_receipt(
        lane.world.world_id, lane.selection.source_admission_id
    )
    selected = lane.selection
    payload = {
        "schema": "dmb_source_statement_v1",
        "clause": {
            "world": lane.world.world_id,
            "campaign": "c1",
            "logical_source": {
                "namespace": receipt.origin.namespace,
                "object_id": receipt.origin.object_id,
            },
            "source_sha256": hashlib.sha256(BODY.encode()).hexdigest(),
            "start_byte": selected.start_byte,
            "end_byte": selected.end_byte,
            "clause_sha256": hashlib.sha256(
                BODY.encode()[selected.start_byte : selected.end_byte]
            ).hexdigest(),
        },
        "quote": BODY.encode()[selected.start_byte : selected.end_byte].decode(),
        "meaning": selected.meaning,
        "mode": selected.mode,
        "reporter": selected.reporter,
        "referents": sorted(selected.referents),
        "uncertainty": selected.uncertainty,
        "qualifications": selected.qualifications,
        "episode": selected.episode,
        "source_order": [o.model_dump() for o in selected.source_order],
        "embedded_content_factive": False,
        "assertion_target": "source_statement",
        "visibility": "gm",
        "proof": {
            "source_admission_id": selected.source_admission_id,
            "evidence_ref_id": selected.evidence_ref_id,
        },
    }
    parent = lane.repo.get_revision(
        lane.world.world_id, selected.expected_parent_revision_id
    ).revision
    review = [
        {
            "payload": payload,
            "parent_context": {
                "world": lane.world.world_id,
                "authority": "native_vnext",
                "campaign": "c1",
                "visibility": "gm",
                "revision": selected.expected_parent_revision_id,
                "domain_ref": parent.domain_contract_ref.model_dump(mode="json"),
                "profile_ref": parent.semantic_profile_ref.model_dump(mode="json"),
            },
        }
    ]

    def confirm(packet):
        return service.confirm(
            ConfirmStatement(
                **{k: packet[k] for k in ("envelope", "prepared", "token")}
            ),
            GM,
        )

    observed = None
    if recovery:

        def lose_ack(packet):
            confirm(packet)
            raise ConnectionError("injected acknowledgment loss after actual commit")

        observed = observe_lost_ack_retry(
            staged,
            lose_ack,
            confirm,
            lambda: service._recover(lane.repo, lane.world.world_id, payload),
            lambda: lane.repo.get_head(lane.world.world_id).head_revision_id,
        )
        confirmed = observed["retry_result"]
    else:
        confirmed = confirm(staged)
    if descendant:
        advance(lane)
    response = service.read_subject(
        managed_world_id=lane.world.world_id,
        campaign_id="c1",
        revision_id=lane.repo.get_head(lane.world.world_id).head_revision_id,
        entity_id=lane.ids["B"],
        principal=GM,
    )
    captured = capture_native_lifecycle(
        lane.repo, [{"prepare": staged, "confirm": confirmed}], response, GM
    )
    captured["recovery"] = observed
    return review, captured


@pytest.mark.parametrize("descendant", [False, True])
def test_real_distinct_stage_revisions(lane, descendant):
    review, captured = lifecycle(lane, descendant)
    result = evaluate_lifecycle(review, captured)
    assert not captured["acquisition_errors"]
    assert result["counts"]["fail"] == 0, result
    assert result["counts"]["unassessed"] == 1  # no lost acknowledgment executed
    assert (
        captured["records"][0]["selection_context"]["revision"]
        != captured["read_context"]["revision"]
    )
    assert result["full_system_ingestion_verified"] is False
    assert captured["execution"]["core_module"].endswith("dungeonmind/__init__.py")
    assert captured["execution"]["wk_module"].endswith("worldkeeper/__init__.py")


@pytest.mark.parametrize(
    "change",
    [
        "meaning",
        "episode",
        "reporter",
        "referents",
        "uncertainty",
        "qualifications",
        "embedded_content_factive",
        "proof",
        "quote",
        "source_order",
    ],
)
def test_changed_child_payload_is_observed_failure(lane, change):
    review, captured = lifecycle(lane)
    payload = captured["records"][0]["published_bundle"]["payload"]
    payload[change] = "tampered"
    result = evaluate_lifecycle(review, captured)
    assert result["counts"]["fail"] > 0


@pytest.mark.parametrize(
    "field",
    [
        "world",
        "campaign",
        "visibility",
        "domain_ref",
        "profile_ref",
        "revision",
        "authority",
    ],
)
def test_context_drift_is_not_normalized_away(lane, field):
    review, captured = lifecycle(lane)
    captured["read_context"][field] = "foreign"
    assert evaluate_lifecycle(review, captured)["counts"]["fail"] > 0


@pytest.mark.parametrize("missing", ["edges", "read_context", "source_bytes"])
def test_missing_proof_unassessed(lane, missing):
    review, captured = lifecycle(lane)
    captured[missing] = {} if missing == "source_bytes" else None
    assert evaluate_lifecycle(review, captured)["counts"]["unassessed"] > 1


def test_wrong_parent_and_native_identity_fail(lane):
    review, captured = lifecycle(lane)
    receipt = captured["records"][0]["confirm"]["result"]["receipt"]
    child = next(
        h
        for h in captured["headers"]
        if h["revision"] == receipt["published_revision_id"]
    )
    child["parent"] = "sibling"
    receipt["publication_id"] = correspondence_key(
        harness_statement(review[0]["payload"])["clause"]
    )
    result = evaluate_lifecycle(review, captured)
    assert (
        sum(
            c["status"] == "fail"
            for name, c in result["checks"].items()
            if name.endswith(("publication_parent", "native_publication_identity"))
        )
        == 2
    )


def test_missing_ancestry_and_partial_discovery_do_not_pass(lane):
    review, captured = lifecycle(lane, True)
    captured["headers"] = []
    captured["read_response"]["status"] = "partial"
    captured["read_response"]["gap_codes"] = ["unavailable"]
    result = evaluate_lifecycle(review, captured)
    assert result["counts"]["unassessed"] > 1
    assert result["checks"]["complete_discovery"]["status"] == "fail"


def test_harness_and_native_identity_are_distinct(lane):
    review, captured = lifecycle(lane)
    result = evaluate_lifecycle(review, captured)
    identities = result["identities"][0]
    assert identities["harness_key"] != native_publication_id(review[0]["payload"])
    assert identities["harness_semantic_digest"] != identities["native_semantic_digest"]


@pytest.mark.parametrize(
    "field",
    [
        "edge_id",
        "statement_id",
        "entity_id",
        "predicate",
        "direction",
        "scope",
        "visibility",
        "evidence_ref_ids",
    ],
)
def test_forged_typed_edge_fails(lane, field):
    review, captured = lifecycle(lane)
    captured["edges"][0][field] = "forged"
    result = evaluate_lifecycle(review, captured)
    assert any(
        name.endswith("authorized_about_discovery") and c["status"] == "fail"
        for name, c in result["checks"].items()
    )


def test_executed_lost_ack_retry_assessed(lane):
    review, captured = lifecycle(lane, recovery=True)
    result = evaluate_lifecycle(review, captured)
    assert result["counts"]["fail"] == 0, result
    assert result["counts"]["unassessed"] == 0


@pytest.mark.parametrize(
    "changed",
    [
        "retry_result",
        "packet_after",
        "head_after_retry",
        "result_before_first_call",
        "original_result",
    ],
)
def test_recovery_remint_or_changed_packet_refused(lane, changed):
    review, captured = lifecycle(lane, recovery=True)
    captured["recovery"][changed] = {} if changed != "head_after_retry" else "new-head"
    assert (
        evaluate_lifecycle(review, captured)["checks"][
            "executed_original_packet_recovery"
        ]["status"]
        == "fail"
    )


@pytest.mark.parametrize(
    "kind", ["cycle", "sibling", "missing", "wrong_world", "wrong_profile"]
)
def test_bad_descendant_chain(lane, kind):
    review, captured = lifecycle(lane, descendant=True)
    read = next(
        h
        for h in captured["headers"]
        if h["revision"] == captured["read_response"]["revision_id"]
    )
    if kind == "cycle":
        read["parent"] = read["revision"]
    elif kind == "sibling":
        read["parent"] = review[0]["parent_context"]["revision"]
    elif kind == "missing":
        read["parent"] = "missing-header"
    elif kind == "wrong_world":
        read["world"] = "other-world"
    else:
        read["profile_ref"] = {"foreign": True}
    result = evaluate_lifecycle(review, captured)
    status = next(
        c["status"]
        for name, c in result["checks"].items()
        if name.endswith("read_descends_from_child")
    )
    assert status == ("unassessed" if kind == "missing" else "fail")


def test_order_endpoint_not_selected_is_unassessed(lane):
    from apps.live_control_server.models.source_statements import SourceOrder

    first, second = BODY.splitlines(keepends=True)
    order = SourceOrder(
        before_start=0,
        before_end=len(first.encode()),
        before_sha256=hashlib.sha256(first.encode()).hexdigest(),
        after_start=len(first.encode()),
        after_end=len(BODY.encode()),
        after_sha256=hashlib.sha256(second.encode()).hexdigest(),
    )
    lane.selection = lane.selection.model_copy(update={"source_order": [order]})
    review, captured = lifecycle(lane)
    result = evaluate_lifecycle(review, captured)
    assert any(
        name.endswith("source_order:0") and c["status"] == "unassessed"
        for name, c in result["checks"].items()
    )


def multiple(lane):
    first_review, first_capture = lifecycle(lane)
    start = len(BODY.splitlines(keepends=True)[0].encode())
    lane.selection = lane.selection.model_copy(
        update={
            "start_byte": start,
            "end_byte": len(BODY.encode()),
            "clause_sha256": hashlib.sha256(BODY.encode()[start:]).hexdigest(),
            "expected_parent_revision_id": lane.repo.get_head(
                lane.world.world_id
            ).head_revision_id,
            "meaning": "Another source-local episode",
            "mode": "narrator",
            "reporter": None,
            "uncertainty": [],
            "episode": "episode-2",
        }
    )
    second_review, second_capture = lifecycle(lane)
    records = [
        {k: r[k] for k in ("prepare", "confirm")}
        for r in first_capture["records"] + second_capture["records"]
    ]
    capture = capture_native_lifecycle(
        lane.repo, records, second_capture["read_response"], GM
    )
    return first_review + second_review, capture


def test_per_statement_parents_children_and_common_descendant(lane):
    review, capture = multiple(lane)
    assert (
        review[0]["parent_context"]["revision"]
        != review[1]["parent_context"]["revision"]
    )
    result = evaluate_lifecycle(review, capture)
    assert not capture["acquisition_errors"]
    assert result["counts"]["fail"] == 0, result


@pytest.mark.parametrize(
    "change",
    [
        "swap_receipt",
        "alias_native_id",
        "extra_native_mapping",
        "missing_statement",
        "extra_statement",
        "duplicate_edge",
        "wrong_typed_edge",
        "extra_event",
        "valid_data_loss",
        "read_mapping",
    ],
)
def test_multi_statement_corruption(lane, change):
    review, capture = multiple(lane)
    first, second = capture["records"]
    if change == "swap_receipt":
        first["confirm"]["result"]["receipt"] = second["confirm"]["result"]["receipt"]
    elif change == "alias_native_id":
        first["confirm"]["result"]["bindings"][0]["durable_id"] = second[
            "published_bundle"
        ]["statement_id"]
    elif change == "extra_native_mapping":
        first["confirm"]["result"]["bindings"].append(
            deepcopy(first["confirm"]["result"]["bindings"][0])
        )
    elif change == "missing_statement":
        capture["read_response"]["statements"].pop()
    elif change == "extra_statement":
        capture["read_response"]["statements"].append(
            deepcopy(capture["read_response"]["statements"][0])
        )
    elif change == "duplicate_edge":
        capture["edges"].append(deepcopy(capture["edges"][0]))
    elif change == "wrong_typed_edge":
        capture["edges"][0]["edge_id"] = next(
            b["durable_id"]
            for b in first["original_bindings"]
            if b["client_op_id"] == "qualified-payload"
        )
    elif change == "extra_event":
        first["graph_delta"]["added"]["assertions"][0]["predicate"] = (
            "dungeonbuddy.custom:fled"
        )
    elif change == "read_mapping":
        capture["read_response"]["statements"][0]["assertion_ids"] = [
            "invented-assertion"
        ]
    else:
        first["graph_delta"]["removed_or_changed"]["assertions"] = [
            "previous-valid-assertion"
        ]
    assert evaluate_lifecycle(review, capture)["counts"]["fail"] > 0
