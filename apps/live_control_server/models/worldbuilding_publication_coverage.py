"""Historical terminal publication facts, separate from extraction readiness."""

from typing import Literal

from pydantic import Field

from apps.live_control_server.models.extract_promote import _ExtractPromoteModel


class WorldbuildingPublicationFacet(_ExtractPromoteModel):
    facet: Literal["existence", "description", "alias", "observation", "relationship"]
    assertion_id: str
    subject_node_id: str
    verdict: Literal["accepted", "rejected"]
    native_operation_id: str
    published_revision_id: str


class WorldbuildingCandidatePublicationCoverage(_ExtractPromoteModel):
    candidate_id: str
    candidate_kind: Literal["node", "edge", "source_observation"]
    status: Literal["published_facts", "rejected_facts", "not_published", "unknown"]
    facets: list[WorldbuildingPublicationFacet] = Field(default_factory=list)


class WorldbuildingHistoricalPublicationReceipt(_ExtractPromoteModel):
    native_operation_id: str
    review_id: str
    parent_revision_id: str
    published_revision_id: str
    reviewed_contribution_id: str
    reviewed_contribution_sha256: str
    unmapped_assertion_ids: list[str] = Field(default_factory=list)


class WorldbuildingPublicationCoverage(_ExtractPromoteModel):
    schema_: Literal["dmb_worldbuilding_publication_coverage_v1"] = Field(
        default="dmb_worldbuilding_publication_coverage_v1", alias="schema",
    )
    run_id: str
    managed_world_id: str
    native_world_id: str
    revision_id: str
    source_artifact_id: str
    source_revision_id: str
    status: Literal["published", "not_published", "unknown"]
    historical_only: Literal[True] = True
    scanned_revision_count: int
    publications: list[WorldbuildingHistoricalPublicationReceipt] = Field(default_factory=list)
    candidates: list[WorldbuildingCandidatePublicationCoverage] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
