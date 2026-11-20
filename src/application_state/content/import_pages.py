"""Explicit offline adoption into Content, never an ordinary page read path."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

import psycopg
from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

from application_state.content import pages, repository as repo
from application_state.content.types import (
    AuthoredPageObject, WorkingCopy, WorkRevision, normalize_markdown, sha256_utf8,
)
from application_state.errors import (
    ApplicationStateConflictError, ApplicationStateValidationError,
)
from application_state.unit_of_work import unit_of_work


class FrozenPage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    page: AuthoredPageObject
    metadata: pages.PageMetadata
    content_status: Literal["draft", "committed"]
    markdown: str | None
    content_sha256: str | None

    @model_validator(mode="after")
    def validate_seed(self) -> FrozenPage:
        page = self.page
        if (page.current_revision_id is not None or page.target_relpath is not None
                or page.object_revision < 1 or not page.title.strip()
                or page.created_at.tzinfo is None or page.updated_at.tzinfo is None):
            raise ValueError("adoption requires exact metadata without a DB revision or file locator")
        if self.markdown is None:
            if self.content_status != "draft" or self.content_sha256 is not None:
                raise ValueError("only an absent draft may omit its body/digest")
        elif (self.markdown != normalize_markdown(self.markdown)
                or self.content_sha256 != sha256_utf8(self.markdown)):
            raise ValueError("adoption body must match its normalized SHA-256")
        return self


@dataclass(frozen=True)
class PageAdoption:
    status: str
    page_count: int


def _matches(conn, seed: FrozenPage) -> bool:
    state = pages._state(conn, str(seed.page.work_object_id), seed.page.world_id)
    if (state.page.model_copy(update={"current_revision_id": None}) != seed.page
            or state.metadata != seed.metadata):
        return False
    revisions = conn.execute(
        "SELECT work_revision_id FROM content.work_revision WHERE work_object_id=%s",
        (seed.page.work_object_id,),
    ).fetchall()
    copy = repo.get_working_copy(conn, seed.page.work_object_id)
    if seed.content_status == "committed":
        revision = repo.get_work_revision(conn, state.page.current_revision_id) if state.page.current_revision_id else None
        return (len(revisions) == 1 and revision is not None
                and revision.revision_n == 1 and revision.work_object_id == seed.page.work_object_id
                and revision.world_id == seed.page.world_id
                and revision.markdown == seed.markdown and revision.content_sha256 == seed.content_sha256
                and copy is None)
    if revisions or state.page.current_revision_id is not None:
        return False
    if seed.markdown is None:
        return copy is None
    return copy == WorkingCopy(
        work_object_id=seed.page.work_object_id, markdown=seed.markdown,
        content_sha256=seed.content_sha256, base_revision_id=None,
        working_copy_revision=1, updated_at=seed.page.updated_at,
    )


def adopt_pages(seeds: list[FrozenPage], *, dry_run: bool = True) -> PageAdoption:
    """Adopt a complete frozen inventory into an empty owner, or exact replay.

    All input is frozen before this transaction. This never reads migration
    files, repairs a partial import, reconstructs old history or grants native
    source/campaign/publication authority. Live writers must be stopped at delivery.
    """
    try:
        seeds = [FrozenPage.model_validate(seed.model_dump()) for seed in seeds]
    except (ValidationError, AttributeError) as exc:
        raise ApplicationStateValidationError("invalid frozen page input") from exc
    ids = [seed.page.work_object_id for seed in seeds]
    operations = [seed.metadata.connected_page_operation_id for seed in seeds
                  if seed.metadata.connected_page_operation_id is not None]
    if len(set(ids)) != len(ids) or len(set(operations)) != len(operations):
        raise ApplicationStateValidationError("duplicate page identity or connected reservation")
    try:
        with unit_of_work(pages._dsn()) as conn:
            # Acquire table intent before row locks, serialize competing adopters
            # and all Content writers; no second import ledger/lock authority.
            conn.execute("LOCK TABLE content.work_object IN SHARE ROW EXCLUSIVE MODE")
            owners = {row[0] for row in conn.execute(
                "SELECT world_id FROM workspace.managed_world FOR KEY SHARE"
            ).fetchall()}
            if any(seed.page.world_id not in owners for seed in seeds):
                raise ApplicationStateValidationError("every page requires its existing exact World owner")
            existing = {row[0] for row in conn.execute(
                "SELECT work_object_id FROM content.work_object WHERE kind='worldbuilding_source'"
            ).fetchall()}
            if existing:
                if existing != set(ids) or not all(_matches(conn, seed) for seed in seeds):
                    raise ApplicationStateConflictError("page inventory differs; adoption never merges or repairs")
                return PageAdoption("already_adopted", len(seeds))
            if ids and conn.execute(
                "SELECT 1 FROM content.work_object WHERE work_object_id=ANY(%s)", (ids,)
            ).fetchone():
                raise ApplicationStateConflictError("page identity is already owned by other Content")
            if dry_run:
                return PageAdoption("would_adopt", len(seeds))
            for seed in seeds:
                repo.insert_work_object(conn, seed.page)
                conn.execute(
                    """INSERT INTO content.page_metadata (work_object_id,document_class,
                    authority_state,visibility_state,connected_page_operation_id)
                    VALUES (%s,%s,%s,%s,%s)""",
                    (seed.page.work_object_id, seed.metadata.document_class,
                     seed.metadata.authority_state, seed.metadata.visibility_state,
                     seed.metadata.connected_page_operation_id),
                )
                if seed.content_status == "committed":
                    # Actual first DB retention time, not a fabricated historical
                    # Save. Preserve the independent legacy object CAS revision.
                    revision = repo.insert_work_revision(conn, WorkRevision(
                        work_revision_id=uuid4(), work_object_id=seed.page.work_object_id,
                        world_id=seed.page.world_id, revision_n=1, markdown=seed.markdown,
                        content_sha256=seed.content_sha256, created_at=repo.now_utc(),
                    ))
                    conn.execute(
                        "UPDATE content.work_object SET current_revision_id=%s WHERE work_object_id=%s",
                        (revision.work_revision_id, seed.page.work_object_id),
                    )
                elif seed.markdown is not None:
                    repo.insert_working_copy(conn, WorkingCopy(
                        work_object_id=seed.page.work_object_id, markdown=seed.markdown,
                        content_sha256=seed.content_sha256, base_revision_id=None,
                        working_copy_revision=1, updated_at=seed.page.updated_at,
                    ))
            return PageAdoption("adopted", len(seeds))
    except psycopg.IntegrityError as exc:
        raise ApplicationStateConflictError("page adoption conflicts with stored Content") from exc
