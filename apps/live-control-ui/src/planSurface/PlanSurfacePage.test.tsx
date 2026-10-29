import {useTourNavigationRegistry,navigationScope} from '../guidedTour/Navigation';
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { createHash, webcrypto } from "node:crypto";
import { StrictMode,useLayoutEffect, type ReactElement, type ReactNode } from "react";
import { afterEach, beforeAll, beforeEach, expect, it, vi } from "vitest";

import * as liveApi from "../api/liveApi";
import * as markdownImporter from "../tiptap/markdown/markdownToTiptap";
import { defaultMarkdownDocumentAdapter } from "../tiptap/MarkdownDocumentAdapter";
import { SelectedWorldProvider, useSelectedWorld } from "../selectedWorld/SelectedWorldContext";
import type { AgentInteractionTrace, WorldOwnedCommittedRevisionV2, WorldOwnedPlanRecordV2, WorldAgentConversationHistoryTurnV3 } from "../api/types";
import { ToolHost } from "../surfaceInteraction/toolHost/ToolHost";
import { PeekRegionProvider, PeekRegionSlot } from "../surfaceInteraction/peekHost";
import { LegacyProjectionHostAdapter } from "./projection/LegacyProjectionHostAdapter";
import { PlanSurfacePage } from "./PlanSurfacePage";
import { GuidedTourProvider, useGuidedTour } from "../guidedTour/GuidedTour";
import { createWalkthrough, reduceTour } from "../guidedTour/protocol";
import { readWalkthrough, writeWalkthrough } from "../guidedTour/storage";
import { WorldGraphLensProvider } from "../graphLens/WorldGraphLensContext";
import { WorldGraphLensProjectionProvider } from "../graphLens/useWorldGraphLensProjection";
import { AgentInteractionProvider, useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { AgentInteractionChrome } from "../agentInteraction/AgentInteractionChrome";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { WorldAgentConversation, WorldAgentConversationProvider } from "../agentInteraction/WorldAgentConversation";
import type { WorldPlanAgentTurnRequestV1, WorldPlanAgentTurnResponse, WorldPlanAgentPlanContextV2, WorldPlanGraphAnswerContextStatusV1, WorldPlanGraphExecutionProjectionV1 } from "../api/types";
import {
  activeThreadStorageKey,
  createAgentInteractionThread,
  loadAgentThreadById,
  persistAgentThread,
  threadIndexStorageKey,
  threadStorageKey,
} from "../agentInteraction/agentInteractionStorage";

const planEncounterCapture=vi.hoisted(()=>({context:null as import('../combat/sceneTemplatesApi').PlanEncounterContext|null}));
vi.mock('../combat/combatProjection',async importOriginal=>{
 const actual=await importOriginal<typeof import('../combat/combatProjection')>();
 return {...actual,useCombatProjection:(...args:Parameters<typeof actual.useCombatProjection>)=>{if(args[0]==='plan')planEncounterCapture.context=args[2] as import('../combat/sceneTemplatesApi').PlanEncounterContext|null;return actual.useCombatProjection(...args);}};
});
const planImageHostCapture = vi.hoisted(() => ({ props: null as any }));
vi.mock("../agentInteraction/WorldAgentConversation", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../agentInteraction/WorldAgentConversation")>();
  return { ...actual, WorldPlanConversationRegistration: (props: any) => {
    planImageHostCapture.props = props;
    return <actual.WorldPlanConversationRegistration {...props} />;
  } };
});
const mediaWizardCapture = vi.hoisted(() => ({ props: null as any }));
vi.mock("../media/MediaImageWizard", () => ({ MediaImageWizard: (props: any) => { mediaWizardCapture.props = props; return <div aria-label="Synthetic Image Studio" />; } }));

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

function WorldHostedPlanPage() {
  const selected = useSelectedWorld();
  if (selected.kind !== "managed") return <span>{selected.kind}</span>;
  return <AgentInteractionProvider><AskPluginSlotProvider>
    <WorldAgentConversationProvider worldId={selected.worldId}>
      <PlanSurfacePage /><AgentInteractionChrome />
      <WorldAgentConversation surface="plan" worldId={selected.worldId} worldName="Of Conks" />
    </WorldAgentConversationProvider>
  </AskPluginSlotProvider></AgentInteractionProvider>;
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

async function openPlanConversation() {
  // The surface shell exists while its selected snapshot is still loading.
  // Wait for the actual document tools before opening the shared dock.
  await waitFor(() => expect(chromeCapture.editorTools).not.toBeNull());
  fireEvent.click(await screen.findByRole("button", { name: "Open", exact: true }));
  return screen.findByRole("region", { name: "World conversation" });
}

function savedWorldPlanConversation() {
  const region = screen.getByRole("region", { name: "World conversation" });
  const options = screen.getByTitle("Conversation options");
  if (!(options.closest("details") as HTMLDetailsElement).open) fireEvent.click(options);
  const context = screen.getByRole("button", { name: /^(Show|Hide) context$/ });
  if (context.getAttribute("aria-expanded") !== "true") fireEvent.click(context);
  return region;
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
  const more = screen.getByTitle("Conversation options").closest("details");
  if (more && !more.open) fireEvent.click(more.querySelector("summary")!);
  fireEvent.click(within(conversation).getByText("Advanced details"));
}

const savedAgentPlanId = "saved-plan-agent-test";
const savedAgentPlanText = "# Private Plan prose\nThe keeper waits beneath the black arch.\n";
const twoScenePlanMarkdown = [
  "# Saved Plan",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:road beat_kind=spine -->",
  "## Road",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:arrival -->",
  "### Arrival",
  "The keeper waits beneath the black arch.",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:warehouse -->",
  "### Warehouse",
  "A lantern moves behind the loading door.",
].join("\n") + "\n";

const currentTwoScenePlanMarkdown = `# Saved Plan

<!-- dmb-playable-element:v2 kind=beat id=beat:road beat_kind=spine -->
## Road
<!-- dmb-playable-element:v2 kind=scene id=scene:arrival -->
### Arrival
The keeper waits beneath the black arch.
<!-- dmb-playable-element:v2 kind=scene id=scene:warehouse -->
### Warehouse
A lantern moves behind the loading door.
`;

it.each([false, true, "stale-apply", "save", "save-clean"] as const)("captures the current Ask scene without Select for Edit; editor selection precedence=%s", async (selectText) => {
  const record = mockSavedPlanForAgent(savedAgentPlanId, 7, 7, twoScenePlanMarkdown.replace("### Arrival", "### Quiet test scene"));
  const prepareSave = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockRejectedValue(new Error("Explicit Save test stop"));
  const commitSave = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  if (selectText === "save-clean") {
    prepareSave.mockResolvedValue({ schema_version: "dmb_tiptap_markdown_write_prepare_v2", scope_mode: "world",
      world_id: worldId, document_id: savedAgentPlanId, title: record.title, target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!, registry_revision: 8, file_exists: true, writer_ok: true,
      writer_confirm_token: "save-clean-token", warnings: [], diagnostics: [] });
    commitSave.mockImplementation(async (request) => {
      const digest = createHash("sha256").update(request.markdown).digest("hex");
      const savedRecord = { ...record, revision: 9 };
      const prior = await liveApi.getWorldOwnedPlanCommittedRevision(savedAgentPlanId);
      vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue({ ...prior, object_revision: 9,
        revision_n: 5, work_revision_id: "saved-plan-revision-5", markdown: request.markdown,
        content_sha256: digest, has_divergent_working_copy: false });
      vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockResolvedValue({ schema_version: "dmb_workspace_document_snapshot_v2",
        record: savedRecord, markdown: request.markdown, content_sha256: digest, file_fingerprint: "postgres",
        file_exists: true, loaded_revision: 9 });
      return { schema_version: "dmb_tiptap_markdown_write_commit_v2", scope_mode: "world", world_id: worldId,
        document_id: savedAgentPlanId, title: record.title, target_relpath: record.target_relpath!,
        target_display_path: record.target_relpath!, registry_revision: 9, committed_revision: 9,
        committed_record: savedRecord, normalized_content_sha256: digest, writer_ok: true,
        writer_phase: "commit", diagnostics: [] };
    });
  }
  const post = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal").mockImplementation(async (request) => ({
    schema_version: request.playable_target ? "dmb_world_plan_document_edit_proposal_v2" : "dmb_world_plan_document_edit_proposal_v1",
    action_id: "00000000-0000-4000-8000-000000000099", idempotency_key: request.idempotency_key,
    document_id: request.document_id, world_id: request.world_id,
    base_revision: request.base_revision, base_content_sha256: request.base_content_sha256,
    draft_sha256: request.draft_sha256, target_kind: request.target_kind,
    selected_text_sha256: request.playable_target ? null : createHash("sha256").update(request.selected_text).digest("hex"),
    ...(request.playable_target ? { playable_target: request.playable_target, marker_grammar_version: "v2",
      body_scope: "heading_body", range_semantics_version: "plan-playable-ranges-v1",
      body_serialization_version: "plan-playable-body-markdown-v1", target_body_sha256: request.target_body_sha256 } : {}),
    replacement_markdown: request.playable_target ? `${request.target_body_markdown}\nOptional GM cue: Ask each player what they notice first.\n` : "Revised selected text",
    summary: "Append a GM cue", assumptions: [], model: "test", model_observed: false,
    model_latency_ms: 0, wall_latency_ms: 0, usage: null,
  }) as any);
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>);
  const page = await screen.findByTestId("world-owned-plan");
  await openPlanConversation();
  expect(await screen.findByRole("region", { name: "Plan content" })).toBeInTheDocument();
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" }));
  const reader = await screen.findByRole("region", { name: "Focused Plan scene" });
  expect(within(reader).queryByRole("button", { name: "Select for Edit" })).not.toBeInTheDocument();
  const conversation = savedWorldPlanConversation();
  expect(within(conversation).getByRole("group", { name: "Selected change target" })).toHaveTextContent("Target: Quiet test scene");
  if (selectText === true) {
    const editor = (screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror") as any).editor;
    let keeper = -1;
    editor.state.doc.descendants((node: any, pos: number) => { if (node.isText && node.text?.startsWith("The keeper")) keeper = pos + 4; });
    expect(keeper).toBeGreaterThan(0);
    act(() => editor.commands.setTextSelection({ from: keeper, to: keeper + 6 }));
    expect(within(conversation).getByLabelText("Actual Plan change target")).toHaveTextContent("Replace selected editor text");
  }
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "For this disposable synthetic Plan only, propose appending exactly this line to the selected Quiet test scene body: Optional GM cue: Ask each player what they notice first. Preserve all existing text and playable markers; make no other change." } });
  fireEvent.click(within(conversation).getByRole("button", { name: "Request a Plan change" }));
  fireEvent.click(within(conversation).getByRole("button", { name: "Propose edit" }));
  const review = await within(conversation).findByRole("region", { name: selectText === true ? "Change selected text" : "Change Quiet test scene" });
  expect(post).toHaveBeenCalledTimes(1);
  const request = post.mock.calls[0]![0];
  expect(request).toMatchObject({ base_revision: 7, base_content_sha256: "b".repeat(64) });
  expect(request.draft_sha256).toMatch(/^[a-f0-9]{64}$/);
  if (selectText === true) {
    expect(request.target_kind).toBe("replace_selection");
    expect(request.playable_target).toBeUndefined();
    expect(request.selected_text).toBe("keeper");
  } else {
    expect(request.target_kind).toBe("replace_playable_body");
    expect(request.playable_target).toEqual({ kind: "scene", id: "scene:arrival" });
    expect(request.target_body_markdown).toBe("The keeper waits beneath the black arch.\n");
    expect(request.target_body_sha256).toBe(createHash("sha256").update(request.target_body_markdown!).digest("hex"));
    const before = within(review).getByRole("region", { name: "Before Quiet test scene" });
    expect(within(before).getByText(request.target_body_markdown!.trim())).toBeInTheDocument();
    expect(before).toHaveTextContent("A lantern moves behind the loading door.");
    expect(within(before).getByRole("heading", { name: "Quiet test scene" })).toBeInTheDocument();
    expect(within(before).queryByText("<!-- dmb-playable-element:v1 kind=scene id=scene:arrival -->")).not.toBeInTheDocument();
    if (selectText === "stale-apply") {
      const prior = await liveApi.getWorldOwnedPlanCommittedRevision(savedAgentPlanId);
      vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue({ ...prior, object_revision: 8 });
      fireEvent.click(within(review).getByRole("button", { name: "Apply to draft" }));
      expect(await within(conversation).findByRole("alert")).toHaveTextContent("committed Plan changed");
      expect(screen.getByTestId("world-owned-plan-markdown-editor")).not.toHaveTextContent("Optional GM cue:");
      expect(post).toHaveBeenCalledTimes(1);
      expect(within(review).queryByRole("button", { name: "Apply to draft" })).not.toBeInTheDocument();
      return;
    }
    fireEvent.click(within(review).getByRole("button", { name: "Apply to draft" }));
    await within(review).findByText("Applied to your draft. Save Plan keeps this change.");
    expect(within(review).queryByRole("button", { name: "Apply to draft" })).not.toBeInTheDocument();
    expect(prepareSave).not.toHaveBeenCalled();
    expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("Optional GM cue: Ask each player what they notice first.");
    const draft = JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)!).markdown;
    expect(draft).toContain("kind=scene id=scene:arrival");
    expect(draft).toContain("kind=scene id=scene:warehouse");
    expect(draft).toContain("A lantern moves behind the loading door.");
    if (selectText === "save" || selectText === "save-clean") {
      const saveButton = within(review).getByRole("button", { name: "Save Plan" });
      fireEvent.click(saveButton);
      await waitFor(() => expect(prepareSave).toHaveBeenCalledTimes(1));
      expect(prepareSave.mock.calls[0]![0]).toMatchObject({ world_id: worldId, document_id: savedAgentPlanId });
      if (selectText === "save-clean") {
        await screen.findByText("Saved to this World.");
        expect(within(review).queryByRole("button", { name: "Save Plan" })).not.toBeInTheDocument();
        expect(within(review).getByRole("region", { name: "Before Quiet test scene" })).toHaveTextContent("The keeper waits beneath the black arch.");
        expect(within(review).getByRole("region", { name: "After Quiet test scene" })).toHaveTextContent("Optional GM cue:");
        expect(within(review).queryByText("Saved to your Plan.")).not.toBeInTheDocument();
        fireEvent.click(saveButton);
        expect(prepareSave).toHaveBeenCalledTimes(1);
        expect(commitSave).toHaveBeenCalledTimes(1);
      }
      expect(post).toHaveBeenCalledTimes(1);
      return;
    }
    fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "Append one more cue." } });
    fireEvent.click(within(conversation).getByRole("button", { name: "Request a Plan change" }));
  fireEvent.click(within(conversation).getByRole("button", { name: "Propose edit" }));
    const nextApply = await within(conversation).findByRole("button", { name: "Apply to draft" });
    const nextReview = nextApply.closest("section[aria-labelledby]")!;
    expect(nextReview).toHaveAccessibleName("Change Quiet test scene");
    fireEvent.click(within(reader).getByRole("button", { name: "Next scene" }));
    await within(nextReview).findByText("This preview is no longer current. It cannot be applied.");
    expect(within(nextReview).queryByRole("button", { name: "Apply to draft" })).not.toBeInTheDocument();
  }
});

function planAgentNamespace(documentId = savedAgentPlanId) {
  return `world-plan-agent:world:${encodeURIComponent(worldId)}:document:${encodeURIComponent(documentId)}`;
}

it("does not send a scene proposal when the mounted snapshot has a stale committed basis", async () => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 8, twoScenePlanMarkdown);
  const post = vi.spyOn(liveApi, "postWorldPlanDocumentEditProposal");
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>);
  const page = await screen.findByTestId("world-owned-plan");
  await openPlanConversation();
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" }));
  await screen.findByRole("region", { name: "Focused Plan scene" });
  const conversation = savedWorldPlanConversation();
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "Append a cue to the current scene." } });
  fireEvent.click(within(conversation).getByRole("button", { name: "Request a Plan change" }));
  fireEvent.click(within(conversation).getByRole("button", { name: "Propose edit" }));
  await waitFor(() => expect(within(conversation).getByRole("alert")).toHaveTextContent(/Select the scene|stale|changed/));
  expect(post).not.toHaveBeenCalled();
  expect(within(conversation).queryByRole("region", { name: "Review proposed Plan edit" })).not.toBeInTheDocument();
});

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
    work_revision_id: "00000000-0000-4000-8000-000000000004",
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
  "<!-- dmb-playable-element:v2 kind=beat id=beat:road beat_kind=spine -->",
  "## Road",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:arrival -->",
  "### Arrival",
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

function canonicalFixtureJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalFixtureJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const record = value as Record<string, unknown>;
    return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${canonicalFixtureJson(record[key])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

function historyCorrelationKey(request: WorldPlanAgentTurnRequestV1): string {
  const hash = createHash("sha1").update(Buffer.from("6ba7b8119dad11d180b400c04fd430c8", "hex"))
    .update(`dmb-agent-turn:${request.owner_scope.world_id}:${request.turn_id}`).digest();
  hash[6] = (hash[6]! & 0x0f) | 0x50;
  hash[8] = (hash[8]! & 0x3f) | 0x80;
  const hex = hash.subarray(0, 16).toString("hex");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

function planGraphContext(
  status: WorldPlanGraphAnswerContextStatusV1,
  options: {
    request?: WorldPlanAgentTurnRequestV1;
    execution?: WorldPlanGraphExecutionProjectionV1 | null;
    completion?: boolean;
  } = {},
): WorldPlanAgentPlanContextV2 {
  const worldId = options.request!.owner_scope.world_id;
  const documentId = options.request!.primary_work.object_id;
  const workRevisionId = "00000000-0000-4000-8000-000000000004";
  const contentSha256 = options.request!.primary_work.expected_content_sha256;
  const graphClaimed = status === "graph_grounded" || status === "graph_grounded_partial";
  const sufficient = status !== "plan_only_insufficient_evidence";
  const graphRevision = "graph-revision-test";
  const assertionIds = sufficient ? ["assertion-internal-test"] : [];
  const evidenceIds = sufficient ? ["evidence-internal-test"] : [];
  const receiptPayload = {
    schema: "dmb_agent_plan_world_graph_context_receipt_v1" as const,
    receipt_serializer_version: "canonical-json-utf8-v1" as const,
    context_receipt_sha256: "0".repeat(64),
    plan_context_policy: { schema: "dmb_plan_context_policy_v1" as const, policy: "auto_plan_world" as const },
    plan_basis: {
      world_id: worldId,
      document_id: documentId,
      object_revision: options.request?.primary_work.expected_revision ?? 7,
      work_revision_id: workRevisionId,
      revision_n: options.request?.primary_work.expected_revision_n ?? 1,
      content_sha256: options.request?.primary_work.expected_content_sha256 ?? contentSha256,
    },
    playable_target: options.request?.playable_target ? {
      schema: "dmb_plan_playable_target_receipt_v1" as const,
      kind: options.request.playable_target.kind,
      id: options.request.playable_target.id,
      marker_grammar_version: "v2" as const,
    } : null,
    graph_authority: {
      managed_world_id: worldId,
      native_world_id: "native-world-internal-test",
      binding_version: 3,
      scope_mode: "world" as const,
      campaign_id: null,
      admissibility_version: "admissibility-test-v1",
      graph_revision: graphRevision,
    },
    graph_packet: {
      schema: "dmb_plan_world_graph_packet_v1" as const,
      packet_serializer_version: "canonical-json-utf8-v1" as const,
      selection_policy_version: "selection-test-v1",
      evidence_sufficiency_policy_version: "evidence-test-v1",
      retrieval_packet_sha256: "b".repeat(64),
      candidate_assertion_ids: assertionIds,
      candidate_relationship_ids: [],
      candidate_evidence_ref_ids: evidenceIds,
      retrieval_status: sufficient ? "complete" as const : "empty" as const,
      evidence_sufficiency_status: sufficient ? "sufficient" as const : "insufficient" as const,
      result_limit: 10,
      coverage_status: status === "graph_grounded_partial" ? "incomplete" as const : "complete" as const,
      truncated: status === "graph_grounded_partial",
      omission_reasons: sufficient ? [] : ["no_claim_ready_evidence"],
    },
    assembled_input: {
      assembler_version: "assembler-test-v1",
      budget_policy_version: "budget-test-v1",
      provider_model_name: "test-model",
      provider_model_version: "test-model-v1",
      tokenizer_name: "test-tokenizer",
      tokenizer_version: "test-tokenizer-v1",
      provider_envelope_input_tokens: 400,
      output_token_reserve: 100,
      context_window_limit: 1000,
      packet_disposition: sufficient ? "included" as const : "omitted_insufficient" as const,
      packet_disposition_reason: sufficient ? null : "insufficient_evidence" as const,
      dispatched_packet_sha256: sufficient ? "c".repeat(64) : null,
      dispatched_assertion_ids: assertionIds,
      dispatched_relationship_ids: [],
      dispatched_evidence_ref_ids: evidenceIds,
      source_token_accounting: [{ source_kind: "plan" as const, source_id: documentId, input_tokens: 200 }],
      included_history: [],
      assembled_input_sha256: "d".repeat(64),
    },
    evidence_mode: "metadata_only" as const,
    source_opened: false as const,
  };
  const { context_receipt_sha256: _ignored, ...receiptForHash } = receiptPayload;
  const receiptDigest = createHash("sha256").update(canonicalFixtureJson(receiptForHash)).digest("hex");
  const receipt = { ...receiptPayload, context_receipt_sha256: receiptDigest };
  const segments = graphClaimed
    ? [{
      kind: "graph_claim" as const,
      claim_id: "claim-internal-test",
      text: "The western gate is watched.",
      target_kind: "assertion" as const,
      target_id: assertionIds[0]!,
      graph_revision: graphRevision,
      evidence_ref_ids: evidenceIds,
    }]
    : [{ kind: "connective" as const, text: "The keeper is below the black arch." }];
  const citationEntries = graphClaimed ? [{
    claim_id: "claim-internal-test",
    target_kind: "assertion" as const,
    target_id: assertionIds[0]!,
    graph_revision: graphRevision,
    evidence_ref_ids: evidenceIds,
    source_opened: false as const,
  }] : [];
  return {
    schema: "dmb_agent_plan_world_graph_context_response_v2",
    receipt,
    completion: options.completion === false ? null : {
      schema: "dmb_plan_world_graph_completion_v1",
      context_receipt_sha256: receiptDigest,
      answer_basis: graphClaimed ? "committed_plan_plus_world_graph" : "committed_plan",
      answer_context_status: status,
      answer_segments: segments,
      citation_map: graphClaimed ? {
        schema: "dmb_graph_citation_map_v1",
        context_receipt_sha256: receiptDigest,
        entries: citationEntries,
      } : null,
    },
    execution: options.execution === undefined ? {
      schema: "dmb_agent_plan_world_graph_execution_projection_v1",
      claimability: "completed",
      authorization_state: "response_received",
      automatic_redispatch: false,
    } : options.execution,
    delivery_replay: false,
  };
}

let serverHistoryTurns: WorldAgentConversationHistoryTurnV3[] = [];

function worldPlanAgentResponse(request: WorldPlanAgentTurnRequestV1): WorldPlanAgentTurnResponse {
  const planContext = request.plan_context_policy ? planGraphContext("plan_only_insufficient_evidence", { request }) : null;
  serverHistoryTurns.push({
    ...(planContext ? { plan_context: planContext } : {}),
    idempotency_key: historyCorrelationKey(request),
    turn_id: request.turn_id, sequence: serverHistoryTurns.length + 1,
    lifecycle_status: "completed", user_text: request.message,
    assistant_text: "The keeper is below the black arch.",
    provenance: {
      world_id: request.owner_scope.world_id, surface_resolution: "resolved",
      surface_id: "plan", surface_instance_id: request.surface.instance_id,
      primary_work: {
        resolution: "resolved", kind: "plan", object_id: request.primary_work.object_id,
        revision: String(request.primary_work.expected_revision), content_sha256: request.primary_work.expected_content_sha256,
        object_revision: request.primary_work.expected_revision,
        work_revision_id: "00000000-0000-4000-8000-000000000004", revision_n: request.primary_work.expected_revision_n,
      },
      supporting_work: request.playable_target ? [{
        resolution: "resolved",
        kind: "dmb_plan_playable_target_v1",
        object_id: request.playable_target.id,
        revision: "v2",
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
  const response: WorldPlanAgentTurnResponse = {
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
        work_revision_id: "00000000-0000-4000-8000-000000000004",
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
  return planContext ? { ...response, schema: "dmb_agent_turn_response_v2", plan_context: planContext } : response;
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

beforeAll(() => {
  Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
});

beforeEach(() => {
  serverHistoryTurns = [];
  vi.spyOn(liveApi,"getWorldPlanConversationActions").mockImplementation(async(world,conversation)=>({schema_version:"dmb_world_plan_action_conversation_projection_v1",world_id:world,conversation_id:conversation,actions:[],next_before_action_sequence:null} as any));
  vi.spyOn(liveApi, "getWorldAgentConversationHistory").mockImplementation(async (owner) => ({
    schema: "dmb_agent_conversation_history_v3",
    world_id: owner,
    conversation_state: "active",
    conversation_id: "11111111-1111-4111-8111-111111111111",
    active_conversation_id: "11111111-1111-4111-8111-111111111111",
    pointer_revision: 1,
    turns: [...serverHistoryTurns],
    next_before_sequence: null,
  }));
  vi.spyOn(liveApi, "getWorldPlanDocumentEditActions").mockImplementation(async (owner, documentId) => {
    const committed = { object_revision: 7, work_revision_id: "00000000-0000-4000-8000-000000000004", revision_n: 4, content_sha256: "b".repeat(64) };
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
  vi.useRealTimers();
  vi.unstubAllGlobals();
  liveApi.setNativeGraphAccessToken(null);
  vi.restoreAllMocks();
  localStorage.clear();
  sessionStorage.clear();
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
      evidenceRefId: "ev:s25",
      sourceArtifactId: "artifact:s25",
      sourceRevisionId: "artifact-rev:s25",
      contentSha256: "a".repeat(64),
      sourceSpanRefId: "span:s25",
      sourceDomain: "session_recap",
      provenanceStatus: "excerpt_ready",
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
  await waitFor(() => expect(projectionRequest).toHaveBeenCalledWith(expect.objectContaining({ managedWorldId: owner }), expect.any(AbortSignal)));
  fireEvent.click(await screen.findByRole("button", { name: "Open", exact: true }));
  const documentReference = await screen.findByRole("button", { name: "Ironveil Warehouse" });
  const editorDom = screen.getByTestId("world-owned-plan-markdown-editor").querySelector(".ProseMirror") as HTMLElement & { editor: import("@tiptap/core").Editor };
  const editorContent = editorDom.editor.getJSON();
  fireEvent.click(documentReference);
  const inspector = await screen.findByRole("dialog", { name: "World Graph object" });
  expect(inspector).toHaveClass("world-plan-graph-reference-inspector");
  const agentConversation = screen.getByRole("region", { name: "World conversation" });
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
  expect(documentReference.isConnected).toBe(true);
  expect(screen.getByRole("region", { name: "World conversation" })).toBe(agentConversation);
  expect(agentConversation?.textContent).toBe(conversationText);
  const cardsTab = within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" });
  fireEvent.click(cardsTab);
  const cards = await screen.findByRole("region", { name: "Focused Plan scene" });
  expect(documentReference.closest(".world-plan-document-view")).not.toHaveAttribute("hidden");
  fireEvent.click(within(inspector).getByRole("button", { name: "Close Ironveil Warehouse" }));
  await waitFor(() => expect(documentReference).toHaveFocus());

  expect(within(cards).getByText(/before entering\./)).toBeInTheDocument();
  const cardReference = await within(cards).findByRole("button", { name: "Ironveil Warehouse" });
  expect(cardReference).toBe(documentReference);
  expect(cardReference).toHaveFocus();
  fireEvent.click(cardReference);
  const cardInspector = await screen.findByRole("dialog", { name: "World Graph object" });
  expect(cardReference.isConnected).toBe(true);
  expect(cards.querySelectorAll('button.recap-node-token[data-graph-node-id="loc:ironveil-warehouse"]')).toHaveLength(1);
  await waitFor(() => expect(completeRead).toHaveBeenCalledTimes(2));
  expect(within(cardInspector).getByRole("article", { name: "Ironveil Warehouse World Graph object" })).toBeInTheDocument();
  expect(within(cards).getByText(/before entering\./)).toBeInTheDocument();
  fireEvent.click(await within(cardInspector).findByRole("button", { name: "Read source" }));
  expect(await screen.findByRole("dialog", { name: "Pinned source passage" })).toBeInTheDocument();
  expect(cardReference.isConnected).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Back to World Graph object" }));
  expect(await screen.findByRole("dialog", { name: "World Graph object" })).toBeInTheDocument();
  expect(cardReference.isConnected).toBe(true);
  fireEvent.click(within(cardInspector).getByRole("button", { name: "Close Ironveil Warehouse" }));
  const restoredCardReference = within(cards).getByRole("button", { name: "Ironveil Warehouse" });
  expect(restoredCardReference).toBe(cardReference);
  await waitFor(() => expect(restoredCardReference).toHaveFocus());

  fireEvent.click(restoredCardReference);
  const reverseInspector = await screen.findByRole("dialog", { name: "World Graph object" });
  fireEvent.click(await within(reverseInspector).findByRole("button", { name: "Read source" }));
  expect(await screen.findByRole("dialog", { name: "Pinned source passage" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Back to World Graph object" }));
  expect(await screen.findByRole("dialog", { name: "World Graph object" })).toBeInTheDocument();
  const documentTab = within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Document" });
  fireEvent.click(documentTab);
  expect(screen.getByTestId("world-plan-document-view")).not.toHaveAttribute("hidden");
  fireEvent.click(within(reverseInspector).getByRole("button", { name: "Close Ironveil Warehouse" }));
  await waitFor(() => expect(restoredCardReference).toHaveFocus());
  expect(screen.queryByRole("region", { name: "Focused Plan scene" })).not.toBeInTheDocument();
  expect(editorDom.isConnected).toBe(true);
  expect(editorDom.editor.getJSON()).toEqual(editorContent);
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

  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  vi.useFakeTimers();
  await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
});

it("retains the mounted Plan and typed question across Cards, Document and dock collapse without dispatch", async () => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, twoScenePlanMarkdown);
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>);
  const input = await screen.findByLabelText("Message DungeonBuddy");
  await waitFor(() => expect(input).toBeEnabled());
  const reader = screen.getByRole("region", {name:"Plan workspace"});
  expect(screen.queryByRole("log")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Open", exact: true }));
  fireEvent.change(input, {target:{value:"Remember the warehouse"}});
  const transcript = screen.getByRole("log");
  fireEvent.click(screen.getByRole("button", { name: "Expand conversation fullscreen" }));
  expect(reader.isConnected).toBe(true);
  expect(reader).toHaveAttribute("hidden");
  expect(screen.getByRole("log")).toBe(transcript);
  expect(screen.getByLabelText("Message DungeonBuddy")).toBe(input);
  expect(input).toHaveValue("Remember the warehouse");
  fireEvent.click(screen.getByRole("button", { name: "Restore conversation dock" }));
  expect(reader).not.toHaveAttribute("hidden");
  expect(screen.getByRole("log")).toBe(transcript);
  fireEvent.click(screen.getByRole("button", {name:"Cards",exact:true}));
  const focusedScene = await screen.findByRole("region", {name:"Focused Plan scene"});
  expect(focusedScene).toHaveTextContent("Arrival");
  fireEvent.click(screen.getByRole("button", {name:"Close conversation",exact:true}));
  expect(transcript.isConnected).toBe(true);
  expect(input.isConnected).toBe(true);
  expect(screen.queryByRole("log")).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", {name:"Document",exact:true}));
  fireEvent.click(screen.getByRole("button", {name:"Open",exact:true}));
  expect(screen.getByRole("region", {name:"Plan workspace"})).toBe(reader);
  expect(screen.getByLabelText("Message DungeonBuddy")).toBe(input);
  expect(screen.getByRole("log")).toBe(transcript);
  expect(input).toHaveValue("Remember the warehouse");
  expect(screen.queryByTestId("agent-interaction-chrome")).toBeNull();
  expect(screen.getAllByTestId("agent-interaction-open")).toHaveLength(1);
  expect(postTurn).not.toHaveBeenCalled();
});

it("restores Cards from the matching Plan URL after reopen and keeps the local editor draft", async () => {
  const record = mockSavedPlanForAgent(savedAgentPlanId, 7, 7, twoScenePlanMarkdown);
  const location = `/plan?world=${worldId}&documentId=${record.document_id}&view=cards`;
  window.history.replaceState({}, "", location);
  const pageTree = (
    <SelectedWorldProvider locationSnapshot={location}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>
  );
  const firstMount = render(pageTree);
  const page = await screen.findByTestId("world-owned-plan");
  const cards = within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" });
  const document = within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Document" });
  await waitFor(() => expect(cards).toHaveAttribute("aria-pressed", "true"));
  expect(screen.getByTestId("world-plan-document-view")).not.toHaveAttribute("hidden");
  const contextIdentity = screen.getByTestId("world-plan-context-identity").textContent;
  expect(contextIdentity).not.toBe("none");

  fireEvent.click(document);
  expect(new URLSearchParams(window.location.search).get("view")).toBeNull();
  const editorSurface = screen.getByTestId("world-owned-plan-markdown-editor");
  const editor = editorSurface.querySelector("[contenteditable]");
  expect(editor).not.toBeNull();
  const tiptap = (editor as HTMLElement & { editor: import("@tiptap/core").Editor }).editor;
  act(() => { tiptap.commands.insertContent("Draft survives Cards and reload "); });
  const draftKey = `dmb:world-plan-local-draft:v2:${worldId}`;
  await waitFor(() => expect(JSON.parse(localStorage.getItem(draftKey) ?? "null").markdown)
    .toContain("Draft survives Cards and reload"));

  fireEvent.click(cards);
  expect(new URLSearchParams(window.location.search).get("view")).toBe("cards");
  expect(cards).toHaveAttribute("aria-pressed", "true");
  const savedDraft = JSON.parse(localStorage.getItem(draftKey) ?? "null").markdown;
  firstMount.unmount();

  render(pageTree);
  const reopenedPage = await screen.findByTestId("world-owned-plan");
  const reopenedCards = within(await screen.findByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" });
  await waitFor(() => expect(reopenedCards).toHaveAttribute("aria-pressed", "true"));
  expect(screen.getByTestId("world-plan-document-view")).not.toHaveAttribute("hidden");
  expect(screen.getByTestId("world-plan-context-identity").textContent).toBe(contextIdentity);
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Document" }));
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("Draft survives Cards and reload");
  expect(JSON.parse(localStorage.getItem(draftKey) ?? "null").markdown).toBe(savedDraft);
});

it("clears the Cards route when opening a different saved Plan identity", async () => {
  const documentA = savedAgentPlanId;
  const documentB = "saved-plan-card-route-b";
  const recordA = mockSavedPlanForAgent(documentA, 7, 7, twoScenePlanMarkdown);
  const recordB = worldPlanRecord(documentB, worldId, 3);
  recordB.title = "Second Plan";
  vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [recordA, recordB],
  });
  const snapshot = (record: WorldOwnedPlanRecordV2, markdown: string) => ({
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown,
    content_sha256: "c".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: record.revision,
  });
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockImplementation(async (id) =>
    id === documentB ? snapshot(recordB, "# Second Plan\n") : snapshot(recordA, twoScenePlanMarkdown));
  const location = `/plan?world=${worldId}&documentId=${documentA}&view=cards`;
  window.history.replaceState({}, "", location);
  render(
    <SelectedWorldProvider locationSnapshot={location}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  const page = await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" })).toHaveAttribute("aria-pressed", "true"));

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentB } });
  await waitFor(() => expect(screen.getByLabelText("Plan title")).toHaveValue("Second Plan"));
  expect(new URLSearchParams(window.location.search).get("documentId")).toBe(documentB);
  expect(new URLSearchParams(window.location.search).get("view")).toBeNull();
  expect(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Document" })).toHaveAttribute("aria-pressed", "true");
  expect(screen.getByTestId("world-plan-document-view")).not.toHaveAttribute("hidden");
  expect(screen.queryByRole("region", { name: "Focused Plan scene" })).not.toBeInTheDocument();
  expect(screen.getByTestId("world-plan-publication")).toHaveAttribute("data-work-object", `document:${documentB}`);
});

it("binds Ask to the exact committed revision and complete current working draft", async () => {
  mockSavedPlanForAgent();
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => worldPlanAgentResponse(request));
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  await openPlanConversation();
  expect(await screen.findByRole("region", { name: "World conversation" })).toBeInTheDocument();
  expect(messageDungeonBuddyField()).toBeEnabled();

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
    "plan_context_policy",
    "plan_authoring_capture",
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
    plan_context_policy: { schema: "dmb_plan_context_policy_v1", policy: "auto_plan_world" },
    message: "What Plan metadata can you see?",
  });
  expect(request.plan_authoring_capture?.draft_markdown).toBe(defaultMarkdownDocumentAdapter.exportMarkdown(JSON.parse(request.plan_authoring_capture!.editor_json)));
  expect(JSON.stringify(request)).not.toContain("Of Conks Session Plan");
  expect(JSON.stringify(request)).not.toContain(`out/workspace/plan/${savedAgentPlanId}.md`);
  expect(JSON.stringify(request)).not.toContain(planAgentNamespace());

  expect(serverHistoryTurns).toHaveLength(2);
  const conversation = screen.getByRole("region", { name: "World conversation" });
  const renderedTurns = [...conversation.querySelectorAll("article[data-sequence]")];
  expect(renderedTurns.map((turn) => turn.getAttribute("data-sequence"))).toEqual(["1", "2"]);
  expect(renderedTurns[0]).toHaveTextContent("What Plan metadata can you see?");
  expect(renderedTurns[1]).toHaveTextContent("And what is its saved revision?");
  expect(renderedTurns.every((turn) => turn.textContent?.includes(`plan ${savedAgentPlanId} · revision 4`))).toBe(true);
  expect(liveApi.getWorldAgentConversationHistory).toHaveBeenCalledWith(worldId, expect.objectContaining({ limit: 50, includeTurnCorrelation: true, signal: expect.any(AbortSignal) }));
  expect(liveApi.getWorldOwnedPlanCommittedRevision).toHaveBeenCalledTimes(3);
  expect(serverHistoryTurns.map((turn) => turn.user_text)).toEqual([
    "What Plan metadata can you see?", "And what is its saved revision?",
  ]);
  expect(serverHistoryTurns.every((turn) => turn.provenance.primary_work.object_id === savedAgentPlanId)).toBe(true);
  expect(localStorage.getItem(threadStorageKey(planAgentNamespace(), request.client_thread_id))).toBeNull();
  expect(JSON.stringify(localStorage)).not.toContain(savedAgentPlanText);
  expect(JSON.stringify(localStorage)).not.toContain("MUST_NOT_BE_PERSISTED");
});

it("targets the current focused scene and records its immutable saved basis", async () => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, currentTwoScenePlanMarkdown);
  const post = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async request => worldPlanAgentResponse(request));
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>);
  const conversation = await openPlanConversation();
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" }));
  await screen.findByRole("region", { name: "Focused Plan scene" });
  expect(screen.queryByRole("button", { name: /Select for Ask|Selected for Ask|Back to outline/ })).not.toBeInTheDocument();
  act(() => capturedPlanControls().changeTitle({ target: { value: "Unsaved local title" } }));
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What happens at the arrival?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(post).toHaveBeenCalledOnce());
  expect(post.mock.calls[0][0]).toMatchObject({
    playable_target: { schema: "dmb_plan_playable_target_v1", kind: "scene", id: "scene:arrival" },
    primary_work: { object_id: savedAgentPlanId, expected_revision: 7, expected_revision_n: 4, expected_content_sha256: "b".repeat(64) },
    client_work_state: "saved_dirty",
  });
  expect(JSON.stringify(post.mock.calls[0][0])).not.toContain(currentTwoScenePlanMarkdown);
  await within(conversation).findByText("The keeper is below the black arch.");
  expect(serverHistoryTurns[0].provenance.supporting_work).toMatchObject([{ object_id: "scene:arrival", revision: "v2" }]);
  expect(serverHistoryTurns[0].provenance.primary_work).toMatchObject({ object_revision: 7, revision_n: 4 });
});

it("keeps submitted scene identity fixed while focus changes during basis verification", async () => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, currentTwoScenePlanMarkdown);
  const getCommitted = vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision);
  const basis = await liveApi.getWorldOwnedPlanCommittedRevision(savedAgentPlanId);
  const post = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async request => worldPlanAgentResponse(request));
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>);
  const conversation = await openPlanConversation();
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" }));
  const reader = await screen.findByRole("region", { name: "Focused Plan scene" });
  let release!: (value: WorldOwnedCommittedRevisionV2) => void;
  getCommitted.mockImplementationOnce(() => new Promise(resolve => { release = resolve; }));
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What happens at the arrival?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(release).toBeTypeOf("function"));
  fireEvent.click(within(reader).getByRole("button", { name: "Next scene" }));
  expect(screen.getByRole("button", { name: "Show scene: Warehouse" })).toHaveAttribute("aria-current", "true");
  await act(async () => { release(basis); });
  await waitFor(() => expect(post).toHaveBeenCalledOnce());
  expect(post.mock.calls[0][0].playable_target).toEqual({ schema: "dmb_plan_playable_target_v1", kind: "scene", id: "scene:arrival" });
  await within(conversation).findByText("The keeper is below the black arch.");
  expect(serverHistoryTurns[0].provenance.supporting_work[0].object_id).toBe("scene:arrival");
});

