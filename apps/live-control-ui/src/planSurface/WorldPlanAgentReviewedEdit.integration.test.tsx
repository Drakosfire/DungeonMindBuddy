import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { StrictMode, useMemo, useState, type ReactNode } from "react";
import { webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeAll, expect, it, vi } from "vitest";
import { Editor } from "@tiptap/core";

import * as liveApi from "../api/liveApi";
import * as conversationLibrary from "../api/conversationLibraryApi";
import * as planEdit from "./agentEdit/planAgentEditProposal";
import type { WorldOwnedPlanRecordV2, WorldPlanActionProjectionPage, WorldPlanDocumentEditProposalRequest, WorldPlanDocumentEditProposalResponse } from "../api/types";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { useAgentInteraction } from "../agentInteraction/useAgentInteraction";
import { AgentInteractionChrome } from "../agentInteraction/AgentInteractionChrome";
import { WorldAgentConversation, WorldAgentConversationProvider, usePublishWorldPlayConversation } from "../agentInteraction/WorldAgentConversation";
import { usePublishAgentSurfaceContext } from "../agentInteraction/usePublishAgentSurfaceContext";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { setupPlanAuthoringIntegration } from "../test/planAuthoringIntegrationFixture";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { activeThreadStorageKey, threadIndexStorageKey, threadStorageKey } from "../agentInteraction/agentInteractionStorage";
import { PlanSurfacePage } from "./PlanSurfacePage";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { DEFAULT_MARKDOWN_EDITOR_EXTENSIONS } from "../tiptap/MarkdownEditorCore";
import {
  playableBodyProtectedStructureMatches,
  resolvePlayableBodyTarget,
} from "./agentEdit/planPlayableBodyTarget";

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

