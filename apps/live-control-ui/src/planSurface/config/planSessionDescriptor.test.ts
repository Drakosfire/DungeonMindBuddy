import { describe, expect, it } from "vitest";

import { mockPlanView } from "../../test/fixtures";
import {
  buildPlanContextFromPlanView,
  createPlanCanvasStorageKey,
  createPlanDocumentDescriptor,
  createPlanSessionDescriptor,
  defaultSessionPrepDocumentId,
  isLegacyNorthGateDocumentId,
  listSelectablePlanDocuments,
} from "./planSessionDescriptor";

describe("planSessionDescriptor", () => {
  it("derives prep session and campaign label from plan view", () => {
    const sessionDescriptor = createPlanSessionDescriptor(mockPlanView);
    expect(sessionDescriptor.campaignId).toBe("longmont-c2");
    expect(sessionDescriptor.campaignLabel).toBe("Longmont C2");
    expect(sessionDescriptor.liveSession).toBe(22);
    expect(sessionDescriptor.prepSession).toBe(23);
    expect(sessionDescriptor.memorySession).toBe(21);
    expect(sessionDescriptor.sourceStatusKind).toBe("unknown");
    expect(sessionDescriptor.sourceStatusLabel).toContain("Session 21");
  });

  it("creates a generic session-prep document by default", () => {
    const context = buildPlanContextFromPlanView(mockPlanView);
    const document = createPlanDocumentDescriptor(context);
    expect(document.documentId).toBe("longmont-c2-session-23-prep");
    expect(document.title).toBe("C2 Session 23 Prep");
    expect(document.starterKind).toBe("session_prep");
    expect(document.status).toBe("local_draft");
    expect(document.targetRelpath).toBe("TBD durable planning path");
  });

  it("keeps generic prep selectable when legacy north gate is active", () => {
    const sessionDescriptor = createPlanSessionDescriptor(mockPlanView, "north-gate-session-runbook");
    const options = listSelectablePlanDocuments(sessionDescriptor);
    expect(options[0].documentId).toBe("longmont-c2-session-23-prep");
    expect(options[0].starterKind).toBe("session_prep");
    expect(options.some((option) => option.documentId === "north-gate-session-runbook")).toBe(true);
  });

  it("keeps legacy north gate only when explicitly requested", () => {
    const context = buildPlanContextFromPlanView(mockPlanView);
    const document = createPlanDocumentDescriptor(context, "north-gate-session-runbook");
    expect(document.documentId).toBe("north-gate-session-runbook");
    expect(document.starterKind).toBe("legacy_north_gate");
    expect(isLegacyNorthGateDocumentId(document.documentId)).toBe(true);
    expect(isLegacyNorthGateDocumentId(defaultSessionPrepDocumentId("longmont-c2", 23))).toBe(false);
  });

  it("keys local canvas storage by campaign, prep session, and document id", () => {
    const prepKey = createPlanCanvasStorageKey({
      campaignId: "longmont-c2",
      prepSession: 24,
      documentId: "longmont-c2-session-24-prep",
    });
    const legacyKey = createPlanCanvasStorageKey({
      campaignId: "longmont-c2",
      prepSession: 23,
      documentId: "north-gate-session-runbook",
    });
    expect(prepKey).toBe("dmb.planCanvas.longmont-c2.24.longmont-c2-session-24-prep");
    expect(legacyKey).toBe("dmb.planCanvas.longmont-c2.23.north-gate-session-runbook");
    expect(prepKey).not.toBe(legacyKey);
  });
});
