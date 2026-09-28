import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import type { WorldOwnedPlanRecordV2 } from "../api/types";
import { PlanSurfacePage } from "./PlanSurfacePage";

vi.mock("../chrome/AppChrome", () => ({
  AppChrome: ({ children }: { children: ReactNode }) => <div>{children}</div>,
}));
vi.mock("./PlanSurfaceShell", () => ({
  PlanSurfaceShell: ({ planView }: { planView: { campaign_id: string } }) => (
    <div data-testid="plan-page-campaign">{planView.campaign_id}</div>
  ),
}));

const worldId = "of-conks-cons-demo";

function VerifiedPlanPage() {
  const selected = useSelectedWorld();
  return selected.kind === "managed" ? <PlanSurfacePage /> : <span>{selected.kind}</span>;
}

afterEach(() => vi.restoreAllMocks());

it("saves a blank managed World Plan through the exact World-scoped V2 contract", async () => {
  localStorage.setItem(`dmb:world-plan-local-draft:v2:${worldId}`, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Plan",
    markdown: "# Session 28\n",
    revision: null,
  }));
  const getPlanView = vi.spyOn(liveApi, "getPlanView");
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue({
    schema_version: "dmb_managed_world_plan_context_v2",
    scope_mode: "world",
    world_id: worldId,
    campaign_id: null,
    session: null,
    authoritative: false,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [],
  });
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{
      schema_version: "dmb_world_container_record_v1",
      world_id: worldId,
      name: "Of Conks",
      source_root_relpath: "corpus/of-conks-cons-demo-markdown",
      created_at: "2026-01-01T00:00:00Z",
    }],
  });
  const record: WorldOwnedPlanRecordV2 = {
    schema_version: "dmb_world_owned_plan_record_v2",
    scope_mode: "world",
    document_id: "66a4b5e8-3557-4902-984b-1fe4f68de044",
    title: "Plan",
    campaign_id: null,
    world_id: worldId,
    target_session: null,
    kind: "plan",
    target_relpath: "out/workspace/plan/66a4b5e8-3557-4902-984b-1fe4f68de044.md",
    status: "active",
    content_status: "committed",
    revision: 3,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [],
  });
  vi.spyOn(liveApi, "createWorldOwnedPlan").mockResolvedValue(record);
  vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: record.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 2,
    file_exists: false,
    writer_ok: true,
    writer_confirm_token: "prepared-world-token",
    warnings: [],
    diagnostics: [],
  });
  vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: record.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 3,
    committed_revision: 3,
    committed_record: record,
    normalized_content_sha256: "a".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record,
    markdown: "# Session 28\n",
    content_sha256: "a".repeat(64),
    file_fingerprint: "postgres",
    file_exists: false,
    loaded_revision: 3,
  });
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(screen.getByText("Saved to this World.")).toBeInTheDocument());
  expect(liveApi.createWorldOwnedPlan).toHaveBeenCalledWith({
    schema_version: "dmb_workspace_document_create_v2",
    scope_mode: "world",
    world_id: worldId,
    title: "Plan",
  });
  expect(liveApi.prepareTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
  }));
  expect(liveApi.commitWorldOwnedPlanMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    world_id: worldId,
    writer_confirm_token: "prepared-world-token",
  }));
  expect(getPlanView).not.toHaveBeenCalled();
  expect(liveApi.getManagedWorldPlanContext).toHaveBeenCalledWith(worldId);
  expect(screen.queryByTestId("plan-page-campaign")).not.toBeInTheDocument();
});
