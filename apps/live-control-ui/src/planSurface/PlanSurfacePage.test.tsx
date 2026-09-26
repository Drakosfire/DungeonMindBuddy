import { render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { mockPlanView } from "../test/fixtures";
import { PlanSurfacePage } from "./PlanSurfacePage";

vi.mock("../chrome/AppChrome", () => ({
  AppChrome: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("./PlanSurfaceShell", () => ({
  PlanSurfaceShell: ({ planView }: { planView: { campaign_id: string } }) => (
    <div data-testid="plan-page-campaign">{planView.campaign_id}</div>
  ),
}));

const worldId = "of-conks-cons-demo";

function VerifiedPlanPage() {
  const selected = useSelectedWorld();
  return selected.kind === "managed" ? <PlanSurfacePage /> : <span>{selected.kind}</span>;
}

afterEach(() => vi.restoreAllMocks());

it("rejects a stale C2 Plan projection under an exact managed World selection", async () => {
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{
      schema_version: "dmb_world_container_record_v1",
      world_id: worldId,
      name: "Of Conks",
      source_root_relpath: "corpus/of-conks-cons-demo-markdown",
      created_at: "2026-01-01T00:00:00Z",
    }],
  });
  const getPlanView = vi.spyOn(liveApi, "getPlanView").mockResolvedValue(mockPlanView);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await waitFor(() => expect(getPlanView).toHaveBeenCalledWith(worldId));
  expect(await screen.findByText(`Plan context does not match selected World ${worldId}.`)).toBeInTheDocument();
  expect(screen.queryByTestId("plan-page-campaign")).not.toBeInTheDocument();
});
