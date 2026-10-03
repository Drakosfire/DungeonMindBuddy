import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getExtractionRun, getPlanView } from "../api/liveApi";
import type { SelectedWorldState } from "../selectedWorld/SelectedWorldContext";
import { mockPlanView } from "../test/fixtures";
import { MemoryIngestPage } from "./MemoryIngestPage";

vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getPlanView: vi.fn(),
  getExtractionRun: vi.fn(),
}));
const selection = vi.hoisted(() => ({ current: { kind: "managed", worldId: "world-b", name: "World B", documentId: null } as SelectedWorldState }));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({ useSelectedWorld: () => selection.current }));
vi.mock("../agentInteraction/usePublishAgentSurfaceContext", () => ({ usePublishAgentSurfaceContext: () => undefined }));
vi.mock("../chrome/AppChrome", () => ({ AppChrome: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("./useIngestRunCatalogInformation", () => ({
  useIngestRunCatalogInformation: () => ({ channel: {}, refresh: () => undefined }),
}));
vi.mock("../planSurface/graphReviewWorkbench/GraphReviewWorkbenchModule", () => ({
  GraphReviewWorkbenchModule: () => <div data-testid="exact-graph-review" />,
}));

const planView = {
  ...mockPlanView,
  campaign_id: "world-b",
  world_id: "world-b",
  session: 0,
};

describe("managed-World Ingest boundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    selection.current = { kind: "managed", worldId: "world-b", name: "World B", documentId: null };
    vi.mocked(getPlanView).mockResolvedValue(planView);
    window.history.replaceState({}, "", "/ingest?world=world-b");
  });

  it("requires a World before any legacy or exact-run reads", async () => {
    selection.current = { kind: "legacy" };
    window.history.replaceState({}, "", "/ingest?campaign=longmont-c2&session=session-22");
    render(<MemoryIngestPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("No World selected.");
    expect(screen.getByRole("alert")).toHaveTextContent("World picker");
    expect(getPlanView).not.toHaveBeenCalled();
    expect(getExtractionRun).not.toHaveBeenCalled();
    expect(screen.queryByTestId("exact-graph-review")).not.toBeInTheDocument();
  });

  it("waits for World verification without reading legacy context", () => {
    selection.current = { kind: "loading", requestedWorldId: "world-b" };
    render(<MemoryIngestPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading World selection");
    expect(getPlanView).not.toHaveBeenCalled();
  });

  it("shows a failed World selection without reading legacy context", () => {
    selection.current = { kind: "error", message: "Unknown managed World: world-b" };
    render(<MemoryIngestPage />);
    expect(screen.getByRole("alert")).toHaveTextContent("Unknown managed World");
    expect(getPlanView).not.toHaveBeenCalled();
  });

  it("does not mount the C1/C2 recap browser on a bare managed landing", async () => {
    render(<MemoryIngestPage />);
    expect(await screen.findByText("No exact extraction run is selected for this World.")).toBeInTheDocument();
    expect(getPlanView).toHaveBeenCalledWith("world-b");
    expect(screen.queryByTestId("exact-graph-review")).not.toBeInTheDocument();
  });

  it("blocks a foreign exact run before mounting the review controller", async () => {
    window.history.replaceState({}, "", "/ingest?world=world-b&extractionRunId=run-a");
    vi.mocked(getExtractionRun).mockResolvedValue({
      run_id: "run-a",
      campaign_id: "world-a",
    } as Awaited<ReturnType<typeof getExtractionRun>>);
    render(<MemoryIngestPage />);
    expect(await screen.findByText("Extraction Run does not belong to World world-b.")).toBeInTheDocument();
    expect(screen.queryByTestId("exact-graph-review")).not.toBeInTheDocument();
    expect(getPlanView).not.toHaveBeenCalled();
  });

  it("admits a matching exact run to the existing review controller", async () => {
    window.history.replaceState({}, "", "/ingest?world=world-b&extractionRunId=run-b");
    vi.mocked(getExtractionRun).mockResolvedValue({
      run_id: "run-b",
      campaign_id: "world-b",
    } as Awaited<ReturnType<typeof getExtractionRun>>);
    render(<MemoryIngestPage />);
    expect(await screen.findByTestId("exact-graph-review")).toBeInTheDocument();
    expect(getPlanView).toHaveBeenCalledWith("world-b");
  });
});
