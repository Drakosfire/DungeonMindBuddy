import hashlib
import json
from uuid import uuid4
import pytest
from application_state.ingest import service as ingest
from application_state.ingest.components import persist_component_payload
from apps.live_control_server.services.extraction_usage import summarize
from graph_memory.ingestion.extraction_run import (
    ExtractionRun,
    ExtractionRunComponentRef,
)
from tests.test_saved_recap_runs import BASE, TOKEN, lane, seed  # noqa: F401


def call(name="actor_pass", **overrides):
    observation = {
        "input_tokens": 100,
        "output_tokens": 20,
        "cached_input_tokens": 40,
        "reasoning_tokens": 15,
        "provider_attempt_count": 1,
        "cost_usd": 0.01,
        "known_cost_usd": 0.01,
        "cost_status": "reported",
        "pricing_source": "provider_reported:test",
    }
    observation.update(overrides)
    return {"pass_name": name, "observation": observation}


def test_accounting_does_not_add_subsets_or_count_attempt_callbacks_twice():
    totals, rows = summarize(
        {"calls": [call(), call("edge_pass")], "attempts": [{"cost_usd": 99}]}
    )
    assert (
        totals.input_tokens == 200
        and totals.output_tokens == 40
        and totals.total_tokens == 240
    )
    assert totals.cached_input_tokens == 80 and totals.reasoning_tokens == 30
    assert (
        totals.cost_usd == 0.02
        and totals.known_cost_usd == 0.02
        and totals.cost_status == "reported"
    )
    assert len(rows) == 2 and totals.provider_attempts == 2


def test_partial_unknown_zero_and_legacy_are_truthful():
    totals, _ = summarize(
        {
            "calls": [
                call(cost_usd=0, known_cost_usd=0),
                call(
                    "edge_pass",
                    cost_usd=None,
                    known_cost_usd=None,
                    cost_status="unavailable",
                    input_tokens=None,
                ),
            ]
        }
    )
    assert (
        totals.cost_usd is None
        and totals.known_cost_usd == 0
        and totals.cost_status == "partial"
    )
    assert totals.input_tokens is None and totals.known_input_tokens == 100
    zero, _ = summarize({"calls": [call(cost_usd=0, known_cost_usd=0)]})
    assert zero.cost_usd == 0 and zero.cost_status == "reported"
    legacy = call()
    legacy["observation"].pop("cost_status")
    legacy["observation"].pop("known_cost_usd")
    old, _ = summarize({"calls": [legacy]})
    assert old.cost_usd is None and old.cost_status == "unavailable"
    missing, _ = summarize(
        {"calls": [{"pass_name": "actor_pass", "observation": None}]}
    )
    assert (
        missing.cost_usd is None
        and missing.input_tokens is None
        and missing.provider_attempts is None
    )


def test_partial_operation_subtotal_is_not_treated_as_full_price():
    result, _ = summarize(
        {
            "calls": [
                call(
                    cost_usd=None,
                    known_cost_usd=0.1,
                    cost_status="partial",
                    provider_attempt_count=2,
                )
            ]
        }
    )
    assert (
        result.cost_status == "partial"
        and result.known_cost_usd == 0.1
        and result.cost_usd is None
    )
    result, _ = summarize(
        {
            "calls": [
                call(
                    provider_attempt_count=0,
                    cost_usd=None,
                    known_cost_usd=None,
                    cost_status="unavailable",
                )
            ]
        }
    )
    assert result.cost_status == "not_dispatched" and result.cost_usd is None


