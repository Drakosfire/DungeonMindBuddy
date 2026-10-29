"""Trusted-host native reads for recap review; no publication or identity choice."""

from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from apps.live_control_server.config import world_graph_authority_database_url
from dungeonmind.application.vnext import (
    EntityReadService,
    EvidenceReadService,
    SearchReadService,
    open_admitted_native_text,
    open_native_text_source_access_context,
)
from dungeonmind.infrastructure.postgres import (
    PostgresDatabase,
    PostgresNativeSourceEvidenceRepository,
)
from graph_memory.vnext.domain_runtime import (
    DungeonBuddyVNextProjectionInput,
    GM_LABEL,
    PLAYER_LABEL,
    build_dungeonbuddy_read_context,
    dungeonbuddy_world_domain_contract,
)


class NativeReviewConflict(ValueError):
    """The immutable snapshot cannot be returned as the current review context."""


def _repository():
    # Every connection made by this adapter is read-only, including source reads.
    authority_dsn = world_graph_authority_database_url()
    prior_options = conninfo_to_dict(authority_dsn).get("options", "")
    dsn = make_conninfo(authority_dsn, options=(
        prior_options + " -c default_transaction_read_only=on"
    ).strip())
    return PostgresNativeSourceEvidenceRepository(PostgresDatabase(dsn))


def _preview(access, evidence_ref_id):
    result = open_admitted_native_text(access, evidence_ref_id)
    packet = result.model_dump(mode="json", exclude={"body_text"})
    if result.status == "available":
        # Body availability is inspection authority, never campaign membership.
        # Return only the exact admitted span, not the shared World source body.
        packet["span_text"] = result.body_text.encode("utf-8")[
            result.span_start_byte : result.span_end_byte
        ].decode("utf-8")
    packet["purpose"] = "evidence_inspection_only"
    return packet


def resolve_native_review_context(*, scope: dict, nodes: list[dict]) -> dict:
    repository = _repository()
    world_id = scope["native_world_id"]
    head = repository.get_head(world_id)
    if head is None or not head.head_revision_id:
        raise NativeReviewConflict("native World has no current revision")
    revision_id = head.head_revision_id
    # Core loads and verifies the exact revision and pins one coherent source
    # view. The same view supplies assertion admission and source inspection.
    access = open_native_text_source_access_context(
        repository=repository,
        space_id=world_id,
        revision_id=revision_id,
        domain_contract=dungeonbuddy_world_domain_contract(),
        audience_labels=(GM_LABEL, PLAYER_LABEL),
    )
    projection = DungeonBuddyVNextProjectionInput(
        world_id=world_id,
        scope_mode="campaign",
        role="gm",
        campaign_id=scope["campaign_id"],
        session_id=scope["session_id"],
        standing_selector=("established", "provisional"),
        revision_id=revision_id,
    )
    context = build_dungeonbuddy_read_context(
        parsed_revision=access.parsed,
        projection_input=projection,
        source_reader=access.source_view,
    )
    search_service = SearchReadService()
    entities = EntityReadService()
    evidence_service = EvidenceReadService()
    selections = []
    for node in sorted(nodes, key=lambda item: item["node_id"]):
        # A matching label or even an exact ID is advisory. It never merges a
        # candidate with a native identity or chooses one of several targets.
        queries = list(dict.fromkeys(
            value for value in (node["node_id"], node.get("label"))
            if isinstance(value, str) and value.strip()
        ))
        searches = [search_service.search_entities(context, query) for query in queries]
        ids = sorted({hit.entity.entity_id for result in searches for hit in result.hits})
        alternatives = []
        for entity_id in ids:
            entity = entities.get_entity(context, entity_id)
            support = [
                evidence_service.get_assertion_evidence(context, assertion.assertion_id)
                for assertion in entity.assertions
            ]
            previews = {
                evidence.evidence_ref_id: _preview(access, evidence.evidence_ref_id)
                for result in support if result.available
                for evidence in result.evidence
            }
            supported = bool(entity.assertions) and all(
                result.available and bool(result.evidence) for result in support
            )
            alternatives.append({
                "entity_id": entity_id,
                "status": "supported_facts" if supported else "insufficient_support",
                "identity_approved": False,
                "entity_result": jsonable_encoder(entity),
                "assertion_support": jsonable_encoder(support),
                "source_inspection": [previews[key] for key in sorted(previews)],
            })
        selections.append({
            "candidate_node_id": node["node_id"],
            "status": (
                "absent" if not alternatives else "ambiguous" if len(alternatives) > 1
                else alternatives[0]["status"]
            ),
            "search_is_advisory": True,
            "queries": queries,
            "search_results": jsonable_encoder(searches),
            "alternatives": alternatives,
        })
    if repository.get_head(world_id) != head:
        raise NativeReviewConflict("native World head changed during review")
    return {
        "revision_id": revision_id,
        "head": jsonable_encoder(head),
        "source_authority_epoch": access.source_view.epoch,
        "projection_input": jsonable_encoder(projection),
        "domain_contract_ref": jsonable_encoder(access.parsed.domain_contract_ref),
        "semantic_profile_ref": jsonable_encoder(access.parsed.semantic_profile_ref),
        "projection_request": context.request.model_dump(mode="json"),
        "selections": selections,
        "identity_approval": False,
        # Core proves admission and provenance bindings. The review still owns
        # whether the cited words entail a claim or identify the same person.
        "semantic_support_verified": False,
    }
