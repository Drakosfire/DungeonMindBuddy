import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { GraphMergeReconciliationMaterializationPanel } from "./GraphMergeReconciliationMaterializationPanel";

vi.mock("../../api/liveApi", () => ({
  prepareGraphMergeReconciliationMaterialization: vi.fn(),
  applyGraphMergeReconciliationMaterialization: vi.fn(),
}));

import {
  applyGraphMergeReconciliationMaterialization,
  prepareGraphMergeReconciliationMaterialization,
} from "../../api/liveApi";

const prepareWithPlans = {
  prepared: true,
  campaign_id: "longmont-c2",
  session_id: "session-23",
  overlay_path: "/tmp/overlay.json",
  union_store_path: "/tmp/preview_union.json",
  materialization_pass_id: "materialize:longmont-c2:session-23:abc123",
  overlay_token: "overlay-token",
  union_store_token: "union-token",
  plan_digest: "plan-digest-value",
  confirm_token: "confirm-token",
  summary: {
    merge_assertion_count: 1,
    applicable_assertion_count: 1,
    skipped_assertion_count: 0,
    redirect_count: 1,
    edge_rewire_count: 1,
    edge_dedupe_count: 0,
  },
  diagnostics: [],
  no_mutation_guarantees: ["Prepare wrote nothing to disk."],
};

const prepareNoPlans = {
  ...prepareWithPlans,
  confirm_token: "confirm-token-empty",
  summary: {
    merge_assertion_count: 0,
    applicable_assertion_count: 0,
    skipped_assertion_count: 0,
    redirect_count: 0,
    edge_rewire_count: 0,
    edge_dedupe_count: 0,
  },
};

const applyResponse = {
  applied: true,
  campaign_id: "longmont-c2",
  session_id: "session-23",
  overlay_path: "/tmp/overlay.json",
  union_store_path: "/tmp/preview_union.json",
  backup_path: "/tmp/backups/preview_union.json.backup.json",
  materialization_pass_id: prepareWithPlans.materialization_pass_id,
  applied_assertion_ids: ["assert-merge-lysandra"],
  skipped_assertion_ids: [],
  summary: {
    redirects_added: 1,
    merge_records_added: 1,
    survivor_nodes_created: 0,
    survivor_nodes_updated: 1,
    merged_away_nodes_marked: 1,
    edges_rewired: 1,
    edges_deduped: 0,
  },
  diagnostics: [],
  no_mutation_guarantees: ["Apply writes only the selected union graph store (with backup)."],
};

