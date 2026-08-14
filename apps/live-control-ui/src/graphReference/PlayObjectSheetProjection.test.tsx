import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { buildGraphObjectCardFromNodeView } from "../graphObjectCard";
import {
  PlayObjectSheetProjection,
  shouldRenderPlayObjectSheet,
} from "./PlayObjectSheetProjection";
import type { GraphReferenceResolution } from "./types";

function morwinResolution(): Extract<GraphReferenceResolution, { kind: "resolved_graph" }> {
  return {
    kind: "resolved_graph",
    locator: "dmb-node:npc:morwin-blackwell",
    reference: null,
    graphNodeId: "npc:morwin-blackwell",
    graphObject: buildGraphObjectCardFromNodeView({
      node_id: "npc:morwin-blackwell",
      label: "Morwin Blackwell",
      kind: "npc",
      role: "npc",
      aliases: ["Morwin"],
      source_domains: ["worldbuilding"],
      evidence_badges: [],
      adjacency: [],
      anchored_to_focus_session: true,
      summary: null,
    }),
    graphScope: null,
    projectionState: "ready",
    message: null,
  };
}

describe("PlayObjectSheetProjection", () => {
  it("renders Morwin play sections and Saladin connected chip", () => {
    const resolution = morwinResolution();
    const onSelect = vi.fn();
    render(
      <PlayObjectSheetProjection
        resolution={resolution}
        model={resolution.graphObject}
        onSelectRelationship={onSelect}
      />,
    );

    expect(screen.getByTestId("play-object-sheet")).toBeInTheDocument();
    expect(screen.getByText(/At the table/i)).toBeInTheDocument();
    expect(screen.getAllByText(/eyes and ears/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText(/Attitude/i)).toBeInTheDocument();
    expect(screen.getByText(/Offers & hooks/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open Saladin/i })).toBeInTheDocument();
    expect(screen.getByTestId("play-map-overlay")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Open 1\. The Shacks/i })).toBeInTheDocument();
    expect(screen.getByTestId("play-object-sheet-provenance")).toHaveTextContent(/Area 2/i);
  });

  it("renders Maglubiyet Rules now and Items tool link", () => {
    const resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> = {
      ...morwinResolution(),
      locator: "dmb-node:item:maglubiyets-statue",
      graphNodeId: "item:maglubiyets-statue",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "item:maglubiyets-statue",
        label: "Maglubiyet’s Statue",
        kind: "item",
        role: "item",
        aliases: [],
        source_domains: ["worldbuilding"],
        evidence_badges: [],
        adjacency: [],
        anchored_to_focus_session: true,
        summary: null,
      }),
    };
    render(
      <PlayObjectSheetProjection resolution={resolution} model={resolution.graphObject} />,
    );
    expect(screen.getByTestId("play-object-sheet-rules")).toHaveTextContent(/3 charges/i);
    expect(screen.getByTestId("play-object-sheet-rules")).toHaveTextContent(/DC 15/i);
    expect(screen.getByTestId("play-object-sheet-tools")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open full text on Items/i })).toHaveAttribute(
      "href",
      expect.stringContaining("/play/items"),
    );
  });

  it("renders Shacks firefighting RULES without Build", () => {
    const resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> = {
      ...morwinResolution(),
      locator: "dmb-node:location:the-shacks",
      graphNodeId: "location:the-shacks",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "location:the-shacks",
        label: "The Shacks",
        kind: "location",
        role: "location",
        aliases: [],
        source_domains: ["worldbuilding"],
        evidence_badges: [],
        adjacency: [],
        anchored_to_focus_session: true,
        summary: null,
      }),
    };
    render(
      <PlayObjectSheetProjection resolution={resolution} model={resolution.graphObject} />,
    );
    expect(screen.getByTestId("play-object-sheet-rules")).toHaveTextContent(/Firefighting/i);
    expect(screen.getByTestId("play-object-sheet-rules")).toHaveTextContent(/DC 12/i);
  });

  it("renders Marrow chamber arrival text", () => {
    const resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> = {
      ...morwinResolution(),
      locator: "dmb-node:location:the-marrow",
      graphNodeId: "location:the-marrow",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "location:the-marrow",
        label: "The Marrow",
        kind: "location",
        role: "location",
        aliases: [],
        source_domains: ["worldbuilding"],
        evidence_badges: [],
        adjacency: [],
        anchored_to_focus_session: true,
        summary: null,
      }),
    };
    render(
      <PlayObjectSheetProjection resolution={resolution} model={resolution.graphObject} />,
    );
    expect(screen.getAllByText(/sickly green light/i).length).toBeGreaterThanOrEqual(1);
    expect(screen.getByTestId("play-object-sheet-rules")).toHaveTextContent(/200 gp/i);
    expect(screen.getByTestId("play-object-sheet-source")).toHaveTextContent(/helix/i);
  });

  it("renders Nar full module source and provenance", () => {
    const resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> = {
      ...morwinResolution(),
      locator: "dmb-node:npc:nar-granitetooth",
      graphNodeId: "npc:nar-granitetooth",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "npc:nar-granitetooth",
        label: "Nar Granitetooth",
        kind: "npc",
        role: "npc",
        aliases: [],
        source_domains: ["worldbuilding"],
        evidence_badges: [],
        adjacency: [],
        anchored_to_focus_session: true,
        summary: null,
      }),
    };
    render(
      <PlayObjectSheetProjection resolution={resolution} model={resolution.graphObject} />,
    );
    const source = screen.getByTestId("play-object-sheet-source");
    expect(source).toHaveTextContent(/slit Sarni/i);
    expect(source).toHaveTextContent(/wandering life/i);
    expect(source).toHaveTextContent(/Sharindlar/i);
    const provenance = screen.getByTestId("play-object-sheet-provenance");
    expect(provenance).toHaveTextContent(/Area 1: The Shacks/i);
  });

  it("renders Shacks door-dump source on location sheet", () => {
    const resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> = {
      ...morwinResolution(),
      locator: "dmb-node:location:the-shacks",
      graphNodeId: "location:the-shacks",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "location:the-shacks",
        label: "The Shacks",
        kind: "location",
        role: "location",
        aliases: [],
        source_domains: ["worldbuilding"],
        evidence_badges: [],
        adjacency: [],
        anchored_to_focus_session: true,
        summary: null,
      }),
    };
    render(
      <PlayObjectSheetProjection resolution={resolution} model={resolution.graphObject} />,
    );
    expect(screen.getByTestId("play-object-sheet-source")).toHaveTextContent(
      /noggin-shaped nose/i,
    );
  });

  it("renders Maglubiyet Appendix B flavor on item sheet", () => {
    const resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> = {
      ...morwinResolution(),
      locator: "dmb-node:item:maglubiyets-statue",
      graphNodeId: "item:maglubiyets-statue",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "item:maglubiyets-statue",
        label: "Maglubiyet’s Statue",
        kind: "item",
        role: "item",
        aliases: [],
        source_domains: ["worldbuilding"],
        evidence_badges: [],
        adjacency: [],
        anchored_to_focus_session: true,
        summary: null,
      }),
    };
    render(
      <PlayObjectSheetProjection resolution={resolution} model={resolution.graphObject} />,
    );
    expect(screen.getByTestId("play-object-sheet-source")).toHaveTextContent(
      /blood will not dry/i,
    );
  });

  it("links Open in Play to Beats with beat and node focus", () => {
    const resolution: Extract<GraphReferenceResolution, { kind: "resolved_graph" }> = {
      ...morwinResolution(),
      locator: "dmb-node:location:the-shacks",
      graphNodeId: "location:the-shacks",
      graphObject: buildGraphObjectCardFromNodeView({
        node_id: "location:the-shacks",
        label: "The Shacks",
        kind: "location",
        role: "location",
        aliases: [],
        source_domains: ["worldbuilding"],
        evidence_badges: [],
        adjacency: [],
        anchored_to_focus_session: true,
        summary: null,
      }),
    };
    render(
      <PlayObjectSheetProjection resolution={resolution} model={resolution.graphObject} />,
    );
    const link = screen.getByTestId("play-object-sheet-open-play-link");
    expect(link).toHaveAttribute("href", expect.stringContaining("/play/beats"));
    expect(link).toHaveAttribute("href", expect.stringContaining("beat=shacks-arrival"));
    expect(link).toHaveAttribute("href", expect.stringContaining("node=location"));
  });

  it("shouldRenderPlayObjectSheet is true only for bridged nodes", () => {
    expect(shouldRenderPlayObjectSheet(morwinResolution())).toBe(true);
    const other = {
      ...morwinResolution(),
      graphNodeId: "npc:stranger",
      locator: "dmb-node:npc:stranger",
    };
    expect(shouldRenderPlayObjectSheet(other)).toBe(false);
  });
});
