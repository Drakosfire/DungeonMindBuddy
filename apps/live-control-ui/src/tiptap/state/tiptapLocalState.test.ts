import { vi } from "vitest";

import { FIXTURE_DOC_ID } from "../../planSurface/config/planSessionDescriptor";
import {
  northGateSessionRunbookStarterContent,
  runbookDescriptorFromRecord,
  tiptapRunbookStorageKey,
} from "../descriptors/tiptapRunbookDescriptors";
import { PlayableIdentitySerializationError } from "../playable/playableElementIdentity";
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
      baseRevision: 1,
      baseContentSha256: "",
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
      baseRevision: 1,
      baseContentSha256: "",
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
      baseRevision: 1,
      baseContentSha256: "",
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
      baseRevision: 1,
      baseContentSha256: "",
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
      baseRevision: 1,
      baseContentSha256: "",
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

  it("does not build split-brain local state from unsafe playable starter content", () => {
    expect(() => buildInitialWorkspaceDocumentLocalState({
      documentId: northGateDescriptor.documentId,
      title: northGateDescriptor.title,
      campaignId: northGateDescriptor.campaignId,
      kind: "runbook",
      targetSession: northGateDescriptor.session,
      surface: "runbook",
      baseRevision: 1,
      baseContentSha256: "",
      starterContent: {
        type: "doc",
        content: [
          {
            type: "heading",
            attrs: { level: 2, playableElementKind: "scene", playableElementId: "scene:arrival" },
            content: [{ type: "text", text: "Arrival" }],
          },
          {
            type: "heading",
            attrs: { level: 2, playableElementKind: "scene", playableElementId: "scene:arrival" },
            content: [{ type: "text", text: "Harbor" }],
          },
        ],
      },
    })).toThrow(PlayableIdentitySerializationError);
  });

  it("clears state under the document key", () => {
    const removeItem = vi.fn();
    clearWorkspaceDocumentLocalState({ removeItem }, FIXTURE_DOC_ID);
    expect(removeItem).toHaveBeenCalledWith(workspaceDocumentStorageKey(FIXTURE_DOC_ID));
  });

  it("migrates v2 local state on read", () => {
    const v2 = {
      schema_version: "dmb_workspace_document_local_state_v2",
      document_id: FIXTURE_DOC_ID,
      title: "Legacy",
      campaign_id: "longmont-c2",
      kind: "runbook",
      target_session: 23,
      surface: "runbook",
      tiptap_json: { type: "doc", content: [] },
      exported_markdown: "# Legacy\n",
      dirty: false,
      created_at: "2026-06-18T12:00:00.000Z",
      updated_at: "2026-06-18T12:00:00.000Z",
      last_local_save_at: "2026-06-18T12:00:00.000Z",
    };
    const migrated = readWorkspaceDocumentLocalState({ getItem: () => JSON.stringify(v2) }, FIXTURE_DOC_ID);
    expect(migrated?.schema_version).toBe(WORKSPACE_DOCUMENT_LOCAL_STATE_SCHEMA);
    expect(migrated?.base_revision).toBe(0);
    expect(migrated?.base_content_sha256).toBe("");
  });
});
