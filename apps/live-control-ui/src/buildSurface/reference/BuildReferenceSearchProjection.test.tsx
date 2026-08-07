import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { referenceFromGraphNode } from "../../graphReference/referenceFromGraphNode";
import type { GraphReferenceSearchItem } from "../../graphReference/types";
import type { BuildReferenceContextBinding } from "./buildBuildSurfaceInteractionPublication";
import { BUILD_REFERENCE_CONTEXT_BINDING_ID } from "./buildReferenceIds";
import { BuildReferenceSearchProjection } from "./BuildReferenceSearchProjection";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

const glowkindleNode: GraphProjectionNodeView = {
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
};

function searchItem(node: GraphProjectionNodeView): GraphReferenceSearchItem {
  return {
    nodeId: node.node_id,
    label: node.label,
    kind: node.kind,
    role: node.role,
    summary: node.summary ?? null,
    aliases: node.aliases ?? [],
    scopeLabel: "longmont-c1",
    reference: referenceFromGraphNode(node),
    nodeView: node,
  };
}

function renderWithContext(context: BuildReferenceContextBinding) {
  return render(
    <BuildReferenceSearchProjection
      bindings={{ [BUILD_REFERENCE_CONTEXT_BINDING_ID]: context }}
    />,
  );
}

function baseContext(
  overrides: Partial<BuildReferenceContextBinding> = {},
): BuildReferenceContextBinding {
  return {
    schema: "dmb_build_reference_context_v1",
    documentId: DOC_ID,
    documentCampaignId: "longmont-c1",
    lens: {
      status: "ready",
      documentId: DOC_ID,
      documentCampaignId: "longmont-c1",
      campaignId: "longmont-c1",
      worldId: "eldyrwild",
      availableCampaignIds: ["longmont-c1"],
      revision: { kind: "head" },
      scopeMode: "campaign",
      focus: { kind: "none", sessionId: null },
    },
    projectionState: "ready",
    projectionError: null,
    requestedRevisionId: null,
    loadedRevisionId: "rev-head",
    loadedIsHead: true,
    items: [searchItem(glowkindleNode)],
    selectCampaign: vi.fn(),
    viewExact: vi.fn(),
    insertChip: vi.fn(),
    insertDisabled: false,
    ...overrides,
  };
}

