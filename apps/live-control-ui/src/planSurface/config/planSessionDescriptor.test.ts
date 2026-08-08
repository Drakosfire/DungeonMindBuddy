import { beforeEach, describe, expect, it, vi } from "vitest";

import { mockPlanView } from "../../test/fixtures";
import {
  buildPlanContextFromPlanView,
  createPlanSessionDescriptor,
  defaultPlanTargetRelpath,
  fixturePlanDocumentDescriptor,
  fixturePlanSessionDescriptor,
  FIXTURE_DOC_ID,
  planCreatePayloadForTargetSession,
  replaceDocumentIdInLocationSearch,
  resolveOrCreatePlanForTargetSession,
  suggestedPlanCreatePayload,
  workspaceDocumentStorageKey,
  workspaceRecordToPlanDocumentDescriptor,
  fixtureWorkspaceDocumentRecord,
} from "./planSessionDescriptor";

vi.mock("../../api/liveApi", () => ({
  listWorkspaceDocuments: vi.fn(),
  createWorkspaceDocument: vi.fn(),
  getWorkspaceDocument: vi.fn(),
}));

import { createWorkspaceDocument, listWorkspaceDocuments } from "../../api/liveApi";

describe("planSessionDescriptor", () => {
  beforeEach(() => {
    vi.mocked(listWorkspaceDocuments).mockReset();
    vi.mocked(createWorkspaceDocument).mockReset();
  });

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

  it("builds create metadata for an explicit target session", () => {
    const payload = planCreatePayloadForTargetSession("longmont-c2", 26);
    expect(payload.title).toBe("C2 Session 26 Prep");
    expect(payload.target_session).toBe(26);
    expect(payload.target_relpath).toBe(defaultPlanTargetRelpath("longmont-c2", 26));
  });

  it("reuses an existing active plan for the target session", async () => {
    const existing = fixtureWorkspaceDocumentRecord({
      document_id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
      title: "C2 Session 26 Prep",
      target_session: 26,
      target_relpath: defaultPlanTargetRelpath("longmont-c2", 26),
    });
    vi.mocked(listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [fixtureWorkspaceDocumentRecord(), existing],
    });

    const result = await resolveOrCreatePlanForTargetSession({
      campaignId: "longmont-c2",
      targetSession: 26,
    });

    expect(result.created).toBe(false);
    expect(result.document.documentId).toBe(existing.document_id);
    expect(result.document.targetSession).toBe(26);
    expect(createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("creates a Session 26 prep plan when none exists", async () => {
    const created = fixtureWorkspaceDocumentRecord({
      document_id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
      title: "C2 Session 26 Prep",
      target_session: 26,
      target_relpath: defaultPlanTargetRelpath("longmont-c2", 26),
    });
    vi.mocked(listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [fixtureWorkspaceDocumentRecord()],
    });
    vi.mocked(createWorkspaceDocument).mockResolvedValue(created);

    const result = await resolveOrCreatePlanForTargetSession({
      campaignId: "longmont-c2",
      targetSession: 26,
    });

    expect(result.created).toBe(true);
    expect(result.document.documentId).toBe(created.document_id);
    expect(result.document.title).toBe("C2 Session 26 Prep");
    expect(createWorkspaceDocument).toHaveBeenCalledWith({
      title: "C2 Session 26 Prep",
      campaign_id: "longmont-c2",
      kind: "plan",
      target_session: 26,
      target_relpath: defaultPlanTargetRelpath("longmont-c2", 26),
    });
  });

  it("replaces documentId in the location search while preserving other params", () => {
    expect(replaceDocumentIdInLocationSearch("?campaign=longmont-c2&session=25", FIXTURE_DOC_ID))
      .toBe(`?campaign=longmont-c2&session=25&documentId=${FIXTURE_DOC_ID}`);
    expect(replaceDocumentIdInLocationSearch("", FIXTURE_DOC_ID))
      .toBe(`?documentId=${FIXTURE_DOC_ID}`);
  });

  it("provides a reusable fixture session descriptor", () => {
    const sessionDescriptor = fixturePlanSessionDescriptor();
    expect(sessionDescriptor.planningDocument.documentId).toBe(FIXTURE_DOC_ID);
  });
});
