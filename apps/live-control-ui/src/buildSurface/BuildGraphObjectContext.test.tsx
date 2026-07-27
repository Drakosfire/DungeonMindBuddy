import { existsSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { BuildSurfacePage } from "./BuildSurfacePage";

const buildSurfaceDir = path.dirname(fileURLToPath(import.meta.url));

describe("BuildGraphObjectContext (PR380B target module)", () => {
  it("production module file is absent on current main", () => {
    expect(existsSync(path.join(buildSurfaceDir, "BuildGraphObjectContext.tsx"))).toBe(false);
  });

  it("current Build route has no graphNodeId/graphRevision query contract", () => {
    window.history.replaceState({}, "", "/build");
    const params = new URLSearchParams(window.location.search);
    expect(params.get("graphNodeId")).toBeNull();
    expect(params.get("graphRevision")).toBeNull();
    expect(params.get("campaign")).toBeNull();
  });

  it("target URL handoff shape is pointer-only (characterization contract)", () => {
    const handoff =
      "/build?campaign=longmont-c2&graphNodeId=pc_caelynn&graphRevision=wg-rev-longmont-c2-session-23-recap-v1";
    const url = new URL(handoff, "http://localhost");
    expect(url.searchParams.get("campaign")).toBe("longmont-c2");
    expect(url.searchParams.get("graphNodeId")).toBe("pc_caelynn");
    expect(url.searchParams.get("graphRevision")).toBe("wg-rev-longmont-c2-session-23-recap-v1");
    expect(url.searchParams.get("graphRunManifestPath")).toBeNull();
    expect(url.searchParams.get("previewUnionStorePath")).toBeNull();
  });

  it("BuildSurfacePage still renders without graph-object context module", () => {
    render(
      <AgentInteractionProvider>
        <BuildSurfacePage />
      </AgentInteractionProvider>,
    );
    expect(screen.getByTestId("build-new-source-form")).toBeInTheDocument();
    expect(screen.queryByTestId("build-graph-object-context")).not.toBeInTheDocument();
  });
});
