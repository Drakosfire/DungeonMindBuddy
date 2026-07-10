import { describe, expect, it } from "vitest";

import type { PlanSessionDescriptor } from "../types";
import { buildPlanDogfoodReport } from "./planDogfoodReport";
import { PLAN_DOGFOOD_CHECKLIST } from "./planDogfoodState";

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
    storageKey: "dmb.planCanvas.longmont-c2.23.longmont-c2-session-23-prep",
    status: "local_draft",
  },
};

describe("buildPlanDogfoodReport", () => {
  it("includes campaign, sessions, target path, save status, checklist, and notes", () => {
    const report = buildPlanDogfoodReport({
      sessionDescriptor,
      checklist: PLAN_DOGFOOD_CHECKLIST,
      state: {
        checked: { "open-plan": true, "add-real-notes": true },
        notes: "Save felt trustworthy.",
        updatedAt: "2026-07-09T00:00:00.000Z",
      },
      saveStatusLabel: "Saved to Markdown",
      generatedAt: "2026-07-09T12:00:00.000Z",
    });

    expect(report).toContain("# /plan Dogfood Report");
    expect(report).toContain("Campaign: Longmont C2");
    expect(report).toContain("Prep session: 23");
    expect(report).toContain("Memory session: 21");
    expect(report).toContain("Document: Longmont C2 Session 23 Prep");
    expect(report).toContain("Target path: corpus/eldyrwild-markdown");
    expect(report).toContain("Save status: Saved to Markdown");
    expect(report).toContain("Generated at: 2026-07-09T12:00:00.000Z");
    expect(report).toContain("- [x] Open /plan for the intended campaign/session");
    expect(report).toContain("- [x] Add real prep notes to the board");
    expect(report).toContain("- [ ] Stop the dev server");
    expect(report).toContain("Save felt trustworthy.");
    expect(report).toContain("## Suggested follow-ups");
  });

  it("uses placeholder when notes are empty", () => {
    const report = buildPlanDogfoodReport({
      sessionDescriptor,
      checklist: PLAN_DOGFOOD_CHECKLIST,
      state: { checked: {}, notes: "", updatedAt: null },
      saveStatusLabel: "Local draft",
      generatedAt: "2026-07-09T12:00:00.000Z",
    });

    expect(report).toContain("_No notes recorded._");
  });
});
