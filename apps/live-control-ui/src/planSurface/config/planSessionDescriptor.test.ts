import { describe, expect, it } from "vitest";

import { mockPlanView } from "../../test/fixtures";
import {
  buildPlanContextFromPlanView,
  createPlanSessionDescriptor,
  defaultPlanTargetRelpath,
  durablePlanTargetRelpath,
  fixturePlanDocumentDescriptor,
  fixturePlanSessionDescriptor,
  FIXTURE_DOC_ID,
  NoActivePlanningDocumentsError,
  planDocumentOptionLabel,
  planDocumentSelectionSearch,
  suggestNextPlanTargetSession,
  suggestedPlanCreatePayload,
  workspaceDocumentStorageKey,
  workspaceRecordToPlanDocumentDescriptor,
  fixtureWorkspaceDocumentRecord,
} from "./planSessionDescriptor";

describe("planSessionDescriptor", () => {
  it("does not invent live-1 as the memory session without an explicit override", () => {
    const planningDocument = fixturePlanDocumentDescriptor();
    const sessionDescriptor = createPlanSessionDescriptor(mockPlanView, planningDocument);
    expect(sessionDescriptor.campaignId).toBe("longmont-c2");
    expect(sessionDescriptor.campaignLabel).toBe("Longmont C2");
    expect(sessionDescriptor.liveSession).toBe(22);
    expect(sessionDescriptor.planningDocument.targetSession).toBe(23);
    expect(sessionDescriptor.memorySession).toBeNull();
    expect(sessionDescriptor.sourceStatusKind).toBe("unknown");
    expect(sessionDescriptor.sourceStatusLabel).toContain("World graph");
  });

  it("honors explicit memory session overrides from the URL context", () => {
    const planningDocument = fixturePlanDocumentDescriptor({ targetSession: 25 });
    const sessionDescriptor = createPlanSessionDescriptor(mockPlanView, planningDocument, {
      memorySession: 24,
    });
    expect(sessionDescriptor.memorySession).toBe(24);
    expect(sessionDescriptor.planningDocument.documentId).toBe(FIXTURE_DOC_ID);
    expect(sessionDescriptor.sourceStatusLabel).toContain("Session 24");
  });

  it("uses live session for ingest/tool fallback when memory focus is unset", () => {
    const planningDocument = fixturePlanDocumentDescriptor();
    const context = buildPlanContextFromPlanView(mockPlanView, planningDocument);
    expect(context.ingestSession).toBe(22);
    expect(context.headerLabel).toContain(planningDocument.title);
  });

  it("maps registry records to opaque plan document descriptors", () => {
    const record = fixtureWorkspaceDocumentRecord();
    const document = workspaceRecordToPlanDocumentDescriptor(record);
    expect(document.documentId).toBe(FIXTURE_DOC_ID);
    expect(document.title).toBe("C2 Session 23 Prep");
    expect(document.status).toBe("active");
    expect(document.contentStatus).toBe("draft");
    expect(document.targetRelpath).toBe(
      "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    );
  });

  it("keys local canvas storage only by opaque document id", () => {
    const docKey = workspaceDocumentStorageKey(FIXTURE_DOC_ID);
    const otherKey = workspaceDocumentStorageKey("22222222-2222-4222-8222-222222222222");
    expect(docKey).toBe(`dmb.workspaceDocument.${FIXTURE_DOC_ID}`);
    expect(docKey).not.toBe(otherKey);
  });

  it("suggests create metadata from live session without inventing document ids", () => {
    const suggested = suggestedPlanCreatePayload("longmont-c2", 22);
    expect(suggested.title).toBe("C2 Session 23 Prep");
    expect(suggested.target_session).toBe(23);
    expect(suggested.target_relpath).toBe(defaultPlanTargetRelpath("longmont-c2", 23));
  });

  it("provides a reusable fixture session descriptor", () => {
    const sessionDescriptor = fixturePlanSessionDescriptor();
    expect(sessionDescriptor.planningDocument.documentId).toBe(FIXTURE_DOC_ID);
  });
});

describe("suggestNextPlanTargetSession", () => {
  it("suggests liveSession + 1 when no active affinities exist", () => {
    expect(suggestNextPlanTargetSession(22, [])).toBe(23);
  });

  it("uses the prep frontier beyond the highest active affinity", () => {
    expect(suggestNextPlanTargetSession(22, [23, 27])).toBe(28);
  });

  it("uses live session when it is ahead of active affinities", () => {
    expect(suggestNextPlanTargetSession(25, [23])).toBe(26);
  });

  it("ignores nullish occupied entries", () => {
    expect(suggestNextPlanTargetSession(10, [null, undefined, 11])).toBe(12);
  });
});

describe("durablePlanTargetRelpath", () => {
  it("returns the default corpus path for known Longmont campaigns", () => {
    expect(durablePlanTargetRelpath("longmont-c2", 23)).toBe(
      defaultPlanTargetRelpath("longmont-c2", 23),
    );
  });

  it("returns null when the durable path cannot be derived", () => {
    expect(durablePlanTargetRelpath("unknown-campaign", 5)).toBeNull();
  });
});

describe("NoActivePlanningDocumentsError", () => {
  it("names the error class for empty active Plan lists", () => {
    const error = new NoActivePlanningDocumentsError("longmont-c2");
    expect(error.name).toBe("NoActivePlanningDocumentsError");
    expect(error.message).toContain("longmont-c2");
  });
});

describe("planDocumentSelectionSearch", () => {
  const DOC_A = "11111111-1111-4111-8111-111111111111";
  const DOC_B = "22222222-2222-4222-8222-222222222222";

  it("sets the exact documentId and preserves session + campaigns lens params", () => {
    const next = planDocumentSelectionSearch(
      "?session=longmont-c2:25&campaigns=longmont-c1,longmont-c2&documentId=" + DOC_A,
      DOC_B,
    );
    const params = new URLSearchParams(next);
    expect(params.get("documentId")).toBe(DOC_B);
    expect(params.get("session")).toBe("longmont-c2:25");
    expect(params.get("campaigns")).toBe("longmont-c1,longmont-c2");
  });

  it("preserves unrelated tool/dogfood state across selection", () => {
    const next = planDocumentSelectionSearch("?dogfood=1&tool=recap&documentId=" + DOC_A, DOC_B);
    const params = new URLSearchParams(next);
    expect(params.get("documentId")).toBe(DOC_B);
    expect(params.get("dogfood")).toBe("1");
    expect(params.get("tool")).toBe("recap");
  });

  it("adds documentId to a param-less search without inventing other params", () => {
    const next = planDocumentSelectionSearch("", DOC_B);
    expect(next).toBe(`?documentId=${DOC_B}`);
  });

  it("never writes the document title or target session into the search", () => {
    const next = planDocumentSelectionSearch("?documentId=" + DOC_A, DOC_B);
    expect(next).not.toContain("Prep");
    expect(next).not.toContain("session");
  });
});

describe("planDocumentOptionLabel", () => {
  it("uses the human title as the primary label", () => {
    const record = fixtureWorkspaceDocumentRecord({ title: "C2 Session 23 Prep", target_session: 23 });
    expect(planDocumentOptionLabel(record)).toBe("C2 Session 23 Prep");
  });

  it("appends target session only when the title does not already name it", () => {
    const record = fixtureWorkspaceDocumentRecord({ title: "Gate contingency", target_session: 26 });
    expect(planDocumentOptionLabel(record)).toBe("Gate contingency · Session 26");
  });

  it("falls back to an untitled label without exposing the UUID", () => {
    const record = fixtureWorkspaceDocumentRecord({ title: "  ", target_session: null });
    expect(planDocumentOptionLabel(record)).toBe("Untitled prep document");
  });
});