it("follows focused Scene for a new Ask and Edit while a pending Ask retains its captured scene", async () => {
  mockSavedPlanForAgent(savedAgentPlanId, 7, 7, twoScenePlanMarkdown);
  const finishTurns: Array<(response: WorldPlanAgentTurnResponse) => void> = [];
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(() => (
    new Promise((resolve) => { finishTurns.push(resolve); })
  ));
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  const page = await screen.findByTestId("world-owned-plan");
  await openPlanConversation();
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" }));

  const reader = await screen.findByRole("region", { name: "Focused Plan scene" });
  const conversation = savedWorldPlanConversation();
  expect(await within(conversation).findByRole("group", { name: "Question focus" })).toHaveTextContent("Arrival");
  openAdvancedDetails(conversation);
  expect(within(conversation).getByText(/Card basis · object revision 7 · SHA-256/)).toBeInTheDocument();
  expect(within(reader).queryByRole("button", { name: "Select for Edit" })).not.toBeInTheDocument();
  expect(within(conversation).getByRole("group", { name: "Selected change target" })).toHaveTextContent("Arrival");

  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What happens at the arrival?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(1));
  const request = postTurn.mock.calls[0]![0];
  expect(request.playable_target).toEqual({ schema: "dmb_plan_playable_target_v1", kind: "scene", id: "scene:arrival" });
  expect(request.primary_work).toMatchObject({ expected_revision: 7, expected_content_sha256: "b".repeat(64) });

  fireEvent.click(within(reader).getByRole("button", { name: "Next scene" }));
  expect(within(savedWorldPlanConversation()).getByRole("group", { name: "Question focus" })).toHaveTextContent("Warehouse");
  expect(within(savedWorldPlanConversation()).getByRole("group", { name: "Selected change target" })).toHaveTextContent("Warehouse");
  expect(postTurn).toHaveBeenCalledTimes(1);

  await act(async () => finishTurns[0]!(worldPlanAgentResponse(request)));
  expect(await within(conversation).findByText(/Playable target: scene scene:arrival · marker grammar v2/)).toBeInTheDocument();
  expect(within(conversation).getByRole("group", { name: "Question focus" })).toHaveTextContent("Warehouse");
  expect(within(conversation).getByRole("group", { name: "Selected change target" })).toHaveTextContent("Warehouse");
  expect(postTurn).toHaveBeenCalledTimes(1);

  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "What is happening at the warehouse?" } });
  sendDiscussMessage(conversation);
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(2));
  const warehouseRequest = postTurn.mock.calls[1]![0];
  expect(warehouseRequest.playable_target).toEqual({ schema: "dmb_plan_playable_target_v1", kind: "scene", id: "scene:warehouse" });
  expect(warehouseRequest.primary_work).toMatchObject({ expected_revision: 7, expected_content_sha256: "b".repeat(64) });
  await act(async () => finishTurns[1]!(worldPlanAgentResponse(warehouseRequest)));
  expect(await within(conversation).findByText(/Playable target: scene scene:warehouse · marker grammar v2/)).toBeInTheDocument();
  expect(postTurn).toHaveBeenCalledTimes(2);
});

it("clears the previous saved Ask target when focus moves to a draft-only Scene", async () => {
  const committedMarkdown = twoScenePlanMarkdown.replace(
    /<!-- dmb-playable-element:v2 kind=scene id=scene:warehouse -->[\s\S]*$/,
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
  await openPlanConversation();
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" }));
  const reader = await screen.findByRole("region", { name: "Focused Plan scene" });
  const conversation = savedWorldPlanConversation();
  expect(within(conversation).getByRole("group", { name: "Question focus" })).toHaveTextContent("Arrival");
  fireEvent.change(messageDungeonBuddyField(conversation), { target: { value: "A question not yet sent" } });

  fireEvent.click(within(reader).getByRole("button", { name: "Next scene" }));
  expect(screen.getByRole("button", {name:"Show scene: Warehouse"})).toHaveAttribute("aria-current","true");
  expect(within(conversation).queryByRole("group", { name: "Question focus" })).not.toBeInTheDocument();
  expect(messageDungeonBuddyField(conversation)).toHaveValue("A question not yet sent");
  expect(postTurn).not.toHaveBeenCalled();
  expect(committedRevision).toHaveBeenCalledTimes(1);
  expect(window.location.pathname + window.location.search).toBe(`/plan?world=${worldId}&documentId=${savedAgentPlanId}&view=cards`);
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

  await openPlanConversation();
  const newConversation = screen.getByRole("button", { name: "New conversation" });
  expect(newConversation.closest(".conversation-dock__header")).toBeInTheDocument();
  expect(newConversation.querySelector("svg")).toBeInTheDocument();
  expect(newConversation).toHaveAttribute("title", "New conversation");
  fireEvent.click(screen.getByTitle("Conversation options"));
  expect(screen.getByTitle("Conversation options").closest("details")).not.toContainElement(newConversation);
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
  await openPlanConversation();
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
  await openPlanConversation();
  const conversation = await screen.findByRole("region", { name: "World conversation" });
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
  let finishTurn: ((response: WorldPlanAgentTurnResponse) => void) | undefined;
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
  await openPlanConversation();
  const conversation = await screen.findByRole("region", { name: "World conversation" });
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
  await openPlanConversation();
  const firstConversation = await screen.findByRole("region", { name: "World conversation" });
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
  await openPlanConversation();
  const reloadedConversation = await screen.findByRole("region", { name: "World conversation" });
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
  await openPlanConversation();
  expect(await screen.findByText("Conversation paused while the Plan is saving.")).toBeInTheDocument();
  expect(messageDungeonBuddyField()).toBeEnabled();
  expect(within(screen.getByRole("region", { name: "World conversation" })).getByRole("button", { name: "Send message" })).toBeDisabled();
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
  await openPlanConversation();
  await waitFor(() => expect(screen.getByText("Plan A transcript answer")).toBeInTheDocument());

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentB } });
  await waitFor(() => expect(screen.getByText("Plan B transcript answer")).toBeInTheDocument());
  expect(screen.queryByText("Plan A transcript answer")).not.toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentA } });
  await waitFor(() => expect(screen.getByText("Plan A transcript answer")).toBeInTheDocument());
  expect(screen.queryByText("Plan B transcript answer")).not.toBeInTheDocument();

  view.unmount();
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentA}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );
  await openPlanConversation();
  await waitFor(() => expect(screen.getByText("Plan A transcript answer")).toBeInTheDocument());
  expect(screen.queryByText("Plan B transcript answer")).not.toBeInTheDocument();
});

