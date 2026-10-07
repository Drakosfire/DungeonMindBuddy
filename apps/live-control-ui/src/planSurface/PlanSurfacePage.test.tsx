import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { StrictMode, type ReactElement, type ReactNode } from "react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import type { AgentInteractionTrace, WorldOwnedCommittedRevisionV2, WorldOwnedPlanRecordV2, WorldAgentConversationHistoryTurnV1 } from "../api/types";
import { PlanSurfacePage } from "./PlanSurfacePage";
import { WorldGraphLensProvider } from "../graphLens/WorldGraphLensContext";
import { WorldGraphLensProjectionProvider } from "../graphLens/useWorldGraphLensProjection";
import { AgentInteractionProvider, useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { AgentInteractionChrome } from "../agentInteraction/AgentInteractionChrome";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import type { WorldPlanAgentTurnRequestV1, WorldPlanAgentTurnResponseV1 } from "../api/types";
import {
  activeThreadStorageKey,
  createAgentInteractionThread,
  loadAgentThreadById,
  persistAgentThread,
  threadIndexStorageKey,
  threadStorageKey,
} from "../agentInteraction/agentInteractionStorage";

const chromeCapture = vi.hoisted(() => ({ editorTools: null as unknown }));

vi.mock("../chrome/AppChrome", async () => {
  const { SurfaceContextHost, SurfaceContextProvider, useSurfaceContext } = await import("../surfaceInteraction/contextHost");
  function ContextIdentityProbe() {
    const { contributions } = useSurfaceContext();
    return <output data-testid="world-plan-context-identity">{contributions["plan-world-context"]?.surfaceIdentity.instanceKey ?? "none"}</output>;
  }
  return {
    AppChrome: ({ children, editorTools }: {
      children: ReactNode;
      editorTools?: { tools?: { sections?: Array<{ id: string; panel?: ReactNode; actions: Array<{ id: string; label: string; onClick: () => void; disabled?: boolean }> }> } } | null;
    }) => {
      chromeCapture.editorTools = editorTools;
      return (
        <SurfaceContextProvider>
          <div>
            <SurfaceContextHost />
            <ContextIdentityProbe />
            {editorTools?.tools?.sections?.map((section) => <div key={section.id}>
              {section.panel}
              {section.actions.map((action) => (
                <button key={`${section.id}:${action.id}`} type="button" onClick={action.onClick} disabled={action.disabled}>{action.label}</button>
              ))}
            </div>)}
            {children}
          </div>
        </SurfaceContextProvider>
      );
    },
  };
});
vi.mock("./PlanSurfaceShell", () => ({
  PlanSurfaceShell: ({ planView }: { planView: { campaign_id: string } }) => (
    <div data-testid="plan-page-campaign">{planView.campaign_id}</div>
  ),
}));

const worldId = "of-conks-cons-demo";

function capturedPlanControls() {
  const tools = chromeCapture.editorTools as {
    tools: { sections: Array<{
      id: string;
      panel?: ReactNode;
      actions: Array<{ label: string; onClick: () => void }>;
    }> };
  };
  const document = tools.tools.sections.find((section) => section.id === "world-plan-document")!;
  const input = (document.panel as ReactElement<{
    children: [string, ReactElement<{ onChange: (event: { target: { value: string } }) => void }>];
  }>).props.children[1];
  return {
    changeTitle: input.props.onChange,
    save: document.actions.find((action) => action.label === "Save Plan")!.onClick,
    bold: tools.tools.sections.flatMap((section) => section.actions).find((action) => action.label === "Bold")!.onClick,
  };
}

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
  return selected.kind === "managed" ? (
    <AgentInteractionProvider>
      <PlanSurfacePage />
      <PublicationProbe />
    </AgentInteractionProvider>
  ) : <span>{selected.kind}</span>;
}

function AgentEnabledPlanPage() {
  const selected = useSelectedWorld();
  return selected.kind === "managed" ? (
    <AgentInteractionProvider>
      <AskPluginSlotProvider>
        <PlanSurfacePage />
        <AgentInteractionChrome />
      </AskPluginSlotProvider>
    </AgentInteractionProvider>
  ) : <span>{selected.kind}</span>;
}

function GraphEnabledAgentPlanPage({ owner }: { owner: string }) {
  return (
    <WorldGraphLensProvider planCampaignId={owner} managedWorldId={owner} focusOptions={[]}>
      <WorldGraphLensProjectionProvider defaultCampaignId={owner}>
        <AgentEnabledPlanPage />
      </WorldGraphLensProjectionProvider>
    </WorldGraphLensProvider>
  );
}

function savedWorldPlanConversation() {
  return screen.getByRole("region", { name: "Saved World Plan conversation" });
}

function messageDungeonBuddyField(conversation = savedWorldPlanConversation()) {
  return within(conversation).getByLabelText("Message DungeonBuddy");
}

function sendDiscussMessage(conversation = savedWorldPlanConversation()) {
  const discussIntent = within(conversation).queryByRole("radio", { name: "Discuss" });
  if (discussIntent) expect(discussIntent).toBeChecked();
  fireEvent.click(within(conversation).getByRole("button", { name: "Send message" }));
}

function openAdvancedDetails(conversation = savedWorldPlanConversation()) {
  fireEvent.click(within(conversation).getByText("Advanced details"));
}

const savedAgentPlanId = "saved-plan-agent-test";
const savedAgentPlanText = "# Private Plan prose\nThe keeper waits beneath the black arch.\n";
const twoScenePlanMarkdown = [
  "# Saved Plan",
  "",
  "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
  "## Arrival",
  "The keeper waits beneath the black arch.",
  "<!-- dmb-playable-element:v1 kind=scene id=scene:warehouse -->",
  "## Warehouse",
  "A lantern moves behind the loading door.",
].join("\n") + "\n";

