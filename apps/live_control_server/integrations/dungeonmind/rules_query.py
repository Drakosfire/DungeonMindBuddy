"""Exact-revision DungeonMind vNext rules search; no World or app-state writes."""

from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable

from dungeonmind.application.vnext.admission import AlwaysAdmitPolicy
from dungeonmind.application.vnext.builder import build_parsed_knowledge_revision
from dungeonmind.application.vnext.evidence_reads import EvidenceReadService
from dungeonmind.application.vnext.materialization import decode_native_graph_payload
from dungeonmind.application.vnext.provenance import InMemoryKnowledgeSourceReader
from dungeonmind.application.vnext.read_context import KnowledgeReadContext
from dungeonmind.application.vnext.search import SearchReadService
from dungeonmind.contracts.vnext.common import KnowledgeStanding, ScopeSelector
from dungeonmind.contracts.vnext.domain import DomainContractDescriptor, parse_semantic_profile_descriptor
from dungeonmind.contracts.vnext.projection import ProjectionRequest
from dungeonmind.contracts.vnext.source import SourceArtifactV3, SourceRevisionV2
from dungeonmind.infrastructure.postgres.database import PostgresDatabase
from dungeonmind.infrastructure.postgres.vnext_knowledge import PostgresKnowledgeRevisionRepository

from apps.live_control_server.models.rules_query import RulesEvidenceItem
from apps.live_control_server.services.rules_query import (
    RulesSearchOutcome, RulesSpaceBinding, RulesSpaceUnavailable,
)


class DungeonMindRulesSearch:
    """Port adapter with an injectable repository factory for server-level tests."""

    def __init__(
        self,
        database_url: str | None,
        *,
        repository_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._database_url = database_url
        self._repository_factory = repository_factory

    def _repository(self) -> Any:
        if self._repository_factory is not None:
            return self._repository_factory()
        if not self._database_url:
            raise RulesSpaceUnavailable("Rules database is not configured")
        return PostgresKnowledgeRevisionRepository(PostgresDatabase(self._database_url))

    def search(
        self, binding: RulesSpaceBinding, question: str, *, max_hits: int
    ) -> RulesSearchOutcome:
        repository = self._repository()
        stored = repository.get_revision(binding.space_id, binding.revision_id)
        if stored is None:
            raise RulesSpaceUnavailable("Configured rules revision is unavailable")
        if stored.graph_payload_sha256 != binding.graph_payload_sha256:
            raise ValueError("Configured rules revision payload differs from trusted binding")
        parsed = build_parsed_knowledge_revision(
            revision=stored.revision,
            decoded_content=decode_native_graph_payload(stored.graph_payload),
        )
        domain = DomainContractDescriptor.model_validate(binding.domain_contract)
        profile = parse_semantic_profile_descriptor(binding.semantic_profile)
        artifacts = {
            item.source_artifact_id: item
            for item in (SourceArtifactV3.model_validate(raw) for raw in binding.source_artifacts)
        }
        revisions = {
            item.source_revision_id: item
            for item in (SourceRevisionV2.model_validate(raw) for raw in binding.source_revisions)
        }
        context = KnowledgeReadContext(
            parsed=parsed,
            request=ProjectionRequest(
                space_id=binding.space_id,
                revision_id=binding.revision_id,
                scope_selector=ScopeSelector(include_unscoped=True),
                standing_selector=[KnowledgeStanding.ESTABLISHED],
            ),
            domain_contract=domain,
            semantic_profile=profile,
            domain_policy=AlwaysAdmitPolicy(policy_id=domain.admission_policy_id),
            source_reader=InMemoryKnowledgeSourceReader(artifacts=artifacts, revisions=revisions),
        )
        search = SearchReadService().search_entities(context, question, limit=max_hits)
        evidence_reads = EvidenceReadService()
        evidence: list[RulesEvidenceItem] = []
        admitted_assertions = 0
        partial = search.completeness.status != "complete"
        for rank, hit in enumerate(search.hits, 1):
            for assertion in hit.admitted_match_assertions:
                admitted_assertions += 1
                support = evidence_reads.get_assertion_evidence(context, assertion.assertion_id)
                if not support.available or support.completeness.status != "complete":
                    partial = True
                    continue
                anchors = {item.evidence_ref_id: item for item in support.anchors}
                for item in support.evidence:
                    prefix = "rulesingestion:evidence-unit:"
                    if not item.source_locator or not item.source_locator.startswith(prefix):
                        partial = True
                        continue
                    unit_id = item.source_locator.removeprefix(prefix)
                    unit = binding.evidence_units.get(unit_id)
                    if unit is None or sha256(unit["text"].encode("utf-8")).hexdigest() != unit["text_sha256"]:
                        partial = True
                        continue
                    anchor = anchors.get(item.evidence_ref_id)
                    evidence.append(RulesEvidenceItem(
                        rank=rank,
                        entity_id=hit.entity.entity_id,
                        assertion_id=assertion.assertion_id,
                        evidence_ref_id=item.evidence_ref_id,
                        evidence_unit_id=unit_id,
                        source_artifact_id=item.source_artifact_id,
                        source_revision_id=item.source_revision_id,
                        source_uri=item.uri,
                        source_locator=item.source_locator,
                        locator=item.locator,
                        source_anchor_id=anchor.anchor_id if anchor else None,
                        excerpt=unit["text"],
                    ))
        return RulesSearchOutcome(
            evidence=tuple(evidence),
            search_result_digest=search.result_digest,
            searched_entities=len(search.hits),
            admitted_assertions=admitted_assertions,
            completeness="partial" if partial else "complete",
            reason=search.completeness.reason if partial else None,
        )