it("retains a completed pending turn with its original Plan provenance after changing documents", async () => {
  const documentA = savedAgentPlanId;
  const documentB = "saved-plan-agent-test-b";
  const recordA = mockSavedPlanForAgent(documentA);
  const recordB = worldPlanRecord(documentB, worldId, 4);
  recordB.title = "Second Of Conks Plan";
  const snapshot = (record: WorldOwnedPlanRecordV2, markdown: string) => ({
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown,
    content_sha256: record.document_id===documentA?"b".repeat(64):"e".repeat(64),
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
  let resolveTurn!: (value: WorldPlanAgentTurnResponse) => void;
  const pendingTurn = new Promise<WorldPlanAgentTurnResponse>((resolve) => { resolveTurn = resolve; });
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockReturnValue(pendingTurn);

  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${documentA}`}>
      <WorldHostedPlanPage />
    </SelectedWorldProvider>,
  );
  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  await openPlanConversation();
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "This answer belongs only to Plan A." } });
  sendDiscussMessage();
  await waitFor(() => expect(postTurn).toHaveBeenCalledTimes(1));
  const request = postTurn.mock.calls[0][0];

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: documentB } });
  await waitFor(() => expect(screen.getByLabelText("Plan title")).toHaveValue(recordB.title));
  await act(async () => resolveTurn(worldPlanAgentResponse(request)));

  await screen.findByText("The keeper is below the black arch.");
  expect(serverHistoryTurns[0].provenance.primary_work.object_id).toBe(documentA);
  expect(screen.getByLabelText("Plan document")).toHaveValue(documentB);
  expect(postTurn).toHaveBeenCalledOnce();
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
  await openPlanConversation();
  expect(await screen.findByLabelText("Message DungeonBuddy")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  await waitFor(() => expect(prepare).toHaveBeenCalledTimes(1));
  expect(screen.getByText("Conversation paused while the Plan is saving.")).toBeInTheDocument();
  expect(messageDungeonBuddyField()).toBeEnabled();
  expect(within(screen.getByRole("region", { name: "World conversation" })).getByRole("button", { name: "Send message" })).toBeDisabled();
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
  expect(messageDungeonBuddyField()).toBeEnabled();
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

const invalidWorldPlanResponses: Array<[string, (response: WorldPlanAgentTurnResponse) => void]> = [
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

it.each(invalidWorldPlanResponses)("refuses an unacknowledged reply and retains exact recovery for %s", async (_description, mutate) => {
  mockSavedPlanForAgent();
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn").mockImplementation(async (request) => {
    const response = worldPlanAgentResponse(request);
    // No durable APP acknowledgement is modeled for this malformed delivery.
    serverHistoryTurns.pop();
    mutate(response);
    return response;
  });
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}>
      <AgentEnabledPlanPage />
    </SelectedWorldProvider>,
  );

  expect(await screen.findByTestId("world-owned-plan")).toBeInTheDocument();
  await openPlanConversation();
  fireEvent.change(messageDungeonBuddyField(), { target: { value: "Question that must not be saved" } });
  sendDiscussMessage();
  await screen.findByText(/1 saved Ask outcome needs a history check/);
  expect(postTurn).toHaveBeenCalledTimes(1);

  const request = postTurn.mock.calls[0][0];
  const recovery = Object.keys(localStorage).filter(key => key.startsWith("dmb:world-plan-pending-ask:v1:"))
    .map(key => JSON.parse(localStorage.getItem(key)!));
  expect(recovery).toHaveLength(1);
  expect(recovery[0].request).toEqual(request);
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
  await openPlanConversation();
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
    title: request.title!,
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
    title: "Edited during commit",
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 5,
    committed_revision: 2,
    committed_record: { ...record, title: "Edited during commit", revision: 5, content_status: "committed" },
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
    title: unrelated.title,
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
    title: unrelated.title,
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
  fireEvent.click(screen.getByRole("button", { name: "New Plan" }));
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
  expect(screen.getByRole("button", { name: "New Plan" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Restore recovered draft into this Plan" })).toBeDisabled();
  const discardButtons = screen.getAllByRole("button", { name: "Discard recovered draft" });
  expect(discardButtons.length).toBeGreaterThan(0);
  for (const button of discardButtons) expect(button).toBeDisabled();
  const retry = screen.getByRole("button", { name: "Retry Plan load" });
  expect(retry).toBeEnabled();

  fireEvent.click(screen.getByRole("button", { name: "New Plan" }));
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
  expect(screen.getByRole("button", { name: "New Plan" })).toBeDisabled();
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

it("opens shared session preparation from the exact saved Plan without unmounting its scene", async () => {
  const record = mockSavedPlanForAgent(savedAgentPlanId, 7, 7, currentTwoScenePlanMarkdown);
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
    markdown: currentTwoScenePlanMarkdown,
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
  const page = screen.getByTestId("world-owned-plan");
  const bar = screen.getByTestId("surface-context-host");
  expect(bar).toContainElement(start);
  expect(bar).toContainElement(screen.getByRole("group", { name: "Plan view" }));
  expect(within(page).queryByRole("group", { name: "Plan view" })).not.toBeInTheDocument();
  expect(within(page).queryByText("Plan changes stay local until you choose Save Plan.")).not.toBeInTheDocument();
  fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Cards" }));
  const reader = await screen.findByRole('region',{name:'Focused Plan scene'});
  const mountedEditor=screen.getByTestId('world-owned-plan-markdown-editor');
  const beforeText=mountedEditor.textContent;
  expect(screen.getByRole('button',{name:'Show scene: Arrival'})).toHaveAttribute('aria-current','true');
  fireEvent.click(within(reader).getByRole('button',{name:'Next scene'}));
  expect(screen.getByRole('button',{name:'Show scene: Warehouse'})).toHaveAttribute('aria-current','true');
  fireEvent.click(start);

  await screen.findByRole('heading',{name:'Play this Plan'});
  expect(window.location.pathname).toBe('/plan');
  expect(new URLSearchParams(window.location.search).get('documentId')).toBe(record.document_id);
  expect(screen.getByTestId('world-owned-plan-markdown-editor')).toBe(mountedEditor);
  expect(mountedEditor.textContent).toBe(beforeText);
  expect(screen.getByRole('button',{name:'Show scene: Warehouse'})).toHaveAttribute('aria-current','true');
  expect(getCommitted).toHaveBeenCalledWith(record.document_id);
});

it.each(["lf", "crlf", "changed-body", "changed-space", "changed-hash", "changed-world", "changed-revision", "working-copy", "edit-during-check"] as const)(
  "starts Play after canonical authoring save without reopening, preserving guards: %s", async (mode) => {
    const initial = mode === "crlf" ? currentTwoScenePlanMarkdown.replace(/\n/g, "\r\n") : currentTwoScenePlanMarkdown;
    const record = mockSavedPlanForAgent(savedAgentPlanId, 7, 7, initial);
    const prior = await liveApi.getWorldOwnedPlanCommittedRevision(savedAgentPlanId);
    const getCommitted = vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue({
      ...prior, work_revision_id: "cccccccc-cccc-4ccc-8ccc-cccccccccccc", has_divergent_working_copy: false,
    });
    vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async request => ({
      schema_version: "dmb_tiptap_markdown_write_prepare_v2", scope_mode: "world", world_id: worldId,
      document_id: savedAgentPlanId, title: request.title!, target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!, registry_revision: 8, file_exists: true,
      writer_ok: true, writer_confirm_token: "canonical-save", warnings: [], diagnostics: [],
    }));
    let saved!: WorldOwnedCommittedRevisionV2;
    const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async request => {
      // Actual writer normalization, rather than an echo of submitted bytes.
      const markdown = (request.markdown.replace(/\n+$/, "") + "\n").replace(/\r\n?/g, "\n");
      const digest = createHash("sha256").update(markdown).digest("hex");
      saved = { ...prior, object_revision: 9, revision_n: 5, title: request.title!,
        work_revision_id: "dddddddd-dddd-4ddd-8ddd-dddddddddddd", markdown, content_sha256: digest,
        has_divergent_working_copy: false };
      getCommitted.mockResolvedValue(saved);
      return { schema_version: "dmb_tiptap_markdown_write_commit_v2", scope_mode: "world", world_id: worldId,
        document_id: savedAgentPlanId, title: request.title!, target_relpath: record.target_relpath!,
        target_display_path: record.target_relpath!, registry_revision: 9, committed_revision: 9,
        committed_record: { ...record, title: request.title!, revision: 9 },
        normalized_content_sha256: digest, writer_ok: true, writer_phase: "commit", diagnostics: [] };
    });
    const location = `/plan?world=${worldId}&documentId=${savedAgentPlanId}`;
    window.history.replaceState({}, "", location);
    render(<SelectedWorldProvider locationSnapshot={location}><VerifiedPlanPage /></SelectedWorldProvider>);
    await screen.findByTestId("world-owned-plan-markdown-editor");
    await waitFor(() => expect(screen.getByTestId("world-plan-start-play")).toBeEnabled());
    const mounted = screen.getByTestId("world-owned-plan-markdown-editor");
    if (mode === "crlf") act(() => capturedPlanControls().changeTitle({ target: { value: "Renamed canonical Plan" } }));
    else {
      fireEvent.click(within(screen.getByRole("group", { name: "Plan view" })).getByRole("button", { name: "Markdown" }));
      fireEvent.change(screen.getByRole("textbox", { name: "Plan Markdown" }), { target: { value: initial + "\n\n" } });
    }
    await act(async () => { capturedPlanControls().save(); });
    await waitFor(() => expect(commit).toHaveBeenCalledOnce());
    const submitted = commit.mock.calls[0][0].markdown;
    if (mode === "crlf") expect(submitted).toContain("\r\n");
    else expect(submitted).toMatch(/\n{3}$/);
    expect(saved.markdown).not.toBe(submitted);
    const start = screen.getByTestId("world-plan-start-play");
    await waitFor(() => expect(start).toBeEnabled());
    if (mode === "changed-body") getCommitted.mockResolvedValue({ ...saved, markdown: saved.markdown.replace("keeper", "stranger") });
    if (mode === "changed-hash") getCommitted.mockResolvedValue({ ...saved, content_sha256: "f".repeat(64) });
    if (mode === "changed-space") getCommitted.mockResolvedValue({ ...saved, markdown: saved.markdown.replace("keeper", "keeper ") });
    if (mode === "changed-world") getCommitted.mockResolvedValue({ ...saved, world_id: "foreign-world" });
    if (mode === "changed-revision") getCommitted.mockResolvedValue({ ...saved, object_revision: saved.object_revision + 1 });
    if (mode === "working-copy") getCommitted.mockResolvedValue({ ...saved, has_divergent_working_copy: true });
    let release!: (value: WorldOwnedCommittedRevisionV2) => void;
    if (mode === "edit-during-check") getCommitted.mockImplementationOnce(() => new Promise(resolve => { release = resolve; }));
    fireEvent.click(start);
    if (mode === "edit-during-check") {
      act(() => capturedPlanControls().changeTitle({ target: { value: "New unsaved title" } }));
      await act(async () => { release(saved); });
    }
    if (mode === "lf" || mode === "crlf") {
      await screen.findByRole("heading", { name: "Play this Plan" });
      expect(planEncounterCapture.context?.verifiedPlan).toEqual({revisionN:saved.revision_n,workRevisionId:saved.work_revision_id,contentSha256:saved.content_sha256});
      expect(screen.queryByTestId("world-plan-start-play-error")).not.toBeInTheDocument();
      expect(screen.getByTestId("world-owned-plan-markdown-editor")).toBe(mounted);
      expect(JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)!).markdown).toBe(submitted);
      expect(window.location.pathname).toBe("/plan");
    } else {
      await screen.findByTestId("world-plan-start-play-error");
      expect(planEncounterCapture.context?.verifiedPlan).toBeNull();
      expect(screen.queryByRole("heading", { name: "Play this Plan" })).not.toBeInTheDocument();
    }
  },
);

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
  const unsupportedMarkdown = "# Plan\n\n<widget>Unrepresentable widget.</widget>\n";
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
  if (textWalker.nextNode()) textNode = textWalker.currentNode as Text;
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
  expect(screen.getByRole("alert")).toHaveTextContent(/Hard breaks in headings or table cells/i);
  expect(localStorage.getItem(recoveryKey)).toBe(originalRecovery);
  const restoredEditor = editorSurface.querySelector(".ProseMirror") as HTMLElement;
  expect(restoredEditor).not.toBe(proseMirror);
  expect(restoredEditor).toHaveTextContent("The keeper waits beneath the black arch.");
  expect(restoredEditor.querySelector("br")).not.toBeInTheDocument();
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
});


it.each(["append","promote","decision"])("authors playable structure through Plan toolbar and explicit Save, retaining identities after reopen (%s)", async mode => {
  vi.spyOn(window,"scrollBy").mockImplementation(()=>{});
  const rect=DOMRect.fromRect({x:0,y:0,width:1,height:1});
  const oldRects=Object.getOwnPropertyDescriptor(Range.prototype,"getClientRects");
  const oldRect=Object.getOwnPropertyDescriptor(Range.prototype,"getBoundingClientRect");
  Object.defineProperty(Range.prototype,"getClientRects",{configurable:true,value:()=>[rect]});
  Object.defineProperty(Range.prototype,"getBoundingClientRect",{configurable:true,value:()=>rect});
  try {
    const envelope="---\r\ntitle: Preserved Plan metadata\r\n---\r\n";
    const record=mockSavedPlanForAgent(savedAgentPlanId,7,7,envelope+"# Authored session\n\nSource quotation retained.\n"+(mode==="promote"?"\n## Preparation\n\n### Arrival\n\n| Lead | Choice |\n| --- | --- |\n| Tavern | Optional |\n":""));
    const prepare=vi.spyOn(liveApi,"prepareTiptapMarkdownWrite").mockResolvedValue({schema_version:"dmb_tiptap_markdown_write_prepare_v2",scope_mode:"world",world_id:worldId,document_id:savedAgentPlanId,title:"Renamed typed Plan",target_relpath:record.target_relpath!,target_display_path:record.target_relpath!,registry_revision:8,file_exists:true,writer_ok:true,writer_confirm_token:"structure-save",warnings:[],diagnostics:[]});
    let saved="";
    const commit=vi.spyOn(liveApi,"commitWorldOwnedPlanMarkdownWrite").mockImplementation(async request=>{
      saved=request.markdown;const digest=createHash("sha256").update(saved).digest("hex");const nextRecord={...record,title:request.title!,revision:9};
      const prior=await liveApi.getWorldOwnedPlanCommittedRevision(savedAgentPlanId);
      vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue({...prior,object_revision:9,revision_n:5,work_revision_id:"structure-work-revision",markdown:saved,content_sha256:digest,has_divergent_working_copy:false});
      vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockResolvedValue({schema_version:"dmb_workspace_document_snapshot_v2",record:nextRecord,markdown:saved,content_sha256:digest,file_fingerprint:"postgres",file_exists:true,loaded_revision:9});
      return {schema_version:"dmb_tiptap_markdown_write_commit_v2",scope_mode:"world",world_id:worldId,document_id:savedAgentPlanId,title:request.title!,target_relpath:record.target_relpath!,target_display_path:record.target_relpath!,registry_revision:9,committed_revision:9,committed_record:nextRecord,normalized_content_sha256:digest,writer_ok:true,writer_phase:"commit",diagnostics:[]};
    });
    const pageTree=<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>;
    window.history.replaceState({}, "", `/plan?world=${worldId}&documentId=${savedAgentPlanId}`);
    const mounted=render(pageTree);
    await screen.findByTestId("world-owned-plan");
    const beat=await screen.findByRole("button",{name:"Add Beat",exact:true});
    await waitFor(()=>expect(beat).toBeEnabled());
    fireEvent.change(screen.getByRole("textbox",{name:"Plan title",exact:true}),{target:{value:"Renamed typed Plan"}});
    expect(screen.getByRole("button",{name:"Add Scene to this Beat"})).toBeDisabled();
    const oldAction=(chromeCapture.editorTools as {tools:{sections:Array<{actions:Array<{label:string;onClick:()=>void}>}>}}).tools.sections.flatMap(section=>section.actions).find(action=>action.label === "Add Beat")!.onClick;
    if(mode!=='promote') {
      fireEvent.click(beat);
      await screen.findByRole("heading",{name:"New Beat",exact:true});
      const scene=screen.getByRole("button",{name:"Add Scene to this Beat"});await waitFor(()=>expect(scene).toBeEnabled());fireEvent.click(scene);
      await screen.findByRole("heading",{name:"New Scene",exact:true});
      if(mode==='decision'){
        const addChoice=await screen.findByRole('button',{name:'Add Choice',exact:true});
        await waitFor(()=>expect(addChoice).toBeEnabled());fireEvent.click(addChoice);
        await screen.findByRole('heading',{name:'New Choice',exact:true});
        const addOption=screen.getByRole('button',{name:'Add Option',exact:true});
        await waitFor(()=>expect(addOption).toBeEnabled());fireEvent.click(addOption);
        await screen.findByText('New option',{exact:true});
      }
    } else {
      const liveEditor=(screen.getByTestId('world-owned-plan-markdown-editor').querySelector('.ProseMirror') as any).editor;
      const select=(text:string)=>act(()=>{liveEditor.state.doc.forEach((node:any,pos:number)=>{if(node.type.name==='heading'&&node.textContent===text)liveEditor.commands.setTextSelection(pos+1);});});
      select('Preparation');fireEvent.click(await screen.findByRole('button',{name:'Make this a Beat',exact:true}));
      select('Arrival');fireEvent.click(await screen.findByRole('button',{name:'Make this a Scene',exact:true}));
      expect(screen.queryByRole('heading',{name:'New Beat',exact:true})).not.toBeInTheDocument();
      expect(screen.getByRole('table')).toHaveTextContent('Optional');
    }
    act(()=>oldAction());
    expect(screen.getAllByRole("heading",{name:mode!=='promote'?"New Beat":"Preparation",exact:true})).toHaveLength(1);
    expect(prepare).not.toHaveBeenCalled();expect(commit).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button",{name:"Save Plan",exact:true}));
    await waitFor(()=>expect(commit).toHaveBeenCalledOnce());
    await screen.findByText("Saved to this World.");
    expect(saved.startsWith(envelope)).toBe(true);
    if(mode==='promote')expect(saved).toContain('| Tavern | Optional |');
    if(mode==='decision'){
      expect(saved.match(/kind=choice id=/g)).toHaveLength(1);
      expect(saved.match(/kind=option id=/g)).toHaveLength(3);
      expect(saved).toContain('First option');expect(saved).toContain('New option');
    }
    const identities=saved.match(/id=(?:beat|scene):[^ ]+/g);expect(identities).toHaveLength(2);expect(saved).toContain("Source quotation retained.");
    mounted.unmount();render(pageTree);await screen.findByRole("heading",{name:mode!=='promote'?"New Scene":"Arrival",exact:true});
    const editor=screen.getByTestId("world-owned-plan-markdown-editor");
    expect(editor).toHaveTextContent("Source quotation retained.");
    expect(editor.querySelector('[data-dmb-playable-id]')?.getAttribute('data-dmb-playable-id')).toBe(identities![0].slice(3));
  } finally {
    if(oldRects)Object.defineProperty(Range.prototype,"getClientRects",oldRects);else Reflect.deleteProperty(Range.prototype,"getClientRects");
    if(oldRect)Object.defineProperty(Range.prototype,"getBoundingClientRect",oldRect);else Reflect.deleteProperty(Range.prototype,"getBoundingClientRect");
  }
});


it.each(["ordinary", "lost", "newer", "conflict", "legacy"] as const)("persists Plan title intent through %s save recovery", async (mode) => {
  const record = mockSavedPlanForAgent();
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  let serverRecord = record;
  const digest = createHash("sha256").update(savedAgentPlanText).digest("hex");
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockImplementation(async () => ({
    schema_version: "dmb_workspace_document_snapshot_v2", record: serverRecord,
    markdown: savedAgentPlanText, content_sha256: digest, file_fingerprint: "postgres",
    file_exists: true, loaded_revision: serverRecord.revision,
  }));
  const prior = await liveApi.getWorldOwnedPlanCommittedRevision(savedAgentPlanId);
  vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockImplementation(async () => ({
    ...prior, title: serverRecord.title, object_revision: serverRecord.revision,
    markdown: savedAgentPlanText, content_sha256: digest, has_divergent_working_copy: false,
  }));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async request => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2", scope_mode: "world", world_id: worldId,
    document_id: savedAgentPlanId, title: request.title!, target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!, registry_revision: request.expected_revision + 1,
    file_exists: true, writer_ok: true, writer_confirm_token: "rename-token", warnings: [], diagnostics: [],
  }));
  let resolveCommit!: () => void;
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async request => {
    if (mode === "newer") await new Promise<void>(resolve => { resolveCommit = resolve; });
    serverRecord = { ...record, title: mode === "conflict" ? "Another writer title" : request.title!, revision: 9 };
    if (mode === "lost" || mode === "conflict") throw new Error("rename response lost");
    return { schema_version: "dmb_tiptap_markdown_write_commit_v2", scope_mode: "world", world_id: worldId,
      document_id: savedAgentPlanId, title: serverRecord.title, target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!, registry_revision: 9, committed_revision: 9,
      committed_record: serverRecord, normalized_content_sha256: digest, writer_ok: true,
      writer_phase: "commit", diagnostics: [] };
  });
  const tree = <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><VerifiedPlanPage /></SelectedWorldProvider>;
  if (mode === "legacy") {
    localStorage.setItem(key, JSON.stringify({ schema_version: "dmb_plan_promotion_recovery_v2", scope_mode: "world",
      world_id: worldId, document_id: savedAgentPlanId, title: record.title, markdown: savedAgentPlanText,
      revision: 7, edit_generation: 1, pending_write: { phase: "commit", base_revision: 6,
        prepared_revision: 7, base_markdown: "# Prior\n", markdown: savedAgentPlanText, edit_generation: 1 } }));
  }
  let mounted = render(tree);
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
  if (mode !== "legacy") fireEvent.change(screen.getByLabelText("Plan title"), { target: { value: "  Renamed Plan  " } });
  fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
  if (mode === "legacy") {
    await screen.findByText("Saved to this World.");
    expect(prepare).not.toHaveBeenCalled(); expect(commit).not.toHaveBeenCalled();
    expect(JSON.parse(localStorage.getItem(key)!)).toMatchObject({ title: record.title, pending_write: null });
    return;
  }
  await waitFor(() => expect(commit).toHaveBeenCalledOnce());
  expect(prepare).toHaveBeenCalledWith(expect.objectContaining({ title: "Renamed Plan", markdown: savedAgentPlanText }));
  expect(commit).toHaveBeenCalledWith(expect.objectContaining({ title: "Renamed Plan", markdown: savedAgentPlanText }));
  if (mode === "newer") {
    expect(JSON.parse(localStorage.getItem(key)!)).toMatchObject({ pending_write: { title: "Renamed Plan", base_title: record.title } });
    fireEvent.change(screen.getByLabelText("Plan title"), { target: { value: "Newer local title" } });
    await act(async () => resolveCommit());
  }
  if (mode === "lost" || mode === "conflict") {
    await screen.findByText("rename response lost");
    mounted.unmount(); mounted = render(tree);
    await screen.findByTestId("world-owned-plan");
    await waitFor(() => expect(screen.getByRole("button", { name: "Save Plan" })).toBeEnabled());
    fireEvent.click(screen.getByRole("button", { name: "Save Plan" }));
    if (mode === "conflict") {
      await screen.findByText(/previous save outcome cannot be proven/);
      expect(JSON.parse(localStorage.getItem(key)!)).toMatchObject({ pending_write: { title: "Renamed Plan" } });
      expect(commit).toHaveBeenCalledOnce();
      return;
    }
  }
  await screen.findByText("Saved to this World.");
  expect(JSON.parse(localStorage.getItem(key)!)).toMatchObject({ title: mode === "newer" ? "Newer local title" : "Renamed Plan", pending_write: null });
  mounted.unmount(); render(tree);
  await screen.findByTestId("world-owned-plan");
  await waitFor(() => expect(screen.getByLabelText("Plan title")).toHaveValue(mode === "newer" ? "Newer local title" : "Renamed Plan"));
  expect(commit).toHaveBeenCalledOnce();
});

it("autosaves a changed Plan after a quiet period and shows the committed server timestamp", async () => {
  const record = mockSavedPlanForAgent();
  const committedAt = "2026-10-18T16:30:00Z";
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: request.title!,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: request.expected_revision + 1,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "autosave-token",
    warnings: [],
    diagnostics: [],
  }));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: request.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: request.expected_revision,
    committed_revision: request.expected_revision,
    committed_record: { ...record, title: request.title, revision: request.expected_revision, updated_at: committedAt },
    normalized_content_sha256: "c".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  }));
  const postGraph = vi.spyOn(liveApi, "postWorldGraphProjection");
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument());

  vi.useFakeTimers();
  fireEvent.input(editorSurface.querySelector("[contenteditable]")!, {
    target: { textContent: "The Plan is safely autosaved." },
  });
  await act(async () => { await vi.advanceTimersByTimeAsync(699); });
  expect(prepare).not.toHaveBeenCalled();

  await act(async () => { await vi.advanceTimersByTimeAsync(1); });
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(prepare).toHaveBeenCalledWith(expect.objectContaining({
    world_id: worldId,
    document_id: record.document_id,
    markdown: expect.stringContaining("The Plan is safely autosaved."),
  }));
  expect(commit).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument();
  expect(document.querySelector(".durable-save-status time")).toHaveAttribute(
    "dateTime",
    "2026-10-18T16:30:00.000Z",
  );
  expect(postGraph).not.toHaveBeenCalled();
  expect(postTurn).not.toHaveBeenCalled();
});

it("keeps edits made during an in-flight autosave dirty and saves them afterward", async () => {
  const record = mockSavedPlanForAgent();
  let releaseFirstCommit!: (value: Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>) => void;
  const firstCommit = new Promise<Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>>((resolve) => {
    releaseFirstCommit = resolve;
  });
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: request.title!,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: request.expected_revision + 1,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: `autosave-${request.expected_revision}`,
    warnings: [],
    diagnostics: [],
  }));
  let commitCalls = 0;
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    commitCalls += 1;
    if (commitCalls === 1) return firstCommit;
    return {
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: record.document_id,
      title: request.title,
      target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!,
      registry_revision: request.expected_revision,
      committed_revision: request.expected_revision,
      committed_record: { ...record, title: request.title, revision: request.expected_revision, updated_at: "2026-10-18T16:31:00Z" },
      normalized_content_sha256: "d".repeat(64),
      writer_ok: true,
      writer_phase: "commit",
      diagnostics: [],
    };
  });
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument());

  vi.useFakeTimers();
  const editor = editorSurface.querySelector("[contenteditable]")!;
  fireEvent.input(editor, { target: { textContent: "First autosave snapshot." } });
  await act(async () => { await vi.advanceTimersByTimeAsync(700); });
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);

  fireEvent.input(editorSurface.querySelector("[contenteditable]")!, {
    target: { textContent: "Newer edit while the first save is pending." },
  });
  await act(async () => releaseFirstCommit({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: record.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: 8,
    committed_revision: 8,
    committed_record: { ...record, revision: 8, updated_at: "2026-10-18T16:30:00Z" },
    normalized_content_sha256: "c".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  }));
  expect(editorSurface).toHaveTextContent("Newer edit while the first save is pending.");
  expect(screen.getByTestId("world-plan-surface-context").querySelector('[data-save-state="unsaved"]')).toBeInTheDocument();

  await act(async () => { await vi.advanceTimersByTimeAsync(700); });
  expect(prepare).toHaveBeenCalledTimes(2);
  expect(prepare.mock.calls[1]![0].markdown).toContain("Newer edit while the first save is pending.");
  expect(commit).toHaveBeenCalledTimes(2);
  expect(document.querySelector(".durable-save-status time")).toHaveAttribute(
    "dateTime",
    "2026-10-18T16:31:00.000Z",
  );
});

it("keeps Plan selection fenced while an autosave is in flight", async () => {
  const firstId = "autosave-switch-a";
  const secondId = "autosave-switch-b";
  const firstRecord = worldPlanRecord(firstId, worldId, 7);
  firstRecord.title = "Of Conks Session Plan";
  const secondRecord = worldPlanRecord(secondId, worldId, 11);
  secondRecord.title = "Second Plan";
  const firstMarkdown = "# First Plan\n";
  const secondMarkdown = "# Second Plan\n";
  mockSavedPlanForAgent(firstId, 7, 7, firstMarkdown);
  vi.spyOn(liveApi, "getWorkspaceDocumentAny").mockImplementation(async (id) => id === secondId ? secondRecord : firstRecord);
  vi.spyOn(liveApi, "listWorldOwnedPlans").mockResolvedValue({
    schema_version: "dmb_workspace_document_registry_v2",
    scope_mode: "world",
    world_id: worldId,
    records: [firstRecord, secondRecord],
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async (id) => {
    const record = id === secondId ? secondRecord : firstRecord;
    return {
      schema_version: "dmb_workspace_document_snapshot_v2",
      record,
      markdown: id === secondId ? secondMarkdown : firstMarkdown,
      content_sha256: id === secondId ? "e".repeat(64) : "f".repeat(64),
      file_fingerprint: "postgres",
      file_exists: true,
      loaded_revision: record.revision,
    };
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision").mockImplementation(async (id) => {
    const record = id === secondId ? secondRecord : firstRecord;
    const markdown = id === secondId ? secondMarkdown : firstMarkdown;
    return {
      schema_version: "dmb_workspace_committed_revision_v2",
      scope_mode: "world",
      world_id: worldId,
      campaign_id: null,
      document_id: id,
      kind: "plan",
      title: record.title,
      status: "active",
      object_revision: record.revision,
      work_revision_id: `work-revision-${id}`,
      revision_n: 4,
      markdown,
      content_sha256: id === secondId ? "e".repeat(64) : "f".repeat(64),
      has_divergent_working_copy: false,
      target_relpath: record.target_relpath!,
    };
  });
  let resolveCommit!: (value: Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>) => void;
  const pendingCommit = new Promise<Awaited<ReturnType<typeof liveApi.commitWorldOwnedPlanMarkdownWrite>>>((resolve) => {
    resolveCommit = resolve;
  });
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: firstId,
    title: request.title!,
    target_relpath: firstRecord.target_relpath!,
    target_display_path: firstRecord.target_relpath!,
    registry_revision: 8,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "switch-pending-save",
    warnings: [],
    diagnostics: [],
  }));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockReturnValue(pendingCommit);
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${firstId}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  const firstEditor = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByLabelText("Plan title")).toHaveValue("Of Conks Session Plan"));
  vi.useFakeTimers();
  fireEvent.input(firstEditor.querySelector("[contenteditable]")!, {
    target: { textContent: "First Plan edited before switching." },
  });
  await act(async () => { await vi.advanceTimersByTimeAsync(700); });
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);

  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: secondId } });
  expect(screen.getByLabelText("Plan title")).toHaveValue("Of Conks Session Plan");
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("First Plan edited before switching.");
  await act(async () => resolveCommit({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: firstId,
    title: "Of Conks Session Plan",
    target_relpath: firstRecord.target_relpath!,
    target_display_path: firstRecord.target_relpath!,
    registry_revision: 8,
    committed_revision: 8,
    committed_record: { ...firstRecord, revision: 8, updated_at: "2026-10-18T16:40:00Z" },
    normalized_content_sha256: "a".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  }));
  expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: secondId } });
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
  expect(screen.getByLabelText("Plan title")).toHaveValue("Second Plan");
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent("Second Plan");
  expect(document.querySelector(".durable-save-status time")).toHaveAttribute(
    "dateTime",
    "2026-01-01T00:00:00.000Z",
  );
});

it("pauses autosave after an uncertain commit and preserves the draft for explicit recovery", async () => {
  const record = mockSavedPlanForAgent();
  const submitted = "Keep this draft until the receipt is understood.";
  const latest = "Keep this newer edit after recovery.";
  const initialSnapshot = {
    schema_version: "dmb_workspace_document_snapshot_v2" as const,
    record,
    markdown: savedAgentPlanText,
    content_sha256: "b".repeat(64),
    file_fingerprint: "postgres",
    file_exists: true,
    loaded_revision: record.revision,
  };
  const recoveredRecord = { ...record, revision: 8, updated_at: "2026-10-18T16:45:00Z" };
  let snapshotCalls = 0;
  let uncertainMarkdown = submitted;
  vi.spyOn(liveApi, "getWorldOwnedPlanSnapshot").mockImplementation(async () => {
    snapshotCalls += 1;
    if (snapshotCalls === 1) return initialSnapshot;
    return {
      schema_version: "dmb_workspace_document_snapshot_v2",
      record: recoveredRecord,
      markdown: uncertainMarkdown,
      content_sha256: "c".repeat(64),
      file_fingerprint: "postgres",
      file_exists: true,
      loaded_revision: 8,
    };
  });
  vi.spyOn(liveApi, "getWorldOwnedPlanCommittedRevision").mockImplementation(async () => ({
    schema_version: "dmb_workspace_committed_revision_v2",
    scope_mode: "world",
    world_id: worldId,
    campaign_id: null,
    document_id: record.document_id,
    kind: "plan",
    title: record.title,
    status: "active",
    object_revision: 8,
    work_revision_id: "work-revision-uncertain-commit",
    revision_n: 5,
    markdown: uncertainMarkdown,
    content_sha256: "c".repeat(64),
    has_divergent_working_copy: false,
    target_relpath: record.target_relpath!,
  }));
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => {
    if (request.expected_revision === 7) uncertainMarkdown = request.markdown;
    return {
      schema_version: "dmb_tiptap_markdown_write_prepare_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: record.document_id,
      title: request.title!,
      target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!,
      registry_revision: request.expected_revision + 1,
      file_exists: true,
      writer_ok: true,
      writer_confirm_token: `uncertain-autosave-${request.expected_revision}`,
      warnings: [],
      diagnostics: [],
    };
  });
  let commitCalls = 0;
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => {
    commitCalls += 1;
    if (commitCalls === 1) throw new Error("Commit response uncertain");
    return {
      schema_version: "dmb_tiptap_markdown_write_commit_v2",
      scope_mode: "world",
      world_id: worldId,
      document_id: record.document_id,
      title: request.title,
      target_relpath: record.target_relpath!,
      target_display_path: record.target_relpath!,
      registry_revision: request.expected_revision,
      committed_revision: request.expected_revision,
      committed_record: { ...record, title: request.title, revision: request.expected_revision, updated_at: "2026-10-18T16:50:00Z" },
      normalized_content_sha256: "d".repeat(64),
      writer_ok: true,
      writer_phase: "commit",
      diagnostics: [],
    };
  });
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument());

  vi.useFakeTimers();
  fireEvent.input(editorSurface.querySelector("[contenteditable]")!, {
    target: { textContent: submitted },
  });
  await act(async () => { await vi.advanceTimersByTimeAsync(700); });
  expect(screen.getByRole("alert")).toHaveTextContent("Commit response uncertain");
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);
  expect(JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)!).markdown)
    .toContain(submitted);
  expect(document.querySelector('[data-save-state="needs-attention"]')).toBeInTheDocument();

  await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);

  fireEvent.input(screen.getByTestId("world-owned-plan-markdown-editor").querySelector("[contenteditable]")!, {
    target: { textContent: latest },
  });
  expect(screen.getByRole("button", { name: "Retry save" })).toBeInTheDocument();
  expect(document.querySelector('[data-save-state="needs-attention"]')).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("Commit response uncertain");
  await act(async () => { await vi.advanceTimersByTimeAsync(10_000); });
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(commit).toHaveBeenCalledTimes(1);

  fireEvent.click(screen.getByRole("button", { name: "Retry save" }));
  await act(async () => {
    await vi.runOnlyPendingTimersAsync();
    for (let index = 0; index < 12; index += 1) await Promise.resolve();
  });
  expect(prepare).toHaveBeenCalledTimes(2);
  expect(prepare.mock.calls[1]![0].markdown).toContain(latest);
  expect(commit).toHaveBeenCalledTimes(2);
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toHaveTextContent(latest);
  expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument();
  expect(document.querySelector(".durable-save-status time")).toHaveAttribute(
    "dateTime",
    "2026-10-18T16:50:00.000Z",
  );
});

it("autosaves exact Markdown source with preserved metadata and card IDs across view switching", async () => {
  const envelope="---\r\ntitle: Kept metadata\r\n---\r\n";
  const body=twoScenePlanMarkdown + "\n> [!READ-ALOUD]\n> The boardwalk crosses dark water.\n";
  const record = mockSavedPlanForAgent(savedAgentPlanId,7,7,envelope+twoScenePlanMarkdown);
  const committedAt = "2026-10-18T16:30:00Z";
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_prepare_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: request.title!,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: request.expected_revision + 1,
    file_exists: true,
    writer_ok: true,
    writer_confirm_token: "autosave-token",
    warnings: [],
    diagnostics: [],
  }));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite").mockImplementation(async (request) => ({
    schema_version: "dmb_tiptap_markdown_write_commit_v2",
    scope_mode: "world",
    world_id: worldId,
    document_id: record.document_id,
    title: request.title,
    target_relpath: record.target_relpath!,
    target_display_path: record.target_relpath!,
    registry_revision: request.expected_revision,
    committed_revision: request.expected_revision,
    committed_record: { ...record, title: request.title, revision: request.expected_revision, updated_at: committedAt },
    normalized_content_sha256: "c".repeat(64),
    writer_ok: true,
    writer_phase: "commit",
    diagnostics: [],
  }));
  const postGraph = vi.spyOn(liveApi, "postWorldGraphProjection");
  const postTurn = vi.spyOn(liveApi, "postWorldPlanAgentTurn");
  render(
    <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}>
      <VerifiedPlanPage />
    </SelectedWorldProvider>,
  );
  const editorSurface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument());

  const oldBold=capturedPlanControls().bold;
  fireEvent.click(screen.getByRole("button",{name:"Markdown",exact:true}));
  act(()=>oldBold());
  expect(screen.getByRole("button",{name:"Bold",exact:true})).toBeDisabled();
  const source=screen.getByRole("textbox",{name:"Plan Markdown"});
  expect(source).toHaveValue(twoScenePlanMarkdown);
  fireEvent.click(screen.getByText("Markdown help",{exact:true}));
  expect(screen.getByText("Read Aloud block",{exact:true})).toBeInTheDocument();
  expect(prepare).not.toHaveBeenCalled();
  vi.useFakeTimers();
  fireEvent.change(source,{target:{value:body}});
  fireEvent.click(screen.getByRole("button",{name:"Document",exact:true}));
  expect(editorSurface).toHaveTextContent("The boardwalk crosses dark water.");
  fireEvent.click(screen.getByRole("button",{name:"Markdown",exact:true}));
  expect(screen.getByRole("textbox",{name:"Plan Markdown"})).toHaveValue(body);
  await act(async () => { await vi.advanceTimersByTimeAsync(699); });
  expect(prepare).not.toHaveBeenCalled();

  await act(async () => { await vi.advanceTimersByTimeAsync(1); });
  expect(prepare).toHaveBeenCalledTimes(1);
  expect(prepare).toHaveBeenCalledWith(expect.objectContaining({
    world_id: worldId,
    document_id: record.document_id,
    markdown: envelope+body,
  }));
  expect(commit).toHaveBeenCalledTimes(1);
  expect(screen.getByText("Saved", { exact: true })).toBeInTheDocument();
  expect(document.querySelector(".durable-save-status time")).toHaveAttribute(
    "dateTime",
    "2026-10-18T16:30:00.000Z",
  );
  expect(postGraph).not.toHaveBeenCalled();
  expect(postTurn).not.toHaveBeenCalled();
});


it.each([983, 4903, 14703])("reuses the validated parse for 20 consecutive accepted edits of a %s-word Plan under StrictMode", async words => {
  const text = "# Synthetic parsing acceptance\n\n" + Array.from({ length: words }, (_, i) => `word${i}`).join(" ") + "\n";
  const record = mockSavedPlanForAgent(savedAgentPlanId, 7, 7, text);
  const imports = vi.spyOn(markdownImporter, "markdownToTiptapDoc");
  render(<StrictMode><SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}><VerifiedPlanPage /></SelectedWorldProvider></StrictMode>);
  const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(surface.querySelector(".ProseMirror")).toHaveTextContent("word0"));
  const editor = (surface.querySelector(".ProseMirror") as HTMLElement & { editor: import("@tiptap/core").Editor }).editor;
  await act(async () => { editor.commands.insertContentAt(editor.state.doc.content.size - 1, " warmup"); });
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  imports.mockClear();
  const start = performance.now();
  for (let i = 0; i < 20; i++) {
    await act(async () => { editor.commands.insertContentAt(editor.state.doc.content.size - 1, ` acceptance${i}`); });
  }
  const elapsed = performance.now() - start;
  const accepted = imports.mock.calls.filter(([source]) => source.includes("acceptance"));
  console.log(JSON.stringify({ measurement: "Plan accepted-edit parse reuse", words, edits: 20, imports: accepted.length, synthetic_dom_ms: elapsed }));
  expect(accepted).toHaveLength(20);
  expect(surface).toHaveTextContent("acceptance19");
  const recovery = JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`) ?? "null");
  expect(recovery.markdown).toContain("acceptance19");
  const last = accepted.at(-1)!;
  expect(markdownImporter.markdownToTiptapDoc(recovery.markdown)).toEqual(imports.mock.results[imports.mock.calls.indexOf(last)]!.value);
});


