import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { makeCapabilityResponse, makeWriteResult } from "../test/fixtures";
import { AppendObservationAction } from "./AppendObservationAction";

describe("AppendObservationAction", () => {
  const capability = makeCapabilityResponse().capabilities.find(
    (c) => c.command_type === "append_observation",
  )!;
  const target = makeCapabilityResponse().target;

  it("renders action button and form", async () => {
    const user = userEvent.setup();
    render(
      <AppendObservationAction
        target={target}
        capability={capability}
        onSubmitCommand={async () => makeWriteResult()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    expect(screen.getByLabelText("Observation")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit observation" })).toBeInTheDocument();
  });

  it("does not submit empty observation", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makeWriteResult());
    render(
      <AppendObservationAction target={target} capability={capability} onSubmitCommand={onSubmit} />,
    );
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await user.click(screen.getByRole("button", { name: "Submit observation" }));
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("builds expected append_observation command shape", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn(async () => makeWriteResult());
    render(
      <AppendObservationAction target={target} capability={capability} onSubmitCommand={onSubmit} />,
    );
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await user.type(screen.getByLabelText("Observation"), "Remember this at the gate.");
    await user.type(screen.getByLabelText("Session clock (optional)"), "during gate scene");
    await user.click(screen.getByRole("button", { name: "Submit observation" }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
    const command = onSubmit.mock.calls[0][0];
    expect(command.command_type).toBe("append_observation");
    expect(command.lane).toBe("observed_play");
    expect(command.requested_by).toEqual({
      requester_type: "human_ui",
      requester_id: "live-control-ui",
    });
    expect(command.payload.visibility).toBe("live_note");
    expect(typeof command.idempotency_key).toBe("string");
    expect(command.idempotency_key).toContain("ui-append-observation");
    expect(command.payload).not.toHaveProperty("source_path");
  });

  it("shows accepted result with appended event id", async () => {
    const user = userEvent.setup();
    render(
      <AppendObservationAction
        target={target}
        capability={capability}
        onSubmitCommand={async () => makeWriteResult({ events_appended: ["evt-observation-abc123"] })}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await user.type(screen.getByLabelText("Observation"), "Live note");
    await user.click(screen.getByRole("button", { name: "Submit observation" }));
    expect(await screen.findByText("Observation appended.")).toBeInTheDocument();
    expect(screen.getByText(/evt-observation-abc123/)).toBeInTheDocument();
  });

  it("shows rejected conflicts", async () => {
    const user = userEvent.setup();
    render(
      <AppendObservationAction
        target={target}
        capability={capability}
        onSubmitCommand={async () =>
          makeWriteResult({
            status: "rejected",
            conflicts: [
              {
                conflict_type: "invalid_payload",
                message: "payload.observation is required",
                target: target,
                recoverable: true,
              },
            ],
          })}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await user.type(screen.getByLabelText("Observation"), "bad");
    await user.click(screen.getByRole("button", { name: "Submit observation" }));
    expect(await screen.findByText("Command rejected.")).toBeInTheDocument();
    expect(screen.getByText(/invalid_payload: payload.observation is required/)).toBeInTheDocument();
  });

  it("shows noop diagnostics", async () => {
    const user = userEvent.setup();
    render(
      <AppendObservationAction
        target={target}
        capability={capability}
        onSubmitCommand={async () =>
          makeWriteResult({
            status: "noop",
            diagnostics: ["duplicate idempotency_key; no new event appended"],
          })}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await user.type(screen.getByLabelText("Observation"), "note");
    await user.click(screen.getByRole("button", { name: "Submit observation" }));
    expect(await screen.findByText("No change.")).toBeInTheDocument();
    expect(screen.getByText(/duplicate idempotency_key/)).toBeInTheDocument();
  });

  it("shows network/API error", async () => {
    const user = userEvent.setup();
    render(
      <AppendObservationAction
        target={target}
        capability={capability}
        onSubmitCommand={async () => {
          throw new Error("server unavailable");
        }}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Append observation" }));
    await user.type(screen.getByLabelText("Observation"), "note");
    await user.click(screen.getByRole("button", { name: "Submit observation" }));
    expect(await screen.findByText("server unavailable")).toBeInTheDocument();
  });
});
