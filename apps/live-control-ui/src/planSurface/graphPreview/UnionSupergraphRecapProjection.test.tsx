import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { WorldGraphProjection } from "../../api/types";
import { FIXTURE_DOC_ID, fixturePlanSessionDescriptor } from "../config/planSessionDescriptor";
import { AdaptiveProjectionContainer } from "../projection/AdaptiveProjectionContainer";
import { ProjectionProvider } from "../projection/projectionContext";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";
import type { SurfaceConfig } from "../types";
import { UnionSupergraphRecapProjection } from "./UnionSupergraphRecapProjection";
import { session23UnionSupergraphFixture } from "./unionSupergraphFixture";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    postWorldGraphProjection: vi.fn(),
    getRecapArtifacts: vi.fn().mockResolvedValue({ records: [] }),
  };
});

import * as liveApi from "../../api/liveApi";

const sessionDescriptor = fixturePlanSessionDescriptor({ memorySession: 23 });

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Longmont C2",
    ingestSession: 23,
    liveSession: 23,
  },
  tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
  canvas: { documentId: FIXTURE_DOC_ID },
  theme: {},
  sessionDescriptor,
};

const worldProjection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: {
    worldId: "eldyrwild",
    campaignId: "longmont-c2",
    revisionId: "rev-1",
    headRevisionId: "rev-1",
    isHead: true,
    focus: { kind: "session", sessionId: "session-23" },
    admissibility: "gm",
  },
  summary: {
    nodeCount: 2,
    relationshipCount: 1,
    attributeCount: 0,
    evidenceCount: 1,
    sourceArtifactCount: 0,
    sourceTruncated: false,
  },
  nodes: [
    {
      nodeId: "pc_caelynn",
      label: "Caelynn",
      kind: "pc",
      role: "pc",
      aliases: ["Caelynn"],
      sourceDomains: ["recap", "worldbuilding"],
      summary: "Read-model example global PC node.",
      anchoredToFocusSession: true,
      evidenceBadges: [
        {
          evidenceRefId: "evidence:session-23:caelynn:recap-mention",
          sourceArtifactId: "artifact:recap:longmont-c2:session-23",
          sourceDomain: "recap",
          evidenceRole: "focus_session_recap_mention",
          isFocusSessionEvidence: true,
          canOpenSource: true,
          canHighlightSpan: true,
          label: "Held the Mireward gate during the incident",
          sessionId: "session-23",
          sourceSpanRefId: "spref:session-23:p014",
        },
      ],
      adjacency: [
        {
          edgeId: "edge:pc_caelynn:connected_to:loc_mirathorn",
          nodeId: "loc_mirathorn",
          label: "Mirathorn",
          kind: "location",
          predicate: "connected_to",
          direction: "outbound",
          anchoredToFocusSession: false,
          sourceDomains: ["worldbuilding"],
          evidenceRefIds: ["evidence:worldbuilding:caelynn:character-note"],
          edgeLabel: "connected to",
          sessionIds: [],
        },
      ],
      suggestedExpansions: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
    },
    {
      nodeId: "loc_mirathorn",
      label: "Mirathorn",
      kind: "location",
      role: "location",
      aliases: ["Mirathorn"],
      sourceDomains: ["worldbuilding"],
      summary: "A trade city.",
      anchoredToFocusSession: false,
      evidenceBadges: [],
      adjacency: [],
      suggestedExpansions: [],
      evidenceRefIds: [],
      sourceArtifactIds: [],
    },
  ],
  relationships: [],
  attributes: [],
  evidence: [],
  sourceArtifacts: [],
  diagnostics: [],
};

function PlanLensHarness({ children }: { children: ReactNode }) {
  return (
    <ProjectionProvider config={surfaceConfig}>
      <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
        {children}
        <AdaptiveProjectionContainer config={surfaceConfig} />
      </PlanGraphReferenceResolverProvider>
    </ProjectionProvider>
  );
}

