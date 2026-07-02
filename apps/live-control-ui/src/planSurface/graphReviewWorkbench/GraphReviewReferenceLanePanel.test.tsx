import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { GraphReviewReferenceLanePanel } from "./GraphReviewReferenceLanePanel";
import type { GraphReviewReferenceLaneView } from "./graphReviewReferenceLaneUtils";

const base: GraphReviewReferenceLaneView = { kind: "empty_reference", laneId: "empty", label: "No reference lane selected", role: "reference", sourceKind: "projection_payload", status: "unknown", summaryItems: [], warnings: [], note: "Projected source rendering is not implemented for this reference lane yet." };

describe("GraphReviewReferenceLanePanel", () => {
  it("renders empty reference guidance", () => {
    render(<GraphReviewReferenceLanePanel referenceLane={base} />);
    expect(screen.getByText("No reference lane selected yet. Select a gold session or manual review variant to populate reference context.")).toBeInTheDocument();
  });
  it("renders gold reference summary and warnings", () => {
    render(<GraphReviewReferenceLanePanel referenceLane={{ ...base, kind: "gold_reference", label: "Gold Fixture", role: "gold", sourceKind: "gold_fixture", status: "missing_projection", warnings: ["Gold/live compare data is not loaded yet."], summaryItems: [{ label: "Gold fixture id", value: "g1" }] }} />);
    expect(screen.getByText("Gold fixture reference")).toBeInTheDocument();
    expect(screen.getByText("g1")).toBeInTheDocument();
    expect(screen.getByText("Gold/live compare data is not loaded yet.")).toBeInTheDocument();
  });
  it("renders manual variant reference summary and note", () => {
    render(<GraphReviewReferenceLanePanel referenceLane={{ ...base, kind: "manual_variant_reference", label: "Manual v1", role: "variant", sourceKind: "manual_review_variant", summaryItems: [{ label: "Variant name", value: "v1" }] }} />);
    expect(screen.getByText("Manual variant reference")).toBeInTheDocument();
    expect(screen.getByText("v1")).toBeInTheDocument();
    expect(screen.getByText(/not projected source text/i)).toBeInTheDocument();
  });
});
