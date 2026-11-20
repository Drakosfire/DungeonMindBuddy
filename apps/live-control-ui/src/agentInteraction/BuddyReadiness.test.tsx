import { act, fireEvent, render, screen } from "@testing-library/react";
import { expect, it, vi, beforeEach } from "vitest";
import { getBuddyReadiness, type BuddyReadinessResponse } from "../api/liveApi";
import { BuddyReadiness } from "./BuddyReadiness";
vi.mock("../api/liveApi", () => ({getBuddyReadiness: vi.fn()}));
beforeEach(() => vi.resetAllMocks());
const ready = (surface: BuddyReadinessResponse["surface"]): BuddyReadinessResponse => ({schema:"dmb_agent_readiness_v1",surface,world_graph:true,configured:true,issues:[]});
it("checks only when active and on explicit recheck, without promising remote success", async () => {
  vi.mocked(getBuddyReadiness).mockResolvedValue(ready("build"));
  const view = render(<BuddyReadiness active={false} surface="build" worldGraph blockedReason={null} />);
  expect(getBuddyReadiness).not.toHaveBeenCalled();
  view.rerender(<BuddyReadiness active surface="build" worldGraph blockedReason={null} />);
  await screen.findByText("Buddy · configured");
  expect(screen.getByRole("status")).toHaveTextContent("Remote providers can still fail");
  fireEvent.click(screen.getByText("Check readiness"));
  await act(async () => {});
  expect(getBuddyReadiness).toHaveBeenCalledTimes(2);
});
it("ignores stale surface checks and shows pending request blockers", async () => {
  let resolve!: (value: BuddyReadinessResponse) => void;
  vi.mocked(getBuddyReadiness).mockImplementationOnce(() => new Promise(r => {resolve = r;}))
    .mockResolvedValueOnce({...ready("play"), configured:false, issues:["Decision provider is not configured."]});
  const view = render(<BuddyReadiness active surface="build" worldGraph blockedReason={null} />);
  view.rerender(<BuddyReadiness active surface="play" worldGraph blockedReason="Resolve saved request." />);
  await screen.findByText("Resolve saved request.");
  await act(async () => resolve(ready("build")));
  expect(screen.queryByText("Buddy · configured")).not.toBeInTheDocument();
  view.rerender(<BuddyReadiness active surface="play" worldGraph blockedReason={null} />);
  expect(screen.getByText("Buddy · needs attention")).toBeInTheDocument();
  expect(screen.getByRole("status")).toHaveTextContent("Decision provider is not configured.");
});
