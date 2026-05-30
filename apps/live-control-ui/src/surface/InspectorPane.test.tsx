import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import {
  makeCapabilityResponse,
  makeEventArtifact,
  makeRollTableArtifact,
  makeWriteResult,
} from "../test/fixtures";
import { InspectorPane } from "./InspectorPane";
import type { PaneTarget } from "./targetTypes";

vi.mock("../api/liveApi");

const target: PaneTarget = {
  target_type: "roll_table",
  target_id: "T-WX",
  label: "Travel weather table",
  source_status: "authoritative",
  role: "next_roll",
  origin: {
    module_id: "timeline",
    row_id: "beat-day1-weather-front",
  },
};

describe("InspectorPane", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeEventArtifact());
    vi.mocked(liveApi.getCapabilities).mockResolvedValue(makeCapabilityResponse());
    vi.mocked(liveApi.postCommand).mockResolvedValue(makeWriteResult());
  });

  it("renders closed state as hidden/unmounted", () => {
    const { container } = render(<InspectorPane state={{ status: "closed" }} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders open empty state without fetching", () => {
    render(<InspectorPane state={{ status: "open", target: null }} onClose={vi.fn()} />);
    expect(screen.getByText("Inspector")).toBeInTheDocument();
    expect(screen.getByText(/Select a timeline ref or record event to inspect/i)).toBeInTheDocument();
    expect(liveApi.getArtifact).not.toHaveBeenCalled();
    expect(liveApi.getCapabilities).not.toHaveBeenCalled();
  });

  it("renders selected event target with loading then artifact content", async () => {
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeEventArtifact());
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<InspectorPane state={{ status: "open", target: { ...target, target_type: "event" } }} onClose={onClose} />);

    expect(screen.getByText(/Loading artifact/i)).toBeInTheDocument();
    expect(await screen.findByText(/Weather resolved to 16./i)).toBeInTheDocument();
    expect(await screen.findByText(/Future capabilities/i)).toBeInTheDocument();
    expect(screen.getByText(/state token:/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("renders selected roll table target with markdown/metadata", async () => {
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    render(<InspectorPane state={{ status: "open", target }} onClose={vi.fn()} />);

    expect(screen.getByText(/Loading artifact/i)).toBeInTheDocument();
    expect(await screen.findByText("Storm weather")).toBeInTheDocument();
    expect(await screen.findByText("d20")).toBeInTheDocument();
    expect(await screen.findByText(/## 1-4/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Patch artifact" })).toBeInTheDocument();
  });

  it("does not fetch unsupported target types and shows unsupported message", async () => {
    render(<InspectorPane state={{ status: "open", target: { ...target, target_type: "npc" } }} onClose={vi.fn()} />);
    expect(await screen.findByText(/Read renderer not implemented for this target type yet/i)).toBeInTheDocument();
    expect(liveApi.getArtifact).not.toHaveBeenCalled();
    expect(liveApi.getCapabilities).not.toHaveBeenCalled();
  });

  it("renders error state while keeping selected target metadata", async () => {
    vi.mocked(liveApi.getArtifact).mockRejectedValue(new Error("target not found"));
    render(<InspectorPane state={{ status: "open", target }} onClose={vi.fn()} />);
    expect(await screen.findByText("target not found")).toBeInTheDocument();
    expect(screen.getByText(/roll table · Travel weather table/i)).toBeInTheDocument();
    expect(screen.getByText("T-WX")).toBeInTheDocument();
  });

  it("renders patch_artifact and append_observation actions for roll_table", async () => {
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    render(<InspectorPane state={{ status: "open", target }} onClose={vi.fn()} />);
    await screen.findByText(/Future capabilities/i);
    expect(screen.getByRole("button", { name: "Patch artifact" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Append observation" })).toBeInTheDocument();
  });

  it("does not show roll-table patch action for event artifacts", async () => {
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeEventArtifact());
    render(<InspectorPane state={{ status: "open", target: { ...target, target_type: "event" } }} onClose={vi.fn()} />);
    await screen.findByText(/Future capabilities/i);
    expect(screen.queryByRole("button", { name: "Patch artifact" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Append observation" })).toBeInTheDocument();
  });

  it("submits append_observation and refreshes selected reads + app callback", async () => {
    const user = userEvent.setup();
    const onCommandAccepted = vi.fn(async () => undefined);
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    render(
      <InspectorPane
        state={{ status: "open", target }}
        onClose={vi.fn()}
        onCommandAccepted={onCommandAccepted}
      />,
    );

    await screen.findByText(/Future capabilities/i);
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await user.type(screen.getByLabelText("Observation"), "Remember this pressure.");
    await user.click(screen.getByRole("button", { name: "Submit observation" }));

    expect(await screen.findByText("Observation appended.")).toBeInTheDocument();
    expect(liveApi.postCommand).toHaveBeenCalledTimes(1);
    expect(liveApi.getArtifact).toHaveBeenCalledTimes(2);
    expect(liveApi.getCapabilities).toHaveBeenCalledTimes(2);
    expect(onCommandAccepted).toHaveBeenCalledTimes(1);
    expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
  });

  it("shows verified read-after-write evidence after accepted patch and successful refresh", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    vi.mocked(liveApi.postCommand)
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "noop",
          metadata: {
            patch: {
              dry_run: true,
              file_state_token_before: "table-token-1",
              file_state_token_after: "table-token-2",
              replacement_count: 1,
            },
          },
        }),
      )
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "accepted",
          events_appended: ["evt-patch-1"],
          artifacts_changed: [
            {
              target_type: "roll_table",
              target_id: "T-WX",
              label: "Storm weather",
              source_status: "authoritative",
              metadata: {},
            },
          ],
          metadata: {
            patch: {
              dry_run: false,
              file_state_token_before: "table-token-1",
              file_state_token_after: "table-token-1",
              replacement_count: 1,
            },
          },
        }),
      );

    render(<InspectorPane state={{ status: "open", target }} onClose={vi.fn()} />);
    await screen.findByRole("button", { name: "Patch artifact" });
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    await user.click(screen.getByRole("button", { name: "Confirm patch" }));

    expect(
      await screen.findByText("Verified: refreshed artifact matches patched state."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
  });

  it("shows accepted-refresh-failed evidence when reload fails after accepted patch", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.getArtifact).mockResolvedValue(makeRollTableArtifact());
    vi.mocked(liveApi.getCapabilities)
      .mockResolvedValueOnce(makeCapabilityResponse())
      .mockRejectedValueOnce(new Error("reload failed"));
    vi.mocked(liveApi.postCommand)
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "noop",
          metadata: {
            patch: {
              dry_run: true,
            },
          },
        }),
      )
      .mockResolvedValueOnce(
        makeWriteResult({
          status: "accepted",
          events_appended: ["evt-patch-2"],
          metadata: {
            patch: {
              dry_run: false,
              file_state_token_after: "table-token-2",
            },
          },
        }),
      );

    render(<InspectorPane state={{ status: "open", target }} onClose={vi.fn()} />);
    await screen.findByRole("button", { name: "Patch artifact" });
    await user.click(screen.getByRole("button", { name: "Patch artifact" }));
    await user.type(screen.getByLabelText("Text to replace"), "Calm skies");
    await user.type(screen.getByLabelText("Replacement text"), "Heavy hail");
    await user.click(screen.getByRole("button", { name: "Preview patch" }));
    await user.click(screen.getByRole("button", { name: "Confirm patch" }));

    expect(
      await screen.findByText(/Patch accepted, but refresh failed\./),
    ).toBeInTheDocument();
    expect(screen.getByText("Refresh error: reload failed")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /close/i })).toBeInTheDocument();
  });

  it("renders selected metadata", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<InspectorPane state={{ status: "open", target }} onClose={onClose} />);

    expect(screen.getByText(/roll table · Travel weather table/i)).toBeInTheDocument();
    expect(screen.getByText("authoritative")).toBeInTheDocument();
    expect(screen.getByText("next_roll")).toBeInTheDocument();
    expect(screen.getByText("T-WX")).toBeInTheDocument();
    expect(screen.getByText(/timeline \/ beat-day1-weather-front/i)).toBeInTheDocument();
    await screen.findByText(/Future capabilities/i);

    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
