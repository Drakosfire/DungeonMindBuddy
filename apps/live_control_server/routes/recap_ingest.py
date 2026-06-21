from __future__ import annotations

import io
import os
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.agent.recap_frontmatter_seed import (
    build_frontmatter_seed,
    default_frontmatter_seed_path,
)
from src.corpus.session_recap_paths import (
    breadcrumbed_relpath,
    campaign_number_from_id,
    frontmatter_seed_relpath,
    normalized_recap_relpath,
)
from src.live_play.recap_ingest_pipeline import PipelineOptions, inspect_recap_ingest_status, run_pipeline
from src.live_play.recap_stage_paths import corpus_root as default_corpus_root

router = APIRouter(prefix="/api/live", tags=["live"])

RecapIngestOperation = Literal[
    "stage_preview",
    "apply_normalize",
    "build_frontmatter_seed",
    "run_breadcrumb_ingest",
    "materialize_session_memory",
    "inspect_status",
]

_CORPUS_ROOT_ENV = "DUNGEONMIND_RECAP_INGEST_CORPUS_ROOT"
_GENERIC_TITLE_TAILS = {
    "",
    "ingest",
    "ingestion",
    "raw recap",
    "raw recap ingest",
    "raw recap ingestion",
    "recap",
    "recap ingest",
    "recap ingestion",
    "session recap",
}


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
    if slug and slug.strip().rstrip(":").lower():
        return slug.strip().rstrip(":").lower() not in _GENERIC_TITLE_TAILS
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


def _run_routing_only_breadcrumb(
    *,
    recap_md: Path,
    frontmatter_seed_md: Path,
    corpus_root: Path,
    out_path: Path,
) -> dict[str, Any]:
    from evals.sentence_routing_retrieval_falsification.breadcrumb_prompt import (
        PROMPT_VARIANT_CONTINUATION,
    )
    from evals.sentence_routing_retrieval_falsification.breadcrumb_query_run import (
        _generate_breadcrumb_artifact_routing_only,
        _resolve_breadcrumb_ingest_model,
    )

    return _generate_breadcrumb_artifact_routing_only(
        recap_md=recap_md,
        frontmatter_seed_md=frontmatter_seed_md,
        corpus_root=corpus_root,
        variant=PROMPT_VARIANT_CONTINUATION,
        model=_resolve_breadcrumb_ingest_model(None),
        out_path=out_path,
        min_routed_records=1,
    )


def _add_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


def _build_frontmatter_seed_from_request(body: RecapIngestRequest, corpus: Path) -> dict[str, Any]:
    campaign_number = campaign_number_from_id(body.campaign_id)
    out_path = default_frontmatter_seed_path(
        corpus_root=corpus,
        campaign_number=campaign_number,
        session=body.session,
    ).resolve()
    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    if out_path.is_file():
        _add_unique(status["states"], "frontmatter_seed_reused")
        _add_unique(status["warnings"], "frontmatter_seed_already_exists")
        status["ingest_report"]["frontmatter_seed_path"] = str(out_path)
        return status

    seed = build_frontmatter_seed(
        corpus_root=corpus,
        campaign_number=campaign_number,
        session=body.session,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(seed if seed.endswith("\n") else seed + "\n", encoding="utf-8")
    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    _add_unique(status["states"], "frontmatter_seed_built")
    status["ingest_report"]["frontmatter_seed_path"] = str(out_path)
    return status


def _run_breadcrumb_ingest_from_request(body: RecapIngestRequest, corpus: Path) -> dict[str, Any]:
    campaign_number = campaign_number_from_id(body.campaign_id)
    normalized_path = (
        corpus
        / normalized_recap_relpath(
            campaign_number=campaign_number,
            session=body.session,
            corpus_root=corpus,
        )
    ).resolve()
    seed_path = (
        corpus
        / frontmatter_seed_relpath(
            campaign_number=campaign_number,
            session=body.session,
            corpus_root=corpus,
        )
    ).resolve()
    breadcrumb_path = (
        corpus
        / breadcrumbed_relpath(
            campaign_number=campaign_number,
            session=body.session,
            corpus_root=corpus,
        )
    ).resolve()

    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    if not seed_path.is_file():
        raise HTTPException(status_code=422, detail=f"frontmatter seed missing: {seed_path}")
    if breadcrumb_path.is_file():
        _add_unique(status["states"], "breadcrumb_ingest_reused")
        _add_unique(status["warnings"], "breadcrumbed_recap_already_exists")
        status["ingest_report"]["breadcrumbed_recap_path"] = str(breadcrumb_path)
        return status

    try:
        report = _run_routing_only_breadcrumb(
            recap_md=normalized_path,
            frontmatter_seed_md=seed_path,
            corpus_root=corpus,
            out_path=breadcrumb_path,
        )
    except SystemExit as exc:
        detail = str(exc) or "breadcrumb ingest failed"
        raise HTTPException(status_code=422, detail=detail) from exc

    status = inspect_recap_ingest_status(
        campaign_id=body.campaign_id,
        session=body.session,
        title=body.title,
        slug=body.slug,
        corpus=corpus,
    )
    _add_unique(status["states"], "breadcrumb_ingest_ran")
    status["ingest_report"]["breadcrumb_ingest"] = report
    return status


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
        if body.operation == "build_frontmatter_seed":
            return _build_frontmatter_seed_from_request(
                body,
                corpus=(corpus or default_corpus_root()).resolve(),
            )
        if body.operation == "run_breadcrumb_ingest":
            return _run_breadcrumb_ingest_from_request(
                body,
                corpus=(corpus or default_corpus_root()).resolve(),
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
