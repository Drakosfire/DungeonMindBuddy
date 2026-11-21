"""Host-owned identity and placement proof for a typed Build Graph reference."""

from __future__ import annotations

import re

from pydantic import ConfigDict, Field, model_validator

from application_state.agent_conversation.authored_graph_references import AuthoredGraphReferenceV1
from application_state.build_proposal.prose_catalog import freeze_build_prose_catalog
from application_state.build_proposal.types import BuildProposalBasis, BuildProseBoundaryTarget, StrictModel
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
                or self.basis.selection is not None or self.basis.editor_sha256 is None):
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
