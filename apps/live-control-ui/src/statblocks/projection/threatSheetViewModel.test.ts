import { describe, expect, it } from "vitest";

import type {
  ThreatBindingHydrationV1,
  ThreatStatblockBindingV1,
  ThreatQueryHydrationHitV1,
  ThreatQueryHydrationResponseV1,
  WorldGraphProjectionNodeView,
} from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import type { GraphReferenceResolution } from "../../graphReference/types";
import revisionFixture from "../../../../../tests/fixtures/statblocks/v1/exact-revision-response.json";
import type { StatblockRevisionResourceV1 } from "../../contracts/dungeonbuddy-statblocks-v1/client";
import {
  buildThreatQueryHydrationRequest,
  buildThreatSheetViewModel,
  selectExactThreatHit,
  sortThreatSheetBindings,
  type ThreatSheetBindingViewModel,
} from "./threatSheetViewModel";

const revision = revisionFixture as StatblockRevisionResourceV1;

const scope = {
  worldId: "eldyrwild",
  campaignId: "longmont-c2",
  revisionId: "rev-1",
};

const threatNode: WorldGraphProjectionNodeView = {
  nodeId: "threat:tripod-null-calf",
  label: "Tripod Null-Calf",
  kind: "threat",
  role: "creature",
  aliases: ["Tripod Null-Calf"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
  summary: "A three-legged aberration.",
};

function makeHit(
  nodeId: string,
  label: string,
  bindings: ThreatBindingHydrationV1[] = [],
): ThreatQueryHydrationHitV1 {
  return {
    threat: { ...threatNode, nodeId, label },
    matchReasons: ["exact_node_id"],
    relationships: [],
    bindings,
    mechanicsDisposition: bindings.length ? "hydrated" : "no_binding",
  };
}

function makeResponse(
  hits: ThreatQueryHydrationHitV1[],
  revisionId = scope.revisionId,
): ThreatQueryHydrationResponseV1 {
  return {
    schema: "dmb_threat_query_hydration_response_v1",
    worldId: scope.worldId,
    campaignId: scope.campaignId,
    revisionId,
    queryText: "threat:tripod-null-calf",
    resultLabel: "threat_query_hydration_ok",
    hits,
    diagnostics: [],
    message: null,
  };
}

function resolvedThreat(
  overrides: Partial<Extract<GraphReferenceResolution, { kind: "resolved_graph" }>> = {},
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: "dmb-node:threat:tripod-null-calf",
    reference: null,
    graphNodeId: "threat:tripod-null-calf",
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: "threat:tripod-null-calf",
      label: "Tripod Null-Calf",
      kind: "threat",
      role: "creature",
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: "A three-legged aberration.",
    }),
    graphScope: scope,
    projectionState: "ready",
    message: "Resolved graph node Tripod Null-Calf.",
    ...overrides,
  };
}

function binding(overrides: Partial<ThreatBindingHydrationV1>): ThreatBindingHydrationV1 {
  return {
    relationshipEdgeId: "edge-1",
    bindingId: "bind-1",
    bindingRole: "primary",
    threatNodeId: "threat:tripod-null-calf",
    resourceNodeId: "sb_000001",
    provider: "dungeonmind",
    statblockId: "sb_000001",
    revisionId: "rev_000002",
    definitionDigest: revision.definition_digest,
    hydrationStatus: "available",
    binding: null,
    revision,
    message: null,
    ...overrides,
  };
}

