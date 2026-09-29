import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { useEffect } from "react";
import { afterEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { WorldOwnedPlanRecordV2 } from "../api/types";
import { AgentInteractionProvider, useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { SelectedWorldProvider } from "../selectedWorld/SelectedWorldContext";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { PeekRegionProvider } from "../surfaceInteraction/peekHost";
import type { SurfaceInteractionEditCommandContribution, SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { PlanSurfacePage } from "./PlanSurfacePage";

const worldId = "world/server-issued:opaque/a";
const documentId = "world-plan-doc/server-issued:opaque/1";
const storageKey = `dmb:world-plan-local-draft:v2:${worldId}`;
const secondWorldId = "world/server-issued:opaque/b";
const firstSavedDocumentId = "world-plan-doc/server-issued:opaque/a";
const secondSavedDocumentId = "world-plan-doc/server-issued:opaque/b";

function record(): WorldOwnedPlanRecordV2 {
  return {
    schema_version: "dmb_world_owned_plan_record_v2",
    scope_mode: "world",
    document_id: documentId,
    title: "Local Plan",
    campaign_id: null,
    world_id: worldId,
    target_session: null,
    kind: "plan",
    target_relpath: `out/workspace/plan/${documentId}.md`,
    status: "active",
    content_status: "committed",
    revision: 1,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function recordFor(world: string, document: string, title: string): WorldOwnedPlanRecordV2 {
  return {
    ...record(),
    document_id: document,
    title,
    world_id: world,
    target_relpath: `out/workspace/plan/${document}.md`,
  };
}

function PublicationProbe({ capture }: { capture?: (publication: SurfaceInteractionPublication | null) => void }) {
  const { surfaceInteractionPublication } = useAgentInteraction();
  useEffect(() => {
    capture?.(surfaceInteractionPublication);
  }, [capture, surfaceInteractionPublication]);
  return <output data-testid="surface-publication">{JSON.stringify(surfaceInteractionPublication)}</output>;
}

function MountedPlanHarness({
  locationSnapshot,
  capture,
}: {
  locationSnapshot: string;
  capture: (publication: SurfaceInteractionPublication | null) => void;
}) {
  return (
    <SurfaceContextProvider>
      <PeekRegionProvider>
        <AgentInteractionProvider>
          <SelectedWorldProvider locationSnapshot={locationSnapshot}>
            <PublicationProbe capture={capture} />
            <PlanSurfacePage />
          </SelectedWorldProvider>
        </AgentInteractionProvider>
      </PeekRegionProvider>
    </SurfaceContextProvider>
  );
}

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

it("publishes one matching World Plan inventory through the real AppChrome and EditHost", async () => {
  const oldDraft = {
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Local Plan",
    markdown: "# Local Plan\n\nA prepared encounter.\n",
    revision: null,
    edit_generation: 4,
    create_uncertain: false,
    uncertain_create_draft: {
      title: "Orphan notes",
      markdown: "# Keep separately\n",
      edit_generation: 3,
      bound_document_id: null,
    },
    pending_write: null,
  };
  localStorage.setItem(storageKey, JSON.stringify(oldDraft));
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
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [],
  });
  window.history.replaceState({}, "", `/plan?world=${encodeURIComponent(worldId)}`);
  render(
    <SurfaceContextProvider>
      <PeekRegionProvider>
        <AgentInteractionProvider>
          <SelectedWorldProvider locationSnapshot={`/plan?world=${encodeURIComponent(worldId)}`}>
            <PublicationProbe />
            <PlanSurfacePage />
          </SelectedWorldProvider>
        </AgentInteractionProvider>
      </PeekRegionProvider>
    </SurfaceContextProvider>,
  );

  const editHost = await screen.findByRole("complementary", { name: "Edit toolbar" });
  await screen.findByTestId("world-owned-plan-markdown-editor");
  const canvas = screen.getByTestId("world-owned-plan");
  await waitFor(() => expect(within(editHost).getByRole("button", { name: "Bold" })).toBeEnabled());
  expect(screen.getByRole("link", { name: "Index" })).toBeInTheDocument();
  expect(screen.getByTestId("world-plan-surface-context")).toBeInTheDocument();
  expect(within(editHost).getByLabelText("Plan title")).toHaveValue("Local Plan");
  expect(within(editHost).getByRole("button", { name: "Save Plan" })).toBeDisabled();
  expect(within(canvas).queryByRole("button", { name: "Bold" })).not.toBeInTheDocument();
  expect(within(canvas).queryByRole("button", { name: "Save Plan" })).not.toBeInTheDocument();
  expect(within(canvas).queryByLabelText("Plan title")).not.toBeInTheDocument();
  expect(within(canvas).getByRole("status", { name: "Recovered Plan draft" })).toBeInTheDocument();

  const publication = JSON.parse(screen.getByTestId("surface-publication").textContent ?? "null");
  const workObject = publication.canvas.workObject;
  expect(workObject).toMatchObject({
    kind: "world-plan-local-draft",
    id: expect.stringContaining(worldId),
  });
  const editCommands = publication.editCommands.filter((command: { target: { kind: string; id: string } }) =>
    command.target.kind === workObject.kind && command.target.id === workObject.id);
  expect(editCommands.length).toBeGreaterThan(0);
  expect(JSON.parse(publication.identity.instanceKey)).toEqual(["world-plan", workObject.kind, workObject.id]);
  const migrated = JSON.parse(localStorage.getItem(storageKey) ?? "null");
  expect(migrated.local_draft_id).toEqual(expect.any(String));
  expect(migrated).toMatchObject(oldDraft);
});

it("promotes the mounted EditHost inventory from its local token to the exact saved document", async () => {
  const capturedPublication: { current: SurfaceInteractionPublication | null } = { current: null };
  const capturePublication = (publication: SurfaceInteractionPublication | null) => {
    capturedPublication.current = publication;
  };
  let retainedReadAloud: SurfaceInteractionEditCommandContribution | undefined;
  localStorage.setItem(storageKey, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    local_draft_id: "local-draft-token",
    title: "Local Plan",
    markdown: "# Local Plan\n\nReady to save.\n",
    revision: null,
  }));
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
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [],
  });
  vi.spyOn(liveApi, "createWorldOwnedPlan").mockResolvedValue(record());
  vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Local Plan",
    target_relpath: record().target_relpath!,
    target_display_path: record().target_relpath!,
    registry_revision: 2,
    file_exists: false,
    writer_ok: true,
    writer_confirm_token: "prepared-token",
    warnings: [],
    diagnostics: [],
  });
  vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Local Plan",
    target_relpath: record().target_relpath!,
    target_display_path: record().target_relpath!,
    registry_revision: 3,
    committed_revision: 3,
    committed_record: { ...record(), revision: 3 },
    normalized_content_sha256: "a".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  });
  window.history.replaceState({}, "", `/plan?world=${encodeURIComponent(worldId)}`);
  render(
    <SurfaceContextProvider>
      <PeekRegionProvider>
        <AgentInteractionProvider>
          <SelectedWorldProvider locationSnapshot={`/plan?world=${encodeURIComponent(worldId)}`}>
            <PublicationProbe capture={capturePublication} />
            <PlanSurfacePage />
          </SelectedWorldProvider>
        </AgentInteractionProvider>
      </PeekRegionProvider>
    </SurfaceContextProvider>,
  );

  const save = await screen.findByRole("button", { name: "Save Plan" });
  await waitFor(() => expect(save).toBeEnabled());
  const originalEditor = screen.getByTestId("world-owned-plan-markdown-editor").querySelector('[contenteditable="true"]');
  expect(originalEditor).not.toBeNull();
  await waitFor(() => {
    retainedReadAloud = capturedPublication.current?.editCommands.find((command) => command.label === "Read aloud");
    expect(retainedReadAloud).toBeDefined();
  });
  expect(screen.getByText("A working space for this World. Your draft is local until you save it.")).toBeInTheDocument();
  const localPublication = JSON.parse(screen.getByTestId("surface-publication").textContent ?? "null");
  expect(localPublication.canvas.workObject).toEqual({
    kind: "world-plan-local-draft",
    id: JSON.stringify(["world-plan-local-draft", worldId, "local-draft-token"]),
  });

  fireEvent.click(save);
  await screen.findByText("Saved to this World.");
  expect(screen.getByText("A saved Plan for this World. Any new edits stay local until you save them.")).toBeInTheDocument();
  await waitFor(() => {
    const publication = JSON.parse(screen.getByTestId("surface-publication").textContent ?? "null");
    expect(publication.canvas.workObject).toEqual({
      kind: "world-plan-document",
      id: JSON.stringify(["world-plan-document", worldId, documentId]),
    });
    expect(JSON.parse(publication.identity.instanceKey)).toEqual([
      "world-plan", "world-plan-document", JSON.stringify(["world-plan-document", worldId, documentId]),
    ]);
    expect(publication.editCommands.some((command: { target: { kind: string; id: string } }) =>
      command.target.kind === "world-plan-document"
      && command.target.id === JSON.stringify(["world-plan-document", worldId, documentId]))).toBe(true);
  });
  const replacementEditor = screen.getByTestId("world-owned-plan-markdown-editor").querySelector('[contenteditable="true"]');
  expect(replacementEditor).not.toBeNull();
  expect(replacementEditor).not.toBe(originalEditor);
  const focusAnchor = screen.getByRole("button", { name: "Save Plan" });
  focusAnchor.focus();
  const replacementMarkup = replacementEditor!.innerHTML;
  await act(async () => {
    await retainedReadAloud!.invoke();
  });
  expect(replacementEditor!.innerHTML).toBe(replacementMarkup);
  expect(document.activeElement).toBe(focusAnchor);
  expect(JSON.parse(localStorage.getItem(storageKey) ?? "null").local_draft_id).toBeNull();
});