it("drops a validated Plan parse on fidelity rejection and ignores the retired editor callback", async () => {
  const record = mockSavedPlanForAgent();
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  render(<StrictMode><SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}><VerifiedPlanPage /></SelectedWorldProvider></StrictMode>);
  const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(surface).toHaveTextContent("The keeper waits beneath the black arch."));
  const editor = (surface.querySelector(".ProseMirror") as HTMLElement & { editor: import("@tiptap/core").Editor }).editor;
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  await act(async () => { editor.commands.insertContentAt(editor.state.doc.content.size - 1, " Accepted safe addition."); });
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  const safeBytes = localStorage.getItem(key);
  const exportMarkdown = vi.spyOn(defaultMarkdownDocumentAdapter, "exportMarkdown").mockReturnValueOnce("# Plan\n\n<div>Cannot preserve this HTML</div>\n");
  await act(async () => { editor.commands.insertContentAt(editor.state.doc.content.size - 1, " Rejected addition."); });
  expect(screen.getByRole("alert")).toHaveTextContent(/edit was reverted to protect the saved Plan/i);
  expect(localStorage.getItem(key)).toBe(safeBytes);
  expect(surface).toHaveTextContent("Accepted safe addition.");
  expect(surface).not.toHaveTextContent("Rejected addition.");
  const restored = (surface.querySelector(".ProseMirror") as HTMLElement & { editor: import("@tiptap/core").Editor }).editor;
  expect(restored).not.toBe(editor);
  exportMarkdown.mockClear();
  await act(async () => { (editor.options.onUpdate as unknown as (event: { editor: typeof editor }) => void)({ editor }); });
  expect(exportMarkdown).not.toHaveBeenCalled();
  expect(localStorage.getItem(key)).toBe(safeBytes);
  expect(prepare).not.toHaveBeenCalled();
});

it("imports the new Plan after switching identity and refuses the previous validated editor", async () => {
  const a = mockSavedPlanForAgent(); const b = { ...worldPlanRecord("parse-reuse-plan-b", worldId, 3), title: "Second Plan" };
  vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({ schema_version: "dmb_workspace_document_registry_v2", scope_mode: "world", world_id: worldId, records: [a, b] });
  const bodyB = "# Second Plan\n\n> [!READ-ALOUD]\n> A bell sounds above the water.\n";
  vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockImplementation(async id => ({ schema_version: "dmb_workspace_document_snapshot_v2", record: id === b.document_id ? b : a,
    markdown: id === b.document_id ? bodyB : savedAgentPlanText, content_sha256: "b".repeat(64), file_fingerprint: "postgres", file_exists: true, loaded_revision: id === b.document_id ? 3 : 7 }));
  const imports = vi.spyOn(markdownImporter, "markdownToTiptapDoc");
  render(<StrictMode><SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${a.document_id}`}><VerifiedPlanPage /></SelectedWorldProvider></StrictMode>);
  const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(surface).toHaveTextContent("The keeper waits beneath the black arch."));
  const editor = (surface.querySelector(".ProseMirror") as HTMLElement & { editor: import("@tiptap/core").Editor }).editor;
  vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
  await act(async () => { editor.commands.insertContentAt(editor.state.doc.content.size - 1, " Accepted in A only."); });
  imports.mockClear();
  await act(async () => { fireEvent.change(screen.getByLabelText("Plan document"), { target: { value: b.document_id } }); });
  expect(surface).toHaveTextContent("A bell sounds above the water.");
  expect(surface).not.toHaveTextContent("Accepted in A only.");
  expect(imports.mock.calls.some(([source]) => source === bodyB)).toBe(true);
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;const savedB = localStorage.getItem(key);
  imports.mockClear();
  await act(async () => { (editor.options.onUpdate as unknown as (event: { editor: typeof editor }) => void)({ editor }); });
  expect(localStorage.getItem(key)).toBe(savedB);
  expect(imports).not.toHaveBeenCalled();
  expect(JSON.parse(savedB ?? "null").document_id).toBe(b.document_id);
});


it("hands a conversation image seed to the existing Plan Studio without changing the document", async () => {
  const record = mockSavedPlanForAgent();
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}><VerifiedPlanPage /></SelectedWorldProvider>);
  const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(planImageHostCapture.props?.imagePromptHost?.unavailableReason).toBeNull());
  const before = surface.textContent;
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  const draftBefore = localStorage.getItem(key);
  const originalHost = planImageHostCapture.props.imagePromptHost;
  act(() => {
    expect(originalHost.open("Exact image prompt\nDark water.")).toBe(true);
    expect(originalHost.open("Must not replace the open draft")).toBe(false);
  });
  expect(screen.getByLabelText("Image Studio · Plan")).toBeInTheDocument();
  expect(mediaWizardCapture.props.initialPrompt).toBe("Exact image prompt\nDark water.");
  expect(planImageHostCapture.props.imagePromptHost.unavailableReason).toMatch(/Close the current/);
  expect(surface.textContent).toBe(before);
  expect(localStorage.getItem(key)).toBe(draftBefore);
  expect(prepare).not.toHaveBeenCalled();
  expect(commit).not.toHaveBeenCalled();
});

it("places a library image from the Plan navbar through the current Plan autosave", async () => {
  const record = mockSavedPlanForAgent();
  const assetId = "ac6c15cc-8c68-4732-8ae2-d9f3f051393a";
  vi.spyOn(liveApi, "authenticatedApiFetch").mockResolvedValue({ response: Response.json({ asset_id: assetId, state: "ready" }), csrf: null, requestEpoch: 0 });
  const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockRejectedValue(new Error("Synthetic verification stops at the owning Plan writer"));
  const commit = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}><VerifiedPlanPage /></SelectedWorldProvider>);
  const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByRole("button", { name: "Open Image Studio" })).toBeEnabled());
  fireEvent.click(screen.getByRole("button", { name: "Open Image Studio" }));
  expect(screen.getByLabelText("Image Studio · Plan")).toBeInTheDocument();
  const editor = (surface.querySelector(".ProseMirror") as HTMLElement & { editor: import("@tiptap/core").Editor }).editor;
  vi.spyOn(editor.view, "posAtCoords").mockReturnValue({ pos: editor.state.doc.content.size - 1, inside: 0 });
  const abort = new AbortController();
  const placing = mediaWizardCapture.props.onChoose({ asset_id: assetId, state: "ready" }, { prompt: "Saved map" }, { mode: "click", signal: abort.signal });
  fireEvent.pointerUp(editor.view.dom, { clientX: 10, clientY: 10 });
  await act(async () => { await placing; });
  expect(screen.queryByLabelText("Image Studio · Plan")).not.toBeInTheDocument();
  const key = `dmb:world-plan-local-draft:v2:${worldId}`;
  const draft = JSON.parse(localStorage.getItem(key) ?? "null");
  expect(draft.document_id).toBe(record.document_id);expect(draft.markdown).toContain(`dmb-media:${assetId}`);
  expect(draft.markdown).toContain("The keeper waits beneath the black arch.");
  await waitFor(() => expect(prepare).toHaveBeenCalledWith(expect.objectContaining({ world_id: worldId, document_id: record.document_id, markdown: expect.stringContaining(`dmb-media:${assetId}`) })));
  expect(commit).not.toHaveBeenCalled();
});

it("disables Plan deletion immediately when an authored edit is not saved", async () => {
  const record = mockSavedPlanForAgent();
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}><VerifiedPlanPage /></SelectedWorldProvider>);
  const surface = await screen.findByTestId("world-owned-plan-markdown-editor");
  await waitFor(() => expect(screen.getByRole("button",{name:"Delete",exact:true})).toBeEnabled());
  const editor = (surface.querySelector(".ProseMirror") as HTMLElement & { editor: import("@tiptap/core").Editor }).editor;
  vi.useFakeTimers({toFake:["setTimeout","clearTimeout"]});
  await act(async () => { editor.commands.insertContentAt(editor.state.doc.content.size - 1," Unsaved trash guard witness."); });
  expect(screen.getByRole("button",{name:"Delete",exact:true})).toBeDisabled();
  expect(screen.queryByRole("button",{name:"Trash",exact:true})).not.toBeInTheDocument();
});

it("manually edits scoped Cards in the same Plan editor and writer, preserves siblings and invalidates media on ABA navigation", async () => {
  const source = `---
private_key: retained-fixture-only
---

<!-- dmb-playable-element:v2 kind=beat id=beat:road beat_kind=spine -->
## Road
Keep watch.
<!-- dmb-playable-element:v2 kind=scene id=scene:a -->
### Alpha
First body.
<!-- dmb-playable-element:v2 kind=scene id=scene:b -->
### Beta
Second body.
`;
  const record=mockSavedPlanForAgent(savedAgentPlanId,7,7,source);
  const prepare=vi.spyOn(liveApi,"prepareTiptapMarkdownWrite").mockRejectedValue(new Error("Stop at canonical writer"));
  const assetId="ac6c15cc-8c68-4732-8ae2-d9f3f051393a";
  vi.spyOn(liveApi,"authenticatedApiFetch").mockResolvedValue({response:Response.json({asset_id:assetId,state:"ready"}),csrf:null,requestEpoch:0});
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${record.document_id}`}><VerifiedPlanPage /></SelectedWorldProvider>);
  const surface=await screen.findByTestId("world-owned-plan-markdown-editor");
 await waitFor(()=>expect(surface).toHaveTextContent("First body."));
  const dom=surface.querySelector(".ProseMirror") as HTMLElement & {editor:import("@tiptap/core").Editor};
  const editor=dom.editor;
  await waitFor(()=>expect(screen.getByRole("button",{name:"Cards",exact:true})).toBeEnabled());
  const before=editor.getJSON();
  fireEvent.click(screen.getByRole("button",{name:"Cards",exact:true}));
  await waitFor(()=>expect(screen.getByTestId("world-plan-document-view")).not.toHaveAttribute("hidden"));
  expect(editor.getJSON()).toEqual(before);expect(prepare).not.toHaveBeenCalled();
  expect(screen.queryByText("Plan and Agent details")).not.toBeInTheDocument();
  const {planCardRange}=await import("./planCardEditing");
  fireEvent.click(screen.getByRole("button",{name:"Open Image Studio"}));
  expect(screen.getByRole("button",{name:"Cards",exact:true})).toHaveAttribute("aria-pressed","true");
  vi.spyOn(editor.view,"posAtCoords").mockReturnValue({pos:planCardRange(editor.state.doc,"scene:a")!.from+1,inside:0});
  const placing=mediaWizardCapture.props.onChoose({asset_id:assetId,state:"ready"},{prompt:"Saved map"},{mode:"click",signal:new AbortController().signal});
  fireEvent.click(screen.getByRole("button",{name:"Show scene: Beta"}));
  fireEvent.click(screen.getByRole("button",{name:"Show scene: Alpha"}));
  fireEvent.pointerUp(editor.view.dom,{clientX:10,clientY:10});
  await act(async()=>{await expect(placing).rejects.toThrow(/changed|again/i);});
  expect(editor.getJSON()).toEqual(before);
  const freshPlacement=mediaWizardCapture.props.onChoose({asset_id:assetId,state:"ready"},{prompt:"Saved map"},{mode:"click",signal:new AbortController().signal});
  fireEvent.pointerUp(editor.view.dom,{clientX:10,clientY:10});
  await act(async()=>{await freshPlacement;});
  expect(JSON.stringify(editor.getJSON())).toContain(assetId);
  expect((surface.querySelector(".ProseMirror") as typeof dom).editor, screen.queryAllByRole("alert").map(e=>e.textContent).join(" | ")).toBe(editor);
  const a=planCardRange(editor.state.doc,"scene:a")!;
  let bodyPosition=a.from+1;editor.state.doc.descendants((node,pos)=>{if(node.type.name==="paragraph" && node.textContent==="First body.") bodyPosition=pos+1;});
  await act(async()=>{editor.commands.insertContentAt(bodyPosition,"Card edit. ");});
  const safe=editor.getJSON();
  await act(async()=>{editor.view.dispatch(editor.state.tr.insertText("outside",editor.state.doc.content.size-1));});
  expect(editor.getJSON()).toEqual(safe);
  expect(screen.getByText(/This change reaches outside/)).toBeInTheDocument();
  await waitFor(()=>expect(prepare).toHaveBeenCalledWith(expect.objectContaining({document_id:record.document_id,markdown:expect.stringContaining("Card edit.")})));
  expect(prepare.mock.calls[0]![0].markdown.split("<!-- dmb-playable-element:v2 kind=scene id=scene:b -->")[1]).toBe(source.split("<!-- dmb-playable-element:v2 kind=scene id=scene:b -->")[1]);
  expect(prepare.mock.calls[0]![0].markdown.match(/private_key: retained-fixture-only/g)).toHaveLength(1);

  fireEvent.click(screen.getByRole("button",{name:"Document",exact:true}));
  expect((surface.querySelector(".ProseMirror") as typeof dom).editor).toBe(editor);
  fireEvent.click(screen.getByRole("button",{name:"Cards",exact:true}));
  expect((surface.querySelector(".ProseMirror") as typeof dom).editor).toBe(editor);
  expect(editor.getJSON()).toEqual(safe);
});

