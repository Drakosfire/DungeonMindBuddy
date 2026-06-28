import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

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
      frontmatter_seed:
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.frontmatter_seed.md",
      breadcrumbed_recap:
        "Longmont Campaign/Campaign 2/Session Recaps/_breadcrumbed/Session 22 - Mireward Road and Lysandro.breadcrumbed.md",
      session_memory_jsonl:
        "Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 22 - Mireward Road and Lysandro.records_meta.jsonl",
    },
    authority: {
      staged_raw_notes: "pre_canonical_evidence",
      canonical_recap: "canon_play",
      normalized_recap: "canon_play_prepared",
      frontmatter_seed: "reviewable_route_allowlist",
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

function mockRecapIngestWithInspect(
  handler: (
    body: Parameters<typeof recapIngestApi.postRecapIngest>[0],
  ) => RecapIngestStatus | Promise<RecapIngestStatus>,
) {
  return vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
    if (body.operation === "inspect_status") {
      return makeStatus({
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      });
    }
    return handler(body);
  });
}

describe("IngestionModule", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(
      makeStatus({
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      }),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders editable recap/source session input", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={23} />);

    const recapSessionInput = screen.getByLabelText("Recap/source session");
    expect(recapSessionInput).toHaveValue(22);
    expect(screen.getAllByText("Required")).toHaveLength(1);
    expect(screen.queryByText(/Used for the canonical recap filename/)).not.toBeInTheDocument();
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 - Mireward Road\n\nThe group travels.");
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road");
    expect(screen.queryByText("Required")).not.toBeInTheDocument();
    await user.clear(recapSessionInput);
    await user.type(recapSessionInput, "21");
    expect(recapSessionInput).toHaveValue(21);
  });

  it("renders from surface catalog when ingestion module is enabled", async () => {
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(
      makeStatus({
        status: "initialized",
        states: ["ingest_status_inspected"],
        entity_spelling_audit: [],
      }),
    );
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
    expect(await screen.findByText("Raw Recap Ingestion")).toBeInTheDocument();
  });

  it("disables stage preview with empty raw text", () => {
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    expect(screen.getByText("Paste raw recap text, then continue to preview.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Stage + Preview" })).toBeDisabled();
  });

  it("submits stage_preview with edited recap session and no raw_path", async () => {
    const user = userEvent.setup();
    const spy = mockRecapIngestWithInspect(() => makeStatus());
    const commandSpy = vi.spyOn(liveApi, "postCommand");

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    const recapSessionInput = screen.getByLabelText("Recap/source session");
    await user.clear(recapSessionInput);
    await user.type(recapSessionInput, "21");
    await user.type(
      screen.getByLabelText("Raw recap text"),
      "Session 22 Recap\n\nThe group turns their focus...",
    );
    await user.type(screen.getByLabelText("Session title"), "Session 21 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));

    await waitFor(() =>
      expect(spy.mock.calls.some(([body]) => body.operation === "stage_preview")).toBe(true),
    );
    expect(spy).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "stage_preview",
        session: 21,
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
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));

    await waitFor(() =>
      expect(screen.getByLabelText("Canonical preview diff")).toBeInTheDocument(),
    );
    expect(screen.getByText(/raw notes -> pre_canonical_evidence/i)).toBeInTheDocument();
    expect(screen.getByText(/Review only. No auto-corrections are applied/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Canonical preview diff")).toHaveTextContent("@@ -1 +1 @@");
  });

  it("explains existing staged raw notes as a review gate instead of a failed stage", async () => {
    const user = userEvent.setup();
    mockRecapIngestWithInspect(() =>
      makeStatus({
        status: "recap_preview_created",
        states: [
          "raw_text_received",
          "staged_raw_notes_reused",
          "staged_raw_notes_conflict",
          "recap_preview_created",
        ],
        warnings: ["staged raw notes already exists; pasted raw text was not used"],
        next_actions: [
          "Review the preview generated from the existing staged notes, or enable --force-stage to overwrite them with the pasted text.",
        ],
      }),
    );

    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\nDifferent pasted text.");
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));

    await waitFor(() => {
      expect(screen.getAllByText("Existing staged notes reused").length).toBeGreaterThan(0);
    });
    expect(screen.getAllByText(/preview uses those notes/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/did not overwrite it with the pasted text/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apply + Normalize" })).toBeEnabled();
  });

  it("disables apply normalize before preview and without a specific session title", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    const applyButton = screen.getByRole("button", { name: "Apply + Normalize" });
    expect(applyButton).toBeDisabled();

    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "Recap");
    expect(applyButton).toBeDisabled();
  });

  it("asks for a specific session title before full ingest", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={22} />);

    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "ingest");

    expect(screen.getByRole("button", { name: "Generate Recap Memory" })).toBeDisabled();
    expect(screen.getAllByText(/Session title is required/).length).toBeGreaterThan(0);
  });

  it("invalidates preview when raw text changes", async () => {
    const user = userEvent.setup();
    vi.spyOn(recapIngestApi, "postRecapIngest").mockResolvedValue(makeStatus());
    render(<IngestionModule campaignId="longmont-c2" session={22} />);

    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Canonical preview diff")).toBeInTheDocument(),
    );

    await user.type(screen.getByLabelText("Raw recap text"), " updated");
    expect(screen.getByText(/Preview invalidated by raw text\/title edits/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Apply + Normalize" })).toBeDisabled();
  });

  it("submits apply_normalize with edited recap session after valid preview", async () => {
    const user = userEvent.setup();
    const spy = mockRecapIngestWithInspect((body) => {
      if (body.operation === "apply_normalize") {
        return makeStatus({
          status: "breadcrumb_required",
          states: ["recap_applied", "normalized_created", "breadcrumb_required"],
          next_actions: [
            "Generate/bless breadcrumb artifact for Session 21, then rerun --materialize-session-memory.",
          ],
        });
      }
      return makeStatus();
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    const recapSessionInput = screen.getByLabelText("Recap/source session");
    await user.clear(recapSessionInput);
    await user.type(recapSessionInput, "21");
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "Session 21 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Apply + Normalize" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Apply + Normalize" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({ operation: "apply_normalize", session: 21 }),
      ),
    );
    await waitFor(() =>
      expect(screen.getAllByText("breadcrumb_required").length).toBeGreaterThan(0),
    );
    expect(screen.getByText("Breadcrumb required before retrieval")).toBeInTheDocument();
    expect(screen.getByText(/Expected v1 boundary: breadcrumb required/i)).toBeInTheDocument();
    expect(screen.getByText(/not retrieval-ready/i)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByText("Next: click Build Frontmatter Seed, then review the generated seed.")).toBeInTheDocument(),
    );
    await user.click(screen.getByText("Terminal path stays available"));
    expect(screen.getByText("Materialize waits for breadcrumb_found.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Materialize Session Memory" })).toBeDisabled();
  });

  it("runs the full ingest pipeline as one sequential operation", async () => {
    const user = userEvent.setup();
    const spy = mockRecapIngestWithInspect((body) => {
      if (body.operation === "stage_preview") {
        return makeStatus({
          status: "recap_preview_created",
          states: ["raw_text_received", "recap_preview_created"],
        });
      }
      if (body.operation === "apply_normalize") {
        return makeStatus({
          status: "breadcrumb_required",
          states: ["recap_applied", "normalized_created", "breadcrumb_required"],
        });
      }
      if (body.operation === "build_frontmatter_seed") {
        return makeStatus({
          status: "breadcrumb_required",
          states: ["recap_applied", "normalized_reused", "frontmatter_seed_found", "breadcrumb_required"],
        });
      }
      if (body.operation === "run_breadcrumb_ingest") {
        return makeStatus({
          status: "recap_applied",
          states: ["recap_applied", "normalized_reused", "frontmatter_seed_found", "breadcrumb_found"],
        });
      }
      return makeStatus({
        status: "ready_for_planning_activation",
        states: ["breadcrumb_found", "session_memory_materialized", "ready_for_planning_activation"],
        ingest_report: { session_memory_record_count: 10, session_memory_check: "ok" },
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Generate Recap Memory" }));

    await waitFor(() =>
      expect(screen.getAllByText("ready_for_planning_activation").length).toBeGreaterThan(0),
    );
    const operations = spy.mock.calls
      .map(([body]) => body.operation)
      .filter((operation) => operation !== "inspect_status");
    expect(operations).toEqual([
      "stage_preview",
      "apply_normalize",
      "build_frontmatter_seed",
      "run_breadcrumb_ingest",
      "materialize_session_memory",
    ]);
    expect(screen.getByText("Ingestion ready_for_planning_activation")).toBeInTheDocument();
    expect(screen.getByText("Complete: recap memory is generated. Review the rendered recap and proof artifacts.")).toBeInTheDocument();
    expect(screen.getByText("records: 10")).toBeInTheDocument();
  });

  it("resumes from disk after clear flow without requiring raw text again", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          session: 23,
          status: "breadcrumb_required",
          states: ["staged_raw_notes_reused", "normalized_reused", "frontmatter_seed_required", "breadcrumb_required", "ingest_status_inspected"],
          paths: {
            ...makeStatus().paths,
            canonical_recap: "Longmont Campaign/Campaign 2/Session Recaps/Session 23 - Recap.md",
            normalized_recap: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - session-23-mireward.md",
          },
          ingest_report: {
            corpus_impact: [
              {
                key: "normalized_recap",
                relpath: "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - session-23-mireward.md",
                exists: true,
                size_bytes: 512,
                preview: "---\ntitle: Session 23 - Mireward\n---\nThe party held the gate.",
              },
              {
                key: "session_memory_jsonl",
                relpath: "Longmont Campaign/Campaign 2/Session Recaps/_session_memory/Session 23 - session-23-mireward.records_meta.jsonl",
                exists: true,
                size_bytes: 128,
                record_count: 3,
                preview: "{\"text\":\"Gate record\"}",
              },
            ],
          },
          entity_spelling_audit: [],
        });
      }
      if (body.operation === "build_frontmatter_seed") {
        return makeStatus({
          session: 23,
          status: "breadcrumb_required",
          states: ["normalized_reused", "frontmatter_seed_found", "breadcrumb_required"],
        });
      }
      if (body.operation === "run_breadcrumb_ingest") {
        return makeStatus({
          session: 23,
          status: "recap_applied",
          states: ["normalized_reused", "frontmatter_seed_found", "breadcrumb_found"],
        });
      }
      return makeStatus({
        session: 23,
        status: "ready_for_planning_activation",
        states: ["breadcrumb_found", "session_memory_materialized", "ready_for_planning_activation"],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={24} />);

    await waitFor(() => expect(screen.getByLabelText("Session title")).toHaveValue("Session 23 - Mireward"));
    expect(screen.getByText("What was ingested?")).toBeInTheDocument();
    expect(screen.getByText("records: 3")).toBeInTheDocument();
    expect(screen.getByText(/The party held the gate/)).toBeInTheDocument();
    expect(screen.queryByText("Raw recap text is required to start a new ingest.")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Generate Recap Memory" }));

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(expect.objectContaining({ operation: "build_frontmatter_seed", session: 23 })),
    );
    const operations = spy.mock.calls.map(([body]) => body.operation);
    expect(operations).not.toContain("stage_preview");
  });

  it("submits build_frontmatter_seed from the breadcrumb boundary", async () => {
    const user = userEvent.setup();
    const spy = mockRecapIngestWithInspect((body) => {
      if (body.operation === "apply_normalize") {
        return makeStatus({
          status: "breadcrumb_required",
          states: ["recap_applied", "normalized_created", "frontmatter_seed_required", "breadcrumb_required"],
        });
      }
      if (body.operation === "build_frontmatter_seed") {
        return makeStatus({
          status: "breadcrumb_required",
          states: [
            "recap_applied",
            "normalized_reused",
            "frontmatter_seed_built",
            "frontmatter_seed_found",
            "breadcrumb_required",
          ],
        });
      }
      return makeStatus();
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Apply + Normalize" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Apply + Normalize" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Build Frontmatter Seed" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Build Frontmatter Seed" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({ operation: "build_frontmatter_seed", session: 22 }),
      ),
    );
    expect(await screen.findByText("Frontmatter seed ready")).toBeInTheDocument();
    expect(screen.getAllByText(/run breadcrumb ingest/i).length).toBeGreaterThan(0);
    expect(screen.getAllByText("frontmatter_seed_found").length).toBeGreaterThan(0);
  });

  it("submits run_breadcrumb_ingest after frontmatter seed is found", async () => {
    const user = userEvent.setup();
    const spy = mockRecapIngestWithInspect((body) => {
      if (body.operation === "run_breadcrumb_ingest") {
        return makeStatus({
          status: "recap_applied",
          states: ["recap_applied", "normalized_reused", "frontmatter_seed_found", "breadcrumb_found", "breadcrumb_ingest_ran"],
        });
      }
      return makeStatus({
        status: "breadcrumb_required",
        states: ["recap_applied", "normalized_reused", "frontmatter_seed_found", "breadcrumb_required"],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Run Breadcrumb Ingest" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Run Breadcrumb Ingest" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({ operation: "run_breadcrumb_ingest", session: 22 }),
      ),
    );
    expect(screen.getAllByText("breadcrumb_found").length).toBeGreaterThan(0);
    await waitFor(() =>
      expect(screen.getByText("Next: click Materialize Session Memory.")).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Materialize Session Memory" })).toBeEnabled();
  });

  it("submits materialize_session_memory with edited recap session and shows ready state", async () => {
    const user = userEvent.setup();
    const spy = mockRecapIngestWithInspect((body) => {
      if (body.operation === "materialize_session_memory") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["breadcrumb_found", "session_memory_materialized", "ready_for_planning_activation"],
          ingest_report: { session_memory_record_count: 10, session_memory_check: "ok" },
        });
      }
      return makeStatus({
        states: ["raw_text_received", "recap_preview_created", "breadcrumb_found"],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    const recapSessionInput = screen.getByLabelText("Recap/source session");
    await user.clear(recapSessionInput);
    await user.type(recapSessionInput, "21");
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\n...");
    await user.type(screen.getByLabelText("Session title"), "Session 21 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Stage + Preview" }));
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Materialize Session Memory" })).toBeEnabled(),
    );
    await user.click(screen.getByRole("button", { name: "Materialize Session Memory" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({ operation: "materialize_session_memory", session: 21 }),
      ),
    );
    expect(screen.getAllByText("ready_for_planning_activation").length).toBeGreaterThan(0);
  });

  it("opens the recap view for generated recap memory", async () => {
    const user = userEvent.setup();
    const assign = vi.fn();
    Object.defineProperty(window, "location", {
      value: { ...window.location, assign },
      writable: true,
    });
    vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({ status: "initialized", states: ["ingest_status_inspected"] });
      }
      return makeStatus({
        status: "ready_for_planning_activation",
        states: [
          "raw_text_received",
          "recap_preview_created",
          "recap_applied",
          "frontmatter_seed_found",
          "breadcrumb_found",
          "session_memory_materialized",
          "ready_for_planning_activation",
        ],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.type(screen.getByLabelText("Raw recap text"), "Session 22 Recap\n\nThe party pressed on.");
    await user.type(screen.getByLabelText("Session title"), "Session 22 - Mireward Road and Lysandro");
    await user.click(screen.getByRole("button", { name: "Generate Recap Memory" }));

    const openButton = await screen.findByRole("button", { name: "Open Recap View" });
    expect(screen.getByText(/Recap memory generated\. Open Recap View/)).toBeInTheDocument();
    await user.click(openButton);

    expect(assign).toHaveBeenCalledWith("/plan?tool=recap&session=session-22");
  });


  it("submits build_graph_preview_bundle and shows source bundle blocked state", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["breadcrumb_found", "session_memory_materialized"],
        });
      }
      if (body.operation === "build_graph_preview_bundle") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["breadcrumb_found", "session_memory_materialized", "graph_source_bundle_ready"],
          ingest_report: {
            graph_preview: {
              status: "source_span_bundle_ready",
              manifest_path: "out/graph_memory/runs/longmont-c2/session-22/run/graph_ingest_run_manifest.json",
              blocked_reason: "Graph source bundle ready. Candidate graph extraction is not wired yet.",
            },
          },
        });
      }
      return makeStatus({
        status: "ready_for_planning_activation",
        states: ["breadcrumb_found", "session_memory_materialized"],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.click(screen.getByText("Advanced graph dogfood"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Build Graph Preview" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Build Graph Preview" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({ operation: "build_graph_preview_bundle", session: 22 }),
      ),
    );
    expect(screen.getAllByText("Graph").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Graph source bundle ready. Candidate graph extraction is not wired yet.").length).toBeGreaterThan(0);
  });

  it("submits materialize_preview_supergraph with a candidate graph path", async () => {
    const user = userEvent.setup();
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "inspect_status") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["breadcrumb_found", "session_memory_materialized"],
        });
      }
      if (body.operation === "materialize_preview_supergraph") {
        return makeStatus({
          status: "ready_for_planning_activation",
          states: ["breadcrumb_found", "session_memory_materialized", "preview_union_store_ready"],
          ingest_report: {
            graph_preview: {
              status: "preview_union_store_ready",
              candidate_graph_path: "out/candidate.json",
              preview_union_store_path: "out/graph_memory/runs/longmont-c2/session-22/run/preview_union_supergraph.json",
              can_open_union_graph: true,
              node_count: 2,
              edge_count: 1,
            },
          },
        });
      }
      return makeStatus({
        status: "ready_for_planning_activation",
        states: ["breadcrumb_found", "session_memory_materialized"],
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={23} />);
    await user.click(screen.getByText("Advanced graph dogfood"));
    await user.type(screen.getByLabelText("Candidate graph path"), "out/candidate.json");
    await waitFor(() => expect(screen.getByRole("button", { name: "Materialize Preview Supergraph" })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: "Materialize Preview Supergraph" }));

    await waitFor(() =>
      expect(spy).toHaveBeenLastCalledWith(
        expect.objectContaining({
          operation: "materialize_preview_supergraph",
          session: 22,
          candidate_graph_path: "out/candidate.json",
        }),
      ),
    );
    expect(screen.getByText("status: preview_union_store_ready")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Graph Preview" })).toBeEnabled();
  });

  it("keeps file replacement controls behind explicit advanced disclosure", async () => {
    const user = userEvent.setup();
    render(<IngestionModule campaignId="longmont-c2" session={22} />);
    expect(screen.queryByText(/Replace saved raw notes/)).not.toBeInTheDocument();
    await user.click(screen.getByText("Advanced file controls"));
    await user.click(screen.getByLabelText(/Show file replacement/));
    expect(screen.getByText(/Replace saved raw notes/)).toBeInTheDocument();
    expect(screen.getByText(/Replace existing canonical recap file/)).toBeInTheDocument();
    expect(screen.getByLabelText("Canonical file name override")).toBeInTheDocument();
  });

  it("offers a reconciliation card and repairs duplicate normalized recaps", async () => {
    const user = userEvent.setup();
    const candidates = [
      {
        basename: "Session 23 - Mireward Gate Battle",
        relpath:
          "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - Mireward Gate Battle.md",
        size_bytes: 9746,
        modified_at: "2026-06-21T23:44:00+00:00",
        is_generic: false,
        recommended: true,
      },
      {
        basename: "Session 23 - ingest",
        relpath:
          "Longmont Campaign/Campaign 2/Session Recaps/_normalized/Session 23 - ingest.md",
        size_bytes: 10476,
        modified_at: "2026-06-21T23:44:00+00:00",
        is_generic: true,
        recommended: false,
      },
    ];
    const spy = vi.spyOn(recapIngestApi, "postRecapIngest").mockImplementation(async (body) => {
      if (body.operation === "reconcile_normalized_recap") {
        return makeStatus({
          session: 23,
          status: "breadcrumb_required",
          states: ["ingest_status_inspected", "normalized_recap_reconciled", "recap_reused"],
          ingest_report: {
            reconciled_kept_basename: body.keep_basename,
            reconciled_archived: [{ from: "a", to: "b" }],
          },
        });
      }
      return makeStatus({
        session: 23,
        status: "initialized",
        states: ["ingest_status_inspected", "normalized_recap_duplicates"],
        entity_spelling_audit: [],
        ingest_report: { normalized_recap_candidates: candidates },
      });
    });

    render(<IngestionModule campaignId="longmont-c2" session={24} />);

    await screen.findByText("Resolve duplicate normalized recaps");
    expect(screen.getAllByText("Session 23 - Mireward Gate Battle").length).toBeGreaterThan(0);
    expect(screen.getByText("Session 23 - ingest")).toBeInTheDocument();
    expect(screen.getByText("recommended")).toBeInTheDocument();
    expect(screen.getByText("tool-shaped")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Repair and Prove" }));

    await waitFor(() =>
      expect(spy).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: "reconcile_normalized_recap",
          keep_basename: "Session 23 - Mireward Gate Battle",
          session: 23,
        }),
      ),
    );
    await waitFor(() =>
      expect(screen.queryByText("Resolve duplicate normalized recaps")).not.toBeInTheDocument(),
    );
  });
});
