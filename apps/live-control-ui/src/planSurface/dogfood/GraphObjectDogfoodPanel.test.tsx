import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useEffect } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GraphProjectionNodeView, UnionSupergraphProjectionResponse } from "../../api/types";
import { ProjectionProvider, useProjection } from "../projection/projectionContext";
import type { PlanSessionDescriptor, SurfaceConfig } from "../types";
import { createPlanCanvasStorageKey } from "../config/planSessionDescriptor";
import { GraphObjectDogfoodPanel } from "./GraphObjectDogfoodPanel";
import { graphObjectDogfoodStorageKey } from "./graphObjectDogfoodStorage";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    getUnionSupergraphProjection: vi.fn(),
  };
});

import * as liveApi from "../../api/liveApi";

const thinNode: GraphProjectionNodeView = {
  node_id: "npc-thin",
  label: "Thin NPC",
  kind: "npc",
  role: "npc",
  aliases: [],
  source_domains: [],
  evidence_badges: [],
  adjacency: [],
  anchored_to_focus_session: true,
  summary: null,
};

const richNode: GraphProjectionNodeView = {
  node_id: "npc-glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  source_domains: ["recap"],
  evidence_badges: [
    {
      evidence_ref_id: "ev-1",
      label: "Session recap mention",
      source_domain: "recap",
      source_artifact_id: "artifact-1",
    },
  ],
  adjacency: [
    {
      edge_id: "edge-1",
      node_id: "location-inn",
      label: "Inn",
      kind: "location",
      predicate: "met at",
      direction: "outgoing",
      related_summary: "Trades herbs.",
      evidence_ref_ids: [],
      source_domains: ["recap"],
      anchored_to_focus_session: true,
      session_ids: ["session-21"],
      source_excerpt: "Glowkindle waved from the inn.",
      source_excerpt_is_full_paragraph: false,
    },
  ],
  anchored_to_focus_session: true,
  summary: "A friendly merchant.",
  source_anchor_text: "Glowkindle waved from the inn.",
};

const innNode: GraphProjectionNodeView = {
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
};

const projection: UnionSupergraphProjectionResponse = {
  campaign_id: "longmont-c2",
  session_id: "session-21",
  node_views: {
    "npc-glowkindle": richNode,
    "npc-thin": thinNode,
    "location-inn": innNode,
  },
  focus: {
    focused_evidence_ref_ids: [],
    focused_node_ids: [],
    focused_edge_ids: [],
  },
  mentions: [],
};

const sessionDescriptor: PlanSessionDescriptor = {
  surfaceId: "plan",
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown",
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "Longmont C2 Session 23 Prep",
    targetRelpath: "corpus/example/Session 23 Prep.md",
    storageKey: createPlanCanvasStorageKey({
      campaignId: "longmont-c2",
      prepSession: 23,
      documentId: "longmont-c2-session-23-prep",
    }),
    status: "local_draft",
  },
};

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    liveSession: 22,
    prepSession: 23,
    ingestSession: 21,
    headerLabel: "Longmont C2",
  },
  sessionDescriptor,
  tools: [],
  canvas: { documentId: "longmont-c2-session-23-prep" },
  theme: {},
};

function ActiveTitleProbe() {
  const { active, activePlanReference } = useProjection();
  return (
    <div data-testid="active-probe">
      <span data-testid="active-title">{active?.title ?? ""}</span>
      <span data-testid="active-kind">{activePlanReference?.kind ?? ""}</span>
      <span data-testid="active-node">{activePlanReference?.graphNodeId ?? ""}</span>
    </div>
  );
}

function renderPanel() {
  return render(
    <ProjectionProvider config={surfaceConfig}>
      <GraphObjectDogfoodPanel sessionDescriptor={sessionDescriptor} />
      <ActiveTitleProbe />
    </ProjectionProvider>,
  );
}

