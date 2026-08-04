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
    },
    projectionState: "ready",
    projectionError: null,
    requestedRevisionId: null,
    loadedRevisionId: "rev-head",
    items: [searchItem(glowkindleNode)],
    selectCampaign: vi.fn(),
    viewExact: vi.fn(),
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

  it("shows campaign selector for selection_required without preselect", () => {
    const selectCampaign = vi.fn();
    renderWithContext(
      baseContext({
        lens: {
          status: "selection_required",
          documentId: DOC_ID,
          documentCampaignId: "eldyrwild",
          worldId: "eldyrwild",
          availableCampaignIds: ["longmont-c1", "longmont-c2"],
          revision: { kind: "head" },
          reason: "World-scoped document (eldyrwild) requires an explicit campaign selection.",
        },
        selectCampaign,
      }),
    );

    const select = screen.getByTestId("build-reference-campaign-select") as HTMLSelectElement;
    expect(select.value).toBe("");
    expect(within(select).getByRole("option", { name: "longmont-c1" })).toBeInTheDocument();
    expect(within(select).getByRole("option", { name: "longmont-c2" })).toBeInTheDocument();
    expect(screen.queryByTestId("graph-reference-search")).not.toBeInTheDocument();
  });

  it("ready state shows View without Insert and lens summary", async () => {
    const user = userEvent.setup();
    const viewExact = vi.fn();

    renderWithContext(baseContext({ viewExact }));

    expect(screen.getByTestId("build-reference-lens-summary")).toHaveTextContent(
      "longmont-c1 · Current head · loaded rev-head",
    );
    await user.type(screen.getByLabelText("Find objects"), "glow");
    expect(screen.queryByRole("button", { name: "Insert chip" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(viewExact).toHaveBeenCalledWith(expect.objectContaining({ nodeId: "npc-glowkindle" }));
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
