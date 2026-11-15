"""Page-only layout metadata. Markdown remains the sole content authority."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Annotated, Literal

from markdown_it import MarkdownIt
from pydantic import BaseModel, ConfigDict, Field
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from application_state.content.markdown_source_blocks import source_block_spans
from application_state.content.types import WorkRevision, sha256_utf8
from application_state.errors import (
    ApplicationStateValidationError,
    ApplicationStateIntegrityError,
)

# Same preserved-envelope recognition as Build's splitLeadingYamlFrontmatter.
_ENVELOPE = re.compile(
    r"^---[ \t]*(?:\r\n|\n)([\s\S]*?)(?:\r\n|\n)---[ \t]*(?:(?:\r\n|\n)|$)"
)
_KEY = re.compile(r"(?:^|\r?\n)[A-Za-z0-9_.-]+:\s*")


def leading_yaml(markdown: str) -> str:
    match = _ENVELOPE.match(markdown)
    return match[0] if match and _KEY.search(match[1]) else ""


Identifier = Annotated[
    str, Field(min_length=1, max_length=80, pattern=r"^[a-zA-Z0-9_-]+$")
]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class _Closed(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class BlockBinding(_Closed):
    kind: Literal["block"] = "block"
    id: Identifier
    byte_start: int = Field(ge=0)
    byte_end: int = Field(gt=0)
    sha256: Digest


class Slot(_Closed):
    id: Identifier
    width: int = Field(ge=2, le=12)
    blocks: list[BlockBinding] = Field(max_length=2048)


class Row(_Closed):
    kind: Literal["row"] = "row"
    id: Identifier
    slots: list[Slot] = Field(min_length=1, max_length=3)
    min_height: int = Field(default=0, ge=0, le=640, multiple_of=8)
    line_mode: Literal["guide", "border", "clean"] = "guide"


class PagePresentation(_Closed):
    schema_version: Literal["dmb_page_presentation_v1"] = "dmb_page_presentation_v1"
    markdown_sha256: Digest
    items: list[Annotated[BlockBinding | Row, Field(discriminator="kind")]] = Field(
        max_length=2048
    )

    def checked(self, markdown: str) -> "PagePresentation":
        if self.markdown_sha256 != sha256_utf8(markdown):
            raise ApplicationStateValidationError(
                "presentation does not bind exact Markdown"
            )
        prefix = leading_yaml(markdown)
        offset = len(prefix.encode("utf-8"))
        # The initial composer binds existing ordinary editor blocks only.
        # Do not accept raw HTML, fenced widgets, or source definitions that
        # the editor cannot reconstruct from one movable block.
        body = markdown[len(prefix) :]
        tokens = (
            MarkdownIt("commonmark", {"html": True})
            .enable("table")
            .parse(body, parser_environment)
        )
        if parser_environment.get("references"):
            raise ApplicationStateValidationError(
                "presentation cannot bind reference definitions"
            )
        allowed = {
            "paragraph_open",
            "heading_open",
            "table_open",
            "blockquote_open",
            "bullet_list_open",
            "ordered_list_open",
            "hr",
        }
        if any(
            token.type not in allowed
            for token in tokens
            if token.level == 0 and token.map
        ):
            raise ApplicationStateValidationError(
                "presentation contains unsupported source blocks"
            )
        if any(
            token.type in {"html_block", "fence", "code_block"}
            or any(child.type == "html_inline" for child in (token.children or []))
            for token in tokens
        ):
            raise ApplicationStateValidationError(
                "presentation contains unsupported source blocks"
            )
        expected = [
            (a + offset, b + offset)
            for a, b in source_block_spans(markdown[len(prefix) :])
        ]
        seen: set[str] = set()
        bindings = []

        def identity(value):
            if value in seen:
                raise ApplicationStateValidationError("duplicate presentation identity")
            seen.add(value)

        for item in self.items:
            identity(item.id)
            if isinstance(item, BlockBinding):
                bindings.append(item)
            else:
                if sum(slot.width for slot in item.slots) != 12:
                    raise ApplicationStateValidationError("row widths must sum to 12")
                if not any(slot.blocks for slot in item.slots):
                    raise ApplicationStateValidationError(
                        "empty presentation rows are not saved"
                    )
                for slot in item.slots:
                    identity(slot.id)
                    for block in slot.blocks:
                        identity(block.id)
                        bindings.append(block)
        if [(b.byte_start, b.byte_end) for b in bindings] != expected:
            raise ApplicationStateValidationError(
                "presentation must bind every complete body block in source order"
            )
        raw = markdown.encode("utf-8")
        if any(
            hashlib.sha256(raw[b.byte_start : b.byte_end]).hexdigest() != b.sha256
            for b in bindings
        ):
            raise ApplicationStateValidationError("presentation block digest mismatch")
        return self

    def fingerprint(self) -> str:
        return hashlib.sha256(
            json.dumps(
                self.model_dump(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode()
        ).hexdigest()


def read(conn, revision: WorkRevision | None) -> PagePresentation | None:
    if revision is None:
        return None
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "SELECT payload, presentation_sha256 FROM content.page_presentation WHERE work_revision_id=%s",
            (revision.work_revision_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    try:
        value = PagePresentation.model_validate(row["payload"]).checked(
            revision.markdown
        )
        if value.fingerprint() != row["presentation_sha256"]:
            raise ValueError("digest mismatch")
        return value
    except (ValueError, ApplicationStateValidationError) as exc:
        raise ApplicationStateIntegrityError(
            "saved Page presentation is invalid"
        ) from exc


def insert(conn, revision: WorkRevision, value: PagePresentation | None) -> None:
    if value is None:
        return
    value.checked(revision.markdown)
    conn.execute(
        "INSERT INTO content.page_presentation (work_revision_id, payload, presentation_sha256) VALUES (%s,%s,%s)",
        (revision.work_revision_id, Jsonb(value.model_dump()), value.fingerprint()),
    )


UNSET = object()


def candidate(value, markdown: str, current: PagePresentation | None):
    if value is UNSET:
        if current is not None:
            raise ApplicationStateValidationError(
                "composed Page requires explicit presentation; this client cannot save it"
            )
        return None
    if value is not None:
        return PagePresentation.model_validate(value).checked(markdown)
    return None