describe("BuildReferenceSearchProjection", () => {
  it("shows invalid lens reason", () => {
    renderWithContext(
      baseContext({
        lens: {
          status: "invalid",
          reason: "Campaign-scoped document (longmont-c1) does not admit campaign lens other.",
        },
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Campaign-scoped document (longmont-c1) does not admit campaign lens other.",
    );
  });

  it("shows nav-lens status for selection_required without campaign select", () => {
    renderWithContext(
      baseContext({
        lens: {
          status: "selection_required",
          documentId: DOC_ID,
          documentCampaignId: "eldyrwild",
          worldId: "eldyrwild",
          availableCampaignIds: ["longmont-c1", "longmont-c2"],
          revision: { kind: "head" },
          scopeMode: "campaign",
          focus: { kind: "none", sessionId: null },
          reason: "World-scoped document (eldyrwild) requires an explicit campaign selection.",
        },
      }),
    );

    expect(screen.getByRole("status")).toHaveTextContent(
      /World-scoped document \(eldyrwild\) requires an explicit campaign selection/i,
    );
    expect(screen.getByRole("status")).toHaveTextContent(/site navigation/i);
    expect(screen.queryByTestId("build-reference-campaign-select")).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-reference-search")).not.toBeInTheDocument();
  });

  it("ready state shows View and Insert chip actions", async () => {
    const user = userEvent.setup();
    const viewExact = vi.fn();
    const insertChip = vi.fn();

    renderWithContext(baseContext({ viewExact, insertChip, insertDisabled: false }));

    expect(screen.getByTestId("build-reference-lens-summary")).toHaveTextContent(
      "longmont-c1 · Current head · loaded rev-head",
    );
    await user.type(screen.getByLabelText("Find objects"), "glow");
    expect(screen.getByRole("button", { name: "Insert chip" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(viewExact).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "npc-glowkindle" }));
    await user.click(screen.getByRole("button", { name: "Insert chip" }));
    expect(insertChip).toHaveBeenCalledWith(
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

  it("disables Insert chip when insertDisabled while View stays available", async () => {
    const user = userEvent.setup();
    const insertChip = vi.fn();

    renderWithContext(baseContext({ insertChip, insertDisabled: true }));

    expect(screen.getByRole("button", { name: "Insert chip" })).toBeDisabled();
    expect(screen.getByText(/Unlock editing to insert chips/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(insertChip).not.toHaveBeenCalled();
  });

  it("enables Insert per object campaign for C1 vs C2 documents against a world union", async () => {
    const user = userEvent.setup();
    const c1Node: GraphProjectionNodeView = {
      ...glowkindleNode,
      node_id: "npc-c1",
      label: "C1 NPC",
      campaign_scope: "longmont-c1",
    };
    const c2Node: GraphProjectionNodeView = {
      ...glowkindleNode,
      node_id: "npc-c2",
      label: "C2 NPC",
      campaign_scope: "longmont-c2",
    };
    const universalNode: GraphProjectionNodeView = {
      ...glowkindleNode,
      node_id: "npc-universal",
      label: "Universal NPC",
      campaign_scope: null,
    };
    const unionItems = [searchItem(c1Node), searchItem(c2Node), searchItem(universalNode)].map(
      (item, index) => ({
        ...item,
        scopeLabel: [c1Node, c2Node, universalNode][index].campaign_scope ?? "World",
        nodeView: [c1Node, c2Node, universalNode][index],
      }),
    );

    const insertChipC1 = vi.fn();
    const { unmount } = renderWithContext(
      baseContext({
        documentCampaignId: "longmont-c1",
        items: unionItems,
        insertChip: insertChipC1,
        insertDisabled: false,
      }),
    );

    expect(
      within(screen.getByText("C1 NPC").closest("li") as HTMLElement).getByRole("button", {
        name: "Insert chip",
      }),
    ).toBeEnabled();
    expect(
      within(screen.getByText("C2 NPC").closest("li") as HTMLElement).getByRole("button", {
        name: "Insert chip",
      }),
    ).toBeDisabled();
    expect(screen.getByTestId("graph-reference-insert-denied-npc-c2")).toHaveTextContent(
      "C2 object · C1 document",
    );
    expect(
      within(screen.getByText("Universal NPC").closest("li") as HTMLElement).getByRole("button", {
        name: "Insert chip",
      }),
    ).toBeEnabled();
    expect(screen.queryByText(/Unlock editing to insert chips/i)).not.toBeInTheDocument();

    await user.click(
      within(screen.getByText("C1 NPC").closest("li") as HTMLElement).getByRole("button", {
        name: "Insert chip",
      }),
    );
    expect(insertChipC1).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "npc-c1" }));
    unmount();

    const insertChipC2 = vi.fn();
    renderWithContext(
      baseContext({
        documentCampaignId: "longmont-c2",
        documentId: DOC_ID,
        lens: {
          status: "ready",
          documentId: DOC_ID,
          documentCampaignId: "longmont-c2",
          campaignId: "longmont-c2",
          worldId: "eldyrwild",
          availableCampaignIds: ["longmont-c1", "longmont-c2"],
          revision: { kind: "head" },
          scopeMode: "world",
          focus: { kind: "none", sessionId: null },
        },
        items: unionItems,
        insertChip: insertChipC2,
        insertDisabled: false,
      }),
    );

    expect(
      within(screen.getByText("C1 NPC").closest("li") as HTMLElement).getByRole("button", {
        name: "Insert chip",
      }),
    ).toBeDisabled();
    expect(screen.getByTestId("graph-reference-insert-denied-npc-c1")).toHaveTextContent(
      "C1 object · C2 document",
    );
    expect(
      within(screen.getByText("C2 NPC").closest("li") as HTMLElement).getByRole("button", {
        name: "Insert chip",
      }),
    ).toBeEnabled();
    expect(
      within(screen.getByText("Universal NPC").closest("li") as HTMLElement).getByRole("button", {
        name: "Insert chip",
      }),
    ).toBeEnabled();
  });

  it("does not label a non-head snapshot as Current head", () => {
    renderWithContext(
      baseContext({
        loadedIsHead: false,
        loadedRevisionId: "rev-stale",
      }),
    );

    expect(screen.getByTestId("build-reference-lens-summary")).toHaveTextContent(
      "longmont-c1 · Loaded rev-stale",
    );
    expect(screen.getByTestId("build-reference-lens-summary")).not.toHaveTextContent("Current head");
  });

  it("error state shows exact error without stale search results", () => {
    renderWithContext(
      baseContext({
        projectionState: "error",
        projectionError: "Pinned revision rev-old does not match loaded revision rev-new.",
        items: [searchItem(glowkindleNode)],
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Pinned revision rev-old does not match loaded revision rev-new.",
    );
    expect(screen.queryByTestId("graph-reference-search-results")).not.toBeInTheDocument();
  });
});
