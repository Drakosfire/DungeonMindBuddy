import { describe, expect, it, vi } from "vitest";

import { parsePlayableHtmlComment } from "../tiptap/playable/playableElementIdentity";
import type { WorkspaceDocumentRecord } from "../api/types";
import {
  BLANK_RUNBOOK_TITLE,
  UNTITLED_BEAT_HEADING,
  campaignIdFromProductContext,
  createBlankRunbook,
  formatBlankRunbookMarkdown,
  resolveBlankRunbookCampaignId,
} from "./blankRunbook";

const DOC_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const BEAT_ID = "beat:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa";

function record(campaignId: string): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: DOC_ID,
    title: BLANK_RUNBOOK_TITLE,
    campaign_id: campaignId,
    target_session: null,
    kind: "runbook",
    target_relpath: null,
    status: "active",
    content_status: "committed",
    revision: 1,
    created_at: "2026-08-27T00:00:00Z",
    updated_at: "2026-08-27T00:00:00Z",
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
    const created = record("operator-campaign");
    created.content_status = "draft";
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

    const result = await createBlankRunbook("operator-campaign", {
      create,
      prepare,
      commit,
      generateBeatId: () => BEAT_ID,
    });

    expect(create).toHaveBeenCalledWith({
      title: BLANK_RUNBOOK_TITLE,
      campaign_id: "operator-campaign",
      kind: "runbook",
      target_session: null,
      target_relpath: null,
    });
    expect(prepare).toHaveBeenCalledWith({
      document_id: DOC_ID,
      markdown: formatBlankRunbookMarkdown(BEAT_ID),
      expected_revision: 1,
    });
    expect(commit).toHaveBeenCalledWith({
      document_id: DOC_ID,
      markdown: formatBlankRunbookMarkdown(BEAT_ID),
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
});
