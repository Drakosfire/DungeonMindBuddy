import { describe, expect, it } from "vitest";

import { NoActivePlanningDocumentsError } from "./config/planSessionDescriptor";
import { fixturePlanDocumentDescriptor } from "./config/planSessionDescriptor";
import {
  PLAN_LOCAL_DRAFT_WORK_KIND,
  adoptCreatedPlanIdentity,
  createPlanLocalDraftMetadata,
  formatPlanLocalDraftId,
  nextPlanShellState,
  planShellAgentDocumentId,
  planShellWorkObject,
  retainCreatedPlan,
} from "./planBlankAuthoringState";

const shell = {
  campaignId: "longmont-c2",
  liveSession: 22,
  memorySession: null,
};

describe("planBlankAuthoringState", () => {
  it("enters blank_ready when listing succeeds with zero Plans and no explicit document", () => {
    const draft = createPlanLocalDraftMetadata({
      campaignId: "longmont-c2",
      title: "C2 Session 23 Prep",
      targetSession: 23,
      localId: formatPlanLocalDraftId("draft-1"),
    });
    const state = nextPlanShellState({
      shell,
      blankDraft: draft,
      outcome: {
        requestedDocumentId: null,
        resolvedDocument: null,
        resolveError: new NoActivePlanningDocumentsError("longmont-c2"),
        selectorListAvailable: true,
        selectorListEmpty: true,
      },
    });
    expect(state.kind).toBe("blank_ready");
  });

  it("enters load_error when Plan inventory listing is unavailable", () => {
    const draft = createPlanLocalDraftMetadata({
      campaignId: "longmont-c2",
      title: "C2 Session 23 Prep",
      targetSession: 23,
      localId: formatPlanLocalDraftId("draft-1"),
    });
    const state = nextPlanShellState({
      shell,
      blankDraft: draft,
      outcome: {
        requestedDocumentId: null,
        resolvedDocument: null,
        resolveError: new Error("list unavailable"),
        selectorListAvailable: false,
        selectorListEmpty: false,
      },
    });
    expect(state.kind).toBe("load_error");
    if (state.kind === "load_error") {
      expect(state.inventoryUnavailable).toBe(true);
      expect(state.localDraft?.localId).toBe(draft.localId);
    }
  });

  it("enters load_error for explicit document failures", () => {
    const state = nextPlanShellState({
      shell,
      blankDraft: null,
      outcome: {
        requestedDocumentId: "missing-doc",
        resolvedDocument: null,
        resolveError: new Error("not found"),
        selectorListAvailable: true,
        selectorListEmpty: false,
      },
    });
    expect(state.kind).toBe("load_error");
  });

  it("keeps local work object separate from durable agent document id", () => {
    const draft = createPlanLocalDraftMetadata({
      campaignId: "longmont-c2",
      title: "C2 Session 23 Prep",
      targetSession: 23,
      localId: formatPlanLocalDraftId("draft-1"),
    });
    const blankState = {
      kind: "blank_ready" as const,
      draft,
      selectorListAvailable: true,
    };
    expect(planShellWorkObject(blankState)).toEqual({
      kind: PLAN_LOCAL_DRAFT_WORK_KIND,
      id: draft.localId,
    });
    expect(planShellAgentDocumentId(blankState)).toBeNull();

    const durable = adoptCreatedPlanIdentity(fixturePlanDocumentDescriptor());
    expect(planShellWorkObject(durable)).toEqual({
      kind: "document",
      id: fixturePlanDocumentDescriptor().documentId,
    });
    expect(planShellAgentDocumentId(durable)).toBe(fixturePlanDocumentDescriptor().documentId);
  });

  it("retains created plan identity without minting a replacement on promotion retry", () => {
    const draft = createPlanLocalDraftMetadata({
      campaignId: "longmont-c2",
      title: "C2 Session 23 Prep",
      targetSession: 23,
      localId: formatPlanLocalDraftId("draft-1"),
    });
    const blankState = {
      kind: "blank_ready" as const,
      draft,
      selectorListAvailable: true,
    };
    const promoting = retainCreatedPlan(blankState, "doc-created");
    expect(promoting.kind).toBe("promoting");
    if (promoting.kind === "promoting") {
      expect(promoting.retainedCreateId).toBe("doc-created");
    }
    expect(planShellAgentDocumentId(promoting)).toBe("doc-created");
    expect(planShellWorkObject(promoting)).toEqual({
      kind: "document",
      id: "doc-created",
    });
  });
});
