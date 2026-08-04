import { describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { referenceFromGraphNode } from "../../graphReference";
import type { GraphReferenceResolution } from "../../graphReference/types";
import type { GraphProjectionNodeView } from "../../api/types";
import { fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import {
  buildPlanGraphObjectActions,
  hasPlanSourceOrEvidence,
} from "./buildPlanGraphObjectActions";

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 21 });

function makeNode(overrides: Partial<GraphProjectionNodeView> = {}): GraphProjectionNodeView {
  return {
    node_id: "npc-glowkindle",
    label: "Glowkindle",
    kind: "npc",
    role: "merchant",
    aliases: [],
    source_domains: ["recap"],
    evidence_badges: [
      {
        evidence_ref_id: "ev-1",
        label: "Session recap mention",
        source_domain: "recap",
        source_artifact_id: "artifact-1",
        evidence_role: "source_evidence",
        is_focus_session_evidence: true,
        can_open_source: true,
        can_highlight_span: false,
      },
    ],
    adjacency: [],
    anchored_to_focus_session: true,
    summary: "A friendly merchant.",
    source_anchor_text: "Glowkindle waved from the inn.",
    ...overrides,
  };
}

function resolvedGraphFromNode(
  node: GraphProjectionNodeView,
  overrides: Partial<Extract<GraphReferenceResolution, { kind: "resolved_graph" }>> = {},
): GraphReferenceResolution {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${node.node_id}`,
    reference: referenceFromGraphNode(node),
    graphObject: buildGraphObjectCardFromNodeView(node),
    graphNodeId: node.node_id,
    graphScope: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev-1",
    },
    projectionState: null,
    ...overrides,
  };
}

describe("buildPlanGraphObjectActions", () => {
  it("orders source, grounded tools, then /ingest for graph hits", () => {
    const onOpenStatblock = vi.fn();
    const resolution = resolvedGraphFromNode(
      makeNode({
        node_id: "statblock-tripod",
        label: "Tripod Null-Calf",
        kind: "statblock",
        role: "creature",
      }),
    );

    const actions = buildPlanGraphObjectActions({
      resolution,
      sessionDescriptor,
      onOpenStatblock,
    });

    expect(actions.map((action) => action.id)).toEqual([
      "open-source",
      "open-statblock",
      "open-ingest",
    ]);
    expect(actions[2]).toMatchObject({
      label: "Review memory in /ingest",
      href: "/ingest?campaign=longmont-c2&session=session-21",
    });
  });

  it("includes Inspect source/evidence only when evidence or source data exists", () => {
    const withEvidence = resolvedGraphFromNode(makeNode());
    const withoutEvidence = resolvedGraphFromNode(
      makeNode({
        node_id: "npc-empty",
        label: "Empty",
        source_domains: [],
        evidence_badges: [],
        source_anchor_text: null,
        summary: null,
      }),
    );

    expect(
      buildPlanGraphObjectActions({ resolution: withEvidence, sessionDescriptor }).some(
        (action) => action.id === "open-source",
      ),
    ).toBe(true);
    expect(
      buildPlanGraphObjectActions({ resolution: withoutEvidence, sessionDescriptor }).some(
        (action) => action.id === "open-source",
      ),
    ).toBe(false);
  });

  it("adds Open statblock tool when grounded and open behavior is provided", () => {
    const onOpenStatblock = vi.fn();
    const relatedStatblock = resolvedGraphFromNode(
      makeNode({
        node_id: "npc-lysandra",
        label: "Lysandra",
        adjacency: [
          {
            edge_id: "edge-sb",
            node_id: "statblock-lysandra",
            label: "Lysandra statblock",
            kind: "statblock",
            predicate: "has_statblock",
            direction: "outgoing",
            related_summary: null,
            evidence_ref_ids: [],
            source_domains: [],
            anchored_to_focus_session: true,
            session_ids: [],
          },
        ],
      }),
    );
    const noStatblock = resolvedGraphFromNode(makeNode());

    const withAction = buildPlanGraphObjectActions({
      resolution: relatedStatblock,
      sessionDescriptor,
      onOpenStatblock,
    });
    expect(withAction.find((action) => action.id === "open-statblock")).toMatchObject({
      label: "Open statblock tool",
    });
    withAction.find((action) => action.id === "open-statblock")?.onClick?.();
    expect(onOpenStatblock).toHaveBeenCalledOnce();

    expect(
      buildPlanGraphObjectActions({
        resolution: noStatblock,
        sessionDescriptor,
        onOpenStatblock,
      }).some((action) => action.id === "open-statblock"),
    ).toBe(false);

    expect(
      buildPlanGraphObjectActions({
        resolution: relatedStatblock,
        sessionDescriptor,
      }).some((action) => action.id === "open-statblock"),
    ).toBe(false);
  });

  it("adds Open roll table tool when grounded and open behavior is provided", () => {
    const onOpenRollTable = vi.fn();
    const rollTable = resolvedGraphFromNode(
      makeNode({
        node_id: "roll-table-gate",
        label: "Gate Dilemma d12",
        kind: "roll-table",
        role: "table",
      }),
    );
    const noRollTable = resolvedGraphFromNode(makeNode());

    const withAction = buildPlanGraphObjectActions({
      resolution: rollTable,
      sessionDescriptor,
      onOpenRollTable,
    });
    expect(withAction.find((action) => action.id === "open-roll-table")).toMatchObject({
      label: "Open roll table tool",
    });
    withAction.find((action) => action.id === "open-roll-table")?.onClick?.();
    expect(onOpenRollTable).toHaveBeenCalledOnce();

    expect(
      buildPlanGraphObjectActions({
        resolution: noRollTable,
        sessionDescriptor,
        onOpenRollTable,
      }).some((action) => action.id === "open-roll-table"),
    ).toBe(false);

    expect(
      buildPlanGraphObjectActions({
        resolution: rollTable,
        sessionDescriptor,
      }).some((action) => action.id === "open-roll-table"),
    ).toBe(false);
  });

  it("keeps corpus fallback actions from implying authoritative graph memory", () => {
    const resolution: GraphReferenceResolution = {
      kind: "resolved_corpus_fallback",
      locator: "#dmb-ref:location:north-reach-gate",
      reference: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      fallback: {
        status: "resolved",
        ref: {
          kind: "ref",
          refType: "location",
          refId: "north-reach-gate",
          label: "North Reach Gate",
        },
        source: "location-index",
        sourcePath: "corpus/locations/north_reach_gate.md",
        message: "Resolved from live location index.",
      },
      projectionState: null,
    };

    const actions = buildPlanGraphObjectActions({ resolution, sessionDescriptor });
    expect(actions.map((action) => action.id)).toEqual(["open-source", "open-ingest"]);
    expect(actions.find((action) => action.id === "open-ingest")?.helpText).toMatch(/Corpus fallback/i);
  });

  it("uses Fix memory copy for unresolved resolutions", () => {
    const resolution: GraphReferenceResolution = {
      kind: "unresolved",
      locator: "#dmb-ref:npc:lysandra",
      reference: {
        kind: "ref",
        refType: "npc",
        refId: "lysandra",
        label: "Lysandra",
      },
      matchingGraphNodeIds: ["npc-a", "npc-b"],
      message: "Could not uniquely resolve this object from graph memory.",
      projectionState: null,
    };

    const actions = buildPlanGraphObjectActions({ resolution, sessionDescriptor });
    expect(actions).toEqual([
      expect.objectContaining({
        id: "open-ingest",
        label: "Fix memory in /ingest",
        href: "/ingest?campaign=longmont-c2&session=session-21",
      }),
    ]);
  });

  it("detects source/evidence presence for Plan cards", () => {
    expect(hasPlanSourceOrEvidence(buildGraphObjectCardFromNodeView(makeNode()))).toBe(true);
    expect(
      hasPlanSourceOrEvidence(
        buildGraphObjectCardFromNodeView(
          makeNode({
            source_domains: [],
            evidence_badges: [],
            source_anchor_text: null,
          }),
        ),
      ),
    ).toBe(false);
  });

  it("suppresses generic Open statblock tool for exact resolved Threats", () => {
    const onOpenStatblock = vi.fn();
    const resolution = resolvedGraphFromNode(
      makeNode({
        node_id: "threat:tripod-null-calf",
        label: "Tripod Null-Calf",
        kind: "threat",
        role: "creature",
      }),
    );

    const actions = buildPlanGraphObjectActions({
      resolution,
      sessionDescriptor,
      onOpenStatblock,
    });

    expect(actions.some((action) => action.id === "open-statblock")).toBe(false);
    expect(actions.some((action) => action.id === "open-ingest")).toBe(true);
  });
});
