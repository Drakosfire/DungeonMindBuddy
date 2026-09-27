import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getPlayActiveRun, getPlayRun, listPlayRuns, putPlayActiveRun } from "../api/liveApi";
import { PlaySurfacePage } from "./PlaySurfacePage";

vi.mock("../api/liveApi", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/liveApi")>()),
  getPlayActiveRun: vi.fn(),
  getPlayRun: vi.fn(),
  getPlayRunReferenceManifest: vi.fn(),
  getCommittedWorkspaceRevision: vi.fn(),
  listPlayRuns: vi.fn(),
  putPlayActiveRun: vi.fn(),
}));
vi.mock("../selectedWorld/SelectedWorldContext", () => ({
  useSelectedWorld: () => ({ kind: "managed", worldId: "world-b", name: "World B", documentId: null }),
}));
vi.mock("../chrome/AppChrome", () => ({ AppChrome: ({ children }: { children: React.ReactNode }) => <div>{children}</div> }));
vi.mock("../agentInteraction/usePublishAgentSurfaceContext", () => ({ usePublishAgentSurfaceContext: () => undefined }));
vi.mock("../agentInteraction/usePublishSurfaceInteraction", () => ({ usePublishSurfaceInteraction: () => undefined }));
vi.mock("../graphLens", () => ({ useOptionalWorldGraphLens: () => null }));
vi.mock("./StartRunPanel", () => ({ StartRunPanel: () => <div>Start Run</div> }));

const runId = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

describe("Play selected-World admission", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listPlayRuns).mockResolvedValue({ records: [] } as Awaited<ReturnType<typeof listPlayRuns>>);
    window.history.replaceState({}, "", `/play?world=world-b&run=${runId}`);
  });

  it("rejects a foreign exact Run before native-ready hydration or active-pointer writes", async () => {
    vi.mocked(getPlayRun).mockResolvedValue({
      run_id: runId,
      campaign_id: "world-a",
    } as Awaited<ReturnType<typeof getPlayRun>>);
    render(<PlaySurfacePage />);
    expect(await screen.findByText(`Run ${runId} does not belong to World world-b.`)).toBeInTheDocument();
    expect(getPlayRun).toHaveBeenCalledExactlyOnceWith(runId);
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });

  it("does not follow a global active Run from another World", async () => {
    window.history.replaceState({}, "", "/play?world=world-b");
    vi.mocked(getPlayActiveRun).mockResolvedValue({ run_id: runId } as Awaited<ReturnType<typeof getPlayActiveRun>>);
    vi.mocked(getPlayRun).mockResolvedValue({
      run_id: runId,
      campaign_id: "world-a",
    } as Awaited<ReturnType<typeof getPlayRun>>);
    render(<PlaySurfacePage />);
    await waitFor(() => expect(screen.getByTestId("play-run-chooser")).toBeInTheDocument());
    expect(window.location.search).toBe("?world=world-b");
    expect(putPlayActiveRun).not.toHaveBeenCalled();
  });
});
