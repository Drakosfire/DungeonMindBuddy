import { act, render, screen, waitFor } from "@testing-library/react";
import { useState, type ComponentProps } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { AgentInteractionProvider, useAgentInteraction } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { WorldGraphLensProjectionProvider, WorldGraphLensProvider } from "../graphLens";
import { mockPlanView, mockSourceBundle } from "../test/fixtures";
import type { WorkspaceDocumentRecord, WorkspaceDocumentSnapshot } from "../api/types";
import * as liveApi from "../api/liveApi";
import { tiptapJsonToSemanticMarkdown } from "../tiptap/markdown/calloutMarkdown";
import { markdownToTiptapDoc } from "../tiptap/markdown/markdownToTiptap";
import { indexPlayableStructureV2 } from "../tiptap/playable/playableStructureIndex";
import { AgentInteractionProjectionTestHost } from "./projection/projectionTestHost";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import {
  FIXTURE_DOC_ID,
  fixturePlanSessionDescriptor,
  fixtureWorkspaceDocumentRecord,
  workspaceRecordToPlanDocumentDescriptor,
} from "./config/planSessionDescriptor";
import { EditCapabilityProvider } from "./edit/editCapability";
import { adoptCreatedPlanIdentity } from "./planBlankAuthoringState";
import { PlanGraphLensProvider } from "./PlanGraphLensContext";
import { PlanGraphReferenceResolverProvider } from "./reference/usePlanGraphReferenceResolver";
import { PlanSurfaceCanvas, canSavePlanningDocument } from "./components/PlanSurfaceCanvas";
import { PlanSurfaceShell } from "./PlanSurfaceShell";
import { createWorkspaceDocumentCreationController } from "../workspaceDocument/workspaceDocumentCreation";

const RUNBOOK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const CONTENT_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

/** Frozen BF4A/BF3B dogfood. Validated against the existing BF1 indexer. */
export const BREACH_DOGFOOD_RUNBOOK_MARKDOWN = [
  "# Breach Dogfood Runbook",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-breach beat_kind=spine -->",
  "## Hold the Breach",
  "",
  "Creatures have broken through the defensive wall. The party must decide",
  "whether to pursue the surviving brood or stabilize the breach before the line",
  "fails completely.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->",
  "### North Gate",
  "",
  "The gate is damaged, the last creatures are retreating toward a broken tunnel,",
  "and exhausted defenders are trying to stabilize the wall.",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:surviving-brood scene=scene:north-gate -->",
  "### What do they do with the surviving brood?",
  "",
  "The brood is disappearing underground while the defenders call for help at the",
  "breach.",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:follow-brood activates=scene:tunnel-pursuit,beat:lower-tunnels -->",
  "- Follow it",
  "",
  "  The party pursues the retreating creatures into the lower tunnels before",
  "  reinforcements arrive.",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:seal-breach suppresses=scene:tunnel-pursuit -->",
  "- Seal the breach",
  "",
  "  The immediate breach is contained, but the surviving creatures remain",
  "  somewhere below.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:tunnel-pursuit -->",
  "### Tunnel Pursuit",
  "",
  "The party enters a damaged tunnel after the fleeing creatures while loose stone",
  "and timbers shift overhead.",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:lower-tunnels beat_kind=optional -->",
  "## Lower Tunnels",
  "",
  "Following the brood deeper turns the defense of the gate into a search below",
  "the fortifications.",
  "",
].join("\n");

function optionListItems(doc: { content?: Array<{ type?: string; content?: unknown[]; attrs?: Record<string, unknown> }> }) {
  const items: Array<{ attrs?: Record<string, unknown> }> = [];
  for (const node of doc.content ?? []) {
    if (node.type !== "bulletList") continue;
    for (const item of node.content ?? []) {
      items.push(item as { attrs?: Record<string, unknown> });
    }
  }
  return items;
}

