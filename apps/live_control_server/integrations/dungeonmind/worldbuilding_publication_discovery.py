"""Verify sealed candidate hypotheses against native historical publications."""

from __future__ import annotations

import json
from dataclasses import replace

from apps.live_control_server.ports.world_graph_authority import (
    WorldbuildingHistoricalPublication,
    WorldbuildingPublicationDiscoveryRequest,
    WorldbuildingPublicationHistory,
    WorldbuildingPublishedFacet,
    WorldGraphAuthorityError,
)


def _value(assertion):
    value = json.loads(assertion.value) if assertion.value else {}
    return value if isinstance(value, dict) else {}


def _hypotheses(request, bindings):
    from graph_memory.worldbuilding_write_plan import _map_edge, _map_node, _candidate_kernel_kind
    from graph_memory.candidate_graph_to_contribution import map_connect_existing_support_assertions

    common = dict(
        source_revision_id=request.source_revision_id,
        source_artifact_id=request.source_artifact_id,
        campaign_scope=None, source_uri=request.source_uri,
    )
    support_common = {**common, "verified_source_artifact_id": common["source_artifact_id"]}
    del support_common["source_artifact_id"]
    support_common.update(source_domain="worldbuilding", session_id=None, campaign_id=None,
                          predicate="worldbuilding_observation", alias_owners={})
    nodes = {node.node_id: node for node in request.preview.nodes}
    for node in nodes.values():
        for verdict in ("accepted", "rejected"):
            yield node.node_id, "node", "existence", _map_node(
                node, **common, acceptance_state=verdict,
                identity_resolution_outcome="created_new" if verdict == "accepted"
                else "rejected_by_operator",
            )
            target = bindings.get(node.node_id)
            if target is not None:
                rows, _ = map_connect_existing_support_assertions(
                    node, **support_common, durable_node_id=target,
                    acceptance_state=verdict, identity_resolution_outcome="human_override",
                    kind_override=_candidate_kernel_kind(node),
                )
                for row in rows:
                    yield node.node_id, "node", ("alias" if row.assertion_kind == "alias"
                        else "description" if (node.description or "").strip()
                        else "observation"), row
    for observation in request.preview.source_observations:
        target = bindings.get(observation.subject_candidate_node_id)
        if target is None:
            continue
        node = replace(nodes[observation.subject_candidate_node_id],
            node_id=observation.observation_id, label=observation.title,
            description=observation.description, evidence_refs=observation.evidence_refs,
            semantic_state=observation.semantic_state, confidence=observation.confidence,
            warnings=observation.warnings, proposed_action=observation.proposed_action,
            aliases=(), corpus_ref=None, session_actions=(), enriched_by=None)
        for verdict in ("accepted", "rejected"):
            rows, _ = map_connect_existing_support_assertions(
                node, **support_common, durable_node_id=target,
                acceptance_state=verdict, identity_resolution_outcome="human_override",
                kind_override=_candidate_kernel_kind(nodes[observation.subject_candidate_node_id]),
            )
            for row in rows:
                yield observation.observation_id, "source_observation", "observation", row
    for edge in request.preview.edges:
        if edge.from_node_id not in bindings or edge.to_node_id not in bindings:
            continue
        for verdict in ("accepted", "rejected"):
            yield edge.edge_id, "edge", "relationship", _map_edge(
                edge, **common, acceptance_state=verdict,
                identity_resolution_outcome="accepted_by_operator" if verdict == "accepted"
                else "rejected_by_operator", node_id_map=bindings,
            )


