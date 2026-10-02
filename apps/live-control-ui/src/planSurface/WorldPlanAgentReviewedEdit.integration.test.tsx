import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { StrictMode, type ReactNode } from "react";
import { webcrypto } from "node:crypto";
import { afterEach, beforeAll, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { WorldOwnedPlanRecordV2, WorldPlanDocumentEditProposalRequest, WorldPlanDocumentEditProposalResponse } from "../api/types";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { AgentInteractionChrome } from "../agentInteraction/AgentInteractionChrome";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { activeThreadStorageKey, threadIndexStorageKey, threadStorageKey } from "../agentInteraction/agentInteractionStorage";
import { PlanSurfacePage } from "./PlanSurfacePage";

const capturedChrome = vi.hoisted(() => ({ editorTools: null as unknown }));

vi.mock("../chrome/AppChrome", async () => {
  const { SurfaceContextHost, SurfaceContextProvider } = await import("../surfaceInteraction/contextHost");
  return {
    AppChrome: ({ children, editorTools }: { children: ReactNode; editorTools?: unknown }) => {
      capturedChrome.editorTools = editorTools;
      const tools = editorTools as { tools?: { sections?: Array<{ id: string; actions?: Array<{ label: string; onClick: () => void; disabled?: boolean }> }> } } | null;
      return (
        <SurfaceContextProvider>
          <SurfaceContextHost />
          {tools?.tools?.sections?.flatMap((section) => section.actions ?? []).map((action) => (
            <button key={action.label} type="button" onClick={action.onClick} disabled={action.disabled}>{action.label}</button>
          ))}
          {children}
        </SurfaceContextProvider>
      );
    },
  };
});

vi.mock("./PlanSurfaceShell", () => ({
  PlanSurfaceShell: () => null,
}));

const worldId = "world-reviewed-edit-integration";
const documentId = "saved-world-plan-reviewed-edit";
const initialMarkdown = "# Plan\n\nThe keeper waits beneath the black arch.\n";
const liveApplyScenarios = [
  [
    "plain prose",
    "Opening image: three lantern flashes ripple across the eastern ridge. The scouts have returned, but no one will explain why they were silent.",
    "A lone watcher keeps vigil above the marsh.",
    "A lone watcher keeps vigil above the marsh.",
  ],
  [
    "canonical READ-ALOUD callout",
    "Opening image: three lantern flashes ripple across the eastern ridge. The scouts have returned, but no one will explain why they were silent.",
    "> [!READ-ALOUD]\n> Three lantern flashes ripple across the eastern ridge. The scouts have returned, but no one will explain their silence. A cold wind threads through the camp, sharp against your skin.",
    "cold wind threads through the camp",
  ],
] as const;
let savedMarkdown = initialMarkdown;
let savedRevision = 7;
let savedDigest = "b".repeat(64);

function planRecord(): WorldOwnedPlanRecordV2 {
  return {
    schema_version: "dmb_world_owned_plan_record_v2",
    scope_mode: "world",
    document_id: documentId,
    title: "Integration Plan",
    campaign_id: null,
    world_id: worldId,
    target_session: null,
    kind: "plan",
    target_relpath: `out/workspace/plan/${documentId}.md`,
    status: "active",
    content_status: "committed",
    revision: savedRevision,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };
}

function managedContext() {
  return {
    schema_version: "dmb_managed_world_plan_context_v2" as const,
    scope_mode: "world" as const,
    world_id: worldId,
    campaign_id: null,
    session: null,
    authoritative: false as const,
    generated_at: "2026-01-01T00:00:00Z",
    derived_from: ["managed_world_container"],
    timeline: [] as [],
  };
}

function IntegrationPage() {
  const selected = useSelectedWorld();
  if (selected.kind !== "managed") return null;
  return (
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <PlanSurfacePage />
        <ThreadSwitchControl />
        <AgentInteractionChrome />
      </AskPluginSlotProvider>
    </AgentInteractionProvider>
  );
}

function ThreadSwitchControl() {
  const agent = useAgentInteraction();
  return <button type="button" onClick={() => agent.createThread("Switched during Apply")}>Switch Agent thread</button>;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function setupWorldApi() {
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext());
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{
      schema_version: "dmb_world_container_record_v1",
      world_id: worldId,
      name: "Integration World",
      source_root_relpath: "corpus/integration-world",
      created_at: "2026-01-01T00:00:00Z",
    }],
  });
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockImplementation(async () => planRecord());
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockImplementation(async () => ({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [planRecord()],
  }));
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async () => ({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record: planRecord(),
    markdown: savedMarkdown,
    content_sha256: savedDigest,
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: savedRevision,
  }));
}

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
  capturedChrome.editorTools = null;
  savedMarkdown = initialMarkdown;
  savedRevision = 7;
  savedDigest = "b".repeat(64);
});

