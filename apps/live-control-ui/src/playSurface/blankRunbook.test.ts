import { describe, expect, it, vi } from "vitest";

import { LiveApiError } from "../api/liveApi";
import { parsePlayableHtmlComment } from "../tiptap/playable/playableElementIdentity";
import type { WorkspaceDocumentRecord, WorkspaceDocumentSnapshot } from "../api/types";
import {
  BLANK_RUNBOOK_TITLE,
  BlankRunbookCreateError,
  UNTITLED_BEAT_HEADING,
  campaignIdFromProductContext,
  createBlankRunbook,
  formatBlankRunbookMarkdown,
  resolveBlankRunbookCampaignId,
} from "./blankRunbook";

const DOC_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const BEAT_ID = "beat:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";
const MARKDOWN = formatBlankRunbookMarkdown(BEAT_ID);

function record(campaignId: string, contentStatus: "draft" | "committed" = "committed"): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: DOC_ID,
    title: BLANK_RUNBOOK_TITLE,
    campaign_id: campaignId,
    target_session: null,
    kind: "runbook",
    target_relpath: null,
    status: "active",
    content_status: contentStatus,
    revision: 1,
    created_at: "2026-08-27T00:00:00Z",
    updated_at: "2026-08-27T00:00:00Z",
  };
}

function snapshot(
  contentStatus: "draft" | "committed",
  markdown = MARKDOWN,
): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record: record("operator-campaign", contentStatus),
    markdown,
    content_sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    file_fingerprint: "fp",
    file_exists: contentStatus === "committed",
    loaded_revision: 1,
  };
}

