import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../../api/types";
import { mapWorldGraphLensObservation } from "../../graphLens/worldGraphLensSurfaceInformation";
import { createSurfaceInformationChannel } from "../../surfaceInformation";
import type { BuildReferenceContextBinding } from "./buildBuildSurfaceInteractionPublication";
import {
  BUILD_REFERENCE_CONTEXT_BINDING_ID,
  BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID,
} from "./buildReferenceIds";
import { BuildReferenceSearchProjection } from "./BuildReferenceSearchProjection";
import { buildWorldGraphInformationDescriptor } from "./buildWorldGraphSurfaceInformation";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

const glowkindleNode: WorldGraphProjectionNodeView = {
  nodeId: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  evidenceRefIds: [],
  sourceArtifactIds: [],
  anchoredToFocusSession: true,
  summary: "A friendly merchant.",
};

const request = {
  schema: "dmb_world_graph_projection_request_v1" as const,
  worldId: "eldyrwild",
  campaignId: "longmont-c1",
  scopeMode: "campaign" as const,
  focus: { kind: "none" as const, sessionId: null },
  admissibility: "gm" as const,
  revisionPin: null,
};

function projection(
  nodes: WorldGraphProjectionNodeView[] = [glowkindleNode],
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      revisionId: "rev-head",
      headRevisionId: "rev-head",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
      ...snapshotOverrides,
    },
    summary: {
      nodeCount: nodes.length,
      relationshipCount: 0,
      attributeCount: 0,
      evidenceCount: 0,
      sourceArtifactCount: 0,
      projectionTruncated: false,
    },
    nodes,
    relationships: [],
    attributes: [],
    evidence: [],
    sourceArtifacts: [],
    diagnostics: [],
  };
}

function commitReady(
  value: WorldGraphProjection,
) {
  const channel = createSurfaceInformationChannel(buildWorldGraphInformationDescriptor(request));
  const ticket = channel.beginObservation({ publishLoading: false });
  if (!ticket) {
    throw new Error("expected observation ticket");
  }
  const revisionId = value.snapshot.revisionId;
  channel.commit(ticket, {
    status: "ready",
    value,
    revision: { kind: "exact", value: revisionId },
    provenance: [{ kind: "world_graph_revision", id: revisionId }],
    inspectionTargets: [
      { kind: "world", id: value.snapshot.worldId },
      { kind: "campaign", id: value.snapshot.campaignId },
      { kind: "world_graph_revision", id: revisionId },
    ],
    diagnostics: [],
  });
  return channel;
}

function commitChannel(
  response: WorldGraphProjection | null,
  error?: unknown,
) {
  const channel = createSurfaceInformationChannel(buildWorldGraphInformationDescriptor(request));
  const ticket = channel.beginObservation();
  if (!ticket) {
    throw new Error("expected observation ticket");
  }
  channel.commit(ticket, mapWorldGraphLensObservation({ request, response, error }));
  return channel;
}

function renderWithBindings(
  context: BuildReferenceContextBinding,
  channel: ReturnType<typeof commitChannel> | null = commitChannel(projection()),
) {
  return render(
    <BuildReferenceSearchProjection
      bindings={{
        [BUILD_REFERENCE_CONTEXT_BINDING_ID]: context,
        [BUILD_WORLD_GRAPH_INFORMATION_CHANNEL_BINDING_ID]: channel,
      }}
    />,
  );
}

function baseContext(
  overrides: Partial<BuildReferenceContextBinding> = {},
): BuildReferenceContextBinding {
  return {
    schema: "dmb_build_reference_context_v2",
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
    selectCampaign: vi.fn(),
    viewExact: vi.fn(),
    insertChip: vi.fn(),
    editorInsertDisabled: false,
    ...overrides,
  };
}

