import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import { useBuildWorkspaceDocumentController } from "./useBuildWorkspaceDocumentController";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    listWorkspaceDocuments: vi.fn(),
    createWorkspaceDocument: vi.fn(),
  };
});

const DOC_A = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";

function buildRecord(
  documentId: string,
  overrides: Partial<WorkspaceDocumentRecord> = {},
): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: documentId,
    title: `Source ${documentId.slice(0, 4)}`,
    campaign_id: "longmont-c1",
    target_session: null,
    kind: "worldbuilding_source",
    target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
    status: "active",
    content_status: "draft",
    revision: 1,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
    source_domain: "worldbuilding",
    document_class: "lore",
    authority_state: "draft",
    visibility_state: "internal",
    ...overrides,
  };
}

function mockSnapshot(documentId: string, overrides: Partial<WorkspaceDocumentRecord> = {}) {
  const record = buildRecord(documentId, overrides);
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record,
    markdown: "",
    content_sha256: `sha-${documentId}`,
    file_fingerprint: "absent" as const,
    file_exists: false,
    loaded_revision: 1,
  };
}

describe("useBuildWorkspaceDocumentController", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.pushState({}, "", "/build");
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [buildRecord(DOC_A), buildRecord(DOC_B, { campaign_id: "longmont-c2" })],
    });
  });

  it("starts empty on bare /build without creating", async () => {
    const { result } = renderHook(() => useBuildWorkspaceDocumentController());

    await waitFor(() => {
      expect(result.current.loadStatus).toBe("empty");
    });
    expect(result.current.activeRecord).toBeNull();
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("lists worldbuilding sources across campaigns", async () => {
    const { result } = renderHook(() => useBuildWorkspaceDocumentController());

    await waitFor(() => {
      expect(result.current.listStatus).toBe("ready");
    });
    expect(liveApi.listWorkspaceDocuments).toHaveBeenCalledWith({
      kind: "worldbuilding_source",
      status: "active",
    });
    expect(result.current.documents).toHaveLength(2);
  });

  it("admits document from URL and canonicalizes campaign", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      mockSnapshot(DOC_A, { campaign_id: "longmont-c1" }),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}&campaign=longmont-c2`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());

    await waitFor(() => {
      expect(result.current.loadStatus).toBe("ready");
    });
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    expect(new URLSearchParams(window.location.search).get("campaign")).toBe("longmont-c1");
  });

  it("selectDocument switches after successful resolve", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    act(() => {
      result.current.selectDocument(DOC_B);
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
  });

  it("failed switch keeps document A and sets switchError", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) => {
      if (id === DOC_B) throw new Error("missing");
      return mockSnapshot(id);
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    act(() => {
      result.current.selectDocument(DOC_B);
    });

    await waitFor(() => {
      expect(result.current.switchError).toMatch(/Could not open that source/i);
    });
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
  });

  it("stale generation does not clobber a newer selection", async () => {
    let resolveB: ((value: ReturnType<typeof mockSnapshot>) => void) | null = null;
    const deferredB = new Promise<ReturnType<typeof mockSnapshot>>((resolve) => {
      resolveB = resolve;
    });

    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) => {
      if (id === DOC_B) return deferredB;
      return mockSnapshot(id);
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    act(() => {
      result.current.selectDocument(DOC_B);
    });
    act(() => {
      result.current.selectDocument(DOC_A);
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    });

    await act(async () => {
      resolveB?.(mockSnapshot(DOC_B));
      await Promise.resolve();
    });

    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
  });

  it("createDocument performs one POST then activates", async () => {
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(
      buildRecord(DOC_B, { title: "Ironveil Property", campaign_id: "longmont-c2" }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, { title: "Ironveil Property", campaign_id: "longmont-c2" }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.createDocument({ title: "Ironveil Property", campaignId: "longmont-c2" });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Ironveil Property",
        campaign_id: "longmont-c2",
        kind: "worldbuilding_source",
      }),
    );
  });
});
