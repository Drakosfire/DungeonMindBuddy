"""Map candidate bundle sources to Kernel GraphContributions (PR006)."""

from __future__ import annotations

from typing import Any

import graph_memory.kernel as kernel
from graph_memory.materialization.acceptance_manifest import sha256_bytes

WORLD_ID = "eldyrwild"
CAMPAIGN_SCOPE = "longmont-c2"
EXTRACTION_PROFILE = "pr006-acceptance-v1"

KERNEL_DOMAIN_MAP: dict[str, str] = {
    "recap": "recap",
    "pc_hub": "worldbuilding",
    "worldbuilding": "worldbuilding",
    "campaign_hub": "npc_note",
    "mechanical": "statblock",
    "authored": "manual_seed",
}

# Stable stub metadata for cross-source edge endpoints.
STUB_NODES: dict[str, dict[str, Any]] = {
    "pc_baergrom": {"label": "Baergrom", "kind": "pc", "role": "pc"},
    "pc_bonogo": {"label": "Bonogo", "kind": "pc", "role": "pc"},
    "pc_caelynn": {"label": "Caelynn", "kind": "pc", "role": "pc"},
    "pc_ephanna": {"label": "Ephanna", "kind": "pc", "role": "pc"},
    "pc_karsemine": {"label": "Karsemine", "kind": "pc", "role": "pc"},
    "pc_stafl": {"label": "Stafl", "kind": "pc", "role": "pc"},
    "loc_mirathorn": {"label": "Mirathorn", "kind": "location", "role": "location"},
    "loc_mireward": {"label": "Mireward", "kind": "location", "role": "location"},
    "npc_lysandra_ironveil": {
        "label": "Captain Lysandra Ironveil",
        "kind": "npc",
        "role": "npc",
    },
    "creature_tripod_null_calf": {
        "label": "Tripod Null Calf",
        "kind": "creature",
        "role": "creature",
    },
    "creature_latch_harrow": {
        "label": "Latch Harrow",
        "kind": "creature",
        "role": "creature",
    },
    "event_journey_mireward_reach": {
        "label": "Journey to Mireward Reach",
        "kind": "event",
        "role": "event",
    },
    **{
        f"event_session_{n}": {
            "label": f"Session {n} Event",
            "kind": "event",
            "role": "event",
        }
        for n in range(1, 24)
    },
}


def map_inventory_domain_to_kernel(domain: str, *, source_uri: str = "") -> str:
    if domain == "campaign_hub" and "Journey" in source_uri:
        return "worldbuilding"
    return KERNEL_DOMAIN_MAP.get(domain, "manual_seed")


