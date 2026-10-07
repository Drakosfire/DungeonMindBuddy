import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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
  GraphReviewWorkbenchModule: ({
    sourceReviewOnly,
    locationSearch,
  }: { sourceReviewOnly?: boolean; locationSearch?: string }) => (
    <div
      data-testid="exact-graph-review"
      data-source-review-only={sourceReviewOnly ? "true" : "false"}
      data-location-search={locationSearch}
    />
  ),
}));

vi.mock("../modules/IngestionModule", () => ({
  IngestionModule: ({ campaignId, session }: { campaignId: string; session: number }) =>
    <div data-testid="recap-workbench">{campaignId} · {session}</div>,
}));

const planView = {
  ...mockPlanView,
  campaign_id: "world-b",
  world_id: "world-b",
  session: 0,
};

function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise;
  });
  return { promise, resolve };
}

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

  it.each(["", "&campaign=longmont-c2", "&campaign=longmont-c1"])("restores the Elderwyld recap entry with campaign URL %s", async (query) => {
    selection.current = { kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null };
    vi.mocked(getPlanView).mockResolvedValue({ ...planView, world_id: "elderwyld", campaign_id: "elderwyld" });
    window.history.replaceState({}, "", `/ingest?world=elderwyld${query}`);
    render(<MemoryIngestPage />);
    expect(await screen.findByTestId("recap-workbench")).toHaveTextContent("longmont-c2 · 29");
    expect(screen.queryByTestId("exact-graph-review")).not.toBeInTheDocument();
  });

  it("blocks a foreign exact run before mounting the review controller", async () => {
    window.history.replaceState({}, "", "/ingest?world=world-b&extractionRunId=run-a");
    vi.mocked(getExtractionRun).mockResolvedValue({
      run_id: "run-a",
      source_domain: "worldbuilding",
      campaign_id: "world-a",
    } as Awaited<ReturnType<typeof getExtractionRun>>);
    render(<MemoryIngestPage />);
    expect(await screen.findByText("Extraction Run does not belong to World world-b.")).toBeInTheDocument();
    expect(screen.queryByTestId("exact-graph-review")).not.toBeInTheDocument();
    expect(getPlanView).not.toHaveBeenCalled();
  });

  it("rejects a plan-view basis resolved for a different managed World", async () => {
    vi.mocked(getPlanView).mockResolvedValue({
      ...planView,
      world_id: "world-a",
      campaign_id: "world-b",
    });
    render(<MemoryIngestPage />);
    expect(await screen.findByText("Ingest context does not match selected World world-b.")).toBeInTheDocument();
    expect(screen.queryByTestId("exact-graph-review")).not.toBeInTheDocument();
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

  it("opens an exact recap as read-only source review with the selected World shown as target", async () => {
    const user = userEvent.setup();
    selection.current = { kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null };
    vi.mocked(getPlanView).mockResolvedValue({
      ...planView,
      world_id: "elderwyld",
      campaign_id: "longmont-c2",
    });
    vi.mocked(getExtractionRun).mockResolvedValue({
      run_id: "s27-run",
      source_domain: "recap",
      source_artifact_id: "s27-source",
      campaign_id: "longmont-c2",
      session_id: "session-27",
    } as Awaited<ReturnType<typeof getExtractionRun>>);
    window.history.replaceState(
      {},
      "",
      "/ingest?world=elderwyld&campaign=longmont-c2&extractionRunId=s27-run",
    );

    render(<MemoryIngestPage />);

    const sourceScope = await screen.findByTestId("source-review-scope");
    expect(sourceScope).toHaveTextContent("longmont-c2");
    expect(screen.getByTestId("source-review-scope")).toHaveTextContent("session-27");
    expect(screen.getByTestId("source-review-scope")).toHaveTextContent("elderwyld");
    const artifactDetails = screen.getByText("Show exact artifact ID").closest("details");
    expect(artifactDetails).not.toHaveAttribute("open");
    expect(screen.getByText("s27-source")).not.toBeVisible();
    await user.click(screen.getByText("Show exact artifact ID"));
    expect(artifactDetails).toHaveAttribute("open");
    expect(screen.getByText("s27-source")).toBeVisible();
    expect(screen.getByTestId("exact-graph-review")).toHaveAttribute(
      "data-source-review-only",
      "true",
    );
    expect(screen.getByText(/does not import it or associate it/)).toBeInTheDocument();
  });

  it("tracks same-World handoff changes and ignores stale exact-run loads", async () => {
    selection.current = { kind: "managed", worldId: "elderwyld", name: "Elderwyld", documentId: null };
    vi.mocked(getPlanView).mockResolvedValue({
      ...planView,
      world_id: "elderwyld",
      campaign_id: "elderwyld",
    });
    const runA = deferred<Awaited<ReturnType<typeof getExtractionRun>>>();
    const runB = deferred<Awaited<ReturnType<typeof getExtractionRun>>>();
    const runC = deferred<Awaited<ReturnType<typeof getExtractionRun>>>();
    vi.mocked(getExtractionRun).mockImplementation((runId) => {
      if (runId === "run-a") return runA.promise;
      if (runId === "run-b") return runB.promise;
      if (runId === "run-c") return runC.promise;
      throw new Error(`unexpected run ${runId}`);
    });
    window.history.replaceState({}, "", "/ingest?world=elderwyld");
    render(<MemoryIngestPage />);
    expect(await screen.findByTestId("recap-workbench")).toBeInTheDocument();

    const navigate = async (runId: string) => {
      await act(async () => {
        window.history.replaceState({}, "", `/ingest?world=elderwyld&extractionRunId=${runId}`);
        window.dispatchEvent(new PopStateEvent("popstate"));
      });
      await waitFor(() => expect(getExtractionRun).toHaveBeenCalledWith(runId));
    };

    await navigate("run-a");
    await navigate("run-b");
    await act(async () => {
      runB.resolve({
        run_id: "run-b",
        source_domain: "worldbuilding",
        source_artifact_id: "source-b",
        campaign_id: "elderwyld",
      } as Awaited<ReturnType<typeof getExtractionRun>>);
      await runB.promise;
    });
    await waitFor(() => {
      expect(screen.getByTestId("exact-graph-review")).toHaveAttribute(
        "data-source-review-only",
        "false",
      );
      expect(screen.getByTestId("exact-graph-review")).toHaveAttribute(
        "data-location-search",
        "?world=elderwyld&extractionRunId=run-b",
      );
    });

    await act(async () => {
      runA.resolve({
        run_id: "run-a",
        source_domain: "recap",
        source_artifact_id: "source-a",
        campaign_id: "longmont-c2",
        session_id: "session-27",
      } as Awaited<ReturnType<typeof getExtractionRun>>);
      await runA.promise;
    });
    expect(screen.queryByTestId("source-review-scope")).not.toBeInTheDocument();
    expect(screen.getByTestId("exact-graph-review")).toHaveAttribute(
      "data-source-review-only",
      "false",
    );

    await navigate("run-c");
    await act(async () => {
      runC.resolve({
        run_id: "run-c",
        source_domain: "recap",
        source_artifact_id: "source-c",
        campaign_id: "longmont-c2",
        session_id: "session-27",
      } as Awaited<ReturnType<typeof getExtractionRun>>);
      await runC.promise;
    });
    expect(await screen.findByTestId("source-review-scope")).toHaveTextContent("source-c");
    expect(screen.getByTestId("exact-graph-review")).toHaveAttribute(
      "data-source-review-only",
      "true",
    );
  });
});
