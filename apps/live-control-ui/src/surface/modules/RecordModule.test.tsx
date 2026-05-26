import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { mockRollEvent } from "../../test/fixtures";
import { RecordModule } from "./RecordModule";
import { RollStackModule } from "./RollStackModule";
import { mockCatalog, mockState } from "../../test/fixtures";

describe("RecordModule", () => {
  it("renders roll_result event summary", () => {
    render(<RecordModule events={[mockRollEvent]} />);
    expect(screen.getByText(/Resolved T-WX roll 7: Hail dent/)).toBeInTheDocument();
    expect(screen.getByText("roll_result")).toBeInTheDocument();
  });

  it("handles empty event list", () => {
    render(<RecordModule events={[]} />);
    expect(screen.getByText(/No events yet/i)).toBeInTheDocument();
  });
});

describe("RollStackModule human labels", () => {
  it("shows Storm weather before raw corpus paths", () => {
    render(
      <RollStackModule
        state={mockState}
        catalogEntry={mockCatalog.find((row) => row.module_id === "roll_stack")}
        events={[]}
      />,
    );
    expect(screen.getByText("Storm weather")).toBeInTheDocument();
    expect(screen.queryByText(/corpus\/eldyrwild/)).not.toBeInTheDocument();
  });
});