describe("BuildReferenceSearchProjection", () => {
  it("shows invalid lens reason", () => {
    renderWithBindings(
      baseContext({
        lens: {
          status: "invalid",
          reason: "Campaign-scoped document (longmont-c1) does not admit campaign lens other.",
        },
      }),
      null,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Campaign-scoped document (longmont-c1) does not admit campaign lens other.",
    );
  });

  it("shows nav-lens status for selection_required without campaign select", () => {
    renderWithBindings(
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
      null,
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

    renderWithBindings(baseContext({ viewExact, insertChip, editorInsertDisabled: false }));

    expect(screen.getByTestId("build-reference-lens-summary")).toHaveTextContent(
      "longmont-c1 · Current head · loaded rev-head",
    );
    await user.type(screen.getByLabelText("Find objects"), "glow");
    expect(screen.getByRole("button", { name: "Insert chip" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(viewExact).toHaveBeenCalledWith("npc-glowkindle");
    await user.click(screen.getByRole("button", { name: "Insert chip" }));
    expect(insertChip).toHaveBeenCalledWith("npc-glowkindle");
  });

  it("disables Insert chip when editorInsertDisabled while View stays available", async () => {
    const user = userEvent.setup();
    const insertChip = vi.fn();

    renderWithBindings(baseContext({ insertChip, editorInsertDisabled: true }));

    expect(screen.getByRole("button", { name: "Insert chip" })).toBeDisabled();
    expect(screen.getByText(/Unlock editing to insert chips/i)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(insertChip).not.toHaveBeenCalled();
  });

  it("enables Insert per object campaign for C1 vs C2 documents against a world union", async () => {
    const user = userEvent.setup();
    const c1Node: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "npc-c1",
      label: "C1 NPC",
      campaignScope: "longmont-c1",
    };
    const c2Node: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "npc-c2",
      label: "C2 NPC",
      campaignScope: "longmont-c2",
    };
    const universalNode: WorldGraphProjectionNodeView = {
      ...glowkindleNode,
      nodeId: "npc-universal",
      label: "Universal NPC",
      campaignScope: null,
    };
    const union = projection([c1Node, c2Node, universalNode], { scopeMode: "world" });
    const worldRequest = { ...request, scopeMode: "world" as const, campaignId: "longmont-c1" };
    const unionChannel = createSurfaceInformationChannel(
      buildWorldGraphInformationDescriptor(worldRequest),
    );
    const ticket = unionChannel.beginObservation();
    unionChannel.commit(
      ticket!,
      mapWorldGraphLensObservation({ request: worldRequest, response: union }),
    );

    const insertChipC1 = vi.fn();
    const { unmount } = renderWithBindings(
      baseContext({
        documentCampaignId: "longmont-c1",
        insertChip: insertChipC1,
        editorInsertDisabled: false,
      }),
      unionChannel,
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
    expect(insertChipC1).toHaveBeenCalledWith("npc-c1");
    unmount();

    const insertChipC2 = vi.fn();
    renderWithBindings(
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
        insertChip: insertChipC2,
        editorInsertDisabled: false,
      }),
      unionChannel,
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
    renderWithBindings(
      baseContext(),
      commitReady(
        projection([glowkindleNode], {
          revisionId: "rev-stale",
          headRevisionId: "rev-head",
          isHead: false,
        }),
      ),
    );

    expect(screen.getByTestId("build-reference-lens-summary")).toHaveTextContent(
      "longmont-c1 · Loaded rev-stale",
    );
    expect(screen.getByTestId("build-reference-lens-summary")).not.toHaveTextContent("Current head");
  });

  it("integrity_error shows exact error without stale search results", () => {
    renderWithBindings(
      baseContext(),
      commitChannel({
        ...projection(),
        snapshot: {
          ...projection().snapshot,
          campaignId: "longmont-c2",
        },
      }),
    );

    expect(screen.getByRole("alert")).toHaveTextContent(/does not match requested campaign/);
    expect(screen.queryByTestId("graph-reference-search-results")).not.toBeInTheDocument();
  });

  it("EMPTY is a successful zero-result state, not unavailable or error", () => {
    renderWithBindings(baseContext(), commitChannel(projection([])));

    expect(screen.getByText("World Graph projection is empty for this exact request.")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByText("Glowkindle")).not.toBeInTheDocument();
    expect(screen.getByText("No nodes in the current projection.")).toBeInTheDocument();
  });

  it("UNAVAILABLE renders the failure reason without leftover items", () => {
    renderWithBindings(
      baseContext(),
      commitChannel(null, new Error("authority down")),
    );

    expect(screen.getByRole("status")).toHaveTextContent(/World Graph is unavailable/);
    expect(screen.getByRole("status")).toHaveTextContent(/authority down/);
    expect(screen.queryByText("Glowkindle")).not.toBeInTheDocument();
  });

  it("updates in place across generations of the same channel handle", () => {
    const channel = createSurfaceInformationChannel(buildWorldGraphInformationDescriptor(request));
    renderWithBindings(baseContext(), channel);

    expect(screen.getByText(/Loading World Graph projection/)).toBeInTheDocument();

    const readyTicket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(
        readyTicket!,
        mapWorldGraphLensObservation({ request, response: projection() }),
      );
    });
    expect(screen.getByText("Glowkindle")).toBeInTheDocument();

    let emptyTicket = null as ReturnType<typeof channel.beginObservation>;
    act(() => {
      emptyTicket = channel.beginObservation();
    });
    act(() => {
      channel.commit(
        emptyTicket!,
        mapWorldGraphLensObservation({ request, response: projection([]) }),
      );
    });
    expect(screen.getByText("World Graph projection is empty for this exact request.")).toBeInTheDocument();
    expect(screen.queryByText("Glowkindle")).not.toBeInTheDocument();
  });
});
