from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError


class LiveRowValidationError(ValueError):
    """Raised when an event or job row fails live_* schema validation before append."""


@lru_cache(maxsize=2)
def _validator(schema_name: str) -> Draft202012Validator:
    schema_dir = Path(__file__).resolve().parents[2] / "evals/c2_live_prep/live/schemas"
    schema = json.loads((schema_dir / schema_name).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(
        schema,
        format_checker=Draft202012Validator.FORMAT_CHECKER,
    )


def validate_live_event_row(row: dict[str, Any]) -> None:
    try:
        _validator("live_event.schema.json").validate(row)
    except ValidationError as exc:
        raise LiveRowValidationError(f"invalid live event row: {exc.message}") from exc


def validate_live_job_row(row: dict[str, Any]) -> None:
    try:
        _validator("live_job.schema.json").validate(row)
    except ValidationError as exc:
        raise LiveRowValidationError(f"invalid live job row: {exc.message}") from exc


def validate_before_append(
    events: list[dict[str, Any]],
    jobs: list[dict[str, Any]],
) -> None:
    for index, event in enumerate(events):
        try:
            validate_live_event_row(event)
        except LiveRowValidationError as exc:
            raise LiveRowValidationError(f"events_to_write[{index}]: {exc}") from exc
    for index, job in enumerate(jobs):
        try:
            validate_live_job_row(job)
        except LiveRowValidationError as exc:
            raise LiveRowValidationError(f"jobs_to_queue[{index}]: {exc}") from exc