function markdownWindow(markdown: string, startMarker: string, endMarker: string | null): string {
  const start = markdown.indexOf(startMarker);
  const end = endMarker == null ? markdown.length : markdown.indexOf(endMarker);
  expect(start).toBeGreaterThanOrEqual(0);
  if (endMarker != null) expect(end).toBeGreaterThan(start);
  return markdown.slice(start, endMarker == null ? undefined : end);
}

function expectCanonicalBreachDogfood(markdown: string) {
  const imported = markdownToTiptapDoc(markdown);
  expect(imported.diagnostics).toEqual([]);
  const indexed = indexPlayableStructureV2(imported.doc);
  expect(indexed.status).toBe("ready");
  if (indexed.status !== "ready") throw new Error("expected ready v2 index");
  const { index } = indexed;
  expect(index.beats.map((beat) => [beat.beatId, beat.beatKind])).toEqual([
    ["beat:hold-breach", "spine"],
    ["beat:lower-tunnels", "optional"],
  ]);
  expect(index.scenes).toEqual([
    { sceneId: "scene:north-gate", beatId: "beat:hold-breach", order: 0 },
    { sceneId: "scene:tunnel-pursuit", beatId: "beat:hold-breach", order: 1 },
  ]);
  expect(index.choices).toEqual([
    {
      choiceId: "choice:surviving-brood",
      beatId: "beat:hold-breach",
      sceneId: "scene:north-gate",
      order: 0,
      optionOrder: ["option:follow-brood", "option:seal-breach"],
    },
  ]);
  expect(index.options).toEqual([
    {
      optionId: "option:follow-brood",
      choiceId: "choice:surviving-brood",
      order: 0,
      activates: ["scene:tunnel-pursuit", "beat:lower-tunnels"],
      suppresses: [],
    },
    {
      optionId: "option:seal-breach",
      choiceId: "choice:surviving-brood",
      order: 1,
      activates: [],
      suppresses: ["scene:tunnel-pursuit"],
    },
  ]);
  const options = optionListItems(imported.doc);
  expect(options.map((item) => item.attrs?.playableElementId)).toEqual([
    "option:follow-brood",
    "option:seal-breach",
  ]);
  expect(options.every((item) => item.attrs?.playableElementKind === "option")).toBe(true);
  const exported = tiptapJsonToSemanticMarkdown(imported.doc);
  const choiceProse = markdownWindow(
    exported,
    "id=choice:surviving-brood",
    "id=option:follow-brood",
  );
  expect(choiceProse).toContain("disappearing underground");
  expect(choiceProse).not.toContain("pursues the retreating");
  expect(choiceProse).not.toContain("immediate breach is contained");
  const followBody = markdownWindow(exported, "id=option:follow-brood", "id=option:seal-breach");
  expect(followBody).toContain("pursues the retreating");
  const sealBody = markdownWindow(exported, "id=option:seal-breach", "id=scene:tunnel-pursuit");
  expect(sealBody).toContain("immediate breach is contained");
}

const BLANK_BEAT_MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa beat_kind=spine -->",
  "## Untitled Beat",
  "",
].join("\n");

function pathlessRunbookRecord(overrides: Partial<WorkspaceDocumentRecord> = {}): WorkspaceDocumentRecord {
  return fixtureWorkspaceDocumentRecord({
    document_id: RUNBOOK_ID,
    title: "Blank Runbook",
    kind: "runbook",
    target_relpath: null,
    target_session: null,
    content_status: "committed",
    revision: 1,
    ...overrides,
  });
}

function snapshotFor(
  record: WorkspaceDocumentRecord,
  markdown: string,
  extra: Partial<WorkspaceDocumentSnapshot> = {},
): WorkspaceDocumentSnapshot {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1",
    record,
    markdown,
    content_sha256: CONTENT_SHA,
    file_fingerprint: "absent",
    file_exists: false,
    loaded_revision: record.revision,
    ...extra,
  };
}

