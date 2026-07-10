import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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
    expect(card).toHaveClass("graph-object-card");
    expect(card).toHaveAttribute("data-graph-object-card-mode", "plan");
    expect(within(card).getByLabelText("Object type: Location")).toHaveClass(
      "graph-object-card__type-badge",
    );
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
    expect(detailsPanel).toHaveClass("graph-object-card__details");
    expect(within(detailsPanel!).getByText("Visibility: Table known")).toBeInTheDocument();
    expect(within(detailsPanel!).getByText(/1 evidence badge/)).toBeInTheDocument();
    expect(within(detailsPanel!).getByText("Session recap mention · recap")).toBeInTheDocument();
    expect(within(detailsPanel!).queryByText("location-inn")).not.toBeInTheDocument();
    expect(within(detailsPanel!).queryByText(/Node ID:/)).not.toBeInTheDocument();
  });

  it("shows node id in plan mode only when showDebugIdentifiers is true", async () => {
    const user = userEvent.setup();
    render(<GraphObjectCard mode="plan" model={planModel} showDebugIdentifiers />);

    const card = screen.getByLabelText(/Inn \(Mireward Reach\) game card/i);
    await user.click(within(card).getByText("Details"));

    const detailsPanel = within(card).getByText("Details").closest("details");
    expect(detailsPanel).not.toBeNull();
    expect(within(detailsPanel!).getByText(/Node ID:/)).toBeInTheDocument();
    expect(within(detailsPanel!).getByText("location-inn")).toBeInTheDocument();
  });

  it("does not render graph-review class names in plan mode", () => {
    const { container } = render(<GraphObjectCard mode="plan" model={planModel} />);

    const graphReviewElements = container.querySelectorAll('[class*="graph-review"]');
    expect(graphReviewElements).toHaveLength(0);
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

  it("renders Plan actions and expands Details for Inspect source/evidence", async () => {
    const user = userEvent.setup();
    const modelWithActions: GraphObjectCardViewModel = {
      ...planModel,
      actions: [
        {
          id: "open-source",
          label: "Inspect source/evidence",
          kind: "open-source",
          helpText: "Opens the card Details section for evidence and source context.",
        },
        {
          id: "open-ingest",
          label: "Review memory in /ingest",
          kind: "open-ingest",
          href: "/ingest?campaign=longmont-c2&session=session-21",
        },
      ],
    };

    render(<GraphObjectCard mode="plan" model={modelWithActions} />);

    const card = screen.getByLabelText(/Inn \(Mireward Reach\) game card/i);
    expect(within(card).getByRole("heading", { name: "Actions" })).toBeInTheDocument();
    expect(within(card).getByRole("link", { name: /Review memory in \/ingest/i })).toHaveAttribute(
      "href",
      "/ingest?campaign=longmont-c2&session=session-21",
    );

    const details = within(card).getByText("Details").closest("details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");

    await user.click(within(card).getByRole("button", { name: /Inspect source\/evidence/i }));
    expect(details).toHaveAttribute("open");
    expect(within(details!).queryByText(/Node ID:/)).not.toBeInTheDocument();
  });

  it("does not render an Actions heading when there are no actions", () => {
    render(<GraphObjectCard mode="plan" model={planModel} />);
    expect(screen.queryByRole("heading", { name: "Actions" })).not.toBeInTheDocument();
  });

  it("renders related objects as plain list items without a callback", () => {
    render(<GraphObjectCard mode="plan" model={planModel} />);

    const card = screen.getByLabelText(/Inn \(Mireward Reach\) game card/i);
    expect(within(card).getByText("Glowkindle")).toBeInTheDocument();
    expect(
      within(card).queryByRole("button", { name: /Open related object/i }),
    ).not.toBeInTheDocument();
    expect(within(card).queryByText("location-inn")).not.toBeInTheDocument();
  });

  it("renders related objects as buttons and calls onSelectRelationship", async () => {
    const user = userEvent.setup();
    const onSelectRelationship = vi.fn();

    render(
      <GraphObjectCard
        mode="plan"
        model={planModel}
        onSelectRelationship={onSelectRelationship}
      />,
    );

    const card = screen.getByLabelText(/Inn \(Mireward Reach\) game card/i);
    const button = within(card).getByRole("button", {
      name: /Open related object Glowkindle/i,
    });
    expect(button).toBeInTheDocument();
    expect(button).not.toHaveTextContent("edge-1");
    expect(within(card).queryByText(/node_id|location-inn/i)).not.toBeInTheDocument();

    await user.click(button);
    expect(onSelectRelationship).toHaveBeenCalledOnce();
    expect(onSelectRelationship).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "edge-1",
        label: "Glowkindle",
        predicate: "negotiated with",
      }),
    );
  });
});