it("keeps Contents beside the same editor and a fixed control set in Document and Cards", async () => {
  mockSavedPlanForAgent(savedAgentPlanId,7,7,currentTwoScenePlanMarkdown);
  const prepare=vi.spyOn(liveApi,"prepareTiptapMarkdownWrite");
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><VerifiedPlanPage /></SelectedWorldProvider>);
  const surface=await screen.findByTestId("world-owned-plan-markdown-editor");
 await waitFor(()=>expect(surface).toHaveTextContent("A lantern moves behind"));
  const dom=surface.querySelector(".ProseMirror");
  await waitFor(()=>expect(screen.getByRole("button",{name:"Cards",exact:true})).toBeEnabled());
  const contents=screen.getByRole("navigation",{name:"Contents"});
  const layout=surface.closest(".plan-cards-workspace");
  expect(layout).toHaveAttribute("data-plan-view","document");
  expect(contents.parentElement).toBe(layout);
  expect(screen.queryByRole("navigation",{name:"Plan scene navigation"})).toBeNull();
  expect(screen.queryByRole("combobox",{name:"Plan scene"})).toBeNull();
  const controls=screen.getByRole("group",{name:"Plan controls"});
  const before=Array.from(controls.querySelectorAll("button")).map(button=>button.getAttribute("aria-label")??button.textContent);
  fireEvent.click(screen.getByRole("button",{name:"Cards",exact:true}));
  expect(surface.closest(".plan-cards-workspace")).toBe(layout);
  expect(layout).toHaveAttribute("data-plan-view","cards");
  expect(screen.getByRole("navigation",{name:"Contents"})).toBe(contents);
  expect(surface.querySelector(".ProseMirror")).toBe(dom);
  expect(Array.from(controls.querySelectorAll("button")).map(button=>button.getAttribute("aria-label")??button.textContent)).toEqual(before);
  fireEvent.click(screen.getByRole("button",{name:"Document",exact:true}));
  expect(layout).toHaveAttribute("data-plan-view","document");
  expect(screen.getByRole("navigation",{name:"Contents"})).toBe(contents);
  expect(surface.querySelector(".ProseMirror")).toBe(dom);
  expect(prepare).not.toHaveBeenCalled();
  expect(screen.getByRole("button",{name:"Markdown",exact:true})).toHaveAttribute("title","Edit raw Markdown source");
});

it("browses Cards with reader arrows while retaining the mounted editor and local draft",async()=>{
 mockSavedPlanForAgent(savedAgentPlanId,7,7,currentTwoScenePlanMarkdown);
 const prepare=vi.spyOn(liveApi,"prepareTiptapMarkdownWrite");
 render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><VerifiedPlanPage /></SelectedWorldProvider>);
 const surface=await screen.findByTestId("world-owned-plan-markdown-editor");
 await waitFor(()=>expect(surface).toHaveTextContent("A lantern moves behind"));
 await waitFor(()=>expect(screen.getByRole("button",{name:"Cards",exact:true})).toBeEnabled());
 expect(screen.queryByRole("navigation",{name:"Card navigation"})).toBeNull();
 fireEvent.click(screen.getByRole("button",{name:"Cards",exact:true}));
 const dom=surface.querySelector(".ProseMirror") as HTMLElement & {editor:import("@tiptap/core").Editor};const editor=dom.editor;
 vi.useFakeTimers({toFake:["setTimeout","clearTimeout"]});
 await act(async()=>{editor.commands.insertContent("Local card draft. ");});
 const draft=editor.getJSON();
 expect(screen.getByRole("button",{name:"Previous scene",exact:true})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"Next scene",exact:true}));
 expect(screen.getByRole("button",{name:"Show scene: Warehouse"})).toHaveAttribute("aria-current","true");
 expect(screen.getByRole("button",{name:"Next scene",exact:true})).toBeDisabled();
 fireEvent.click(screen.getByRole("button",{name:"Previous scene",exact:true}));
 expect(screen.getByRole("button",{name:"Show scene: Arrival"})).toHaveAttribute("aria-current","true");
 expect((surface.querySelector(".ProseMirror") as typeof dom).editor).toBe(editor);
 expect(editor.getJSON()).toEqual(draft);
 expect(JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)??"null").markdown).toContain("Local card draft.");
 expect(prepare).not.toHaveBeenCalled();
});

it("publishes Rules Lookup from the actual native managed Plan and preserves writer draft, selection and undo", async () => {
  mockSavedPlanForAgent();
  const catalog = vi.spyOn(liveApi, "getRulesCatalog").mockResolvedValue({ schema: "dmb_rules_catalog_v1", sources: [{ corpus: "a".repeat(64), available: true, ruleset_id: "dnd_2024", title: "SRD", coverage: "One section only.", unit_count: 1 }] });
  const rulesText = "A creature cannot willingly end a move in occupied space.";
  const hit = { corpus: "a".repeat(64), citation_id: "b".repeat(64), ruleset_id: "dnd_2024", unit_id: "c".repeat(64), text_sha256: createHash("sha256").update(rulesText).digest("hex"), section: "Occupancy", source_title: "SRD", source_uri: "https://example.invalid/srd.pdf", source_sha256: "d".repeat(64), page_fingerprint: "e".repeat(64), pdf_page_index: 13, printed_page: 14, excerpt: rulesText, excerpt_start: 0, excerpt_end: rulesText.length, excerpt_complete: true };
  const query = vi.spyOn(liveApi, "queryRulesEvidence").mockResolvedValue({ schema: "dmb_rules_lookup_packet_v1", corpus: hit.corpus, ruleset_id: hit.ruleset_id, query_id: "f".repeat(64), normalized_query: "prone", status: "evidence", coverage: "One section only.", coverage_status: "limited", hits: [hit], additional_matches: false });
  const inspect = vi.spyOn(liveApi, "getRulesPassage").mockResolvedValue({ ...hit, schema: "dmb_rules_passage_v1", text: rulesText, attribution: "Public source attribution" });
  const save = vi.spyOn(liveApi, "commitWorldOwnedPlanMarkdownWrite");
  function NativeComposition() {
    const selected = useSelectedWorld();
    return selected.kind === "managed" ? <AgentInteractionProvider><AskPluginSlotProvider><PeekRegionProvider>
      <PlanSurfacePage /><ToolHost /><LegacyProjectionHostAdapter /><PeekRegionSlot />
    </PeekRegionProvider></AskPluginSlotProvider></AgentInteractionProvider> : null;
  }
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><NativeComposition /></SelectedWorldProvider>);
  const writer = await screen.findByTestId("world-owned-plan-markdown-editor");
  const editor = (writer.querySelector(".ProseMirror") as any).editor;
  const original = editor.getJSON();
  act(() => { editor.commands.setTextSelection(2); editor.commands.insertContent("unsaved native Rules draft "); });
  const before = editor.getJSON(), selection = editor.state.selection.toJSON();
  expect(catalog).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Tools", exact: true }));
  fireEvent.click(await screen.findByRole("button", { name: "Rules Lookup", exact: true }));
  await screen.findByRole("region", { name: "Rules lookup", exact: true });
  await screen.findByRole("combobox", { name: "Rules source" });
  expect(catalog).toHaveBeenCalledTimes(1);
  fireEvent.change(screen.getByRole("textbox", { name: "Rules question" }), { target: { value: "prone" } });
  fireEvent.click(screen.getByRole("button", { name: "Look up rules" }));
  fireEvent.click(await screen.findByRole("button", { name: "Inspect cited passage" }));
  expect(await screen.findByRole("region", { name: "Cited rules passage" })).toHaveTextContent(rulesText);
  expect(query).toHaveBeenCalledTimes(1); expect(inspect).toHaveBeenCalledTimes(1);
  expect(screen.getByTestId("world-owned-plan-markdown-editor")).toBe(writer);
  expect(editor.getJSON()).toEqual(before); expect(editor.state.selection.toJSON()).toEqual(selection);
  fireEvent.click(screen.getByRole("button", { name: "Close toolbox", exact: true }));
  expect(editor.getJSON()).toEqual(before); expect(save).not.toHaveBeenCalled();
  act(() => editor.commands.undo()); expect(editor.getJSON()).toEqual(original);
});


it("root Plan exposes World selection instead of the campaign inventory and preserves recovery bytes", async () => {
  window.history.replaceState({}, "", "/plan?documentId=b7e0d9da-37ad-444a-9a62-25f7c61bb32d");
  const recoveryKey = "dmb:world-plan-local-draft:v2:elderwyld";
  const oldDraft = JSON.stringify({schema_version:"dmb_plan_promotion_recovery_v2",scope_mode:"world",
    world_id:"elderwyld",document_id:null,title:"Unsaved session",markdown:"# Recollections\nStill drafting.",revision:null});
  localStorage.setItem(recoveryKey, oldDraft);
  vi.spyOn(liveApi, "listWorldContainers").mockResolvedValue({records:[{
    world_id: "elderwyld", name: "Elderwyld",
  }]} as never);
  const legacyRead = vi.spyOn(liveApi, "getPlanView");
  render(<PlanSurfacePage />);
  expect(await screen.findByRole("link", {name: /Elderwyld/})).toHaveAttribute("href", "/plan?world=elderwyld");
  expect(screen.queryByRole("combobox", {name: "Plan document"})).toBeNull();
  expect(legacyRead).not.toHaveBeenCalled();
  expect(localStorage.getItem(recoveryKey)).toBe(oldDraft);
});


it.each(["cards", "document"])("restores the selected Plan scene after host remount in %s without a content write", async (view) => {
  mockSavedPlanForAgent(savedAgentPlanId,7,7,currentTwoScenePlanMarkdown);
  const prepare = vi.spyOn(liveApi,"prepareTiptapMarkdownWrite");
  const commit = vi.spyOn(liveApi,"commitWorldOwnedPlanMarkdownWrite");
  const scroll = vi.fn();
  const priorScroll = HTMLElement.prototype.scrollIntoView;
  HTMLElement.prototype.scrollIntoView = scroll;
  try {
    const tree = <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><VerifiedPlanPage /></SelectedWorldProvider>;
    let page = render(tree);
    await screen.findByTestId("world-owned-plan-markdown-editor");
    await screen.findByRole("button",{name:"Show scene: Warehouse"});
    await waitFor(()=>expect(screen.getByRole("button",{name:"Cards",exact:true})).toBeEnabled());
    fireEvent.click(screen.getByRole("button",{name:"Cards",exact:true}));
    fireEvent.click(screen.getByRole("button",{name:"Show scene: Warehouse"}));
    expect(screen.getByRole("button",{name:"Show scene: Warehouse"})).toHaveAttribute("aria-current","true");
    page.unmount();
    const url = `/plan?world=${worldId}&documentId=${savedAgentPlanId}${view === "cards" ? "&view=cards" : ""}`;
    window.history.replaceState({},"",url);
    scroll.mockClear();
    page = render(<SelectedWorldProvider locationSnapshot={url}><VerifiedPlanPage /></SelectedWorldProvider>);
    await screen.findByTestId("world-owned-plan-markdown-editor");
    await screen.findByRole("button",{name:"Show scene: Warehouse"});
    await waitFor(()=>expect(screen.getByRole("button",{name:"Show scene: Warehouse"})).toHaveAttribute("aria-current","true"));
    if (view === "cards") {
      expect(screen.getByRole("button",{name:"Next scene",exact:true})).toBeDisabled();
      expect(screen.getByRole("button",{name:"Previous scene",exact:true})).toBeEnabled();
    } else {
      await waitFor(()=>expect(scroll).toHaveBeenCalled());
      expect(scroll.mock.instances.some(element => element?.getAttribute("data-dmb-playable-id") === "scene:warehouse")).toBe(true);
    }
    expect(prepare).not.toHaveBeenCalled();
    expect(commit).not.toHaveBeenCalled();
    page.unmount();
  } finally { HTMLElement.prototype.scrollIntoView = priorScroll; }
});

it("does not restore a scene absent from the current Plan draft", async () => {
  const {writePlanScenePosition} = await import("./planScenePosition");
  writePlanScenePosition(worldId,savedAgentPlanId,"scene:removed");
  mockSavedPlanForAgent(savedAgentPlanId,7,7,currentTwoScenePlanMarkdown);
  const prepare = vi.spyOn(liveApi,"prepareTiptapMarkdownWrite");
  window.history.replaceState({},"",`/plan?world=${worldId}&documentId=${savedAgentPlanId}&view=cards`);
  render(<SelectedWorldProvider locationSnapshot={window.location.pathname+window.location.search}><VerifiedPlanPage /></SelectedWorldProvider>);
  await screen.findByTestId("world-owned-plan-markdown-editor");
  const arrival = await screen.findByRole("button",{name:"Show scene: Arrival"});
  await waitFor(()=>expect(arrival).toHaveAttribute("aria-current","true"));
  expect(screen.getByRole("button",{name:"Previous scene",exact:true})).toBeDisabled();
  expect(prepare).not.toHaveBeenCalled();
});

it('opens the current scene encounter tool while retaining the mounted Plan editor and scene position',async()=>{
  mockSavedPlanForAgent(savedAgentPlanId,7,7,currentTwoScenePlanMarkdown);
  const sceneApi=await import('../combat/sceneTemplatesApi');vi.spyOn(sceneApi,'getSceneTemplate').mockResolvedValue(null);
  render(<SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentInteractionProvider><AskPluginSlotProvider><PlanSurfacePage/><ToolHost/><LegacyProjectionHostAdapter/></AskPluginSlotProvider></AgentInteractionProvider></SelectedWorldProvider>);
  const button=await screen.findByRole('button',{name:'Scene encounter'});
  const editor=screen.getByTestId('world-owned-plan-editor');const before=editor.querySelector('.ProseMirror');
  fireEvent.click(button);
  await screen.findByRole('region',{name:'Encounter preparation for Arrival'});
  expect(before?.isConnected).toBe(true);expect(editor.querySelector('.ProseMirror')).toBe(before);
  expect(sceneApi.getSceneTemplate).toHaveBeenCalledWith(expect.objectContaining({worldId,documentId:savedAgentPlanId,sceneId:'scene:arrival'}));
});


