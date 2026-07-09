import { describe, expect, it } from "vitest";

import { mockPlanView } from "../../test/fixtures";
import {
  buildPlanContextFromPlanView,
  createPlanCanvasStorageKey,
  createPlanDocumentDescriptor,
  createPlanSessionDescriptor,
  defaultSessionPrepDocumentId,
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

  it("creates only the generic session-prep document", () => {
    const context = buildPlanContextFromPlanView(mockPlanView);
    const document = createPlanDocumentDescriptor(context);
    expect(document.documentId).toBe("longmont-c2-session-23-prep");
    expect(document.title).toBe("C2 Session 23 Prep");
    expect(document.status).toBe("local_draft");
    expect(document.targetRelpath).toBe(
      "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    );
  });

  it("keys local canvas storage by campaign, prep session, and document id", () => {
    const prepKey = createPlanCanvasStorageKey({
      campaignId: "longmont-c2",
      prepSession: 24,
      documentId: "longmont-c2-session-24-prep",
    });
    const otherKey = createPlanCanvasStorageKey({
      campaignId: "longmont-c2",
      prepSession: 23,
      documentId: defaultSessionPrepDocumentId("longmont-c2", 23),
    });
    expect(prepKey).toBe("dmb.planCanvas.longmont-c2.24.longmont-c2-session-24-prep");
    expect(otherKey).toBe("dmb.planCanvas.longmont-c2.23.longmont-c2-session-23-prep");
    expect(prepKey).not.toBe(otherKey);
  });
});