function IsolatedCanvas(
  props: Omit<ComponentProps<typeof PlanSurfaceCanvas>, "onSaveStatusChange" | "onEditorToolsChange"> & {
    onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void;
  },
) {
  const [saveStatusLabel, setSaveStatusLabel] = useState("Local draft · not yet saved to Markdown");
  return (
    <>
      <span data-testid="plan-canvas-save-status">{saveStatusLabel}</span>
      <PlanSurfaceCanvas
        {...props}
        onSaveStatusChange={setSaveStatusLabel}
      />
    </>
  );
}

function durableCanvasShellProps(document: ReturnType<typeof workspaceRecordToPlanDocumentDescriptor>) {
  return {
    shellState: adoptCreatedPlanIdentity(document),
    selectorListAvailable: true,
    createController: createWorkspaceDocumentCreationController(),
  };
}

function renderIsolatedCanvas(
  document: ReturnType<typeof workspaceRecordToPlanDocumentDescriptor>,
  onEditorToolsChange?: (tools: AppChromeToolsGeneration | null) => void,
) {
  const sessionDescriptor = fixturePlanSessionDescriptor({ planningDocument: document });
  const config = createPlanSurfaceConfig(mockPlanView, document, "?campaigns=longmont-c1,longmont-c2");
  return render(
    <EditCapabilityProvider>
      <AgentInteractionProjectionTestHost config={config}>
        <PlanGraphLensProvider planCampaignId={sessionDescriptor.campaignId}>
          <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
            <IsolatedCanvas
              sessionDescriptor={sessionDescriptor}
              theme={config.theme}
              onEditorToolsChange={onEditorToolsChange}
              {...durableCanvasShellProps(document)}
            />
          </PlanGraphReferenceResolverProvider>
        </PlanGraphLensProvider>
      </AgentInteractionProjectionTestHost>
    </EditCapabilityProvider>,
  );
}

function PlanPublicationProbe() {
  const { projectionSurface, surfaceInteractionBasePublication } = useAgentInteraction();
  const workObject = surfaceInteractionBasePublication?.canvas?.workObject;
  return (
    <output
      data-testid="plan-surface-publication"
      data-agent-document-id={surfaceInteractionBasePublication?.agentContext?.documentId ?? "null"}
      data-canvas-document-id={projectionSurface?.publication.config.canvas.documentId ?? "null"}
      data-canvas-work-object={workObject ? `${workObject.kind}:${workObject.id}` : "null"}
    />
  );
}

describe("canSavePlanningDocument", () => {
  it("allows a pathless Runbook", () => {
    expect(canSavePlanningDocument({ kind: "runbook", targetRelpath: null })).toBe(true);
  });

  it("does not allow a pathless Plan", () => {
    expect(canSavePlanningDocument({ kind: "plan", targetRelpath: null })).toBe(false);
  });

  it("keeps an ordinary path-backed Plan saveable", () => {
    expect(canSavePlanningDocument({
      kind: "plan",
      targetRelpath: "corpus/eldyrwild-markdown/Longmont Campaign/Campaign 2/Session Prep/Session 23 Prep.md",
    })).toBe(true);
  });
});

describe("Breach dogfood Runbook grammar", () => {
  it("is admitted by the existing v2 indexer with Option list items", () => {
    expectCanonicalBreachDogfood(BREACH_DOGFOOD_RUNBOOK_MARKDOWN);
  });
});

