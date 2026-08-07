import { describe, expect, it } from "vitest";

import { glanceOnlyForGraphReference } from "./openGraphReferencePolicy";
import type { GraphReferenceResolution } from "./types";
import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";

describe("glanceOnlyForGraphReference", () => {
  it("opens Threats as full (glanceOnly false)", () => {
    const resolution = {
      kind: "resolved_graph",
      locator: "dmb-node:threat:x",
      reference: null,
      graphNodeId: "threat:x",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "threat:x",
        label: "X",
        kind: "threat",
        role: "creature",
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
    } satisfies Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;

    expect(glanceOnlyForGraphReference(resolution)).toBe(false);
  });

  it("keeps non-Threats glance-first", () => {
    const resolution = {
      kind: "resolved_graph",
      locator: "dmb-node:location-inn",
      reference: null,
      graphNodeId: "location-inn",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "location-inn",
        label: "Inn",
        kind: "location",
        role: "location",
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
    } satisfies Extract<GraphReferenceResolution, { kind: "resolved_graph" }>;

    expect(glanceOnlyForGraphReference(resolution)).toBe(true);
  });
});