it.each(liveApplyScenarios)("composes, reviews, applies, saves, and reloads a live %s edit on the mounted editor", async (_label, sourceMarkdown, replacementMarkdown, expectedAppliedText) => {
  savedMarkdown = sourceMarkdown;
  setupWorldApi();
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v1",
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: request.target_kind,
    selected_text_sha256: await sha256Hex(request.selected_text),
    replacement_markdown: replacementMarkdown,
    summary: "Add a lantern-lit opening beat.",
    assumptions: ["The lantern is already present at the location."],
    model: "gpt-6-luna",
    model_observed: true,
    model_latency_ms: 1,
    wall_latency_ms: 1,
    usage: null,
  }));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: documentId,
    title: "Integration Plan",
    target_relpath: `out/workspace/plan/${documentId}.md`,
    target_display_path: `out/workspace/plan/${documentId}.md`,
    registry_revision: 8,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "integration-save-token",
    warnings: [],
    diagnostics: [],
  });
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    savedMarkdown = request.markdown;
    savedRevision = 8;
    savedDigest = "c".repeat(64);
    const committedRecord = { ...planRecord(), revision: savedRevision };
    return {
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: documentId,
      title: "Integration Plan",
      target_relpath: `out/workspace/plan/${documentId}.md`,
      target_display_path: `out/workspace/plan/${documentId}.md`,
      registry_revision: savedRevision,
      committed_revision: savedRevision,
      committed_record: committedRecord,
      normalized_content_sha256: savedDigest,
      writer_ok: true,
      writer_phase: "commit",
      diagnostics: [],
    };
  });

  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(editorSurface).toHaveTextContent(sourceMarkdown));
  const proseMirror = editorSurface.querySelector(".ProseMirror") as HTMLElement;
  const textNode = proseMirror.querySelector("p")?.firstChild as Text;
  expect(textNode?.textContent).toBe(sourceMarkdown);
  const range = document.createRange();
  const firstSentenceEnd = sourceMarkdown.indexOf(".") + 1;
  range.setStart(textNode, firstSentenceEnd);
  range.collapse(true);
  const domSelection = window.getSelection();
  domSelection?.removeAllRanges();
  domSelection?.addRange(range);
  fireEvent.mouseUp(proseMirror);
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByRole("region", { name: "Saved World Plan conversation" })).toBeInTheDocument();
  expect(screen.getByText(/Ask sends this Plan’s exact committed text and your question to the configured model/)).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("What should DungeonBuddy change?"), {
    target: { value: "Add a warm light source to the opening." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Compose proposal" }));
  expect(await screen.findByRole("region", { name: "Review proposed Plan edit" })).toBeInTheDocument();
  const request = proposal.mock.calls[0][0];
  expect(request).toMatchObject({
    document_id: documentId,
    world_id: worldId,
    base_revision: 7,
    base_content_sha256: "b".repeat(64),
    instruction: "Add a warm light source to the opening.",
  });
  expect(request.draft_markdown.trimEnd()).toBe(sourceMarkdown);
  expect(request.target_kind).toBe("insert_at_caret");
  expect(request.selected_text).toBe("");
  expect(JSON.stringify(request)).not.toContain("session");
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(sourceMarkdown);
  expect(screen.getByRole("region", { name: "Review proposed Plan edit" })).toHaveTextContent(expectedAppliedText);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Apply to mounted draft" }));
  await waitFor(() => {
    expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(sourceMarkdown);
    expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(expectedAppliedText);
  });
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  const namespace = `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
  const threadId = localStorage.getItem(activeThreadStorageKey(namespace, "plan", documentId));
  expect(threadId).toBeTruthy();
  const proposalTurn = JSON.parse(localStorage.getItem(threadStorageKey(namespace, threadId!)) ?? "null").turns[0];
  expect(proposalTurn).toMatchObject({
    backend: "plan_edit",
    planEdit: { applied: true, targetKind: "insert_at_caret" },
  });
  expect(proposalTurn.replacement_markdown).toBeUndefined();

  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(screen.getByText("Saved to this World.")).toBeInTheDocument());
  expect(commit).toHaveBeenCalledWith(expect.objectContaining({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    world_id: worldId,
    document_id: documentId,
    writer_confirm_token: "integration-save-token",
    markdown: expect.stringContaining(replacementMarkdown),
  }));

  view.unmount();
  window.history.replaceState({}, "", location);
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  expect(await screen.findByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(sourceMarkdown);
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(expectedAppliedText);
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByText("Plan proposal · Applied to the local draft")).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Apply to mounted draft" })).not.toBeInTheDocument();
});

it("drops a delayed proposal that completes after the mounted Plan conversation unmounts", async () => {
  setupWorldApi();
  let release!: (value: WorldPlanDocumentEditProposalResponse) => void;
  const pending = new Promise<WorldPlanDocumentEditProposalResponse>((resolve) => { release = resolve; });
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockReturnValue(pending);
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  expect(await screen.findByTestId("world-owned-plan-markdown-editor")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.change(await screen.findByLabelText("What should DungeonBuddy change?"), {
    target: { value: "Add a lantern." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Compose proposal" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  const request: WorldPlanDocumentEditProposalRequest = proposal.mock.calls[0][0];
  const namespace = `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;

  view.unmount();
  await act(async () => {
    release({
      schema_version: "dmb_world_plan_document_edit_proposal_v1",
      document_id: request.document_id,
      world_id: request.world_id,
      base_revision: request.base_revision,
      base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256,
      target_kind: request.target_kind,
      selected_text_sha256: await sha256Hex(request.selected_text),
      replacement_markdown: "A lantern glows.",
      summary: "Add a lantern.",
      assumptions: [],
      model: "gpt-6-luna",
      model_observed: true,
      model_latency_ms: 1,
      wall_latency_ms: 1,
      usage: null,
    });
    await pending;
  });

  expect(localStorage.getItem(activeThreadStorageKey(namespace, "plan", documentId))).toBeNull();
  expect(localStorage.getItem(threadIndexStorageKey(namespace, "plan", documentId))).toBeNull();
});