function planAgentNamespace(documentId = savedAgentPlanId) {
  return `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
}

function mockSavedPlanForAgent(
  documentId = savedAgentPlanId,
  revision = 7,
  committedObjectRevision = revision,
  markdown = savedAgentPlanText,
  ownerWorldId = worldId,
) {
  window.history.replaceState({}, "", `/plan?world=${ownerWorldId}&documentId=${documentId}`);
  const record = worldPlanRecord(documentId, ownerWorldId, revision);
  record.title = "Of Conks Session Plan";
  record.target_relpath = `out/workspace/plan/${documentId}.md`;
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockResolvedValue(record);
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(ownerWorldId));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{
      schema_version: "dmb_world_container_record_v1",
      world_id: ownerWorldId,
      name: "Of Conks",
      source_root_relpath: "corpus/of-conks-cons-demo-markdown",
      created_at: "2026-01-01T00:00:00Z",
    }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: ownerWorldId,
    records: [record],
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record,
    markdown,
    content_sha256: "b".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: revision,
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision").mockResolvedValue({
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: ownerWorldId,
    campaign_id: null,
    document_id: documentId,
    kind: "plan",
    title: "Of Conks Session Plan",
    status: "active",
    object_revision: committedObjectRevision,
    work_revision_id: "work-revision-plan-4",
    revision_n: 4,
    markdown,
    content_sha256: "b".repeat(64),
    has_divergent_working_copy: true,
    target_relpath: record.target_relpath,
  } satisfies WorldOwnedCommittedRevisionV2);
  return record;
}

const graphActivationMarkdown = [
  "# Saved Plan",
  "",
  "<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->",
  "## Arrival",
  "Read [Ironveil Warehouse](dmb-node:loc:ironveil-warehouse) before entering.",
].join("\n") + "\n";

function managedGraphProjectionFixture() {
  const node = {
    nodeId: "loc:ironveil-warehouse",
    label: "Ironveil Warehouse",
    kind: "Location",
    role: "location",
    aliases: [],
    sourceDomains: [],
    anchoredToFocusSession: false,
    evidenceBadges: [],
    adjacency: [],
    suggestedExpansions: [],
    evidenceRefIds: [],
    sourceArtifactIds: [],
  };
  const snapshot = {
    worldId: "eldyrwild",
    campaignId: "",
    revisionId: "managed-head-3",
    headRevisionId: "managed-head-3",
    isHead: true,
    focus: { kind: "none" as const },
    admissibility: "gm" as const,
    scopeMode: "world" as const,
  };
  return {
    schema: "dmb_managed_world_graph_projection_v1" as const,
    managedWorldId: "elderwyld",
    nativeWorldId: "eldyrwild",
    bindingVersion: 1,
    projection: {
      schema: "dmb_world_graph_projection_v1" as const,
      snapshot,
      summary: { nodeCount: 1, relationshipCount: 0, attributeCount: 0, evidenceCount: 0, sourceArtifactCount: 0, projectionTruncated: false },
      nodes: [node], relationships: [], attributes: [], evidence: [], sourceArtifacts: [], diagnostics: [],
    },
  };
}

let serverHistoryTurns: WorldAgentConversationHistoryTurnV1[] = [];

function worldPlanAgentResponse(request: WorldPlanAgentTurnRequestV1): WorldPlanAgentTurnResponseV1 {
  serverHistoryTurns.push({
    turn_id: request.turn_id, sequence: serverHistoryTurns.length + 1,
    lifecycle_status: "completed", user_text: request.message,
    assistant_text: "The keeper is below the black arch.",
    provenance: {
      world_id: request.owner_scope.world_id, surface_resolution: "resolved",
      surface_id: "plan", surface_instance_id: request.surface.instance_id,
      primary_work: {
        resolution: "resolved", kind: "plan", object_id: request.primary_work.object_id,
        revision: null, content_sha256: request.primary_work.expected_content_sha256,
        object_revision: request.primary_work.expected_revision,
        work_revision_id: "work-revision-plan-4", revision_n: request.primary_work.expected_revision_n,
      },
      supporting_work: request.playable_target ? [{
        resolution: "resolved",
        kind: "dmb_plan_playable_target_v1",
        object_id: request.playable_target.id,
        revision: request.playable_target.id.startsWith("beat:") ? "v2" : "v1",
        content_sha256: null,
        object_revision: null,
        work_revision_id: null,
        revision_n: null,
      }] : [],
      selected_object: {
        resolution: "absent", kind: null, object_id: null, revision: null,
        content_sha256: null, object_revision: null, work_revision_id: null, revision_n: null,
      },
    },
  });
  return {
    schema: "dmb_agent_turn_response_v1",
    client_thread_id: request.client_thread_id,
    turn_id: request.turn_id,
    surface: { surface_id: "plan", instance_id: request.surface.instance_id, status: "resolved" },
    owner_scope: { status: "resolved", kind: "world", owner_id: request.owner_scope.world_id, name: "Of Conks" },
    primary_work: {
      status: "resolved",
      kind: "plan",
      object_id: request.primary_work.object_id,
      revision_used: request.primary_work.expected_revision,
      expected_revision: request.primary_work.expected_revision,
      content_basis: {
        world_id: request.owner_scope.world_id,
        document_id: request.primary_work.object_id,
        object_revision: request.primary_work.expected_revision,
        work_revision_id: "work-revision-plan-4",
        revision_n: request.primary_work.expected_revision_n,
        content_sha256: request.primary_work.expected_content_sha256,
        committed_status: "committed",
        has_divergent_working_copy: true,
      },
    },
    client_work_state_reported: request.client_work_state,
    graph: {
      status: "not_requested",
      world_id: null,
      campaign_id: null,
      scope_mode: null,
      revision_id: null,
      focus: null,
      selection_node_id: null,
      selection_found: null,
      head_revision_id: null,
      is_head: null,
    },
    conversation: {
      client_thread_id: request.client_thread_id,
      turn_id: request.turn_id,
      pointer_status: "absent",
      pointer_id: null,
      conversation_id: "11111111-1111-4111-8111-111111111111",
    },
    answer: {
      status: "ok",
      text: "The keeper is below the black arch.",
      code: null,
      message: null,
      graph_grounded: false,
      trace: { raw_source: "MUST_NOT_BE_PERSISTED" },
    },
  };
}

function PublicationProbe() {
  const { surfaceInteractionBasePublication } = useAgentInteraction();
  const publication = surfaceInteractionBasePublication;
  return (
    <div data-testid="world-plan-publication"
      data-instance-key={publication?.identity.instanceKey ?? "none"}
      data-work-object={publication?.canvas?.workObject ? `${publication.canvas.workObject.kind}:${publication.canvas.workObject.id}` : "none"}
    />
  );
}

beforeEach(() => {
  serverHistoryTurns = [];
  vi.spyOn(liveApi, "getWorldAgentConversationHistory").mockImplementation(async (owner) => ({
    schema: "dmb_agent_conversation_history_v1",
    world_id: owner,
    conversation_state: serverHistoryTurns.length ? "active" : "absent",
    conversation_id: serverHistoryTurns.length ? "11111111-1111-4111-8111-111111111111" : null,
    active_conversation_id: serverHistoryTurns.length ? "11111111-1111-4111-8111-111111111111" : null,
    pointer_revision: serverHistoryTurns.length ? 1 : 0,
    turns: [...serverHistoryTurns],
    next_before_sequence: null,
  }));
  vi.spyOn(liveApi, "getWorldPlanDocumentEditActions").mockImplementation(async (owner, documentId) => {
    const committed = { object_revision: 7, work_revision_id: "work-revision-plan-4", revision_n: 4, content_sha256: "b".repeat(64) };
    return {
      schema_version: "dmb_world_plan_action_projection_v1",
      basis: {
        world_id: owner,
        document_id: documentId,
        object_revision: committed.object_revision,
        work_revision_id: committed.work_revision_id,
        revision_n: committed.revision_n,
        content_sha256: committed.content_sha256,
      },
      actions: [],
    };
  });
});

afterEach(() => {
  liveApi.setNativeGraphAccessToken(null);
  vi.restoreAllMocks();
  localStorage.clear();
  window.history.replaceState({}, "", "/");
  chromeCapture.editorTools = null;
});

it("opens exact managed World Graph references from Document and Cards without changing Plan content", async () => {
  const owner = "elderwyld";
  const record = mockSavedPlanForAgent("saved-plan-graph-activation", 7, 7, graphActivationMarkdown, owner);
  const managedProjection = managedGraphProjectionFixture();
  const projectionRequest = vi.spyOn(liveApi, "postManagedWorldGraphProjection").mockResolvedValue(managedProjection);
  const completeRead = vi.spyOn(liveApi, "postWorldGraphCompleteObject").mockResolvedValue({
    schema: "dmb_world_graph_object_projection_v1",
    found: true,
    completeness: { status: "complete", reason: null, truncatedFields: [] },
    snapshot: managedProjection.projection.snapshot,
    requestedNodeId: "loc:ironveil-warehouse",
    resolvedNodeId: "loc:ironveil-warehouse",
    node: {
      nodeId: "loc:ironveil-warehouse",
      label: "Ironveil Warehouse",
      kind: "location",
      role: "place",
      aliases: ["Warehouse"],
      sourceDomains: ["session_recap"],
      anchoredToFocusSession: false,
      evidenceBadges: [{
        evidenceRefId: "ev:s25",
        sourceArtifactId: "artifact:s25",
        sourceSpanRefId: "span:s25",
        sourceDomain: "session_recap",
        evidenceRole: "supporting",
        isFocusSessionEvidence: false,
        canOpenSource: true,
        canHighlightSpan: false,
        label: "S25 recap passage",
      }],
      adjacency: [],
      suggestedExpansions: [],
      evidenceRefIds: ["ev:s25"],
      sourceArtifactIds: ["artifact:s25"],
    },
    relatedNodes: [],
    semanticFingerprint: "graph-object-fingerprint",
    sourceBindings: [{
      evidence_ref_id: "ev:s25",
      source_artifact_id: "artifact:s25",
      source_revision_id: "artifact-rev:s25",
      content_sha256: "a".repeat(64),
      source_span_ref_id: "span:s25",
      source_domain: "session_recap",
      provenance_status: "excerpt_ready",
      excerpt: "Lysandra led the warehouse watch through the storm.",
    }],
  });
  const save = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${owner}&documentId=${record.document_id}`}>
      <GraphEnabledAgentPlanPage owner={owner} />
    </SelectedWorldProvider>,
  );

  const page = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(projectionRequest).toHaveBeenCalledWith(expect.objectContaining({ managedWorldId: owner })));
  const documentReference = await screen.findByRole("button", { name: "Ironveil Warehouse" });
  documentReference.focus();
  fireEvent.click(documentReference);
  const inspector = await screen.findByRole("dialog", { name: "World Graph object" });
  expect(inspector).toHaveClass("world-plan-graph-reference-inspector");
  const agentConversation = document.querySelector(".world-plan-agent-conversation");
  expect(agentConversation).not.toBeNull();
  expect(inspector).not.toContainElement(agentConversation);
  const conversationText = agentConversation?.textContent;
  await waitFor(() => expect(completeRead).toHaveBeenCalledWith(expect.objectContaining({
    worldId: "eldyrwild", campaignId: "", scopeMode: "world", nodeId: "loc:ironveil-warehouse", revisionPin: "managed-head-3",
  })));
  expect(within(inspector).getByRole("article", { name: "Ironveil Warehouse World Graph object" })).toBeInTheDocument();
  fireEvent.click(await within(inspector).findByRole("button", { name: "Read source" }));
  expect(await screen.findByRole("dialog", { name: "Pinned source passage" })).toBeInTheDocument();
  expect(screen.getByText("Lysandra led the warehouse watch through the storm.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Back to World Graph object" }));
  expect(await screen.findByRole("dialog", { name: "World Graph object" })).toBeInTheDocument();
  expect(document.querySelector(".world-plan-agent-conversation")).toBe(agentConversation);
  expect(agentConversation?.textContent).toBe(conversationText);
  fireEvent.click(within(inspector).getByRole("button", { name: "Close" }));
  await waitFor(() => expect(documentReference).toHaveFocus());

  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const cards = await screen.findByTestId("world-plan-cards");
  expect(cards).toHaveTextContent("Read Ironveil Warehouse before entering.");
  const cardReference = await within(cards).findByRole("button", { name: "Ironveil Warehouse" });
  cardReference.focus();
  fireEvent.click(cardReference);
  const cardInspector = await screen.findByRole("dialog", { name: "World Graph object" });
  await waitFor(() => expect(completeRead).toHaveBeenCalledTimes(2));
  expect(within(cardInspector).getByRole("article", { name: "Ironveil Warehouse World Graph object" })).toBeInTheDocument();
  expect(within(cards).getByText(/before entering\./)).toBeInTheDocument();
  expect(save).not.toHaveBeenCalled();
  expect(prepare).not.toHaveBeenCalled();
});

it("keeps the local blank Plan out of Agent scope until it has been saved", async () => {
  window.history.replaceState({}, "", `/plan?world=${worldId}`);
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
    records: [],
  });
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByTestId("world-plan-context-identity")).not.toHaveTextContent("none"));
  expect(await screen.findByText("Save this Plan to start an Agent conversation.")).toBeInTheDocument();
  expect(screen.queryByTestId("agent-interaction-chrome")).not.toBeInTheDocument();
  expect(postTurn).not.toHaveBeenCalled();
});

