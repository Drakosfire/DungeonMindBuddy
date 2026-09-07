import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { GraphReviewWorkbenchHeader } from "./GraphReviewWorkbenchHeader";

describe("GraphReviewWorkbenchHeader", () => {
  it("shows empty-state copy and Load recap button when nothing is loaded", () => {
    render(
      <GraphReviewWorkbenchHeader loaded={false} sessionLabel={null} onOpenLoad={vi.fn()} />,
    );

    expect(screen.getByRole("heading", { name: "Graph Review Workbench" })).toBeInTheDocument();
    expect(screen.getByText("Prose-first review tool")).toBeInTheDocument();
    expect(screen.getByText("No session loaded")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(screen.queryByTestId("graph-authoring-mode-toggle")).not.toBeInTheDocument();
  });

  it("shows compact session label and Load recap when loaded", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel="Session 1 · Longmont C1"
        onOpenLoad={vi.fn()}
      />,
    );

    expect(screen.getByText("Session 1 · Longmont C1")).toBeInTheDocument();
    expect(screen.queryByText(/category_decomposed/i)).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Load recap" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Author graph objects" })).not.toBeInTheDocument();
    expect(screen.queryByTestId("graph-authoring-mode-toggle")).not.toBeInTheDocument();
  });

  it("keeps ingest identity behind Advanced details when an exact run is loaded", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel={null}
        onOpenLoad={vi.fn()}
        exactRun={{
          extractionRunId: "graph-ingest:longmont-c1:session-17:20260724T031527Z",
          sourceDomain: "recap",
          status: "validated",
          sourceArtifactId: "artifact:recap:longmont-c1:session-17",
          profileId: null,
          campaignId: "longmont-c1",
          sessionId: "session-17",
          documentId: null,
          revision: null,
          reviewable: false,
          readOnly: true,
          worldId: "eldyrwild",
          graphId: "rev:abc",
          inspectOnlyReason: "This ExtractionRun is inspect-only and cannot be prepared for World Graph merge.",
        }}
      />,
    );

    expect(screen.getByText("Session 17 · Longmont C1")).toBeInTheDocument();
    expect(screen.getByText("Read-only")).toBeInTheDocument();
    expect(screen.getByText("Advanced details")).toBeInTheDocument();
    expect(screen.queryByText("Exact run loaded")).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-review-exact-run-banner")).toHaveTextContent(
      "graph-ingest:longmont-c1:session-17:20260724T031527Z",
    );
    expect(screen.getByTestId("graph-review-exact-run-scope")).toHaveTextContent(
      "campaign longmont-c1 · session session-17",
    );
  });

  it("uses exact-run identity over a stale catalog session label", () => {
    render(
      <GraphReviewWorkbenchHeader
        loaded
        sessionLabel="Session 23 · Longmont C2"
        onOpenLoad={vi.fn()}
        exactRun={{
          extractionRunId: "er_handoff_b",
          sourceDomain: "recap",
          status: "validated",
          sourceArtifactId: "sa_handoff",
          profileId: null,
          campaignId: "longmont-c1",
          sessionId: "session-17",
          documentId: null,
          revision: null,
          reviewable: false,
          readOnly: true,
          worldId: "eldyrwild",
          graphId: "rev:abc",
          inspectOnlyReason: "This ExtractionRun is inspect-only and cannot be prepared for World Graph merge.",
        }}
      />,
    );

    expect(screen.getByText("Session 17 · Longmont C1")).toBeInTheDocument();
    expect(screen.queryByText("Session 23 · Longmont C2")).not.toBeInTheDocument();
    expect(screen.getByTestId("graph-review-exact-run-banner")).toHaveTextContent("er_handoff_b");
    expect(screen.getByTestId("graph-review-exact-run-banner")).not.toHaveTextContent(
      "er_stale_catalog",
    );
  });
});