const worldId = "world-reviewed-edit-integration";
const documentId = "saved-world-plan-reviewed-edit";
const initialMarkdown = "# Plan\n\nThe keeper waits beneath the black arch.\n";
const v2OptionPlanMarkdown = [
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
const protectedScenePlanMarkdown = [
  "# ",
  "",
  "DOGFOOD REVISION CHECK — saved for source pin verification.",
  "",
  "The air carries a cool, earthy scent of damp stone, like a cellar after rain.",
  "",
  "# DOGFOOD DISPOSABLE — Plan-to-Play smoke test 2026-10-06",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:dogfood-smoke beat_kind=spine -->",
  "## Smoke test",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:dogfood-smoke -->",
  "### Quiet test scene",
  "",
  "A clearly synthetic scene used only to verify the local Plan-to-Play path. No campaign canon.",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:dogfood-smoke scene=scene:dogfood-smoke -->",
  "### What should happen?",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:dogfood-continue -->",
  "- Continue the smoke test.",
  "",
].join("\n");
const multiParagraphProtectedScenePlanMarkdown = [
  "# Disposable card edit",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:smoke beat_kind=spine -->",
  "## Smoke",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:smoke -->",
  "### Quiet scene",
  "",
  "Scene body.",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:smoke scene=scene:smoke -->",
  "### Choose",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:smoke -->",
  "- **Continue the smoke test.**",
  "",
  "  First option paragraph with [the guide](dmb-node:node:guide).",
  "",
  "  Second option paragraph.",
  "",
].join("\n");
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

function CurrentIntegrationPage() {
  const selected = useSelectedWorld();
  if (selected.kind !== "managed") return null;
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <WorldAgentConversationProvider worldId={selected.worldId}>
      <PlanSurfacePage /><AgentInteractionChrome />
      <WorldAgentConversation surface="plan" worldId={selected.worldId} worldName="Integration World" />
    </WorldAgentConversationProvider>
  </AskPluginSlotProvider></AgentInteractionProvider>;
}

function IntegrationPlayPublisher() {
  const context = useMemo(() => ({surfaceId: "play" as const, label: "Play", campaignId: null, documentId: null,
    sessionNumber: null, ambientSummary: "World Run", sourceEnvelope: null}), []);
  const run = useMemo(() => ({worldId, runId: "run-one", runRevision: 3,
    surfaceInstanceId: "play-instance", contentBasis: {edition_revision: 0, edition_revision_id: null,
      content_sha256: "a".repeat(64)}, beatId: "beat:crossing", sceneId: "scene:west-gate",
    beatTitle: "The Crossing", sceneTitle: "West Gate"}), []);
  usePublishAgentSurfaceContext(context);
  usePublishWorldPlayConversation(run, null);
  return null;
}

function SwitchableNativeIntegrationPage() {
  const [surface, setSurface] = useState<"plan" | "play">("plan");
  return <AgentInteractionProvider><AskPluginSlotProvider><WorldAgentConversationProvider worldId={worldId}>
    <button type="button" onClick={() => setSurface(current => current === "plan" ? "play" : "plan")}>Switch surface</button>
    {surface === "plan" ? <PlanSurfacePage /> : <SurfaceContextProvider><IntegrationPlayPublisher /></SurfaceContextProvider>}
    <AgentInteractionChrome /><WorldAgentConversation surface={surface} worldId={worldId} worldName="Integration World" />
  </WorldAgentConversationProvider></AskPluginSlotProvider></AgentInteractionProvider>;
}

function ThreadSwitchControl() {
  const agent = useAgentInteraction();
  return <button type="button" onClick={() => agent.createThread("Switched during Apply")}>Switch Agent thread</button>;
}

async function sha256Hex(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function v2OptionProposalResponse(
  request: WorldPlanDocumentEditProposalRequest,
  actionId: string,
  replacementMarkdown: string,
): WorldPlanDocumentEditProposalResponse {
  if (request.target_kind !== "replace_playable_body" || !request.playable_target) {
    throw new Error("The mounted card-body test must submit a typed Playable target.");
  }
  return {
    schema_version: "dmb_world_plan_document_edit_proposal_v2",
    action_id: actionId,
    idempotency_key: request.idempotency_key,
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: "replace_playable_body",
    selected_text_sha256: null,
    playable_target: request.playable_target,
    marker_grammar_version: "v2",
    body_scope: "option_item_content",
    range_semantics_version: "plan-playable-ranges-v1",
    body_serialization_version: "plan-playable-body-markdown-v1",
    target_body_sha256: request.target_body_sha256!,
    replacement_markdown: replacementMarkdown,
    summary: "Revise the selected Option body.",
    assumptions: [],
    model: "gpt-6-luna",
    model_observed: true,
    model_latency_ms: 1,
    wall_latency_ms: 1,
    usage: null,
  };
}

function v2SceneProposalResponse(
  request: WorldPlanDocumentEditProposalRequest,
  actionId: string,
  replacementMarkdown: string,
): WorldPlanDocumentEditProposalResponse {
  if (request.target_kind !== "replace_playable_body" || request.playable_target?.kind !== "scene") {
    throw new Error("The mounted Scene test must submit a typed Playable body target.");
  }
  return {
    schema_version: "dmb_world_plan_document_edit_proposal_v2",
    action_id: actionId,
    idempotency_key: request.idempotency_key,
    document_id: request.document_id,
    world_id: request.world_id,
    base_revision: request.base_revision,
    base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256,
    target_kind: "replace_playable_body",
    selected_text_sha256: null,
    playable_target: request.playable_target,
    marker_grammar_version: "v2",
    body_scope: "heading_body",
    range_semantics_version: "plan-playable-ranges-v1",
    body_serialization_version: "plan-playable-body-markdown-v1",
    target_body_sha256: request.target_body_sha256!,
    replacement_markdown: replacementMarkdown,
    summary: "Preserve the smoke sentence and add a sensory GM cue.",
    assumptions: [],
    model: "gpt-6-luna",
    model_observed: true,
    model_latency_ms: 1,
    wall_latency_ms: 1,
    usage: null,
  };
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

it("resumes the second identical saved selection after remount, then reviews, applies, saves and reopens", async () => {
  savedMarkdown = "# Plan\n\nSame passage.\n\nOther prose.\n\nSame passage.\n";
  setupWorldApi();
  const conversationId = "00000000-0000-4000-8000-000000000071";
  const clarificationId = "00000000-0000-4000-8000-000000000072";
  const proposalId = "00000000-0000-4000-8000-000000000073";
  const actions: any[] = [];
  vi.spyOn(liveApi, "getWorldAgentConversationHistory").mockResolvedValue({
    schema: "dmb_agent_conversation_history_v1", world_id: worldId,
    conversation_state: "active", conversation_id: conversationId,
    active_conversation_id: conversationId, pointer_revision: 4,
    turns: [], next_before_sequence: null,
  });
  vi.mocked(liveApi.getWorldPlanDocumentEditActions).mockImplementation(async () => ({
    schema_version: "dmb_world_plan_action_projection_v1",
    basis: { world_id: worldId, document_id: documentId, object_revision: savedRevision,
      work_revision_id: "00000000-0000-4000-8000-000000000010", revision_n: 1, content_sha256: savedDigest },
    actions,
  }));
  vi.spyOn(liveApi, "getWorldPlanConversationActions").mockImplementation(async () => ({
    schema_version: "dmb_world_plan_action_conversation_projection_v1", world_id: worldId,
    conversation_id: conversationId, actions, next_before_action_sequence: null,
  }));
  const post = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => {
    const result = request.continuation_of_action_id
      ? { kind: "proposal", result_id: "00000000-0000-4000-8000-000000000074",
        message: "Change only the second passage.", answer_segments: [], citation_map: null }
      : { kind: "clarification", result_id: "00000000-0000-4000-8000-000000000075",
        message: "Which occurrence should change?", answer_segments: [], citation_map: null };
    const actionId = request.continuation_of_action_id ? proposalId : clarificationId;
    actions.push({
      action_id: actionId, action_type: "revise", status: "completed",
      basis: { world_id: worldId, document_id: documentId, object_revision: 7,
        work_revision_id: "00000000-0000-4000-8000-000000000010", revision_n: 1, content_sha256: request.base_content_sha256 },
      instruction: request.instruction, assistant_summary: result.message,
      action_sequence: actions.length + 1, accepted_at: "2026-10-12T00:00:00Z",
      completed_at: "2026-10-12T00:00:01Z", playable_target_receipt: null,
      selection_anchor: request.selection_anchor,
      consultation: { receipt: { origin_conversation_id: conversationId, origin_pointer_revision: 4,
        draft_sha256: request.draft_sha256, selected_text_sha256: await sha256Hex(request.selected_text),
        continuation: request.continuation_of_action_id
          ? { continuation_of_action_id: clarificationId } : null },
      result },
      source_open_targets: [],
    });
    if (!request.continuation_of_action_id) return {
      schema_version: "dmb_world_plan_edit_clarification_v1", action_id: actionId,
      idempotency_key: request.idempotency_key, document_id: documentId, world_id: worldId,
      base_revision: 7, base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256, selected_text_sha256: await sha256Hex(request.selected_text),
      kind: "clarification", message: result.message,
      consultation: { origin_conversation_id: conversationId, origin_pointer_revision: 4, result },
    } as any;
    return {
      schema_version: "dmb_world_plan_document_edit_proposal_v1", action_id: actionId,
      idempotency_key: request.idempotency_key, document_id: documentId, world_id: worldId,
      base_revision: 7, base_content_sha256: request.base_content_sha256,
      draft_sha256: request.draft_sha256, target_kind: "replace_selection",
      selected_text_sha256: await sha256Hex(request.selected_text),
      replacement_markdown: "Only second changed.", summary: result.message,
      assumptions: [], model: "fake-provider", model_observed: false,
      model_latency_ms: 0, wall_latency_ms: 0, usage: null,
      consultation: { origin_conversation_id: conversationId, origin_pointer_revision: 4, result },
    } as any;
  });
  vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockResolvedValue({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2", scope_mode: "world",
    world_id: worldId, document_id: documentId, title: "Integration Plan",
    target_relpath: `out/workspace/plan/${documentId}.md`,
    target_display_path: `out/workspace/plan/${documentId}.md`,
    registry_revision: 8, file_exists: true, writer_ok: true,
    writer_confirm_token: "selection-save-token", warnings: [], diagnostics: [],
  });
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    savedMarkdown = request.markdown;
    savedRevision = 8;
    savedDigest = await sha256Hex(savedMarkdown);
    return { schema_version: "dmb_tiptap_markdown_write_commit_v2", scope_mode: "world",
      world_id: worldId, document_id: documentId, title: "Integration Plan",
      target_relpath: `out/workspace/plan/${documentId}.md`,
      target_display_path: `out/workspace/plan/${documentId}.md`,
      registry_revision: 8, committed_revision: 8,
      committed_record: { ...planRecord(), revision: 8 },
      normalized_content_sha256: savedDigest, writer_ok: true, writer_phase: "commit", diagnostics: [] };
  });
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  let view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
  const proseMirror = surface.querySelector(".ProseMirror") as HTMLElement;
  const mountedEditor = (proseMirror as HTMLElement & { editor: Editor }).editor;
  const duplicates = Array.from(proseMirror.querySelectorAll("p")).filter((p) => p.textContent === "Same passage.");
  expect(duplicates).toHaveLength(2);
  const positions: number[] = [];
  mountedEditor.state.doc.descendants((node, position) => {
    if (node.isText && node.text === "Same passage.") positions.push(position);
  });
  expect(positions).toHaveLength(2);
  act(() => mountedEditor.commands.setTextSelection({ from: positions[1]!, to: positions[1]! + "Same passage.".length }));
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  await screen.findByText(/No messages yet/);
  await waitFor(() => expect(liveApi.getWorldAgentConversationHistory).toHaveBeenCalled());
  await waitFor(() => expect(liveApi.getWorldPlanConversationActions).toHaveBeenCalledWith(worldId, conversationId));
  fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "Revise this passage." } });
  fireEvent.click(await screen.findByRole("button", { name: "Propose edit" }));
  await screen.findAllByText("Which occurrence should change?");
  expect(post).toHaveBeenCalledTimes(1);
  expect(post.mock.calls[0]![0]).toMatchObject({ target_kind: "replace_selection", selected_text: "Same passage." });
  const originalAnchor = post.mock.calls[0]![0].selection_anchor!;
  expect(originalAnchor.from).toBeGreaterThan(1);
  view.unmount();
  window.getSelection()?.removeAllRanges();

  view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  await screen.findByTestId("world-owned-plan-markdown-editor");
  expect(window.getSelection()?.isCollapsed).toBe(true);
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  await screen.findByText(/No messages yet/);
  fireEvent.click(await screen.findByRole("button", { name: "Reply about this edit" }));
  await waitFor(() => expect(screen.getByLabelText("Actual Plan change target")).toHaveTextContent("Replace selected editor text"));
  expect(screen.queryAllByRole("alert").map((element) => element.textContent)).toEqual([]);
  await screen.findByRole("button", { name: "Propose edit" });
  fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), { target: { value: "The second one." } });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  const review = await screen.findByRole("region", { name: "Change selected text" });
  expect(post).toHaveBeenCalledTimes(2);
  expect(post.mock.calls[1]![0].selection_anchor).toEqual(originalAnchor);
  expect(review).toHaveTextContent("Same passage.");
  expect(review).toHaveTextContent("Only second changed.");
  fireEvent.click(within(review).getByRole("button", { name: "Apply to draft" }));
  await waitFor(() => expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("Only second changed."));
  expect(screen.getByTestId("world-owned-plan-markdown-editor").textContent?.match(/Same passage\./g)).toHaveLength(1);
  fireEvent.click(within(review).getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(commit).toHaveBeenCalledTimes(1));
  view.unmount();
  render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const reopened = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(reopened).toHaveTextContent("Only second changed."));
  expect(reopened.textContent?.match(/Same passage\./g)).toHaveLength(1);
}, 30_000);

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

