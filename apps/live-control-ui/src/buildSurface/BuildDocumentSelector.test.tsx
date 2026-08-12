import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

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

    expect(screen.getByRole("option", { name: "Choose source" })).toBeInTheDocument();
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
