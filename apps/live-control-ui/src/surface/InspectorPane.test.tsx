import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { InspectorPane } from "./InspectorPane";
import type { PaneTarget } from "./targetTypes";

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
  it("renders closed state as hidden/unmounted", () => {
    const { container } = render(<InspectorPane state={{ status: "closed" }} onClose={vi.fn()} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders open empty state", () => {
    render(<InspectorPane state={{ status: "open", target: null }} onClose={vi.fn()} />);
    expect(screen.getByText("Inspector")).toBeInTheDocument();
    expect(screen.getByText(/Select a timeline ref or record event to inspect/i)).toBeInTheDocument();
  });

  it("renders selected metadata and placeholder copy", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    render(<InspectorPane state={{ status: "open", target }} onClose={onClose} />);

    expect(screen.getByText(/roll table · Travel weather table/i)).toBeInTheDocument();
    expect(screen.getByText("authoritative")).toBeInTheDocument();
    expect(screen.getByText("next_roll")).toBeInTheDocument();
    expect(screen.getByText("T-WX")).toBeInTheDocument();
    expect(screen.getByText(/timeline \/ beat-day1-weather-front/i)).toBeInTheDocument();
    expect(screen.getByText(/Read renderer not implemented yet/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /close/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
