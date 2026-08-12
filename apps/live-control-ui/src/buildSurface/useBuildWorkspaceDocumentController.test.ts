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
    listWorldContainers: vi.fn(),
    createWorldContainer: vi.fn(),
    createWorkspaceDocument: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
    updateWorkspaceDocumentMetadata: vi.fn(),
  };
});

const DOC_A = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";

const GLASS_ORCHARD_WORLD = {
  schema_version: "dmb_world_container_record_v1" as const,
  world_id: "44444444-4444-4444-8444-444444444444",
  name: "The Glass Orchard",
  source_root_relpath: "corpus/the-glass-orchard-markdown",
  created_at: "2026-07-22T00:00:00Z",
};

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

function mockSnapshot(
  documentId: string,
  overrides: Partial<WorkspaceDocumentRecord> = {},
  snapshotOverrides: {
    markdown?: string;
    file_exists?: boolean;
  } = {},
) {
  const record = buildRecord(documentId, overrides);
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record,
    markdown: snapshotOverrides.markdown ?? "",
    content_sha256: `sha-${documentId}`,
    file_fingerprint: "absent" as const,
    file_exists: snapshotOverrides.file_exists ?? false,
    loaded_revision: 1,
  };
}

describe("useBuildWorkspaceDocumentController", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    window.history.pushState({}, "", "/build");
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [buildRecord(DOC_A), buildRecord(DOC_B, { campaign_id: "longmont-c2" })],
    });
    vi.mocked(liveApi.listWorldContainers).mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [],
    });
    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockImplementation(
      async (documentId, request) =>
        buildRecord(documentId, {
          title: request.title ?? `Source ${documentId.slice(0, 4)}`,
          revision: (request.expected_revision ?? 1) + 1,
        }),
    );
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
      result.current.createDocument({
        title: "Ironveil Property",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
      });
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
      result.current.createDocument({
        title: "Foreign",
        destination: { kind: "campaign", campaignId: "unknown-scope" },
      });
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
      result.current.createDocument({
        title: "Eldyrwild Lore",
        destination: { kind: "campaign", campaignId: "eldyrwild" },
      });
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
      result.current.createDocument({
        title: "Ironveil Property",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
      });
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
      result.current.createDocument({
        title: "Pending",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
      });
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
        destination: { kind: "campaign", campaignId: "longmont-c2" },
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
        destination: { kind: "campaign", campaignId: "longmont-c2" },
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
        return mockSnapshot(
          DOC_B,
          {
            title: "Imported Source",
            campaign_id: "longmont-c2",
            content_status: "committed",
            revision: 2,
          },
          {
            markdown: "# Imported\n",
            file_exists: true,
          },
        );
      }
      return mockSnapshot(id, {
        content_status: id === DOC_A ? "committed" : "draft",
        campaign_id: id === DOC_A ? "longmont-c1" : "longmont-c2",
      });
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported Source",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activationError).toMatch(/Source imported; could not open it yet/i);
    });
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);
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
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# First\n",
      });
    });

    await act(async () => {
      result.current.importSourceDocument({
        title: "Overlapping Import",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
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

  it("fresh Import creates a new identity even when an active draft exists", async () => {
    const blankSource = buildRecord(DOC_A, {
      title: "Blank Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
      content_status: "draft",
    });
    const imported = buildRecord(DOC_B, {
      title: "Imported Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    vi.mocked(liveApi.createWorkspaceDocument)
      .mockResolvedValueOnce(blankSource)
      .mockResolvedValueOnce(imported);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        campaign_id: "longmont-c2",
        world_id: "eldyrwild",
        content_status: id === DOC_A ? "draft" : "committed",
        revision: id === DOC_A ? 1 : 2,
        title: id === DOC_A ? "Blank Source" : "Imported Source",
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

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.createDocument({
        title: "Blank Source",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
      });
    });
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported Source",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(2);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ document_id: DOC_B }),
    );
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ document_id: DOC_B }),
    );
  });

  it("creates a new document when importing into a committed active source", async () => {
    const committedActive = buildRecord(DOC_A, {
      campaign_id: "longmont-c1",
      content_status: "committed",
      revision: 2,
    });
    const imported = buildRecord("33333333-3333-4333-8333-333333333333", {
      title: "Imported Source",
      campaign_id: "longmont-c1",
      world_id: "eldyrwild",
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValueOnce(imported);
    vi.mocked(liveApi.listWorkspaceDocuments).mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [committedActive, buildRecord(DOC_B, { campaign_id: "longmont-c2" })],
    });
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        campaign_id: id === DOC_A ? "longmont-c1" : "longmont-c2",
        content_status: id === imported.document_id ? "committed" : "committed",
        revision: 2,
      }),
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
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported Source",
        destination: { kind: "campaign", campaignId: "longmont-c1" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(imported.document_id);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({ document_id: imported.document_id }),
    );
  });

  it("fails ambiguous commit reconcile when snapshot markdown differs", async () => {
    const imported = buildRecord(DOC_B, {
      title: "Ambiguous Import",
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
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockRejectedValue(new Error("network lost"));
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(
        id,
        {
          campaign_id: "longmont-c2",
          world_id: "eldyrwild",
          content_status: id === DOC_B ? "committed" : "committed",
          revision: id === DOC_B ? 2 : 2,
        },
        {
          markdown: id === DOC_B ? "# Different content\n" : "",
          file_exists: id === DOC_B,
        },
      ),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Ambiguous Import",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.importError).toMatch(/does not match pasted Markdown/i);
    });
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
  });

  it("reconciles ambiguous commit via snapshot without a second commit", async () => {
    const imported = buildRecord(DOC_B, {
      title: "Ambiguous Import",
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
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockRejectedValue(new Error("network lost"));
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(
        id,
        {
          campaign_id: "longmont-c2",
          content_status: "committed",
          revision: 2,
        },
        {
          markdown: "# Imported\n",
          file_exists: true,
        },
      ),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Ambiguous Import",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.retryImportSource({ markdown: "# Imported\n" });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledTimes(1);
  });

  it("restores pending import from sessionStorage when URL still shows previous document", async () => {
    const blankSource = buildRecord(DOC_B, {
      title: "Blank Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
      content_status: "draft",
    });
    sessionStorage.setItem(
      "dmb.build.pendingSourceImport.v1",
      JSON.stringify({ documentId: DOC_B }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        campaign_id: id === DOC_B ? "longmont-c2" : "longmont-c1",
        world_id: "eldyrwild",
        content_status: id === DOC_B ? "draft" : "committed",
        revision: id === DOC_B ? 1 : 2,
      }),
    );
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_B,
      title: blankSource.title,
      target_relpath: blankSource.target_relpath ?? "",
      target_display_path: blankSource.target_relpath ?? "",
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
      title: blankSource.title,
      target_relpath: blankSource.target_relpath ?? "",
      target_display_path: blankSource.target_relpath ?? "",
      registry_revision: 2,
      committed_revision: 2,
      committed_record: { ...blankSource, content_status: "committed", revision: 2 },
      normalized_content_sha256: "sha",
      writer_ok: true,
      diagnostics: [],
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result, unmount } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);

    unmount();

    const { result: reloaded } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(reloaded.current.activeRecord?.document_id).toBe(DOC_A));
    expect(reloaded.current.pendingImportDocumentId).toBe(DOC_B);

    await act(async () => {
      reloaded.current.importSourceDocument({
        title: "Imported Source",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(reloaded.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("does not reuse active empty draft when campaign mismatches import form", async () => {
    const blankC1 = buildRecord(DOC_A, {
      title: "Blank C1",
      campaign_id: "longmont-c1",
      world_id: "eldyrwild",
      content_status: "draft",
    });
    const imported = buildRecord(DOC_B, {
      title: "Imported C2",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(imported);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        campaign_id: id === DOC_A ? "longmont-c1" : "longmont-c2",
        world_id: "eldyrwild",
        content_status: id === DOC_A ? "draft" : "committed",
        revision: id === DOC_A ? 1 : 2,
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
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));
    expect(result.current.activeRecord?.content_status).toBe("draft");

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported C2",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(1);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Imported C2",
        campaign_id: "longmont-c2",
      }),
    );
    void blankC1;
  });

  it("rejects committed pending recovery when campaign/world scope mismatches", async () => {
    const pendingCommitted = buildRecord(DOC_B, {
      title: "Pending C2",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
      content_status: "committed",
      revision: 2,
    });
    sessionStorage.setItem(
      "dmb.build.pendingSourceImport.v1",
      JSON.stringify({ documentId: DOC_B }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(
        id,
        {
          campaign_id: id === DOC_B ? "longmont-c2" : "longmont-c1",
          world_id: "eldyrwild",
          content_status: "committed",
          revision: 2,
          title: id === DOC_B ? pendingCommitted.title : `Source ${id.slice(0, 4)}`,
        },
        {
          markdown: id === DOC_B ? "# Imported\n" : "",
          file_exists: id === DOC_B,
        },
      ),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported C1",
        destination: { kind: "campaign", campaignId: "longmont-c1" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.importError).toMatch(/different destination/i);
    });
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(liveApi.commitTiptapMarkdownWrite).not.toHaveBeenCalled();
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);
  });

  it("updates title on pending reuse before source_import when form title differs", async () => {
    const blankSource = buildRecord(DOC_B, {
      title: "Blank Source",
      campaign_id: "longmont-c2",
      world_id: "eldyrwild",
      content_status: "draft",
    });
    const retitled = { ...blankSource, title: "Imported Source", revision: 2 };
    sessionStorage.setItem(
      "dmb.build.pendingSourceImport.v1",
      JSON.stringify({ documentId: DOC_B }),
    );
    vi.mocked(liveApi.updateWorkspaceDocumentMetadata).mockResolvedValue(retitled);
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        campaign_id: id === DOC_B ? "longmont-c2" : "longmont-c1",
        world_id: "eldyrwild",
        content_status: id === DOC_B ? "draft" : "committed",
        revision: id === DOC_B ? 1 : 2,
        title: id === DOC_B ? "Blank Source" : `Source ${id.slice(0, 4)}`,
      }),
    );
    vi.mocked(liveApi.prepareTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: DOC_B,
      title: retitled.title,
      target_relpath: retitled.target_relpath ?? "",
      target_display_path: retitled.target_relpath ?? "",
      registry_revision: 2,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "confirm-token",
      warnings: [],
      diagnostics: [],
    });
    vi.mocked(liveApi.commitTiptapMarkdownWrite).mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: DOC_B,
      title: retitled.title,
      target_relpath: retitled.target_relpath ?? "",
      target_display_path: retitled.target_relpath ?? "",
      registry_revision: 3,
      committed_revision: 3,
      committed_record: { ...retitled, content_status: "committed", revision: 3 },
      normalized_content_sha256: "sha",
      writer_ok: true,
      diagnostics: [],
    });
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported Source",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(liveApi.updateWorkspaceDocumentMetadata).toHaveBeenCalledWith(DOC_B, {
      title: "Imported Source",
      expected_revision: 1,
    });
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({
        document_id: DOC_B,
        expected_revision: 2,
      }),
    );
  });

  it("rejects whitespace-only markdown in importSourceDocument", async () => {
    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Whitespace",
        destination: { kind: "campaign", campaignId: "longmont-c2" },
        markdown: "   \n\t  \n",
      });
    });

    expect(result.current.importError).toMatch(/Paste non-empty Markdown/i);
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
  });

  it("new world create calls createWorldContainer once then posts document with matching world ids", async () => {
    vi.mocked(liveApi.createWorldContainer).mockResolvedValue(GLASS_ORCHARD_WORLD);
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(
      buildRecord(DOC_B, {
        title: "Orchard Lore",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
      }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        title: "Orchard Lore",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
      }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.createDocument({
        title: "Orchard Lore",
        destination: { kind: "new_world", name: "The Glass Orchard" },
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorldContainer).toHaveBeenCalledTimes(1);
    expect(liveApi.createWorldContainer).toHaveBeenCalledWith({ name: "The Glass Orchard" });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Orchard Lore",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
        kind: "worldbuilding_source",
      }),
    );
  });

  it("new world import calls createWorldContainer then source_import with exact world ids", async () => {
    const imported = buildRecord(DOC_B, {
      title: "Imported Orchard",
      campaign_id: GLASS_ORCHARD_WORLD.world_id,
      world_id: GLASS_ORCHARD_WORLD.world_id,
      target_relpath: `corpus/the-glass-orchard-markdown/_dungeonbuddy/sources/${DOC_B}/source.md`,
    });
    vi.mocked(liveApi.createWorldContainer).mockResolvedValue(GLASS_ORCHARD_WORLD);
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
        title: "Imported Orchard",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
        content_status: "committed",
        revision: 2,
      }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.importSourceDocument({
        title: "Imported Orchard",
        destination: { kind: "new_world", name: "The Glass Orchard" },
        markdown: "# Orchard\n",
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorldContainer).toHaveBeenCalledTimes(1);
    expect(liveApi.createWorldContainer).toHaveBeenCalledWith({ name: "The Glass Orchard" });
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        title: "Imported Orchard",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
      }),
    );
    expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(
      expect.objectContaining({
        document_id: DOC_B,
        write_mode: "source_import",
      }),
    );
  });

  it("retries source create after new world was created without minting a second distinct world", async () => {
    vi.mocked(liveApi.createWorldContainer).mockResolvedValue(GLASS_ORCHARD_WORLD);
    vi.mocked(liveApi.createWorkspaceDocument)
      .mockRejectedValueOnce(new Error("create failed"))
      .mockResolvedValueOnce(
        buildRecord(DOC_B, {
          title: "Retry Lore",
          campaign_id: GLASS_ORCHARD_WORLD.world_id,
          world_id: GLASS_ORCHARD_WORLD.world_id,
        }),
      );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        title: "Retry Lore",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
      }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.createDocument({
        title: "Retry Lore",
        destination: { kind: "new_world", name: "The Glass Orchard" },
      });
    });

    await waitFor(() => {
      expect(result.current.createError).toMatch(/world was created/i);
    });
    expect(liveApi.createWorldContainer).toHaveBeenCalledTimes(1);

    await act(async () => {
      result.current.createDocument({
        title: "Retry Lore",
        destination: { kind: "new_world", name: "The Glass Orchard" },
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorldContainer).toHaveBeenCalledTimes(2);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledTimes(2);
    for (const [request] of vi.mocked(liveApi.createWorkspaceDocument).mock.calls) {
      expect(request.world_id).toBe(GLASS_ORCHARD_WORLD.world_id);
      expect(request.campaign_id).toBe(GLASS_ORCHARD_WORLD.world_id);
    }
  });

  it("reconciles ambiguous world create via listWorldContainers without duplicate world", async () => {
    vi.mocked(liveApi.createWorldContainer).mockRejectedValueOnce(new Error("network lost"));
    vi.mocked(liveApi.listWorldContainers).mockResolvedValue({
      schema_version: "dmb_world_container_registry_v1",
      records: [GLASS_ORCHARD_WORLD],
    });
    vi.mocked(liveApi.createWorkspaceDocument).mockResolvedValue(
      buildRecord(DOC_B, {
        title: "Reconciled Orchard",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
      }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(id, {
        title: "Reconciled Orchard",
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
      }),
    );

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.listStatus).toBe("ready"));

    await act(async () => {
      result.current.createDocument({
        title: "Reconciled Orchard",
        destination: { kind: "new_world", name: "The Glass Orchard" },
      });
    });

    await waitFor(() => {
      expect(result.current.activeRecord?.document_id).toBe(DOC_B);
    });
    expect(liveApi.createWorldContainer).toHaveBeenCalledTimes(1);
    expect(liveApi.createWorkspaceDocument).toHaveBeenCalledWith(
      expect.objectContaining({
        campaign_id: GLASS_ORCHARD_WORLD.world_id,
        world_id: GLASS_ORCHARD_WORLD.world_id,
      }),
    );
  });

  it("fails closed when pending import destination world differs from form destination", async () => {
    const pendingCommitted = buildRecord(DOC_B, {
      title: "Pending World",
      campaign_id: GLASS_ORCHARD_WORLD.world_id,
      world_id: GLASS_ORCHARD_WORLD.world_id,
      content_status: "committed",
      revision: 2,
    });
    sessionStorage.setItem(
      "dmb.build.pendingSourceImport.v1",
      JSON.stringify({ documentId: DOC_B }),
    );
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockImplementation(async (id) =>
      mockSnapshot(
        id,
        {
          campaign_id: id === DOC_B ? GLASS_ORCHARD_WORLD.world_id : "longmont-c1",
          world_id: id === DOC_B ? GLASS_ORCHARD_WORLD.world_id : "eldyrwild",
          content_status: "committed",
          revision: 2,
          title: id === DOC_B ? pendingCommitted.title : `Source ${id.slice(0, 4)}`,
        },
        {
          markdown: id === DOC_B ? "# Imported\n" : "",
          file_exists: id === DOC_B,
        },
      ),
    );
    window.history.pushState({}, "", `/build?documentId=${DOC_A}`);

    const { result } = renderHook(() => useBuildWorkspaceDocumentController());
    await waitFor(() => expect(result.current.activeRecord?.document_id).toBe(DOC_A));
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);

    await act(async () => {
      result.current.importSourceDocument({
        title: "Different World Import",
        destination: { kind: "world", worldId: "eldyrwild" },
        markdown: "# Imported\n",
      });
    });

    await waitFor(() => {
      expect(result.current.importError).toMatch(/different destination/i);
    });
    expect(liveApi.createWorkspaceDocument).not.toHaveBeenCalled();
    expect(liveApi.createWorldContainer).not.toHaveBeenCalled();
    expect(result.current.activeRecord?.document_id).toBe(DOC_A);
    expect(result.current.pendingImportDocumentId).toBe(DOC_B);
  });
});
