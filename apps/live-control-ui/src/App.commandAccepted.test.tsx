import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "./api/liveApi";
import { makeWriteResult, mockCatalog, mockLayout, mockPlanView, mockState } from "./test/fixtures";
import { App } from "./App";

vi.mock("./api/liveApi");
vi.mock("./surface/SurfaceShell", () => ({
  SurfaceShell: () => <div data-testid="surface-shell-mock">Surface shell</div>,
}));
vi.mock("./surface/InspectorPane", () => ({
  InspectorPane: ({
    onCommandAccepted,
  }: {
    onCommandAccepted?: (result: ReturnType<typeof makeWriteResult>) => Promise<void> | void;
  }) => (
    <button
      type="button"
      onClick={() => {
        void onCommandAccepted?.(makeWriteResult());
      }}
    >
      Trigger command accepted
    </button>
  ),
}));

describe("App command accepted callback", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(liveApi.getSurface).mockResolvedValue({
      catalog: mockCatalog,
      layout: mockLayout,
      state: mockState,
    });
    vi.mocked(liveApi.getEvents).mockResolvedValue({ events: [] });
    vi.mocked(liveApi.getJobs).mockResolvedValue({ jobs: [] });
    vi.mocked(liveApi.getPlanView).mockResolvedValue(mockPlanView);
  });

  it("refreshes app data after accepted command callback", async () => {
    const user = userEvent.setup();
    render(<App />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: "Trigger command accepted" })).toBeInTheDocument();
    });
    const surfaceCallsBefore = vi.mocked(liveApi.getSurface).mock.calls.length;

    await user.click(screen.getByRole("button", { name: "Trigger command accepted" }));

    await waitFor(() => {
      expect(vi.mocked(liveApi.getSurface).mock.calls.length).toBeGreaterThan(surfaceCallsBefore);
    });
  });
});