def seed_usage(world, *, ledger=None):
    base, source = seed(world)
    rid = "usage-" + uuid4().hex
    payload = {
        "run_id": rid,
        "source_sha256": source.content_sha256,
        "calls": [call()],
        "private_request": "PRIVATE_SENTINEL",
    }
    if ledger is not None:
        payload.update(ledger)
    raw = json.dumps(payload).encode()
    digest = hashlib.sha256(raw).hexdigest()
    data = base.model_dump(mode="json")
    data.update(run_id=rid, lineage={"source_sha256": source.content_sha256})
    data["components"]["pass_telemetry"] = ExtractionRunComponentRef(
        kind="pass_telemetry",
        uri="repo://poison/ledger.json",
        sha256=digest,
        exists=True,
    ).model_dump(mode="json")
    run = ingest.create_extraction_run(ExtractionRun.model_validate(data))
    persist_component_payload(
        run_id=rid, expected_revision=run.revision, kind="pass_telemetry", payload=raw
    )
    return run


def read(client, world, run, **extra):
    return client.get(
        f"{BASE}/{run.run_id}/usage",
        params={
            "managed_world_id": world.world_id,
            "expected_run_revision": run.revision,
            **extra,
        },
    )


def test_mounted_usage_reads_exact_database_receipt_without_source_body(
    lane, monkeypatch
):
    from application_state.source import service as sources

    client, world, _, _ = lane
    run = seed_usage(world)
    monkeypatch.setattr(
        sources,
        "get_source_markdown",
        lambda **_: pytest.fail("usage read source body"),
    )
    r = read(client, world, run)
    assert r.status_code == 200, r.text
    assert (
        r.json()["totals"]["costUsd"] == 0.01
        and r.json()["totals"]["totalTokens"] == 120
    )
    assert r.json()["runId"] == run.run_id and "PRIVATE_SENTINEL" not in r.text
    assert "no-store" in r.headers["cache-control"]
    assert ingest.get_extraction_run(run.run_id).revision == run.revision


def test_auth_world_revision_and_selector_checks_before_receipt_access(lane):
    client, world, other, _ = lane
    run = seed_usage(world)
    client.headers.pop("Authorization")
    assert read(client, world, run).status_code == 401
    client.headers["Authorization"] = f"Bearer {TOKEN}"
    assert read(client, other, run).status_code == 404
    assert (
        read(client, world, run, expected_run_revision=run.revision + 1).status_code
        == 409
    )
    assert (
        client.get(
            f"{BASE}/{run.run_id}/usage",
            params=[
                ("managed_world_id", world.world_id),
                ("managed_world_id", other.world_id),
                ("expected_run_revision", run.revision),
            ],
        ).status_code
        == 422
    )


def test_missing_receipt_is_unavailable_and_wrong_receipt_binding_is_rejected(lane):
    client, world, _, _ = lane
    run, _ = seed(world)
    response = read(client, world, run)
    assert response.status_code == 200, response.text
    assert response.json()["totals"]["costStatus"] == "unavailable"
    bad = seed_usage(world, ledger={"run_id": "foreign-run"})
    assert read(client, world, bad).status_code == 409


def test_private_attempt_and_operation_receipts_retain_price_without_exposing_text():
    from src.graph_memory.extraction.bounded_recap_execution import (
        _private_response_envelope,
    )

    record = _private_response_envelope(
        binding={"run_id": "r", "prepared_revision": 2},
        ordinal=1,
        pass_name="actor_pass",
        request={},
        context_hashes={},
        raw_observation={
            "cost_usd": None,
            "known_cost_usd": 0.01,
            "cost_status": "partial",
            "pricing_source": "provider_reported:test",
            "input_tokens": 10,
        },
        response_text="private response",
        attempt_event={
            "ordinal": 1,
            "event_id": "event:1",
            "cost_usd": 0.01,
            "pricing_source": "provider_reported:test",
        },
    )
    assert record["ge_observation"]["known_cost_usd"] == 0.01
    assert record["ge_observation"]["cost_status"] == "partial"
    assert record["ge_attempt"]["cost_usd"] == 0.01
    totals, _ = summarize(
        {
            "calls": [
                {"pass_name": "actor_pass", "observation": record["ge_observation"]}
            ]
        }
    )
    assert (
        totals.cost_usd is None
        and totals.known_cost_usd == 0.01
        and totals.cost_status == "partial"
    )
