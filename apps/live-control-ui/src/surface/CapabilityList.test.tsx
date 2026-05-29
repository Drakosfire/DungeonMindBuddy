import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { makeCapabilityResponse } from "../test/fixtures";
import { CapabilityList } from "./CapabilityList";

describe("CapabilityList", () => {
  it("renders disabled capability rows as informational content", () => {
    const response = makeCapabilityResponse();
    const { container } = render(<CapabilityList capabilities={response.capabilities} />);

    expect(screen.getByText("Future capabilities")).toBeInTheDocument();
    expect(screen.getByText("Patch artifact")).toBeInTheDocument();
    expect(screen.getByText("Append observation")).toBeInTheDocument();
    expect(screen.getAllByText(/Command bus not implemented until PR85/)).not.toHaveLength(0);
    expect(container.querySelectorAll("button")).toHaveLength(0);
  });

  it("renders empty informational state when no capabilities are present", () => {
    render(<CapabilityList capabilities={[]} />);
    expect(screen.getByText(/No capabilities were returned for this target/i)).toBeInTheDocument();
  });
});
