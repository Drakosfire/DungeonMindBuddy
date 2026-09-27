import { render, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { WorldContainerRecord } from "../api/types";
import { WorldGraphLensProvider } from "../graphLens/WorldGraphLensContext";
import { WorldGraphLensProjectionProvider, useOptionalWorldGraphLensProjection } from "../graphLens/useWorldGraphLensProjection";
import { SelectedWorldProvider, useSelectedWorld } from "./SelectedWorldContext";

const world: WorldContainerRecord = {
  schema_version: "dmb_world_container_record_v1",
  world_id: "of-conks-cons-demo",
  name: "Of Conks",
  source_root_relpath: "corpus/of-conks-cons-demo-markdown",
  created_at: "2026-01-01T00:00:00Z",
};

function GraphShell() {
  const selected = useSelectedWorld();
  if (selected.kind !== "managed") return <span>{selected.kind}</span>;
  return (
    <WorldGraphLensProvider planCampaignId="longmont-c2" managedWorldId={selected.worldId}>
      <WorldGraphLensProjectionProvider defaultCampaignId="longmont-c2">
        <GraphState />
      </WorldGraphLensProjectionProvider>
    </WorldGraphLensProvider>
  );
}

function GraphState() {
  const graph = useOptionalWorldGraphLensProjection();
  return <span data-testid="managed-graph-state">{graph?.projectionState ?? "missing"}</span>;
}

afterEach(() => vi.restoreAllMocks());

describe("managed World graph integration", () => {
  it("projects only the verified managed World and never loads C2 bundles", async () => {
    vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [world],
    });
    const bundle = vi.spyOn(liveApi, "getSourceBundle").mockRejectedValue(new Error("must not load"));
    const project = vi.spyOn(liveApi, "postWorldGraphProjection").mockRejectedValue(
      new liveApi.LiveApiError("no published head", 404, { code: "world_graph_unavailable" }),
    );
    const view = render(
      <SelectedWorldProvider locationSnapshot={`/plan?world=${world.world_id}`}>
        <GraphShell />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(project).toHaveBeenCalled());
    await waitFor(() => expect(view.getByTestId("managed-graph-state")).toHaveTextContent("unavailable"));
    expect(project.mock.calls[0]?.[0]).toMatchObject({
      worldId: world.world_id,
      campaignId: world.world_id,
      scopeMode: "world",
      focus: { kind: "none", sessionId: null },
    });
    expect(bundle).not.toHaveBeenCalled();
    view.rerender(
      <SelectedWorldProvider locationSnapshot="/plan?world=unknown-world">
        <GraphShell />
      </SelectedWorldProvider>,
    );
    await waitFor(() => expect(view.queryByText("error")).toBeTruthy());
    expect(project).toHaveBeenCalledTimes(1);
  });
});
