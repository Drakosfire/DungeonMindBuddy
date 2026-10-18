import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ActionTerminalDiagnostic } from "./ActionTerminalDiagnostic";
import { getPlanActionTerminalDiagnostic } from "../../api/liveApi";
import type { ActionTerminalDiagnosticRead } from "../../api/types";
vi.mock("../../api/liveApi", () => ({ getPlanActionTerminalDiagnostic: vi.fn() }));
const read = vi.mocked(getPlanActionTerminalDiagnostic);
const missing: ActionTerminalDiagnosticRead = { schema: "dmb_plan_action_terminal_diagnostic_read_v1",
  world_id: "world", action_id: "action", status: "indeterminate", availability: "unavailable", diagnostic: null };
function open() { const details = screen.getByText("Failure details").closest("details")!; details.open = true; fireEvent(details, new Event("toggle")); }
beforeEach(() => { read.mockReset(); read.mockResolvedValue(missing); });
it("reads only on expansion and preserves honest historical absence", async () => {
  render(<ActionTerminalDiagnostic worldId="world" actionId="action" />);
  expect(read).not.toHaveBeenCalled(); open();
  await screen.findByText(/No valid terminal report/);
  expect(read).toHaveBeenCalledWith("world", "action", expect.any(AbortSignal));
  expect(screen.getByText(/uncertain outcome remains uncertain/)).toBeInTheDocument();
});
it("aborts and clears on owner changes and ignores late replies", async () => {
  let resolve!: (value: ActionTerminalDiagnosticRead) => void;
  read.mockImplementation(() => new Promise(done => { resolve = done; }));
  const view = render(<ActionTerminalDiagnostic worldId="world" actionId="action" />); open();
  await screen.findByRole("status");
  const signal = read.mock.calls[0][2]!;
  view.rerender(<ActionTerminalDiagnostic worldId="other" actionId="other" />);
  expect(signal.aborted).toBe(true);
  await act(async () => resolve(missing));
  expect(screen.queryByText(/No valid terminal report/)).not.toBeInTheDocument();
  expect(read).toHaveBeenCalledTimes(1);
});
it("rejects foreign binding", async () => {
  read.mockResolvedValue({ ...missing, action_id: "foreign" });
  render(<ActionTerminalDiagnostic worldId="world" actionId="action" />); open();
  await screen.findByRole("alert");
});
