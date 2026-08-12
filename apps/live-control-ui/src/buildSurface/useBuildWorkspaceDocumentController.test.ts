import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { WorkspaceDocumentRecord } from "../api/types";
import { writeBuildLastCampaignId } from "./buildBareEntryCampaign";
import { useBuildWorkspaceDocumentController } from "./useBuildWorkspaceDocumentController";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    listWorkspaceDocuments: vi.fn(),
    createWorkspaceDocument: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
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
        world_id: "eldyrwild",
      }),
    );
  });

  it("rejects create campaigns outside admissible Build scope without POSTing", async () => {
    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.createDocument({ title: "Foreign", campaignId: "eldyrwild" });
    });

    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(result.current.createError).toMatch(/Choose a campaign/i);
  });

  it("allows create into an admissible loadable campaign such as eldyrwild", async () => {
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [
        buildRecord(DOC_A),
        buildRecord(DOC_B, { campaign_id: "eldyrwild", title: "Eldyrwild Source" }),
      ],
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(
      buildRecord("33333333-3333-4333-8333-333333333333", {
        title: "Eldyrwild Lore",
        campaign_id: "eldyrwild",
      }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, { title: "Eldyrwild Lore", campaign_id: "eldyrwild" }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));
    expect(result.current.creatableCampaignIds).toContain("eldyrwild");

    await act(async () => {
      result.current.createDocument({ title: "Eldyrwild Lore", campaignId: "eldyrwild" });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.campaign_id).toBe("eldyrwild");
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Eldyrwild Lore",
        campaign_id: "eldyrwild",
        kind: "worldbuilding_source",
      }),
    );
  });

  it("suggests admitted loadable campaigns for New Source prefill", async () => {
    writeBuildLastCampaignId("longmont-c2");
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      mockSnapshot(DOC_A, { campaign_id: "eldyrwild" }),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}&campaign=`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    expect(result.current.creatableCampaignIds).toContain("eldyrwild");
    expect(result.current.suggestedCreateCampaignId).toBe("eldyrwild");
  });

  it("does not suggest campaigns outside creatable choices on blank campaign=", async () => {
    writeBuildLastCampaignId("longmont-c2");
    window.history.pushState({}, "", "/build?campaign=");

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    expect(result.current.suggestedCreateCampaignId).toBeNull();
  });

  it("activation failure retains A; Retry Open B does not POST again", async () => {
    let bAttempts = 0;
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(
      buildRecord(DOC_B, { title: "Ironveil Property", campaign_id: "longmont-c2" }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) => {
      if (id === DOC_B) {
        bAttempts += 1;
        if (bAttempts === 1) throw new Error("activation failed");
        return mockSnapshot(DOC_B, { title: "Ironveil Property", campaign_id: "longmont-c2" });
      }
      return mockSnapshot(id);
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.createDocument({ title: "Ironveil Property", campaignId: "longmont-c2" });
    });

    await waitFor(() => {
      expect(result.current.activationError).toMatch(/activation failed|Failed to open/i);
    });
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.retryCreatedDocument();
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(result.current.activationError).toBeNull();
  });

  it("superseded create does not activate after later navigation", async () => {
    let resolveCreate:
      | ((value: WorkspaceDocumentRecord) => void)
      | null = null;
    vi.mocked(liveApi.createWorkspaceDocument).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve;
        }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.createDocument({ title: "Pending", campaignId: "longmont-c2" });
    });

    act(() => {
      result.current.selectDocument(DOC_B);
    });
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_B));

    await act(async () => {
      resolveCreate?.(buildRecord(DOC_A, { title: "Pending", campaign_id: "longmont-c2", document_id: "33333333-3333-4333-8333-333333333333" }));
      await Promise.resolve();
    });

    expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("history.back restores A; failed history target keeps A and restores URL", async () => {
    const DOC_C = "33333333-3333-4333-8333-333333333333";
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) => {
      if (id === DOC_C) throw new Error("gone");
      return mockSnapshot(id);
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}&campaign=longmont-c1`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    act(() => {
      result.current.selectDocument(DOC_B);
    });
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_B));

    await act(async () => {
      const popped = new Promise<void>((resolve) => {
        window.addEventListener("popstate", () => resolve(), { once: true });
      });
      window.history.back();
      await popped;
    });
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));
    expect(new URLSearchParams(window.location.search).get("documentId")).toBe(DOC_A);

    await act(async () => {
      const popped = new Promise<void>((resolve) => {
        window.addEventListener("popstate", () => resolve(), { once: true });
      });
      window.history.forward();
      await popped;
    });
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_B));

    // Corrupt forward target in history by replacing current entry, then back to A, then
    // forward into a missing document — A must remain and URL must be restored.
    window.history.pushState({}, "", `/build?documentId=${DOC_C}&campaign=longmont-c1`);
    await act(async () => {
      window.dispatchEvent(new PopStateEvent("popstate"));
    });
    await waitFor(() => {
      expect(result.current.switchError).toMatch(/Could not open that source/i);
    });
    expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    expect(new URLSearchParams(window.location.search).get("documentId")).toBe(DOC_B);
  });

  it("does not expose documentId for Canvas until admission completes", async () => {
    let resolveSnapshot: ((value: ReturnType<typeof mockSnapshot>) => void) | null = null;
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveSnapshot = resolve;
        }),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.loadStatus).toBe("loading"));
    expect(result.current.activeDocumentId).toBeNull();
    expect(result.current.activeRecord).toBeNull();

    await act(async () => {
      resolveSnapshot?.(mockSnapshot(DOC_A));
      await Promise.resolve();
    });
    await waitFor(() => expect(result.current.activeDocumentId).toBe(DOC_A));
  });

  it("rejects direct-link discarded records without mounting Canvas", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      mockSnapshot(DOC_A, { status: "discarded" }),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.loadStatus).toBe("error"));
    expect(result.current.activeDocumentId).toBeNull();
    expect(result.current.activeRecord).toBeNull();
  });

  it("rejects direct-link non-worldbuilding records without mounting Canvas", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(
      mockSnapshot(DOC_A, { kind: "plan", target_relpath: "out/workspace/plan/x.md" }),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.loadStatus).toBe("error"));
    expect(result.current.activeDocumentId).toBeNull();
    expect(result.current.activeRecord).toBeNull();
  });

  it("importSourceDocument creates once then source_imports and activates", async () => {
    const imported = buildRecord(DOC_B, {
      title: "Hesta's Apothecary",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
      target_relpath: `corpus/eldyrwild-markdown/_dungeonbuddy/sources/${DOC_B}/source.md`,
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(imported);
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "confirm-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: { ...imported, content_status: "committed", revision: 2 },
      normalized_content_sha256: "sha",
      writer_ok: true,
      diagnostics: [],
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        title: "Hesta's Apothecary",
        campaign_id: "longmont-c2",
        world_id: "eldyrwild",
        content_status: "committed",
        revision: 2,
      }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Hesta's Apothecary",
        campaignId: "longmont-c2",
        markdown: "# Hesta\n\n| a | b |\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({
        document_id: DOC_B,
        write_mode: "source_import",
      }),
    );
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({
        document_id: DOC_B,
        write_mode: "source_import",
      }),
    );
  });

  it("failed import retains created record and retry does not POST again", async () => {
    const imported = buildRecord(DOC_B, {
      title: "Retry Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(imported);
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockRejectedValue(new Error("prepare failed"));
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Retry Source",
        campaignId: "longmont-c2",
        markdown: "# Retry\n",
      });
    });

    await waitFor(() => {
      expect(result.current.importError).toMatch(/prepare failed/i);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);

    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "confirm-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: { ...imported, content_status: "committed", revision: 2 },
      normalized_content_sha256: "sha",
      writer_ok: true,
      diagnostics: [],
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, { content_status: "committed", revision: 2 }),
    );

    await act(async () => {
      result.current.retryImportSource({ markdown: "# Retry\n" });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("post-commit import activation failure retries open without prepare or commit", async () => {
    const imported = buildRecord(DOC_B, {
      title: "Imported Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(imported);
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "confirm-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: { ...imported, content_status: "committed", revision: 2 },
      normalized_content_sha256: "sha",
      writer_ok: true,
      diagnostics: [],
    });

    let activationAttempts = 0;
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) => {
      if (id === DOC_B) {
        activationAttempts += 1;
        if (activationAttempts === 1) {
          throw new Error("activation failed");
        }
        return mockSnapshot(DOC_B, {
          title: "Imported Source",
          campaign_id: "longmont-c2",
          content_status: "committed",
          revision: 2,
        });
      }
      return mockSnapshot(id);
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported Source",
        campaignId: "longmont-c2",
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activationError).toMatch(/Source imported; could not open it yet/i);
    });
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.retryCreatedDocument();
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(result.current.activationError).toBeNull();
  });

  it("does not POST a second create when import is already in flight", async () => {
    let resolveCreate: ((value: WorkspaceDocumentRecord) => void) | null = null;
    const imported = buildRecord(DOC_B, {
      title: "Overlapping Import",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveCreate = resolve;
        }),
    );
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "confirm-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_B,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: { ...imported, content_status: "committed", revision: 2 },
      normalized_content_sha256: "sha",
      writer_ok: true,
      diagnostics: [],
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, { content_status: "committed", revision: 2 }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Overlapping Import",
        campaignId: "longmont-c2",
        markdown: "# First\n",
      });
    });

    await act(async () => {
      result.current.importSourceDocument({
        title: "Overlapping Import",
        campaignId: "longmont-c2",
        markdown: "# Second\n",
      });
    });

    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);

    await act(async () => {
      resolveCreate?.(imported);
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(result.current.creating).toBe(false);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
  });

  it("does not reuse a blank New Source record for a fresh Import submit", async () => {
    const blankSource = buildRecord(DOC_B, {
      title: "Blank Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    const imported = buildRecord("33333333-3333-4333-8333-333333333333", {
      title: "Imported Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    vi.mocked(liveApi.createWorkspaceDocument)
      .mockResolvedValueOnce(blankSource)
      .mockResolvedValueOnce(imported);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, { campaign_id: "longmont-c2", content_status: "committed", revision: 2 }),
    );
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: imported.document_id,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "confirm-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: imported.document_id,
      title: imported.title,
      target_relpath: imported.target_relpath ?? "",
      target_display_path: imported.target_relpath ?? "",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: { ...imported, content_status: "committed", revision: 2 },
      normalized_content_sha256: "sha",
      writer_ok: true,
      diagnostics: [],
    });

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.createDocument({ title: "Blank Source", campaignId: "longmont-c2" });
    });
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_B));
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported Source",
        campaignId: "longmont-c2",
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(imported.document_id);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ document_id: imported.document_id }),
    );
  });
});
