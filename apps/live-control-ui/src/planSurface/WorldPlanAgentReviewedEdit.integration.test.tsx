import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { StrictMode, type ReactNode } from "react";
import { webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeAll, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import type { WorldOwnedPlanRecordV2, WorldPlanActionProjectionPage, WorldPlanDocumentEditProposalRequest, WorldPlanDocumentEditProposalResponse } from "../api/types";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { AgentInteractionChrome } from "../agentInteraction/AgentInteractionChrome";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { activeThreadStorageKey, threadIndexStorageKey, threadStorageKey } from "../agentInteraction/agentInteractionStorage";
import { PlanSurfacePage } from "./PlanSurfacePage";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";

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
const repositoryRoot = resolve(process.cwd(), "../..");
const session29Markdown = readFileSync(resolve(
  repositoryRoot,
  "corpus",
  "eldyrwild-markdown",
  "Longmont Campaign",
  "Campaign 2",
  "Session Prep",
  "Session 29 - Buddy Plan.md",
), "utf8");

function session29V2Markers(markdown: string): string[] {
  return Array.from(markdown.matchAll(/<!--\s*dmb-playable-element:v2[^\r\n]*?-->/g), (match) => match[0]);
}

function session29NodeLinks(markdown: string): string[] {
  return Array.from(markdown.matchAll(/\[[^\]]*\]\(dmb-node:[^)]+\)/g), (match) => match[0]);
}

function normalizeThematicBreakSpacing(markdown: string): string {
  return markdown.replace(/\n+(?=---(?:\r?\n|$))/g, "\n");
}

