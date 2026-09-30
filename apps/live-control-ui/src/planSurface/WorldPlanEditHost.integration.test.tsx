import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import * as liveApi from "../api/liveApi";
import type { WorldOwnedPlanRecordV2 } from "../api/types";
import { SelectedWorldProvider } from "../selectedWorld/SelectedWorldContext";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { PeekRegionProvider } from "../surfaceInteraction/peekHost";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { PlanSurfacePage } from "./PlanSurfacePage";

const worldId = "edit-host-world";
let currentPublication: SurfaceInteractionPublication | null = null;

function PublicationWitness() {
  currentPublication = useAgentInteraction().surfaceInteractionPublication;
  return <output data-testid="edit-target">{currentPublication?.canvas?.workObject
    ? `${currentPublication.canvas.workObject.kind}:${currentPublication.canvas.workObject.id}` : "none"}</output>;
}

function renderPlan() {
  return render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <AgentInteractionProvider>
        <SurfaceContextProvider>
          <PeekRegionProvider>
            <PlanSurfacePage />
            <PublicationWitness />
          </PeekRegionProvider>
        </SurfaceContextProvider>
      </AgentInteractionProvider>
    </SelectedWorldProvider>,
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  currentPublication = null;
  window.history.replaceState({}, "", "/");
});

it("routes World Plan title, Save, formatting and insertion through the real docked EditHost at 390×844", async () => {
  Object.defineProperty(window, "innerWidth", { configurable: true, value: 390 });
  Object.defineProperty(window, "innerHeight", { configurable: true, value: 844 });
  window.history.replaceState({}, "", `/plan?world=${worldId}`);
  const draftKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  localStorage.setItem(draftKey, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Plan",
    markdown: "# Session plan\n",
    revision: null,
  }));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId,
      name: "Edit Host World", source_root_relpath: "corpus/edit-host-world",
      created_at: "2026-01-01T00:00:00Z" }],
  });
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
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [],
  });
  const savedRecord: WorldOwnedPlanRecordV2 = {
    schema_version: "dmb_world_owned_plan_record_v2",
    scope_mode: "world",
    document_id: "saved-edit-host-plan",
    title: "Edited title",
    campaign_id: null,
    world_id: worldId,
    target_session: null,
    kind: "plan",
    target_relpath: "out/workspace/plan/saved-edit-host-plan.md",
    status: "active",
    content_status: "committed",
    revision: 3,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
  const create = vi.spyOn(liveApi, "createWorldOwnedPlan").mockResolvedValue(savedRecord);
  vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: savedRecord.document_id,
    title: savedRecord.title,
    target_relpath: savedRecord.target_relpath!,
    target_display_path: savedRecord.target_relpath!,
    registry_revision: 2,
    file_exists: false,
    writer_ok: true,
    writer_confirm_token: "prepared-edit-host",
    warnings: [],
    diagnostics: [],
  });
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: savedRecord.document_id,
    title: savedRecord.title,
    target_relpath: savedRecord.target_relpath!,
    target_display_path: savedRecord.target_relpath!,
    registry_revision: 3,
    committed_revision: 3,
    committed_record: savedRecord,
    normalized_content_sha256: "a".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record: savedRecord,
    markdown: "# Session plan\n",
    content_sha256: "a".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 3,
  });

  const view = renderPlan();
  const host = await screen.findByTestId("surface-edit-host");
  await waitFor(() => expect(within(host).getByRole("button", { name: "Save Plan" })).toBeEnabled());
  expect(host).toHaveAttribute("data-layout", "dock");
  const localId = JSON.parse(localStorage.getItem(draftKey) ?? "null").local_draft_id;
  await waitFor(() => expect(screen.getByTestId("edit-target")).toHaveTextContent(`plan-local-draft:${localId}`));
  expect(new Set(currentPublication!.editCommands.map((command) => command.id)).size).toBe(currentPublication!.editCommands.length);
  expect(currentPublication!.editCommands.every((command) =>
    command.target.kind === "plan-local-draft" && command.target.id === localId)).toBe(true);
  const retiredSave = currentPublication!.editCommands.find((command) => command.label === "Save Plan")!.invoke;
  const retiredBold = currentPublication!.editCommands.find((command) => command.label === "Bold")!.invoke;
  expect(within(screen.getByTestId("world-owned-plan")).queryByLabelText("Plan title")).toBeNull();
  expect(within(screen.getByTestId("world-owned-plan")).queryByRole("button", { name: "Save Plan" })).toBeNull();
  expect(within(screen.getByTestId("world-owned-plan")).queryByRole("button", { name: "Bold" })).toBeNull();

  fireEvent.click(within(host).getByRole("button", { name: "Close Edit" }));
  expect(within(host).queryByLabelText("Plan title")).toBeNull();
  fireEvent.click(within(host).getByRole("button", { name: "Edit" }));
  expect(within(host).getByLabelText("Plan title")).toHaveValue("Plan");
  fireEvent.change(within(host).getByLabelText("Plan title"), { target: { value: "Edited title" } });
  expect(JSON.parse(localStorage.getItem(draftKey) ?? "null").title).toBe("Edited title");
  expect(within(host).getByRole("button", { name: "Bold" })).toBeEnabled();
  fireEvent.click(within(host).getByRole("button", { name: "Bold" }));
  fireEvent.click(within(host).getByRole("button", { name: "Read aloud" }));
  await waitFor(() => expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("Read aloud"));
  fireEvent.click(within(host).getByRole("button", { name: "Save Plan" }));
  await screen.findByText("Saved to this World.");
  expect(create).toHaveBeenCalledWith(expect.objectContaining({ world_id: worldId, title: "Edited title" }));
  expect(commit).toHaveBeenCalledWith(expect.objectContaining({ world_id: worldId, document_id: savedRecord.document_id }));
  await waitFor(() => expect(screen.getByTestId("edit-target")).toHaveTextContent(`document:${savedRecord.document_id}`));
  const savedJournal = localStorage.getItem(draftKey);
  retiredSave();
  retiredBold();
  expect(commit).toHaveBeenCalledTimes(1);
  expect(localStorage.getItem(draftKey)).toBe(savedJournal);
  const unmountedSave = currentPublication!.editCommands.find((command) => command.label === "Save Plan")!.invoke;
  view.unmount();
  unmountedSave();
  expect(commit).toHaveBeenCalledTimes(1);
});
