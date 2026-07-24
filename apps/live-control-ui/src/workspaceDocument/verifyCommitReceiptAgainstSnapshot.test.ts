import { describe, expect, it } from "vitest";

import type {
  TiptapMarkdownWriteCommitResponse,
  WorkspaceDocumentSnapshot,
} from "../api/types";
import { fixtureWorkspaceDocumentRecord } from "../planSurface/config/planSessionDescriptor";
import { verifyCommitReceiptAgainstSnapshot } from "./verifyCommitReceiptAgainstSnapshot";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function snapshot(overrides: Partial<WorkspaceDocumentSnapshot> = {}): WorkspaceDocumentSnapshot {
  const record = fixtureWorkspaceDocumentRecord({ document_id: DOC_ID, revision: 2 });
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown: "# Saved\n",
    content_sha256: "sha-match",
    file_fingerprint: "fp-match",
    file_exists: true,
    loaded_revision: 2,
    ...overrides,
  };
}

function receipt(overrides: Partial<TiptapMarkdownWriteCommitResponse> = {}): TiptapMarkdownWriteCommitResponse {
  return {
    schema_version: "dmb_tiptap_markdown_write_commit_v1",
    document_id: DOC_ID,
    title: "C2 Session 23 Prep",
    target_relpath: "corpus/prep.md",
    target_display_path: "corpus/prep.md",
    registry_revision: 2,
    committed_revision: 2,
    committed_record: fixtureWorkspaceDocumentRecord({ document_id: DOC_ID, revision: 2 }),
    normalized_content_sha256: "sha-match",
    writer_ok: true,
    diagnostics: [],
    ...overrides,
  };
}

describe("verifyCommitReceiptAgainstSnapshot", () => {
  it("agrees when all receipt fields match the snapshot", () => {
    expect(verifyCommitReceiptAgainstSnapshot(receipt(), snapshot())).toEqual({ ok: true });
  });

  it("agrees when receipt omits file_fingerprint", () => {
    expect(verifyCommitReceiptAgainstSnapshot(
      receipt({ file_fingerprint: null }),
      snapshot({ file_fingerprint: "fp-match" }),
    )).toEqual({ ok: true });
  });

  it("rejects document_id mismatch", () => {
    const result = verifyCommitReceiptAgainstSnapshot(
      receipt({ document_id: "22222222-2222-4222-8222-222222222222" }),
      snapshot(),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toMatch(/document_id/i);
  });

  it("rejects revision mismatch (N vs N+1)", () => {
    const result = verifyCommitReceiptAgainstSnapshot(
      receipt({ committed_revision: 2 }),
      snapshot({ loaded_revision: 3, record: fixtureWorkspaceDocumentRecord({ document_id: DOC_ID, revision: 3 }) }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toMatch(/revision/i);
  });

  it("rejects content hash mismatch", () => {
    const result = verifyCommitReceiptAgainstSnapshot(
      receipt({ normalized_content_sha256: "sha-a" }),
      snapshot({ content_sha256: "sha-b" }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toMatch(/content_sha256/i);
  });

  it("rejects fingerprint mismatch when receipt supplies one", () => {
    const result = verifyCommitReceiptAgainstSnapshot(
      receipt({ file_fingerprint: "fp-a" }),
      snapshot({ file_fingerprint: "fp-b" }),
    );
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.reason).toMatch(/file_fingerprint/i);
  });
});
