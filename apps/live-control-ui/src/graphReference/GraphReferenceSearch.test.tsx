import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { GraphReferenceSearch } from "./GraphReferenceSearch";
import { referenceFromGraphNode } from "./referenceFromGraphNode";
import type { GraphReferenceSearchItem } from "./types";

function searchItem(
  node: GraphProjectionNodeView,
  scopeLabel: string,
): GraphReferenceSearchItem {
  return {
    nodeId: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    summary: node.summary ?? null,
    aliases: node.aliases ?? [],
    scopeLabel,
    reference: referenceFromGraphNode(node),
    nodeView: node,
  };
}

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
    campaign_scope: "longmont-c1",
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
    campaign_scope: null,
  },
];

const items = [
  searchItem(nodes[0], "Longmont C1"),
  searchItem(nodes[1], "world"),
];

describe("GraphReferenceSearch", () => {
  it("searches projection nodes and inserts a chip from a match", async () => {
    const user = userEvent.setup();
    const onInsert = vi.fn();

    render(
      <GraphReferenceSearch
        items={items}
        projectionState="ready"
        onInsert={onInsert}
      />,
    );

    await user.type(screen.getByLabelText("Find objects"), "glow");
    const results = screen.getByTestId("graph-reference-search-results");
    expect(within(results).getByText("Glowkindle")).toBeInTheDocument();
    expect(within(results).queryByText("Inn")).not.toBeInTheDocument();

    await user.click(within(results).getByRole("button", { name: "Insert chip" }));
    expect(onInsert).toHaveBeenCalledWith({
      kind: "ref",
      refType: "graph-node",
      refId: "npc-glowkindle",
      label: "Glowkindle",
    });
  });

  it("shows scope provenance on search results", async () => {
    const user = userEvent.setup();

    render(
      <GraphReferenceSearch
        items={items}
        projectionState="ready"
        onInsert={() => undefined}
      />,
    );

    await user.type(screen.getByLabelText("Find objects"), "glow");
    const results = screen.getByTestId("graph-reference-search-results");
    expect(within(results).getByText(/Longmont C1/i)).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Find objects"));
    await user.type(screen.getByLabelText("Find objects"), "inn");
    const innResults = screen.getByTestId("graph-reference-search-results");
    expect(within(innResults).getByText(/world/i)).toBeInTheDocument();
  });

  it("keeps search and view available while insert is locked", async () => {
    const user = userEvent.setup();
    const onInsert = vi.fn();
    const onView = vi.fn();

    render(
      <GraphReferenceSearch
        items={items}
        projectionState="ready"
        insertDisabled
        onInsert={onInsert}
        onView={onView}
      />,
    );

    expect(screen.getByText(/Unlock editing to insert chips/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText("Find objects"), "inn");
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(onView).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "location-inn" }));
    expect(screen.getByRole("button", { name: "Insert chip" })).toBeDisabled();
    expect(onInsert).not.toHaveBeenCalled();
  });

  it("omits Insert controls in view-only mode when onInsert is absent", async () => {
    const user = userEvent.setup();
    const onView = vi.fn();

    render(
      <GraphReferenceSearch
        items={items}
        projectionState="ready"
        insertDisabled
        onView={onView}
      />,
    );

    expect(screen.queryByText(/Unlock editing to insert chips/i)).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Find objects"), "inn");
    expect(screen.queryByRole("button", { name: "Insert chip" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(onView).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "location-inn" }));
  });
});
