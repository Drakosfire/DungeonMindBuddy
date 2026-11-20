"""Exact-run accounting from retained operation observations, never duplicate callbacks."""

from __future__ import annotations
import json
import math
from collections.abc import Mapping
from pathlib import Path
from apps.live_control_server.models.extraction_usage import (
    ExtractionUsageResponse,
    PassUsage,
    UsageMetrics,
)
from apps.live_control_server.services.ingest_run_catalog import (
    IngestRunCatalogError,
    CODE_INTEGRITY,
    _stable_scope,
    _require_scope_unchanged,
)


def number(value):
    return (
        float(value)
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
        else None
    )


def tokens(value):
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0
        else None
    )


def aggregate(rows: list[UsageMetrics]) -> UsageMetrics:
    values = {}
    for field in [
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "reasoning_tokens",
        "provider_attempts",
    ]:
        parts = [getattr(row, field) for row in rows]
        values[field] = (
            sum(parts) if parts and all(x is not None for x in parts) else None
        )
    for field in ["input_tokens", "output_tokens"]:
        parts = [
            getattr(row, "known_" + field)
            for row in rows
            if getattr(row, "known_" + field) is not None
        ]
        values["known_" + field] = sum(parts) if parts else None
    if values["input_tokens"] is not None and values["output_tokens"] is not None:
        values["total_tokens"] = values["input_tokens"] + values["output_tokens"]
    charged = [row for row in rows if row.cost_status != "not_dispatched"]
    known = [row.known_cost_usd for row in charged if row.known_cost_usd is not None]
    complete = bool(charged) and all(
        row.cost_status == "reported" and row.cost_usd is not None for row in charged
    )
    values.update(
        cost_usd=sum(row.cost_usd for row in charged) if complete else None,
        known_cost_usd=sum(known) if known else None,
        cost_status="reported"
        if complete
        else "partial"
        if known
        else "not_dispatched"
        if rows and not charged
        else "unavailable",
    )
    sources = {
        row.pricing_source
        for row in charged
        if row.known_cost_usd is not None and row.pricing_source
    }
    values["pricing_source"] = (
        next(iter(sources))
        if len(sources) == 1
        else "multiple reported sources"
        if sources
        else None
    )
    return UsageMetrics(**values)


def summarize(ledger: dict) -> tuple[UsageMetrics, list[PassUsage]]:
    calls = ledger.get("calls")
    if not isinstance(calls, list):
        return UsageMetrics(), []
    rows = []
    for call in calls:
        if not isinstance(call, Mapping) or not isinstance(call.get("pass_name"), str):
            raise IngestRunCatalogError(
                "Retained usage receipt is invalid.",
                code=CODE_INTEGRITY,
                status_code=409,
            )
        obs = call.get("observation") or {}
        if not isinstance(obs, Mapping):
            raise IngestRunCatalogError(
                "Retained usage observation is invalid.",
                code=CODE_INTEGRITY,
                status_code=409,
            )
        data = {
            field: tokens(obs.get(field))
            for field in [
                "input_tokens",
                "output_tokens",
                "cached_input_tokens",
                "reasoning_tokens",
            ]
        }
        attempts = tokens(obs.get("provider_attempt_count"))
        reported = (
            number(obs.get("cost_usd"))
            if obs.get("cost_status") == "reported"
            else None
        )
        known = number(obs.get("known_cost_usd"))
        if reported is not None:
            known = reported
        # Old receipts have no cost-completeness contract. Keep them unknown.
        status = (
            "not_dispatched"
            if attempts == 0
            else "reported"
            if reported is not None
            else "partial"
            if known is not None
            else "unavailable"
        )
        data.update(
            known_input_tokens=data["input_tokens"],
            known_output_tokens=data["output_tokens"],
            provider_attempts=attempts,
            cost_usd=reported,
            known_cost_usd=known,
            cost_status=status,
            pricing_source=obs.get("pricing_source")
            if isinstance(obs.get("pricing_source"), str)
            else None,
        )
        if data["input_tokens"] is not None and data["output_tokens"] is not None:
            data["total_tokens"] = data["input_tokens"] + data["output_tokens"]
        rows.append(PassUsage(pass_name=call["pass_name"], **data))
    return aggregate(rows), rows


def read_extraction_usage(
    *, root: Path, managed_world_id: str, run_id: str, expected_run_revision: int
):
    from application_state.ingest import service as ingest
    from application_state.ingest.components import get_component_bytes

    scope = _stable_scope(root, managed_world_id)
    run = ingest.get_extraction_run(run_id, world_id=scope.native_world_id)
    if run.source_domain != "recap" or run.revision != expected_run_revision:
        raise IngestRunCatalogError(
            "Selected extraction run changed or is not a Recap run.",
            code=CODE_INTEGRITY,
            status_code=409,
        )
    ref = run.components.get("pass_telemetry")
    ledger = {}
    if ref is not None and ref.exists:
        try:
            ledger = json.loads(
                get_component_bytes(
                    run_id=run_id, kind="pass_telemetry", content_sha256=ref.sha256
                )
            )
        except (ValueError, UnicodeDecodeError) as exc:
            raise IngestRunCatalogError(
                "Retained usage receipt could not be decoded.",
                code=CODE_INTEGRITY,
                status_code=409,
            ) from exc
        if not isinstance(ledger, dict):
            raise IngestRunCatalogError(
                "Retained usage receipt is invalid.",
                code=CODE_INTEGRITY,
                status_code=409,
            )
        binding = ledger.get("binding")
        if binding is not None and (
            not isinstance(binding, Mapping)
            or binding.get("run_id") != run_id
            or binding.get("source_sha256") != run.lineage.get("source_sha256")
        ):
            raise IngestRunCatalogError(
                "Retained usage execution binding is invalid.",
                code=CODE_INTEGRITY,
                status_code=409,
            )
        if ledger.get("run_id") not in (None, run_id) or ledger.get(
            "source_sha256"
        ) not in (None, run.lineage.get("source_sha256")):
            raise IngestRunCatalogError(
                "Retained usage receipt belongs to another run.",
                code=CODE_INTEGRITY,
                status_code=409,
            )
    totals, passes = summarize(ledger)
    _require_scope_unchanged(root, scope)
    if (
        ingest.get_extraction_run(run_id, world_id=scope.native_world_id).revision
        != expected_run_revision
    ):
        raise IngestRunCatalogError(
            "Selected extraction run changed while reading usage.",
            code=CODE_INTEGRITY,
            status_code=409,
        )
    return ExtractionUsageResponse(
        managed_world_id=managed_world_id,
        run_id=run_id,
        run_revision=run.revision,
        totals=totals,
        passes=passes,
    )