describe("blankRunbook", () => {
  it("formats one canonical v2 Beat and no Scene/Decision/Option content", () => {
    const markdown = formatBlankRunbookMarkdown(BEAT_ID);
    const lines = markdown.trimEnd().split("\n");
    expect(lines).toEqual([
      "<!-- dmb-playable-element:v2 kind=beat id=beat:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa beat_kind=spine -->",
      `## ${UNTITLED_BEAT_HEADING}`,
    ]);
    const parsed = parsePlayableHtmlComment(lines[0]);
    expect(parsed).toEqual({
      status: "canonical",
      identity: { kind: "beat", id: BEAT_ID, version: "v2", beatKind: "spine" },
    });
    expect(markdown).not.toMatch(/kind=scene/);
    expect(markdown).not.toMatch(/kind=choice/);
    expect(markdown).not.toMatch(/kind=option/);
    expect(markdown).not.toMatch(/longmont-c2/);
  });

  it("uses valid World focus as product context and ignores unavailable defaults", () => {
    expect(
      campaignIdFromProductContext({
        focusValidationStatus: "unavailable",
        lens: { focus: { campaignId: "longmont-c2" } },
      }),
    ).toBeNull();
    expect(
      campaignIdFromProductContext({
        focusValidationStatus: "valid",
        lens: { focus: { campaignId: "longmont-c2" } },
      }),
    ).toBe("longmont-c2");
    expect(campaignIdFromProductContext(null)).toBeNull();
    expect(resolveBlankRunbookCampaignId(null, "  operator-campaign  ")).toBe("operator-campaign");
    expect(resolveBlankRunbookCampaignId("from-world", "typed")).toBe("from-world");
  });

  it("creates and commits through workspace + TipTap write without starting a Run", async () => {
    const created = record("operator-campaign", "draft");
    const committed = record("operator-campaign");
    const create = vi.fn().mockResolvedValue(created);
    const prepare = vi.fn().mockResolvedValue({
      writer_ok: true,
      writer_confirm_token: "token-1",
    });
    const commit = vi.fn().mockResolvedValue({
      committed_record: committed,
      writer_ok: true,
    });
    const onAttemptRetained = vi.fn();

    const result = await createBlankRunbook("operator-campaign", {
      create,
      prepare,
      commit,
      generateBeatId: () => BEAT_ID,
      onAttemptRetained,
    });

    expect(create).toHaveBeenCalledWith({
      title: BLANK_RUNBOOK_TITLE,
      campaign_id: "operator-campaign",
      kind: "runbook",
      target_session: null,
      target_relpath: null,
    });
    expect(onAttemptRetained).toHaveBeenCalledWith({
      documentId: DOC_ID,
      beatId: BEAT_ID,
      markdown: MARKDOWN,
      expectedRevision: 1,
      campaignId: "operator-campaign",
    });
    expect(prepare).toHaveBeenCalledWith({
      document_id: DOC_ID,
      markdown: MARKDOWN,
      expected_revision: 1,
    });
    expect(commit).toHaveBeenCalledWith({
      document_id: DOC_ID,
      markdown: MARKDOWN,
      writer_confirm_token: "token-1",
      expected_revision: 1,
    });
    expect(result.record.document_id).toBe(DOC_ID);
    expect(result.beatId).toBe(BEAT_ID);
    expect(result.markdown).toContain("## Untitled Beat");
  });

  it("refuses a missing campaign instead of defaulting to longmont-c2", async () => {
    const create = vi.fn();
    await expect(createBlankRunbook("  ", { create })).rejects.toThrow(/Campaign is required/);
    expect(create).not.toHaveBeenCalled();
  });

  it("retains the first WorkObject across a prepare failure and retries that document", async () => {
    const created = record("operator-campaign", "draft");
    const committed = record("operator-campaign");
    const create = vi.fn().mockResolvedValue(created);
    const prepare = vi.fn()
      .mockRejectedValueOnce(new Error("prepare unavailable"))
      .mockResolvedValue({
        writer_ok: true,
        writer_confirm_token: "token-2",
      });
    const commit = vi.fn().mockResolvedValue({
      committed_record: committed,
      writer_ok: true,
    });
    const getSnapshot = vi.fn().mockResolvedValue(snapshot("draft"));

    const first = createBlankRunbook("operator-campaign", {
      create,
      prepare,
      commit,
      getSnapshot,
      generateBeatId: () => BEAT_ID,
    });
    await expect(first).rejects.toMatchObject({
      name: "BlankRunbookCreateError",
      attempt: {
        documentId: DOC_ID,
        beatId: BEAT_ID,
        markdown: MARKDOWN,
        expectedRevision: 1,
        campaignId: "operator-campaign",
      },
    });
    const retained = await first.catch((error: BlankRunbookCreateError) => error.attempt);

    const result = await createBlankRunbook("operator-campaign", {
      create,
      prepare,
      commit,
      getSnapshot,
      generateBeatId: () => "beat:should-not-be-used",
      attempt: retained,
    });

    expect(create).toHaveBeenCalledTimes(1);
    expect(prepare).toHaveBeenCalledTimes(2);
    expect(commit).toHaveBeenCalledTimes(1);
    expect(result.record.document_id).toBe(DOC_ID);
    expect(result.beatId).toBe(BEAT_ID);
  });

  it("treats a lost commit as success when the exact document already has the starter bytes", async () => {
    const created = record("operator-campaign", "draft");
    const create = vi.fn().mockResolvedValue(created);
    const prepare = vi.fn().mockResolvedValue({
      writer_ok: true,
      writer_confirm_token: "token-1",
    });
    const commit = vi.fn().mockRejectedValue(new Error("network"));
    const getSnapshot = vi.fn().mockResolvedValue(snapshot("committed"));

    const result = await createBlankRunbook("operator-campaign", {
      create,
      prepare,
      commit,
      getSnapshot,
      generateBeatId: () => BEAT_ID,
    });

    expect(create).toHaveBeenCalledTimes(1);
    expect(commit).toHaveBeenCalledTimes(1);
    expect(getSnapshot).toHaveBeenCalledWith(DOC_ID);
    expect(result.record.content_status).toBe("committed");
    expect(result.record.document_id).toBe(DOC_ID);
  });

  it("reconciles an uncertain commit on retry instead of minting a second WorkObject", async () => {
    const created = record("operator-campaign", "draft");
    const create = vi.fn().mockResolvedValue(created);
    const prepare = vi.fn().mockResolvedValue({
      writer_ok: true,
      writer_confirm_token: "token-1",
    });
    const commit = vi.fn().mockRejectedValue(new Error("network"));
    const getSnapshot = vi.fn()
      .mockRejectedValueOnce(new LiveApiError("snapshot unavailable", 503))
      .mockResolvedValue(snapshot("committed"));

    const first = createBlankRunbook("operator-campaign", {
      create,
      prepare,
      commit,
      getSnapshot,
      generateBeatId: () => BEAT_ID,
    });
    await expect(first).rejects.toBeInstanceOf(BlankRunbookCreateError);
    const retained = await first.catch((error: BlankRunbookCreateError) => error.attempt);

    const result = await createBlankRunbook("other-campaign-should-be-ignored", {
      create,
      prepare,
      commit,
      getSnapshot,
      generateBeatId: () => "beat:should-not-be-used",
      attempt: retained,
    });

    expect(create).toHaveBeenCalledTimes(1);
    expect(prepare).toHaveBeenCalledTimes(1);
    expect(commit).toHaveBeenCalledTimes(1);
    expect(result.record.document_id).toBe(DOC_ID);
    expect(result.beatId).toBe(BEAT_ID);
  });
});
