import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import * as recapIngestApi from "../api/recapIngestApi";
import type { RecapIngestStatus } from "../api/types";
import { mockCatalog, mockLayout, mockPlanView, mockState } from "../test/fixtures";
import { SurfaceShell } from "../surface/SurfaceShell";
import { IngestionModule } from "./IngestionModule";

function makeStatus(overrides: Partial<RecapIngestStatus> = {}): RecapIngestStatus {
  return {
    schema: "dmb_raw_recap_ingest_status_v1",
    campaign_id: "longmont-c2",
    session: 22,
    status: "recap_preview_created",
    states: ["raw_text_received", "recap_preview_created"],
    paths: {
      staged_raw_notes:
        "Longmont Campaign/Campaign 2/_ingest_staging/session_22_raw_notes.md",
      canonical_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/Session 22 - Mireward Road and Lysandro.md",
      normalized_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 22 - Mireward Road and Lysandro.md",
      breadcrumbed_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md",
      session_memory_jsonl:
        "Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.jsonl",
    },
    authority: {
      staged_raw_notes: "pre_canonical_evidence",
      canonical_recap: "canon_play",
      normalized_recap: "canon_play_prepared",
      breadcrumbed_recap: "canon_play_routed",
      session_memory: "derived_memory",
    },
    warnings: [],
    errors: [],
    next_actions: [],
    ingest_report: {
      title_line_stripped: true,
      paragraph_count_in: 6,
      paragraph_count_out: 6,
      duplicates_detected: 0,
      duplicates_removed: 0,
      preview_diff: "@@ -1 +1 @@\n-old\n+new\n",
    },
    entity_spelling_audit: [
      {
        canonical_guess: "Caelynn",
        variants: ["Caeylynn", "Caelynn"],
        action: "review_only",
      },
    ],
    ...overrides,
  };
}

describe("IngestionModule", () => {
  it("renders from surface catalog when ingestion module is enabled", () => {
    const catalog = [
      ...mockCatalog,
      {
        module_id: "ingestion",
        title: "Ingestion",
        default_slot: "sidebar" as const,
        required: false,
        enabled_by_default: false,
        description: "Raw recap ingest operator pane",
        config_schema: null,
      },
    ];
    const layout = {
      ...mockLayout,
      modules: [
        ...mockLayout.modules,
        {
          module_id: "ingestion",
          slot: "sidebar" as const,
          order: 10,
          enabled: true,
          collapsed: false,
          size: null,
          config: {},
        },
      ],
    };
    render(
      <SurfaceShell
        catalog={catalog}
        layout={layout}
        state={mockState}
        events={[]}
        jobs={[]}
        planView={mockPlanView}
        onQuerySuccess={vi.fn()}
        onLayoutSaved={vi.fn()}
      />,
    );
    expect(screen.getByText("Raw Recap Ingestion")).toBeInTheDocument();
  });

  it("disables stage preview with empty raw text", () => {
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    expect(screen.getByRole("button", { name: "Stage + Preview" })).toBeDisabled();
  });

  it("submits stage_preview with raw_text and no raw_path", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus());
    const commandSpy = vi.spyOn(liveApi, "postCommand");

    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    await user.type(
      screen.getByLabelText("Raw recap text"),
      "Session 22 Recap\n\nThe group turns their focus...",
    );
    await user.type(screen.getByLabelText("Slug"), "Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));

    await waitFor(() => expect(spy).toHaveBeenCalledTimes(1));
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "stage_preview",
        raw_text: expect.stringContaining("Session 22 Recap"),
      }),
    );
    expect((spy.mock.calls[0][0] as Record<string, unknown>).raw_path).toBeUndefined();
    expect(commandSpy).not.toHaveBeenCalled();
  });

  it("renders status, authority transition, spelling audit, and preview diff as read-only", async () => {
    const user = userEvent.setup();
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus());

    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Slug"), "Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));

    await waitFor(() =>
      expect(screen.getByLabelText("Canonical preview diff")).toBeInTheDocument(),
    );
    expect(screen.getByText(/raw notes -> pre_canonical_evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/Review only. No auto-corrections are applied/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Canonical preview diff")).toHaveTextContent("@@ -1 +1 @@");
  });

  it("disables apply normalize before preview and without non-generic slug", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    const applyButton = screen.getByRole("button", { name: "Apply + Normalize" });
    expect(applyButton).toBeDisabled();

    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Slug"), "Recap");
    expect(applyButton).toBeDisabled();
  });

  it("invalidates preview when raw text changes", async () => {
    const user = userEvent.setup();
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus());
    render(<IngestionModule campaignId="longmont-c2" session={22} />);

    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Slug"), "Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Canonical preview diff")).toBeInTheDocument(),
    );

    await user.type(screen.getByLabelText("Raw recap text"), " updated");
    expect(screen.getByText(/Preview invalidated by raw text\/slug\/title edits/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apply + Normalize" })).toBeDisabled();
  });

  it("submits apply_normalize after valid preview", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest");
    spy
      .mockResolvedValueOnce(makeStatus())
      .mockResolvedValueOnce(makeStatus({ status: "breadcrumb_required", states: ["breadcrumb_required"], next_actions: ["Generate/bless breadcrumb artifact"] }));

    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Slug"), "Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Apply + Normalize" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Apply + Normalize" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({ operation: "apply_normalize" }),
      ),
    );
    expect(screen.getByText(/Generate\/bless breadcrumb artifact/)).toBeInTheDocument();
  });

  it("submits materialize_session_memory and shows ready state", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest");
    spy
      .mockResolvedValueOnce(makeStatus({ states: ["raw_text_received", "recap_preview_created", "breadcrumb_found"] }))
      .mockResolvedValueOnce(
        makeStatus({
          status: "ready_for_planning_activation",
          states: ["breadcrumb_found", "session_memory_materialized", "ready_for_planning_activation"],
          ingest_report: { session_memory_record_count: 10, session_memory_check: "ok" },
        }),
      );

    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Slug"), "Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Materialize Session Memory" })).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: "Materialize Session Memory" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({ operation: "materialize_session_memory" }),
      ),
    );
    expect(screen.getAllByText("ready_for_planning_activation").length).toBeGreaterThan(0);
  });

  it("keeps force controls behind explicit advanced disclosure", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    expect(screen.queryByText(/Overwrite staged raw notes/)).not.toBeInTheDocument();
    await user.click(screen.getByText("Advanced overwrite controls"));
    await user.click(screen.getByLabelText(/Enable overwrite toggles/));
    expect(screen.getByText(/Overwrite staged raw notes/)).toBeInTheDocument();
    expect(screen.getByText(/Overwrite existing canonical recap/)).toBeInTheDocument();
  });
});