function renderWithPlanLens(ui: ReactElement) {
  return render(<PlanLensHarness>{ui}</PlanLensHarness>);
}

describe("UnionSupergraphRecapProjection", () => {
  beforeEach(() => {
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(worldProjection);
  });

  it("shows a session title without projection jargon", () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
        projectionSource="world-graph"
      />,
    );

    expect(screen.getByRole("heading", { level: 2, name: "Session 23" })).toBeInTheDocument();
    expect(screen.getByText(/Click a highlighted name/i)).toBeInTheDocument();
    expect(screen.queryByText(/session focus lens/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/World Graph head/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/TipTap/i)).not.toBeInTheDocument();
  });

  it("hides Recap chrome when embedded in Graph Review", () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
        projectionSource="world-graph"
        chrome="embedded"
      />,
    );

    expect(screen.queryByText(/^Recap$/)).not.toBeInTheDocument();
    expect(screen.queryByRole("heading", { level: 2, name: "Session 23" })).not.toBeInTheDocument();
    expect(screen.queryByText(/Click a highlighted name/i)).not.toBeInTheDocument();
    expect(screen.getByLabelText("Session 23 recap")).toBeInTheDocument();
  });

  it("renders recap without a default static explorer panel", () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    expect(screen.getByRole("heading", { level: 2, name: "Session 23" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Graph object panel")).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/Caelynn graph object/i)).not.toBeInTheDocument();
  });

  it("opens PlanReferenceObjectCard via the shared drawer when a recap chip is clicked", async () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    await waitFor(() => {
      expect(screen.getByLabelText(/Caelynn graph object/i)).toBeInTheDocument();
    });
    expect(screen.getByLabelText("Connected objects and relationships")).toBeInTheDocument();
    expect(screen.queryByLabelText("Graph object panel")).not.toBeInTheDocument();
  });

  it("navigates related objects through the Plan reference host", async () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    await waitFor(() => {
      expect(screen.getByLabelText(/Caelynn graph object/i)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: /Open related object.*Mirathorn/i }));

    await waitFor(() => {
      expect(screen.getByLabelText(/Mirathorn graph object/i)).toBeInTheDocument();
    });
  });

  it("shows GraphObjectCard evidence from the resolved world graph node", async () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    fireEvent.click(caelynnPill);

    const card = await waitFor(() => screen.getByLabelText(/Caelynn graph object/i));
    fireEvent.click(within(card).getByText("Details"));
    expect(within(card).getByLabelText("Evidence and source")).toBeInTheDocument();
    expect(within(card).getByText(/Held the Mireward gate/i)).toBeInTheDocument();
  });

  it("applies role styling to recap pills", async () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    expect(caelynnPill).toHaveClass("role-pc");
  });

  it("shows GM planning hover card content on recap pills", async () => {
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
      />,
    );

    const caelynnPill = await waitFor(() => {
      const pill = screen
        .getAllByRole("button", { name: "Caelynn" })
        .find((button) => button.classList.contains("recap-node-token"));
      expect(pill).toBeTruthy();
      return pill as HTMLButtonElement;
    });
    const hoverCard = caelynnPill.parentElement?.querySelector(".recap-node-hover-card");
    expect(hoverCard).toHaveTextContent("PC");
    expect(hoverCard).not.toHaveTextContent("Why now");
    expect(hoverCard).toHaveTextContent("Read-model example global PC node");
  });

  it("calls legacy opener when provided", () => {
    const onOpenLegacy = vi.fn();
    renderWithPlanLens(
      <UnionSupergraphRecapProjection
        payload={session23UnionSupergraphFixture}
        selectedSessionId="session-23"
        onSelectSession={() => undefined}
        sessionOptions={["session-23"]}
        onOpenLegacy={onOpenLegacy}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Older preview" }));
    expect(onOpenLegacy).toHaveBeenCalledOnce();
  });
});