describe("PlanSurfaceCanvas Runbook authoring", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "world",
      },
      summary: {
        nodeCount: 0,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    });
  });

  it("loads a pathless Runbook as interactive and saveable without fabricating a path", async () => {
    const record = pathlessRunbookRecord();
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot").mockResolvedValue(
      snapshotFor(record, BLANK_BEAT_MARKDOWN),
    );
    let editorTools: AppChromeToolsGeneration | null = null;
    renderIsolatedCanvas(
      workspaceRecordToPlanDocumentDescriptor(record),
      (tools) => { editorTools = tools; },
    );

    await waitFor(() => {
      expect(screen.getByTestId("plan-surface-canvas-editor")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-authoring-identity")).toHaveTextContent(
      "Editing Runbook · Blank Runbook",
    );
    await waitFor(() => {
      const saveAction = editorTools?.tools.sections
        ?.find((section) => section.id === "plan-markdown-save")
        ?.actions.find((action) => action.label === "Save to Markdown");
      expect(saveAction?.disabled).toBeFalsy();
    });
  });

  it("does not enable Save for a pathless Plan", async () => {
    const record = fixtureWorkspaceDocumentRecord({
      target_relpath: null,
      kind: "plan",
    });
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot").mockResolvedValue(
      snapshotFor(record, "# Plan\n"),
    );
    let editorTools: AppChromeToolsGeneration | null = null;
    renderIsolatedCanvas(
      workspaceRecordToPlanDocumentDescriptor(record),
      (tools) => { editorTools = tools; },
    );
    await waitFor(() => {
      expect(screen.getByTestId("plan-surface-canvas-editor")).toBeInTheDocument();
    });
    await waitFor(() => {
      const saveAction = editorTools?.tools.sections
        ?.find((section) => section.id === "plan-markdown-save")
        ?.actions.find((action) => action.label === "Save to Markdown");
      expect(saveAction).toBeDefined();
    });
    const saveAction = editorTools!.tools.sections!
      .find((section) => section.id === "plan-markdown-save")!
      .actions.find((action) => action.label === "Save to Markdown")!;
    expect(saveAction.disabled).toBe(true);
  });

  it("saves Decision-bearing v2 Markdown through prepare/commit on the same WorkObject", async () => {
    const record = pathlessRunbookRecord();
    const committed = pathlessRunbookRecord({ revision: 2, content_status: "committed" });
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot")
      .mockResolvedValueOnce(snapshotFor(record, BREACH_DOGFOOD_RUNBOOK_MARKDOWN))
      .mockResolvedValue(snapshotFor(committed, BREACH_DOGFOOD_RUNBOOK_MARKDOWN, {
        loaded_revision: 2,
        content_sha256: "abc123sha256",
      }));
    const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: RUNBOOK_ID,
      title: record.title,
      target_relpath: `runbook:${RUNBOOK_ID}`,
      target_display_path: `runbook:${RUNBOOK_ID}`,
      registry_revision: 1,
      file_exists: false,
      writer_ok: true,
      writer_confirm_token: "confirm-token",
      warnings: [],
      diagnostics: [],
    });
    vi.spyOn(liveApi, "commitTiptapMarkdownWrite").mockResolvedValue({
      schema_version: "dmb_tiptap_markdown_write_commit_v1",
      document_id: RUNBOOK_ID,
      title: record.title,
      target_relpath: `runbook:${RUNBOOK_ID}`,
      target_display_path: `runbook:${RUNBOOK_ID}`,
      registry_revision: 2,
      committed_revision: 2,
      committed_record: committed,
      normalized_content_sha256: "abc123sha256",
      writer_ok: true,
      diagnostics: [],
    });
    const putPlayRun = vi.spyOn(liveApi, "putPlayRun");
    const putManifest = vi.spyOn(liveApi, "putPlayRunReferenceManifest");

    let editorTools: AppChromeToolsGeneration | null = null;
    renderIsolatedCanvas(
      workspaceRecordToPlanDocumentDescriptor(record),
      (tools) => { editorTools = tools; },
    );
    await waitFor(() => {
      expect(screen.getByTestId("plan-surface-canvas-editor")).toBeInTheDocument();
    });
    await waitFor(() => {
      const saveAction = editorTools?.tools.sections
        ?.find((section) => section.id === "plan-markdown-save")
        ?.actions.find((action) => action.label === "Save to Markdown");
      expect(saveAction?.disabled).toBeFalsy();
    });
    const saveAction = editorTools!.tools.sections!
      .find((section) => section.id === "plan-markdown-save")!
      .actions.find((action) => action.label === "Save to Markdown")!;
    await act(async () => {
      saveAction.onClick();
    });

    await waitFor(() => {
      expect(prepare).toHaveBeenCalled();
    });
    const prepareBody = prepare.mock.calls[0]?.[0];
    expect(prepareBody?.document_id).toBe(RUNBOOK_ID);
    expect(prepareBody).not.toHaveProperty("target_relpath");
    expectCanonicalBreachDogfood(prepareBody?.markdown ?? "");
    expect(liveApi.commitTiptapMarkdownWrite).toHaveBeenCalledWith(expect.objectContaining({
      document_id: RUNBOOK_ID,
      writer_confirm_token: "confirm-token",
    }));
    await waitFor(() => {
      expect(screen.getByTestId("plan-markdown-save-success")).toBeInTheDocument();
    });
    expect(screen.getByTestId("plan-markdown-save-target")).toHaveTextContent("native Runbook WorkObject");
    expect(committed.target_relpath).toBeNull();
    expect(committed.kind).toBe("runbook");
    expect(committed.document_id).toBe(RUNBOOK_ID);
    expect(committed.revision).toBe(2);
    expect(putPlayRun).not.toHaveBeenCalled();
    expect(putManifest).not.toHaveBeenCalled();
  });
});

