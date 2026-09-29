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

function worldPlanRecord(id: string, owner: string, revision = 1): WorldOwnedPlanRecordV2 {
  return {
    schema_version: "dmb_world_owned_plan_record_v2",
    scope_mode: "world",
    document_id: id,
    title: "Plan",
    campaign_id: null,
    world_id: owner,
    target_session: null,
    kind: "plan",
    target_relpath: `out/workspace/plan/${id}.md`,
    status: "active",
    content_status: "committed",
    revision,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function managedContext(owner: string) {
  return {
    schema_version: "dmb_managed_world_plan_context_v2" as const,
    scope_mode: "world" as const,
    world_id: owner,
    campaign_id: null,
    session: null,
    authoritative: false,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [],
  };
}

function VerifiedPlanPage() {
  const selected = useSelectedWorld();
  return selected.kind === "managed" ? <PlanSurfacePage /> : <span>{selected.kind}</span>;
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

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

it("keeps a late World A create acknowledgement in A's recovery journal after navigating to World B", async () => {
  const worldA = "world-a";
  const worldB = "world-b";
  const keyA = `dmb:world-plan-local-draft:v2:${worldA}`;
  const keyB = `dmb:world-plan-local-draft:v2:${worldB}`;
  localStorage.setItem(keyA, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldA,
    document_id: null,
    title: "A plan",
    markdown: "# World A notes\n",
    revision: null,
  }));
  localStorage.setItem(keyB, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldB,
    document_id: null,
    title: "B plan",
    markdown: "# World B notes\n",
    revision: null,
  }));
  let resolveCreate!: (record: WorldOwnedPlanRecordV2) => void;
  const create = vi.spyOn(liveApi, "createWorldOwnedPlan").mockImplementation(() => new Promise((resolve) => {
    resolveCreate = resolve;
  }));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockRejectedValue(new Error("A-scoped continuation stopped"));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockImplementation(async (id) => managedContext(id));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [worldA, worldB].map((id) => ({
      schema_version: "dmb_world_container_record_v1" as const,
      world_id: id,
      name: id,
      source_root_relpath: `corpus/${id}`,
      created_at: "2026-01-01T00:00:00Z",
    })),
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockImplementation(async (id) => ({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: id,
    records: [],
  }));
  window.history.replaceState({}, "", `/plan?world=${worldA}`);
  const view = render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldA}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(create).toHaveBeenCalledWith(expect.objectContaining({ world_id: worldA })));

  window.history.replaceState({}, "", `/plan?world=${worldB}`);
  view.rerender(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldB}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await waitFor(() => expect(screen.getByLabelText("Plan title")).toHaveValue("B plan"));

  resolveCreate(worldPlanRecord("created-in-a", worldA, 1));
  await waitFor(() => {
    const recoveredA = JSON.parse(localStorage.getItem(keyA) ?? "null");
    expect(recoveredA.document_id).toBe("created-in-a");
  });
  expect(window.location.search).toBe(`?world=${worldB}`);
  expect(JSON.parse(localStorage.getItem(keyB) ?? "null")).toMatchObject({
    world_id: worldB,
    document_id: null,
    markdown: "# World B notes\n",
  });
  await waitFor(() => expect(prepare).toHaveBeenCalledWith(expect.objectContaining({ world_id: worldA })));
  expect(commit).not.toHaveBeenCalled();
});