describe("GraphMergeReconciliationMaterializationPanel", () => {
  beforeEach(() => {
    vi.mocked(prepareGraphMergeReconciliationMaterialization).mockReset();
    vi.mocked(applyGraphMergeReconciliationMaterialization).mockReset();
  });

  it("shows unavailable copy without preview store path", () => {
    render(
      <GraphMergeReconciliationMaterializationPanel
        campaignId="longmont-c2"
        sessionId="session-23"
      />,
    );

    expect(
      screen.getByText(/Select a live ingest run with a preview union graph store/i),
    ).toBeInTheDocument();
    expect(screen.queryByTestId("graph-merge-reconciliation-prepare-button")).not.toBeInTheDocument();
  });

  it("shows no-plans copy when prepare finds zero applicable merges", async () => {
    vi.mocked(prepareGraphMergeReconciliationMaterialization).mockResolvedValue(prepareNoPlans);
    const user = userEvent.setup();

    render(
      <GraphMergeReconciliationMaterializationPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        previewUnionStorePath="stores/preview_union.json"
      />,
    );

    await user.click(screen.getByTestId("graph-merge-reconciliation-prepare-button"));

    expect(
      await screen.findByTestId("graph-merge-reconciliation-no-plans"),
    ).toHaveTextContent("No committed identity merges need materialization");
    expect(screen.queryByTestId("graph-merge-reconciliation-apply-button")).not.toBeInTheDocument();
  });

  it("shows apply button when prepare finds an applicable plan", async () => {
    vi.mocked(prepareGraphMergeReconciliationMaterialization).mockResolvedValue(prepareWithPlans);
    const user = userEvent.setup();

    render(
      <GraphMergeReconciliationMaterializationPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        previewUnionStorePath="stores/preview_union.json"
      />,
    );

    await user.click(screen.getByTestId("graph-merge-reconciliation-prepare-button"));

    expect(await screen.findByTestId("graph-merge-reconciliation-apply-button")).toBeEnabled();
    expect(screen.getByText(/1 would apply now/i)).toBeVisible();
    expect(screen.queryByText("assert-merge-lysandra")).not.toBeInTheDocument();
  });

  it("apply success shows summary, backup in details, and refreshes projection", async () => {
    vi.mocked(prepareGraphMergeReconciliationMaterialization).mockResolvedValue(prepareWithPlans);
    vi.mocked(applyGraphMergeReconciliationMaterialization).mockResolvedValue(applyResponse);
    const onRefreshProjection = vi.fn().mockResolvedValue({ node_views: {} });
    const user = userEvent.setup();

    render(
      <GraphMergeReconciliationMaterializationPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        previewUnionStorePath="stores/preview_union.json"
        onRefreshProjection={onRefreshProjection}
      />,
    );

    await user.click(screen.getByTestId("graph-merge-reconciliation-prepare-button"));
    await user.click(await screen.findByTestId("graph-merge-reconciliation-apply-button"));

    expect(await screen.findByTestId("graph-merge-reconciliation-apply-summary")).toBeInTheDocument();
    expect(screen.getByText(/1 redirect added/i)).toBeVisible();
    await waitFor(() => {
      expect(onRefreshProjection).toHaveBeenCalledTimes(1);
    });

    const details = screen.getByText("Technical apply details").closest("details");
    expect(details).not.toBeNull();
    await user.click(details!);
    const scope = within(details as HTMLElement);
    expect(scope.getByText(applyResponse.backup_path!)).toBeInTheDocument();
    expect(scope.getByText("assert-merge-lysandra")).toBeInTheDocument();
  });

  it("shows user-facing error for stale conflict responses", async () => {
    vi.mocked(prepareGraphMergeReconciliationMaterialization).mockResolvedValue(prepareWithPlans);
    vi.mocked(applyGraphMergeReconciliationMaterialization).mockRejectedValue(
      new Error(JSON.stringify({ code: "stale_union_store", message: "stale union store" })),
    );
    const user = userEvent.setup();

    render(
      <GraphMergeReconciliationMaterializationPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        previewUnionStorePath="stores/preview_union.json"
      />,
    );

    await user.click(screen.getByTestId("graph-merge-reconciliation-prepare-button"));
    await user.click(await screen.findByTestId("graph-merge-reconciliation-apply-button"));

    expect(
      await screen.findByText(/Prepare again before applying/i),
    ).toBeInTheDocument();
  });

  it("keeps raw ids in collapsed technical details only on prepare preview", async () => {
    vi.mocked(prepareGraphMergeReconciliationMaterialization).mockResolvedValue(prepareWithPlans);
    const user = userEvent.setup();

    render(
      <GraphMergeReconciliationMaterializationPanel
        campaignId="longmont-c2"
        sessionId="session-23"
        previewUnionStorePath="stores/preview_union.json"
      />,
    );

    await user.click(screen.getByTestId("graph-merge-reconciliation-prepare-button"));
    await screen.findByTestId("graph-merge-reconciliation-prepare-preview");

    expect(screen.queryByText(prepareWithPlans.materialization_pass_id)).not.toBeVisible();

    const details = screen.getByText("Technical materialization details").closest("details");
    await user.click(details!);
    expect(
      within(details as HTMLElement).getByText(prepareWithPlans.materialization_pass_id),
    ).toBeInTheDocument();
  });
});