def _node_value(
    node: dict[str, Any],
    *,
    kernel_domain: str,
    source_artifact_id: str,
    source_uri: str,
    campaign_scope: str,
    evidence_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    evidence_payload = [
        {
            "evidence_ref_id": ref.get("evidence_ref_id", ""),
            "source_domain": kernel_domain,
            "locator": ref.get("locator"),
            "session_id": ref.get("session_id"),
        }
        for ref in evidence_refs
    ]
    return {
        "kind": node.get("kind", "unknown"),
        "role": node.get("role", node.get("kind", "unknown")),
        "aliases": list(node.get("aliases") or [node.get("label", node["node_id"])]),
        "source_domains": [kernel_domain],
        "canon_state": "not_canon_promotion",
        "summary": node.get("summary"),
        "evidence": evidence_payload,
        "source_artifacts": [
            {
                "source_artifact_id": source_artifact_id,
                "source_domain": kernel_domain,
                "campaign_id": campaign_scope,
                "uri": source_uri,
            }
        ],
    }


def _build_node_assertion(
    node: dict[str, Any],
    *,
    kernel_domain: str,
    source_artifact_id: str,
    source_revision_id: str,
    source_uri: str,
    campaign_scope: str,
    evidence_refs: list[dict[str, Any]],
) -> kernel.GraphContributionAssertion:
    node_id = node["node_id"]
    return kernel.build_assertion(
        assertion_kind="node",
        acceptance_state="accepted",
        subject_node_id=node_id,
        label=node.get("label", node_id),
        value=_node_value(
            node,
            kernel_domain=kernel_domain,
            source_artifact_id=source_artifact_id,
            source_uri=source_uri,
            campaign_scope=campaign_scope,
            evidence_refs=evidence_refs,
        ),
        evidence_ref_ids=[ref.get("evidence_ref_id", "") for ref in evidence_refs if ref.get("evidence_ref_id")],
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        campaign_scope=campaign_scope,
        epistemic_kind="fact",
        visibility="gm",
        identity_resolution_outcome="created_new",
    )


def _stub_node_assertion(
    node_id: str,
    *,
    kernel_domain: str,
    source_artifact_id: str,
    source_revision_id: str,
    source_uri: str,
    campaign_scope: str,
) -> kernel.GraphContributionAssertion:
    meta = STUB_NODES[node_id]
    node = {
        "node_id": node_id,
        "label": meta["label"],
        "kind": meta["kind"],
        "role": meta["role"],
        "aliases": [meta["label"]],
    }
    return _build_node_assertion(
        node,
        kernel_domain=kernel_domain,
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        source_uri=source_uri,
        campaign_scope=campaign_scope,
        evidence_refs=[],
    )


def source_entry_to_contribution(
    entry: dict[str, Any],
    *,
    campaign_scope: str = CAMPAIGN_SCOPE,
    known_node_ids: set[str] | None = None,
) -> kernel.GraphContribution:
    """Convert one accepted bundle source entry into a GraphContribution."""
    source_domain = entry["source_domain"]
    source_uri = entry["source_uri"]
    kernel_domain = map_inventory_domain_to_kernel(source_domain, source_uri=source_uri)
    source_artifact_id = entry["source_artifact_id"]
    source_revision_id = entry["source_revision_id"]
    candidate = entry.get("candidate_graph") or {}
    nodes = list(candidate.get("nodes") or [])
    edges = list(candidate.get("edges") or [])
    evidence_refs = list(candidate.get("evidence_refs") or [])
    unresolved = list(candidate.get("unresolved_mentions") or [])

    local_node_ids = {node["node_id"] for node in nodes}
    endpoint_ids: set[str] = set()
    for edge in edges:
        endpoint_ids.add(edge["source_node_id"])
        endpoint_ids.add(edge["target_node_id"])

    accepted_nodes: list[kernel.GraphContributionAssertion] = []
    seen: set[str] = set()
    for node in nodes:
        nid = node["node_id"]
        if nid in seen:
            continue
        seen.add(nid)
        accepted_nodes.append(
            _build_node_assertion(
                node,
                kernel_domain=kernel_domain,
                source_artifact_id=source_artifact_id,
                source_revision_id=source_revision_id,
                source_uri=source_uri,
                campaign_scope=campaign_scope,
                evidence_refs=evidence_refs,
            )
        )

    for node_id in sorted(endpoint_ids):
        if node_id in seen:
            continue
        if known_node_ids and node_id in known_node_ids:
            continue
        if node_id not in STUB_NODES:
            continue
        seen.add(node_id)
        accepted_nodes.append(
            _stub_node_assertion(
                node_id,
                kernel_domain=kernel_domain,
                source_artifact_id=source_artifact_id,
                source_revision_id=source_revision_id,
                source_uri=source_uri,
                campaign_scope=campaign_scope,
            )
        )

    accepted_edges: list[kernel.GraphContributionAssertion] = []
    session_ids: list[str] = []
    for ref in evidence_refs:
        sid = ref.get("session_id")
        if sid:
            session_ids.append(sid)

    for edge in edges:
        edge_value: dict[str, Any] = {
            "source_domains": [kernel_domain],
            "canon_state": "not_canon_promotion",
            "source_artifacts": [
                {
                    "source_artifact_id": source_artifact_id,
                    "source_domain": kernel_domain,
                    "campaign_id": campaign_scope,
                    "uri": source_uri,
                }
            ],
        }
        if session_ids:
            edge_value["session_ids"] = list(dict.fromkeys(session_ids))
        accepted_edges.append(
            kernel.build_assertion(
                assertion_kind="edge",
                acceptance_state="accepted",
                subject_node_id=edge["source_node_id"],
                target_node_id=edge["target_node_id"],
                predicate=edge["predicate"],
                label=edge.get("label", edge["predicate"]),
                value=edge_value,
                evidence_ref_ids=[
                    ref.get("evidence_ref_id", "")
                    for ref in evidence_refs
                    if ref.get("evidence_ref_id")
                ],
                source_artifact_id=source_artifact_id,
                source_revision_id=source_revision_id,
                campaign_scope=campaign_scope,
                epistemic_kind="fact",
                visibility="gm",
                identity_resolution_outcome="created_new",
            )
        )

    rejected: list[kernel.GraphContributionAssertion] = []
    identity_mentions: list[kernel.ContributionIdentityMention] = []
    for mention in unresolved:
        mention_id = f"mention:{sha256_bytes(mention.get('mention_text', '').encode()).replace('sha256:', '')[:12]}"
        identity_mentions.append(
            kernel.ContributionIdentityMention(
                mention_id=mention_id,
                label=mention.get("mention_text", ""),
                object_kind="unknown",
                candidate_node_ids=list(mention.get("candidate_node_ids") or []),
                identity_resolution_outcome="ambiguous",
                diagnostics=[mention.get("reason", "ambiguous_mention")],
            )
        )
        rejected.append(
            kernel.build_assertion(
                assertion_kind="node",
                acceptance_state="rejected",
                subject_node_id=None,
                label=mention.get("mention_text", "ambiguous"),
                value={"reason": mention.get("reason", "ambiguous_mention")},
                source_artifact_id=source_artifact_id,
                source_revision_id=source_revision_id,
                campaign_scope=campaign_scope,
                identity_resolution_outcome="ambiguous",
            )
        )

    return kernel.create_graph_contribution(
        world_id=WORLD_ID,
        source_kind="source_extraction",
        source_artifact_id=source_artifact_id,
        source_revision_id=source_revision_id,
        extraction_profile=EXTRACTION_PROFILE,
        campaign_scope=campaign_scope,
        accepted_assertions=[*accepted_nodes, *accepted_edges],
        rejected_assertions=rejected,
        unresolved_mentions=identity_mentions,
    )


def _contribution_sort_key(entry: dict[str, Any]) -> tuple[int, str]:
    """Order: PCs → world hubs → npc/creature → recaps (nodes before edges-heavy)."""
    domain = entry.get("source_domain", "")
    uri = entry.get("source_uri", "")
    order = {
        "pc_hub": 0,
        "worldbuilding": 1,
        "mechanical": 2,
        "campaign_hub": 3,
        "recap": 4,
        "authored": 5,
    }.get(domain, 9)
    return (order, uri)


def bundle_sources_to_contributions(
    bundle: dict[str, Any],
    *,
    campaign_scope: str | None = None,
) -> list[kernel.GraphContribution]:
    """Convert all accepted bundle sources to contributions with cross-source node stubs."""
    scope = campaign_scope or bundle.get("campaign_scope") or CAMPAIGN_SCOPE
    sources = [s for s in bundle.get("sources", []) if s.get("status") == "accepted"]

    all_node_ids: set[str] = set()
    for entry in sources:
        cg = entry.get("candidate_graph") or {}
        for node in cg.get("nodes") or []:
            all_node_ids.add(node["node_id"])

    ordered = sorted(sources, key=_contribution_sort_key)
    return [
        source_entry_to_contribution(
            entry,
            campaign_scope=scope,
            known_node_ids=all_node_ids,
        )
        for entry in ordered
    ]
