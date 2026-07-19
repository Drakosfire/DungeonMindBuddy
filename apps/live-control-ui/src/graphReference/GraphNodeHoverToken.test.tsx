import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GraphNodeHoverToken } from "./GraphNodeHoverToken";
import type { GraphNodeGlancePresentation } from "./types";

const presentation: GraphNodeGlancePresentation = {
  nodeId: "node:bubbles",
  label: "Bubbles the Float Goat",
  kind: "creature",
  role: "creature",
  summary: "A float goat rescued from the flooded river.",
  whyNow: null,
  knownBefore: null,
  planningChips: [{ label: "creature", tone: "neutral" }],
  threadHints: [],
};

describe("GraphNodeHoverToken", () => {
  it("renders a CSS hover glance with summary", () => {
    render(
      <GraphNodeHoverToken
        presentation={presentation}
        label={presentation.label}
        pinned={false}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /Bubbles the Float Goat/i })).toBeInTheDocument();
    const glance = document.querySelector(".recap-node-hover-card");
    expect(glance).toBeInTheDocument();
    expect(glance).toHaveTextContent("A float goat rescued from the flooded river.");
    expect(glance).toHaveAttribute("role", "tooltip");
  });
});
