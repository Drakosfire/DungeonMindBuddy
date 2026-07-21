import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { IngestionSourceBundle, SourceUnit } from "../../api/types";
import { PlanGraphLensProvider } from "../PlanGraphLensContext";
import { PlanGraphLoadPanel } from "./PlanGraphLoadPanel";

function wrapper({ children }: { children: ReactNode }) {
  return createElement(PlanGraphLensProvider, { planCampaignId: "longmont-c2" }, children);
}

function unitWithSession(sessionNumber: number): SourceUnit {
  return {
    unitId: `unit-${sessionNumber}`,
    artifactId: `artifact-${sessionNumber}`,
    anchorId: `anchor-${sessionNumber}`,
    unitKind: "normalized_recap",
    label: `Session ${sessionNumber}`,
    fields: { sessionNumber },
    sourceAnchor: {
      anchorId: `anchor-${sessionNumber}`,
      artifactId: `artifact-${sessionNumber}`,
      label: `Session ${sessionNumber}`,
      anchorKind: "document",
      locator: {
        locatorId: `loc-${sessionNumber}`,
        scheme: "corpus_path",
        value: `session-${sessionNumber}.md`,
      },
      relatedLocators: [],
      displaySummary: null,
      metadata: {},
    },
    canonState: "played_canon",
    lifecycleState: "ingested",
    evidenceRole: "source_evidence",
    authorityState: "played_truth",
    visibilityState: "gm_private",
    provenance: [],
    diagnostics: {},
  };
}

function bundleWithSessions(...sessions: number[]): IngestionSourceBundle {
  return {
    schema_version: "dmb_ingestion_source_bundle_v1",
    bundle_id: `bundle-${sessions.join("-")}`,
    scope: "campaign-ingested",
    corpus_root: "corpus",
    artifacts: [],
    anchors: [],
    units: sessions.map(unitWithSession),
    coverage: {},
    diagnostics: [],
  };
}

describe("PlanGraphLoadPanel", () => {
  beforeEach(() => {
    window.history.replaceState({}, "", "/plan");
  });

  it("renders lens summary with node count when projection is ready", () => {
    render(
      <PlanGraphLoadPanel
        projectionState="ready"
        nodeCount={45}
        focusOptions={[]}
        loadBundle={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByTestId("plan-graph-load-panel")).toBeInTheDocument();
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · no session focus · 45 nodes · ready/i,
    );
  });

  it("shows loading status while projection loads", () => {
    render(
      <PlanGraphLoadPanel
        projectionState="loading"
        nodeCount={0}
        focusOptions={[]}
        loadBundle={vi.fn()}
      />,
      { wrapper },
    );

    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(/Loading/i);
  });

  it("toggles a campaign into the lens", async () => {
    const user = userEvent.setup();
    render(
      <PlanGraphLoadPanel
        projectionState="ready"
        nodeCount={45}
        focusOptions={[]}
        loadBundle={vi.fn()}
      />,
      { wrapper },
    );

    const c1 = screen.getByRole("checkbox", { name: /Longmont C1/i });
    expect(c1).not.toBeChecked();
    await user.click(c1);
    expect(c1).toBeChecked();
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(/Union · C1\+C2/i);
  });

  it("offers Focus session options from ingest bundles only", async () => {
    const loadBundle = vi.fn(async (_scope?: string, campaignId?: string) => {
      if (campaignId === "longmont-c2") return bundleWithSessions(24, 22, 1);
      if (campaignId === "longmont-c1") return bundleWithSessions(3);
      return bundleWithSessions();
    });

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} loadBundle={loadBundle} />,
      { wrapper },
    );

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "C2 · Session 24" })).toBeInTheDocument();
    });
    expect(screen.getByRole("option", { name: "C2 · Session 22" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "C2 · Session 1" })).toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "C2 · Session 40" })).not.toBeInTheDocument();
    expect(screen.queryByRole("option", { name: "C1 · Session 3" })).not.toBeInTheDocument();
    expect(loadBundle).toHaveBeenCalledWith("campaign-ingested", "longmont-c2");
  });

  it("applies Focus session and updates the status line", async () => {
    const user = userEvent.setup();
    const loadBundle = vi.fn(async () => bundleWithSessions(24, 22));

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} loadBundle={loadBundle} />,
      { wrapper },
    );

    await waitFor(() => {
      expect(screen.getByRole("option", { name: "C2 · Session 24" })).toBeInTheDocument();
    });

    await user.selectOptions(screen.getByLabelText("Focus session"), "longmont-c2:24");
    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /C2 only · C2 · Session 24 · 45 nodes · ready/i,
    );
  });

  it("clears stale URL focus that is absent from ingest bundles", async () => {
    window.history.replaceState(
      {},
      "",
      "/plan?campaigns=longmont-c2&session=longmont-c2:40",
    );
    const loadBundle = vi.fn(async () => bundleWithSessions(24, 22, 1));

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} loadBundle={loadBundle} />,
      { wrapper },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
        /C2 only · no session focus · 45 nodes · ready/i,
      );
    });
    expect(screen.queryByRole("option", { name: "C2 · Session 40" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Focus session")).toHaveValue("");
    expect(window.location.search).not.toMatch(/session=longmont-c2:40/);
    expect(screen.getByRole("option", { name: "C2 · Session 24" })).toBeInTheDocument();
  });

  it("keeps valid URL focus that is present in ingest bundles", async () => {
    window.history.replaceState(
      {},
      "",
      "/plan?campaigns=longmont-c2&session=longmont-c2:24",
    );
    const loadBundle = vi.fn(async () => bundleWithSessions(24, 22, 1));

    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={45} loadBundle={loadBundle} />,
      { wrapper },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
        /C2 only · C2 · Session 24 · 45 nodes · ready/i,
      );
    });
    expect(screen.getByLabelText("Focus session")).toHaveValue("longmont-c2:24");
    expect(window.location.search).toMatch(/session=longmont-c2%3A24|session=longmont-c2:24/);
  });

  it("shows fail-closed status when graph lens context is missing", () => {
    render(
      <PlanGraphLoadPanel projectionState="ready" nodeCount={0} focusOptions={[]} />,
    );

    expect(screen.getByTestId("plan-graph-load-status")).toHaveTextContent(
      /Graph lens unavailable/i,
    );
  });
});
