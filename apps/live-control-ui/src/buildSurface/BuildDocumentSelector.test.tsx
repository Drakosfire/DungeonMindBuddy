import { setNativeGraphAccessToken } from "../api/liveApi";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
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

function openCategory(name: string) {
  fireEvent.click(screen.getByTestId("build-document-select"));
  const dialog = screen.getByRole("dialog", { name: "Open document" });
  if (name !== "Recent") fireEvent.click(within(dialog).getByRole("button", { name, exact: true }));
  return dialog;
}

describe("BuildDocumentSelector", () => {
  it("finds a saved statblock by title and addresses its exact revision in Build", async () => {
    setNativeGraphAccessToken("fixture");
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async url => new Response(JSON.stringify(
      String(url).includes("world-mechanics/associations") ? [
        { request: { draft_id: "creature", target: { campaign_scope: null } },
          proof: { locator: { revision_id: "saved-revision" } } },
      ] : String(url).includes("statblock-reviews") ? {
        reviews: [{ review_id: "sewer-review", name: "Sewer Meat Extraction", draft_id: "unpublished" },
          { review_id: "saved-review", name: "Already saved extraction", draft_id: "creature" }],
      } : String(url).includes("build-pdf-sources") ? {
        next: null, documents: [{ source_revision_id: "remote", content_sha256: "abcde123",
          created_at: "2026-11-11T00:00:00Z" }],
      } : {
      total: 3,
      drafts: [
        { world_id: "elderwyld", draft_id: "unpublished", name: "Sewer Meat Extraction", saved_revision_id: "unpublished-mechanics" },
        { world_id: "elderwyld", draft_id: "creature", name: "Sewer Meat Creature",
          saved_revision_id: "newer-unpublished-revision" },
        { world_id: "elsewhere", draft_id: "foreign", name: "Sewer Giant",
          saved_revision_id: "other-revision" },
      ],
    })));
    const previousUrl = window.location.href;
    window.history.replaceState({}, "", "/build?world=elderwyld");
    try {
      render(<BuildDocumentSelector worldId="elderwyld"
        documents={[record(DOC_A, "Alpha", "longmont-c1")]} listStatus="ready"
        activeDocumentId={null} activeRecord={null} preferredCampaignId={null}
        switching={false} onSelect={vi.fn()} />);
      expect(request).not.toHaveBeenCalled();
      const dialog = openCategory("All documents");
      expect(await screen.findByRole("button", { name: "PDF · 2026-11-11 · abcde123" }))
        .toHaveAttribute("data-document-id", "/build?world=elderwyld&pdf=remote");
      expect(screen.queryByRole("button", { name: "Sewer Meat Extraction" })).not.toBeInTheDocument();
      const statblock = await screen.findByRole("button", { name: "Sewer Meat Creature" });
      expect(screen.queryByRole("button", { name: "Already saved extraction" })).not.toBeInTheDocument();
      expect(statblock).toHaveAttribute("data-document-id", "/build?world=elderwyld&draft=creature&revision=saved-revision");
      const catalogCalls = () => request.mock.calls.filter(([url]) =>
        String(url).includes("/native-source-inspection/catalog"));
      expect(catalogCalls()).toHaveLength(1);
      fireEvent.click(within(dialog).getByRole("button", { name: "Close document picker" }));
      openCategory("All documents");
      expect(catalogCalls()).toHaveLength(1);
      expect(screen.queryByRole("button", { name: "Sewer Giant" })).not.toBeInTheDocument();
      await userEvent.type(screen.getByRole("searchbox"), "sewer");
      expect(screen.queryByRole("button", { name: "Alpha" })).not.toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Sewer Meat Creature" })).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: "Sewer Meat Extraction" })).not.toBeInTheDocument();
      fireEvent.click(screen.getByRole("button", { name: "Statblock drafts", exact: true }));
      expect(await screen.findByRole("button", { name: "Sewer Meat Extraction" }))
        .toHaveAttribute("data-document-id", "/build?world=elderwyld&pdfReview=sewer-review");
      fireEvent.click(screen.getByRole("button", { name: "Sewer Meat Extraction" }));
      expect(window.location.search).toBe("?world=elderwyld&pdfReview=sewer-review");
    } finally {
      window.history.replaceState({}, "", previousUrl);
      request.mockRestore();
      setNativeGraphAccessToken(null);
    }
  });

  it("loads the current World’s catalogs while the picker is open", async () => {
    setNativeGraphAccessToken("fixture");
    const request = vi.spyOn(globalThis, "fetch").mockImplementation(async () =>
      new Response("{}", { status: 503 }));
    const props = {
      documents: [], listStatus: "ready" as const, activeDocumentId: null, activeRecord: null,
      preferredCampaignId: null, switching: false, onSelect: vi.fn(),
    };
    const catalogCalls = () => request.mock.calls.filter(([url]) =>
      String(url).includes("/native-source-inspection/catalog"));
    try {
      const view = render(<BuildDocumentSelector {...props} worldId="elderwyld" />);
      const dialog = openCategory("All documents");
      await within(dialog).findByText("Ingested text documents unavailable");
      fireEvent.click(within(dialog).getByRole("button", { name: "Close document picker" }));
      view.rerender(<BuildDocumentSelector {...props} worldId="pilot" />);
      expect(catalogCalls()).toHaveLength(1);
      openCategory("All documents");
      await waitFor(() => expect(catalogCalls()).toHaveLength(2));
      expect(JSON.parse(String(catalogCalls()[1][1]?.body))).toMatchObject({ managed_world_id: "pilot" });
      await screen.findByText("Ingested text documents unavailable");
      view.rerender(<BuildDocumentSelector {...props} worldId="elderwyld" />);
      await waitFor(() => expect(catalogCalls()).toHaveLength(3));
      expect(JSON.parse(String(catalogCalls()[2][1]?.body))).toMatchObject({ managed_world_id: "elderwyld" });
      await screen.findByText("Ingested text documents unavailable");
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
        : String(url).includes("world-mechanics/associations") ? [] : { total: 0, drafts: [] },
    )));
    try {
      render(<BuildDocumentSelector worldId="elderwyld" documents={[]} listStatus="ready"
        activeDocumentId={null} activeRecord={null} preferredCampaignId={null}
        switching={false} onSelect={vi.fn()} />);
      openCategory("PDFs");
      expect(await screen.findByRole("button", { name: "MeatMindNode.pdf" }))
        .toHaveAttribute("data-document-id", "/build?world=elderwyld&pdf=source");
      expect(screen.queryByRole("button", { name: "Withdrawn PDF" })).not.toBeInTheDocument();
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

    const dialog = openCategory("Recent");
    expect(within(dialog).getByRole("button", { name: "Recent" })).toHaveAttribute("aria-pressed", "true");
    expect(within(dialog).getByText("Documents you open will appear here.")).toBeInTheDocument();
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

    const dialog = openCategory("Pages");
    expect(within(dialog).getAllByRole("listitem").map(row => row.textContent)).toEqual([
      "BetaPages · C2", "AlphaPages · C1",
    ]);
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

    const dialog = openCategory("Pages");
    expect(within(dialog).getByRole("button", { name: /Ironveil · lore · updated/i })).toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: /Ironveil · faction · updated/i })).toBeInTheDocument();
  });

  it("opens the exact page and preserves search while loading more pages", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();
    const loadMorePages = vi.fn();
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
        loadMorePages={loadMorePages}
        onSelect={onSelect}
      />,
    );

    const dialog = openCategory("Pages");
    await user.type(within(dialog).getByRole("searchbox"), "Beta");
    await user.click(within(dialog).getByRole("button", { name: "Load more pages" }));
    expect(loadMorePages).toHaveBeenCalledOnce();
    expect(within(dialog).getByRole("searchbox")).toHaveValue("Beta");
    await user.click(within(dialog).getByRole("button", { name: "Beta" }));
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

    const dialog = openCategory("Recent");
    expect(within(dialog).getByRole("button", { name: "Ironveil Manufactory Grounds" })).toBeInTheDocument();
    expect(within(dialog).queryByRole("button", { name: "Ironveil Property" })).not.toBeInTheDocument();
    expect(within(dialog).getByRole("button", { name: "Ironveil Manufactory Grounds" })).toHaveAttribute("aria-current", "page");
  });
});