def discover_worldbuilding_publications(bundle, request: WorldbuildingPublicationDiscoveryRequest):
    from dungeonmind.application import discover_review_publications
    from dungeonmind.contracts.contribution import AcceptanceState
    from apps.live_control_server.integrations.dungeonmind import world_graph_writes as writes
    from apps.live_control_server.integrations.dungeonmind.world_graph_authority_adapter import (
        _worldbuilding_expressible,
    )
    from apps.live_control_server.integrations.dungeonmind.world_graph_source_admission_adapter import (
        DungeonMindWorldGraphSourceAdmissionAdapter,
    )
    from apps.live_control_server.models.world_graph_contributions import create_graph_contribution
    from apps.live_control_server.services.worldbuilding_graph_publication import (
        _qualify_worldbuilding_native_edges, _worldbuilding_native_vocabulary_binding,
    )
    from apps.live_control_server.integrations.dungeonmind.contribution_mapping import (
        map_worldbuilding_extraction_contribution_v3,
    )

    history = discover_review_publications(
        world_id=request.world_id, revision_id=request.revision_id,
        reviewer_id=request.run_id, source_plan_schema=writes.WORLDBUILDING_SOURCE_PLAN_SCHEMA,
        world_graph_repository=bundle.world_graph,
        publication_repository=bundle.finalized_review_publications,
        review_repository=bundle.contribution_reviews,
    )
    publications = history.publications
    if not publications:
        return WorldbuildingPublicationHistory(
            request.world_id, request.revision_id, request.run_id, request.source_artifact_id,
            request.source_revision_id, (), history.scanned_revision_count,
        )
    pair = (request.source_artifact_id, request.source_revision_id)
    pair_to_dm = writes.catalog_aware_source_revision_ids(bundle.sources, request.world_id, {pair})
    admitted = DungeonMindWorldGraphSourceAdmissionAdapter(sources=bundle.sources).prove(
        world_id=request.world_id, source_artifact_id=pair[0],
        source_revision_id=pair_to_dm[pair], source_revision_token=pair[1],
    )
    if admitted.content_sha256 != pair[1].removeprefix("sha256:"):
        raise WorldGraphAuthorityError("Historical source content disagrees", code="integrity_failure")
    nodes = {node.node_id: node for node in request.preview.nodes}
    observations = {row.observation_id: row for row in request.preview.source_observations}
    proposed_bindings = {}
    for entry in publications:
        contribution = entry.review.reviewed_contribution
        if (contribution.source_artifact_id != pair[0]
                or contribution.source_revision_id != pair_to_dm[pair]
                or contribution.campaign_scope is not None):
            raise WorldGraphAuthorityError("Run publication source disagrees", code="integrity_failure")
        for row in contribution.assertions:
            if (row.source_artifact_id != pair[0]
                    or row.source_revision_id != pair_to_dm[pair]):
                raise WorldGraphAuthorityError("Assertion source disagrees", code="integrity_failure")
            if row.acceptance_state != AcceptanceState.ACCEPTED:
                continue
            value = _value(row)
            candidate_id = (row.subject_object_id if row.assertion_kind == "node"
                            else value.get("extract_node_id"))
            if candidate_id in observations:
                candidate_id = observations[candidate_id].subject_candidate_node_id
            if candidate_id in nodes:
                proposed_bindings.setdefault(candidate_id, set()).add(row.subject_object_id)
    bindings = {key: next(iter(values)) for key, values in proposed_bindings.items() if len(values) == 1}
    hypotheses = list(_hypotheses(request, bindings))
    found = []
    for entry in publications:
        receipt = entry.publication
        state = entry.review
        parent = bundle.world_graph.get_revision(request.world_id, receipt.expected_parent_revision_id)
        context = writes.mutation_context_from_revision_payload(
            parent, world_id=request.world_id, head_revision_id=receipt.expected_parent_revision_id,
        )
        endpoint_kinds = writes._candidate_endpoint_kinds(context, state.candidate_contribution)
        actual_candidates = {row.assertion_id: row for row in state.candidate_contribution.assertions}
        matches = {}
        for candidate_id, candidate_kind, facet, raw in hypotheses:
            verdict = raw.acceptance_state
            if raw.assertion_id not in actual_candidates and not (
                raw.predicate == "governs" and any(
                    _value(row).get("extract_edge_id") == candidate_id
                    for row in actual_candidates.values()
                )
            ):
                continue
            effect = _qualify_worldbuilding_native_edges(
                preview=request.preview,
                effect={"accepted_proposals": [raw.model_dump(mode="json")]
                        if verdict == "accepted" else [], "node_id_map": bindings},
                native_vocabulary_binding=_worldbuilding_native_vocabulary_binding(),
            )
            if verdict == "accepted":
                raw = type(raw).model_validate(effect["accepted_proposals"][0])
            contribution = create_graph_contribution(
                world_id=request.world_id, source_kind="source_extraction",
                source_artifact_id=pair[0], source_revision_id=pair[1], campaign_scope=None,
                extraction_profile=None, authored_by="publication_discovery_hypothesis",
                accepted_assertions=[raw] if verdict == "accepted" else [],
                rejected_assertions=[raw] if verdict == "rejected" else [],
                candidate_assertions=[], unresolved_mentions=[],
                produced_at="1970-01-01T00:00:00Z", diagnostics=[],
            )
            contribution = _worldbuilding_expressible(contribution)
            evidence = writes._recap_extraction_evidence_view(
                contribution, pair_to_dm=pair_to_dm, sources=bundle.sources,
            )
            expected = map_worldbuilding_extraction_contribution_v3(
                evidence, contribution, pair_to_dm,
            ).assertions[0]
            updates = {"acceptance_state": AcceptanceState.CANDIDATE}
            if verdict == "accepted":
                updates.update(temporal_scope=writes._normalized_temporal_scope(expected.temporal_scope))
                updates.update(writes._qualified_assertion_update(expected, endpoint_kinds=endpoint_kinds))
            expected = expected.model_copy(update=updates)
            actual = actual_candidates.get(expected.assertion_id)
            actual_verdict = next((str(row.acceptance_state)
                                   for row in state.record.assertion_verdicts
                                   if row.assertion_id == expected.assertion_id), None)
            if actual is None or actual_verdict != verdict:
                continue
            if expected.model_dump(mode="json") != actual.model_dump(mode="json"):
                continue
            matches.setdefault(expected.assertion_id, []).append(WorldbuildingPublishedFacet(
                candidate_id, candidate_kind, facet, expected.assertion_id,
                actual.subject_object_id, verdict,
            ))
        facets = []
        unmapped = []
        for row in state.reviewed_contribution.assertions:
            if row.acceptance_state not in (AcceptanceState.ACCEPTED, AcceptanceState.REJECTED):
                unmapped.append(row.assertion_id)
                continue
            options = matches.get(row.assertion_id, [])
            if len(options) != 1:
                unmapped.append(row.assertion_id)
            else:
                facets.append(options[0])
        found.append(WorldbuildingHistoricalPublication(
            native_operation_id=receipt.operation_id, review_id=receipt.review_id,
            parent_revision_id=receipt.expected_parent_revision_id,
            published_revision_id=receipt.published_revision_id,
            reviewed_contribution_id=receipt.reviewed_contribution_id,
            reviewed_contribution_sha256=receipt.reviewed_contribution_sha256,
            facets=tuple(facets), unmapped_assertion_ids=tuple(sorted(unmapped)),
        ))
    # A matching ID hint is not a proven identity binding. Only fully matched
    # existence/description/observation hypotheses can ground aliases or edges.
    proven = {}
    for publication in found:
        for fact in publication.facets:
            if fact.facet not in ("existence", "description", "observation") or fact.verdict != "accepted":
                continue
            owner = (observations[fact.candidate_id].subject_candidate_node_id
                     if fact.candidate_kind == "source_observation" else fact.candidate_id)
            proven.setdefault(owner, set()).add(fact.subject_node_id)
    proven = {key: next(iter(values)) for key, values in proven.items() if len(values) == 1}
    edges = {edge.edge_id: edge for edge in request.preview.edges}
    filtered = []
    for publication in found:
        kept = []
        unmapped = set(publication.unmapped_assertion_ids)
        for fact in publication.facets:
            edge = edges.get(fact.candidate_id) if fact.facet == "relationship" else None
            if (
                (fact.facet == "alias" and proven.get(fact.candidate_id) != fact.subject_node_id)
                or (edge is not None and any(
                    endpoint not in proven or proven.get(endpoint) != bindings.get(endpoint)
                    for endpoint in (edge.from_node_id, edge.to_node_id)
                ))
            ):
                unmapped.add(fact.assertion_id)
                continue
            kept.append(fact)
            if fact.facet == "existence" and (nodes[fact.candidate_id].description or "").strip():
                kept.append(replace(fact, facet="description"))
        filtered.append(replace(publication, facets=tuple(kept),
                                unmapped_assertion_ids=tuple(sorted(unmapped))))
    return WorldbuildingPublicationHistory(
        request.world_id, request.revision_id, request.run_id, pair[0], pair[1],
        tuple(filtered), history.scanned_revision_count,
    )