it("pins Ask to the exact committed World Plan revision and excludes editor text", async () => {
  mockSavedPlanForAgent();
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => worldPlanAgentResponse(request));
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByRole("region", { name: "Saved World Plan conversation" })).toBeInTheDocument();
  expect(screen.getByText(/Talk through the saved Plan, or choose Propose edit to request a change/)).toBeInTheDocument();

  act(() => capturedPlanControls().changeTitle({ target: { value: "Unsaved local title" } }));
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "What Plan metadata can you see?" } });
  sendDiscussMessage();
  expect(await screen.findByText(/The keeper is below the black arch\./)).toBeInTheDocument();
  expect(serverHistoryTurns[0].provenance.primary_work).toMatchObject({ object_revision: 7, revision_n: 4, content_sha256: "b".repeat(64) });
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "And what is its saved revision?" } });
  sendDiscussMessage();
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.getAllByText(/The keeper is below the black arch\./)).toHaveLength(2));

  const [request, followUpRequest] = postTurn.mock.calls.map(([value]) => value);
  expect(followUpRequest.client_thread_id).not.toBe(request.client_thread_id);
  expect(followUpRequest.turn_id).not.toBe(request.turn_id);
  expect(Object.keys(request).sort()).toEqual([
    "client_thread_id",
    "client_work_state",
    "graph_request",
    "graph_selection",
    "message",
    "owner_scope",
    "primary_work",
    "schema",
    "surface",
    "turn_id",
  ].sort());
  expect(request).toMatchObject({
    schema: "dmb_agent_turn_request_v1",
    surface: { surface_id: "plan", instance_id: screen.getByTestId("world-plan-context-identity").textContent },
    owner_scope: { kind: "world", world_id: worldId },
    primary_work: {
      kind: "plan",
      object_id: savedAgentPlanId,
      expected_revision: 7,
      expected_revision_n: 4,
      expected_content_sha256: "b".repeat(64),
    },
    client_work_state: "saved_dirty",
    graph_request: { mode: "none" },
    graph_selection: null,
    message: "What Plan metadata can you see?",
  });
  expect(JSON.stringify(request)).not.toContain(savedAgentPlanText);
  expect(JSON.stringify(request)).not.toContain("Of Conks Session Plan");
  expect(JSON.stringify(request)).not.toContain(`out/workspace/plan/${savedAgentPlanId}.md`);
  expect(JSON.stringify(request)).not.toContain(planAgentNamespace());

  expect(serverHistoryTurns).toHaveLength(2);
  const conversation = screen.getByRole("region", { name: "Saved World Plan conversation" });
  const renderedTurns = [...conversation.querySelectorAll("article[data-sequence]")];
  expect(renderedTurns.map((turn) => turn.getAttribute("data-sequence"))).toEqual(["1", "2"]);
  expect(renderedTurns[0]).toHaveTextContent("What Plan metadata can you see?");
  expect(renderedTurns[1]).toHaveTextContent("And what is its saved revision?");
  expect(renderedTurns.every((turn) => turn.textContent?.includes(`plan ${savedAgentPlanId} · revision 4`))).toBe(true);
  expect(liveApi.getWorldAgentConversationHistory).toHaveBeenCalledWith(worldId, { limit: 50, includeTurnCorrelation: true });
  expect(liveApi.getWorldOwnedPlanCommittedRevision).toHaveBeenCalledTimes(2);
  expect(serverHistoryTurns.map((turn) => turn.user_text)).toEqual([
    "What Plan metadata can you see?", "And what is its saved revision?",
  ]);
  expect(serverHistoryTurns.every((turn) => turn.provenance.primary_work.object_id === savedAgentPlanId)).toBe(true);
  expect(localStorage.getItem(threadStorageKey(planAgentNamespace(), request.client_thread_id))).toBeNull();
  expect(JSON.stringify(localStorage)).not.toContain(savedAgentPlanText);
  expect(JSON.stringify(localStorage)).not.toContain("MUST_NOT_BE_PERSISTED");
});

it.each([
  {
    grammar: "v1",
    kind: "scene" as const,
    id: "scene:arrival",
    markdown: "# Saved Plan\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\nThe keeper waits below the arch.\n",
  },
  {
    grammar: "v2",
    kind: "beat" as const,
    id: "beat:arrival",
    markdown: "# Saved Plan\n\n<!-- dmb-playable-element:v2 kind=beat id=beat:arrival beat_kind=spine -->\n## Arrival\nThe keeper waits below the arch.\n<!-- dmb-playable-element:v2 kind=scene id=scene:gate -->\n### Gate\nA guard watches the passage.\n",
  },
])("targets one $grammar committed card and records its immutable basis", async ({ grammar, kind, id, markdown }) => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, markdown);
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => worldPlanAgentResponse(request));
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  const page = await screen.findByTestId("world-owned-plan");
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const cards = await screen.findByTestId("world-plan-cards");
  const cardButtons = within(cards).getAllByRole("button", { name: "Select for Ask" });
  const card = cardButtons.find((button) => button.getAttribute("data-target-id") === id)!;
  await waitFor(() => expect(card).toBeEnabled());
  fireEvent.click(card);

  const conversation = savedWorldPlanConversation();
  expect(within(conversation).getByText(`${kind} · ${id}`)).toBeInTheDocument();
  expect(within(conversation).getByText(/Ask uses the committed Plan revision; unsaved edits are not included/)).toBeInTheDocument();
  act(() => capturedPlanControls().changeTitle({ target: { value: "Unsaved local title" } }));
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What happens at this card?" } });
  sendDiscussMessage(conversation);

  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(1));
  const request = postTurn.mock.calls[0]![0];
  expect(request.playable_target).toEqual({ schema: "dmb_plan_playable_target_v1", kind, id });
  expect(request).toMatchObject({
    primary_work: {
      object_id: savedAgentPlanId,
      expected_revision: 7,
      expected_revision_n: 4,
      expected_content_sha256: "b".repeat(64),
    },
    client_work_state: "saved_dirty",
    graph_request: { mode: "none" },
    graph_selection: null,
  });
  expect(JSON.stringify(request)).not.toContain(markdown);
  expect(JSON.stringify(request)).not.toContain("The keeper waits below the arch.");
  expect(await within(conversation).findByText(new RegExp(`Playable target: ${kind} ${id} · marker grammar ${grammar} · committed Plan ${savedAgentPlanId}`))).toBeInTheDocument();
  expect(within(conversation).getByText(/WorkRevision work-revision-plan-4, revision 4, SHA-256/)).toBeInTheDocument();
});

it("keeps the submitted card identity fixed while selection changes during basis verification", async () => {
  const markdown = "# Saved Plan\n\n<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->\n## Arrival\nThe keeper waits below the arch.\n<!-- dmb-playable-element:v1 kind=choice id=choice:route -->\n### Choose a route\nTwo paths are open.\n";
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, markdown);
  const getCommitted = vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision");
  let releaseBasis!: (basis: WorldOwnedCommittedRevisionV2) => void;
  const pendingBasis = new Promise<WorldOwnedCommittedRevisionV2>((resolve) => { releaseBasis = resolve; });
  getCommitted.mockImplementation(() => pendingBasis);
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => worldPlanAgentResponse(request));
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  const page = await screen.findByTestId("world-owned-plan");
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const cards = await screen.findByTestId("world-plan-cards");
  const selectById = (id: string) => within(cards).getAllByRole("button", { name: /Select for Ask|Selected for Ask/ })
    .find((button) => button.getAttribute("data-target-id") === id)!;
  fireEvent.click(selectById("scene:arrival"));
  const conversation = savedWorldPlanConversation();
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What happens at the arrival?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(getCommitted).toHaveBeenCalledTimes(1));

  fireEvent.click(selectById("choice:route"));
  expect(within(conversation).getByText("choice · choice:route")).toBeInTheDocument();
  await act(async () => releaseBasis({
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    campaign_id: null,
    document_id: savedAgentPlanId,
    kind: "plan",
    title: "Of Conks Session Plan",
    status: "active",
    object_revision: 7,
    work_revision_id: "work-revision-plan-4",
    revision_n: 4,
    markdown,
    content_sha256: "b".repeat(64),
    has_divergent_working_copy: false,
    target_relpath: `out/workspace/plan/${savedAgentPlanId}.md`,
  }));

  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(1));
  expect(postTurn.mock.calls[0]![0].playable_target).toEqual({
    schema: "dmb_plan_playable_target_v1",
    kind: "scene",
    id: "scene:arrival",
  });
  expect(await within(conversation).findByText(/Playable target: scene scene:arrival · marker grammar v1/)).toBeInTheDocument();
});

it("follows focused Scene for a new Ask while a pending Ask and Edit target stay on their original cards", async () => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, twoScenePlanMarkdown);
  const finishTurns: Array<(response: WorldPlanAgentTurnResponseV1) => void> = [];
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(() => (
    new Promise((resolve) => { finishTurns.push(resolve); })
  ));
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  const page = await screen.findByTestId("world-owned-plan");
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  fireEvent.click(within(screen.getByTestId("world-plan-cards")).getByRole("button", { name: "Open scene: Arrival" }));

  const reader = screen.getByTestId("world-plan-scene-reader");
  const conversation = savedWorldPlanConversation();
  expect(await within(conversation).findByRole("group", { name: "Selected Playable card for Ask" })).toHaveTextContent("scene · scene:arrival");
  expect(within(conversation).getByText(/Committed Plan revision 7 · SHA-256/)).toBeInTheDocument();
  fireEvent.click(within(reader).getByRole("button", { name: "Select for Edit" }));
  expect(within(conversation).getByRole("group", { name: "Selected Playable card for edit" })).toHaveTextContent("scene · scene:arrival");

  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What happens at the arrival?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(1));
  const request = postTurn.mock.calls[0]![0];
  expect(request.playable_target).toEqual({ schema: "dmb_plan_playable_target_v1", kind: "scene", id: "scene:arrival" });
  expect(request.primary_work).toMatchObject({ expected_revision: 7, expected_content_sha256: "b".repeat(64) });

  fireEvent.click(within(reader).getByRole("button", { name: "Next scene" }));
  expect(within(savedWorldPlanConversation()).getByRole("group", { name: "Selected Playable card for Ask" })).toHaveTextContent("scene · scene:warehouse");
  expect(within(savedWorldPlanConversation()).getByRole("group", { name: "Selected Playable card for edit" })).toHaveTextContent("scene · scene:arrival");
  expect(postTurn).toHaveBeenCalledTimes(1);

  await act(async () => finishTurns[0]!(worldPlanAgentResponse(request)));
  expect(await within(conversation).findByText(/Playable target: scene scene:arrival · marker grammar v1/)).toBeInTheDocument();
  expect(within(conversation).getByRole("group", { name: "Selected Playable card for Ask" })).toHaveTextContent("scene · scene:warehouse");
  expect(within(conversation).getByRole("group", { name: "Selected Playable card for edit" })).toHaveTextContent("scene · scene:arrival");
  expect(postTurn).toHaveBeenCalledTimes(1);

  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What is happening at the warehouse?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(2));
  const warehouseRequest = postTurn.mock.calls[1]![0];
  expect(warehouseRequest.playable_target).toEqual({ schema: "dmb_plan_playable_target_v1", kind: "scene", id: "scene:warehouse" });
  expect(warehouseRequest.primary_work).toMatchObject({ expected_revision: 7, expected_content_sha256: "b".repeat(64) });
  await act(async () => finishTurns[1]!(worldPlanAgentResponse(warehouseRequest)));
  expect(await within(conversation).findByText(/Playable target: scene scene:warehouse · marker grammar v1/)).toBeInTheDocument();
  expect(postTurn).toHaveBeenCalledTimes(2);
});

