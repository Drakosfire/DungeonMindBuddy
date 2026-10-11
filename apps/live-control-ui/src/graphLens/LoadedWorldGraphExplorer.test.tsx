import { fireEvent, render, screen, within } from "@testing-library/react";
import { beforeAll, describe, expect, it, vi } from "vitest";
import type { WorldGraphProjection, WorldGraphProjectionNodeView } from "../api/types";
import { LoadedGraphBrowser, LoadedWorldGraphExplorer } from "./LoadedWorldGraphExplorer";

const state = vi.hoisted(() => ({ world: { kind: "managed", worldId: "elderwyld", name: "Elderwyld" }, graph: null as any }));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({ useSelectedWorld: () => state.world }));
vi.mock("./useWorldGraphLensProjection", () => ({ useOptionalWorldGraphLensProjection: () => state.graph }));
beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
});
const node = (id: string, label: string): WorldGraphProjectionNodeView => ({
  nodeId: id, label, kind: "person", role: "NPC", aliases: [], sourceDomains: ["Session 28"], summary: `${label} guards the warehouse.`,
  anchoredToFocusSession: false, evidenceBadges: [], adjacency: [], suggestedExpansions: [], evidenceRefIds: [], sourceArtifactIds: [],
});
const projection: WorldGraphProjection = {
  schema: "dmb_world_graph_projection_v1",
  snapshot: { worldId: "native-world", campaignId: "", revisionId: "revision-1", headRevisionId: "revision-1", isHead: true, focus: { sessionId: null }, admissibility: "gm", scopeMode: "world" },
  summary: { nodeCount: 2, relationshipCount: 1, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: true },
  nodes: [{ ...node("lysandra", "Lysandra"), aliases: ["Ironveil"], adjacency: [{ edgeId: "edge-1", nodeId: "brin", label: "Brin", kind: "person", predicate: "works with", direction: "outgoing", anchoredToFocusSession: false, sourceDomains: [], evidenceRefIds: [], sessionIds: [] }] }, node("brin", "Brin")],
  relationships: [], attributes: [], evidence: [], sourceArtifacts: [], diagnostics: [],
};

describe("loaded World graph inspection", () => {
  it("searches aliases and navigates loaded connections without a fetch", () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    render(<LoadedGraphBrowser worldName="Elderwyld" projection={projection} />);
    fireEvent.click(screen.getByRole("button", { name: "Explore loaded graph" }));
    expect(screen.getByRole("dialog", { name: "Elderwyld loaded graph" })).toBeVisible();
    expect(screen.getByText(/projection is truncated/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Find a node"), { target: { value: "Ironveil" } });
    fireEvent.click(screen.getByRole("button", { name: "Lysandra person" }));
    const detail = screen.getByRole("article", { name: "Selected graph node" });
    expect(detail).toHaveTextContent("Lysandra guards the warehouse.");
    fireEvent.click(within(detail).getByRole("button", { name: "Brin" }));
    expect(detail).toHaveTextContent("Brin guards the warehouse.");
    fireEvent.click(screen.getByRole("button", { name: "Close graph" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Explore loaded graph" })).toHaveFocus();
    expect(fetchSpy).not.toHaveBeenCalled();
    fetchSpy.mockRestore();
  });

  it("removes stale graph content and gates exploration when the projection is unavailable", () => {
    const view = render(<LoadedGraphBrowser worldName="Elderwyld" projection={projection} />);
    fireEvent.click(screen.getByRole("button", { name: "Explore loaded graph" }));
    fireEvent.click(screen.getByRole("button", { name: "Lysandra person" }));
    view.rerender(<LoadedGraphBrowser worldName="Elderwyld" projection={null} />);
    expect(screen.getByRole("button", { name: "Explore loaded graph" })).toBeDisabled();
    expect(screen.queryByText("Lysandra guards the warehouse.")).not.toBeInTheDocument();
    expect(screen.getByText(/previous projection is no longer shown/)).toBeInTheDocument();
  });

  it("resets the inspector when the managed World switches", () => {
    state.graph = { projectionState: "ready", projection };
    const view = render(<LoadedWorldGraphExplorer />);
    fireEvent.click(screen.getByRole("button", { name: "Explore loaded graph" }));
    state.world = { kind: "managed", worldId: "sheep", name: "Sheep" };
    state.graph = { projectionState: "loading", projection: null };
    view.rerender(<LoadedWorldGraphExplorer />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Explore loaded graph" })).toBeDisabled();
  });
});
