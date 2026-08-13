import { describe, expect, it } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import {
  glanceOnlyForGraphReference,
  opensFullPlaySheet,
} from "./openGraphReferencePolicy";
import type { GraphReferenceResolution } from "./types";

function resolved(
  nodeId: string,
  kind: string,
  role: string,
): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: `dmb-node:${nodeId}`,
    reference: null,
    graphNodeId: nodeId,
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: nodeId,
      label: nodeId,
      kind,
      role,
      aliases: [],
      source_domains: [],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: null,
    }),
    graphScope: null,
    projectionState: "ready",
    message: null,
  };
}

describe("glanceOnlyForGraphReference", () => {
  it("opens Threats as full (glanceOnly false)", () => {
    const resolution = resolved("threat:x", "threat", "creature");
    expect(opensFullPlaySheet(resolution)).toBe(true);
    expect(glanceOnlyForGraphReference(resolution)).toBe(false);
  });

  it("opens Of Conks Morwin as full play sheet", () => {
    const resolution = resolved("npc:morwin-blackwell", "npc", "npc");
    expect(opensFullPlaySheet(resolution)).toBe(true);
    expect(glanceOnlyForGraphReference(resolution)).toBe(false);
  });

  it("keeps non-bridged non-Threats glance-first", () => {
    const resolution = resolved("location-inn", "location", "location");
    expect(opensFullPlaySheet(resolution)).toBe(false);
    expect(glanceOnlyForGraphReference(resolution)).toBe(true);
  });
});
