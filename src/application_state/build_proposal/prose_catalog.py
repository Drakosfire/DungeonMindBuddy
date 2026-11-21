"""Complete root prose boundary offers from one exact Build editor and draft."""

from __future__ import annotations

import json
from hashlib import sha256
from typing import Literal

from pydantic import ConfigDict, Field

from application_state.agent_conversation.plan_authoring import strict_json
from application_state.agent_conversation.plan_slot_layout import (
    prose_editor_node_size,
    require_matching_prose_block,
)
from application_state.content.markdown_source_blocks import source_block_spans
from .types import BuildProposalBasis, BuildProseBoundaryTarget, BuildWriteCapability, StrictModel


def _digest(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


class BuildProseOccurrence(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    alias: str = Field(pattern=r"^passage[1-9][0-9]*$")
    passage: str = Field(min_length=1)
    headings: tuple[str, ...]
    before: int = Field(ge=0)
    after: int = Field(ge=1)

    def choices(self):
        section = " / ".join(self.headings) or "Before the first heading"
        return tuple(dict(selector=f"{self.alias}:{operation}", operation=operation,
                          section=section, passage=self.passage)
                     for operation in ("insert_before", "insert_after"))


class BuildProseBoundaryCatalog(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["dmb_build_prose_boundary_catalog_v1"] = "dmb_build_prose_boundary_catalog_v1"
    editor_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    editor_size: int = Field(ge=0)
    passages: tuple[BuildProseOccurrence, ...]

    @property
    def choices_sha256(self) -> str:
        # Keep the exact order/keys from the mounted Build catalog.
        choices = [choice for passage in self.passages for choice in passage.choices()]
        return _digest(json.dumps(choices, ensure_ascii=False, separators=(",", ":")))

    def target(self, alias: str, operation: Literal["insert_before", "insert_after"]) -> BuildProseBoundaryTarget:
        passage = next((candidate for candidate in self.passages if candidate.alias == alias), None)
        if passage is None:
            raise ValueError("Build requested a prose alias outside its exact catalog")
        position = passage.before if operation == "insert_before" else passage.after
        return BuildProseBoundaryTarget(
            catalog_sha256=self.choices_sha256, alias=f"{alias}:{operation}",
            operation=operation, **{"from": position, "to": position},
            before_text_sha256=_digest(passage.passage),
        )


def freeze_build_prose_catalog(
    basis: BuildProposalBasis, editor_json: str, draft: str,
) -> BuildProseBoundaryCatalog:
    """Refuse altered input, then inspect every supported root block in order."""
    if basis.selection is not None or basis.editor_sha256 != _digest(editor_json) or basis.draft_sha256 != _digest(draft):
        raise ValueError("Build prose offers require the exact draft and an unrelated collapsed caret")
    editor = strict_json(editor_json)
    if not isinstance(editor, dict) or editor.get("type") != "doc" or not isinstance(editor.get("content"), list):
        raise ValueError("Build prose offers require an exact editor document")
    source = draft.encode("utf-8")
    spans = source_block_spans(draft)
    if len(spans) != len(editor["content"]):
        raise ValueError("Build prose editor differs from its exact root Markdown")
    position = 0
    headings = []
    passages = []
    for block, (start, end) in zip(editor["content"], spans, strict=True):
        if not isinstance(block, dict) or block.get("type") not in {"heading", "paragraph", "horizontalRule"}:
            raise ValueError("Build contextual placement requires an admitted root prose page")
        attrs = block.get("attrs", {})
        if not isinstance(attrs, dict) or any(
            value is not None and key not in {"level", "pageBlockId"} for key, value in attrs.items()
        ):
            raise ValueError("Build prose block has metadata absent from the Markdown")
        if block["type"] == "heading" and type(attrs.get("level")) is not int:
            raise ValueError("Build prose heading requires its exact editor level")
        require_matching_prose_block(block, source[start:end].decode("utf-8"))
        after = position + prose_editor_node_size(block)
        text = "".join(child["text"] for child in block.get("content", []) if child.get("type") == "text")
        if block["type"] == "heading":
            level = block["attrs"]["level"]
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, text))
        elif block["type"] == "paragraph" and text.strip() and all(
            child["type"] == "text"
            and all(mark["type"] in {"bold", "italic", "strike", "code", "underline"}
                    for mark in child.get("marks", []))
            for child in block.get("content", [])
        ):
            passages.append(BuildProseOccurrence(
                alias=f"passage{len(passages) + 1}", passage=text,
                headings=tuple(title for _, title in headings), before=position, after=after,
            ))
        position = after
    if basis.caret > position:
        raise ValueError("Build prose caret is outside the exact editor snapshot")
    return BuildProseBoundaryCatalog(editor_sha256=basis.editor_sha256,
                                     draft_sha256=basis.draft_sha256, editor_size=position,
                                     passages=tuple(passages))


def catalog_for_build_capability(capability: BuildWriteCapability | None) -> BuildProseBoundaryCatalog | None:
    if capability is None or capability.boundary_editor_json is None:
        return None
    return freeze_build_prose_catalog(capability.basis, capability.boundary_editor_json, capability.draft_markdown)