it("clears the previous saved Ask target when focus moves to a draft-only Scene", async () => {
  const committedMarkdown = twoScenePlanMarkdown.replace(
    /<!-- dmb-playable-element:v1 kind=scene id=scene:warehouse -->[\s\S]*$/,
    "",
  );
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, committedMarkdown);
  localStorage.setItem(`dmb:world-plan-local-draft:v2:${worldId}`, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: savedAgentPlanId,
    title: "Of Conks Session Plan",
    markdown: twoScenePlanMarkdown,
    revision: 7,
    edit_generation: 1,
  }));
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  const committedRevision = vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  const page = await screen.findByTestId("world-owned-plan");
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(within(page).getByRole("button", { name: "Cards" }));
  const cards = screen.getByTestId("world-plan-cards");
  expect(within(cards).getByText("Draft / unsaved")).toBeInTheDocument();
  fireEvent.click(within(cards).getByRole("button", { name: "Open scene: Arrival" }));
  const reader = screen.getByTestId("world-plan-scene-reader");
  const conversation = savedWorldPlanConversation();
  expect(within(conversation).getByRole("group", { name: "Selected Playable card for Ask" })).toHaveTextContent("scene · scene:arrival");
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "A question not yet sent" } });

  fireEvent.click(within(reader).getByRole("button", { name: "Next scene" }));
  expect(screen.getByTestId("world-plan-scene-reader")).toHaveTextContent("The default Ask card target is cleared");
  expect(within(conversation).queryByRole("group", { name: "Selected Playable card for Ask" })).not.toBeInTheDocument();
  expect(messageDungeonBuddyField(conversation)).toHaveValue("A question not yet sent");
  expect(postTurn).not.toHaveBeenCalled();
  expect(committedRevision).not.toHaveBeenCalled();
  expect(window.location.pathname + window.location.search).toBe(`/plan?world=${worldId}&documentId=${savedAgentPlanId}`);
});

it("connects and revokes the local Agent and Graph session from Settings", async () => {
  mockSavedPlanForAgent();
  const connect = vi.spyOn(liveApi, "connectNativeGraphSession").mockResolvedValue("test-csrf");
  const revoke = vi.spyOn(liveApi, "revokeNativeGraphSession").mockResolvedValue();
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.click(await screen.findByRole("button", { name: "Settings" }));
  expect(screen.queryByLabelText("Local operator credential")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Connect local session" }));
  expect(connect).toHaveBeenCalledOnce();
  expect(await screen.findByText("Local Agent and Graph session active.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Revoke local session" }));
  expect(revoke).toHaveBeenCalledOnce();
  expect(await screen.findByText("Local Agent and Graph session revoked.")).toBeInTheDocument();
});

it("keeps completed server Ask transcripts and provider trace payloads out of browser storage", async () => {
  mockSavedPlanForAgent();
  const requestId = "resp_plan_receipt_1";
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
    const response = worldPlanAgentResponse(request);
    response.answer.trace = {
      schema: "dmb_agent_turn_trace_v1",
      trace_id: "plan-trace-receipt",
      runtime: "process_isolated",
      backend: "hermes",
      mode: "hermes_graph_agent",
      provider: "openai-api",
      model: "gpt-5.4",
      started_at: "2026-09-30T00:00:00Z",
      completed_at: "2026-09-30T00:00:01Z",
      elapsed_ms: 1000,
      status: "ok",
      usage: {
        available: true,
        status: "reported",
        input_tokens: 10,
        output_tokens: 2,
        total_tokens: 12,
      },
      cost: { status: "estimated", usd: 0.000055, priced_call_count: 1, unpriced_call_count: 0 },
      model_calls: [{
        call_id: "call-1",
        runtime_api_request_id: requestId,
        sequence: 1,
        status: "ok",
        provider: "openai-api",
        requested_model: "gpt-5.4",
        response_model: "gpt-5.4",
        duration_ms: 900,
        usage: {
          available: true,
          status: "reported",
          input_tokens: 10,
          output_tokens: 2,
          total_tokens: 12,
        },
        cost: { status: "estimated", usd: 0.000055 },
        request: { body: "RAW_PROMPT_SECRET" },
      }],
      steps: [],
      context_summary: {},
      artifact_refs: [],
      warnings: [],
      prompt_preview: "RAW_PROMPT_SECRET",
      prompt: "RAW_PROMPT_SECRET",
      messages: [{ role: "user", content: "RAW_PROMPT_SECRET" }],
    };
    return response;
  });
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "What trace receipts are available?" } });
  sendDiscussMessage();
  expect(await screen.findByText(/The keeper is below the black arch\./)).toBeInTheDocument();

  const request = postTurn.mock.calls[0][0];
  expect(serverHistoryTurns[0]).toMatchObject({ turn_id: request.turn_id, lifecycle_status: "completed" });
  expect(localStorage.getItem(threadStorageKey(planAgentNamespace(), request.client_thread_id))).toBeNull();
  expect(JSON.stringify(localStorage)).not.toContain(requestId);
  expect(JSON.stringify(localStorage)).not.toContain("RAW_PROMPT_SECRET");
});

it("lets a saved World Plan opt into diagnostics before its first Agent turn", async () => {
  mockSavedPlanForAgent();
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  const conversation = await screen.findByRole("region", { name: "Saved World Plan conversation" });
  openAdvancedDetails(conversation);
  const offButton = within(conversation).getByRole("button", { name: "Show trace details" });
  expect(offButton).toHaveAttribute("aria-pressed", "false");
  expect(localStorage.getItem(activeThreadStorageKey(planAgentNamespace(), "plan", savedAgentPlanId))).toBeNull();

  fireEvent.click(offButton);
  expect(within(conversation).getByRole("button", { name: "Hide trace details" })).toHaveAttribute("aria-pressed", "true");
  const threadId = localStorage.getItem(activeThreadStorageKey(planAgentNamespace(), "plan", savedAgentPlanId));
  expect(threadId).toBeNull();
  expect(postTurn).not.toHaveBeenCalled();
});

it("keeps the trace toggle disabled while the first World Plan Agent turn is pending", async () => {
  mockSavedPlanForAgent();
  let finishTurn: ((response: WorldPlanAgentTurnResponseV1) => void) | undefined;
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation((request) => (
    new Promise((resolve) => {
      finishTurn = resolve;
    })
  ));
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  const conversation = await screen.findByRole("region", { name: "Saved World Plan conversation" });
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What metadata is available?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(1));

  openAdvancedDetails(conversation);
  expect(within(conversation).getByRole("button", { name: "Show trace details" })).toBeDisabled();
  act(() => finishTurn?.(worldPlanAgentResponse(postTurn.mock.calls[0][0])));
  expect(await screen.findByText(/The keeper is below the black arch\./)).toBeInTheDocument();
  expect(within(conversation).getByRole("button", { name: "Show trace details" })).toBeEnabled();
  expect(postTurn).toHaveBeenCalledTimes(1);
});

