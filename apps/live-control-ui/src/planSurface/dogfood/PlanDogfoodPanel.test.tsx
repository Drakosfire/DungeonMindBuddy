import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../../api/liveApi";
import type { PlanSessionDescriptor } from "../types";
import { createPlanCanvasStorageKey } from "../config/planSessionDescriptor";
import { PlanGraphReferenceResolverProvider } from "../reference/usePlanGraphReferenceResolver";
import { PlanDogfoodPanel } from "./PlanDogfoodPanel";
import {
  planDogfoodStorageKey,
  dogfoodModeFromLocation,
} from "./planDogfoodState";

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
    <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
      <PlanDogfoodPanel
        sessionDescriptor={sessionDescriptor}
        saveStatusLabel={saveStatusLabel}
      />
    </PlanGraphReferenceResolverProvider>,
  );
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
    vi.restoreAllMocks();
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "session", sessionId: "session-21" },
        admissibility: "gm",
      },
      summary: { nodeCount: 0, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
      nodes: [],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });
  });

  it("renders checklist and notes", () => {
    renderPanel();

    expect(screen.getByRole("region", { name: "Dogfood checklist" })).toBeInTheDocument();
    expect(
      screen.getByText('Ask: "What changed after the latest ingested recap?"'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Dogfood notes")).toBeInTheDocument();
    expect(screen.getByTestId("plan-world-graph-snapshot")).toHaveTextContent("World Graph unavailable.");
  });

  it("checking an item persists to localStorage", async () => {
    const user = userEvent.setup();
    renderPanel();

    const checkbox = screen.getByRole("checkbox", {
      name: /Ask: "What changed after the latest ingested recap\?"/,
    });
    await user.click(checkbox);

    expect(checkbox).toBeChecked();
    const stored = JSON.parse(
      localStorage.getItem(planDogfoodStorageKey(sessionDescriptor)) ?? "{}",
    );
    expect(stored.checked["ask-s1-question"]).toBe(true);
  });

  it("reloads checked state from localStorage on remount", () => {
    localStorage.setItem(
      planDogfoodStorageKey(sessionDescriptor),
      JSON.stringify({
        checked: { "answer-discloses-lag": true },
        notes: "",
        updatedAt: "2026-07-09T00:00:00.000Z",
      }),
    );

    renderPanel();

    expect(
      screen.getByRole("checkbox", {
        name: /Answer discloses memory lag/,
      }),
    ).toBeChecked();
  });

  it("persists notes to localStorage", async () => {
    const user = userEvent.setup();
    renderPanel();

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

    renderPanel();
    await user.type(screen.getByLabelText("Dogfood notes"), " extra");
    await user.click(screen.getByRole("button", { name: "Reset dogfood checklist" }));

    expect(localStorage.getItem(planDogfoodStorageKey(sessionDescriptor))).toBeNull();
    expect(localStorage.getItem(canvasKey)).toContain("board-content");
    expect(screen.getByLabelText("Dogfood notes")).toHaveValue("");
    expect(
      screen.getByRole("checkbox", {
        name: /Open \/plan\?dogfood=1&campaign=longmont-c2&session=24/,
      }),
    ).not.toBeChecked();
  });

  it("copies dogfood report to clipboard and shows success message", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    renderPanel("Saved to Markdown");
    await user.click(
      screen.getByRole("checkbox", {
        name: /Open \/plan\?dogfood=1&campaign=longmont-c2&session=24/,
      }),
    );
    await user.type(screen.getByLabelText("Dogfood notes"), "Lag disclosure felt useful.");
    await user.click(screen.getByRole("button", { name: "Copy dogfood report" }));

    await waitFor(() => {
      expect(writeText).toHaveBeenCalledTimes(1);
    });
    const copied = String(writeText.mock.calls[0]?.[0] ?? "");
    expect(copied).toContain("# /plan Dogfood Report");
    expect(copied).toContain("Campaign: Longmont C2");
    expect(copied).toContain("Lag disclosure felt useful.");
    expect(copied).toContain("Save status: Saved to Markdown");
    expect(copied).toContain("CreativeOperationSession");
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

    renderPanel();
    await user.click(screen.getByRole("button", { name: "Copy dogfood report" }));

    expect(
      await screen.findByText(/Could not copy to clipboard/i),
    ).toBeInTheDocument();
    fireEvent.click(screen.getByText("Report preview"));
    expect(screen.getByText(/# \/plan Dogfood Report/)).toBeInTheDocument();
  });
});
