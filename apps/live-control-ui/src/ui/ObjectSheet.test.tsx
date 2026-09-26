import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { GraphObjectCardViewModel } from "../graphObjectCard/types";
import { ObjectSheet } from "./ObjectSheet";
import {
  faction,
  location,
  relationshipHeavy,
  richNpc,
  sparseNpc,
} from "./fixtures/worldObjects";

describe("ObjectSheet workshop presentation", () => {
  it("keeps a sparse NPC useful without inventing empty sections or diagnostic placeholders", () => {
    render(<ObjectSheet model={sparseNpc} />);

    const sheet = screen.getByRole("region", { name: "Quiet witness object sheet" });
    expect(within(sheet).getByRole("heading", { level: 2, name: "Quiet witness" })).toBeInTheDocument();
    expect(within(sheet).getByText("NPC")).toBeInTheDocument();
    expect(within(sheet).queryByRole("region", { name: "At the table" })).not.toBeInTheDocument();
    expect(within(sheet).queryByRole("region", { name: "Connected objects" })).not.toBeInTheDocument();
    expect(within(sheet).queryByText("Source and provenance")).not.toBeInTheDocument();
    expect(sheet).not.toHaveTextContent(sparseNpc.id);
  });

  it("puts table-useful meaning before connected objects and keeps source metadata secondary", async () => {
    const user = userEvent.setup();
    render(<ObjectSheet model={richNpc} />);

    const sheet = screen.getByRole("region", { name: "Brin object sheet" });
    expect(within(sheet).getByRole("heading", { level: 2, name: "Brin" })).toBeInTheDocument();
    expect(within(sheet).getByText("Refugee leader")).toBeInTheDocument();
    expect(within(sheet).getByText("Also known as Brin Holloway")).toBeInTheDocument();
    expect(within(sheet).getByText("C2")).toBeInTheDocument();
    const text = sheet.textContent ?? "";
    expect(text.indexOf("A cook from Edge")).toBeLessThan(text.indexOf("Connected objects"));
    expect(within(sheet).getByText(/Brin sorted the arrivals/)).toBeInTheDocument();
    expect(within(sheet).getByText(/Orik · coordinated with/)).toBeInTheDocument();

    const source = within(sheet).getByText("Source and provenance").closest("details");
    expect(source).not.toBeNull();
    expect(source).not.toHaveAttribute("open");
    await user.click(within(sheet).getByText("Source and provenance"));
    expect(source).toHaveAttribute("open");
    expect(within(source!).getByText("Visibility: GM private")).toBeInTheDocument();
    expect(within(source!).getByText("1 evidence item")).toBeInTheDocument();
    expect(within(source!).getByText("Session 25 recap")).toBeInTheDocument();
    expect(sheet).not.toHaveTextContent(richNpc.id);
    expect(sheet).not.toHaveTextContent(richNpc.relationships[0].id);
    expect(sheet).not.toHaveTextContent(richNpc.evidence[0].id);
  });

  it("uses the existing game-summary precedence and one hierarchy for Location and Faction", () => {
    const locationModel: GraphObjectCardViewModel = {
      ...location,
      summary: "Older graph summary",
      gameSummary: "Preferred table summary",
    };
    const { rerender } = render(<ObjectSheet model={locationModel} />);
    expect(screen.getByRole("heading", { level: 2, name: "South Gate" })).toBeInTheDocument();
    expect(screen.getByText("Preferred table summary")).toBeInTheDocument();
    expect(screen.queryByText("Older graph summary")).not.toBeInTheDocument();

    rerender(<ObjectSheet model={faction} />);
    expect(screen.getByRole("heading", { level: 2, name: "River Wardens" })).toBeInTheDocument();
    expect(screen.getByText("Faction")).toBeInTheDocument();
    expect(screen.getByText(/A small civic watch/)).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Connected objects" })).toBeInTheDocument();
  });

  it("bounds 15 relationships, discloses all locally, and resets on object change", async () => {
    const user = userEvent.setup();
    const { rerender } = render(<ObjectSheet model={relationshipHeavy} />);
    const connections = screen.getByRole("region", { name: "Connected objects" });
    expect(within(connections).getAllByRole("listitem")).toHaveLength(8);
    expect(within(connections).queryByText(/Contact 15/)).not.toBeInTheDocument();

    const disclosure = within(connections).getByRole("button", {
      name: "Show all 15 relationships (7 more)",
    });
    expect(disclosure).toHaveAttribute("aria-expanded", "false");
    await user.click(disclosure);
    expect(within(connections).getAllByRole("listitem")).toHaveLength(15);
    expect(within(connections).getByText(/Contact 15/)).toBeInTheDocument();
    expect(within(connections).getByRole("button", { name: "Show fewer" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );

    rerender(<ObjectSheet model={{ ...relationshipHeavy, id: "workshop:npc:another" }} />);
    expect(within(connections).getAllByRole("listitem")).toHaveLength(8);
    expect(within(connections).getByRole("button", { name: /Show all 15/ })).toHaveAttribute(
      "aria-expanded",
      "false",
    );
  });
});
