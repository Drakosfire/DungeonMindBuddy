import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GraphReviewAuthoringWorkbenchModule } from "./GraphReviewAuthoringWorkbenchModule";
import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import { mockTripodNode } from "./graphReviewAuthoringMockData";

describe("GraphReviewAuthoringWorkbenchModule", () => {
  it("starts with the inspector rail collapsed and labels the walkthrough as mock-only", () => {
    render(<GraphReviewAuthoringWorkbenchModule />);
    expect(screen.getByRole("button", { name: "Inspector" })).toBeInTheDocument();
    expect(screen.queryByLabelText("Tripod Null-Calf game card")).not.toBeInTheDocument();
    expect(screen.getByText(/Visual walkthrough \/ mock UX scaffold — no live data, no writes/i)).toBeInTheDocument();
    expect(screen.getByText(/demo-only Gold Draft, Live Run, proposal counts, and game objects/i)).toBeInTheDocument();
  });

  it("shows an empty inspector state when opened without a selection", () => {
    render(<GraphReviewAuthoringWorkbenchModule />);
    fireEvent.click(screen.getByRole("button", { name: "Inspector" }));
    expect(screen.getByText("Select a pill or relationship to inspect game-facing details.")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Tripod Null-Calf threatens North Gate" })).not.toBeInTheDocument();
  });

  it("renders source and mutability in lane headers", () => {
    render(<GraphReviewAuthoringWorkbenchModule />);
    expect(screen.getByText(/seeded gold draft · editable · Seeded from candidate gold fixture/i)).toBeInTheDocument();
    expect(screen.getByText(/live run · read-only · Latest vocabulary-assisted run/i)).toBeInTheDocument();
  });

  it("opens a readable relationship card from a chip", () => {
    render(<GraphReviewAuthoringWorkbenchModule />);
    fireEvent.click(screen.getAllByRole("button", { name: "threatens → North Gate" })[0]);
    expect(screen.getByRole("heading", { name: "Tripod Null-Calf threatens North Gate" })).toBeInTheDocument();
  });

  it("accepts a staged proposal before counting it as visible in the draft", () => {
    render(<GraphReviewAuthoringWorkbenchModule />);
    expect(screen.getAllByText(/Accepted mock proposals visible in this draft:\s*0/)[0]).toBeInTheDocument();
    const northGateCard = screen.getByRole("heading", { name: "North Gate" }).closest("article");
    if (!northGateCard) throw new Error("North Gate proposal card missing");
    fireEvent.click(within(northGateCard).getByRole("button", { name: "Accept" }));
    expect(screen.getAllByText(/Accepted mock proposals visible in this draft:\s*1/)[0]).toBeInTheDocument();
  });
});

describe("GraphReviewNodeGameCard", () => {
  it("renders available surfaces before Evidence / Debug", () => {
    const { container } = render(<GraphReviewNodeGameCard node={mockTripodNode} onShowRelationships={() => undefined} />);
    expect(container.textContent?.indexOf("Open statblock")).toBeLessThan(container.textContent?.indexOf("Evidence / Debug") ?? 0);
  });
});
