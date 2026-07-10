import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { PlanGraphRefSearch } from "./PlanGraphRefSearch";

const nodes: GraphProjectionNodeView[] = [
  {
    node_id: "npc-glowkindle",
    label: "Glowkindle",
    kind: "npc",
    role: "merchant",
    aliases: ["Glow"],
    source_domains: ["recap"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    summary: "A friendly merchant.",
  },
  {
    node_id: "location-inn",
    label: "Inn",
    kind: "location",
    role: "location",
    aliases: ["The Inn"],
    source_domains: ["recap"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: true,
    summary: "Meeting place.",
  },
];

describe("PlanGraphRefSearch", () => {
  it("searches projection nodes and inserts a chip from a match", async () => {
    const user = userEvent.setup();
    const onInsert = vi.fn();

    render(
      <PlanGraphRefSearch
        nodes={nodes}
        projectionState="ready"
        onInsert={onInsert}
      />,
    );

    await user.type(screen.getByLabelText("Search"), "glow");
    const results = screen.getByTestId("plan-graph-ref-search-results");
    expect(within(results).getByText("Glowkindle")).toBeInTheDocument();
    expect(within(results).queryByText("Inn")).not.toBeInTheDocument();

    await user.click(within(results).getByRole("button", { name: "Insert chip" }));
    expect(onInsert).toHaveBeenCalledWith({
      kind: "ref",
      refType: "npc",
      refId: "npc-glowkindle",
      label: "Glowkindle",
    });
  });
});