it("persists the prepared revision before commit and retries against that exact revision", async () => {
  const documentId = "prepared-revision-plan";
  const record = worldPlanRecord(documentId, worldId, 1);
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  localStorage.setItem(key, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Plan",
    markdown: "# Intended plan\n",
    revision: 1,
  }));
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockResolvedValue(record);
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
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
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [record],
  });
  let snapshotCalls = 0;
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async () => {
    snapshotCalls += 1;
    const revision = snapshotCalls === 1 ? 1 : 2;
    return {
      schema_version: "dmb_workspace_document_snapshot_v2",
      record: { ...record, revision },
      markdown: revision === 2 ? "# Intended plan\n" : "# Original\n",
      content_sha256: "a".repeat(64),
      file_fingerprint: "postgres",
      file_exists: false,
      loaded_revision: revision,
    };
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision").mockResolvedValue({
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    kind: "plan",
    campaign_id: null,
    title: "Plan",
    status: "active",
    object_revision: 1,
    work_revision_id: "revision-1",
    revision_n: 1,
    markdown: "# Original\n",
    content_sha256: "a".repeat(64),
    has_divergent_working_copy: true,
    target_relpath: record.target_relpath,
  });
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Plan",
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: request.expected_revision + 1,
    file_exists: false,
    writer_ok: true,
    writer_confirm_token: `token-${request.expected_revision + 1}`,
    warnings: [],
    diagnostics: [],
  }));
  let resolveCommit!: (value: Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>) => void;
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite")
    .mockRejectedValueOnce(new Error("commit response failed"))
    .mockImplementationOnce(() => new Promise((resolve) => { resolveCommit = resolve; }));
  const commitReceipt = {
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: documentId,
      title: "Plan",
      target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!,
      registry_revision: 4,
      committed_revision: 3,
      committed_record: { ...record, revision: 3 },
      normalized_content_sha256: "b".repeat(64),
      writer_ok: true,
      writer_phase: "commit",
      diagnostics: [],
  } satisfies Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>;
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await screen.findByText("commit response failed");
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    revision: 2,
    pending_write: { phase: "commit", base_revision: 1, prepared_revision: 2 },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(commit).toHaveBeenCalledTimes(2));
  fireEvent.change(screen.getByLabelText("Plan title"), { target: { value: "Newer title edit" } });
  const journalWhileCommitPending = JSON.parse(localStorage.getItem(key) ?? "null");
  expect(journalWhileCommitPending.title).toBe("Newer title edit");
  resolveCommit(commitReceipt);
  await screen.findByText("Saved to this World.");
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    title: "Newer title edit",
    pending_write: null,
  });
  expect(prepare.mock.calls.map(([request]) => request.expected_revision)).toEqual([1, 2]);
  expect(commit.mock.calls.map(([request]) => request.expected_revision)).toEqual([2, 3]);
});

