"""Repair entity records that fail JSON Schema validation via OpenAI Batch API.

Band-aid path: cheaper primary model (e.g. nano) can emit enum typos; submit invalid
rows to a stronger model in /v1/responses batch mode with full validator context.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError as PydanticValidationError

from src.contracts.schema_validation import (
    list_validation_failures,
    validate_instance,
)
from src.ingestion.openai_batch_pipeline import (
    build_jsonl_request_line,
    build_responses_batch_request_body,
    extract_output_text_from_responses_body,
    extract_response_body_from_batch_line,
    merge_usage,
    run_batch_job,
    usage_dict_from_responses_body,
)

logger = logging.getLogger(__name__)

_REPAIR_CUSTOM_ID_RE = re.compile(r"^entity_schema_repair_(\d+)$")

ENTITY_SCHEMA_REPAIR_SYSTEM_PROMPT = """You repair a single DungeonMindBuddy entity JSON record so it validates against entity.schema.json v0.1.

Rules:
- Output must be one complete entity object (same keys as the input where applicable), valid JSON.
- Make the smallest change that fixes validation: prefer fixing enums, nullability, and required fields over rewriting content.
- Preserve entity_id, display_name, aliases, span_text, and semantic intent unless a field is invalid and must be corrected.
- Never invent new entities; only fix the provided record.
- authority must be exactly one of: canon_reference, planning_note, play_record, rumor_or_belief, mechanic_reference, or null (not typos like rumor_or_b_belief).
- entity_class / entity_kind must be one of: actor, group, place, object, event, concept.
- entity_type must be one of: npc, location, faction, item, other.

Return structured output: repaired_record_json must be a JSON string containing the full repaired object (not an array, not wrapped in markdown)."""


class EntitySchemaRepairOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repaired_record_json: str = Field(
        ...,
        description="Stringified JSON object for one entity record matching entity.schema.json v0.1.",
    )


def _entity_schema_hint_block() -> str:
    from src.contracts.schema_validation import load_schema

    schema = load_schema("entity.schema.json")
    props = schema.get("properties") or {}
    lines: list[str] = ["## Selected entity.schema.json constraints (hints)\n"]

    def pick_enum(key: str) -> None:
        block = props.get(key) or {}
        enum_vals = block.get("enum")
        if isinstance(enum_vals, list):
            lines.append(f"- **{key}**: one of {json.dumps(enum_vals, ensure_ascii=False)}")

    pick_enum("entity_class")
    pick_enum("entity_type")
    pick_enum("entity_kind")
    pick_enum("authority")
    pick_enum("record_status")
    pick_enum("entity_status")
    pick_enum("decision")
    pick_enum("exclude_reason")
    pick_enum("source_profile")
    return "\n".join(lines) + "\n"


def build_entity_repair_user_prompt(
    *,
    record: dict[str, Any],
    validation_error: str,
) -> str:
    hint = _entity_schema_hint_block()
    payload = json.dumps(record, indent=2, ensure_ascii=False)
    return (
        f"{hint}\n"
        "## Record that failed validation (JSON)\n"
        f"```json\n{payload}\n```\n\n"
        "## jsonschema error (verbatim context)\n"
        f"{validation_error}\n"
    )


def repair_entity_records_via_openai_batch(
    records: list[dict[str, Any]],
    *,
    client: OpenAI,
    repair_model: str,
    work_dir: Path,
    poll_interval_sec: float = 30.0,
    print_status: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Run Batch /v1/responses jobs to fix invalid entity rows. Returns new list + meta (usage, counts)."""
    failures = list_validation_failures(records, "entity.schema.json")
    meta: dict[str, Any] = {
        "skipped": False,
        "invalid_count": len(failures),
        "repaired_count": 0,
        "usage": {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0},
    }
    if not failures:
        meta["skipped"] = True
        return list(records), meta

    work_dir.mkdir(parents=True, exist_ok=True)
    lines: list[dict[str, Any]] = []
    for idx, rec, err in failures:
        body = build_responses_batch_request_body(
            model=repair_model,
            system_prompt=ENTITY_SCHEMA_REPAIR_SYSTEM_PROMPT,
            user_prompt=build_entity_repair_user_prompt(record=rec, validation_error=err),
            text_format=EntitySchemaRepairOutput,
        )
        lines.append(
            build_jsonl_request_line(
                custom_id=f"entity_schema_repair_{idx}",
                body=body,
            )
        )

    if print_status:
        print(
            f"  Schema repair batch: submitting {len(lines)} invalid entity record(s) "
            f"with model={repair_model!r}",
            flush=True,
        )

    out_rows, err_rows, batch_meta = run_batch_job(
        client,
        lines=lines,
        work_dir=work_dir,
        file_prefix="entity_schema_repair",
        poll_interval_sec=poll_interval_sec,
        print_status=print_status,
    )
    meta["batch"] = batch_meta

    if err_rows and print_status:
        print(f"  Warning: schema repair batch error file has {len(err_rows)} row(s).", flush=True)

    out_map: dict[int, str] = {}
    for row in out_rows:
        cid = row.get("custom_id")
        if not isinstance(cid, str):
            continue
        m = _REPAIR_CUSTOM_ID_RE.match(cid)
        if not m:
            continue
        body = extract_response_body_from_batch_line(row)
        if not body:
            continue
        text = extract_output_text_from_responses_body(body)
        if text:
            out_map[int(m.group(1))] = text
        merge_usage(meta["usage"], usage_dict_from_responses_body(body))

    updated = list(records)
    repair_errors: list[str] = []

    for idx, _old, _err in failures:
        raw = out_map.get(idx)
        if raw is None:
            repair_errors.append(f"index {idx}: missing batch output")
            continue
        try:
            parsed_out = EntitySchemaRepairOutput.model_validate_json(raw)
            repaired = json.loads(parsed_out.repaired_record_json)
        except (json.JSONDecodeError, PydanticValidationError, ValueError) as e:
            repair_errors.append(f"index {idx}: parse repair output: {e}")
            continue
        if not isinstance(repaired, dict):
            repair_errors.append(f"index {idx}: repaired payload is not an object")
            continue
        try:
            validate_instance(repaired, "entity.schema.json")
        except Exception as e:
            repair_errors.append(f"index {idx}: repaired record still invalid: {e}")
            continue
        updated[idx] = repaired
        meta["repaired_count"] += 1

    if repair_errors:
        msg = "; ".join(repair_errors[:12])
        if len(repair_errors) > 12:
            msg += f" ... (+{len(repair_errors) - 12} more)"
        raise RuntimeError(f"entity schema repair batch failed: {msg}")

    validate_many_after = list_validation_failures(updated, "entity.schema.json")
    if validate_many_after:
        raise RuntimeError(
            "entity schema repair left invalid records: "
            + ", ".join(str(i) for i, _, _ in validate_many_after[:20])
        )

    logger.info(
        "schema_repair_batch done invalid=%d repaired=%d usage=%s",
        len(failures),
        meta["repaired_count"],
        meta["usage"],
    )
    return updated, meta
