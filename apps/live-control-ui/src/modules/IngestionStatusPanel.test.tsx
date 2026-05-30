import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { RecapIngestStatus } from "../api/types";
import { IngestionStatusPanel } from "./IngestionStatusPanel";

const sample: RecapIngestStatus = {
  schema: "dmb_raw_recap_ingest_status_v1",
  campaign_id: "longmont-c2",
  session: 22,
  status: "breadcrumb_required",
  states: ["raw_text_received", "recap_preview_created", "breadcrumb_required"],
  paths: {
    staged_raw_notes: "a",
    canonical_recap: "b",
    normalized_recap: "c",
    breadcrumbed_recap: "d",
    session_memory_jsonl: "e",
  },
  authority: {
    staged_raw_notes: "pre_canonical_evidence",
    canonical_recap: "canon_play",
    normalized_recap: "canon_play_prepared",
    breadcrumbed_recap: "canon_play_routed",
    session_memory: "derived_memory",
  },
  warnings: ["entity spelling variants detected; review_only"],
  errors: [],
  next_actions: ["Generate/bless breadcrumb artifact for Session 22"],
  ingest_report: {
    title_line_stripped: true,
    paragraph_count_in: 7,
    paragraph_count_out: 7,
    duplicates_detected: 0,
    duplicates_removed: 0,
    preview_diff: "@@ -1 +1 @@\n-test\n+test\n",
  },
  entity_spelling_audit: [],
};

describe("IngestionStatusPanel", () => {
  it("renders status sections, ingest report fields, and read-only diff", () => {
    render(<IngestionStatusPanel result={sample} />);
    expect(screen.getAllByText("breadcrumb_required").length).toBeGreaterThan(0);
    expect(screen.getByText("raw_text_received")).toBeInTheDocument();
    expect(screen.getByText("entity spelling variants detected; review_only")).toBeInTheDocument();
    expect(screen.getByText(/Generate\/bless breadcrumb artifact/)).toBeInTheDocument();
    expect(screen.getByText(/title_line_stripped: true/)).toBeInTheDocument();
    expect(screen.getByLabelText("Canonical preview diff")).toHaveTextContent("@@ -1 +1 @@");
  });
});