it("fences held EditHost commands across document, blank, World, and unmount transitions", async () => {
  const capturedPublication: { current: SurfaceInteractionPublication | null } = { current: null };
  const capturePublication = (publication: SurfaceInteractionPublication | null) => {
    capturedPublication.current = publication;
  };
  const firstRecord = recordFor(worldId, firstSavedDocumentId, "First saved Plan");
  const secondRecord = recordFor(worldId, secondSavedDocumentId, "Second saved Plan");
  const secondWorldRecord = recordFor(secondWorldId, "world-plan-doc/server-issued:b1", "Other World Plan");
  const recordsById = new Map([
    [firstRecord.document_id, firstRecord],
    [secondRecord.document_id, secondRecord],
    [secondWorldRecord.document_id, secondWorldRecord],
  ]);
  const worlds = [
    { schema_version: "dmb_world_container_record_v1" as const, world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks", created_at: "2026-01-01T00:00:00Z" },
    { schema_version: "dmb_world_container_record_v1" as const, world_id: secondWorldId, name: "Second World", source_root_relpath: "worlds/second", created_at: "2026-01-01T00:00:00Z" },
  ];
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockImplementation(async (requestedWorldId) => ({
    schema_version: "dmb_managed_world_plan_context_v2",
    scope_mode: "world",
    world_id: requestedWorldId,
    campaign_id: null,
    session: null,
    authoritative: false,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [],
  }));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: worlds,
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockImplementation(async (requestedWorldId) => ({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: requestedWorldId,
    records: requestedWorldId === worldId ? [firstRecord, secondRecord] : [secondWorldRecord],
  }));
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async (requestedDocumentId) => {
    const requestedRecord = recordsById.get(requestedDocumentId);
    if (!requestedRecord) throw new Error(`Unknown test Plan ${requestedDocumentId}`);
    return {
      schema_version: "dmb_workspace_document_snapshot_v2",
      record: requestedRecord,
      markdown: `# ${requestedRecord.title}\n\nSaved body for ${requestedRecord.title}.\n`,
      content_sha256: "b".repeat(64),
      file_fingerprint: "postgres",
      file_exists: true,
      loaded_revision: requestedRecord.revision,
    };
  });

  const locationFor = (world: string) => `/plan?world=${encodeURIComponent(world)}`;
  const firstLocation = locationFor(worldId);
  window.history.replaceState({}, "", firstLocation);
  const view = render(
    <MountedPlanHarness locationSnapshot={firstLocation} capture={capturePublication} />,
  );
  await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(capturedPublication.current?.editCommands.some((command) => command.label === "Read aloud")).toBe(true));

  const activeEditor = () => {
    const editor = screen.getByTestId("world-owned-plan-markdown-editor").querySelector<HTMLElement>('[contenteditable="true"]');
    expect(editor).not.toBeNull();
    return editor!;
  };
  const retainedCommand = () => {
    const publication = capturedPublication.current;
    const command = publication?.editCommands.find((candidate) => candidate.label === "Read aloud");
    expect(command).toBeDefined();
    return command!;
  };
  const assertHeldCommandIsInert = async (
    command: SurfaceInteractionEditCommandContribution,
    editor: HTMLElement,
  ) => {
    const focusAnchor = screen.getByRole("combobox", { name: "Plan document" });
    focusAnchor.focus();
    const markup = editor.innerHTML;
    await act(async () => {
      await command.invoke();
    });
    expect(editor.innerHTML).toBe(markup);
    expect(document.activeElement).toBe(focusAnchor);
  };

  const localCommand = retainedCommand();
  const planSelector = screen.getByRole("combobox", { name: "Plan document" });
  fireEvent.change(planSelector, { target: { value: firstSavedDocumentId } });
  await waitFor(() => expect(new URL(window.location.href).searchParams.get("documentId")).toBe(firstSavedDocumentId));
  await screen.findByText("Saved body for First saved Plan.");
  await waitFor(() => expect(capturedPublication.current?.canvas.workObject).toMatchObject({
    kind: "world-plan-document",
    id: JSON.stringify(["world-plan-document", worldId, firstSavedDocumentId]),
  }));
  const firstSavedEditor = activeEditor();
  expect(firstSavedEditor).not.toBeNull();
  await assertHeldCommandIsInert(localCommand, firstSavedEditor);

  const firstDocumentCommand = retainedCommand();
  fireEvent.change(screen.getByRole("combobox", { name: "Plan document" }), {
    target: { value: secondSavedDocumentId },
  });
  await waitFor(() => expect(new URL(window.location.href).searchParams.get("documentId")).toBe(secondSavedDocumentId));
  await screen.findByText("Saved body for Second saved Plan.");
  await waitFor(() => expect(capturedPublication.current?.canvas.workObject).toMatchObject({
    kind: "world-plan-document",
    id: JSON.stringify(["world-plan-document", worldId, secondSavedDocumentId]),
  }));
  const secondSavedEditor = activeEditor();
  expect(secondSavedEditor).not.toBe(firstSavedEditor);
  await assertHeldCommandIsInert(firstDocumentCommand, secondSavedEditor);

  const secondDocumentCommand = retainedCommand();
  fireEvent.click(screen.getByRole("button", { name: "New blank Plan" }));
  await waitFor(() => expect(capturedPublication.current?.canvas.workObject.kind).toBe("world-plan-local-draft"));
  const newBlankEditor = activeEditor();
  expect(newBlankEditor).not.toBe(secondSavedEditor);
  await assertHeldCommandIsInert(secondDocumentCommand, newBlankEditor);

  const blankCommand = retainedCommand();
  const secondLocation = locationFor(secondWorldId);
  window.history.replaceState({}, "", secondLocation);
  view.rerender(<MountedPlanHarness locationSnapshot={secondLocation} capture={capturePublication} />);
  await screen.findByTestId("world-owned-plan-markdown-editor");
  await screen.findByRole("option", { name: "Other World Plan" });
  fireEvent.change(screen.getByRole("combobox", { name: "Plan document" }), {
    target: { value: secondWorldRecord.document_id },
  });
  await waitFor(() => expect(new URL(window.location.href).searchParams.get("documentId")).toBe(secondWorldRecord.document_id));
  await screen.findByText("Saved body for Other World Plan.");
  await waitFor(() => expect(capturedPublication.current?.canvas.workObject).toMatchObject({
    kind: "world-plan-document",
    id: JSON.stringify(["world-plan-document", secondWorldId, secondWorldRecord.document_id]),
  }));
  const secondWorldEditor = activeEditor();
  expect(secondWorldEditor).not.toBe(newBlankEditor);
  await assertHeldCommandIsInert(blankCommand, secondWorldEditor);

  const unmountedCommand = retainedCommand();
  const finalEditor = secondWorldEditor;
  const externalFocusAnchor = document.createElement("button");
  document.body.append(externalFocusAnchor);
  externalFocusAnchor.focus();
  view.unmount();
  expect(finalEditor.isConnected).toBe(false);
  await act(async () => {
    await unmountedCommand.invoke();
  });
  expect(document.activeElement).toBe(externalFocusAnchor);
  externalFocusAnchor.remove();
});

