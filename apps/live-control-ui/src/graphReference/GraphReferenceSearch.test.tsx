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
  searchItem(nodes[0], "longmont-c1"),
  searchItem(nodes[1], "World"),
];

const unionNodes: GraphProjectionNodeView[] = [
  {
    node_id: "npc-c1",
    label: "C1 NPC",
    kind: "npc",
    role: "ally",
    aliases: [],
    source_domains: ["recap"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: false,
    summary: null,
    campaign_scope: "longmont-c1",
  },
  {
    node_id: "npc-c2",
    label: "C2 NPC",
    kind: "npc",
    role: "ally",
    aliases: [],
    source_domains: ["recap"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: false,
    summary: null,
    campaign_scope: "longmont-c2",
  },
  {
    node_id: "npc-universal",
    label: "Universal NPC",
    kind: "npc",
    role: "ally",
    aliases: [],
    source_domains: ["recap"],
    evidence_badges: [],
    adjacency: [],
    anchored_to_focus_session: false,
    summary: null,
    campaign_scope: null,
  },
];

const unionItems = [
  searchItem(unionNodes[0], "longmont-c1"),
  searchItem(unionNodes[1], "longmont-c2"),
  searchItem(unionNodes[2], "World"),
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
    expect(onInsert).toHaveBeenCalledWith(
      expect.objectContaining({
        nodeId: "npc-glowkindle",
        reference: expect.objectContaining({
          kind: "ref",
          refType: "graph-node",
          refId: "npc-glowkindle",
          label: "Glowkindle",
        }),
      }),
    );
  });

  it("shows scope provenance on search results including World for universal nodes", async () => {
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
    expect(within(results).getByText(/longmont-c1/i)).toBeInTheDocument();

    await user.clear(screen.getByLabelText("Find objects"));
    await user.type(screen.getByLabelText("Find objects"), "inn");
    const innResults = screen.getByTestId("graph-reference-search-results");
    expect(within(innResults).getByText(/World/i)).toBeInTheDocument();
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

  it("permits Insert per object campaign tenancy for a C1 document against a C1+C2+universal projection", async () => {
    const user = userEvent.setup();
    const onInsert = vi.fn();
    const insertDeniedReason = (item: GraphReferenceSearchItem) => {
      if (item.nodeView.campaign_scope === "longmont-c2") return "C2 object · C1 document";
      return null;
    };

    render(
      <GraphReferenceSearch
        items={unionItems}
        projectionState="ready"
        insertDeniedReason={insertDeniedReason}
        onInsert={onInsert}
      />,
    );

    expect(screen.queryByText(/Unlock editing to insert chips/i)).not.toBeInTheDocument();

    const c1Button = within(
      screen.getByText("C1 NPC").closest("li") as HTMLElement,
    ).getByRole("button", { name: "Insert chip" });
    const c2Row = screen.getByText("C2 NPC").closest("li") as HTMLElement;
    const c2Button = within(c2Row).getByRole("button", { name: "Insert chip" });
    const universalButton = within(
      screen.getByText("Universal NPC").closest("li") as HTMLElement,
    ).getByRole("button", { name: "Insert chip" });

    expect(c1Button).toBeEnabled();
    expect(universalButton).toBeEnabled();
    expect(c2Button).toBeDisabled();
    expect(within(c2Row).getByTestId("graph-reference-insert-denied-npc-c2")).toHaveTextContent(
      "C2 object · C1 document",
    );

    await user.click(c1Button);
    await user.click(universalButton);
    await user.click(c2Button);
    expect(onInsert).toHaveBeenCalledTimes(2);
    expect(onInsert).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "npc-c1" }));
    expect(onInsert).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "npc-universal" }));
  });

  it("permits Insert per object campaign tenancy for a C2 document against a C1+C2+universal projection", async () => {
    const user = userEvent.setup();
    const onInsert = vi.fn();
    const insertDeniedReason = (item: GraphReferenceSearchItem) => {
      if (item.nodeView.campaign_scope === "longmont-c1") return "C1 object · C2 document";
      return null;
    };

    render(
      <GraphReferenceSearch
        items={unionItems}
        projectionState="ready"
        insertDeniedReason={insertDeniedReason}
        onInsert={onInsert}
      />,
    );

    const c1Row = screen.getByText("C1 NPC").closest("li") as HTMLElement;
    const c1Button = within(c1Row).getByRole("button", { name: "Insert chip" });
    const c2Button = within(
      screen.getByText("C2 NPC").closest("li") as HTMLElement,
    ).getByRole("button", { name: "Insert chip" });
    const universalButton = within(
      screen.getByText("Universal NPC").closest("li") as HTMLElement,
    ).getByRole("button", { name: "Insert chip" });

    expect(c1Button).toBeDisabled();
    expect(c2Button).toBeEnabled();
    expect(universalButton).toBeEnabled();
    expect(within(c1Row).getByTestId("graph-reference-insert-denied-npc-c1")).toHaveTextContent(
      "C1 object · C2 document",
    );

    await user.click(c2Button);
    await user.click(universalButton);
    await user.click(c1Button);
    expect(onInsert).toHaveBeenCalledTimes(2);
    expect(onInsert).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "npc-c2" }));
    expect(onInsert).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "npc-universal" }));
  });
});
