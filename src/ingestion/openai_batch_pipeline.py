"""Submit and retrieve OpenAI Batch API jobs targeting POST /v1/responses."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, TypeVar

from openai import OpenAI
from openai.lib._parsing._responses import type_to_text_format_param
from pydantic import BaseModel

TextFormatT = TypeVar("TextFormatT", bound=BaseModel)


def build_responses_batch_request_body(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    text_format: type[TextFormatT],
) -> dict[str, Any]:
    fmt = type_to_text_format_param(text_format)
    return {
        "model": model,
        "input": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "text": {"format": fmt},
    }


def build_jsonl_request_line(
    *,
    custom_id: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    return {
        "custom_id": custom_id,
        "method": "POST",
        "url": "/v1/responses",
        "body": body,
    }


def write_jsonl(path: Path, lines: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in lines:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def append_jsonl(path: Path, lines: list[dict[str, Any]]) -> None:
    """Append JSONL rows to an existing file (or create it if missing)."""
    if not lines:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        for row in lines:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_jsonl_bytes(raw: bytes) -> list[dict[str, Any]]:
    text = raw.decode("utf-8")
    rows: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def extract_response_body_from_batch_line(row: dict[str, Any]) -> dict[str, Any] | None:
    err = row.get("error")
    if isinstance(err, dict) and err.get("message"):
        return None
    resp = row.get("response")
    if not isinstance(resp, dict):
        return None
    body = resp.get("body")
    if isinstance(body, dict):
        return body
    return None


def extract_status_code_from_batch_line(row: dict[str, Any]) -> int | None:
    resp = row.get("response")
    if not isinstance(resp, dict):
        return None
    code = resp.get("status_code")
    try:
        return int(code) if code is not None else None
    except (TypeError, ValueError):
        return None


def extract_output_text_from_responses_body(body: dict[str, Any]) -> str | None:
    for item in body.get("output") or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for part in item.get("content") or []:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "output_text":
                t = part.get("text")
                if isinstance(t, str) and t.strip():
                    return t
    return None


def usage_dict_from_responses_body(body: dict[str, Any]) -> dict[str, int]:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return {"input_tokens": 0, "output_tokens": 0, "cached_tokens": 0}
    details = usage.get("input_tokens_details")
    cached = 0
    if isinstance(details, dict):
        try:
            cached = int(details.get("cached_tokens", 0) or 0)
        except (TypeError, ValueError):
            cached = 0
    try:
        inp = int(usage.get("input_tokens", 0) or 0)
    except (TypeError, ValueError):
        inp = 0
    try:
        out = int(usage.get("output_tokens", 0) or 0)
    except (TypeError, ValueError):
        out = 0
    return {"input_tokens": inp, "output_tokens": out, "cached_tokens": cached}


def merge_usage(into: dict[str, int], part: dict[str, int]) -> None:
    for k in ("input_tokens", "output_tokens", "cached_tokens"):
        into[k] = into.get(k, 0) + part.get(k, 0)


def run_batch_job(
    client: OpenAI,
    *,
    lines: list[dict[str, Any]],
    work_dir: Path,
    file_prefix: str,
    poll_interval_sec: float = 30.0,
    print_status: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    """Upload JSONL, poll batch, return (output_rows, error_rows, status_meta)."""
    work_dir.mkdir(parents=True, exist_ok=True)
    req_path = work_dir / f"{file_prefix}_requests.jsonl"
    write_jsonl(req_path, lines)

    with req_path.open("rb") as fh:
        batch_file = client.files.create(file=fh, purpose="batch")

    batch = client.batches.create(
        input_file_id=batch_file.id,
        endpoint="/v1/responses",
        completion_window="24h",
    )
    meta: dict[str, Any] = {
        "batch_id": batch.id,
        "input_file_id": batch_file.id,
        "request_count": len(lines),
    }
    if print_status:
        print(f"  OpenAI Batch submitted: {batch.id} ({len(lines)} requests)", flush=True)

    b = batch
    terminal = {"completed", "failed", "expired", "cancelled"}
    while b.status not in terminal:
        time.sleep(poll_interval_sec)
        b = client.batches.retrieve(b.id)
        if print_status and b.request_counts is not None:
            rc = b.request_counts
            print(
                f"  Batch {b.id} status={b.status} completed={rc.completed} failed={rc.failed} total={rc.total}",
                flush=True,
            )

    meta["final_status"] = b.status
    if b.request_counts is not None:
        meta["request_counts"] = {
            "completed": b.request_counts.completed,
            "failed": b.request_counts.failed,
            "total": b.request_counts.total,
        }

    output_rows: list[dict[str, Any]] = []
    error_rows: list[dict[str, Any]] = []

    if b.status != "completed":
        meta["error"] = f"batch_status={b.status}"
        return output_rows, error_rows, meta

    if b.output_file_id:
        content = client.files.content(b.output_file_id)
        raw = content.read()
        (work_dir / f"{file_prefix}_output.jsonl").write_bytes(raw)
        output_rows = read_jsonl_bytes(raw)

    if b.error_file_id:
        err_content = client.files.content(b.error_file_id)
        err_raw = err_content.read()
        (work_dir / f"{file_prefix}_errors.jsonl").write_bytes(err_raw)
        error_rows = read_jsonl_bytes(err_raw)

    return output_rows, error_rows, meta