it("assigns a fresh blank World a stable local identity on its first edit and reload", async () => {
  const locationSnapshot = `/plan?world=${encodeURIComponent(worldId)}`;
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
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [],
  });
  window.history.replaceState({}, "", locationSnapshot);
  const mount = () => render(
    <SurfaceContextProvider>
      <PeekRegionProvider>
        <AgentInteractionProvider>
          <SelectedWorldProvider locationSnapshot={locationSnapshot}>
            <PublicationProbe />
            <PlanSurfacePage />
          </SelectedWorldProvider>
        </AgentInteractionProvider>
      </PeekRegionProvider>
    </SurfaceContextProvider>,
  );

  const first = mount();
  await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByRole("button", { name: "Read aloud" })).toBeEnabled());
  const publication = () => JSON.parse(screen.getByTestId("surface-publication").textContent ?? "null");
  await waitFor(() => expect(publication().canvas.workObject.kind).toBe("world-plan-local-draft"));
  const firstTarget = publication().canvas.workObject;
  const firstTuple = JSON.parse(firstTarget.id);
  expect(firstTuple).toEqual(["world-plan-local-draft", worldId, expect.any(String)]);
  expect(firstTuple[2]).not.toBe("pending-local-draft");

  fireEvent.click(screen.getByRole("button", { name: "Read aloud" }));
  await waitFor(() => {
    expect(JSON.parse(localStorage.getItem(storageKey) ?? "null").local_draft_id).toBe(firstTuple[2]);
  });
  first.unmount();

  mount();
  await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => {
    expect(publication().canvas.workObject).toEqual(firstTarget);
    expect(JSON.parse(localStorage.getItem(storageKey) ?? "null").local_draft_id).toBe(firstTuple[2]);
  });
});
