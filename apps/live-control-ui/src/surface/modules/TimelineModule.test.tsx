import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mockCatalog, mockPlanView } from "../../test/fixtures";
import { TimelineModule } from "./TimelineModule";

describe("TimelineModule", () => {
  it("renders label, status, time hint, summary, and prompt", () => {
    render(
      <TimelineModule
        planView={mockPlanView}
        catalogEntry={mockCatalog.find((row) => row.module_id === "timeline")}
      />,
    );

    expect(screen.getByText("Timeline")).toBeInTheDocument();
    expect(screen.getByText("projected")).toBeInTheDocument();
    expect(screen.getByText("Day 1")).toBeInTheDocument();
    expect(screen.getByText(/Weather and march pressure/)).toBeInTheDocument();
    expect(screen.getByText(/Prompt: Roll T-WX/)).toBeInTheDocument();
  });

  it("renders typed ref chips with human labels", () => {
    render(<TimelineModule planView={mockPlanView} />);
    expect(screen.getByText(/roll table · Travel weather table/i)).toBeInTheDocument();
  });

  it("renders empty state when no timeline rows exist", () => {
    render(<TimelineModule planView={{ ...mockPlanView, timeline: [] }} />);
    expect(screen.getByText(/No projected beats yet/i)).toBeInTheDocument();
  });
});