describe("GraphObjectDogfoodPanel", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(liveApi.getUnionSupergraphProjection).mockReset();
    vi.mocked(liveApi.getUnionSupergraphProjection).mockResolvedValue(projection);
  });

  it("renders available projection nodes", async () => {
    renderPanel();

    const available = await screen.findByTestId("graph-object-dogfood-available");
    expect(within(available).getByText("Glowkindle")).toBeInTheDocument();
    expect(within(available).getByText("Thin NPC")).toBeInTheDocument();
    expect(within(available).getByText("Inn")).toBeInTheDocument();
  });

  it("filters available nodes by graph search", async () => {
    const user = userEvent.setup();
    renderPanel();

    await screen.findByTestId("graph-object-dogfood-available");
    await user.type(screen.getByLabelText("Search graph"), "glow");

    const available = screen.getByTestId("graph-object-dogfood-available");
    expect(within(available).getByText("Glowkindle")).toBeInTheDocument();
    expect(within(available).queryByText("Thin NPC")).not.toBeInTheDocument();
    expect(within(available).queryByText("Inn")).not.toBeInTheDocument();
  });

  it("adds a card to the local dogfood list without duplicating", async () => {
    const user = userEvent.setup();
    renderPanel();

    const available = await screen.findByTestId("graph-object-dogfood-available");
    const glowRow = within(available).getByText("Glowkindle").closest("li");
    expect(glowRow).toBeTruthy();
    await user.click(within(glowRow as HTMLElement).getByRole("button", { name: "Add card" }));

    const collection = screen.getByTestId("graph-object-dogfood-collection");
    expect(within(collection).getByText("Glowkindle")).toBeInTheDocument();
    expect(within(glowRow as HTMLElement).getByRole("button", { name: "Added" })).toBeDisabled();

    const stored = JSON.parse(
      localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor)) ?? "{}",
    );
    expect(stored.addedNodeIds).toEqual(["npc-glowkindle"]);
  });

  it("views a card through the real Plan reference projection path", async () => {
    const user = userEvent.setup();
    renderPanel();

    const available = await screen.findByTestId("graph-object-dogfood-available");
    const glowRow = within(available).getByText("Glowkindle").closest("li") as HTMLElement;
    await user.click(within(glowRow).getByRole("button", { name: "Add card" }));
    const collection = screen.getByTestId("graph-object-dogfood-collection");
    await user.click(within(collection).getByRole("button", { name: "View card" }));

    await waitFor(() => {
      expect(screen.getByTestId("active-title")).toHaveTextContent("Glowkindle");
      expect(screen.getByTestId("active-kind")).toHaveTextContent("graph-node");
      expect(screen.getByTestId("active-node")).toHaveTextContent("npc-glowkindle");
    });

    const stored = JSON.parse(
      localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor)) ?? "{}",
    );
    expect(stored.viewedNodeIds).toContain("npc-glowkindle");
  });

  it("surfaces thin-card coverage when summary/relationships/evidence are missing", async () => {
    const user = userEvent.setup();
    renderPanel();

    const available = await screen.findByTestId("graph-object-dogfood-available");
    const thinRow = within(available).getByText("Thin NPC").closest("li") as HTMLElement;
    await user.click(within(thinRow).getByRole("button", { name: "Add card" }));

    expect(screen.getByText(/Thin card/i)).toBeInTheDocument();
    expect(screen.getByText(/Missing: summary/i)).toBeInTheDocument();
  });

  it("removes from dogfood list with local-only copy and no write endpoints", async () => {
    const user = userEvent.setup();
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    renderPanel();

    const available = await screen.findByTestId("graph-object-dogfood-available");
    const glowRow = within(available).getByText("Glowkindle").closest("li") as HTMLElement;
    await user.click(within(glowRow).getByRole("button", { name: "Add card" }));
    await user.click(screen.getByRole("button", { name: "Remove from dogfood list" }));

    expect(screen.queryByTestId("graph-object-dogfood-collection")).not.toBeInTheDocument();
    expect(screen.getByText(/No cards on the dogfood list yet/i)).toBeInTheDocument();
    expect(screen.getByText(/Does not delete graph nodes or corpus markdown/i)).toBeInTheDocument();

    const writeCalls = fetchSpy.mock.calls.filter((call) => {
      const init = call[1] as RequestInit | undefined;
      const method = String(init?.method ?? "GET").toUpperCase();
      return method !== "GET" && method !== "HEAD";
    });
    expect(writeCalls).toHaveLength(0);
    fetchSpy.mockRestore();
  });

  it("persists usefulness and notes locally", async () => {
    const user = userEvent.setup();
    renderPanel();

    const available = await screen.findByTestId("graph-object-dogfood-available");
    const glowRow = within(available).getByText("Glowkindle").closest("li") as HTMLElement;
    await user.click(within(glowRow).getByRole("button", { name: "Add card" }));

    await user.selectOptions(screen.getByLabelText("Usefulness for Glowkindle"), "useful");
    await user.type(screen.getByLabelText("Notes for Glowkindle"), "Would use at the table.");

    await waitFor(() => {
      const stored = JSON.parse(
        localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor)) ?? "{}",
      );
      expect(stored.usefulnessByNodeId["npc-glowkindle"]).toBe("useful");
      expect(stored.notesByNodeId["npc-glowkindle"]).toContain("Would use at the table.");
    });
  });

  it("clears local dogfood graph state", async () => {
    const user = userEvent.setup();
    renderPanel();

    const available = await screen.findByTestId("graph-object-dogfood-available");
    const glowRow = within(available).getByText("Glowkindle").closest("li") as HTMLElement;
    await user.click(within(glowRow).getByRole("button", { name: "Add card" }));
    await user.click(screen.getByRole("button", { name: "Clear graph object dogfood list" }));

    expect(localStorage.getItem(graphObjectDogfoodStorageKey(sessionDescriptor))).toBeNull();
    expect(screen.getByText(/No cards on the dogfood list yet/i)).toBeInTheDocument();
  });
});

describe("GraphObjectDogfoodPanel relationship traversal handoff", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.mocked(liveApi.getUnionSupergraphProjection).mockReset();
    vi.mocked(liveApi.getUnionSupergraphProjection).mockResolvedValue(projection);
  });

  it("does not auto-add a related card opened outside Add", async () => {
    function SeedRelatedView() {
      const { openPlanReferenceResolution } = useProjection();
      useEffect(() => {
        openPlanReferenceResolution({
          kind: "graph-node",
          locator: "dmb-node:location-inn",
          refType: "location",
          refId: "location-inn",
          graphObject: {
            id: "location-inn",
            label: "Inn",
            typeBadgeLabel: "Location",
            actions: [],
          },
          graphNodeId: "location-inn",
          fallback: null,
          source: "union-supergraph",
        });
      }, [openPlanReferenceResolution]);
      return null;
    }

    render(
      <ProjectionProvider config={surfaceConfig}>
        <SeedRelatedView />
        <GraphObjectDogfoodPanel sessionDescriptor={sessionDescriptor} />
      </ProjectionProvider>,
    );

    expect(await screen.findByText(/Viewing a related card that is not on the dogfood list/i)).toBeInTheDocument();
    expect(screen.queryByTestId("graph-object-dogfood-collection")).not.toBeInTheDocument();
  });
});