it("reveals a stored World Plan call mode after rehydrate only when diagnostics are enabled", async () => {
  mockSavedPlanForAgent();
  const thread = createAgentInteractionThread(
    planAgentNamespace(),
    null,
    "plan",
    "hermes",
    "Continuity witness",
    savedAgentPlanId,
  );
  const storedTurnId = "stored-continuity-witness-turn";
  const trace: AgentInteractionTrace = {
    schema: "dmb_agent_turn_trace_v1",
    trace_id: "stored-continuity-witness-trace",
    agent_thread_id: thread.threadId,
    turn_id: storedTurnId,
    runtime: "process_isolated",
    backend: "hermes",
    mode: "hermes_graph_agent",
    provider: "openai-api",
    model: "gpt-6-luna",
    started_at: "2026-10-01T00:00:00.000Z",
    completed_at: "2026-10-01T00:00:01.000Z",
    elapsed_ms: 1000,
    status: "ok",
    usage: {
      available: true,
      status: "reported",
      input_tokens: 528,
      output_tokens: 78,
      total_tokens: 606,
    },
    cost: { status: "unavailable", usd: null },
    model_calls: [{
      call_id: "stored-continuity-witness-call",
      sequence: 1,
      status: "ok",
      provider: "openai-api",
      requested_model: "gpt-6-luna",
      response_model: "gpt-6-luna",
      api_mode: "codex_responses",
      usage: {
        available: true,
        status: "reported",
        input_tokens: 528,
        output_tokens: 78,
        total_tokens: 606,
      },
      cost: { status: "unavailable", usd: null },
    }],
    spans: [],
    steps: [],
    context_summary: {},
    artifact_refs: [],
    warnings: [],
  };
  thread.turns = [{
    turnId: storedTurnId,
    askedAt: "2026-10-01T00:00:00.000Z",
    completedAt: "2026-10-01T00:00:01.000Z",
    question: "For continuity, remember the silver fox chose periwinkle.",
    answer: "Periwinkle",
    backend: "hermes",
    status: "ok",
    trace,
  }];
  persistAgentThread(thread);
  const legacyBytes = localStorage.getItem(threadStorageKey(planAgentNamespace(), thread.threadId));
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  const mountPlan = () => render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  const firstMount = mountPlan();
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  const firstConversation = await screen.findByRole("region", { name: "Saved World Plan conversation" });
  openAdvancedDetails(firstConversation);
  const offButton = within(firstConversation).getByRole("button", { name: "Show trace details" });
  expect(offButton).toHaveAttribute("aria-pressed", "false");
  expect(within(firstConversation).queryByTestId("agent-trace-model-calls")).not.toBeInTheDocument();

  fireEvent.click(offButton);
  const firstCalls = await within(firstConversation).findByTestId("agent-trace-model-calls");
  const firstInspector = firstCalls.closest("details");
  expect(firstInspector).not.toHaveAttribute("open");
  fireEvent.click(within(firstInspector!).getByText("Advanced diagnostics"));
  expect(within(firstInspector!).getByText("API mode")).toBeInTheDocument();
  expect(within(firstInspector!).getByText("codex_responses")).toBeInTheDocument();
  expect(loadAgentThreadById(planAgentNamespace(), thread.threadId)?.uiState?.traceVisible).not.toBe(true);
  expect(localStorage.getItem(threadStorageKey(planAgentNamespace(), thread.threadId))).toBe(legacyBytes);
  expect(postTurn).not.toHaveBeenCalled();

  firstMount.unmount();
  mountPlan();
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  const reloadedConversation = await screen.findByRole("region", { name: "Saved World Plan conversation" });
  openAdvancedDetails(reloadedConversation);
  expect(within(reloadedConversation).getByRole("button", { name: "Show trace details" })).toHaveAttribute("aria-pressed", "false");
  expect(within(reloadedConversation).queryByTestId("agent-trace-model-calls")).not.toBeInTheDocument();
  fireEvent.click(within(reloadedConversation).getByRole("button", { name: "Show trace details" }));
  const reloadedCalls = await within(reloadedConversation).findByTestId("agent-trace-model-calls");
  const reloadedInspector = reloadedCalls.closest("details");
  expect(reloadedInspector).not.toHaveAttribute("open");
  fireEvent.click(within(reloadedInspector!).getByText("Advanced diagnostics"));
  expect(within(reloadedInspector!).getByText("codex_responses")).toBeInTheDocument();
  expect(localStorage.getItem(threadStorageKey(planAgentNamespace(), thread.threadId))).toBe(legacyBytes);
  expect(postTurn).not.toHaveBeenCalled();
});

it("keeps Ask disabled for an unresolved pending write", async () => {
  mockSavedPlanForAgent();
  localStorage.setItem(`dmb:world-plan-local-draft:v2:${worldId}`, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: savedAgentPlanId,
    title: "Of Conks Session Plan",
    markdown: savedAgentPlanText,
    revision: 7,
    edit_generation: 1,
    pending_write: {
      phase: "commit",
      base_revision: 7,
      prepared_revision: 8,
      base_markdown: "# Previous committed Plan\n",
      markdown: savedAgentPlanText,
      edit_generation: 1,
    },
  }));
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByText("Conversation paused while the Plan is saving.")).toBeInTheDocument();
  expect(messageDungeonBuddyField()).toBeDisabled();
  expect(within(screen.getByRole("region", { name: "Saved World Plan conversation" })).getByRole("button", { name: "Saving…" })).toBeDisabled();
  expect(postTurn).not.toHaveBeenCalled();
});

it("isolates Plan conversations when switching saved documents and after reload", async () => {
  const documentA = savedAgentPlanId;
  const documentB = "saved-plan-agent-test-b";
  const recordA = mockSavedPlanForAgent(documentA);
  const recordB = worldPlanRecord(documentB, worldId, 4);
  recordB.title = "Second Of Conks Plan";
  const snapshot = (record: WorldOwnedPlanRecordV2, text: string) => ({
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown: text,
    content_sha256: "d".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: record.revision,
  });
  vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [recordA, recordB],
  });
  vi.mocked(liveApi.getWorkspaceDocumentAny).mockResolvedValue(recordA);
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockImplementation(async (id) =>
    id === documentB ? snapshot(recordB, "# Second Plan text\n") : snapshot(recordA, savedAgentPlanText));

  const makeThread = (documentId: string, answer: string) => {
    const thread = createAgentInteractionThread(
      planAgentNamespace(documentId), null, "plan", "hermes", `${documentId} conversation`, documentId,
    );
    thread.turns = [{
      turnId: `${documentId}-turn`,
      askedAt: "2026-09-30T00:00:00Z",
      completedAt: "2026-09-30T00:00:01Z",
      question: `${documentId} question`,
      answer,
      backend: "hermes",
      status: "ok",
      agentTurnResolved: null,
    }];
    persistAgentThread(thread);
  };
  makeThread(documentA, "Plan A transcript answer");
  makeThread(documentB, "Plan B transcript answer");

  const view = render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentA}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByText("Plan A transcript answer")).toBeInTheDocument();

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentB } });
  expect(await screen.findByText("Plan B transcript answer")).toBeInTheDocument();
  expect(screen.queryByText("Plan A transcript answer")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentA } });
  expect(await screen.findByText("Plan A transcript answer")).toBeInTheDocument();
  expect(screen.queryByText("Plan B transcript answer")).not.toBeInTheDocument();

  view.unmount();
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentA}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByText("Plan A transcript answer")).toBeInTheDocument();
  expect(screen.queryByText("Plan B transcript answer")).not.toBeInTheDocument();
});

it("drops a pending turn when the selected saved Plan changes", async () => {
  const documentA = savedAgentPlanId;
  const documentB = "saved-plan-agent-test-b";
  const recordA = mockSavedPlanForAgent(documentA);
  const recordB = worldPlanRecord(documentB, worldId, 4);
  recordB.title = "Second Of Conks Plan";
  const snapshot = (record: WorldOwnedPlanRecordV2, markdown: string) => ({
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown,
    content_sha256: "e".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: record.revision,
  });
  vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [recordA, recordB],
  });
  vi.mocked(liveApi.getWorkspaceDocumentAny).mockResolvedValue(recordA);
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockImplementation(async (id) =>
    id === documentB ? snapshot(recordB, "# Second Plan text\n") : snapshot(recordA, savedAgentPlanText));
  let resolveTurn!: (value: WorldPlanAgentTurnResponseV1) => void;
  const pendingTurn = new Promise<WorldPlanAgentTurnResponseV1>((resolve) => { resolveTurn = resolve; });
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockReturnValue(pendingTurn);

  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentA}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "This answer belongs only to Plan A." } });
  sendDiscussMessage();
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(1));
  const request = postTurn.mock.calls[0][0];

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentB } });
  expect(await screen.findByText("No messages here yet. Start with a question about the saved Plan.")).toBeInTheDocument();
  await act(async () => resolveTurn(worldPlanAgentResponse(request)));

  expect(screen.queryByText("This answer belongs only to Plan A.")).not.toBeInTheDocument();
  expect(screen.queryByText(/saved Plan title and revision metadata/)).not.toBeInTheDocument();
  expect(localStorage.getItem(threadStorageKey(planAgentNamespace(documentA), request.client_thread_id))).toBeNull();
  expect(localStorage.getItem(activeThreadStorageKey(planAgentNamespace(documentA), "plan", documentA))).toBeNull();
});

it("does not send the prepared revision while its Plan save is still committing", async () => {
  const record = mockSavedPlanForAgent();
  let releasePrepare!: (value: Awaited<ReturnType<typeof liveApi.prepareTiptapMarkdownWrite>>) => void;
  const pendingPrepare = new Promise<Awaited<ReturnType<typeof liveApi.prepareTiptapMarkdownWrite>>>((resolve) => {
    releasePrepare = resolve;
  });
  let releaseCommit!: (value: Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>) => void;
  const pendingCommit = new Promise<Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>>((resolve) => {
    releaseCommit = resolve;
  });
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockReturnValue(pendingPrepare);
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockReturnValue(pendingCommit);
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  expect(await screen.findByLabelText("Message DungeonBuddy")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(prepare).toHaveBeenCalledTimes(1));
  expect(screen.getByText("Conversation paused while the Plan is saving.")).toBeInTheDocument();
  expect(messageDungeonBuddyField()).toBeDisabled();
  expect(within(screen.getByRole("region", { name: "Saved World Plan conversation" })).getByRole("button", { name: "Saving…" })).toBeDisabled();
  expect(postTurn).not.toHaveBeenCalled();

  await act(async () => releasePrepare({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: record.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 8,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "prepared-token",
    warnings: [],
    diagnostics: [],
  }));
  await waitFor(() => expect(commit).toHaveBeenCalledTimes(1));
  expect(messageDungeonBuddyField()).toBeDisabled();
  expect(postTurn).not.toHaveBeenCalled();

  await act(async () => releaseCommit({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: record.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 8,
    committed_revision: 8,
    committed_record: { ...record, revision: 8 },
    normalized_content_sha256: "c".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  }));
  await screen.findByText("Saved to this World.");
});