it("keeps a Scene target available when a sibling Option has multiple paragraphs", async () => {
  const markdown = [
    "# Plan",
    "",
    "<!-- dmb-playable-element:v2 kind=beat id=beat:smoke beat_kind=spine -->",
    "## Smoke",
    "",
    "<!-- dmb-playable-element:v2 kind=scene id=scene:smoke -->",
    "### Quiet scene",
    "",
    "Scene body.",
    "",
    "<!-- dmb-playable-element:v2 kind=choice id=choice:smoke scene=scene:smoke -->",
    "### Choose",
    "",
    "<!-- dmb-playable-element:v2 kind=option id=option:smoke -->",
    "- **Continue the smoke test.**",
    "",
    "  First option paragraph.",
    "",
    "  Second option paragraph.",
    "",
  ].join("\n");
  const imported = markdownToTiptapDoc(markdown);
  const editor = new Editor({ extensions: DEFAULT_MARKDOWN_EDITOR_EXTENSIONS, content: imported.doc });
  try {
    const before = editor.getJSON();
    const beforeList = before.content?.find((node) => node.type === "bulletList");
    expect(beforeList?.content?.[0]?.content).toHaveLength(3);
    const reloaded = markdownToTiptapDoc(tiptapJsonToSemanticMarkdown(before)).doc;
    const afterList = reloaded.content?.find((node) => node.type === "bulletList");
    expect(afterList?.content?.[0]?.content).toHaveLength(3);
    const target = await resolvePlayableBodyTarget(editor, { kind: "scene", id: "scene:smoke" });
    expect(target.targetBodyMarkdown).toBe("Scene body.\n");
    expect(playableBodyProtectedStructureMatches(before, reloaded, target)).toBe(true);
  } finally { editor.destroy(); }
});

