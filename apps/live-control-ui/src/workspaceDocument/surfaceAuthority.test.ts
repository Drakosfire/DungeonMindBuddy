import { describe, expect, it } from "vitest";

import type { WorkspaceDocumentRecord } from "../api/types";
import { assertSurfaceAuthority } from "./surfaceAuthority";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function record(overrides: Partial<WorkspaceDocumentRecord> = {}): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: DOC_ID,
    title: "World Lore",
    campaign_id: "eldyrwild",
    target_session: null,
    kind: "worldbuilding_source",
    target_relpath: `out/workspace/worldbuilding/${DOC_ID}.md`,
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

describe("assertSurfaceAuthority", () => {
  it("rejects plan UUID on build surface before local state", () => {
    const result = assertSurfaceAuthority({
      requestedDocumentId: DOC_ID,
      requestedKind: "worldbuilding_source",
      surface: "build",
      record: record({ kind: "plan", target_session: 3 }),
      loadedRevision: 1,
    });
    expect(result.ok).toBe(false);
    expect(result.rejectCode).toBe("kind_mismatch");
  });

  it("rejects when requested kind matches but surface forbids it", () => {
    const result = assertSurfaceAuthority({
      requestedDocumentId: DOC_ID,
      requestedKind: "plan",
      surface: "build",
      record: record({ kind: "plan", target_session: 3 }),
      loadedRevision: 1,
    });
    expect(result.ok).toBe(false);
    expect(result.rejectCode).toBe("surface_kind_forbidden");
  });

  it("rejects discarded documents by default", () => {
    const result = assertSurfaceAuthority({
      requestedDocumentId: DOC_ID,
      requestedKind: "worldbuilding_source",
      surface: "build",
      record: record({ status: "discarded" }),
      loadedRevision: 1,
    });
    expect(result.ok).toBe(false);
    expect(result.rejectCode).toBe("discarded_not_supported");
  });

  it("accepts worldbuilding_source on build", () => {
    const result = assertSurfaceAuthority({
      requestedDocumentId: DOC_ID,
      requestedKind: "worldbuilding_source",
      surface: "build",
      record: record(),
      loadedRevision: 1,
    });
    expect(result.ok).toBe(true);
    expect(result.authoritativeKind).toBe("worldbuilding_source");
  });
});
