"""Product selection and fail-closed status mapping for read-only rules search."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Protocol

from apps.live_control_server.models.rules_query import (
    RulesEvidenceItem, RulesQueryPacket, RulesQueryRequest, RulesQueryTrace,
)


@dataclass(frozen=True)
class RulesSpaceBinding:
    ruleset_id: str
    space_id: str
    revision_id: str
    graph_payload_sha256: str
    domain_contract: dict
    semantic_profile: dict
    source_artifacts: list[dict]
    source_revisions: list[dict]
    evidence_units: dict[str, dict]


@dataclass(frozen=True)
class RulesSearchOutcome:
    evidence: tuple[RulesEvidenceItem, ...]
    search_result_digest: str
    searched_entities: int
    admitted_assertions: int
    completeness: str
    reason: str | None = None


class RulesSpaceUnavailable(RuntimeError):
    pass


class RulesSearchFailure(RuntimeError):
    pass


class RulesSearchPort(Protocol):
    def search(self, binding: RulesSpaceBinding, question: str, *, max_hits: int) -> RulesSearchOutcome: ...


def load_binding(path: Path) -> RulesSpaceBinding:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema_version") != "dmb_rules_space_binding_v1":
        raise ValueError("Unsupported rules binding manifest")
    if len(value.get("graph_payload_sha256", "")) != 64:
        raise ValueError("Rules binding lacks exact payload digest")
    return RulesSpaceBinding(
        ruleset_id=value["ruleset_id"],
        space_id=value["space_id"],
        revision_id=value["revision_id"],
        graph_payload_sha256=value["graph_payload_sha256"],
        domain_contract=value["domain_contract"],
        semantic_profile=value["semantic_profile"],
        source_artifacts=value["source_artifacts"],
        source_revisions=value["source_revisions"],
        evidence_units=value["evidence_units"],
    )


def query_rules(
    request: RulesQueryRequest,
    *,
    binding: RulesSpaceBinding | None,
    source: RulesSearchPort,
) -> RulesQueryPacket:
    space_id = binding.space_id if binding and request.ruleset_id == binding.ruleset_id else None
    revision_id = binding.revision_id if space_id else None
    query_material = json.dumps(
        [request.ruleset_id, request.question, revision_id], ensure_ascii=False, separators=(",", ":")
    )
    query_id = "rules-query:" + sha256(query_material.encode("utf-8")).hexdigest()[:32]
    if space_id is None:
        return RulesQueryPacket(
            query_id=query_id, ruleset_id=request.ruleset_id,
            status="rules_space_unavailable",
            trace=RulesQueryTrace(searched_revision_id="", completeness="unavailable",
                                  reason="ruleset_not_configured"),
        )
    try:
        result = source.search(binding, request.question, max_hits=request.max_hits)
    except RulesSpaceUnavailable:
        return RulesQueryPacket(
            query_id=query_id, ruleset_id=request.ruleset_id,
            rules_space_id=space_id, rules_revision_id=revision_id,
            status="rules_space_unavailable",
            trace=RulesQueryTrace(searched_revision_id=revision_id,
                                  completeness="unavailable", reason="rules_space_unavailable"),
        )
    except Exception:
        return RulesQueryPacket(
            query_id=query_id, ruleset_id=request.ruleset_id,
            rules_space_id=space_id, rules_revision_id=revision_id,
            status="downstream_failure",
            trace=RulesQueryTrace(searched_revision_id=revision_id,
                                  completeness="unavailable", reason="rules_search_failed"),
        )
    if result.completeness != "complete":
        status = "insufficient_evidence"
    elif not result.evidence:
        status = "no_evidence"
    else:
        status = "success"
    return RulesQueryPacket(
        query_id=query_id, ruleset_id=request.ruleset_id,
        rules_space_id=space_id, rules_revision_id=revision_id,
        status=status, evidence=list(result.evidence),
        trace=RulesQueryTrace(
            searched_revision_id=revision_id,
            search_result_digest=result.search_result_digest,
            searched_entities=result.searched_entities,
            admitted_assertions=result.admitted_assertions,
            returned_evidence=len(result.evidence),
            completeness="complete" if result.completeness == "complete" else "partial",
            reason=result.reason,
        ),
    )