it.each(liveApplyScenarios)("stages, reviews, explicitly saves, and reloads a live %s edit on the mounted editor", async (label, sourceMarkdown, replacementMarkdown, expectedAppliedText) => {
  setupWorldApi();
  const current = setupPlanAuthoringIntegration(planRecord(), sourceMarkdown, replacementMarkdown);
  const nativeNavigator = navigator;
  vi.stubGlobal("navigator", new Proxy(nativeNavigator, {
    get: (target, key) => key === "locks"
      ? { request: async (_name: string, work: () => unknown) => work() }
      : Reflect.get(target, key, target),
  }));
  const location = "/plan?world=" + worldId + "&documentId=" + documentId;
  window.history.replaceState({}, "", location);
  const tree = () => <StrictMode><SelectedWorldProvider locationSnapshot={location}><CurrentIntegrationPage /></SelectedWorldProvider></StrictMode>;
  let view = render(tree());
  try {
    const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const element = surface.querySelector(".ProseMirror") as HTMLElement & { editor: Editor };
    const editor = element.editor;
    const firstParagraph = editor.state.doc.firstChild!;
    expect(firstParagraph.type.name).toBe("paragraph");
    const originalParagraph = firstParagraph.textContent;
    const firstSentenceEnd = originalParagraph.indexOf(".") + 1;
    expect(firstSentenceEnd).toBeGreaterThan(0);
    const position = 1 + firstSentenceEnd;
    act(() => editor.commands.setTextSelection(position));
    const before = editor.getJSON();
    const beforeText = editor.state.doc.textBetween(0, editor.state.doc.content.size, "");
    const originalQuotes = before.content?.filter(node => node.type === "blockquote") ?? [];
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    const conversation = await screen.findByRole("region", {name: "World conversation"});
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"}))
      .toHaveAttribute("aria-busy", "false"));
    const field = within(conversation).getByLabelText("Message DungeonBuddy");
    fireEvent.change(field, {target: {value: "Add a warm light source to the opening."}});
    fireEvent.click(within(conversation).getByText(/^(Automatic|Plan change) · Change$/));
    fireEvent.click(within(conversation).getByRole("button", {name: "Request a Plan change"}));
    const send = within(conversation).getByRole("button", {name: "Propose edit"});
    await waitFor(() => expect(send).toBeEnabled());
    fireEvent.click(send);
    await waitFor(() => expect(current.post).toHaveBeenCalledTimes(1));
    const request = current.post.mock.calls[0]![0];
    const capture = request.plan_authoring_capture!;
    expect(request.plan_requested_operation).toBe("write_current_page");
    expect(request.owner_scope).toEqual({kind: "world", world_id: worldId});
    expect(request.primary_work.object_id).toBe(documentId);
    expect(capture).toMatchObject({
      schema: "dmb_plan_authoring_capture_v1", world_id: worldId, document_id: documentId,
      base_revision: 7, target_kind: "insert_at_caret", selected_text: "", from: position, to: position,
    });
    expect(JSON.parse(capture.editor_json)).toEqual(before);
    expect(capture.draft_markdown).toContain(originalParagraph);
    expect(request).not.toHaveProperty("session");
    const suggestion = await screen.findByRole("textbox", {name: "Suggestion text"});
    expect(suggestion).toHaveTextContent(expectedAppliedText);
    expect(suggestion.closest("[data-turn-id]")).toBeNull();
    expect(editor.getJSON()).toEqual(before);
    expect(current.readSaved().markdown).toBe(sourceMarkdown);
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(0);
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
    expect(current.legacyProposal).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("region", {name: "Suggestion review"})).getByRole("button", {name: "Save", exact: true}));
    await waitFor(() => expect(current.readReview()?.state).toBe("applied"));
    const saved = current.readSaved();
    expect(saved.record.revision).toBe(8);
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(1);
    const after = editor.getJSON();
    const afterText = editor.state.doc.textBetween(0, editor.state.doc.content.size, "");
    const insertedText = label === "canonical READ-ALOUD callout"
      ? replacementMarkdown.split("\n").slice(1).map(line => line.replace(/^> ?/, "")).join("\n")
      : replacementMarkdown;
    // The inserted block splits the paragraph; Markdown reload drops its one
    // leading boundary space, while every other original character is protected.
    const protectedSuffix = beforeText.slice(firstSentenceEnd).replace(/^ /, "");
    const expectedText = beforeText.slice(0, firstSentenceEnd) + insertedText + protectedSuffix;
    expect(afterText).toBe(expectedText);
    expect(saved.markdown).toBe(tiptapJsonToSemanticMarkdown(after));
    if (label === "canonical READ-ALOUD callout") expect(saved.markdown).toContain("> [!READ-ALOUD]");
    if (label === "plain root blockquote") {
      expect(after.content?.filter(node => node.type === "blockquote")).toEqual(originalQuotes);
      expect(saved.markdown).toContain("> A root-level witness keeps watch from the broken wall.");
    }
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
    view.unmount();
    window.history.replaceState({}, "", location);
    view = render(tree());
    const reopened = await screen.findByTestId("world-owned-plan-markdown-editor");
    await waitFor(() => {
      const reopenedEditor = (reopened.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
      expect(reopenedEditor.getJSON()).toEqual(after);
    });
    expect(liveApi.getWorldOwnedPlanSnapshot).toHaveBeenLastCalledWith(documentId);
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    await screen.findByRole("region", {name: "World conversation"});
    fireEvent.click(await screen.findByText("Trace", {selector: "summary"}));
    await screen.findByText("Suggestion saved on the Plan.");
    expect(screen.queryByRole("textbox", {name: "Suggestion text"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Save", exact: true})).not.toBeInTheDocument();
    expect(current.readReview()?.state).toBe("applied");
    expect(current.post).toHaveBeenCalledTimes(1);
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(1);
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
  } finally {
    view.unmount();
    vi.unstubAllGlobals();
    sessionStorage.clear();
  }
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

async function currentSectionRoundTrip(
  sourceMarkdown: string, heading: string, replacementForDraft: (draft: string) => string,
  verifyCapture: (selectedText: string, draft: string) => void,
  verifySaved: (markdown: string) => void,
) {
  setupWorldApi();
  const current = setupPlanAuthoringIntegration(planRecord(), sourceMarkdown, replacementForDraft);
  const nativeNavigator = navigator;
  vi.stubGlobal("navigator", new Proxy(nativeNavigator, {
    get: (target, key) => key === "locks"
      ? { request: async (_name: string, work: () => unknown) => work() }
      : Reflect.get(target, key, target),
  }));
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const tree = () => <StrictMode><SelectedWorldProvider locationSnapshot={location}><CurrentIntegrationPage /></SelectedWorldProvider></StrictMode>;
  let view = render(tree());
  try {
    const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const editor = (surface.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
    const before = editor.getJSON();
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    const conversation = await screen.findByRole("region", {name: "World conversation"});
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"})).toHaveAttribute("aria-busy", "false"));
    fireEvent.change(within(conversation).getByLabelText("Message DungeonBuddy"), {target: {value: `Revise ${heading} with reviewed details.`}});
    fireEvent.click(within(conversation).getByText(/^(Automatic|Plan change) · Change$/));
    fireEvent.click(within(conversation).getByRole("button", {name: "Request a Plan change"}));
    const targetSummary = within(conversation).getByText("Choose section").closest("summary")!;
    expect(targetSummary.closest("details")).not.toHaveAttribute("open");
    fireEvent.click(targetSummary);
    expect(targetSummary.closest("details")).toHaveAttribute("open");
    fireEvent.click(within(conversation).getByRole("button", {name: "Refresh sections"}));
    const select = within(conversation).getByRole("combobox", {name: "Plan section (optional)"}) as HTMLSelectElement;
    expect(select).toHaveAttribute("aria-describedby", "world-plan-agent-target-help");
    await waitFor(() => expect(Array.from(select.options).some(option => option.textContent?.includes(heading))).toBe(true));
    const option = Array.from(select.options).find(row => row.textContent?.includes(heading))!;
    expect(option.disabled).toBe(false);
    fireEvent.change(select, {target: {value: option.value}});
    await waitFor(() => expect(editor.state.selection.empty).toBe(false));
    const {from, to} = editor.state.selection;
    expect(editor.getJSON()).toEqual(before);
    expect(current.post).not.toHaveBeenCalled();
    expect(current.commands).not.toHaveBeenCalled();
    const send = within(conversation).getByRole("button", {name: "Propose edit"});
    await waitFor(() => expect(send).toBeEnabled());
    fireEvent.click(send);
    await waitFor(() => expect(current.post).toHaveBeenCalledTimes(1));
    const capture = current.post.mock.calls[0]![0].plan_authoring_capture!;
    expect(current.post.mock.calls[0]![0].plan_requested_operation).toBe("write_current_page");
    expect(capture).toMatchObject({world_id: worldId, document_id: documentId, base_revision: 7,
      target_kind: "replace_selection", from, to});
    expect(JSON.parse(capture.editor_json)).toEqual(before);
    verifyCapture(capture.selected_text, capture.draft_markdown);
    const replacement = replacementForDraft(capture.draft_markdown);
    const canonicalReplacement = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(replacement).doc);
    const expected = selectedMarkdownSection(capture.draft_markdown, heading).replace(canonicalReplacement);
    await screen.findByRole("textbox", {name: "Suggestion text"});
    expect(editor.getJSON()).toEqual(before);
    expect(current.readSaved().markdown).toBe(sourceMarkdown);
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(0);
    expect(current.legacyProposal).not.toHaveBeenCalled();
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
    fireEvent.click(within(screen.getByRole("region", {name: "Suggestion review"})).getByRole("button", {name: "Save", exact: true}));
    await waitFor(() => expect(current.readReview()?.state).toBe("applied"));
    const saved = current.readSaved();
    expect(saved.record.revision).toBe(8);
    expect(normalizeThematicBreakSpacing(saved.markdown)).toBe(normalizeThematicBreakSpacing(expected));
    verifySaved(saved.markdown);
    const after = editor.getJSON();
    expect(tiptapJsonToSemanticMarkdown(after)).toBe(saved.markdown);
    view.unmount();
    window.history.replaceState({}, "", location);
    view = render(tree());
    const reopened = await screen.findByTestId("world-owned-plan-markdown-editor");
    await waitFor(() => expect((reopened.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor.getJSON()).toEqual(after));
    verifySaved(current.readSaved().markdown);
    expect(current.post).toHaveBeenCalledTimes(1);
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(1);
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
  } finally {
    view.unmount();
    vi.unstubAllGlobals();
    sessionStorage.clear();
  }
}

it.each(session29SectionCases)("targets a Session 29 $label and explicitly saves its reviewed subtree", async (sectionCase) => {
  expect(session29V2Markers(session29Markdown)).toHaveLength(90);
  expect(session29NodeLinks(session29Markdown)).toHaveLength(72);
  await currentSectionRoundTrip(session29Markdown, sectionCase.heading,
    draft => reviseFirstSectionProse(selectedMarkdownSection(draft, sectionCase.heading).fragment),
    (selected, draft) => {
      expect(selected).toContain(sectionCase.heading);
      expect(selected).toContain(sectionCase.includedChild);
      expect(selected).not.toContain(sectionCase.excludedPeer);
      expect(session29V2Markers(draft)).toEqual(session29V2Markers(session29Markdown));
      expect(session29NodeLinks(draft)).toEqual(session29NodeLinks(session29Markdown));
    },
    markdown => {
      expect(session29V2Markers(markdown)).toEqual(session29V2Markers(session29Markdown));
      expect(session29NodeLinks(markdown)).toEqual(session29NodeLinks(session29Markdown));
      expect(markdown).toContain("reviewed section detail");
    });
}, 30_000);

it("stages, explicitly saves, and reloads rich content inside one selected World Plan section", async () => {
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
  const canonicalReplacement = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(replacementMarkdown).doc);
  await currentSectionRoundTrip(sourceMarkdown, "Mireward", () => replacementMarkdown,
    selected => {
      expect(selected).toContain("Mireward");
      expect(selected).toContain("After the attack");
      expect(selected).toContain("The town waits.");
      expect(selected).not.toContain("North Road");
      expect(selected).not.toContain("A different route.");
    },
    markdown => {
      expect(selectedMarkdownSection(markdown, "Mireward").fragment).toBe(canonicalReplacement);
      expect(selectedMarkdownSection(markdown, "North Road").fragment).toBe(selectedMarkdownSection(tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(sourceMarkdown).doc), "North Road").fragment);
      const semanticTree = JSON.stringify(markdownToTiptapDoc(selectedMarkdownSection(markdown, "Mireward").fragment).doc);
      for (const type of ["bold", "italic", "blockquote", "callout", "decisionConsequence"]) {
        expect(semanticTree).toContain(`"type":"${type}"`);
      }
    });
}, 30_000);

it("settles a late native Plan turn after unmount and recovers its suggestion without applying or reposting", async () => {
  setupWorldApi();
  const current = setupPlanAuthoringIntegration(planRecord(), initialMarkdown, "A late lantern glows.");
  const respond = current.post.getMockImplementation()!;
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  current.post.mockImplementation(async request => { await gate; return respond(request); });
  const nativeNavigator = navigator;
  vi.stubGlobal("navigator", new Proxy(nativeNavigator, {
    get: (target, key) => key === "locks"
      ? { request: async (_name: string, work: () => unknown) => work() }
      : Reflect.get(target, key, target),
  }));
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const tree = () => <StrictMode><SelectedWorldProvider locationSnapshot={location}><CurrentIntegrationPage /></SelectedWorldProvider></StrictMode>;
  const pendingPrefix = `dmb:world-plan-pending-ask:v1:${encodeURIComponent(worldId)}:${encodeURIComponent(documentId)}:`;
  const pendingKeys = () => Object.keys(localStorage).filter(key => key.startsWith(pendingPrefix));
  const namespace = `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
  let view = render(tree());
  try {
    const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const editor = (surface.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
    const before = editor.getJSON();
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    const conversation = await screen.findByRole("region", {name: "World conversation"});
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"})).toHaveAttribute("aria-busy", "false"));
    fireEvent.change(within(conversation).getByLabelText("Message DungeonBuddy"), {target: {value: "Add a late lantern."}});
    fireEvent.click(within(conversation).getByText(/^(Automatic|Plan change) · Change$/));
    fireEvent.click(within(conversation).getByRole("button", {name: "Request a Plan change"}));
    const send = within(conversation).getByRole("button", {name: "Propose edit"});
    await waitFor(() => expect(send).toBeEnabled());
    fireEvent.click(send);
    await waitFor(() => expect(current.post).toHaveBeenCalledTimes(1));
    expect(pendingKeys()).toHaveLength(1);
    const request = current.post.mock.calls[0]![0];
    expect(JSON.parse(localStorage.getItem(pendingKeys()[0]!)!)).toMatchObject({
      schema: "dmb_world_plan_pending_ask_v1", request,
      origin: {worldId, documentId, objectRevision: 7},
    });
    expect(request.plan_requested_operation).toBe("write_current_page");
    expect(request.plan_authoring_capture).toMatchObject({world_id: worldId, document_id: documentId, base_revision: 7});
    view.unmount();
    await act(async () => { release(); await current.post.mock.results[0]!.value; });
    await waitFor(() => expect(pendingKeys()).toHaveLength(0));
    expect(editor.getJSON()).toEqual(before);
    expect(current.commands).not.toHaveBeenCalled();
    expect(current.readReview()).toBeNull();
    expect(current.readSaved().markdown).toBe(initialMarkdown);
    expect(current.readSaved().record.revision).toBe(7);
    expect(localStorage.getItem(activeThreadStorageKey(namespace, "plan", documentId))).toBeNull();
    expect(localStorage.getItem(threadIndexStorageKey(namespace, "plan", documentId))).toBeNull();

    // The accepted turn belongs to durable World history. A fresh mount must
    // recover it without reposting or silently applying its proposed edit.
    view = render(tree());
    const reopenedSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const reopenedEditor = (reopenedSurface.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    fireEvent.click(await screen.findByText("Trace", {exact: true}));
    expect(await screen.findByRole("textbox", {name: "Suggestion text"})).toHaveTextContent("A late lantern glows.");
    expect(await screen.findByText("Add a late lantern.", {exact: true})).toBeInTheDocument();
    expect(reopenedEditor.getJSON()).toEqual(before);
    expect(reopenedEditor.state.doc.textBetween(0, reopenedEditor.state.doc.content.size, "")).not.toContain("A late lantern glows.");
    expect(current.readSaved().markdown).toBe(initialMarkdown);
    expect(current.readSaved().record.revision).toBe(7);
    expect(current.commands).toHaveBeenCalled();
    expect(current.commands.mock.calls.map(call => call[2].operation)).toEqual(["open"]);
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
    expect(current.legacyProposal).not.toHaveBeenCalled();
    expect(current.post).toHaveBeenCalledTimes(1);
  } finally {
    release();
    view.unmount();
    vi.unstubAllGlobals();
    sessionStorage.clear();
  }
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

it("rejects an initial native proposal whose origin key differs from its sealed capture", async () => {
  setupWorldApi();
  const foreignKey = "00000000-0000-4000-8000-000000000033";
  const current = setupPlanAuthoringIntegration(planRecord(), initialMarkdown, "FOREIGN-ACTION-REPLACEMENT");
  const respond = current.post.getMockImplementation()!;
  let returnedOrigin = "";
  current.post.mockImplementation(async request => {
    const response = await respond(request);
    if (!("plan_proposal" in response) || !response.plan_proposal) throw new Error("Expected the sealed proposal fixture.");
    // The retained history and returned response share this proposal. Keep both
    // corrupt: a valid saved proposal must not launder an uncorrelated reply.
    response.plan_proposal.origin.idempotency_key = foreignKey;
    returnedOrigin = response.plan_proposal.origin.idempotency_key;
    return response;
  });
  const nativeNavigator = navigator;
  vi.stubGlobal("navigator", new Proxy(nativeNavigator, {
    get: (target, key) => key === "locks"
      ? { request: async (_name: string, work: () => unknown) => work() }
      : Reflect.get(target, key, target),
  }));
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><CurrentIntegrationPage /></SelectedWorldProvider></StrictMode>);
  try {
    const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const editor = (surface.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
    const before = editor.getJSON();
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    const conversation = await screen.findByRole("region", {name: "World conversation"});
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"})).toHaveAttribute("aria-busy", "false"));
    fireEvent.change(within(conversation).getByLabelText("Message DungeonBuddy"), {target: {value: "Add a distant bell."}});
    fireEvent.click(within(conversation).getByText(/^(Automatic|Plan change) · Change$/));
    fireEvent.click(within(conversation).getByRole("button", {name: "Request a Plan change"}));
    const send = within(conversation).getByRole("button", {name: "Propose edit"});
    await waitFor(() => expect(send).toBeEnabled());
    fireEvent.click(send);
    await waitFor(() => expect(current.post).toHaveBeenCalledTimes(1));
    await screen.findByText("Reply details contained an invalid Graph-context receipt. The saved message and page suggestion were kept.");
    expect(returnedOrigin).toBe(foreignKey);
    const request = current.post.mock.calls[0]![0];
    expect(request.plan_requested_operation).toBe("write_current_page");
    expect(request.plan_authoring_capture!.idempotency_key).not.toBe(foreignKey);
    expect(request.plan_authoring_capture).toMatchObject({world_id: worldId, document_id: documentId, base_revision: 7});
    expect(screen.queryByRole("textbox", {name: "Suggestion text"})).not.toBeInTheDocument();
    expect(screen.queryByRole("region", {name: "Suggestion review"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Save", exact: true})).not.toBeInTheDocument();
    expect(editor.getJSON()).toEqual(before);
    expect(surface).not.toHaveTextContent("FOREIGN-ACTION-REPLACEMENT");
    expect(current.readSaved().markdown).toBe(initialMarkdown);
    expect(current.readSaved().record.revision).toBe(7);
    expect(current.readReview()).toBeNull();
    expect(current.commands).not.toHaveBeenCalled();
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
    expect(current.legacyProposal).not.toHaveBeenCalled();
    expect(current.post).toHaveBeenCalledTimes(1);
  } finally {
    view.unmount();
    vi.unstubAllGlobals();
    sessionStorage.clear();
  }
});

it("rejects a conversation switch during deferred native Save without changing the mounted editor", async () => {
  setupWorldApi();
  const current = setupPlanAuthoringIntegration(planRecord(), initialMarkdown, "A lantern glows under the arch.");
  const nextConversation = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb";
  let switched = false;
  let freshPointerReads = 0;
  const messages = vi.mocked(conversationLibrary.readActiveConversationMessages);
  const readMessages = messages.getMockImplementation()!;
  messages.mockImplementation(async (...args) => {
    const page = await readMessages(...args);
    if (!switched) return page;
    freshPointerReads += 1;
    return {...page, conversation_id: nextConversation, active_conversation_id: nextConversation,
      pointer_revision: 5, messages: [], next_before_sequence: null};
  });
  const history = vi.mocked(liveApi.getWorldAgentConversationHistory);
  const readHistory = history.getMockImplementation()!;
  history.mockImplementation(async (...args) => {
    const page = await readHistory(...args);
    return switched ? {...page, conversation_id: nextConversation, active_conversation_id: nextConversation,
      pointer_revision: 5, turns: [], next_before_sequence: null} : page;
  });
  const actions = vi.mocked(liveApi.getWorldPlanConversationActions);
  const readActions = actions.getMockImplementation()!;
  actions.mockImplementation(async (...args) => {
    expect(args[0]).toBe(worldId);
    if (args[1] !== nextConversation) return readActions(...args);
    expect(switched).toBe(true);
    return {schema_version: "dmb_world_plan_action_conversation_projection_v1", world_id: worldId,
      conversation_id: nextConversation, actions: [], next_before_action_sequence: null};
  });
  const reset = vi.spyOn(liveApi, "postWorldAgentNewConversation").mockImplementation(async (world, command) => {
    expect(world).toBe(worldId);
    expect(command).toMatchObject({expected_pointer_revision: 4,
      expected_active_conversation_id: "11111111-1111-4111-8111-111111111111"});
    switched = true;
    return {schema: "dmb_agent_new_conversation_response_v1", world_id: worldId,
      conversation_id: nextConversation, active_conversation_id: nextConversation, pointer_revision: 5};
  });
  const nativeNavigator = navigator;
  vi.stubGlobal("navigator", new Proxy(nativeNavigator, {
    get: (target, key) => key === "locks"
      ? { request: async (_name: string, work: () => unknown) => work() }
      : Reflect.get(target, key, target),
  }));
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><CurrentIntegrationPage /></SelectedWorldProvider></StrictMode>);
  let release!: () => void;
  const gate = new Promise<void>(resolve => { release = resolve; });
  try {
    const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const editor = (surface.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
    const before = editor.getJSON();
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    const conversation = await screen.findByRole("region", {name: "World conversation"});
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"})).toHaveAttribute("aria-busy", "false"));
    fireEvent.change(within(conversation).getByLabelText("Message DungeonBuddy"), {target: {value: "Add a lantern."}});
    fireEvent.click(within(conversation).getByText(/^(Automatic|Plan change) · Change$/));
    fireEvent.click(within(conversation).getByRole("button", {name: "Request a Plan change"}));
    const send = within(conversation).getByRole("button", {name: "Propose edit"});
    await waitFor(() => expect(send).toBeEnabled());
    fireEvent.click(send);
    await screen.findByRole("textbox", {name: "Suggestion text"});
    const save = within(screen.getByRole("region", {name: "Suggestion review"})).getByRole("button", {name: "Save", exact: true});
    await waitFor(() => expect(save).toBeEnabled());
    const realRestore = planEdit.restorePlanAuthoringTarget;
    const restore = vi.spyOn(planEdit, "restorePlanAuthoringTarget").mockImplementationOnce(async (...args) => {
      await gate;
      return realRestore(...args);
    });
    fireEvent.click(save);
    await waitFor(() => expect(restore).toHaveBeenCalledTimes(1));
    const pendingRestore = restore.mock.results[0]!.value;
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    expect(screen.getByRole("region", {name: "World conversation"})).toBeVisible();
    const newConversation = screen.getByRole("button", {name: "New conversation", exact: true});
    await waitFor(() => expect(newConversation).toBeEnabled());
    fireEvent.click(newConversation);
    await waitFor(() => expect(reset).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(freshPointerReads).toBeGreaterThan(0));
    await waitFor(() => expect(screen.queryByRole("region", {name: "Suggestion review"})).not.toBeInTheDocument());
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"})).toHaveAttribute("aria-busy", "false"));
    await act(async () => {
      release();
      await pendingRestore.catch((error: unknown) => expect(error).toBeInstanceOf(planEdit.PlanEditGuardError));
    });
    expect(editor.getJSON()).toEqual(before);
    expect(editor.state.doc.textBetween(0, editor.state.doc.content.size, "")).not.toContain("A lantern glows under the arch.");
    expect(screen.queryByRole("region", {name: "Suggestion review"})).not.toBeInTheDocument();
    expect(current.readSaved().markdown).toBe(initialMarkdown);
    expect(current.readSaved().record.revision).toBe(7);
    expect(current.commands.mock.calls.map(call => call[2].operation)).toEqual(["open"]);
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
    expect(current.legacyProposal).not.toHaveBeenCalled();
    expect(current.post).toHaveBeenCalledTimes(1);
  } finally {
    release();
    view.unmount();
    vi.unstubAllGlobals();
    sessionStorage.clear();
  }
});

async function currentSceneBodyRoundTrip(
  source: string, sceneId: string, replacement: string, originalBody: string,
  verifySaved: (markdown: string) => void, changeViewDuringSave = false,
) {
  setupWorldApi();
  const current = setupPlanAuthoringIntegration(planRecord(), source, replacement);
  const nativeNavigator = navigator;
  vi.stubGlobal("navigator", new Proxy(nativeNavigator, {
    get: (target, key) => key === "locks"
      ? { request: async (_name: string, work: () => unknown) => work() }
      : Reflect.get(target, key, target),
  }));
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const tree = () => <StrictMode><SelectedWorldProvider locationSnapshot={location}><CurrentIntegrationPage /></SelectedWorldProvider></StrictMode>;
  let view = render(tree());
  try {
    const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const editor = (surface.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
    const before = editor.getJSON();
    const target = await resolvePlayableBodyTarget(editor, {kind: "scene", id: sceneId});
    expect(target.targetBodyMarkdown).toBe(originalBody);
    fireEvent.click(within(screen.getByRole("group", {name: "Plan view"})).getByRole("button", {name: "Cards"}));
    const reader = await screen.findByRole("region", {name: "Focused Plan scene"});
    expect(within(reader).queryByRole("button", {name: "Select for Edit"})).not.toBeInTheDocument();
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    const conversation = await screen.findByRole("region", {name: "World conversation"});
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"})).toHaveAttribute("aria-busy", "false"));
    expect(within(conversation).getByLabelText("Actual Plan change target")).toHaveTextContent(`Replace scene body:`);
    expect(within(conversation).getByLabelText("Actual Plan change target")).toHaveTextContent(sceneId);
    fireEvent.change(within(conversation).getByLabelText("Message DungeonBuddy"), {target: {value: "Add one short GM cue to the current scene while preserving its original text."}});
    fireEvent.click(within(conversation).getByText(/^(Automatic|Plan change) · (Change|Question)$/));
    fireEvent.click(within(conversation).getByRole("button", {name: "Request a Plan change"}));
    const send = within(conversation).getByRole("button", {name: "Propose edit"});
    await waitFor(() => expect(send).toBeEnabled());
    fireEvent.click(send);
    await waitFor(() => expect(current.post).toHaveBeenCalledTimes(1));
    const request = current.post.mock.calls[0]![0];
    expect(request.plan_requested_operation).toBe("write_current_page");
    expect(request.playable_target).toMatchObject({kind: "scene", id: sceneId});
    expect(request.plan_authoring_capture).toMatchObject({world_id: worldId, document_id: documentId,
      base_revision: 7, target_kind: "replace_playable_body", selected_text: "",
      playable_target: {kind: "scene", id: sceneId, marker_grammar_version: "v2", body_markdown: originalBody}});
    expect(JSON.parse(request.plan_authoring_capture!.editor_json)).toEqual(before);
    await screen.findByRole("textbox", {name: "Suggestion text"});
    expect(editor.getJSON()).toEqual(before);
    expect(current.readSaved().markdown).toBe(source);
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(0);
    expect(current.legacyProposal).not.toHaveBeenCalled();
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
    if (changeViewDuringSave) {
      const dispatch = current.commands.getMockImplementation()!;
      current.commands.mockImplementation(async (...args) => {
        const review = await dispatch(...args);
        if (args[2].operation === "prepare") {
          fireEvent.click(within(screen.getByRole("group", {name: "Plan view"})).getByRole("button", {name: "Document", exact: true}));
        }
        return review;
      });
    }
    fireEvent.click(within(screen.getByRole("region", {name: "Suggestion review"})).getByRole("button", {name: "Save", exact: true}));
    if (changeViewDuringSave) {
      await waitFor(() => expect(screen.queryAllByRole("alert").map(element => element.textContent).join(" | ")).toMatch(/differs from its sealed copy|changed/));
      expect(current.commands.mock.calls.some(call => call[2].operation === "prepare")).toBe(true);
      expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(0);
      expect(current.readSaved().markdown).toBe(source);
      expect(current.post).toHaveBeenCalledTimes(1);
      return;
    }
    await waitFor(() => expect(current.readReview()?.state, JSON.stringify({alerts: screen.queryAllByRole("alert").map(element => element.textContent), confirmCount: current.commands.mock.calls.filter(call => call[2].operation === "confirm").length, persistedUnchanged: current.readSaved().markdown === source})).toBe("applied"));
    const saved = current.readSaved();
    expect(saved.record.revision).toBe(8);
    const parsed = markdownToTiptapDoc(saved.markdown);
    expect(parsed.diagnostics.filter(diagnostic => diagnostic.level === "warning")).toEqual([]);
    expect(source.indexOf(originalBody)).toBe(source.lastIndexOf(originalBody));
    const canonicalReplacement = tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(replacement).doc);
    // These fixtures end in the edited scene. Cards retains its two-newline
    // scene separator at EOF; require that exact delimiter, not broad trimming.
    expect(source.endsWith("\n") && !source.endsWith("\n\n")).toBe(true);
    expect(saved.markdown).toBe(source.replace(originalBody, canonicalReplacement) + "\n");
    expect(playableBodyProtectedStructureMatches(before, parsed.doc, target)).toBe(true);
    expect(session29V2Markers(saved.markdown)).toEqual(session29V2Markers(source));
    expect(session29NodeLinks(saved.markdown)).toEqual(session29NodeLinks(source));
    verifySaved(saved.markdown);
    const after = editor.getJSON();
    expect(tiptapJsonToSemanticMarkdown(after)).toBe(tiptapJsonToSemanticMarkdown(parsed.doc));
    const savedTarget = await resolvePlayableBodyTarget(editor, {kind: "scene", id: sceneId});
    expect(savedTarget.targetBodyMarkdown).toBe(tiptapJsonToSemanticMarkdown(markdownToTiptapDoc(replacement).doc));
    view.unmount();
    window.history.replaceState({}, "", location);
    view = render(tree());
    const reopened = await screen.findByTestId("world-owned-plan-markdown-editor");
    await waitFor(() => expect((reopened.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor.getJSON()).toEqual(after));
    expect(current.post).toHaveBeenCalledTimes(1);
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(1);
    expect(current.ordinaryPrepare).not.toHaveBeenCalled();
    expect(current.ordinaryCommit).not.toHaveBeenCalled();
  } finally {
    view.unmount();
    vi.unstubAllGlobals();
    sessionStorage.clear();
  }
}

it("saves a reviewed focused Scene body without changing surrounding Plan content", async () => {
  await currentSceneBodyRoundTrip(protectedScenePlanMarkdown, "scene:dogfood-smoke",
    "A clearly synthetic scene used only to verify the local Plan-to-Play path. No campaign canon.\n\nGM note: Pause here and invite the players to choose their next action.",
    "A clearly synthetic scene used only to verify the local Plan-to-Play path. No campaign canon.\n",
    markdown => {
      expect(markdown).toContain("DOGFOOD REVISION CHECK — saved for source pin verification.");
      expect(markdown).toContain("The air carries a cool, earthy scent of damp stone, like a cellar after rain.");
      expect(markdown).toContain("- Continue the smoke test.");
    });
});

it("saves a reviewed focused Scene edit with a protected multi-paragraph sibling Option", async () => {
  await currentSceneBodyRoundTrip(multiParagraphProtectedScenePlanMarkdown, "scene:smoke",
    "Scene body.\n\nGM note: Pause here for the players to choose their next action.", "Scene body.\n",
    markdown => {
      const doc = markdownToTiptapDoc(markdown).doc;
      const list = doc.content?.find(node => node.type === "bulletList");
      expect(list?.content?.[0]?.content).toHaveLength(3);
      expect(markdown).toContain("First option paragraph with [the guide](dmb-node:node:guide).");
      expect(markdown).toContain("Second option paragraph.");
    });
});

it("refuses a Cards view change after preparation before confirming a Scene Save", async () => {
  await currentSceneBodyRoundTrip(protectedScenePlanMarkdown, "scene:dogfood-smoke",
    "A clearly synthetic scene used only to verify the local Plan-to-Play path. No campaign canon.\n\nOne reviewed cue.",
    "A clearly synthetic scene used only to verify the local Plan-to-Play path. No campaign canon.\n",
    () => {}, true);
});

it("drops a delayed card-body proposal after a new Option target is selected", async () => {
  savedMarkdown = v2OptionPlanMarkdown;
  setupWorldApi();
  let release!: (value: WorldPlanDocumentEditProposalResponse) => void;
  const pending = new Promise<WorldPlanDocumentEditProposalResponse>((resolve) => { release = resolve; });
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockReturnValue(pending);
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(editorSurface).toHaveTextContent("Wait by the gate."));
  const originalEditorText = editorSurface.textContent;
  fireEvent.click(await screen.findByRole("button", { name: "Cards" }));
  const cards = screen.getByTestId("world-plan-cards");
  const exploreCard = cards.querySelector('[data-element-id="option:explore"]');
  const waitCard = cards.querySelector('[data-element-id="option:wait"]');
  expect(exploreCard).not.toBeNull();
  expect(waitCard).not.toBeNull();
  fireEvent.click(within(exploreCard as HTMLElement).getByRole("button", { name: "Select for Edit" }));
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Guide Aldric through the gate quietly." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  const request = proposal.mock.calls[0]?.[0];
  expect(request).toMatchObject({
    target_kind: "replace_playable_body",
    playable_target: { kind: "option", id: "option:explore" },
  });

  fireEvent.click(within(waitCard as HTMLElement).getByRole("button", { name: "Select for Edit" }));
  await waitFor(() => expect(screen.getByRole("group", { name: "Selected Playable card for edit" })).toHaveTextContent("option:wait"));
  await act(async () => {
    release(v2OptionProposalResponse(request!, "00000000-0000-4000-8000-000000000041", "A quiet guide leads the way."));
    await pending;
  });

  expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
  expect(editorSurface.textContent).toBe(originalEditorText);
  expect(savedMarkdown).toBe(v2OptionPlanMarkdown);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  view.unmount();
});

it("drops a late same-card response when a newer capture is current", async () => {
  savedMarkdown = v2OptionPlanMarkdown;
  setupWorldApi();
  let releaseFirst!: (value: WorldPlanDocumentEditProposalResponse) => void;
  let releaseSecond!: (value: WorldPlanDocumentEditProposalResponse) => void;
  const firstPending = new Promise<WorldPlanDocumentEditProposalResponse>((resolve) => { releaseFirst = resolve; });
  const secondPending = new Promise<WorldPlanDocumentEditProposalResponse>((resolve) => { releaseSecond = resolve; });
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal")
    .mockImplementationOnce(() => firstPending)
    .mockImplementationOnce(() => secondPending);
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(editorSurface).toHaveTextContent("Wait by the gate."));
  const originalEditorText = editorSurface.textContent;
  fireEvent.click(await screen.findByRole("button", { name: "Cards" }));
  const cards = screen.getByTestId("world-plan-cards");
  const exploreCard = cards.querySelector('[data-element-id="option:explore"]');
  expect(exploreCard).not.toBeNull();
  fireEvent.click(within(exploreCard as HTMLElement).getByRole("button", { name: "Select for Edit" }));
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Add the stale guide response." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  const firstRequest = proposal.mock.calls[0]?.[0];
  expect(firstRequest).toMatchObject({
    target_kind: "replace_playable_body",
    playable_target: { kind: "option", id: "option:explore" },
  });

  fireEvent.click(within(exploreCard as HTMLElement).getByRole("button", { name: "Selected for Edit" }));
  await waitFor(() => expect(screen.getByLabelText("Message DungeonBuddy")).not.toBeDisabled());
  fireEvent.change(screen.getByLabelText("Message DungeonBuddy"), {
    target: { value: "Use the newer guide response." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(2));
  const secondRequest = proposal.mock.calls[1]?.[0];
  expect(secondRequest).toMatchObject({
    target_kind: "replace_playable_body",
    playable_target: { kind: "option", id: "option:explore" },
    instruction: "Use the newer guide response.",
  });
  expect(secondRequest?.idempotency_key).not.toBe(firstRequest?.idempotency_key);

  await act(async () => {
    releaseFirst(v2OptionProposalResponse(firstRequest!, "00000000-0000-4000-8000-000000000043", "A stale guide leads [Aldric](dmb-node:node:captain-lysandra-ironveil) forward."));
    await firstPending;
  });
  expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Message DungeonBuddy")).toHaveValue("Use the newer guide response.");
  expect(editorSurface.textContent).toBe(originalEditorText);
  expect(savedMarkdown).toBe(v2OptionPlanMarkdown);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  await act(async () => {
    releaseSecond(v2OptionProposalResponse(secondRequest!, "00000000-0000-4000-8000-000000000044", "A fresh guide leads [Aldric](dmb-node:node:captain-lysandra-ironveil) forward."));
    await secondPending;
  });
  const review = await screen.findByRole("region", { name: "Review proposed Plan edit" });
  expect(review).toHaveTextContent("A fresh guide leads");
  expect(review).not.toHaveTextContent("A stale guide leads");
  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => {
    expect(editorSurface).toHaveTextContent("A fresh guide leads");
    expect(editorSurface).not.toHaveTextContent("A stale guide leads");
  });
  expect(savedMarkdown).toBe(v2OptionPlanMarkdown);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  view.unmount();
});

it("refuses card-body Apply when the selected target changes during recapture", async () => {
  savedMarkdown = v2OptionPlanMarkdown;
  setupWorldApi();
  const proposal = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) =>
    v2OptionProposalResponse(request, "00000000-0000-4000-8000-000000000042", "Wait while the guide distracts the guard."));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><IntegrationPage /></SelectedWorldProvider></StrictMode>);
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(editorSurface).toHaveTextContent("Wait by the gate."));
  const originalEditorText = editorSurface.textContent;
  fireEvent.click(await screen.findByRole("button", { name: "Cards" }));
  const cards = screen.getByTestId("world-plan-cards");
  const exploreCard = cards.querySelector('[data-element-id="option:explore"]');
  const waitCard = cards.querySelector('[data-element-id="option:wait"]');
  expect(exploreCard).not.toBeNull();
  expect(waitCard).not.toBeNull();
  fireEvent.click(within(waitCard as HTMLElement).getByRole("button", { name: "Select for Edit" }));
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(screen.getByRole("radio", { name: "Propose edit" }));
  fireEvent.change(await screen.findByLabelText("Message DungeonBuddy"), {
    target: { value: "Wait while the guide creates a distraction." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(proposal).toHaveBeenCalledTimes(1));
  expect(proposal.mock.calls[0]?.[0]).toMatchObject({
    target_kind: "replace_playable_body",
    playable_target: { kind: "option", id: "option:wait" },
  });
  await screen.findByRole("region", { name: "Review proposed Plan edit" });
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  const originalDigest = crypto.subtle.digest.bind(crypto.subtle);
  let releaseDigest!: () => void;
  const digestGate = new Promise<void>((resolve) => { releaseDigest = resolve; });
  const digest = vi.spyOn(crypto.subtle, "digest").mockImplementationOnce(async (...args) => {
    await digestGate;
    return originalDigest(...args);
  });
  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => expect(digest).toHaveBeenCalledTimes(1));
  fireEvent.click(within(exploreCard as HTMLElement).getByRole("button", { name: "Select for Edit" }));
  await waitFor(() => expect(screen.getByRole("group", { name: "Selected Playable card for edit" })).toHaveTextContent("option:explore"));
  await act(async () => { releaseDigest(); });

  expect(await screen.findByRole("alert")).toHaveTextContent("changed while capturing the target");
  expect(screen.queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Apply changes" })).not.toBeInTheDocument();
  expect(editorSurface.textContent).toBe(originalEditorText);
  expect(editorSurface).not.toHaveTextContent("Wait while the guide distracts the guard.");
  expect(savedMarkdown).toBe(v2OptionPlanMarkdown);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  view.unmount();
});

it("edits one selected Option body, keeps Apply draft-only, then saves and freshly reopens the same Plan", async () => {
  savedMarkdown = v2OptionPlanMarkdown;
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
  expect(screen.getByRole("region", { name: "Review proposed Plan edit" })).toHaveTextContent(replacement);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "Apply changes" }));
  await waitFor(() => {
    expect(editorSurface).toHaveTextContent("Quietly guide");
    expect(editorSurface).toHaveTextContent("through the gate.");
  });
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
  await waitFor(() => {
    expect(reopened).toHaveTextContent("Quietly guide");
    expect(reopened).toHaveTextContent("through the gate.");
  });
  expect(reopened).toHaveTextContent("Wait by the gate.");
});

it("keeps a native Plan suggestion read-only in Play and reviewable after returning", async () => {
  setupWorldApi();
  const source = "Opening image: three lantern flashes ripple across the eastern ridge.\n";
  const current = setupPlanAuthoringIntegration(planRecord(), source, "A lone watcher keeps vigil.");
  const nativeNavigator = navigator;
  vi.stubGlobal("navigator", new Proxy(nativeNavigator, {get: (target, key) => key === "locks"
    ? {request: async (_name: string, work: () => unknown) => work()} : Reflect.get(target, key, target)}));
  const location = `/plan?world=${worldId}&documentId=${documentId}`;
  window.history.replaceState({}, "", location);
  const view = render(<StrictMode><SelectedWorldProvider locationSnapshot={location}><SwitchableNativeIntegrationPage /></SelectedWorldProvider></StrictMode>);
  try {
    const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
    const editor = (surface.querySelector(".ProseMirror") as HTMLElement & {editor: Editor}).editor;
    act(() => editor.commands.setTextSelection(15));
    const before = editor.getJSON();
    fireEvent.click(await screen.findByRole("button", {name: "Open", exact: true}));
    const conversation = await screen.findByRole("region", {name: "World conversation"});
    await waitFor(() => expect(within(conversation).getByRole("region", {name: "World conversation transcript"})).toHaveAttribute("aria-busy", "false"));
    fireEvent.change(within(conversation).getByLabelText("Message DungeonBuddy"), {target: {value: "Add a watcher to the Plan."}});
    fireEvent.click(within(conversation).getByText(/^(Automatic|Plan change) · Change$/));
    fireEvent.click(within(conversation).getByRole("button", {name: "Request a Plan change"}));
    const propose = within(conversation).getByRole("button", {name: "Propose edit"});
    await waitFor(() => expect(propose).toBeEnabled());
    fireEvent.click(propose);
    await screen.findByRole("textbox", {name: "Suggestion text"});
    expect(editor.getJSON()).toEqual(before);
    expect(current.readSaved().markdown).toBe(source);
    fireEvent.click(screen.getByRole("button", {name: "Switch surface"}));
    fireEvent.click((await screen.findAllByRole("button", {name: "Open", exact: true}))[0]!);
    await screen.findByText("Add a watcher to the Plan.");
    expect(await screen.findByText("Open the suggestion’s original page to review it.")).toBeVisible();
    expect(screen.queryByRole("textbox", {name: "Suggestion text"})).not.toBeInTheDocument();
    expect(screen.queryByRole("button", {name: "Save", exact: true})).not.toBeInTheDocument();
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(0);
    expect(current.readSaved().markdown).toBe(source);
    fireEvent.click(screen.getByRole("button", {name: "Switch surface"}));
    await screen.findByTestId("world-owned-plan-markdown-editor");
    const review = await screen.findByRole("region", {name: "Suggestion review"});
    fireEvent.click(within(review).getByRole("button", {name: "Save", exact: true}));
    await waitFor(() => expect(current.readReview()?.state).toBe("applied"));
    expect(current.readSaved().markdown).toContain("A lone watcher keeps vigil.");
    expect(current.commands.mock.calls.filter(call => call[2].operation === "confirm")).toHaveLength(1);
  } finally {
    view.unmount();
    vi.unstubAllGlobals();
    sessionStorage.clear();
  }
});