describe("threatSheetViewModel", () => {
  it("builds exact SBW10a request from scope and selected Threat node ID", () => {
    expect(buildThreatQueryHydrationRequest(scope, "threat:tripod-null-calf")).toEqual({
      schema: "dmb_threat_query_hydration_request_v1",
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionPin: "rev-1",
      queryText: "threat:tripod-null-calf",
      focusNodeIds: ["threat:tripod-null-calf"],
      maxHits: 64,
      includeMechanics: true,
    });
  });

  it("selects the exact node ID even when another hit sorts earlier", () => {
    const response = makeResponse([
      makeHit("threat:other-beast", "Tripod Null-Calf"),
      makeHit("threat:tripod-null-calf", "Tripod Null-Calf"),
    ]);

    expect(selectExactThreatHit(response, scope, "threat:tripod-null-calf")).toEqual({
      status: "ready",
      hit: response.hits[1],
    });
  });

  it("rejects a label-equivalent substitute with a different node ID", () => {
    const response = makeResponse([makeHit("threat:other-beast", "Tripod Null-Calf")]);
    expect(selectExactThreatHit(response, scope, "threat:tripod-null-calf")).toEqual({
      status: "not_found",
      message: null,
    });
  });

  it("returns not_found for zero exact hits", () => {
    const response = makeResponse([]);
    expect(selectExactThreatHit(response, scope, "threat:tripod-null-calf")).toEqual({
      status: "not_found",
      message: null,
    });
  });

  it("returns integrity_failure for multiple exact hits", () => {
    const response = makeResponse([
      makeHit("threat:tripod-null-calf", "Tripod Null-Calf"),
      makeHit("threat:tripod-null-calf", "Tripod Null-Calf"),
    ]);
    expect(selectExactThreatHit(response, scope, "threat:tripod-null-calf")).toMatchObject({
      status: "integrity_failure",
    });
  });

  it("returns revision_mismatch when response revision differs from pin", () => {
    const response = makeResponse([makeHit("threat:tripod-null-calf", "Tripod Null-Calf")], "rev-other");
    expect(selectExactThreatHit(response, scope, "threat:tripod-null-calf")).toMatchObject({
      status: "revision_mismatch",
    });
  });

  it("rejects a response from a different graph campaign even when revision matches", () => {
    const response = makeResponse([makeHit("threat:tripod-null-calf", "Tripod Null-Calf")]);
    response.campaignId = "other-campaign";
    expect(selectExactThreatHit(response, scope, "threat:tripod-null-calf")).toMatchObject({
      status: "revision_mismatch",
    });
  });

  it("sorts bindings deterministically by role, phase, variant, and binding ID", () => {
    const bindings: ThreatSheetBindingViewModel[] = [
      {
        relationshipEdgeId: "edge-a",
        bindingId: "bind-a",
        role: "alpha",
        phaseKey: null,
        variantLabel: null,
        statblockId: "sb-a",
        revisionId: "rev-a",
        definitionDigest: null,
        hydrationStatus: "available",
        revision: null,
        message: null,
      },
      {
        relationshipEdgeId: "edge-b",
        bindingId: "bind-b",
        role: "beta",
        phaseKey: null,
        variantLabel: null,
        statblockId: "sb-b",
        revisionId: "rev-b",
        definitionDigest: null,
        hydrationStatus: "available",
        revision: null,
        message: null,
      },
    ];

    expect(sortThreatSheetBindings(bindings).map((entry) => entry.bindingId)).toEqual(["bind-a", "bind-b"]);
  });

  it("builds a view model with every binding and no first-winner compact mechanics", () => {
    const hit = makeHit("threat:tripod-null-calf", "Tripod Null-Calf", [
      binding({ bindingId: "bind-a", bindingRole: "alpha" }),
      binding({ bindingId: "bind-b", bindingRole: "beta", phaseKey: "enraged" }),
    ]);
    const model = buildThreatSheetViewModel({
      resolution: resolvedThreat(),
      hit,
      loadStatus: "ready",
    });

    expect(model.bindings).toHaveLength(2);
    expect(model.bindings.map((entry) => entry.bindingId)).toEqual(["bind-a", "bind-b"]);
  });

  it("reads phase and variant ordering metadata from the typed binding payload", () => {
    const typedBinding: ThreatStatblockBindingV1 = {
      schema: "dmb_threat_statblock_binding_v1",
      bindingId: "bind-phase",
      provider: "dungeonmind",
      statblockId: "sb_000001",
      revisionId: "rev_000002",
      contract: "dungeonmind.dungeonbuddy-statblocks",
      contractVersion: "1.0.0",
      definitionDigest: revision.definition_digest,
      role: "phase",
      phaseKey: "enraged",
      variantLabel: "elite",
    };
    const model = buildThreatSheetViewModel({
      resolution: resolvedThreat(),
      hit: makeHit("threat:tripod-null-calf", "Tripod Null-Calf", [
        binding({ bindingId: "bind-phase", bindingRole: null, binding: typedBinding }),
      ]),
      loadStatus: "ready",
    });

    expect(model.bindings[0]).toMatchObject({
      role: "phase",
      phaseKey: "enraged",
      variantLabel: "elite",
    });
  });
});