const invalidWorldPlanResponses: Array<[string, (response: WorldPlanAgentTurnResponseV1) => void]> = [
  ["a different Plan ID", (response) => { response.primary_work.object_id = "another-plan"; }],
  ["a different expected revision", (response) => { response.primary_work.expected_revision = 8; }],
  ["a missing committed content basis", (response) => { response.primary_work.content_basis = null; }],
  ["a different committed World", (response) => { response.primary_work.content_basis!.world_id = "another-world"; }],
  ["a different committed Plan", (response) => { response.primary_work.content_basis!.document_id = "another-plan"; }],
  ["a different committed object revision", (response) => { response.primary_work.content_basis!.object_revision += 1; }],
  ["a different committed revision number", (response) => { response.primary_work.content_basis!.revision_n += 1; }],
  ["a different committed digest", (response) => { response.primary_work.content_basis!.content_sha256 = "c".repeat(64); }],
  ["a contradictory used revision", (response) => { response.primary_work.revision_used = 8; }],
  ["a different top-level thread ID", (response) => { response.client_thread_id = "another-thread"; }],
  ["a different nested thread ID", (response) => { response.conversation.client_thread_id = "another-thread"; }],
  ["a different top-level turn ID", (response) => { response.turn_id = "another-turn"; }],
  ["a different nested turn ID", (response) => { response.conversation.turn_id = "another-turn"; }],
  ["a different surface instance", (response) => { response.surface.instance_id = "another-surface"; }],
  ["a rejected surface paired with a valid answer", (response) => { response.surface.status = "rejected"; }],
  ["an unavailable surface paired with a valid answer", (response) => { response.surface.status = "unavailable"; }],
  ["a requested graph", (response) => { response.graph.status = "ready"; }],
  ["graph scope data despite no graph request", (response) => { response.graph.world_id = worldId; }],
  ["a graph focus despite no graph request", (response) => { response.graph.focus = { node_id: "node-1" }; }],
  ["a graph-grounded answer", (response) => { response.answer.graph_grounded = true; }],
  ["an error answer", (response) => { response.answer.status = "error"; }],
  ["a blank answer", (response) => { response.answer.text = "  "; }],
  ["a malformed answer shape", (response) => { delete (response.answer as { trace?: Record<string, unknown> }).trace; }],
];

it.each(invalidWorldPlanResponses)("persists no first-turn transcript for %s", async (_description, mutate) => {
  mockSavedPlanForAgent();
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
    const response = worldPlanAgentResponse(request);
    mutate(response);
    return response;
  });
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "Question that must not be saved" } });
  sendDiscussMessage();
  expect(await screen.findByRole("alert")).toHaveTextContent(/response|turn|revision|Plan/i);
  expect(postTurn).toHaveBeenCalledTimes(1);

  const request = postTurn.mock.calls[0][0];
  const namespace = planAgentNamespace();
  expect(localStorage.getItem(threadStorageKey(namespace, request.client_thread_id))).toBeNull();
  expect(localStorage.getItem(activeThreadStorageKey(namespace, "plan", savedAgentPlanId))).toBeNull();
  expect(screen.queryByText("DungeonBuddy: Question that must not be saved")).not.toBeInTheDocument();
  expect(screen.queryByText(/The keeper is below the black arch\./)).not.toBeInTheDocument();
});

it("stops before the Agent call when the committed Plan changed since this view loaded", async () => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 8);
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  fireEvent.click(await screen.findByRole("button", { name: "Open" }));
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "Question that must not be sent" } });
  sendDiscussMessage();

  expect(await screen.findByRole("alert")).toHaveTextContent(/committed Plan changed|Refresh the Plan/i);
  expect(postTurn).not.toHaveBeenCalled();
  expect(localStorage.getItem(activeThreadStorageKey(planAgentNamespace(), "plan", savedAgentPlanId))).toBeNull();
});

it("preserves a scoped legacy provider pointer without a render-phase update or thread rewrite", async () => {
  const namespace = planAgentNamespace();
  const legacyThread = createAgentInteractionThread(namespace, null, "plan", "hermes", "Legacy Plan thread", savedAgentPlanId);
  legacyThread.hermesSession = { sessionId: "legacy-provider-pointer", runtime: "api" };
  persistAgentThread(legacyThread);
  const storedThreadKey = threadStorageKey(namespace, legacyThread.threadId);
  const legacyBytes = localStorage.getItem(storedThreadKey);
  const setItem = vi.spyOn(Storage.prototype, "setItem");
  const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);
  mockSavedPlanForAgent();

  render(
    <StrictMode>
      <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
        <AgentEnabledPlanPage />
      </SelectedWorldProvider>
    </StrictMode>,
  );
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  await waitFor(() => {
    const stored = JSON.parse(localStorage.getItem(storedThreadKey) ?? "null");
    expect(stored.hermesSession).toEqual({ sessionId: "legacy-provider-pointer", runtime: "api" });
  });
  expect(JSON.parse(localStorage.getItem(storedThreadKey) ?? "null").turns).toEqual([]);
  expect(JSON.parse(localStorage.getItem(threadIndexStorageKey(namespace, "plan", savedAgentPlanId)) ?? "{}").threads[0].hermesSessionId).toBe("legacy-provider-pointer");
  expect(setItem.mock.calls.filter(([key]) => key === storedThreadKey)).toHaveLength(0);
  expect(localStorage.getItem(storedThreadKey)).toBe(legacyBytes);
  expect(consoleError.mock.calls.flat().join(" ")).not.toMatch(/Cannot update a component.*while rendering/i);
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
  const view = render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  expect(screen.getByTestId("world-plan-surface-context")).toBeInTheDocument();
  await waitFor(() => expect(screen.getByRole("button", { name: "Bold" })).toBeEnabled());
  expect(screen.getByRole("button", { name: "Read aloud" })).toBeEnabled();
  expect(screen.getByTestId("world-owned-plan-editor")).toHaveClass("plan-surface-canvas");
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toBeInTheDocument();
  const initialLocalId = JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`) ?? "null").local_draft_id;
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `plan-local-draft:${initialLocalId}`));
  expect(screen.getByTestId("world-plan-context-identity")).toHaveTextContent(screen.getByTestId("world-plan-publication").getAttribute("data-instance-key")!);
  fireEvent.click(screen.getByRole("button", { name: "Read aloud" }));
  await waitFor(() => expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("Read aloud"));
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  const prePromotionControls = capturedPlanControls();
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(screen.getByText("Saved to this World.")).toBeInTheDocument());
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `document:${record.document_id}`));
  expect(screen.getByTestId("world-plan-context-identity")).toHaveTextContent(screen.getByTestId("world-plan-publication").getAttribute("data-instance-key")!);
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
  const savedJournal = localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`);
  prePromotionControls.changeTitle({ target: { value: "Stale local title" } });
  prePromotionControls.bold();
  prePromotionControls.save();
  expect(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)).toBe(savedJournal);
  expect(liveApi.createWorldOwnedPlan).toHaveBeenCalledTimes(1);
  const postPromotionControls = capturedPlanControls();
  view.unmount();
  postPromotionControls.changeTitle({ target: { value: "Unmounted title" } });
  postPromotionControls.bold();
  postPromotionControls.save();
  expect(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)).toBe(savedJournal);
  expect(liveApi.createWorldOwnedPlan).toHaveBeenCalledTimes(1);
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
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentId } });
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
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: unrelatedId } });
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