it("blocks a duplicate create after an unknown create outcome until recovery refresh", async () => {
  localStorage.setItem(`dmb:world-plan-local-draft:v2:${worldId}`, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Plan",
    markdown: "# Plan\n",
    revision: null,
  }));
  const create = vi.spyOn(liveApi, "createWorldOwnedPlan").mockRejectedValue(new Error("network lost"));
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
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
  const inventory = vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [],
  });
  window.history.replaceState({}, "", `/plan?world=${worldId}`);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await screen.findByText(/creation response was uncertain/);
  expect(screen.getByRole("button", { name: "Save Plan" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Refresh Saved Plans" }));
  await waitFor(() => expect(inventory).toHaveBeenCalledTimes(2));
  expect(create).toHaveBeenCalledTimes(1);
});

it("quarantines lost-create text until explicit Plan binding, then saves and reopens without another create", async () => {
  const documentId = "created-but-unacknowledged";
  const record = worldPlanRecord(documentId, worldId, 1);
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  localStorage.setItem(key, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Plan",
    markdown: "# Plan\n",
    revision: null,
  }));
  const create = vi.spyOn(liveApi, "createWorldOwnedPlan").mockRejectedValue(new Error("response lost after server create"));
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
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
  const inventory = vi.spyOn(liveApi, "listWorldOwnedPlans")
    .mockResolvedValueOnce({ schema_version: "dmb_workspace_document_registry_v2", scope_mode: "world", world_id: worldId, records: [] })
    .mockResolvedValue({ schema_version: "dmb_workspace_document_registry_v2", scope_mode: "world", world_id: worldId, records: [record] });
  let snapshotCalls = 0;
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async () => {
    snapshotCalls += 1;
    const committed = snapshotCalls > 1;
    const revision = committed ? 5 : 1;
    return {
      schema_version: "dmb_workspace_document_snapshot_v2",
      record: { ...record, revision },
      markdown: committed ? "# Plan\n" : "",
      content_sha256: "a".repeat(64),
      file_fingerprint: "postgres",
      file_exists: committed,
      loaded_revision: revision,
    };
  });
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockResolvedValue(record);
  vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Plan",
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: request.expected_revision + 1,
    file_exists: false,
    writer_ok: true,
    writer_confirm_token: `recovered-draft-token-${request.expected_revision + 1}`,
    warnings: [],
    diagnostics: [],
  }));
  let resolveFirstCommit!: (value: Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>) => void;
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite")
    .mockImplementationOnce(() => new Promise((resolve) => { resolveFirstCommit = resolve; }))
    .mockResolvedValueOnce({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Plan",
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 5,
    committed_revision: 2,
    committed_record: { ...record, revision: 5, content_status: "committed" },
    normalized_content_sha256: "a".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  });
  window.history.replaceState({}, "", `/plan?world=${worldId}`);
  const page = render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await screen.findByText(/creation response was uncertain/);
  expect(JSON.parse(localStorage.getItem(key) ?? "null").uncertain_create_draft.markdown).toBe("# Plan\n");

  fireEvent.click(screen.getByRole("button", { name: "Refresh Saved Plans" }));
  await screen.findByRole("option", { name: "Plan" });
  fireEvent.change(screen.getByLabelText("Saved Plans"), { target: { value: documentId } });
  const restoreButton = await screen.findByRole("button", { name: "Restore recovered draft into this Plan" });
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    document_id: documentId,
    markdown: "",
    uncertain_create_draft: { markdown: "# Plan\n", bound_document_id: null },
  });
  fireEvent.click(restoreButton);
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    document_id: documentId,
    markdown: "# Plan\n",
    uncertain_create_draft: { markdown: "# Plan\n", bound_document_id: documentId },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(commit).toHaveBeenCalledTimes(1));
  fireEvent.change(screen.getByLabelText("Plan title"), { target: { value: "Edited during commit" } });
  const newerRecovery = JSON.parse(localStorage.getItem(key) ?? "null").uncertain_create_draft;
  expect(newerRecovery).toMatchObject({
    bound_document_id: documentId,
    title: "Edited during commit",
    markdown: "# Plan\n",
  });
  const firstReceipt = {
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Plan",
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 3,
    committed_revision: 1,
    committed_record: { ...record, revision: 3, content_status: "committed" },
    normalized_content_sha256: "a".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  } satisfies Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>;
  resolveFirstCommit(firstReceipt);
  await screen.findByText("Saved to this World.");
  expect(create).toHaveBeenCalledTimes(1);
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    document_id: documentId,
    markdown: "# Plan\n",
    uncertain_create_draft: { title: "Edited during commit", bound_document_id: documentId },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(commit).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(JSON.parse(localStorage.getItem(key) ?? "null").uncertain_create_draft).toBeNull());

  page.unmount();
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByTestId("world-owned-plan-editor").textContent).toContain("Plan"));
  expect(create).toHaveBeenCalledTimes(1);
});

it("preserves a quarantined draft when opening an unrelated existing Plan", async () => {
  const unrelatedId = "unrelated-saved-plan";
  const unrelated = worldPlanRecord(unrelatedId, worldId, 4);
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  localStorage.setItem(key, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Recovered draft",
    markdown: "# Keep these notes\n",
    revision: null,
  }));
  const create = vi.spyOn(liveApi, "createWorldOwnedPlan").mockRejectedValue(new Error("response lost"));
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks-cons-demo-markdown", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [unrelated],
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record: unrelated,
    markdown: "# Other Plan\n",
    content_sha256: "b".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 4,
  });
  vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: unrelatedId,
    title: "Other Plan",
    target_relpath: unrelated.target_relpath!,
    target_display_path: unrelated.target_relpath!,
    registry_revision: 5,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "unrelated-save-token",
    warnings: [],
    diagnostics: [],
  });
  vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: unrelatedId,
    title: "Other Plan",
    target_relpath: unrelated.target_relpath!,
    target_display_path: unrelated.target_relpath!,
    registry_revision: 6,
    committed_revision: 2,
    committed_record: { ...unrelated, revision: 6, content_status: "committed" },
    normalized_content_sha256: "c".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  });
  window.history.replaceState({}, "", `/plan?world=${worldId}`);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await screen.findByText(/creation response was uncertain/);
  const pendingRecovery = JSON.parse(localStorage.getItem(key) ?? "null");
  pendingRecovery.uncertain_create_draft.bound_document_id = "recovery-plan-a";
  localStorage.setItem(key, JSON.stringify(pendingRecovery));
  fireEvent.change(screen.getByLabelText("Saved Plans"), { target: { value: unrelatedId } });
  await screen.findByRole("button", { name: "Restore recovered draft into this Plan" });
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    document_id: unrelatedId,
    markdown: "# Other Plan\n",
    uncertain_create_draft: { markdown: "# Keep these notes\n", bound_document_id: "recovery-plan-a" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await screen.findByText("Saved to this World.");
  expect(create).toHaveBeenCalledTimes(1);
  expect(JSON.parse(localStorage.getItem(key) ?? "null").uncertain_create_draft).toMatchObject({
    markdown: "# Keep these notes\n",
    bound_document_id: "recovery-plan-a",
  });
});

