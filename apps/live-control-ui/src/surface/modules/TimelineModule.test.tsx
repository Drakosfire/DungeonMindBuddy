import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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
    expect(screen.queryByRole("button")).toBeNull();
  });

  it("renders selectable chips and emits pane target from row/ref metadata", async () => {
    const user = userEvent.setup();
    const onSelectTarget = vi.fn();
    render(<TimelineModule planView={mockPlanView} onSelectTarget={onSelectTarget} />);

    await user.click(screen.getByRole("button", { name: /roll table · Travel weather table/i }));
    expect(onSelectTarget).toHaveBeenCalledWith({
      target_type: "roll_table",
      target_id: "T-WX",
      label: "Travel weather table",
      source_status: "authoritative",
      role: "next_roll",
      origin: {
        module_id: "timeline",
        row_id: "beat-day1-weather-front",
      },
    });
  });

  it("renders empty state when no timeline rows exist", () => {
    render(<TimelineModule planView={{ ...mockPlanView, timeline: [] }} />);
    expect(screen.getByText(/No projected beats yet/i)).toBeInTheDocument();
  });
});