it('fences ordinary Plan Save during proposal apply, uncertain confirmation and reload',async()=>{
  const nativeNavigator=navigator;let lockTail:Promise<unknown>=Promise.resolve();
  const locks={request:(_name:string,work:()=>unknown)=>{const turn=lockTail.then(work);lockTail=turn.catch(()=>undefined);return turn;}};
  vi.stubGlobal('navigator',new Proxy(nativeNavigator,{get:(target,key)=>key==='locks'?locks:Reflect.get(target,key,target)}));
  mockSavedPlanForAgent(savedAgentPlanId,7,7,'# Plan\n\nOpening frame');
  const prepareSave=vi.spyOn(liveApi,'prepareTiptapMarkdownWrite');
  const commitSave=vi.spyOn(liveApi,'commitWorldOwnedPlanMarkdownWrite');
  const tree=()=> <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>;
  let mounted=render(tree());
  await screen.findByTestId('world-owned-plan-markdown-editor');
  await waitFor(()=>expect(planImageHostCapture.props?.editBridge?.captureAuthoring).toBeTypeOf('function'));
  const bridge=planImageHostCapture.props.editBridge;
  const identity={idempotencyKey:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',conversationId:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',pointerRevision:1};
  let captured:any,prepared:any;
  const expected={worldId,documentId:savedAgentPlanId,threadId:'synthetic-thread',namespace:'synthetic-plan'};
  const binding=()=>({mounted:true,verifiedWorldId:worldId,activeThreadId:'synthetic-thread',
    scope:{campaignId:'synthetic-plan',surfaceId:'plan',sessionNumber:null,documentId:savedAgentPlanId}});
  await act(async()=>{captured=await bridge.captureAuthoring(identity);
    prepared=await bridge.prepareAuthoring(captured.target,'A proposed opening.','cccccccc-cccc-4ccc-8ccc-cccccccccccc',expected,binding);});
  const application={application_id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',capture:captured.capture,
    markdown:prepared.admitted.canonicalMarkdown,after_editor_json:prepared.afterEditorJson,after_editor_sha256:prepared.afterEditorSha256,
    after_markdown:prepared.afterMarkdown,after_draft_sha256:prepared.afterDraftSha256,after_title:bridge.authoringTitle(),outcome:'applying'};
  let rejectConfirm!:(reason:Error)=>void;
  const confirm=vi.fn(()=>new Promise((_resolve,reject)=>{rejectConfirm=reject;}));
  const ordinarySave=capturedPlanControls().save;
  let saving!:Promise<unknown>,competing!:Promise<unknown>;
  act(()=>{saving=bridge.saveAuthoring(captured.target,prepared,application,expected,binding,confirm);
    void saving.catch(()=>undefined);
    competing=bridge.saveAuthoring(captured.target,prepared,{...application,application_id:'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee'},expected,binding,confirm);
    void competing.catch(()=>undefined);});
  await act(async()=>{await expect(competing).rejects.toThrow(/pending application/);});
  act(()=>ordinarySave());
  await waitFor(()=>expect(confirm).toHaveBeenCalledTimes(1));
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,800));});
  expect(prepareSave).not.toHaveBeenCalled();expect(commitSave).not.toHaveBeenCalled();
  const key=`dmb:world-plan-local-draft:v2:${worldId}`;
  const holdKey=Object.keys(localStorage).find(key=>key.startsWith('dmb:plan-application-hold:v1:'))!;
  expect(JSON.parse(localStorage.getItem(holdKey)!).application_id).toBe(application.application_id);
  await act(async()=>{rejectConfirm(new Error('Lost confirmation response'));await saving.catch(()=>undefined);});
  const retained=JSON.parse(localStorage.getItem(key)!);expect(retained.markdown).toContain('A proposed opening.');
  mounted.unmount();mounted=render(tree());
  await screen.findByTestId('world-owned-plan-markdown-editor');
  act(()=>capturedPlanControls().save());
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,800));});
  expect(prepareSave).not.toHaveBeenCalled();expect(commitSave).not.toHaveBeenCalled();
  expect(JSON.parse(localStorage.getItem(holdKey)!).application_id).toBe(application.application_id);
  expect(screen.getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('A proposed opening.');
  mounted.unmount();
  // Opening another Plan rewrites the ordinary current-draft slot; the pending
  // application pointer must survive independently through another reload.
  const other='other-plan-navigation';
  mockSavedPlanForAgent(other,7,7,'# Other Plan\n');
  const otherTree=()=> <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${other}`}><AgentEnabledPlanPage /></SelectedWorldProvider>;
  mounted=render(otherTree());await screen.findByTestId('world-owned-plan-markdown-editor');mounted.unmount();
  mounted=render(otherTree());await screen.findByTestId('world-owned-plan-markdown-editor');mounted.unmount();
  mockSavedPlanForAgent(savedAgentPlanId,7,7,'# Plan\n\nOpening frame');
  mounted=render(tree());await screen.findByTestId('world-owned-plan-markdown-editor');
  act(()=>capturedPlanControls().save());
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,800));});
  expect(prepareSave).not.toHaveBeenCalled();expect(commitSave).not.toHaveBeenCalled();
  expect(JSON.parse(localStorage.getItem(holdKey)!).application_id).toBe(application.application_id);
  const recoveryApi=await import('../api/planAuthoringReviewApi');
  const actionId=prepared.admitted.response.action_id;
  const savedReview={schema:'dmb_plan_authoring_review_snapshot_v1',world_id:worldId,action_id:actionId,origin_sha256:'a'.repeat(64),
    review:{applications:[application]}};
  const readReview=vi.spyOn(recoveryApi,'readPlanAuthoringReview').mockResolvedValue(savedReview as any);
  const currentBridge=planImageHostCapture.props.editBridge;
  await expect(currentBridge.reconcileAuthoring(actionId,application.application_id)).rejects.toThrow(/still unresolved/);
  expect(localStorage.getItem(holdKey)).not.toBeNull();
  readReview.mockResolvedValue({...savedReview,review:{applications:[{...application,outcome:'superseded'}]}} as any);
  const editorNode=screen.getByTestId('world-owned-plan-markdown-editor');const beforeRecovery=editorNode.textContent;
  await act(async()=>{await currentBridge.reconcileAuthoring(actionId,application.application_id);});
  expect(localStorage.getItem(holdKey)).toBeNull();expect(editorNode.textContent).toBe(beforeRecovery);
  mounted.unmount();
});


it('serializes two mounted Plan hosts so only one pending application can mutate the page',async()=>{
  const nativeNavigator=navigator;let tail:Promise<unknown>=Promise.resolve();
  const locks={request:(_name:string,work:()=>unknown)=>{const next=tail.then(work);tail=next.catch(()=>undefined);return next;}};
  vi.stubGlobal('navigator',new Proxy(nativeNavigator,{get:(target,key)=>key==='locks'?locks:Reflect.get(target,key,target)}));
  mockSavedPlanForAgent(savedAgentPlanId,7,7,'# Plan\n\nOpening frame');
  const ordinary=vi.spyOn(liveApi,'prepareTiptapMarkdownWrite');
  const tree=()=> <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><AgentEnabledPlanPage /></SelectedWorldProvider>;
  const first=render(tree());await within(first.container).findByTestId('world-owned-plan-markdown-editor');
  await waitFor(()=>expect(planImageHostCapture.props?.editBridge?.captureAuthoring).toBeTypeOf('function'));
  const a=planImageHostCapture.props.editBridge;
  const second=render(tree());await within(second.container).findByTestId('world-owned-plan-markdown-editor');
  await waitFor(()=>{expect(planImageHostCapture.props?.editBridge?.captureAuthoring).toBeTypeOf('function');expect(planImageHostCapture.props.editBridge).not.toBe(a);});
  const b=planImageHostCapture.props.editBridge;
  const expected={worldId,documentId:savedAgentPlanId,threadId:'synthetic-thread',namespace:'synthetic-plan'};
  const binding=()=>({mounted:true,verifiedWorldId:worldId,activeThreadId:'synthetic-thread',
    scope:{campaignId:'synthetic-plan',surfaceId:'plan',sessionNumber:null,documentId:savedAgentPlanId}});
  async function prepared(bridge:any,action:string,applicationId:string){
    const captured=await bridge.captureAuthoring({idempotencyKey:action,conversationId:'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb',pointerRevision:1});
    const draft=await bridge.prepareAuthoring(captured.target,'Only one proposed opening.',action,expected,binding);
    return {captured,draft,application:{application_id:applicationId,capture:captured.capture,
      markdown:draft.admitted.canonicalMarkdown,after_editor_json:draft.afterEditorJson,after_editor_sha256:draft.afterEditorSha256,
      after_markdown:draft.afterMarkdown,after_draft_sha256:draft.afterDraftSha256,after_title:bridge.authoringTitle(),outcome:'applying'}};
  }
  let left:any,right:any;
  await act(async()=>{left=await prepared(a,'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa','cccccccc-cccc-4ccc-8ccc-cccccccccccc');
    right=await prepared(b,'dddddddd-dddd-4ddd-8ddd-dddddddddddd','eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee');});
  const confirm=vi.fn(async()=>{throw new Error('Unknown confirmation outcome');});
  let results:PromiseSettledResult<unknown>[]=[];
  await act(async()=>{results=await Promise.allSettled([
    a.saveAuthoring(left.captured.target,left.draft,left.application,expected,binding,confirm),
    b.saveAuthoring(right.captured.target,right.draft,right.application,expected,binding,confirm),
  ]);});
  expect(confirm).toHaveBeenCalledTimes(1);expect(results.every(item=>item.status==='rejected')).toBe(true);
  expect(within(first.container).getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('Only one proposed opening.');
  expect(within(second.container).getByTestId('world-owned-plan-markdown-editor')).not.toHaveTextContent('Only one proposed opening.');
  expect(Object.keys(localStorage).filter(key=>key.startsWith('dmb:plan-application-hold:v1:'))).toHaveLength(1);
  await act(async()=>{await new Promise(resolve=>setTimeout(resolve,800));});expect(ordinary).not.toHaveBeenCalled();
  first.unmount();second.unmount();
});

it.each(['valid','wrong_work_revision','lost_confirm','lost_confirm_newer','lost_before_commit','newer_draft','move'] as const)('ordinary first Send stages an editable Plan object, saves once and reloads it without drafting in chat (%s)',async mode=>{
  const nativeNavigator=navigator;
  vi.stubGlobal('navigator',new Proxy(nativeNavigator,{get:(target,key)=>key==='locks'?{request:async(_name:string,work:()=>unknown)=>work()}:Reflect.get(target,key,target)}));
  const record=mockSavedPlanForAgent(savedAgentPlanId,7,7,'# Plan\n\nOriginal preparation.\n');
  const reviewApi=await import('../api/planAuthoringReviewApi');
  const conversationId='11111111-1111-4111-8111-111111111111';let conversationReady=false;
  vi.mocked(liveApi.getWorldAgentConversationHistory).mockImplementation(async()=>({schema:'dmb_agent_conversation_history_v3',world_id:worldId,
    conversation_state:conversationReady?'active':'absent',conversation_id:conversationReady?conversationId:null,
    active_conversation_id:conversationReady?conversationId:null,pointer_revision:conversationReady?1:0,turns:[...serverHistoryTurns],next_before_sequence:null}));
  const newConversation=vi.spyOn(liveApi,'postWorldAgentNewConversation').mockImplementation(async(owner,request)=>{
    expect(request.expected_active_conversation_id).toBeNull();expect(request.expected_pointer_revision).toBe(0);
    const retained=Object.keys(localStorage).map(key=>localStorage.getItem(key)).some(raw=>raw?.includes(request.command_id));
    expect(retained).toBe(true);conversationReady=true;
    return {schema:'dmb_agent_new_conversation_response_v1',world_id:owner,conversation_id:conversationId,active_conversation_id:conversationId,pointer_revision:1};
  });
  const hash=(text:string)=>createHash('sha256').update(text).digest('hex');
  const action='aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',turn='bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
  let proposal:any,review:any=null,originHash='',lostConfirm=false;
  const post=vi.spyOn(liveApi,'postWorldPlanAgentTurn').mockImplementation(async request=>{
    expect(conversationReady).toBe(true);expect(request.plan_authoring_capture).toBeDefined();
    const response:any=worldPlanAgentResponse(request),capture=request.plan_authoring_capture!;
    expect(capture.conversation_id).toBe(conversationId);expect(capture.expected_pointer_revision).toBe(1);
    expect(capture.idempotency_key).toBe(historyCorrelationKey(request));
    const markdown='## Proposed visitors\n\nA traveling keeper may ask about the lantern.\n';
    const origin={schema:'dmb_plan_jev_proposal_origin_v1',action_id:action,idempotency_key:capture.idempotency_key,
      action_request_fingerprint:'c'.repeat(64),action_fence:1,basis:structuredClone(response.plan_context.receipt.plan_basis),
      conversation_id:conversationId,turn_id:turn,product_attempt:1,expected_pointer_revision:1,
      context_receipt_sha256:response.plan_context.receipt.context_receipt_sha256,execution_policy_sha256:'d'.repeat(64),
      capture_sha256:hash(canonicalFixtureJson(capture)),controller_attempt_id:'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
      selection_event_id:'dddddddd-dddd-4ddd-8ddd-dddddddddddd',expected_turn_revision:2,
      writer_attempt_id:'eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee',writer_envelope_sha256:'e'.repeat(64),raw_reply_sha256:'f'.repeat(64),
      evidence_event_ids:[],replacement_markdown_sha256:hash(markdown)};
    if(mode==='wrong_work_revision')origin.basis.work_revision_id='ffffffff-ffff-4fff-8fff-ffffffffffff';
    proposal={schema:'dmb_plan_authored_proposal_v1',capture,origin,replacement_markdown:markdown};originHash=hash(canonicalFixtureJson(origin));
    const retained=serverHistoryTurns.at(-1)!;retained.turn_id=turn;retained.plan_proposal=proposal;
    return {...response,plan_proposal:proposal};
  });
  vi.spyOn(reviewApi,'readPlanAuthoringReview').mockImplementation(async()=>({schema:'dmb_plan_authoring_review_snapshot_v1',
    world_id:worldId,action_id:action,origin_sha256:originHash,review}));
  const commands=vi.spyOn(reviewApi,'commandPlanAuthoringReview').mockImplementation(async(_world,_action,command)=>{
    expect(command.expected_revision).toBe(review?.revision??0);expect(command.origin_sha256).toBe(originHash);
    if(command.operation==='open')review={schema:'dmb_plan_authoring_review_v1',world_id:worldId,action_id:action,origin_sha256:originHash,
      revision:0,state:'editing',markdown:proposal.replacement_markdown,markdown_sha256:hash(proposal.replacement_markdown),capture:proposal.capture,applications:[]};
    if(command.operation==='move')review={...review,capture:command.capture};
    if(command.operation==='save')review={...review,markdown:command.markdown,markdown_sha256:hash(command.markdown)};
    if(command.operation==='prepare')review={...review,state:'applying',applications:[{...command,capture:review.capture,
      markdown:review.markdown,markdown_sha256:review.markdown_sha256,base_work_revision_id:proposal.origin.basis.work_revision_id,
      base_revision_n:4,outcome:'applying',saved_work_revision_id:null,saved_revision_n:null}]};
    if(command.operation==='confirm'&&mode==='lost_before_commit'&&!lostConfirm){lostConfirm=true;throw new Error('Lost confirmation before commit');}
    if(command.operation==='confirm'){
      const application=review.applications.at(-1),updated={...record,revision:8};
      const previous=await liveApi.getWorldOwnedPlanCommittedRevision(savedAgentPlanId);
      vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockResolvedValue({schema_version:'dmb_workspace_document_snapshot_v2',record:updated,
        markdown:application.after_markdown,content_sha256:application.after_draft_sha256,file_fingerprint:'postgres',file_exists:true,loaded_revision:8});
      vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue({...previous,object_revision:8,revision_n:5,
        work_revision_id:'00000000-0000-4000-8000-000000000005',markdown:application.after_markdown,content_sha256:application.after_draft_sha256});
      review={...review,state:'applied',applications:[{...application,outcome:'saved',saved_work_revision_id:'00000000-0000-4000-8000-000000000005',saved_revision_n:5}]};
    }
    review={...review,revision:review.revision+1,last_command_id:command.command_id,last_command_sha256:'a'.repeat(64),updated_at:'2026-10-26T00:00:00Z'};
    if(command.operation==='confirm'&&(mode==='lost_confirm'||mode==='lost_confirm_newer')&&!lostConfirm){lostConfirm=true;throw new Error('Lost confirmation after commit');}
    return review;
  });
  const ordinary=vi.spyOn(liveApi,'prepareTiptapMarkdownWrite');
  const tree=()=> <SelectedWorldProvider locationSnapshot={`/plan?world=${worldId}&documentId=${savedAgentPlanId}`}><WorldHostedPlanPage /></SelectedWorldProvider>;
  let mounted=render(tree());await screen.findByTestId('world-owned-plan-markdown-editor');await openPlanConversation();
  const editor=(screen.getByTestId('world-owned-plan-markdown-editor').querySelector('.ProseMirror') as any).editor;
  act(()=>editor.commands.setTextSelection(editor.state.doc.content.size-1));
  const conversation=savedWorldPlanConversation();
  fireEvent.change(messageDungeonBuddyField(conversation),{target:{value:'Invent a short section of possible visitors and put it on this Plan.'}});
  const send=within(conversation).getByRole('button',{name:'Send message',exact:true});
  await waitFor(()=>expect(send).toBeEnabled());fireEvent.click(send);
  await waitFor(()=>expect(post,conversation.textContent??'').toHaveBeenCalledTimes(1));
  if(mode==='wrong_work_revision'){
    await waitFor(()=>expect(document.body.textContent).toContain('response did not match this saved Plan'));
    expect(screen.queryByRole('textbox',{name:'Suggestion text'})).not.toBeInTheDocument();
    expect(Object.keys(localStorage).filter(key=>key.startsWith('dmb:world-plan-pending-ask:v1:'))).toHaveLength(1);
    expect(commands).not.toHaveBeenCalled();mounted.unmount();return;
  }
  let suggestion=await screen.findByRole('textbox',{name:'Suggestion text'});
  expect(newConversation).toHaveBeenCalledTimes(1);expect(post).toHaveBeenCalledTimes(1);
  expect(suggestion).toHaveTextContent('A traveling keeper may ask about the lantern.');
  expect(suggestion.closest('[data-turn-id]')).toBeNull();
  expect(within(conversation).queryByText('A traveling keeper may ask about the lantern.')).not.toBeInTheDocument();
  if(mode==='newer_draft'){
    act(()=>editor.commands.insertContent(' Author added a newer sentence.'));
    await waitFor(()=>expect(screen.queryByRole('textbox',{name:'Suggestion text'})).not.toBeInTheDocument());
    await openPlanConversation();fireEvent.click(await screen.findByRole('button',{name:'Use current page placement'}));
    suggestion=await screen.findByRole('textbox',{name:'Suggestion text'});
  }
  if(mode==='move'){
    const originalFrom=review.capture.from;
    fireEvent.click(screen.getByRole('button',{name:'Move',exact:true}));
    act(()=>{editor.commands.setTextSelection(7);editor.view.focus();});
    fireEvent.keyDown(editor.view.dom,{key:'Enter'});
    await waitFor(()=>expect(review.capture.from).toBe(7));expect(review.capture.from).not.toBe(originalFrom);
    suggestion=screen.getByRole('textbox',{name:'Suggestion text'});
  }
  const suggestionEditor=(suggestion as any).editor;
  act(()=>{suggestionEditor.commands.setTextSelection(suggestionEditor.state.doc.content.size-1);suggestionEditor.commands.insertContent(' Keep this cue.');});
  const region=screen.getByRole('region',{name:'Suggestion review'});
  fireEvent.click(within(region).getByRole('button',{name:'Save',exact:true}));
  if(mode==='lost_confirm'||mode==='lost_confirm_newer'||mode==='lost_before_commit'){
    await waitFor(()=>expect(document.body.textContent).toContain('Lost confirmation'));
    expect(Object.keys(localStorage).filter(key=>key.startsWith('dmb:plan-application-hold:'))).toHaveLength(1);
    mounted.unmount();mounted=render(tree());await screen.findByTestId('world-owned-plan-markdown-editor');await openPlanConversation();
    expect(commands.mock.calls.filter(call=>call[2].operation==='confirm')).toHaveLength(1);
    expect(ordinary).not.toHaveBeenCalled();
    if(mode==='lost_before_commit')fireEvent.click(await screen.findByRole('button',{name:'Retry exact confirm operation'}));
    await waitFor(()=>expect(review?.state).toBe('applied'));
    if(mode==='lost_confirm_newer'){
      const recoveredEditor=(screen.getByTestId('world-owned-plan-markdown-editor').querySelector('.ProseMirror') as any).editor;
      act(()=>recoveredEditor.commands.insertContent(' A newer local sentence after the saved proposal.'));
    }
    const acknowledge=await screen.findByRole('button',{name:'Acknowledge saved result'});fireEvent.click(acknowledge);
  }
  await waitFor(()=>expect(review?.state).toBe('applied'));
  await waitFor(()=>expect(Object.keys(localStorage).filter(key=>key.startsWith('dmb:plan-application-hold:'))).toHaveLength(0));
  expect(screen.getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('Keep this cue.');
  if(mode==='newer_draft')expect(screen.getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('Author added a newer sentence.');
  if(mode==='lost_confirm_newer')expect(screen.getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('A newer local sentence after the saved proposal.');
  expect(commands.mock.calls.filter(call=>call[2].operation==='confirm')).toHaveLength(mode==='lost_before_commit'?2:1);
  if(mode==='lost_before_commit')expect(new Set(commands.mock.calls.filter(call=>call[2].operation==='confirm').map(call=>call[2].command_id)).size).toBe(1);
  expect(ordinary).not.toHaveBeenCalled();
  mounted.unmount();mounted=render(tree());await screen.findByTestId('world-owned-plan-markdown-editor');
  expect(screen.getByTestId('world-owned-plan-markdown-editor')).toHaveTextContent('Keep this cue.');
  expect(post).toHaveBeenCalledTimes(1);expect(commands.mock.calls.filter(call=>call[2].operation==='confirm')).toHaveLength(mode==='lost_before_commit'?2:1);
  mounted.unmount();
});


function OpenPlanTour() {
  const tour = useGuidedTour();
  return <button onClick={tour?.open}>Open Plan walkthrough</button>;
}
function ResumedPlanPage() {
  return <GuidedTourProvider worldId={worldId}><VerifiedPlanPage /><OpenPlanTour /></GuidedTourProvider>;
}
async function resumedPlanFixture(phase: 'running' | 'paused' = 'running') {
  planEncounterCapture.context = null;
  const record = mockSavedPlanForAgent(savedAgentPlanId, 7, 7, currentTwoScenePlanMarkdown);
  const prior = await liveApi.getWorldOwnedPlanCommittedRevision(record.document_id);
  const committed = {...prior, has_divergent_working_copy:false};
  const read = vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockResolvedValue(committed);
  read.mockClear();
  Object.defineProperty(navigator, 'locks', {configurable:true,value:{request:vi.fn(async (_:string, action:()=>unknown)=>action())}});
  let walkthrough = createWalkthrough(worldId, 'sheep', 'resumed-plan-tour', '2026-10-28T00:00:00Z');
  walkthrough = reduceTour(walkthrough, {kind:'bind',pin:{kind:'plan',worldId,objectId:record.document_id,revision:committed.revision_n,revisionId:committed.work_revision_id,digest:committed.content_sha256}});
  if (phase === 'paused') walkthrough = reduceTour(walkthrough,{kind:'phase',phase});
  writeWalkthrough(localStorage,walkthrough,null);
  const location = `/plan?world=${worldId}&documentId=${record.document_id}`;
  const mount = () => render(<SelectedWorldProvider locationSnapshot={location}><ResumedPlanPage /></SelectedWorldProvider>);
  return {committed, read, mount};
}

it('reverifies a resumed clean Plan on mount/remount without opening Play or writing, and only observes an existing Plan', async () => {
  const {committed,read,mount}=await resumedPlanFixture();
  const write=vi.spyOn(liveApi,'commitWorldOwnedPlanMarkdownWrite');
  const first=mount();
  await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
  expect(read).toHaveBeenCalledOnce();
  expect(screen.queryByRole('heading',{name:'Play this Plan'})).not.toBeInTheDocument();
  await waitFor(()=>expect(readWalkthrough(localStorage,worldId)?.record.steps.plan.state).toBe('existing'));
  expect(readWalkthrough(localStorage,worldId)?.record.steps.mechanics.evidence).toEqual([]);
  expect(readWalkthrough(localStorage,worldId)?.record.steps.adoption.evidence).toEqual([]);
  first.unmount();planEncounterCapture.context=null;mount();
  await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
  expect(read).toHaveBeenCalledTimes(2);expect(write).not.toHaveBeenCalled();
});

it('does not verify paused guidance until Resume and does not open a Play dialog', async () => {
  const {committed,read,mount}=await resumedPlanFixture('paused');mount();
  await screen.findByTestId('world-owned-plan-markdown-editor');
  await waitFor(()=>expect(screen.getByTestId('world-plan-start-play')).toBeEnabled());
  expect(read).not.toHaveBeenCalled();expect(planEncounterCapture.context?.verifiedPlan).toBeNull();
  fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));
  fireEvent.click(screen.getByRole('button',{name:'Resume',exact:true}));
  await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
  expect(read).toHaveBeenCalledOnce();expect(screen.queryByRole('heading',{name:'Play this Plan'})).not.toBeInTheDocument();
});

it.each(['world','revision','hash','body','working-copy','inactive','campaign','work-id'] as const)(
  'refuses resumed Plan verification with mismatched %s and does not automatically retry',async mode=>{
    const {committed,read,mount}=await resumedPlanFixture();
    const changed={...committed};
    if(mode==='world')changed.world_id='different-world';
    if(mode==='revision')changed.object_revision++;
    if(mode==='hash')changed.content_sha256='e'.repeat(64);
    if(mode==='body')changed.markdown+='Changed text';
    if(mode==='working-copy')changed.has_divergent_working_copy=true;
    if(mode==='inactive')changed.status='trashed';
    if(mode==='campaign')changed.campaign_id='foreign-campaign';
    if(mode==='work-id')changed.work_revision_id='not-an-immutable-uuid';
    read.mockResolvedValue(changed);mount();
    await screen.findByTestId('world-plan-start-play-error');
    expect(planEncounterCapture.context?.verifiedPlan).toBeNull();
    await act(async()=>{});expect(read).toHaveBeenCalledOnce();
    expect(readWalkthrough(localStorage,worldId)?.record.steps.mechanics.evidence).toEqual([]);
    read.mockResolvedValue(committed);fireEvent.click(screen.getByTestId('world-plan-start-play'));
    await screen.findByRole('heading',{name:'Play this Plan'});
    expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id);
    // Session preparation also performs its own read; no background retry happened before this explicit click.
  },
);

it.each(['edit','location','unmount','pause'] as const)('drops a resumed Plan reply after %s',async mode=>{
 const {committed,read,mount}=await resumedPlanFixture();let resolve!:(v:WorldOwnedCommittedRevisionV2)=>void;
 read.mockImplementationOnce(()=>new Promise(r=>{resolve=r;}));const mounted=mount();
 await waitFor(()=>expect(read).toHaveBeenCalledOnce());
 if(mode==='edit')act(()=>capturedPlanControls().changeTitle({target:{value:'New unsaved draft'}}));
 if(mode==='location')window.history.replaceState({},'',`/plan?world=other&documentId=${savedAgentPlanId}`);
 if(mode==='unmount')mounted.unmount();
 if(mode==='pause'){fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));fireEvent.click(screen.getByRole('button',{name:'Pause',exact:true}));await screen.findByText('Guidance paused');}
 await act(async()=>resolve(committed));
 expect(planEncounterCapture.context?.verifiedPlan).toBeNull();
 expect(readWalkthrough(localStorage,worldId)?.record.steps.plan.evidence).toEqual([]);
 if(mode==='edit')expect(JSON.parse(localStorage.getItem(`dmb:world-plan-local-draft:v2:${worldId}`)!).title).toBe('New unsaved draft');
});

it('restarts pending verification for the new walkthrough and rejects the old reply',async()=>{
 const {committed,read,mount}=await resumedPlanFixture();let resolve!:(v:WorldOwnedCommittedRevisionV2)=>void;
 read.mockImplementationOnce(()=>new Promise(r=>{resolve=r;}));mount();await waitFor(()=>expect(read).toHaveBeenCalledOnce());
 fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));fireEvent.click(screen.getByRole('button',{name:'Restart guidance',exact:true}));
 await waitFor(()=>expect(read).toHaveBeenCalledTimes(2));
 await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
 await act(async()=>resolve({...committed,world_id:'old-foreign-world'}));
 expect(screen.queryByTestId('world-plan-start-play-error')).not.toBeInTheDocument();
 expect(readWalkthrough(localStorage,worldId)?.record.id).not.toBe('resumed-plan-tour');
});

it('manual preview supersedes a pending background refusal and later refusal clears cached scope',async()=>{
 const {committed,read,mount}=await resumedPlanFixture();let reject!:(v:Error)=>void;
 read.mockImplementationOnce(()=>new Promise((_,r)=>{reject=r;}));mount();await waitFor(()=>expect(read).toHaveBeenCalledOnce());
 fireEvent.click(screen.getByTestId('world-plan-start-play'));await screen.findByRole('heading',{name:'Play this Plan'});
 await act(async()=>reject(new Error('Earlier background failure')));
 expect(screen.queryByTestId('world-plan-start-play-error')).not.toBeInTheDocument();
 expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id);
 // Close the preview, then explicitly check again against a now-refused owner result.
 fireEvent.keyDown(document,{key:'Escape'});
 await waitFor(()=>expect(screen.queryByRole('heading',{name:'Play this Plan'})).not.toBeInTheDocument());
 read.mockResolvedValue({...committed,has_divergent_working_copy:true});fireEvent.click(screen.getByTestId('world-plan-start-play'));
 await screen.findByTestId('world-plan-start-play-error');
 expect(planEncounterCapture.context?.verifiedPlan).toBeNull();
});


it('cancels a pending background read when another tab replaces the running walkthrough',async()=>{
 const {committed,read,mount}=await resumedPlanFixture();let resolve!:(v:WorldOwnedCommittedRevisionV2)=>void;
 read.mockImplementationOnce(()=>new Promise(r=>{resolve=r;}));mount();await waitFor(()=>expect(read).toHaveBeenCalledOnce());
 const retained=readWalkthrough(localStorage,worldId)!;
 writeWalkthrough(localStorage,createWalkthrough(worldId,'sheep','other-tab-walk','2026-10-28T01:00:00Z'),retained);
 act(()=>window.dispatchEvent(new StorageEvent('storage',{key:`dmb:guided-journey:v1:${worldId}:current`})));
 await waitFor(()=>expect(read).toHaveBeenCalledTimes(2));
 await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
 await act(async()=>resolve({...committed,world_id:'old-foreign-world'}));
 expect(screen.queryByTestId('world-plan-start-play-error')).not.toBeInTheDocument();
 expect(readWalkthrough(localStorage,worldId)?.record.id).toBe('other-tab-walk');
});


it('rechecks on pause/resume and clears a previously cached pin when the owner refuses it',async()=>{
 const {committed,read,mount}=await resumedPlanFixture();mount();
 await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
 fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));
 fireEvent.click(screen.getByRole('button',{name:'Pause',exact:true}));await screen.findByText('Guidance paused');
 read.mockRejectedValue(new Error('Owner temporarily unavailable. Use Start Play to retry verification.'));
 fireEvent.click(screen.getByRole('button',{name:'Resume',exact:true}));
 await screen.findByTestId('world-plan-start-play-error');
 expect(planEncounterCapture.context?.verifiedPlan).toBeNull();
 await act(async()=>{});expect(read).toHaveBeenCalledTimes(2);
});


it('opens the ordinary Statblocks projection from the exact Plan generation step without dispatching or saving',async()=>{
 const {committed}=await resumedPlanFixture();const retained=readWalkthrough(localStorage,worldId)!;
 writeWalkthrough(localStorage,reduceTour(retained.record,{kind:'move',index:3}),retained);
 const generate=vi.spyOn(liveApi,'generateThreatDraftCandidate'),save=vi.spyOn(liveApi,'commitWorldOwnedPlanMarkdownWrite');
 const location=`/plan?world=${worldId}&documentId=${savedAgentPlanId}`;
 render(<SelectedWorldProvider locationSnapshot={location}><AgentInteractionProvider><AskPluginSlotProvider><GuidedTourProvider worldId={worldId}><PlanSurfacePage/><ToolHost/><LegacyProjectionHostAdapter/><OpenPlanTour/></GuidedTourProvider></AskPluginSlotProvider></AgentInteractionProvider></SelectedWorldProvider>);
 await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
 fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));fireEvent.click(await screen.findByRole('button',{name:'Open Statblocks',exact:true}));
 await screen.findByTestId('create-and-generate-submit');
 expect(screen.getByTestId('create-and-generate-submit')).toHaveAttribute('data-guided-control','generation');
 expect(generate).not.toHaveBeenCalled();expect(save).not.toHaveBeenCalled();
 expect(readWalkthrough(localStorage,worldId)?.record.steps.generation.state).not.toBe('completed');
});

it('opens the real saved Plan preview through guidance without starting a Run or saving',async()=>{
 const {committed,mount}=await resumedPlanFixture();
 const retained=readWalkthrough(localStorage,worldId)!;
 writeWalkthrough(localStorage,reduceTour(retained.record,{kind:'move',index:2}),retained);
 const save=vi.spyOn(liveApi,'commitWorldOwnedPlanMarkdownWrite');
 mount();await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
 fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));
 fireEvent.click(await screen.findByRole('button',{name:'Open saved Plan preview'}));
 await screen.findByRole('heading',{name:'Play this Plan'});
 expect(screen.queryByRole('complementary',{name:'Guided journey'})).not.toBeInTheDocument();
 expect(window.location.pathname).toBe('/plan');expect(save).not.toHaveBeenCalled();
 expect(readWalkthrough(localStorage,worldId)?.record.bindings.run).toBeUndefined();
 expect(readWalkthrough(localStorage,worldId)?.record.steps.play.evidence).toEqual([]);
});
it('does not open a late guided Plan preview after guidance restarts',async()=>{
 const {committed,read,mount}=await resumedPlanFixture();const retained=readWalkthrough(localStorage,worldId)!;
 writeWalkthrough(localStorage,reduceTour(retained.record,{kind:'move',index:2}),retained);
 mount();await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
 let release!:(value:WorldOwnedCommittedRevisionV2)=>void;
 read.mockImplementationOnce(()=>new Promise(resolve=>{release=resolve;}));
 fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));fireEvent.click(await screen.findByRole('button',{name:'Open saved Plan preview'}));
 await waitFor(()=>expect(release).toBeTypeOf('function'));
 fireEvent.click(screen.getByRole('button',{name:'Restart guidance'}));await waitFor(()=>expect(readWalkthrough(localStorage,worldId)?.record.id).not.toBe('resumed-plan-tour'));
 await act(async()=>{release(committed);});expect(screen.queryByRole('heading',{name:'Play this Plan'})).not.toBeInTheDocument();
 expect(readWalkthrough(localStorage,worldId)?.record.bindings.run).toBeUndefined();
});


it('rejects a changed bound Plan before replacing the current editor and URL through guidance',async()=>{
 const {committed,mount}=await resumedPlanFixture();
 const original=await liveApi.getWorldOwnedPlanSnapshot(savedAgentPlanId);
 const otherId='99999999-9999-4999-8999-999999999999',otherWork='88888888-8888-4888-8888-888888888888';
 const other={...original,record:{...original.record,document_id:otherId,title:'Other saved Plan'}};
 vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockImplementation(async id=>id===otherId?other:original);
 vi.mocked(liveApi.getWorldOwnedPlanCommittedRevision).mockImplementation(async id=>id===otherId?{...committed,document_id:otherId,work_revision_id:otherWork}:committed);
 vi.mocked(liveApi.listWorldOwnedPlans).mockResolvedValue({schema_version:'dmb_workspace_document_registry_v2',scope_mode:'world',world_id:worldId,records:[original.record,other.record]});
 const old=readWalkthrough(localStorage,worldId)!;
 let walk=createWalkthrough(worldId,'sheep','bound-plan-drift','2026-10-28T00:00:00Z');
 walk=reduceTour(walk,{kind:'bind',pin:{kind:'plan',worldId,objectId:otherId,revision:committed.revision_n,revisionId:otherWork,digest:'c'.repeat(64)}});walk=reduceTour(walk,{kind:'move',index:2});writeWalkthrough(localStorage,walk,old);
 mount();await waitFor(()=>expect(planEncounterCapture.context?.verifiedPlan?.workRevisionId).toBe(committed.work_revision_id));
 fireEvent.click(screen.getByRole('button',{name:'Open Plan walkthrough'}));fireEvent.click(await screen.findByRole('button',{name:'Open the bound plan'}));
 await screen.findByText(/exact bound Plan version is unavailable/);
 expect(screen.getByLabelText('Plan document')).toHaveValue(savedAgentPlanId);expect(new URLSearchParams(window.location.search).get('documentId')).toBe(savedAgentPlanId);
 expect(readWalkthrough(localStorage,worldId)?.record.bindings.plan?.objectId).toBe(otherId);
});
it('refuses an unavailable exact Plan version on guided route entry before admitting a newer snapshot',async()=>{
 const {committed}=await resumedPlanFixture();const old=readWalkthrough(localStorage,worldId)!;
 const walk={...old.record,index:2,bindings:{plan:{...old.record.bindings.plan!,revision:committed.revision_n-1}}};writeWalkthrough(localStorage,walk,old);
 function MarkRoute(){const registry=useTourNavigationRegistry();useLayoutEffect(()=>{registry?.beginDestination(navigationScope(readWalkthrough(localStorage,worldId)!.record,0)!);},[registry]);return null;}
 render(<SelectedWorldProvider locationSnapshot={window.location.pathname+window.location.search}><GuidedTourProvider worldId={worldId}><MarkRoute/><VerifiedPlanPage/></GuidedTourProvider></SelectedWorldProvider>);
 await screen.findByText(/exact bound Plan version is unavailable/);
 expect(readWalkthrough(localStorage,worldId)?.record.bindings.plan?.revision).toBe(committed.revision_n-1);
 expect(readWalkthrough(localStorage,worldId)?.record.bindings.run).toBeUndefined();
});

it.each(['restart','step'])('cancels a pending guided routed Plan after %s before publishing its editor',async kind=>{
 const {committed}=await resumedPlanFixture();const old=readWalkthrough(localStorage,worldId)!;
 writeWalkthrough(localStorage,{...old.record,index:2},old);
 const original=await liveApi.getWorldOwnedPlanSnapshot(savedAgentPlanId);let release!:(value:typeof original)=>void;
 vi.mocked(liveApi.getWorldOwnedPlanSnapshot).mockReturnValueOnce(new Promise(resolve=>{release=resolve;}));
 function MarkRoute(){const registry=useTourNavigationRegistry();useLayoutEffect(()=>{registry?.beginDestination(navigationScope(readWalkthrough(localStorage,worldId)!.record,0)!);},[registry]);return null;}
 render(<SelectedWorldProvider locationSnapshot={window.location.pathname+window.location.search}><GuidedTourProvider worldId={worldId}><MarkRoute/><VerifiedPlanPage/></GuidedTourProvider></SelectedWorldProvider>);
 await waitFor(()=>expect(release).toBeTypeOf('function'));
 const retained=readWalkthrough(localStorage,worldId)!;
 writeWalkthrough(localStorage,kind==='restart'?createWalkthrough(worldId,'sheep','replacement','2026-10-28T01:00:00Z'):reduceTour(retained.record,{kind:'move',index:3}),retained);
 await act(async()=>release(original));await screen.findByText(/Guided navigation canceled/);
 expect(screen.queryByDisplayValue(original.markdown)).not.toBeInTheDocument();expect(readWalkthrough(localStorage,worldId)?.record.bindings.run).toBeUndefined();
 expect(committed.document_id).toBe(savedAgentPlanId);
});