it("keeps an unbound recovery through a reconciled commit for another Plan", async () => {
  const documentId = "ordinary-plan-b";
  const record = worldPlanRecord(documentId, worldId, 2);
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  localStorage.setItem(key, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Other Plan",
    markdown: "# Other Plan\n",
    revision: 2,
    edit_generation: 5,
    pending_write: {
      phase: "commit",
      base_revision: 1,
      prepared_revision: 2,
      base_markdown: "# Previous\n",
      markdown: "# Other Plan\n",
      edit_generation: 5,
    },
    uncertain_create_draft: {
      title: "Recovered notes",
      markdown: "# Keep these notes\n",
      edit_generation: 3,
      bound_document_id: null,
    },
  }));
  const create = vi.spyOn(liveApi, "createWorldOwnedPlan");
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockResolvedValue(record);
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks-cons-demo-markdown", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [record],
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record,
    markdown: "# Other Plan\n",
    content_sha256: "a".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 2,
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision").mockResolvedValue({
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    kind: "plan",
    campaign_id: null,
    title: "Other Plan",
    status: "active",
    object_revision: 2,
    work_revision_id: "revision-b2",
    revision_n: 2,
    markdown: "# Other Plan\n",
    content_sha256: "a".repeat(64),
    has_divergent_working_copy: false,
    target_relpath: record.target_relpath,
  });
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await screen.findByText("Saved to this World.");
  expect(create).not.toHaveBeenCalled();
  expect(liveApi.getWorldOwnedPlanCommittedRevision).toHaveBeenCalledWith(documentId);
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    pending_write: null,
    uncertain_create_draft: {
      markdown: "# Keep these notes\n",
      bound_document_id: null,
    },
  });
});

it("does not bind an unbound recovery to the empty-ID blank Plan while editing it", async () => {
  const documentId = "saved-plan-for-blank-transition";
  const record = worldPlanRecord(documentId, worldId, 4);
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  localStorage.setItem(key, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Saved Plan",
    markdown: "# Saved Plan\n",
    revision: 4,
    edit_generation: 2,
    create_uncertain: false,
    uncertain_create_draft: {
      title: "Recovered notes",
      markdown: "# Keep these notes\n",
      edit_generation: 1,
      bound_document_id: null,
    },
  }));
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockResolvedValue(record);
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks-cons-demo-markdown", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [record],
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record,
    markdown: "# Saved Plan\n",
    content_sha256: "a".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 4,
  });
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "New blank Plan" }));
  fireEvent.change(screen.getByLabelText("Plan title"), { target: { value: "New blank edit" } });
  expect(JSON.parse(localStorage.getItem(key) ?? "null")).toMatchObject({
    document_id: null,
    title: "New blank edit",
    uncertain_create_draft: {
      title: "Recovered notes",
      markdown: "# Keep these notes\n",
      bound_document_id: null,
    },
  });
  expect(screen.getByRole("button", { name: "Save Plan" })).toBeDisabled();
});