it("preserves a blank recovery journal and keeps Plan actions locked after context failure", async () => {
  const documentId = "plan-b-context-retry";
  const draftKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  const journal = {
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Plan A working draft",
    markdown: "# A private draft\n",
    revision: null,
    edit_generation: 9,
    create_uncertain: true,
    uncertain_create_draft: {
      title: "Uncertain create recovery",
      markdown: "# Keep this separate\n",
      edit_generation: 9,
      bound_document_id: null,
    },
  };
  const originalJournal = JSON.stringify(journal);
  localStorage.setItem(draftKey, originalJournal);
  const record = worldPlanRecord(documentId, worldId, 3);
  record.title = "Plan B";
  const planSnapshot = {
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown: "# B saved body\n",
    content_sha256: "b".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 3,
  };
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const getContext = vi.spyOn(liveApi, "getManagedWorldPlanContext")
    .mockRejectedValueOnce(new Error("Context unavailable"))
    .mockResolvedValue(managedContext(worldId));
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockResolvedValue(record);
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
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockResolvedValue(planSnapshot);

  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByText("Context unavailable")).toBeInTheDocument();
  expect(localStorage.getItem(draftKey)).toBe(originalJournal);
  expect(screen.queryByText("A private draft")).not.toBeInTheDocument();
  const editor = screen.getByTestId("world-owned-plan-markdown-editor").querySelector("[contenteditable]");
  expect(editor).not.toBeNull();
  expect(editor).toHaveAttribute("contenteditable", "false");
  expect(screen.queryByRole("button", { name: "Save Plan" })).not.toBeInTheDocument();
  expect(screen.getByLabelText("Plan document")).toBeDisabled();
  expect(screen.getByRole("button", { name: "New blank Plan" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Restore recovered draft into this Plan" })).toBeDisabled();
  const discardButtons = screen.getAllByRole("button", { name: "Discard recovered draft" });
  expect(discardButtons.length).toBeGreaterThan(0);
  for (const button of discardButtons) expect(button).toBeDisabled();
  const retry = screen.getByRole("button", { name: "Retry Plan load" });
  expect(retry).toBeEnabled();

  fireEvent.click(screen.getByRole("button", { name: "New blank Plan" }));
  fireEvent.click(screen.getByRole("button", { name: "Restore recovered draft into this Plan" }));
  fireEvent.click(discardButtons[0]);
  expect(localStorage.getItem(draftKey)).toBe(originalJournal);

  fireEvent.click(retry);
  await screen.findByText("B saved body");
  expect(getContext).toHaveBeenCalledTimes(2);
  expect(screen.queryByText("A private draft")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Plan document")).toBeEnabled();
});

it("keeps another Plan's draft out of a failed document load and retries without changing its journal", async () => {
  const firstId = "plan-a-document-retry";
  const documentId = "plan-b-document-retry";
  const draftKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  const originalJournal = JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: firstId,
    local_draft_id: `local-plan:${worldId}:draft-a`,
    title: "Plan A private title",
    markdown: "# A private draft body\n",
    revision: 2,
    edit_generation: 7,
    pending_write: {
      phase: "commit",
      base_revision: 2,
      prepared_revision: 3,
      base_markdown: "# A saved body\n",
      markdown: "# A private draft body\n",
      edit_generation: 7,
    },
  });
  localStorage.setItem(draftKey, originalJournal);
  const record = worldPlanRecord(documentId, worldId, 4);
  record.title = "Plan B";
  const planSnapshot = {
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown: "# B saved body\n",
    content_sha256: "c".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 4,
  };
  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${documentId}`);
  const getContext = vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockResolvedValue(record);
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks-cons-demo-markdown", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [worldPlanRecord(firstId, worldId, 2), record],
  });
  const getSnapshot = vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot")
    .mockRejectedValueOnce(new Error("Plan B snapshot unavailable"))
    .mockResolvedValue(planSnapshot);

  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByText("Plan B snapshot unavailable")).toBeInTheDocument();
  expect(localStorage.getItem(draftKey)).toBe(originalJournal);
  expect(screen.queryByText("A private draft body")).not.toBeInTheDocument();
  expect(screen.queryByText("Plan A private title")).not.toBeInTheDocument();
  expect(screen.getByLabelText("Plan document")).toBeDisabled();
  expect(screen.getByRole("button", { name: "New blank Plan" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Retry Plan load" })).toBeEnabled();

  fireEvent.click(screen.getByRole("button", { name: "Retry Plan load" }));
  await screen.findByText("B saved body");
  expect(localStorage.getItem(draftKey)).not.toBe(originalJournal);
  expect(getContext).toHaveBeenCalledTimes(2);
  expect(getSnapshot).toHaveBeenCalledTimes(2);
  expect(screen.queryByText("A private draft body")).not.toBeInTheDocument();
});

it("retires outgoing Plan editing and canvas identity through pending and failed saved-document loads", async () => {
  const firstId = "plan-a";
  const secondId = "plan-b";
  const draftKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  const firstRecord = worldPlanRecord(firstId, worldId, 2);
  const secondRecord = worldPlanRecord(secondId, worldId, 7);
  localStorage.setItem(draftKey, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: firstId,
    title: "A draft title",
    markdown: "# A draft body\n",
    revision: 2,
    edit_generation: 4,
  }));
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockImplementation(async (id) =>
    id === secondId ? secondRecord : firstRecord);
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks-cons-demo-markdown", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [firstRecord, secondRecord],
  });
  let resolveSecond!: (snapshot: Awaited<ReturnType<typeof liveApi.getWorldOwnedPlanSnapshot>>) => void;
  const pendingSecond = new Promise<Awaited<ReturnType<typeof liveApi.getWorldOwnedPlanSnapshot>>>((resolve) => {
    resolveSecond = resolve;
  });
  const snapshot = (record: WorldOwnedPlanRecordV2, markdown: string) => ({
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown,
    content_sha256: "a".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: record.revision,
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async (id) =>
    id === secondId ? pendingSecond : snapshot(firstRecord, "# A saved body\n"));

  window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${firstId}`);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${firstId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `document:${firstId}`));
  const firstIdentity = screen.getByTestId("world-plan-publication").getAttribute("data-instance-key");
  const outgoingTitle = screen.getByLabelText("Plan title");
  const outgoingControls = capturedPlanControls();
  const outgoingEditor = screen.getByTestId("world-owned-plan-markdown-editor").querySelector("[contenteditable]");
  expect(outgoingEditor).not.toBeNull();
  expect(outgoingEditor).toHaveAttribute("contenteditable", "true");
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: secondId } });
  expect(outgoingEditor).toHaveAttribute("contenteditable", "false");
  await waitFor(() => expect(screen.getByText("Loading World Plan…")).toBeInTheDocument());
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", "none"));
  expect(screen.getByTestId("world-plan-context-identity")).toHaveTextContent(firstIdentity!);
  expect(screen.queryByLabelText("Plan title")).not.toBeInTheDocument();
  fireEvent.change(outgoingTitle, { target: { value: "Wrong destination" } });
  outgoingControls.changeTitle({ target: { value: "Wrong callback title" } });
  outgoingControls.bold();
  outgoingControls.save();
  fireEvent.input(outgoingEditor!, { target: { textContent: "Wrong destination body" } });
  expect(JSON.parse(localStorage.getItem(draftKey) ?? "null")).toMatchObject({
    document_id: firstId,
    title: "A draft title",
    markdown: "# A draft body\n",
  });
  resolveSecond(snapshot(secondRecord, "# B saved body\n"));
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  await waitFor(() => expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("B saved body"));
  expect(screen.getByTestId("world-owned-plan-markdown-editor").querySelector("[contenteditable]")).not.toBe(outgoingEditor);
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `document:${secondId}`));
  expect(screen.getByTestId("world-plan-context-identity")).toHaveTextContent(screen.getByTestId("world-plan-publication").getAttribute("data-instance-key")!);
  const secondIdentity = screen.getByTestId("world-plan-context-identity").textContent;
  expect(screen.getByLabelText("Plan title")).toHaveValue("Plan");
  expect(JSON.parse(localStorage.getItem(draftKey) ?? "null")).toMatchObject({
    document_id: secondId,
    markdown: "# B saved body\n",
    revision: 7,
  });
  const secondJournal = localStorage.getItem(draftKey);
  outgoingControls.changeTitle({ target: { value: "Wrong loaded title" } });
  outgoingControls.bold();
  outgoingControls.save();
  expect(localStorage.getItem(draftKey)).toBe(secondJournal);
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockRejectedValueOnce(new Error("Snapshot unavailable"));
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: firstId } });
  await waitFor(() => expect(screen.getByText("Snapshot unavailable")).toBeInTheDocument());
  expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", "none");
  expect(screen.getByTestId("world-plan-context-identity")).toHaveTextContent(secondIdentity!);
  expect(screen.getByTestId("world-plan-context-identity")).not.toHaveTextContent(firstIdentity!);
  expect(screen.getByLabelText("Plan document")).toHaveValue(secondId);
  expect(screen.getByLabelText("Plan document")).toBeDisabled();
  expect(screen.queryByLabelText("Plan title")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Retry Plan load" })).toBeEnabled();

  fireEvent.click(screen.getByRole("button", { name: "Retry Plan load" }));
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  expect(screen.getByLabelText("Plan document")).toHaveValue(firstId);
  expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `document:${firstId}`);
});

it("migrates a legacy blank World draft to one stable canvas and context identity", async () => {
  const draftKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  const recovery = { title: "Recovered", markdown: "# Recovery\n", edit_generation: 3, bound_document_id: null };
  const pendingWrite = { phase: "prepare", base_revision: 1, prepared_revision: null, base_markdown: "# Old\n", markdown: "# New\n", edit_generation: 2 };
  localStorage.setItem(draftKey, JSON.stringify({
    schema_version: "dmb_plan_promotion_recovery_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: null,
    title: "Legacy draft",
    markdown: "# Keep my text\n",
    revision: null,
    edit_generation: 4,
    create_uncertain: false,
    uncertain_create_draft: recovery,
    pending_write: pendingWrite,
  }));
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockResolvedValue(managedContext(worldId));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [{ schema_version: "dmb_world_container_record_v1", world_id: worldId, name: "Of Conks", source_root_relpath: "corpus/of-conks-cons-demo-markdown", created_at: "2026-01-01T00:00:00Z" }],
  });
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [],
  });
  window.history.replaceState({}, "", `/plan?world=${worldId}`);
  const mount = () => render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  const first = mount();
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).not.toHaveAttribute("data-work-object", "none"));
  const migrated = JSON.parse(localStorage.getItem(draftKey) ?? "null");
  expect(migrated).toMatchObject({
    document_id: null,
    title: "Legacy draft",
    markdown: "# Keep my text\n",
    uncertain_create_draft: recovery,
    pending_write: pendingWrite,
  });
  expect(migrated.edit_generation).toBe(4);
  expect(migrated.local_draft_id).toMatch(new RegExp(`^local-plan:${worldId}:`));
  const firstKey = screen.getByTestId("world-plan-publication").getAttribute("data-instance-key");
  expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `plan-local-draft:${migrated.local_draft_id}`);
  await waitFor(() => expect(screen.getByTestId("world-plan-context-identity")).toHaveTextContent(firstKey!));
  fireEvent.change(screen.getByLabelText("Plan title"), { target: { value: "Renamed local draft" } });
  expect(JSON.parse(localStorage.getItem(draftKey) ?? "null")).toMatchObject({
    local_draft_id: migrated.local_draft_id,
    title: "Renamed local draft",
    uncertain_create_draft: recovery,
    pending_write: pendingWrite,
  });
  first.unmount();

  mount();
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-instance-key", firstKey));
  expect(JSON.parse(localStorage.getItem(draftKey) ?? "null").local_draft_id).toBe(migrated.local_draft_id);
  const retiredBlankControls = capturedPlanControls();
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: "" } });
  await waitFor(() => expect(JSON.parse(localStorage.getItem(draftKey) ?? "null").local_draft_id).not.toBe(migrated.local_draft_id));
  const newDraft = JSON.parse(localStorage.getItem(draftKey) ?? "null");
  expect(newDraft.local_draft_id).toMatch(new RegExp(`^local-plan:${worldId}:`));
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `plan-local-draft:${newDraft.local_draft_id}`));
  expect(screen.getByTestId("world-plan-context-identity")).not.toHaveTextContent(firstKey!);
  const blankJournal = localStorage.getItem(draftKey);
  retiredBlankControls.changeTitle({ target: { value: "Old blank title" } });
  retiredBlankControls.bold();
  retiredBlankControls.save();
  expect(localStorage.getItem(draftKey)).toBe(blankJournal);
});

