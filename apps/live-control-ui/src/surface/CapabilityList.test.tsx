import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  makeAppendObservationCommand,
  makeCapabilityResponse,
  makeWriteResult,
} from "../test/fixtures";
import { CapabilityList } from "./CapabilityList";

describe("CapabilityList", () => {
  it("renders disabled capabilities as non-clickable informational rows", () => {
    const response = makeCapabilityResponse();
    const { container } = render(
      <CapabilityList target={response.target} capabilities={response.capabilities} />,
    );

    expect(screen.getByText("Future capabilities")).toBeInTheDocument();
    expect(screen.getByText("Patch artifact")).toBeInTheDocument();
    expect(screen.getByText("Append observation")).toBeInTheDocument();
    expect(screen.getByText(/Not implemented in PR85/)).toBeInTheDocument();
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  it("renders append_observation action affordance when enabled", () => {
    const response = makeCapabilityResponse();
    const onSubmit = async () => makeWriteResult();
    render(
      <CapabilityList
        target={response.target}
        capabilities={response.capabilities}
        onSubmitCommand={onSubmit}
      />,
    );
    expect(screen.getByRole("button", { name: "Append observation" })).toBeInTheDocument();
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
    render(<CapabilityList target={response.target} capabilities={response.capabilities} />);
    expect(screen.getByText(/Action not supported in this pane version/i)).toBeInTheDocument();
  });

  it("renders empty informational state when no capabilities are present", () => {
    render(
      <CapabilityList
        target={makeAppendObservationCommand().target}
        capabilities={[]}
      />,
    );
    expect(screen.getByText(/No capabilities were returned for this target/i)).toBeInTheDocument();
  });
});