it("rejects a thread switch during deferred Apply without changing the mounted editor", async () => {
  setupWorldApi();
  vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v1",
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: request.target_kind,
    selected_text_sha256: await sha256Hex(request.selected_text),
    replacement_markdown: "A lantern glows under the arch.",
    summary: "Add a lantern-lit opening beat.",
    assumptions: [],
    model: "gpt-6-luna",
    model_observed: true,
    model_latency_ms: 1,
    wall_latency_ms: 1,
    usage: null,
  }));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.change(await screen.findByLabelText("What should DungeonBuddy change?"), {
    target: { value: "Add a lantern." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Compose proposal" }));
  expect(await screen.findByRole("region", { name: "Review proposed Plan edit" })).toBeInTheDocument();
  const editorTextBefore = editorSurface.textContent;

  const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const digest = vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
    await gate;
    return originalDigest(...args);
  });
  fireEvent.click(screen.getByRole("button", { name: "Apply to mounted draft" }));
  await waitFor(() => expect(digest).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole("button", { name: "Switch Agent thread" }));
  await waitFor(() => expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument());
  await act(async () => { release(); });

  expect(editorSurface.textContent).toBe(editorTextBefore);
  expect(editorSurface).not.toHaveTextContent("A lantern glows under the arch.");
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
});