function selectedMarkdownSection(markdown: string, headingText: string): { fragment: string; replace: (replacement: string) => string } {
  const lines = markdown.split("\n");
  const offsets: number[] = [];
  const headings: Array<{ line: number; offset: number; level: number; text: string }> = [];
  let offset = 0;
  for (let line = 0; line < lines.length; line += 1) {
    offsets.push(offset);
    const match = /^(#{1,6})\s+(.+?)\s*$/.exec(lines[line]);
    if (match) headings.push({ line, offset, level: match[1].length, text: match[2] });
    offset += lines[line].length + 1;
  }
  const selected = headings.find((heading) => heading.text === headingText);
  if (!selected) throw new Error(`Session 29 heading not found: ${headingText}`);
  const nextPeer = headings.find((heading) => heading.offset > selected.offset && heading.level <= selected.level);
  const markerBefore = (line: number) => line > 0 && /<!--\s*dmb-playable-element:v2\b/.test(lines[line - 1]);
  const startLine = markerBefore(selected.line) ? selected.line - 1 : selected.line;
  let endLine = nextPeer ? (markerBefore(nextPeer.line) ? nextPeer.line - 1 : nextPeer.line) : lines.length;
  if (nextPeer) {
    while (endLine > startLine && !lines[endLine - 1]!.trim()) endLine -= 1;
    if (endLine > startLine && /^---+$/.test(lines[endLine - 1]!.trim())) {
      endLine -= 1;
    }
  }
  const start = offsets[startLine];
  const end = nextPeer ? offsets[endLine] : markdown.length;
  const fragment = markdown.slice(start, end);

  return {
    fragment,
    replace(replacement) {
      return `${markdown.slice(0, start)}${replacement}${markdown.slice(end)}`;
    },
  };
}

function reviseFirstSectionProse(fragment: string): string {
  const lines = fragment.split("\n");
  const headingLine = lines.findIndex((line) => /^#{1,6}\s+/.test(line));
  const proseLine = lines.findIndex((line, index) => index > headingLine
    && line.trim()
    && !/^#{1,6}\s+/.test(line)
    && !/^<!--/.test(line.trim())
    && !/^>/.test(line.trim())
    && !/^---+$/.test(line.trim()));
  if (proseLine < 0) throw new Error("Session 29 target section has no prose to revise.");
  lines[proseLine] = `${lines[proseLine]} [reviewed section detail]`;
  return lines.join("\n");
}

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
  [
    "plain root blockquote",
    "Opening image: three lantern flashes ripple across the eastern ridge.\n\n> A root-level witness keeps watch from the broken wall.\n",
    "A lone watcher keeps vigil above the marsh.",
    "A lone watcher keeps vigil above the marsh.",
    "Opening image: three lantern flashes ripple across the eastern ridge.A root-level witness keeps watch from the broken wall.",
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
  vi.spyOn(liveApi, "getWorldPlanDocumentEditActions").mockResolvedValue({
    schema_version: "dmb_world_plan_action_projection_v1",
    basis: {
      world_id: worldId,
      document_id: documentId,
      object_revision: savedRevision,
      work_revision_id: "00000000-0000-4000-8000-000000000010",
      revision_n: 1,
      content_sha256: savedDigest,
    },
    actions: [],
  });
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

it.each(liveApplyScenarios)("composes, reviews, applies, saves, and reloads a live %s edit on the mounted editor", async (_label, sourceMarkdown, replacementMarkdown, expectedAppliedText, expectedVisibleSource = sourceMarkdown) => {
  savedMarkdown = sourceMarkdown;
  setupWorldApi();
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v1",
    action_id: "00000000-0000-4000-8000-000000000001",
    idempotency_key: request.idempotency_key,
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
  await waitFor(() => expect(editorSurface).toHaveTextContent(expectedVisibleSource));
  const proseMirror = editorSurface.querySelector(".ProseMirror") as HTMLElement;
  const textNode = proseMirror.querySelector("p")?.firstChild as Text;
  expect(textNode?.textContent).toContain("Opening image:");
  const range = document.createRange();
  const firstSentenceEnd = (textNode?.textContent ?? "").indexOf(".") + 1;
  range.setStart(textNode, firstSentenceEnd);
  range.collapse(true);
  const domSelection = window.getSelection();
  domSelection?.removeAllRanges();
  domSelection?.addRange(range);
  fireEvent.mouseUp(proseMirror);
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByRole("region", { name: "Saved World Plan conversation" })).toBeInTheDocument();
  expect(screen.getByText(/Talk through the saved Plan, or choose Propose edit to request a change/)).toBeInTheDocument();

  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
    target: { value: "Add a warm light source to the opening." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await screen.findByRole("region", { name: "Review proposed Plan edit" }).catch(() => {
    const alerts = screen.queryAllByRole("alert").map((element) => element.textContent).filter(Boolean).join(" | ");
    throw new Error(`Section proposal was rejected. Alerts: ${alerts || "none"}`);
  });
  const request = proposal.mock.calls[0][0];
  expect(request).toMatchObject({
    document_id: documentId,
    world_id: worldId,
    base_revision: 7,
    base_content_sha256: "b".repeat(64),
    instruction: "Add a warm light source to the opening.",
  });
  if (_label === "plain root blockquote") {
    expect(request.draft_markdown).toContain("> A root-level witness keeps watch from the broken wall.");
  } else {
    expect(request.draft_markdown.trimEnd()).toBe(sourceMarkdown);
  }
  expect(request.target_kind).toBe("insert_at_caret");
  expect(request.selected_text).toBe("");
  expect(JSON.stringify(request)).not.toContain("session");
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(expectedVisibleSource);
  expect(screen.getByRole("region", { name: "Review proposed Plan edit" })).toHaveTextContent(expectedAppliedText);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => {
    expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(expectedVisibleSource);
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
  if (_label === "plain root blockquote") {
    expect(commit.mock.calls[0][0].markdown).toContain("> A root-level witness keeps watch from the broken wall.");
  }

  view.unmount();
  window.history.replaceState({}, "", location);
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  expect(await screen.findByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(expectedVisibleSource);
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(expectedAppliedText);
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByText("Local proposal · Applied to your draft")).toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Local Plan proposal activity" })).toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
});

const session29SectionCases = [
  {
    label: "parent Beat",
    heading: "The Hours They Bought",
    includedChild: "Mireward After the Attack",
    excludedPeer: "Sixteen People Still Sleeping",
  },
  {
    label: "scene",
    heading: "Mireward After the Attack",
    includedChild: "The town is damaged but functioning.",
    excludedPeer: "What Do You Do With the Time You Bought?",
  },
] as const;

it.each(session29SectionCases)("targets a Session 29 $label and keeps Apply within a safe round-trip boundary", async (sectionCase) => {
  savedMarkdown = session29Markdown;
  expect(session29V2Markers(session29Markdown)).toHaveLength(90);
  expect(session29NodeLinks(session29Markdown)).toHaveLength(72);
  setupWorldApi();
  let expectedAfterApply = "";
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => {
    const section = selectedMarkdownSection(request.draft_markdown, sectionCase.heading);
    const replacement = reviseFirstSectionProse(section.fragment);
    const canonicalReplacement = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(replacement).doc);
    expectedAfterApply = section.replace(canonicalReplacement);
    return {
      schema_version: "dmb_world_plan_document_edit_proposal_v1",
      action_id: "00000000-0000-4000-8000-000000000002",
      idempotency_key: request.idempotency_key,
      document_id: request.document_id,
      world_id: request.world_id,
      base_revision: request.base_revision,
      base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256,
      target_kind: request.target_kind,
      selected_text_sha256: await sha256Hex(request.selected_text),
      replacement_markdown: replacement,
      summary: `Revise ${sectionCase.heading}.`,
      assumptions: [],
      model: "gpt-6-luna",
      model_observed: true,
      model_latency_ms: 1,
      wall_latency_ms: 1,
      usage: null,
    };
  });
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
      committed_record: { ...planRecord(), revision: savedRevision },
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
  await waitFor(() => expect(editorSurface).toHaveTextContent("The Hours They Bought"));
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));

  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.click(screen.getByRole("button", { name: "Refresh sections" }));
  const sectionSelect = await screen.findByRole("combobox", { name: "Plan section (optional)" }) as HTMLSelectElement;
  await waitFor(() => expect(sectionSelect.options.length).toBeGreaterThan(1));
  const option = Array.from(sectionSelect.options).find((candidate) => candidate.textContent?.includes(sectionCase.heading));
  expect(option).toBeDefined();

  if (sectionCase.label === "parent Beat") {
    const beforeSelection = editorSurface.textContent;
    expect(option!.disabled).toBe(true);
    expect(option!.textContent).toContain("unavailable");
    fireEvent.change(sectionSelect, { target: { value: option!.value } });
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(
      "This heading section changes editor structure during Markdown round-trip",
    ));
    expect(sectionSelect.value).toBe("");
    expect(editorSurface.textContent).toBe(beforeSelection);
    expect(proposal).not.toHaveBeenCalled();
    expect(prepare).not.toHaveBeenCalled();
    expect(commit).not.toHaveBeenCalled();
    expect(savedMarkdown).toBe(session29Markdown);
    return;
  }

  expect(option!.disabled).toBe(false);
  fireEvent.change(sectionSelect, { target: { value: option!.value } });
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(`${option!.textContent} selected`));
  const beforeProposalText = editorSurface.textContent;
  expect(proposal).not.toHaveBeenCalled();
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
    target: { value: `Revise ${sectionCase.heading} with one reviewed detail.` },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1), { timeout: 3_000 }).catch(() => {
    const alerts = screen.queryAllByRole("alert").map((element) => element.textContent).filter(Boolean).join(" | ");
    throw new Error(`Section proposal was not sent. Alerts: ${alerts || "none"}`);
  });
  expect(proposal).toHaveBeenCalledTimes(1);
  const request = proposal.mock.calls[0][0];
  expect(request.target_kind).toBe("replace_selection");
  expect(request.selected_text).toContain(sectionCase.heading);
  expect(request.selected_text).toContain(sectionCase.includedChild);
  expect(request.selected_text).not.toContain(sectionCase.excludedPeer);
  expect(session29V2Markers(request.draft_markdown)).toEqual(session29V2Markers(session29Markdown));
  expect(session29NodeLinks(request.draft_markdown)).toEqual(session29NodeLinks(session29Markdown));
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).not.toHaveTextContent("reviewed section detail");
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  await screen.findByRole("region", { name: "Review proposed Plan edit" });
  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => expect(editorSurface).toHaveTextContent("reviewed section detail")).catch(() => {
    const alerts = screen.queryAllByRole("alert").map((element) => element.textContent).filter(Boolean).join(" | ");
    throw new Error(`Section Apply failed. Alerts: ${alerts || "none"}`);
  });
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  expect(savedMarkdown).toBe(session29Markdown);

  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(screen.getByText("Saved to this World.")).toBeInTheDocument());
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);
  const submittedMarkdown = commit.mock.calls[0][0].markdown;
  expect(normalizeThematicBreakSpacing(submittedMarkdown)).toBe(normalizeThematicBreakSpacing(expectedAfterApply));
  expect(commit.mock.calls[0][0].markdown).toBe(prepare.mock.calls[0][0].markdown);
  expect(session29V2Markers(submittedMarkdown)).toEqual(session29V2Markers(session29Markdown));
  expect(session29NodeLinks(submittedMarkdown)).toEqual(session29NodeLinks(session29Markdown));
  expect(submittedMarkdown).toContain("reviewed section detail");

  view.unmount();
  window.history.replaceState({}, "", location);
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const reloadedEditor = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(reloadedEditor).toHaveTextContent("reviewed section detail"));
  expect(session29V2Markers(savedMarkdown)).toEqual(session29V2Markers(session29Markdown));
  expect(session29NodeLinks(savedMarkdown)).toEqual(session29NodeLinks(session29Markdown));
}, 30_000);

