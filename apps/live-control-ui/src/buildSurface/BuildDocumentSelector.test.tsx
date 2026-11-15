import { setNativeGraphAccessToken } from "../api/liveApi";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { pdfRegionKey, retainedPdfKey } from "../api/retainedPdfRegions";
import type { WorkspaceDocumentRecord } from "../api/types";
import { BuildDocumentSelector } from "./BuildDocumentSelector";

const DOC_A = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";

function record(documentId: string, title: string, campaignId: string): WorkspaceDocumentRecord {
  return {
    schema_version: "dmb_workspace_document_record_v1",
    document_id: documentId,
    title,
    campaign_id: campaignId,
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
  };
}

describe("BuildDocumentSelector", () => {
  it("finds a saved statblock by title and addresses its exact revision in Build", async () => {
    setNativeGraphAccessToken("fixture");
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async url => new Response(JSON.stringify(
      String(url).includes("build-pdf-sources") ? {
        next: null, documents: [{ source_revision_id: "remote", content_sha256: "abcde123",
          created_at: "2026-11-11T00:00:00Z" }],
      } : {
      total: 2,
      drafts: [
        { world_id: "elderwyld", draft_id: "creature", name: "Sewer Meat Creature",
          saved_revision_id: "saved-revision" },
        { world_id: "elsewhere", draft_id: "foreign", name: "Sewer Giant",
          saved_revision_id: "other-revision" },
      ],
    })));
    try {
      render(<BuildDocumentSelector worldId="elderwyld"
        documents={[record(DOC_A, "Alpha", "longmont-c1")]} listStatus="ready"
        activeDocumentId={null} activeRecord={null} preferredCampaignId={null}
        switching={false} onSelect={vi.fn()} />);
      expect(await screen.findByRole("option", { name: "PDF · 2026-11-11 · abcde123" }))
        .toHaveValue("/build?world=elderwyld&pdf=remote");
      const statblock = await screen.findByRole("option", { name: "Sewer Meat Creature" });
      expect(statblock).toHaveValue("/build?world=elderwyld&draft=creature&revision=saved-revision");
      expect(screen.queryByRole("option", { name: "Sewer Giant" })).not.toBeInTheDocument();
      await userEvent.type(screen.getByRole("searchbox"), "sewer");
      expect(screen.queryByRole("option", { name: "Alpha" })).not.toBeInTheDocument();
      expect(statblock).toBeInTheDocument();
    } finally {
      request.mockRestore();
      setNativeGraphAccessToken(null);
    }
  });

  it("lists one Build document for multiple saved regions of a PDF", async () => {
    const locator = { source_revision_id: "source", content_sha256: "digest",
      page: 1, left: 0, top: 0, right: 1, bottom: 1 };
    const keys = [locator, { ...locator, page: 2 }].map(region => {
      const key = retainedPdfKey("elderwyld") + pdfRegionKey(region);
      localStorage.setItem(key, JSON.stringify({ name: "MeatMindNode.pdf", locator: region }));
      return key;
    });
    setNativeGraphAccessToken("fixture");
    const staleKey = retainedPdfKey("elderwyld") + pdfRegionKey({ ...locator, source_revision_id: "withdrawn" });
    localStorage.setItem(staleKey, JSON.stringify({
      name: "Withdrawn PDF", locator: { ...locator, source_revision_id: "withdrawn" },
    }));
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async url => new Response(JSON.stringify(
      String(url).includes("build-pdf-sources")
        ? { next: null, documents: [{ source_revision_id: "source", content_sha256: "digest", created_at: "2026-11-11" }] }
        : { total: 0, drafts: [] },
    )));
    try {
      render(<BuildDocumentSelector worldId="elderwyld" documents={[]} listStatus="ready"
        activeDocumentId={null} activeRecord={null} preferredCampaignId={null}
        switching={false} onSelect={vi.fn()} />);
      expect(await screen.findByRole("option", { name: "MeatMindNode.pdf" }))
        .toHaveValue("/build?world=elderwyld&pdf=source");
      expect(screen.queryByRole("option", { name: "Withdrawn PDF" })).not.toBeInTheDocument();
    } finally {
      request.mockRestore();
      setNativeGraphAccessToken(null);
      localStorage.removeItem(staleKey);
      keys.forEach(key => localStorage.removeItem(key));
    }
  });

  it("shows placeholder when no active document", () => {
    render(
      <BuildDocumentSelector
        documents={[record(DOC_A, "Alpha", "longmont-c1")]}
        listStatus="ready"
        activeDocumentId={null}
        activeRecord={null}
        preferredCampaignId="longmont-c2"
        switching={false}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("option", { name: "Open document" })).toBeInTheDocument();
  });

  it("groups options by campaign with preferred campaign first", () => {
    render(
      <BuildDocumentSelector
        documents={[
          record(DOC_A, "Alpha", "longmont-c1"),
          record(DOC_B, "Beta", "longmont-c2"),
        ]}
        listStatus="ready"
        activeDocumentId={DOC_B}
        activeRecord={record(DOC_B, "Beta", "longmont-c2")}
        preferredCampaignId="longmont-c2"
        switching={false}
        onSelect={vi.fn()}
      />,
    );

    const select = screen.getByTestId("build-document-select");
    const optgroups = select.querySelectorAll("optgroup");
    expect(optgroups[0]).toHaveAttribute("label", "C2");
    expect(optgroups[1]).toHaveAttribute("label", "C1");
  });

  it("disambiguates duplicate titles in the same campaign", () => {
    const duplicateA = record(DOC_A, "Ironveil", "longmont-c1");
    const duplicateB = {
      ...record(DOC_B, "Ironveil", "longmont-c1"),
      document_class: "faction" as const,
      updated_at: "2026-08-01T00:00:00Z",
    };

    render(
      <BuildDocumentSelector
        documents={[duplicateA, duplicateB]}
        listStatus="ready"
        activeDocumentId={DOC_A}
        activeRecord={duplicateA}
        preferredCampaignId="longmont-c1"
        switching={false}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByRole("option", { name: /Ironveil · lore · updated/i })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: /Ironveil · faction · updated/i })).toBeInTheDocument();
  });

  it("calls onSelect with exact document id", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    render(
      <BuildDocumentSelector
        documents={[
          record(DOC_A, "Alpha", "longmont-c1"),
          record(DOC_B, "Beta", "longmont-c2"),
        ]}
        listStatus="ready"
        activeDocumentId={DOC_A}
        activeRecord={record(DOC_A, "Alpha", "longmont-c1")}
        preferredCampaignId="longmont-c1"
        switching={false}
        onSelect={onSelect}
      />,
    );

    await user.selectOptions(screen.getByTestId("build-document-select"), DOC_B);
    expect(onSelect).toHaveBeenCalledWith(DOC_B);
  });

  it("overlays live activeRecord title over a stale documents list entry", () => {
    const staleList = record(DOC_A, "Ironveil Property", "longmont-c1");
    const liveRenamed = {
      ...record(DOC_A, "Ironveil Manufactory Grounds", "longmont-c1"),
      revision: 2,
    };

    render(
      <BuildDocumentSelector
        documents={[staleList, record(DOC_B, "Beta", "longmont-c2")]}
        listStatus="ready"
        activeDocumentId={DOC_A}
        activeRecord={liveRenamed}
        preferredCampaignId="longmont-c1"
        switching={false}
        onSelect={vi.fn()}
      />,
    );

    const select = screen.getByTestId("build-document-select");
    expect(within(select).getByRole("option", { name: "Ironveil Manufactory Grounds" })).toBeInTheDocument();
    expect(within(select).queryByRole("option", { name: "Ironveil Property" })).not.toBeInTheDocument();
    expect(select).toHaveValue(DOC_A);
  });
});
