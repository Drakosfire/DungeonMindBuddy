import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import type { ReferenceResolution } from "../reference/referenceResolver";
import { ProjectionProvider } from "../projection/projectionContext";
import type { SurfaceConfig } from "../types";
import { SelectedObjectCard } from "./SelectedObjectCard";

const surfaceConfig: SurfaceConfig = {
  id: "plan",
  label: "Plan",
  context: {
    campaignId: "longmont-c2",
    headerLabel: "Longmont C2",
    prepSession: 24,
    ingestSession: 23,
    liveSession: 23,
  },
  tools: [
    { id: "statblock", label: "Statblock", size: "wide" },
  ],
  canvas: { documentId: "longmont-c2-session-24-prep" },
  theme: {},
  sessionDescriptor: {
    surfaceId: "plan",
    campaignId: "longmont-c2",
    campaignLabel: "Longmont C2",
    prepSession: 24,
    memorySession: 23,
    sourceStatusLabel: "unknown",
    sourceStatusKind: "unknown",
    planningDocument: {
      documentId: "longmont-c2-session-24-prep",
      title: "C2 Session 24 Prep",
      targetRelpath: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 24 Prep.md",
      storageKey: "dmb.planCanvas.longmont-c2.24.longmont-c2-session-24-prep",
      status: "local_draft",
    },
  },
};

function renderCard(resolution: ReferenceResolution) {
  return render(
    <ProjectionProvider config={surfaceConfig}>
      <SelectedObjectCard resolution={resolution} />
    </ProjectionProvider>,
  );
}

describe("SelectedObjectCard", () => {
  it("renders title, type badge, summary, primary fields, and source path", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Resolved from live location index.",
      sourcePath: "corpus/locations/north_reach_gate.md",
      item: {
        title: "North Reach Gate",
        district: "North Reach",
        table_note: "Crowded checkpoint.",
      },
    });

    expect(screen.getByRole("heading", { name: "North Reach Gate" })).toBeInTheDocument();
    expect(screen.getByText("Location")).toBeInTheDocument();
    expect(screen.getByText("Crowded checkpoint.")).toBeInTheDocument();
    expect(screen.getByText("District")).toBeInTheDocument();
    expect(screen.getByText("North Reach")).toBeInTheDocument();
    expect(screen.getByText("Source")).toBeInTheDocument();
    expect(screen.getByText("corpus/locations/north_reach_gate.md")).toBeInTheDocument();
  });

  it("omits empty fields", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "npc",
        refId: "lysandro-ironveil",
        label: "Lysandro Ironveil",
      },
      message: "Resolved from live npc index.",
      item: {
        title: "Lysandro Ironveil",
        table_note: "Human accelerant at the gate.",
      },
    });

    expect(screen.queryByText("Faction")).not.toBeInTheDocument();
    expect(screen.getByText("Human accelerant at the gate.")).toBeInTheDocument();
  });

  it("renders unresolved card without crashing", () => {
    renderCard({
      status: "unresolved",
      ref: {
        kind: "ref",
        refType: "location",
        refId: "north-reach-gate",
        label: "North Reach Gate",
      },
      message: "Could not resolve this reference.",
    });

    const card = screen.getByLabelText(/North Reach Gate selected object/i);
    expect(within(card).getByText(/Could not resolve this reference/i)).toBeInTheDocument();
    expect(within(card).getByText("Type")).toBeInTheDocument();
    expect(within(card).getByText("north-reach-gate")).toBeInTheDocument();
  });

  it("does not render edit-lock copy", () => {
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "statblock",
        refId: "tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      message: "Resolved from live statblock index.",
      item: { title: "Tripod Null-Calf", challenge_rating: "5" },
    });

    expect(screen.queryByText(/Read-only until unlocked/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/two-phase corpus writer/i)).not.toBeInTheDocument();
  });

  it("exposes expand and ingest follow-up actions", async () => {
    const user = userEvent.setup();
    renderCard({
      status: "resolved",
      ref: {
        kind: "ref",
        refType: "statblock",
        refId: "tripod-null-calf",
        label: "Tripod Null-Calf",
      },
      message: "Resolved from live statblock index.",
      item: { title: "Tripod Null-Calf", challenge_rating: "5" },
    });

    expect(screen.getByRole("button", { name: "Expand details" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Review memory in /ingest" })).toHaveAttribute("href", "/ingest");
    await user.click(screen.getByRole("button", { name: "Open statblock workbench" }));
  });
});