it("reviews, applies, saves, and reloads rich content inside one selected World Plan section", async () => {
  const sourceMarkdown = [
    "# Plan",
    "",
    "## Mireward",
    "",
    "### After the attack",
    "",
    "The town waits.",
    "",
    "## North Road",
    "",
    "A different route.",
  ].join("\n");
  const replacementMarkdown = [
    "## Mireward",
    "",
    "### After the attack",
    "",
    "The **watcher** waits for *a signal*.",
    "",
    "> The first witness speaks from the gate.",
    ">",
    "> The second witness answers from the river.",
    "",
    "> [!READ-ALOUD]",
    "> The river carries a low, silver sound.",
    "",
    "> [!DECISION-CONSEQUENCE]",
    "> ### Decision",
    "> Hold the bridge.",
    ">",
    "> ### Consequence",
    "> The town keeps the crossing until dawn.",
  ].join("\n");
  savedMarkdown = sourceMarkdown;
  setupWorldApi();
  const canonicalReplacement = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(replacementMarkdown).doc);
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v1",
    action_id: "00000000-0000-4000-8000-000000000003",
    idempotency_key: request.idempotency_key,
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: request.target_kind,
    selected_text_sha256: await sha256Hex(request.selected_text),
    replacement_markdown: replacementMarkdown,
    summary: "Add the reviewed voices and decision.",
    assumptions: [],
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
    writer_confirm_token: "integration-rich-section-save-token",
    warnings: [],
    diagnostics: [],
  });
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    savedMarkdown = request.markdown;
    savedRevision = 8;
    savedDigest = "d".repeat(64);
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
      committed_record: { ...planRecord(), revision: savedRevision },
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
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  const sectionSelect = await screen.findByRole("combobox", { name: "Plan section (optional)" }) as HTMLSelectElement;
  fireEvent.click(screen.getByRole("button", { name: "Refresh sections" }));
  await waitFor(() => expect(sectionSelect.options.length).toBeGreaterThan(1));
  const option = Array.from(sectionSelect.options).find((candidate) => candidate.textContent?.includes("Mireward"));
  expect(option).toBeDefined();
  fireEvent.change(sectionSelect, { target: { value: option!.value } });
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent(`${option!.textContent} selected`));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
    target: { value: "Add the reviewed multi-paragraph witnesses, read-aloud, and decision consequence." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  await screen.findByRole("region", { name: "Review proposed Plan edit" });
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).not.toHaveTextContent("The watcher");
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => expect(editorSurface).toHaveTextContent("second witness answers from the river"));
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  expect(savedMarkdown).toBe(sourceMarkdown);

  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(screen.getByText("Saved to this World.")).toBeInTheDocument());
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);
  const submittedMarkdown = commit.mock.calls[0][0].markdown;
  expect(selectedMarkdownSection(submittedMarkdown, "Mireward").fragment).toBe(canonicalReplacement);
  expect(submittedMarkdown).toContain("## North Road");
  expect(commit.mock.calls[0][0].markdown).toBe(prepare.mock.calls[0][0].markdown);
  const reloadedSection = selectedMarkdownSection(savedMarkdown, "Mireward").fragment;
  const semanticTree = markdownToTiptapDoc(reloadedSection).doc;
  const serializedTree = JSON.stringify(semanticTree);
  expect(serializedTree).toContain('"type":"bold"');
  expect(serializedTree).toContain('"type":"italic"');
  expect(serializedTree).toContain('"type":"blockquote"');
  expect(serializedTree).toContain('"type":"callout"');
  expect(serializedTree).toContain('"type":"decisionConsequence"');

  view.unmount();
  window.history.replaceState({}, "", location);
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const reloadedEditor = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(reloadedEditor).toHaveTextContent("The watcher"));
  expect(selectedMarkdownSection(savedMarkdown, "Mireward").fragment).toBe(canonicalReplacement);
}, 30_000);

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
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Add a lantern." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  const request: WorldPlanDocumentEditProposalRequest = proposal.mock.calls[0][0];
  const namespace = `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;

  view.unmount();
  await act(async () => {
    release({
      schema_version: "dmb_world_plan_document_edit_proposal_v1",
      action_id: "00000000-0000-4000-8000-000000000004",
      idempotency_key: request.idempotency_key,
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

it("keeps an indeterminate late action out of Review and offers an explicit fresh attempt", async () => {
  setupWorldApi();
  const statusPage: WorldPlanActionProjectionPage = {
    schema_version: "dmb_world_plan_action_projection_v1" as const,
    basis: {
      world_id: worldId,
      document_id: documentId,
      object_revision: savedRevision,
      work_revision_id: "00000000-0000-4000-8000-000000000010",
      revision_n: 1,
      content_sha256: savedDigest,
    },
    actions: [],
  };
  vi.spyOn(liveApi, "getWorldPlanDocumentEditActions").mockImplementation(async () => statusPage);
  let rejectProposal!: (reason: unknown) => void;
  const pending = new Promise<WorldPlanDocumentEditProposalResponse>((_resolve, reject) => { rejectProposal = reject; });
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockReturnValue(pending);
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  const originalText = editorSurface.textContent;
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Add a distant bell." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  expect(proposal.mock.calls[0][0].idempotency_key).toMatch(/^[0-9a-f-]{36}$/i);

  statusPage.actions = [{
    action_id: "00000000-0000-4000-8000-000000000030",
    action_type: "compose",
    status: "indeterminate",
    basis: statusPage.basis,
    instruction: "Add a distant bell.",
    assistant_summary: null,
    action_sequence: 1,
    accepted_at: "2026-10-03T12:00:00Z",
    completed_at: null,
  }];
  await act(async () => {
    rejectProposal(Object.assign(new Error("The Plan action outcome is indeterminate."), { status: 409 }));
    await pending.catch(() => undefined);
  });
  expect(await screen.findByRole("alert")).toHaveTextContent("indeterminate");
  expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();

  fireEvent.click(screen.getByText("Advanced details"));
  fireEvent.click(screen.getByRole("button", { name: "Refresh action status" }));
  expect(await screen.findByText("indeterminate", { exact: true })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Continue with a new edit" }));
  expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Add a distant bell.");
  expect(editorSurface.textContent).toBe(originalText);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  view.unmount();
});

it("reuses the same action key after a network-uncertain retry of an identical intent", async () => {
  setupWorldApi();
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal")
    .mockRejectedValueOnce(new TypeError("Network response was lost."))
    .mockImplementationOnce(async (request) => ({
      schema_version: "dmb_world_plan_document_edit_proposal_v1",
      action_id: "00000000-0000-4000-8000-000000000031",
      idempotency_key: request.idempotency_key,
      document_id: request.document_id,
      world_id: request.world_id,
      base_revision: request.base_revision,
      base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256,
      target_kind: request.target_kind,
      selected_text_sha256: await sha256Hex(request.selected_text),
      replacement_markdown: "A distant bell sounds.",
      summary: "Add a distant bell.",
      assumptions: [],
      model: "gpt-6-luna",
      model_observed: true,
      model_latency_ms: 1,
      wall_latency_ms: 1,
      usage: null,
    }));
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  await screen.findByTestId("world-owned-plan-markdown-editor");
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Add a distant bell." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  const firstKey = proposal.mock.calls[0][0].idempotency_key;
  await screen.findByRole("alert");
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  expect(await screen.findByRole("region", { name: "Review proposed Plan edit" })).toBeInTheDocument();
  expect(proposal).toHaveBeenCalledTimes(2);
  expect(proposal.mock.calls[1][0].idempotency_key).toBe(firstKey);
});

it("rejects a proposal response that is not correlated to the submitted action key", async () => {
  setupWorldApi();
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v1",
    action_id: "00000000-0000-4000-8000-000000000032",
    idempotency_key: "00000000-0000-4000-8000-000000000033",
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: request.target_kind,
    selected_text_sha256: await sha256Hex(request.selected_text),
    replacement_markdown: "FOREIGN-ACTION-REPLACEMENT",
    summary: "FOREIGN-ACTION-SUMMARY",
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
  await screen.findByTestId("world-owned-plan-markdown-editor");
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Add a distant bell." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  expect(await screen.findByRole("alert")).toHaveTextContent("did not match this edit request");
  expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
});

it("rejects a thread switch during deferred Apply without changing the mounted editor", async () => {
  setupWorldApi();
  vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v1",
    action_id: "00000000-0000-4000-8000-000000000005",
    idempotency_key: request.idempotency_key,
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
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Add a lantern." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  expect(await screen.findByRole("region", { name: "Review proposed Plan edit" })).toBeInTheDocument();
  const editorTextBefore = editorSurface.textContent;

  const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
  let release!: () => void;
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const digest = vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
    await gate;
    return originalDigest(...args);
  });
  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => expect(digest).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole("button", { name: "Switch Agent thread" }));
  await waitFor(() => expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument());
  await act(async () => { release(); });

  expect(editorSurface.textContent).toBe(editorTextBefore);
  expect(editorSurface).not.toHaveTextContent("A lantern glows under the arch.");
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
});

it("edits one selected Option body, keeps Apply draft-only, then saves and freshly reopens the same Plan", async () => {
  savedMarkdown = [
    "# Plan",
    "",
    "<!-- dmb-playable-element:v2 kind=beat id=beat:approach beat_kind=spine -->",
    "## Approach",
    "The party reaches the gate.",
    "",
    "<!-- dmb-playable-element:v2 kind=choice id=choice:route -->",
    "### Route",
    "Choose a path.",
    "",
    "<!-- dmb-playable-element:v2 kind=option id=option:explore activates=beat:arrival -->",
    "- Explore [Aldric](dmb-node:node:captain-lysandra-ironveil) at dusk.",
    "",
    "<!-- dmb-playable-element:v2 kind=option id=option:wait suppresses=beat:arrival -->",
    "- Wait by the gate.",
    "",
    "<!-- dmb-playable-element:v2 kind=beat id=beat:arrival beat_kind=optional -->",
    "## Arrival",
    "A guide appears.",
    "",
  ].join("\n");
  setupWorldApi();
  const replacement = "Quietly guide [Aldric](dmb-node:node:captain-lysandra-ironveil) through the gate.";
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: "dmb_world_plan_document_edit_proposal_v2",
    action_id: "00000000-0000-4000-8000-000000000011",
    idempotency_key: request.idempotency_key,
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: "replace_playable_body",
    selected_text_sha256: null,
    playable_target: request.playable_target!,
    marker_grammar_version: "v2",
    body_scope: "option_item_content",
    range_semantics_version: "plan-playable-ranges-v1",
    body_serialization_version: "plan-playable-body-markdown-v1",
    target_body_sha256: request.target_body_sha256!,
    replacement_markdown: replacement,
    summary: "Steers Aldric through the gate quietly.",
    assumptions: [],
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
    writer_confirm_token: "integration-card-save-token",
    warnings: [],
    diagnostics: [],
  });
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    savedMarkdown = request.markdown;
    savedRevision = 8;
    savedDigest = "c".repeat(64);
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
      committed_record: { ...planRecord(), revision: savedRevision },
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
  await waitFor(() => expect(editorSurface).toHaveTextContent("Wait by the gate."));
  fireEvent.click(await screen.findByRole("button", { name: "Cards" }));
  const cards = screen.getByTestId("world-plan-cards");
  const targetCard = cards.querySelector('[data-element-id="option:explore"]');
  expect(targetCard).not.toBeNull();
  fireEvent.click(within(targetCard as HTMLElement).getByRole("button", { name: "Select for Edit" }));
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Guide Aldric through the gate without drawing attention." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await screen.findByRole("region", { name: "Review proposed Plan edit" });

  expect(proposal).toHaveBeenCalledTimes(1);
  expect(proposal.mock.calls[0]?.[0]).toMatchObject({
    target_kind: "replace_playable_body",
    selected_text: "",
    playable_target: { kind: "option", id: "option:explore" },
    body_serialization_version: "plan-playable-body-markdown-v1",
    target_body_markdown: "Explore [Aldric](dmb-node:node:captain-lysandra-ironveil) at dusk.\n",
  });
  expect(screen.getByRole("region", { name: "Review proposed Plan edit" })).toHaveTextContent(replacement.replace(/\[([^\]]+)\]\([^)]+\)/, "$1"));
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => expect(editorSurface).toHaveTextContent("Quietly guide Aldric through the gate."));
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  expect(savedMarkdown).not.toContain("Quietly guide Aldric");

  fireEvent.click(await screen.findByRole("button", { name: "Save Plan" }));
  await screen.findByText("Saved to this World.");
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);
  expect(savedMarkdown).toContain("option:explore activates=beat:arrival");
  expect(savedMarkdown).toContain("option:wait suppresses=beat:arrival");
  expect(savedMarkdown).toContain("- Wait by the gate.");
  expect(savedMarkdown).toContain("[Aldric](dmb-node:node:captain-lysandra-ironveil)");
  expect(savedMarkdown).toContain("- Quietly guide [Aldric](dmb-node:node:captain-lysandra-ironveil) through the gate.");

  view.unmount();
  window.history.replaceState({}, "", location);
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const reopened = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(reopened).toHaveTextContent("Quietly guide Aldric through the gate."));
  expect(reopened).toHaveTextContent("Wait by the gate.");
});
