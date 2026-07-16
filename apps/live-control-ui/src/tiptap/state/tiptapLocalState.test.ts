import { vi } from "vitest";

import { FIXTURE_DOC_ID } from "../../planSurface/config/planSessionDescriptor";
import {
  northGateSessionRunbookStarterContent,
  runbookDescriptorFromRecord,
  tiptapRunbookStorageKey,
} from "../descriptors/tiptapRunbookDescriptors";
import {
  buildInitialWorkspaceDocumentLocalState,
  clearWorkspaceDocumentLocalState,
  readWorkspaceDocumentLocalState,
  workspaceDocumentStorageKey,
  writeWorkspaceDocumentLocalState,
  WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
} from "./tiptapLocalState";

const northGateDescriptor = runbookDescriptorFromRecord({
  document_id: FIXTURE_DOC_ID,
  title: "North Gate Session Runbook",
  campaign_id: "longmont-c2",
  target_session: 23,
  target_relpath: "evals/c2_live_prep/mireward-prep/content/tiptap/north-gate-session-runbook.md",
  revision: 1,
}, northGateSessionRunbookStarterContent);

const otherDescriptor = runbookDescriptorFromRecord({
  document_id: "22222222-2222-4222-8222-222222222222",
  title: "Other Runbook",
  campaign_id: "longmont-c2",
  target_session: 24,
  target_relpath: "evals/c2_live_prep/mireward-prep/content/tiptap/other.md",
  revision: 1,
});

describe("Workspace document local state", () => {
  it("builds descriptor-derived initial state for the session runbook", () => {
    const now = "2026-06-18T12:00:00.000Z";
    const state = buildInitialWorkspaceDocumentLocalState({
      documentId: northGateDescriptor.documentId,
      title: northGateDescriptor.title,
      campaignId: northGateDescriptor.campaignId,
      kind: "runbook",
      targetSession: northGateDescriptor.session,
      surface: "runbook",
      starterContent: northGateDescriptor.starterContent,
      now,
    });

    expect(workspaceDocumentStorageKey(FIXTURE_DOC_ID)).toBe(tiptapRunbookStorageKey(northGateDescriptor));
    expect(state).toMatchObject({
      schema_version: WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA,
      document_id: FIXTURE_DOC_ID,
      title: "North Gate Session Runbook",
      campaign_id: "longmont-c2",
      target_session: 23,
      surface: "runbook",
      dirty: false,
      created_at: now,
      updated_at: now,
      last_local_save_at: now,
    });
    expect(state.exported_markdown).toContain("# C2S23 North Gate Session Runbook");
  });

  it("reads valid document-keyed local state", () => {
    const state = buildInitialWorkspaceDocumentLocalState({
      documentId: northGateDescriptor.documentId,
      title: northGateDescriptor.title,
      campaignId: northGateDescriptor.campaignId,
      kind: "runbook",
      targetSession: northGateDescriptor.session,
      surface: "runbook",
      starterContent: northGateDescriptor.starterContent,
      now: "2026-06-18T12:00:00.000Z",
    });
    const storage = { getItem: vi.fn(() => JSON.stringify(state)) };

    expect(readWorkspaceDocumentLocalState(storage, FIXTURE_DOC_ID)).toEqual(state);
    expect(storage.getItem).toHaveBeenCalledWith(workspaceDocumentStorageKey(FIXTURE_DOC_ID));
  });

  it("rejects mismatched document ids", () => {
    const state = buildInitialWorkspaceDocumentLocalState({
      documentId: FIXTURE_DOC_ID,
      title: northGateDescriptor.title,
      campaignId: northGateDescriptor.campaignId,
      kind: "runbook",
      targetSession: northGateDescriptor.session,
      surface: "runbook",
      starterContent: northGateDescriptor.starterContent,
    });

    expect(readWorkspaceDocumentLocalState({ getItem: () => JSON.stringify(state) }, "other-id")).toBeNull();
  });

  it("writes and reads two documents under isolated keys", () => {
    const values = new Map<string, string>();
    const storage = {
      getItem: vi.fn((key: string) => values.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => { values.set(key, value); }),
    };
    const sessionState = buildInitialWorkspaceDocumentLocalState({
      documentId: northGateDescriptor.documentId,
      title: northGateDescriptor.title,
      campaignId: northGateDescriptor.campaignId,
      kind: "runbook",
      targetSession: northGateDescriptor.session,
      surface: "runbook",
      starterContent: northGateDescriptor.starterContent,
      now: "2026-06-18T12:00:00.000Z",
    });
    const otherState = buildInitialWorkspaceDocumentLocalState({
      documentId: otherDescriptor.documentId,
      title: otherDescriptor.title,
      campaignId: otherDescriptor.campaignId,
      kind: "runbook",
      targetSession: otherDescriptor.session,
      surface: "runbook",
      starterContent: otherDescriptor.starterContent,
      now: "2026-06-18T12:00:00.000Z",
    });

    writeWorkspaceDocumentLocalState(storage, sessionState);
    writeWorkspaceDocumentLocalState(storage, otherState);

    expect(tiptapRunbookStorageKey(northGateDescriptor)).not.toBe(tiptapRunbookStorageKey(otherDescriptor));
    expect(readWorkspaceDocumentLocalState(storage, FIXTURE_DOC_ID)?.document_id).toBe(FIXTURE_DOC_ID);
    expect(readWorkspaceDocumentLocalState(storage, otherDescriptor.documentId)?.document_id)
      .toBe(otherDescriptor.documentId);
  });

  it("clears state under the document key", () => {
    const removeItem = vi.fn();
    clearWorkspaceDocumentLocalState({ removeItem }, FIXTURE_DOC_ID);
    expect(removeItem).toHaveBeenCalledWith(workspaceDocumentStorageKey(FIXTURE_DOC_ID));
  });
});
