from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.live_play.recap_ingest_pipeline import PipelineOptions, inspect_recap_ingest_status, run_pipeline

router = APIRouter(prefix="/api/live", tags=["live"])

RecapIngestOperation = Literal[
    "stage_preview",
    "apply_normalize",
    "materialize_session_memory",
    "inspect_status",
]

_CORPUS_ROOT_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"
_GENERIC_TITLE_TAILS = {"", "recap"}


class RecapIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: RecapIngestOperation
    campaign_id: str = Field(min_length=1)
    session: Annotated[int, Field(ge=1)]
    raw_text: str | None = None
    slug: str | None = None
    title: str | None = None
    force_stage: bool = False
    force_recap: bool = False
    check: bool = False


class RecapIngestStatusResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_: Literal["dmb_raw_recap_ingest_status_v1"] = Field(alias="schema")
    campaign_id: str
    session: int
    status: str
    states: list[str]
    paths: dict[str, str | None]
    authority: dict[str, str]
    warnings: list[str]
    errors: list[str]
    next_actions: list[str]
    ingest_report: dict[str, Any]
    entity_spelling_audit: list[dict[str, Any]]


def _tail_from_title(title: str | None) -> str:
    if not title:
        return ""
    raw = title.strip()
    if raw.lower().startswith("session ") and "-" in raw:
        _prefix, _dash, tail = raw.partition("-")
        return tail.strip().rstrip(":").lower()
    return raw.rstrip(":").lower()


def _is_non_generic_slug_or_title(*, slug: str | None, title: str | None) -> bool:
    if slug and slug.strip().rstrip(":").lower() not in _GENERIC_TITLE_TAILS:
        return True
    tail = _tail_from_title(title)
    return tail not in _GENERIC_TITLE_TAILS


def _pipeline_corpus_root() -> Path | None:
    raw = os.environ.get(_CORPUS_ROOT_ENV, "").strip()
    if not raw:
        return None
    root = Path(raw).expanduser().resolve()
    if not root.is_dir():
        raise HTTPException(status_code=500, detail=f"invalid {_CORPUS_ROOT_ENV}: {root}")
    return root


def _options_for_request(body: RecapIngestRequest) -> PipelineOptions:
    operation = body.operation
    if operation == "stage_preview":
        raw = (body.raw_text or "").strip()
        if not raw:
            raise HTTPException(status_code=422, detail="stage_preview requires non-empty raw_text")
        return PipelineOptions(
            campaign_id=body.campaign_id,
            session=body.session,
            raw_path=None,
            raw_stdin=True,
            title=body.title,
            slug=body.slug,
            stage=True,
            preview=True,
            apply=False,
            normalize=False,
            materialize_session_memory=False,
            check=False,
            force_stage=body.force_stage,
            force_recap=False,
            json_output=True,
        )

    if operation == "apply_normalize":
        if not _is_non_generic_slug_or_title(slug=body.slug, title=body.title):
            raise HTTPException(
                status_code=422,
                detail="apply_normalize requires non-generic slug or title",
            )
        return PipelineOptions(
            campaign_id=body.campaign_id,
            session=body.session,
            raw_path=None,
            raw_stdin=False,
            title=body.title,
            slug=body.slug,
            stage=False,
            preview=True,
            apply=True,
            normalize=True,
            materialize_session_memory=False,
            check=False,
            force_stage=False,
            force_recap=body.force_recap,
            json_output=True,
        )

    if operation == "materialize_session_memory":
        if not _is_non_generic_slug_or_title(slug=body.slug, title=body.title):
            raise HTTPException(
                status_code=422,
                detail="materialize_session_memory requires non-generic slug or title",
            )
        return PipelineOptions(
            campaign_id=body.campaign_id,
            session=body.session,
            raw_path=None,
            raw_stdin=False,
            title=body.title,
            slug=body.slug,
            stage=False,
            preview=False,
            apply=False,
            normalize=False,
            materialize_session_memory=True,
            check=body.check,
            force_stage=False,
            force_recap=False,
            json_output=True,
        )

    raise HTTPException(status_code=422, detail=f"unsupported operation: {operation}")


@router.post("/recap-ingest", response_model=RecapIngestStatusResponse)
def post_recap_ingest(body: RecapIngestRequest) -> dict[str, Any]:
    try:
        corpus = _pipeline_corpus_root()
        if body.operation == "inspect_status":
            return inspect_recap_ingest_status(
                campaign_id=body.campaign_id,
                session=body.session,
                title=body.title,
                slug=body.slug,
                corpus=corpus,
            )
        options = _options_for_request(body)
        if body.operation == "stage_preview":
            status = run_pipeline(
                options,
                stdin=io.StringIO(body.raw_text or ""),
                corpus=corpus,
            )
        else:
            status = run_pipeline(options, corpus=corpus)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return status
