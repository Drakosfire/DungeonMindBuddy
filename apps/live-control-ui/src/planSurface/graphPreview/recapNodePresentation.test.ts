import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";
import {
  adjacencyThreadLabel,
  buildRecapNodePresentation,
  defaultPinnedNodeId,
  evidencePlanningText,
  roleClass,
} from "./recapNodePresentation";

describe("recapNodePresentation", () => {
  it("derives role class slugs", () => {
    expect(roleClass("PC")).toBe("pc");
    expect(roleClass("location")).toBe("location");
  });

  it("builds GM planning scan fields from node view evidence", () => {
    const node = session23UnionSupergraphFixture.node_views.pc_caelynn as GraphProjectionNodeView;
    const presentation = buildRecapNodePresentation(node);

    expect(presentation.summary).toContain("Read-model example global PC node");
    expect(presentation.whyNow).toBe("Held the Mireward gate during the incident");
    expect(presentation.knownBefore).toBe("Tied to Mirathorn politics in character notes");
    expect(presentation.planningChips.some((chip) => chip.label === "pc")).toBe(true);
    expect(presentation.planningChips.some((chip) => chip.label === "S23")).toBe(true);
    expect(presentation.threadHints[0]?.edgeLabel).toBe("participated in Mireward Gate Incident");
  });

  it("formats evidence and adjacency labels for planning display", () => {
    const node = session23UnionSupergraphFixture.node_views.pc_caelynn as GraphProjectionNodeView;
    const focusBadge = node.evidence_badges[0];
    const adjacency = node.adjacency[1];

    expect(evidencePlanningText(focusBadge)).toBe("Held the Mireward gate during the incident");
    expect(adjacencyThreadLabel(adjacency)).toBe("connected to Mirathorn");
  });

  it("defaults pinned node to focused node or first mention", () => {
    expect(defaultPinnedNodeId(session23UnionSupergraphFixture)).toBe("pc_caelynn");
  });
});
