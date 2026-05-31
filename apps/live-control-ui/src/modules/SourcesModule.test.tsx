import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { RecapIngestStatus } from "../api/types";
import { SourcesModule } from "./SourcesModule";

const mockInspectReady: RecapIngestStatus = {
  schema: "dmb_raw_recap_ingest_status_v1",
  campaign_id: "longmont-c2",
  session: 22,
  status: "ready_for_planning_activation",
  states: [
    "staged_raw_notes_reused",
    "recap_reused",
    "normalized_reused",
    "breadcrumb_found",
    "session_memory_materialized",
    "ready_for_planning_activation",
    "ingest_status_inspected",
  ],
  paths: {
    staged_raw_notes: "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md",
    canonical_recap: "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
    normalized_recap:
      "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md",
    breadcrumbed_recap:
      "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md",
    session_memory_jsonl:
      "Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.jsonl",
    session_memory_meta:
      "Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.json",
  },
  authority: {},
  warnings: [],
  errors: [],
  next_actions: ["Ingest complete. Proceed with planning activation."],
  ingest_report: {},
  entity_spelling_audit: [],
};

vi.mock("../api/recapIngestApi", () => ({
  postRecapIngest: vi.fn(),
}));

import { postRecapIngest } from "../api/recapIngestApi";

describe("SourcesModule", () => {
  beforeEach(() => {
    vi.mocked(postRecapIngest).mockReset();
    vi.mocked(postRecapIngest).mockResolvedValue(mockInspectReady);
  });

  it("shows corpus ladder when inspect reports ready_for_planning_activation", async () => {
    render(<SourcesModule campaignId="longmont-c2" session={23} />);

    await waitFor(() => {
      expect(screen.getByText("Corpus loaded for planning")).toBeInTheDocument();
    });

    expect(screen.getByText("Ready for planning activation")).toBeInTheDocument();
    expect(screen.getByText("Session memory")).toBeInTheDocument();
    expect(postRecapIngest).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "inspect_status",
        campaign_id: "longmont-c2",
        session: 22,
      }),
    );
  });

  it("refreshes status when Refresh is clicked", async () => {
    const user = userEvent.setup();
    render(<SourcesModule campaignId="longmont-c2" session={23} />);

    await waitFor(() => {
      expect(postRecapIngest).toHaveBeenCalledTimes(1);
    });

    await user.click(screen.getByRole("button", { name: "Refresh" }));

    await waitFor(() => {
      expect(postRecapIngest).toHaveBeenCalledTimes(2);
    });
  });
});
