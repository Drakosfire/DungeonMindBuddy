"""Host-owned identity and placement proof for a typed Build Graph reference."""

from __future__ import annotations

import re

from markdown_it import MarkdownIt
from pydantic import ConfigDict, Field, model_validator

from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
from application_state.agent_conversation.plan_authoring import strict_json
from application_state.agent_conversation.plan_slot_layout import prose_editor_node_size
from application_state.build_proposal.prose_catalog import freeze_build_prose_catalog
from application_state.build_proposal.types import BuildProposalBasis, BuildProseBoundaryTarget, StrictModel
from application_state.content.markdown_source_blocks import source_block_spans
from application_state.errors import ApplicationStateConflictError


class BuildGraphReferencePlacement(StrictModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    basis: BuildProposalBasis
    boundary: BuildProseBoundaryTarget
    reference: AuthoredGraphReferenceV1
    entity_kind: str = Field(min_length=1)

    @model_validator(mode="after")
    def exact_world_and_editor(self):
        if (self.reference.managed_world_id != self.basis.world_id
                or self.basis.visibility != "internal" or self.basis.selection is not None
                or self.basis.editor_sha256 is None):
            raise ValueError("A Graph reference placement requires its World and captured root boundary")
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]*", self.reference.node_id):
            raise ValueError("The selected Graph identity cannot be represented by a typed reference")
        return self

    def require_boundary(self, editor_json: str, draft_markdown: str) -> None:
        try:
            catalog = freeze_build_prose_catalog(self.basis, editor_json, draft_markdown)
            alias, _ = self.boundary.alias.rsplit(":", 1)
            offered = catalog.target(alias, self.boundary.operation)
        except ValueError as error:
            raise ApplicationStateConflictError("The captured Graph reference boundary changed") from error
        if offered != self.boundary:
            raise ApplicationStateConflictError("The captured Graph reference boundary changed")

    def require_editor_insertion(self, editor_json: str, draft_markdown: str, after_editor_json: str) -> int:
        """Admit only the typed atom at the frozen root boundary and preserve all siblings."""
        self.require_boundary(editor_json, draft_markdown)
        before = strict_json(editor_json)
        original = before["content"]
        positions = {0: 0}
        position = 0
        for index, block in enumerate(original, start=1):
            position += prose_editor_node_size(block)
            positions[position] = index
        index = positions[self.boundary.from_]
        try:
            after = strict_json(after_editor_json)
        except ValueError as error:
            raise ApplicationStateConflictError("The Graph reference needs a valid editor insertion") from error
        if not isinstance(after, dict) or not isinstance(after.get("content"), list):
            raise ApplicationStateConflictError("The Graph reference needs a valid editor insertion")
        blocks = after["content"]
        if (len(blocks) != len(original) + 1
                or {**after, "content": blocks[:index] + blocks[index + 1:]} != before):
            raise ApplicationStateConflictError("The Graph reference insertion would change unrelated content")
        paragraph = blocks[index]
        if not isinstance(paragraph, dict):
            raise ApplicationStateConflictError("The Graph reference must insert exactly one typed atom")
        attrs = paragraph.get("attrs", {})
        retained = any(block.get("attrs", {}).get("pageBlockId") for block in original)
        block_id = f"page-graph-ref-{self.boundary.catalog_sha256[:32]}-{self.boundary.from_}" if retained else None
        expected = [{"type": "runbookReference", "attrs": {
            "kind": "ref", "refType": "graph-node", "refId": self.reference.node_id,
            "label": " ".join(self.reference.label.split()),
        }}]
        if (paragraph.get("type") != "paragraph" or paragraph.get("content") != expected
                or paragraph.keys() - {"type", "attrs", "content"} or not isinstance(attrs, dict)
                or attrs.get("pageBlockId") != block_id
                or any(key != "pageBlockId" and value is not None for key, value in attrs.items())):
            raise ApplicationStateConflictError("The Graph reference must insert exactly one typed atom")
        return index

    def require_draft_insertion(self, before: str, after: str, index: int) -> None:
        """Verify the editor's serialized typed link and its exact surrounding bytes."""
        original = before.encode("utf-8")
        updated = after.encode("utf-8")
        blocks = source_block_spans(after)
        if len(blocks) != len(source_block_spans(before)) + 1 or not 0 <= index < len(blocks):
            raise ApplicationStateConflictError("The serialized Graph reference changed the page blocks")
        start, end = blocks[index]
        block = updated[start:end]
        fragment = block.strip(b"\n")
        start += len(block) - len(block.lstrip(b"\n"))
        end = start + len(fragment)
        prefix = updated[:start]
        suffix = updated[end:]
        separator = b"\n\n"
        if not ((prefix.endswith(separator) and prefix[:-len(separator)] + suffix == original)
                or (suffix.startswith(separator) and prefix + suffix[len(separator):] == original)):
            raise ApplicationStateConflictError("The serialized Graph reference would change unrelated bytes")
        parsed = MarkdownIt("commonmark").parse(fragment.decode("utf-8"))
        if [token.type for token in parsed] != ["paragraph_open", "inline", "paragraph_close"]:
            raise ApplicationStateConflictError("The serialized Graph reference must be one typed link")
        children = parsed[1].children or []
        if ([token.type for token in children] != ["link_open", "text", "link_close"]
                or children[0].attrs != {"href": f"#dmb-ref:graph-node:{self.reference.node_id}"}
                or children[1].content != " ".join(self.reference.label.split())):
            raise ApplicationStateConflictError("The serialized Graph reference differs from the authorized identity")
