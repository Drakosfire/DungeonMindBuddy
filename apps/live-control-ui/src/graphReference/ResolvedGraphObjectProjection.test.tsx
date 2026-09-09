import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import { adaptWorldGraphNodeView } from "../worldGraph/worldGraphNodeViewAdapter";
import { session23WorldGraphRecapFixture } from "../planSurface/graphPreview/worldGraphRecapFixture";
import type { GraphReferenceResolution } from "./types";
import { ResolvedGraphObjectProjection } from "./ResolvedGraphObjectProjection";

vi.mock("../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../api/liveApi")>("../api/liveApi");
  return {
    ...actual,
    postWorldGraphCompleteObject: vi.fn(),
  };
});

import * as liveApi from "../api/liveApi";

const caelynn = session23WorldGraphRecapFixture.nodeViews.pc_caelynn;

function resolvedCaelynn(): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: "dmb-node:pc_caelynn",
    reference: null,
    graphNodeId: "pc_caelynn",
    graphObject: buildGraphObjectCardFromNodeView(adaptWorldGraphNodeView(caelynn)),
    graphScope: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "world",
      revisionId: session23WorldGraphRecapFixture.snapshot.revisionId,
    },
    projectionState: "ready",
    message: "Resolved.",
  };
}

function completeObject(status: "complete" | "partial") {
  return {
    schema: "dmb_world_graph_object_projection_v1" as const,
    found: true,
    completeness: {
      status,
      reason: status === "partial" ? "relationships_truncated" : null,
      truncatedFields: status === "partial" ? ["relationships"] : [],
    },
    snapshot: session23WorldGraphRecapFixture.snapshot,
    requestedNodeId: "pc_caelynn",
    resolvedNodeId: "pc_caelynn",
    node: caelynn,
    relatedNodes: [],
    semanticFingerprint: "fp-test",
  };
}

describe("ResolvedGraphObjectProjection partial completeness", () => {
  beforeEach(() => {
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockReset();
  });

  it("does not treat a partial object as ordinary ready", async () => {
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue(completeObject("partial"));

    const { container } = render(
      <ResolvedGraphObjectProjection resolution={resolvedCaelynn()} originSurface="plan" />,
    );

    expect(await screen.findByTestId("complete-object-partial-warning")).toHaveTextContent(
      /Partial World object: truncated relationships/i,
    );
    expect(container.querySelector("[data-complete-object-status='partial']")).toBeTruthy();
    expect(container.querySelector("[data-complete-object-status='ready']")).toBeNull();
    expect(screen.getByText("Caelynn")).toBeInTheDocument();
  });

  it("keeps complete objects as ready without a partial warning", async () => {
    vi.mocked(liveApi.postWorldGraphCompleteObject).mockResolvedValue(completeObject("complete"));

    const { container } = render(
      <ResolvedGraphObjectProjection resolution={resolvedCaelynn()} originSurface="plan" />,
    );

    await waitFor(() => {
      expect(container.querySelector("[data-complete-object-status='ready']")).toBeTruthy();
    });
    expect(screen.queryByTestId("complete-object-partial-warning")).not.toBeInTheDocument();
  });
});
