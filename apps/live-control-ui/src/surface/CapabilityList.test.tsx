import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  makeAppendObservationCommand,
  makeCapabilityResponse,
  makeEventArtifact,
  makeRollTableArtifact,
  makeWriteResult,
} from "../test/fixtures";
import { CapabilityList } from "./CapabilityList";

describe("CapabilityList", () => {
  it("renders disabled capabilities as non-clickable informational rows", () => {
    const response = makeCapabilityResponse({
      capabilities: makeCapabilityResponse().capabilities.map((capability) => ({
        ...capability,
        enabled: false,
        disabled_reason: "Disabled for test.",
      })),
    });
    const { container } = render(
      <CapabilityList
        target={response.target}
        artifact={makeRollTableArtifact()}
        capabilities={response.capabilities}
      />,
    );

    expect(screen.getByText("Future capabilities")).toBeInTheDocument();
    expect(screen.getByText("Patch artifact")).toBeInTheDocument();
    expect(screen.getByText("Append observation")).toBeInTheDocument();
    expect(screen.getAllByText(/Disabled for test/)).toHaveLength(2);
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  it("renders append_observation action affordance when enabled", () => {
    const response = makeCapabilityResponse();
    const onSubmit = async () => makeWriteResult();
    render(
      <CapabilityList
        target={response.target}
        artifact={makeRollTableArtifact()}
        capabilities={response.capabilities}
        onSubmitCommand={onSubmit}
      />,
    );
    expect(screen.getByRole("button", { name: "Append observation" })).toBeInTheDocument();
  });

  it("renders patch_artifact action affordance for enabled roll-table capability", () => {
    const response = makeCapabilityResponse();
    const onSubmit = async () => makeWriteResult();
    render(
      <CapabilityList
        target={response.target}
        artifact={makeRollTableArtifact()}
        capabilities={response.capabilities}
        onSubmitCommand={onSubmit}
      />,
    );
    expect(screen.getByRole("button", { name: "Patch artifact" })).toBeInTheDocument();
  });

  it("keeps enabled patch_artifact inert for non-roll-table targets", () => {
    const response = makeCapabilityResponse({
      target: {
        ...makeCapabilityResponse().target,
        target_type: "event",
        target_id: "evt-roll-1",
      },
    });
    render(
      <CapabilityList
        target={response.target}
        artifact={makeEventArtifact()}
        capabilities={response.capabilities}
      />,
    );
    expect(screen.getByText(/Action not supported in this pane version/i)).toBeInTheDocument();
  });

  it("keeps queue_canon_patch inert when enabled", () => {
    const response = makeCapabilityResponse({
      capabilities: [
        ...makeCapabilityResponse().capabilities,
        {
          command_type: "queue_canon_patch",
          label: "Queue canon patch",
          lane: "canon_patch",
          enabled: true,
          required_fields: ["summary"],
          risk_level: "high",
          disabled_reason: null,
          metadata: {},
        },
      ],
    });
    render(
      <CapabilityList
        target={response.target}
        artifact={makeRollTableArtifact()}
        capabilities={response.capabilities}
      />,
    );
    expect(screen.getByText(/Queue canon patch/)).toBeInTheDocument();
    expect(screen.getByText(/Action not supported in this pane version/i)).toBeInTheDocument();
  });

  it("keeps unsupported enabled capability inert", () => {
    const response = makeCapabilityResponse({
      capabilities: [
        ...makeCapabilityResponse().capabilities,
        {
          command_type: "request_retrieval_refresh",
          label: "Refresh retrieval",
          lane: "retrieval_curation",
          enabled: true,
          required_fields: [],
          risk_level: "low",
          disabled_reason: null,
          metadata: {},
        },
      ],
    });
    render(
      <CapabilityList
        target={response.target}
        artifact={makeRollTableArtifact()}
        capabilities={response.capabilities}
      />,
    );
    expect(screen.getByText(/Action not supported in this pane version/i)).toBeInTheDocument();
  });

  it("renders empty informational state when no capabilities are present", () => {
    render(
      <CapabilityList
        target={makeAppendObservationCommand().target}
        artifact={makeRollTableArtifact()}
        capabilities={[]}
      />,
    );
    expect(screen.getByText(/No capabilities were returned for this target/i)).toBeInTheDocument();
  });
});