it("replaces World Plan identity by World and releases the canvas on unmount", async () => {
  const secondWorld = "world-b";
  vi.spyOn(liveApi, "getManagedWorldPlanContext").mockImplementation(async (id) => managedContext(id));
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({
    schema_version: "dmb_world_container_registry_v1",
    records: [worldId, secondWorld].map((id) => ({
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
  function Harness({ world, show = true }: { world: string; show?: boolean }) {
    return (
      <AgentInteractionProvider>
        {show ? (
          <SelectedWorldProvider key={world} locationSnapshot={`/plan?world=${world}`}>
            <PlanSurfacePage />
          </SelectedWorldProvider>
        ) : null}
        <PublicationProbe />
      </AgentInteractionProvider>
    );
  }
  const { rerender } = render(<Harness world={worldId} />);
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).not.toHaveAttribute("data-work-object", "none"));
  const firstWorkObject = screen.getByTestId("world-plan-publication").getAttribute("data-work-object");
  const firstIdentity = screen.getByTestId("world-plan-publication").getAttribute("data-instance-key");
  expect(firstWorkObject).toContain(`local-plan:${worldId}:`);
  const worldAKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  const worldAJournal = localStorage.getItem(worldAKey);
  const worldAControls = capturedPlanControls();
  rerender(<Harness world={secondWorld} />);
  await waitFor(() => expect(screen.getByTestId("world-plan-publication").getAttribute("data-work-object")).toContain(`local-plan:${secondWorld}:`));
  expect(screen.getByTestId("world-plan-publication")).not.toHaveAttribute("data-instance-key", firstIdentity);
  const worldBKey = `dmb:world-plan-local-draft:v2:${secondWorld}`;
  const worldBJournal = localStorage.getItem(worldBKey);
  worldAControls.changeTitle({ target: { value: "Cross World title" } });
  worldAControls.bold();
  worldAControls.save();
  expect(localStorage.getItem(worldAKey)).toBe(worldAJournal);
  expect(localStorage.getItem(worldBKey)).toBe(worldBJournal);
  rerender(<Harness world={secondWorld} show={false} />);
  await waitFor(() => expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", "none"));
});

it("keeps the checked-in Session 29 linked Plan safely editable after root-quote support", async () => {
  const record = mockSavedPlanForAgent();
  const session29Plan = readFileSync(
    "../../corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 29 - Buddy Plan.md",
    "utf8",
  );
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record,
    markdown: session29Plan,
    content_sha256: "d".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 7,
  });
  const location = `/plan?world=${worldId}&documentId=${savedAgentPlanId}`;
  window.history.replaceState({}, "", location);
  render(
    <SelectedWorldProvider locationSnapshot={location}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );

  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  expect(screen.queryByRole("alert", { name: "Markdown preservation warning" })).not.toBeInTheDocument();
  expect(editorSurface.querySelector(".ProseMirror")).toHaveAttribute("contenteditable", "true");
  expect(editorSurface).toHaveTextContent("Session 29 is about giving the table ownership again.");
  expect(editorSurface).toHaveTextContent("For the first time in what feels like hours, nothing new is crawling out of the ground.");
  await waitFor(() => expect(editorSurface.querySelectorAll(".graph-node-reference-view")).toHaveLength(72));
  await waitFor(() => expect(editorSurface.querySelectorAll("[data-dmb-playable-id]")).toHaveLength(90));
  expect(JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`) ?? "null").markdown).toBe(session29Plan);
});

it("starts Play from the exact clean committed World Plan revision", async () => {
  const record = mockSavedPlanForAgent();
  const committed = {
    schema_version: "dmb_workspace_committed_revision_v2" as const,
    scope_mode: "world" as const,
    world_id: worldId,
    campaign_id: null,
    document_id: record.document_id,
    kind: "plan" as const,
    title: "Of Conks Session Plan",
    status: "active" as const,
    object_revision: 7,
    work_revision_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    revision_n: 4,
    markdown: savedAgentPlanText,
    content_sha256: "b".repeat(64),
    has_divergent_working_copy: false,
    target_relpath: record.target_relpath,
  } satisfies WorldOwnedCommittedRevisionV2;
  const getCommitted = vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision)
    .mockResolvedValue(committed);
  const location = `/plan?world=${worldId}&documentId=${record.document_id}`;
  window.history.replaceState({}, "", location);
  render(
    <SelectedWorldProvider locationSnapshot={location}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );

  const start = await screen.findByTestId("world-plan-start-play");
  await waitFor(() => expect(start).toBeEnabled());
  fireEvent.click(start);

  await waitFor(() => expect(window.location.pathname).toBe("/play"));
  const params = new URLSearchParams(window.location.search);
  expect(params.get("world")).toBe(worldId);
  expect(params.get("plan")).toBe(record.document_id);
  expect(params.get("plan_revision")).toBe("4");
  expect(params.get("plan_work_revision_id")).toBe(committed.work_revision_id);
  expect(params.get("plan_sha256")).toBe(committed.content_sha256);
  expect(getCommitted).toHaveBeenCalledWith(record.document_id);
});

it("keeps Start Play disabled while the selected World Plan has unsaved edits", async () => {
  const record = mockSavedPlanForAgent();
  const committed = {
    schema_version: "dmb_workspace_committed_revision_v2" as const,
    scope_mode: "world" as const,
    world_id: worldId,
    campaign_id: null,
    document_id: record.document_id,
    kind: "plan" as const,
    title: "Of Conks Session Plan",
    status: "active" as const,
    object_revision: 7,
    work_revision_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
    revision_n: 4,
    markdown: savedAgentPlanText,
    content_sha256: "b".repeat(64),
    has_divergent_working_copy: false,
    target_relpath: record.target_relpath,
  } satisfies WorldOwnedCommittedRevisionV2;
  vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue(committed);
  const location = `/plan?world=${worldId}&documentId=${record.document_id}`;
  window.history.replaceState({}, "", location);
  render(
    <SelectedWorldProvider locationSnapshot={location}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );

  const start = await screen.findByTestId("world-plan-start-play");
  await waitFor(() => expect(start).toBeEnabled());
  act(() => capturedPlanControls().changeTitle({ target: { value: "Unsaved title" } }));

  expect(start).toBeDisabled();
  expect(screen.getByTestId("world-plan-start-play-disabled")).toHaveTextContent(/clean, committed Plan/i);
});

it("preserves unsupported source and recovery bytes and refuses Save before prepare or commit", async () => {
  const record = mockSavedPlanForAgent();
  const unsupportedMarkdown = "# Plan\n\nRead [the rules](https://example.com/rules) before continuing.\n";
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockResolvedValue({
    schema_version: "dmb_workspace_document_snapshot_v2",
    record,
    markdown: unsupportedMarkdown,
    content_sha256: "e".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: 7,
  });
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockRejectedValue(new Error("prepare must not be called"));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockRejectedValue(new Error("commit must not be called"));
  const location = `/plan?world=${worldId}&documentId=${savedAgentPlanId}`;
  window.history.replaceState({}, "", location);
  render(
    <SelectedWorldProvider locationSnapshot={location}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );

  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeDisabled());
  expect(screen.getByRole("alert", { name: "Markdown preservation warning" })).toHaveTextContent(/cannot safely preserve/i);
  expect(editorSurface.querySelector(".ProseMirror")).toHaveAttribute("contenteditable", "false");
  const recoveryKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  const recoveryBytes = localStorage.getItem(recoveryKey);
  expect(JSON.parse(recoveryBytes ?? "null").markdown).toBe(unsupportedMarkdown);

  await act(async () => { capturedPlanControls().save(); });

  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
  expect(localStorage.getItem(recoveryKey)).toBe(recoveryBytes);
});

it("reverts an editor transaction that the semantic Markdown serializer cannot preserve", async () => {
  mockSavedPlanForAgent();
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockRejectedValue(new Error("prepare must not be called"));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockRejectedValue(new Error("commit must not be called"));
  const location = `/plan?world=${worldId}&documentId=${savedAgentPlanId}`;
  window.history.replaceState({}, "", location);
  render(
    <SelectedWorldProvider locationSnapshot={location}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );

  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(editorSurface.querySelector(".ProseMirror")).toHaveTextContent("The keeper waits beneath the black arch."));
  const proseMirror = editorSurface.querySelector(".ProseMirror") as HTMLElement;
  const textWalker = document.createTreeWalker(proseMirror, NodeFilter.SHOW_TEXT);
  let textNode: Text | null = null;
  while (textWalker.nextNode()) textNode = textWalker.currentNode as Text;
  if (!textNode) throw new Error("Expected Plan editor text before testing a hard break.");
  const range = document.createRange();
  range.setStart(textNode, textNode.textContent?.length ?? 0);
  range.collapse(true);
  const selection = window.getSelection();
  selection?.removeAllRanges();
  selection?.addRange(range);
  fireEvent.mouseUp(proseMirror);

  const recoveryKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  const originalRecovery = localStorage.getItem(recoveryKey);
  fireEvent.keyDown(proseMirror, { key: "Enter", code: "Enter", shiftKey: true });

  expect(await screen.findByRole("alert")).toHaveTextContent(/edit was reverted to protect the saved Plan/i);
  expect(screen.getByRole("alert")).toHaveTextContent(/Hard breaks are not represented losslessly/i);
  expect(localStorage.getItem(recoveryKey)).toBe(originalRecovery);
  const restoredEditor = editorSurface.querySelector(".ProseMirror") as HTMLElement;
  expect(restoredEditor).not.toBe(proseMirror);
  expect(restoredEditor).toHaveTextContent("The keeper waits beneath the black arch.");
  expect(restoredEditor.querySelector("br")).not.toBeInTheDocument();
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
});
