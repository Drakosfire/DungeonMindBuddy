import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { GraphObjectCard } from "./GraphObjectCard";
import type { GraphObjectCardViewModel } from "./types";

const planModel: GraphObjectCardViewModel = {
  id: "location-inn",
  label: "Inn (Mireward Reach)",
  kind: "location",
  role: "location",
  typeBadgeLabel: "Location",
  secondaryRoleLabel: null,
  aliases: ["The Inn", "Mireward Inn"],
  summary: "The party's meeting place with the town leader.",
  gameSummary: "The party's meeting place with the town leader.",
  whyItMattersNow: "The council meets here tonight.",
  relationships: [
    {
      id: "edge-1",
      label: "Glowkindle",
      predicate: "negotiated with",
      summary: "Trades rare herbs.",
    },
  ],
  evidence: [
    {
      id: "ev-1",
      label: "Session recap mention",
      sourceDomain: "recap",
    },
  ],
  sourceDomains: ["recap"],
  visibilityLabel: "Table known",
  details: {
    visibilityLabel: "Table known",
    sourceDomains: ["recap"],
    evidenceCount: 1,
    sourceAnchorText: "They all head to the Inn",
    nodeId: "location-inn",
  },
  actions: [],
};

describe("GraphObjectCard", () => {
  it("renders plan mode with label, type badge, aliases, summary, relationships, and evidence", async () => {
    const user = userEvent.setup();
    render(<GraphObjectCard mode="plan" model={planModel} />);

    const card = screen.getByLabelText(/Inn \(Mireward Reach\) game card/i);
    expect(card).toHaveAttribute("data-graph-object-card-mode", "plan");
    expect(within(card).getByLabelText("Object type: Location")).toHaveTextContent("Location");
    expect(within(card).getByRole("heading", { level: 4 })).toHaveTextContent("Inn (Mireward Reach)");
    expect(within(card).getByText(/Also known as: The Inn, Mireward Inn/)).toBeInTheDocument();
    expect(
      within(card).getByText("The party's meeting place with the town leader."),
    ).toBeInTheDocument();
    expect(within(card).getByText(/The council meets here tonight\./)).toBeInTheDocument();
    expect(within(card).getByRole("heading", { name: "Related objects" })).toBeInTheDocument();
    expect(within(card).getByText(/Glowkindle/)).toBeInTheDocument();
    expect(within(card).getByText(/negotiated with/)).toBeInTheDocument();

    await user.click(within(card).getByText("Details"));

    const detailsPanel = within(card).getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(within(detailsPanel!).getByText("Visibility: Table known")).toBeInTheDocument();
    expect(within(detailsPanel!).getByText(/1 evidence badge/)).toBeInTheDocument();
    expect(within(detailsPanel!).getByText("Session recap mention · recap")).toBeInTheDocument();
    expect(within(detailsPanel!).getByText("location-inn")).toBeInTheDocument();
  });

  it("does not render review-only copy in plan mode by default", () => {
    render(<GraphObjectCard mode="plan" model={planModel} />);

    expect(screen.queryByText("Gold Fixture")).not.toBeInTheDocument();
    expect(screen.queryByText("Live Run")).not.toBeInTheDocument();
    expect(screen.queryByText(/Delta ID:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Lane role:/)).not.toBeInTheDocument();
    expect(screen.queryByText("Stage relationship")).not.toBeInTheDocument();
    expect(screen.queryByText("Review status")).not.toBeInTheDocument();
  });
});
