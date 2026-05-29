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

  it("renders only append_observation as action and keeps others informational", async () => {
    render(<InspectorPane state={{ status: "open", target }} onClose={vi.fn()} />);
    await screen.findByText(/Future capabilities/i);
    expect(screen.getByText(/Patch artifact/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Append observation" })).toBeInTheDocument();
    const patchButtons = screen
      .queryAllByRole("button")
      .filter((button) => /patch artifact/i.test(button.textContent ?? ""));
    expect(patchButtons).toHaveLength(0);
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
