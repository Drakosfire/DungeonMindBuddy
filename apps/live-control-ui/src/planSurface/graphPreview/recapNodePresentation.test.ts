import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";
import {
  buildRecapNodePresentation,
  defaultPinnedNodeId,
  roleClass,
} from "./recapNodePresentation";

describe("recapNodePresentation", () => {
  it("derives role class slugs", () => {
    expect(roleClass("PC")).toBe("pc");
    expect(roleClass("location")).toBe("location");
  });

  it("builds chips and description from node view evidence", () => {
    const node = session23UnionSupergraphFixture.node_views.pc_caelynn as GraphProjectionNodeView;
    const presentation = buildRecapNodePresentation(node);

    expect(presentation.description).toContain("recap");
    expect(presentation.chips.some((chip) => chip.label.includes("focus evidence"))).toBe(true);
    expect(presentation.chips.some((chip) => chip.label.includes("adjacent"))).toBe(true);
    expect(presentation.chips.some((chip) => chip.label === "focus session")).toBe(true);
  });

  it("defaults pinned node to focused node or first mention", () => {
    expect(defaultPinnedNodeId(session23UnionSupergraphFixture)).toBe("pc_caelynn");
  });
});
