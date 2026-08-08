"""Versioned extraction-profile protocol for production graph extraction."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol

# Profile-owned post-extraction gate. Returns human-readable errors; empty means ok.
PostExtractionValidator = Callable[[Mapping[str, Any]], Sequence[str]]


@dataclass(frozen=True)
class ExtractionPassSpec:
    pass_id: str
    default_node_type: str | None
    instruction: str
    progress_label: str
    kind: str = "node"  # node | beat | encounter_job | edge | claimed_fill
    include_dispositions: bool = False
    allowed_node_types: tuple[str, ...] | None = None


@dataclass(frozen=True)
class ExtractionProfile:
    """Executable extraction policy selected by exact profile_id + profile_version."""

    profile_id: str
    profile_version: str
    admitted_source_domains: frozenset[str]
    admitted_document_classes: frozenset[str] | None
    node_passes: tuple[ExtractionPassSpec, ...]
    beat_pass: ExtractionPassSpec | None
    encounter_job_pass: ExtractionPassSpec | None
    edge_pass: ExtractionPassSpec
    evidence_rule: str
    default_semantic_state: Mapping[str, str]
    enable_encounter_job_pass: bool = False
    enable_party_participation_attachment: bool = False
    enable_encounter_job_edge_guidance: bool = False
    enable_dynamic_node_vocabulary_packet: bool = False
    # Post-sanitize LLM fill onto deterministic PC/companion anchors using
    # known-entity mention claims. Descriptions + evidence only.
    enable_party_claimed_fill: bool = False
    # Recap-oriented session relationship sweep (session-sized counts, refugee/
    # siege/evac guidance). Profiles that own evergreen prose must set False.
    enable_session_relationship_sweep: bool = True
    # Same-run label/type-class consolidation (dedup_nodes + cross-class
    # reconcile). Profiles that forbid automatic identity merges set False so
    # ambiguous collisions remain separate candidates for review.
    enable_automatic_identity_consolidation: bool = True
    # When True (recap default), empty edge evidence_refs may be repaired by
    # copying an endpoint node's citation. Profiles that require relationship-
    # native evidence set False so empty edge evidence reaches validation.
    enable_edge_evidence_inheritance: bool = True
    allow_null_session: bool = False
    schema_ids: Mapping[str, str] = field(default_factory=dict)
    vocabulary_policy: Mapping[str, Any] = field(default_factory=dict)
    post_extraction_validation_policy: Mapping[str, Any] = field(default_factory=dict)
    # Executable profile-owned bounds check. Invoked by the generic production
    # controller before VALIDATED/REVIEWABLE. Descriptive policy mappings alone
    # are not sufficient — wire a callable when the profile declares bounds.
    post_extraction_validator: PostExtractionValidator | None = None

    @property
    def qualified_id(self) -> str:
        return f"{self.profile_id}@{self.profile_version}"

    def admits(
        self,
        *,
        source_domain: str,
        document_class: str | None = None,
        session_id: str | None,
    ) -> list[str]:
        errors: list[str] = []
        if source_domain not in self.admitted_source_domains:
            errors.append(
                f"profile {self.qualified_id} does not admit source_domain={source_domain!r}"
            )
        if (
            self.admitted_document_classes is not None
            and (
                document_class is None
                or document_class not in self.admitted_document_classes
            )
        ):
            errors.append(
                f"profile {self.qualified_id} requires document_class in "
                f"{sorted(self.admitted_document_classes)}; got {document_class!r}"
            )
        if session_id is None and not self.allow_null_session:
            errors.append(
                f"profile {self.qualified_id} requires session_id"
            )
        if session_id is not None and self.allow_null_session and source_domain == "worldbuilding":
            errors.append(
                f"profile {self.qualified_id} forbids fabricated session_id for worldbuilding"
            )
        return errors


class ExtractionProfileRegistry(Protocol):
    def get(self, profile_id: str, profile_version: str) -> ExtractionProfile: ...


class UnknownExtractionProfileError(ValueError):
    pass


class InadmissibleExtractionProfileError(ValueError):
    pass


_PROFILE_REGISTRY: dict[tuple[str, str], ExtractionProfile] = {}


def register_extraction_profile(profile: ExtractionProfile) -> ExtractionProfile:
    key = (profile.profile_id, profile.profile_version)
    _PROFILE_REGISTRY[key] = profile
    return profile


def get_extraction_profile(profile_id: str, profile_version: str) -> ExtractionProfile:
    if not profile_id or not profile_version:
        raise UnknownExtractionProfileError(
            "exact profile_id and profile_version are required"
        )
    key = (profile_id, profile_version)
    profile = _PROFILE_REGISTRY.get(key)
    if profile is None:
        raise UnknownExtractionProfileError(
            f"unknown extraction profile: {profile_id}@{profile_version}"
        )
    return profile


def require_admitted_profile(
    *,
    profile_id: str,
    profile_version: str,
    source_domain: str,
    document_class: str | None = None,
    session_id: str | None,
) -> ExtractionProfile:
    profile = get_extraction_profile(profile_id, profile_version)
    errors = profile.admits(
        source_domain=source_domain,
        document_class=document_class,
        session_id=session_id,
    )
    if errors:
        raise InadmissibleExtractionProfileError("; ".join(errors))
    return profile


def list_registered_profiles() -> Sequence[ExtractionProfile]:
    return tuple(_PROFILE_REGISTRY.values())
