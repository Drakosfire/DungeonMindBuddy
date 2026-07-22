import { describe, expect, it, vi } from "vitest";

import {
  createWorkspaceDocument,
  listWorkspaceDocuments,
  prepareTiptapMarkdownWrite,
} from "./liveApi";
import type {
  CreateWorkspaceDocumentRequest,
  TiptapMarkdownWritePrepareResponse,
  WorkspaceDocumentRecord,
} from "./types";

function worldbuildingRecord(overrides: Partial<WorkspaceDocumentRecord> = {}): WorkspaceDocumentRecord {
  const documentId = overrides.document_id ?? "11111111-1111-4111-8111-111111111111";
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: documentId,
    title: "World Lore",
    campaign_id: "eldyrwild",
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

describe("liveApi workspace worldbuilding contracts", () => {
  it("posts worldbuilding create payloads and returns registry-owned targets", async () => {
    const record = worldbuildingRecord();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(record), { status: 200, headers: { "Content-Type": "application/json" } }),
    );

    const request: CreateWorkspaceDocumentRequest = {
      title: "World Lore",
      campaign_id: "eldyrwild",
      kind: "worldbuilding_source",
      source_domain: "worldbuilding",
      document_class: "lore",
      authority_state: "draft",
      visibility_state: "internal",
    };
    const created = await createWorkspaceDocument(request);

    expect(created.target_relpath).toBe(`out/workspace/worldbuilding/${record.document_id}.md`);
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("/api/live/workspace-documents"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(request),
      }),
    );
    fetchMock.mockRestore();
  });

  it("lists worldbuilding_source documents by kind", async () => {
    const record = worldbuildingRecord();
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(
        JSON.stringify({
          schema_version: "dmb_workspace_document_registry_v1",
          records: [record],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );

    const listed = await listWorkspaceDocuments({ kind: "worldbuilding_source" });
    expect(listed.records).toHaveLength(1);
    expect(listed.records[0]?.kind).toBe("worldbuilding_source");
    expect(String(fetchMock.mock.calls[0]?.[0])).toContain("kind=worldbuilding_source");
    fetchMock.mockRestore();
  });

  it("surfaces prepare diagnostics when writer_ok is false", async () => {
    const prepare: TiptapMarkdownWritePrepareResponse = {
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: "11111111-1111-4111-8111-111111111111",
      title: "World Lore",
      target_relpath: "out/workspace/worldbuilding/11111111-1111-4111-8111-111111111111.md",
      target_display_path: "out/workspace/worldbuilding/11111111-1111-4111-8111-111111111111.md",
      registry_revision: 1,
      file_exists: false,
      writer_ok: false,
      writer_phase: "prepare",
      writer_confirm_token: null,
      writer_diff: "",
      warnings: ["Commit blocked: unsupported Markdown would be lossy."],
      diagnostics: ["line 2: unsupported Markdown block would be lossy on commit"],
    };
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(prepare), { status: 200, headers: { "Content-Type": "application/json" } }),
    );

    const response = await prepareTiptapMarkdownWrite({
      document_id: prepare.document_id,
      markdown: "| a | b |\n",
      expected_revision: 1,
    });
    expect(response.writer_ok).toBe(false);
    expect(response.writer_confirm_token).toBeNull();
    expect(response.diagnostics.some((item) => item.includes("lossy"))).toBe(true);
    fetchMock.mockRestore();
  });
});
