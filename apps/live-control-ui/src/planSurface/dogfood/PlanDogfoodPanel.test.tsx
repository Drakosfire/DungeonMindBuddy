import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PlanSessionDescriptor } from "../types";
import { createPlanCanvasStorageKey } from "../config/planSessionDescriptor";
import { PlanDogfoodPanel } from "./PlanDogfoodPanel";
import {
  planDogfoodStorageKey,
  dogfoodModeFromLocation,
} from "./planDogfoodState";

vi.mock("../../api/liveApi", async () => {
  const actual = await vi.importActual<typeof import("../../api/liveApi")>("../../api/liveApi");
  return {
    ...actual,
    getUnionSupergraphProjection: vi.fn().mockResolvedValue({
      campaign_id: "longmont-c2",
      session_id: "session-21",
      node_views: {},
      focus: {
        focused_evidence_ref_ids: [],
        focused_node_ids: [],
        focused_edge_ids: [],
      },
      mentions: [],
    }),
  };
});

const sessionDescriptor: PlanSessionDescriptor = {
  surfaceId: "plan",
  campaignId: "longmont-c2",
  campaignLabel: "Longmont C2",
  prepSession: 23,
  memorySession: 21,
  liveSession: 22,
  sourceStatusLabel: "Session 21",
  sourceStatusKind: "unknown",
  planningDocument: {
    documentId: "longmont-c2-session-23-prep",
    title: "Longmont C2 Session 23 Prep",
    targetRelpath:
      "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    storageKey: createPlanCanvasStorageKey({
      campaignId: "longmont-c2",
      prepSession: 23,
      documentId: "longmont-c2-session-23-prep",
    }),
    status: "local_draft",
  },
};

function renderPanel(saveStatusLabel = "Local draft · not yet saved to Markdown") {
  return render(
    <PlanDogfoodPanel
      sessionDescriptor={sessionDescriptor}
      saveStatusLabel={saveStatusLabel}
    />,
  );
}

async function renderPanelReady(saveStatusLabel = "Local draft · not yet saved to Markdown") {
  const view = renderPanel(saveStatusLabel);
  await screen.findByTestId("graph-object-dogfood-panel");
  await waitFor(() => {
    expect(screen.getByText("No nodes in the current projection.")).toBeInTheDocument();
  });
  return view;
}

describe("dogfoodModeFromLocation", () => {
  it("returns true only when dogfood=1", () => {
    expect(
      dogfoodModeFromLocation({ search: "?campaign=longmont-c2&dogfood=1" } as Location),
    ).toBe(true);
    expect(dogfoodModeFromLocation({ search: "?dogfood=0" } as Location)).toBe(false);
    expect(dogfoodModeFromLocation({ search: "" } as Location)).toBe(false);
  });
});

describe("PlanDogfoodPanel", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders checklist and notes", async () => {
    await renderPanelReady();

    expect(screen.getByRole("region", { name: "Dogfood checklist" })).toBeInTheDocument();
    expect(screen.getByText("Add real prep notes to the board")).toBeInTheDocument();
    expect(screen.getByLabelText("Dogfood notes")).toBeInTheDocument();
    expect(screen.getByTestId("graph-object-dogfood-panel")).toBeInTheDocument();
  });

  it("checking an item persists to localStorage", async () => {
    const user = userEvent.setup();
    await renderPanelReady();

    const checkbox = screen.getByRole("checkbox", {
      name: "Add real prep notes to the board",
    });
    await user.click(checkbox);

    expect(checkbox).toBeChecked();
    const stored = JSON.parse(
      localStorage.getItem(planDogfoodStorageKey(sessionDescriptor)) ?? "{}",
    );
    expect(stored.checked["add-real-notes"]).toBe(true);
  });

  it("reloads checked state from localStorage on remount", async () => {
    localStorage.setItem(
      planDogfoodStorageKey(sessionDescriptor),
      JSON.stringify({
        checked: { "save-markdown": true },
        notes: "",
        updatedAt: "2026-07-09T00:00:00.000Z",
      }),
    );

    await renderPanelReady();

    expect(screen.getByRole("checkbox", { name: "Save to Markdown" })).toBeChecked();
  });

  it("persists notes to localStorage", async () => {
    const user = userEvent.setup();
    await renderPanelReady();

    await user.type(screen.getByLabelText("Dogfood notes"), "Recovery felt solid.");

    await waitFor(() => {
      const stored = JSON.parse(
        localStorage.getItem(planDogfoodStorageKey(sessionDescriptor)) ?? "{}",
      );
      expect(stored.notes).toContain("Recovery felt solid.");
    });
  });

  it("reset clears only dogfood state, not plan canvas storage", async () => {
    const user = userEvent.setup();
    const canvasKey = sessionDescriptor.planningDocument.storageKey;
    localStorage.setItem(canvasKey, JSON.stringify({ doc: "board-content" }));
    localStorage.setItem(
      planDogfoodStorageKey(sessionDescriptor),
      JSON.stringify({
        checked: { "open-plan": true },
        notes: "Keep this out after reset",
        updatedAt: "2026-07-09T00:00:00.000Z",
      }),
    );

    await renderPanelReady();
    await user.type(screen.getByLabelText("Dogfood notes"), " extra");
    await user.click(screen.getByRole("button", { name: "Reset dogfood checklist" }));

    expect(localStorage.getItem(planDogfoodStorageKey(sessionDescriptor))).toBeNull();
    expect(localStorage.getItem(canvasKey)).toContain("board-content");
    expect(screen.getByLabelText("Dogfood notes")).toHaveValue("");
    expect(screen.getByRole("checkbox", { name: "Open /plan for the intended campaign/session" })).not.toBeChecked();
  });

  it("copies dogfood report to clipboard and shows success message", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    await renderPanelReady("Saved to Markdown");
    await user.click(screen.getByRole("checkbox", { name: "Open /plan for the intended campaign/session" }));
    await user.type(screen.getByLabelText("Dogfood notes"), "Useful source preview.");
    await user.click(screen.getByRole("button", { name: "Copy dogfood report" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(1);
    });
    const copied = String(writeText.mock.calls[0]?.[0] ?? "");
    expect(copied).toContain("# /plan Dogfood Report");
    expect(copied).toContain("Campaign: Longmont C2");
    expect(copied).toContain("Useful source preview.");
    expect(copied).toContain("Save status: Saved to Markdown");
    expect(screen.getByText("Dogfood report copied.")).toBeInTheDocument();
  });

  it("shows report preview when clipboard copy fails", async () => {
    const user = userEvent.setup();
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: vi.fn().mockRejectedValue(new Error("denied")),
      },
    });

    await renderPanelReady();
    await user.click(screen.getByRole("button", { name: "Copy dogfood report" }));

    expect(
      await screen.findByText(/Could not copy to clipboard/i),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("Report preview"));
    expect(screen.getByText(/# \/plan Dogfood Report/)).toBeInTheDocument();
  });
});
