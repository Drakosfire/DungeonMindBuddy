"""Strict models for approved GraphContribution bundles (PR006C)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from graph_memory.kernel.contribution_models import GraphContribution
from graph_memory.kernel.identity_models import IdentityDecisionRecord


class _BundleModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ContributionBundleEntry(_BundleModel):
    path: str
    sha256: str
    contribution_id: str


class SharedSupportExpectation(_BundleModel):
    node_id: str
    contribution_paths: list[str]
    source_domains: list[str]


class ContributionBundleManifest(_BundleModel):
    schema_: str = Field(alias="schema")
    version: str
    bundle_id: str
    world_id: str
    primary_campaign_scope: str
    planning_focus: str
    focus_sessions: list[str]
    ordered_contributions: list[ContributionBundleEntry]
    identity_decisions: list[str]
    required_node_ids: list[str]
    required_edge_ids: list[str]
    expected_source_domains: list[str]
    expected_shared_support: list[SharedSupportExpectation]
    non_claims: list[str]
    bundle_digest: str

    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class LoadedContributionBundle(_BundleModel):
    bundle_path: Path
    manifest: ContributionBundleManifest
    contributions: list[GraphContribution]
    identity_decision_records: list[IdentityDecisionRecord] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", strict=True, arbitrary_types_allowed=True)


class ContributionBundleValidationReport(_BundleModel):
    bundle_id: str
    bundle_digest: str
    world_id: str
    primary_campaign_scope: str
    contribution_count: int
    identity_decision_count: int
    accepted_assertion_count: int
    rejected_assertion_count: int
    unresolved_mention_count: int
    assertion_counts_by_kind: dict[str, int]
    source_domains: list[str]
    required_node_count: int
    required_edge_count: int
    evidence_coverage: dict[str, Any]
    shared_support_expectations: list[dict[str, Any]]
    validation_errors: list[str]
    validation_warnings: list[str]
    ok: bool
