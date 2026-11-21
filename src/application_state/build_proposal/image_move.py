"""Exact saved Page presentation proof for a typed Build image move."""

from __future__ import annotations

from copy import deepcopy
from uuid import UUID

from markdown_it import MarkdownIt
from pydantic import ConfigDict, model_validator

from application_state.agent_conversation.plan_authoring import strict_json
from application_state.build_proposal.image_move_layout import require_build_image_layout
from application_state.build_proposal.types import BuildProposalBasis, StrictModel
from application_state.content.page_presentation import BlockBinding, Digest, Identifier, PagePresentation, Row
from application_state.content.types import sha256_utf8
from application_state.errors import ApplicationStateConflictError


class BuildImageMovePlacement(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    basis: BuildProposalBasis
    presentation_sha256: Digest
    row_id: Identifier
    source_slot_id: Identifier
    destination_slot_id: Identifier
    image_block_id: Identifier

    @model_validator(mode="after")
    def exact_saved_composed_basis(self):
        if (
            self.basis.visibility != "internal"
            or self.basis.editor_sha256 is None
            or self.basis.draft_sha256 != self.basis.content_sha256
            or self.source_slot_id == self.destination_slot_id
        ):
            raise ValueError("Image movement requires an exact saved internal Page and distinct slots")
        return self

    def project_saved_move(self, before: PagePresentation, markdown: str) -> tuple[PagePresentation, str]:
        """Project the only allowed layout delta and resolve the exact saved media identity."""
        if sha256_utf8(markdown) != self.basis.content_sha256 or before.fingerprint() != self.presentation_sha256:
            raise ApplicationStateConflictError("The captured Page layout changed")
        before.checked(markdown)

        for index, item in enumerate(before.items):
            if isinstance(item, Row) and item.id == self.row_id:
                row_index, row = index, item
                break
        else:
            raise ApplicationStateConflictError("The offered image row is unavailable")

        for index, slot in enumerate(row.slots[:-1]):
            if slot.id == self.source_slot_id:
                source_index, source = index, slot
                break
        else:
            raise ApplicationStateConflictError("The offered image has no adjacent right slot")

        destination = row.slots[source_index + 1]
        image = source.blocks[-1] if source.blocks else None
        if (
            destination.id != self.destination_slot_id
            or destination.blocks
            or not isinstance(image, BlockBinding)
            or image.id != self.image_block_id
        ):
            raise ApplicationStateConflictError("The offered image must be at the edge beside an empty right slot")

        image_source = markdown.encode("utf-8")[image.byte_start:image.byte_end].decode("utf-8")
        tokens = MarkdownIt("commonmark", {"html": True}).parse(image_source)
        if [token.type for token in tokens] != ["paragraph_open", "inline", "paragraph_close"]:
            raise ApplicationStateConflictError("The offered block is not a standalone managed image")
        children = tokens[1].children or []
        if len(children) != 1 or children[0].type != "image":
            raise ApplicationStateConflictError("The offered block is not a standalone managed image")
        target = children[0].attrGet("src") or ""
        try:
            if not target.startswith("dmb-media:") or target != f"dmb-media:{UUID(target[10:])}":
                raise ValueError("Not a managed image")
        except ValueError as error:
            raise ApplicationStateConflictError("The offered block is not a standalone managed image") from error

        slots = list(row.slots)
        slots[source_index] = source.model_copy(update={"blocks": source.blocks[:-1]})
        slots[source_index + 1] = destination.model_copy(update={"blocks": [image]})
        items = list(before.items)
        items[row_index] = row.model_copy(update={"slots": slots})
        return before.model_copy(update={"items": items}).checked(markdown), target[10:]


    def project_editor_move(self, editor_json: str, saved: PagePresentation, markdown: str, asset_id: str) -> dict:
        """Verify the exact editor and its saved media identity before computing the only permitted delta."""
        if sha256_utf8(editor_json) != self.basis.editor_sha256:
            raise ApplicationStateConflictError("The captured editor changed")
        try:
            before = strict_json(editor_json)
            require_build_image_layout(before, markdown, saved)
            projected = deepcopy(before)
            if projected["type"] != "doc":
                raise ValueError("Expected a document")
            rows = [
                row for row in projected["content"]
                if row["type"] == "pageRow" and row["attrs"]["id"] == self.row_id
            ]
            if len(rows) != 1:
                raise ValueError("The row is not unique")
            row = rows[0]
            slots = row["content"]
            offered = [
                (source, destination) for source, destination in zip(slots, slots[1:])
                if source["type"] == destination["type"] == "pageSlot"
                and source["attrs"]["id"] == self.source_slot_id
                and destination["attrs"]["id"] == self.destination_slot_id
            ]
            if len(offered) != 1:
                raise ValueError("The slot pair is not unique")
            source, destination = offered[0]
            source_blocks = source["content"]
            block = source_blocks[-1]
            children = block.get("content", [])
            if (
                destination.get("content")
                or block["type"] != "paragraph"
                or block["attrs"]["pageBlockId"] != self.image_block_id
                or len(children) != 1
                or children[0]["type"] != "mediaImage"
                or children[0]["attrs"]["assetId"] != asset_id
            ):
                raise ValueError("Expected one standalone image beside an empty slot")
            destination["content"] = [source_blocks.pop()]
            if not source_blocks:
                del source["content"]
        except (TypeError, ValueError, KeyError, IndexError, AttributeError, StopIteration) as error:
            raise ApplicationStateConflictError("The editor does not carry the exact offered image and slot") from error
        return projected
