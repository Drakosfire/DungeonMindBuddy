import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { describe, expect, it } from "vitest";

import type { GraphProjectionNodeView } from "../../api/types";
import { buildGraphObjectCardFromNodeView } from "../../graphObjectCard";
import { ProjectionProvider } from "../projection/projectionContext";
import type { SurfaceConfig } from "../types";
import { PlanReferenceObjectCard } from "./PlanReferenceObjectCard";
import type { PlanReferenceResolution } from "./graphAwareReferenceResolver";

const glowkindleNode: GraphProjectionNodeView = {
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

const sessionDescriptor = {
  surfaceId: "plan" as const,
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown" as const,
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "C2 Session 23 Prep",
    targetRelpath: "corpus/example.md",
    storageKey: "storage-key",
    status: "local_draft" as const,
  },
};

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Longmont C2",
    prepSession: 23,
    ingestSession: 21,
    liveSession: 22,
  },
  tools: [{ id: "statblock", label: "Statblock", size: "wide" }],
  canvas: { documentId: "longmont-c2-session-23-prep" },
  theme: {},
  sessionDescriptor,
};

function renderWithProjection(ui: ReactElement) {
  return render(<ProjectionProvider config={surfaceConfig}>{ui}</ProjectionProvider>);
}

describe("PlanReferenceObjectCard", () => {
  it("renders GraphObjectCard for graph-node hits", async () => {
    const resolution: PlanReferenceResolution = {
      kind: "graph-node",
      locator: "dmb-node:npc-glowkindle",
      graphObject: buildGraphObjectCardFromNodeView(glowkindleNode),
      graphNodeId: "npc-glowkindle",
      fallback: null,
      source: "union-supergraph",
      graphProjectionState: "ready",
    };

    const user = userEvent.setup();
    render(<PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />);

    const card = screen.getByLabelText(/Glowkindle graph object/i);
    expect(card).toHaveClass("graph-object-card");
    expect(within(card).getByRole("heading", { level: 4 })).toHaveTextContent("Glowkindle");
    expect(within(card).getByText(/Also known as: Glow/)).toBeInTheDocument();
    expect(within(card).getByText("A friendly merchant.")).toBeInTheDocument();
    expect(within(card).getByRole("heading", { name: "Related objects" })).toBeInTheDocument();

    expect(within(card).getByRole("link", { name: /Review memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );
    expect(within(card).getByRole("button", { name: /Inspect source\/evidence/i })).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /Open statblock/i })).not.toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /Open roll table/i })).not.toBeInTheDocument();

    await user.click(within(card).getByText("Details"));
    expect(within(card).getByText(/1 evidence badge/)).toBeInTheDocument();
    expect(within(card).queryByText(/Node ID:/)).not.toBeInTheDocument();
    expect(within(card).queryByText("npc-glowkindle")).not.toBeInTheDocument();
    expect(screen.queryByTestId("plan-reference-fallback-banner")).not.toBeInTheDocument();
    expect(screen.queryByTestId("plan-reference-unresolved-card")).not.toBeInTheDocument();
  });

  it("opens Details when Inspect source/evidence is clicked", async () => {
    const resolution: PlanReferenceResolution = {
      kind: "graph-node",
      locator: "dmb-node:npc-glowkindle",
      graphObject: buildGraphObjectCardFromNodeView(glowkindleNode),
      graphNodeId: "npc-glowkindle",
      fallback: null,
      source: "union-supergraph",
      graphProjectionState: "ready",
    };

    const user = userEvent.setup();
    render(<PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />);

    const card = screen.getByLabelText(/Glowkindle graph object/i);
    const details = within(card).getByText("Details").closest("details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");

    await user.click(within(card).getByRole("button", { name: /Inspect source\/evidence/i }));
    expect(details).toHaveAttribute("open");
  });

  it("renders Open statblock for grounded statblock graph nodes when projection can open tools", async () => {
    const resolution: PlanReferenceResolution = {
      kind: "graph-node",
      locator: "dmb-node:statblock-tripod",
      refType: "statblock",
      graphObject: buildGraphObjectCardFromNodeView({
        ...glowkindleNode,
        node_id: "statblock-tripod",
        label: "Tripod Null-Calf",
        kind: "statblock",
        role: "creature",
      }),
      graphNodeId: "statblock-tripod",
      fallback: null,
      source: "union-supergraph",
      graphProjectionState: "ready",
    };

    const user = userEvent.setup();
    renderWithProjection(
      <PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />,
    );

    const card = screen.getByLabelText(/Tripod Null-Calf graph object/i);
    expect(within(card).getByRole("button", { name: /Open statblock/i })).toBeInTheDocument();
    expect(within(card).queryByRole("button", { name: /Open roll table/i })).not.toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /Review memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );

    await user.click(within(card).getByRole("button", { name: /Open statblock/i }));
    // Click must not crash; tool open is handled by ProjectionProvider.
    expect(within(card).getByRole("button", { name: /Open statblock/i })).toBeInTheDocument();
  });

  it("omits Open statblock when projection context is unavailable", () => {
    const resolution: PlanReferenceResolution = {
      kind: "graph-node",
      locator: "dmb-node:statblock-tripod",
      refType: "statblock",
      graphObject: buildGraphObjectCardFromNodeView({
        ...glowkindleNode,
        node_id: "statblock-tripod",
        label: "Tripod Null-Calf",
        kind: "statblock",
        role: "creature",
      }),
      graphNodeId: "statblock-tripod",
      fallback: null,
      source: "union-supergraph",
      graphProjectionState: "ready",
    };

    render(<PlanReferenceObjectCard resolution={resolution} sessionDescriptor={sessionDescriptor} />);

    expect(screen.queryByRole("button", { name: /Open statblock/i })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Review memory in \/ingest/i })).toBeInTheDocument();
  });

  it("renders unresolved state for ambiguous graph matches", () => {
    const resolution: PlanReferenceResolution = {
      kind: "unresolved",
      locator: "#dmb-ref:npc:lysandra",
      refType: "npc",
      refId: "lysandra",
      graphObject: null,
      graphNodeId: null,
      ambiguousNodeIds: ["npc-lysandra-a", "npc-lysandra-b"],
      fallback: null,
      source: "unresolved",
      message:
        "Could not uniquely resolve this object from graph memory. Use /ingest to review aliases or identity. Open /ingest to fix memory.",
      graphProjectionState: "ready",
    };

    render(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
      />,
    );

    expect(screen.getByTestId("plan-reference-unresolved-card")).toBeInTheDocument();
    expect(screen.getByText(/Could not uniquely resolve this object from graph memory/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Fix memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );
    expect(screen.queryByLabelText(/graph object/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/selected object/i)).not.toBeInTheDocument();
  });

  it("renders corpus fallback as fallback, not authoritative graph memory", () => {
    const resolution: PlanReferenceResolution = {
      kind: "corpus-index",
      locator: "#dmb-ref:location:north-reach-gate",
      refType: "location",
      refId: "north-reach-gate",
      graphObject: null,
      graphNodeId: null,
      fallback: {
        status: "resolved",
        ref: {
          kind: "ref",
          refType: "location",
          refId: "north-reach-gate",
          label: "North Reach Gate",
        },
        source: "location-index",
        item: {
          title: "North Reach Gate",
          settlement: "Mireward Reach",
          corpus_display_path: "corpus/locations/north_reach_gate.md",
        },
        sourcePath: "corpus/locations/north_reach_gate.md",
        message: "Resolved from live location index.",
      },
      source: "corpus-index",
      graphProjectionState: "ready",
    };

    render(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
      />,
    );

    expect(screen.getByTestId("plan-reference-fallback-banner")).toHaveTextContent(
      /Graph memory did not resolve this yet/i,
    );
    expect(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).toBeInTheDocument();
    expect(within(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).getByText(
      "Location reference resolved from corpus index.",
    )).toBeInTheDocument();
    expect(
      within(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).getByRole("link", {
        name: /Review memory in \/ingest/i,
      }),
    ).toHaveAttribute("href", "/ingest?campaign=longmont-c2&session=session-21");
    expect(
      within(screen.getByLabelText(/North Reach Gate corpus fallback object/i)).getByText(
        "Freshness: Corpus index fallback",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByLabelText(/selected object/i)).not.toBeInTheDocument();
  });

  it("shows projection-unavailable note on unresolved cards", () => {
    const resolution: PlanReferenceResolution = {
      kind: "unresolved",
      locator: "#dmb-ref:npc:missing",
      refType: "npc",
      refId: "missing",
      graphObject: null,
      graphNodeId: null,
      fallback: {
        status: "unresolved",
        ref: {
          kind: "ref",
          refType: "npc",
          refId: "missing",
          label: "Missing NPC",
        },
        message: "Could not resolve this reference.",
      },
      source: "unresolved",
      message: "Could not resolve this reference from graph memory or corpus indexes. Open /ingest to fix memory.",
      graphProjectionState: "unavailable",
    };

    render(
      <PlanReferenceObjectCard
        resolution={resolution}
        sessionDescriptor={sessionDescriptor}
        projectionState="unavailable"
      />,
    );

    expect(screen.getByText(/Union Supergraph projection is unavailable/i)).toBeInTheDocument();
  });
});