describe("Plan default selector stays Plan-only", () => {
  it("does not change the fixture Plan document identity", () => {
    const plan = fixtureWorkspaceDocumentRecord({ document_id: FIXTURE_DOC_ID, kind: "plan" });
    expect(plan.kind).toBe("plan");
    expect(canSavePlanningDocument({
      kind: "plan",
      targetRelpath: plan.target_relpath,
    })).toBe(true);
  });
});

describe("explicit Runbook documentId in Plan", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("opens the exact Runbook WorkObject while the selector still lists plans", async () => {
    window.history.pushState({}, "", `/plan?documentId=${RUNBOOK_ID}`);
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "world",
      },
      summary: {
        nodeCount: 0,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    } as Awaited<ReturnType<typeof liveApi.postWorldGraphProjection>>);
    vi.spyOn(liveApi, "getSourceBundle").mockResolvedValue(mockSourceBundle);
    const list = vi.spyOn(liveApi, "listWorkspaceDocuments").mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [fixtureWorkspaceDocumentRecord()],
    });
    vi.spyOn(liveApi, "getWorkspaceDocument").mockResolvedValue(pathlessRunbookRecord());
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot").mockResolvedValue(
      snapshotFor(pathlessRunbookRecord(), BLANK_BEAT_MARKDOWN),
    );

    function Harness() {
      const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);
      return (
        <AgentInteractionProvider>
          <PlanPublicationProbe />
          <AskPluginSlotProvider>
            <WorldGraphLensProvider planCampaignId="longmont-c2">
              <WorldGraphLensProjectionProvider defaultCampaignId="longmont-c2">
                <SurfaceContextProvider>
                  <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
                    <PlanSurfaceShell planView={mockPlanView} onEditorToolsChange={setEditorTools} />
                  </AppChrome>
                </SurfaceContextProvider>
              </WorldGraphLensProjectionProvider>
            </WorldGraphLensProvider>
          </AskPluginSlotProvider>
        </AgentInteractionProvider>
      );
    }

    render(<Harness />);
    await waitFor(() => {
      expect(screen.getByTestId("plan-authoring-identity")).toHaveTextContent(
        "Editing Runbook · Blank Runbook",
      );
    });
    await waitFor(() => {
      expect(screen.getByTestId("plan-surface-canvas-editor")).toBeInTheDocument();
    });
    expect(screen.queryByTestId("plan-canvas-authoring-error")).not.toBeInTheDocument();
    expect(liveApi.getWorkspaceDocument).toHaveBeenCalledWith(RUNBOOK_ID);
    expect(list).toHaveBeenCalledWith(expect.objectContaining({ kind: "plan" }));
    expect(screen.getByTestId("plan-surface-publication")).toHaveAttribute(
      "data-agent-document-id",
      RUNBOOK_ID,
    );
    expect(screen.getByTestId("plan-surface-publication")).toHaveAttribute(
      "data-canvas-work-object",
      `document:${RUNBOOK_ID}`,
    );
  });

  it("refuses a cross-campaign exact Runbook without publishing durable identity", async () => {
    window.history.pushState({}, "", `/plan?documentId=${RUNBOOK_ID}`);
    vi.spyOn(liveApi, "postWorldGraphProjection").mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c2",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
        scopeMode: "world",
      },
      summary: {
        nodeCount: 0,
        relationshipCount: 0,
        attributeCount: 0,
        evidenceCount: 0,
        sourceArtifactCount: 0,
        projectionTruncated: false,
      },
      nodes: [],
      relationships: [],
      attributes: [],
      evidence: [],
      sourceArtifacts: [],
      diagnostics: [],
    } as Awaited<ReturnType<typeof liveApi.postWorldGraphProjection>>);
    vi.spyOn(liveApi, "getSourceBundle").mockResolvedValue(mockSourceBundle);
    vi.spyOn(liveApi, "listWorkspaceDocuments").mockResolvedValue({
      schema_version: "dmb_workspace_document_registry_v1",
      records: [fixtureWorkspaceDocumentRecord()],
    });
    vi.spyOn(liveApi, "getWorkspaceDocument").mockResolvedValue(
      pathlessRunbookRecord({ campaign_id: "longmont-c1", title: "C1 Runbook" }),
    );
    const snapshot = vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot");

    function Harness() {
      const [editorTools, setEditorTools] = useState<AppChromeToolsGeneration | null>(null);
      return (
        <AgentInteractionProvider>
          <PlanPublicationProbe />
          <AskPluginSlotProvider>
            <WorldGraphLensProvider planCampaignId="longmont-c2">
              <WorldGraphLensProjectionProvider defaultCampaignId="longmont-c2">
                <SurfaceContextProvider>
                  <AppChrome activeRoute="plan" editorTools={editorTools} editToolboxLayout="dock">
                    <PlanSurfaceShell planView={mockPlanView} onEditorToolsChange={setEditorTools} />
                  </AppChrome>
                </SurfaceContextProvider>
              </WorldGraphLensProjectionProvider>
            </WorldGraphLensProvider>
          </AskPluginSlotProvider>
        </AgentInteractionProvider>
      );
    }

    render(<Harness />);
    await waitFor(() => {
      expect(screen.getByTestId("plan-canvas-authoring-error")).toHaveTextContent("longmont-c1");
      expect(screen.getByTestId("plan-surface-publication")).toHaveAttribute(
        "data-canvas-work-object",
        `plan-shell:error:longmont-c2:${RUNBOOK_ID}`,
      );
    });
    expect(screen.getByTestId("plan-canvas-authoring-error")).toHaveTextContent("longmont-c2");
    expect(screen.queryByTestId("plan-authoring-identity")).not.toBeInTheDocument();
    expect(screen.queryByTestId("plan-surface-canvas-editor")).not.toBeInTheDocument();
    const publication = screen.getByTestId("plan-surface-publication");
    expect(publication).toHaveAttribute("data-agent-document-id", "null");
    expect(publication).toHaveAttribute("data-canvas-document-id", "null");
    expect(screen.getByRole("button", { name: "Close Edit" })).toBeInTheDocument();
    expect(screen.getByRole("complementary", { name: "Edit toolbar" })).toBeInTheDocument();
    expect(snapshot).not.toHaveBeenCalled();
  });
});
