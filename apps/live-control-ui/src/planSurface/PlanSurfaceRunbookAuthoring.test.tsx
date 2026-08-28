import { act, render, screen, waitFor } from "@testing-library/react";
import { useState, type ComponentProps } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AppChrome, type AppChromeToolsGeneration } from "../chrome/AppChrome";
import { AgentInteractionProvider } from "../agentInteraction/AgentInteractionProvider";
import { AskPluginSlotProvider } from "../agentInteraction/AskPluginSlot";
import { SurfaceContextProvider } from "../surfaceInteraction/contextHost";
import { WorldGraphLensProjectionProvider, WorldGraphLensProvider } from "../graphLens";
import { mockPlanView, mockSourceBundle } from "../test/fixtures";
import type { WorkspaceDocumentRecord, WorkspaceDocumentSnapshot } from "../api/types";
import * as liveApi from "../api/liveApi";
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
import { PlanGraphLensProvider } from "./PlanGraphLensContext";
import { PlanGraphReferenceResolverProvider } from "./reference/usePlanGraphReferenceResolver";
import { PlanSurfaceCanvas, canSavePlanningDocument } from "./components/PlanSurfaceCanvas";
import { PlanSurfaceShell } from "./PlanSurfaceShell";

const RUNBOOK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddddd";
const CONTENT_SHA = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

/** Canonical v2 paste used for BF4A/BF3B dogfood. Validated against BF1 indexer. */
export const BF3B_DOGFOOD_RUNBOOK_MARKDOWN = [
  "<!-- dmb-playable-element:v2 kind=beat id=beat:hold-the-breach beat_kind=spine -->",
  "## Hold the Breach",
  "",
  "Creatures have broken through the town's defensive wall. The party must decide whether to pursue the survivors or secure the breach before more can get through.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:north-gate -->",
  "### North Gate",
  "",
  "The north gate is splintered and partly collapsed. A handful of creatures are retreating into the damaged tunnels while defenders struggle to brace the wall.",
  "",
  "<!-- dmb-playable-element:v2 kind=choice id=choice:surviving-brood scene=scene:north-gate -->",
  "### What do they do with the surviving brood?",
  "",
  "The survivors are escaping below while the defenders try to stabilize the breach.",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:follow-it activates=scene:tunnel-pursuit,beat:lower-tunnels -->",
  "- Follow it",
  "",
  "  Pursue the retreating creatures into the lower tunnels before reinforcements arrive.",
  "",
  "<!-- dmb-playable-element:v2 kind=option id=option:seal-the-breach suppresses=scene:tunnel-pursuit -->",
  "- Seal the breach",
  "",
  "  Contain the immediate breach, but leave the surviving creatures somewhere below.",
  "",
  "<!-- dmb-playable-element:v2 kind=scene id=scene:tunnel-pursuit -->",
  "### Tunnel Pursuit",
  "",
  "The party enters the damaged tunnel after the fleeing creatures, following them beneath the fortifications before the trail disappears.",
  "",
  "<!-- dmb-playable-element:v2 kind=beat id=beat:lower-tunnels beat_kind=optional -->",
  "## Lower Tunnels",
  "",
  "Following the threat deeper underground opens a new phase of the defense below the town.",
  "",
].join("\n");

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
            />
          </PlanGraphReferenceResolverProvider>
        </PlanGraphLensProvider>
      </AgentInteractionProjectionTestHost>
    </EditCapabilityProvider>,
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

describe("BF3B dogfood Runbook grammar", () => {
  it("is admitted by the existing v2 indexer", () => {
    const imported = markdownToTiptapDoc(BF3B_DOGFOOD_RUNBOOK_MARKDOWN);
    expect(imported.diagnostics).toEqual([]);
    const indexed = indexPlayableStructureV2(imported.doc);
    expect(indexed.status).toBe("ready");
    if (indexed.status !== "ready") return;
    expect(indexed.index.beatOrder).toEqual(["beat:hold-the-breach", "beat:lower-tunnels"]);
    expect(indexed.index.choices.map((choice) => choice.choiceId)).toEqual(["choice:surviving-brood"]);
    expect(indexed.index.options.map((option) => option.optionId)).toEqual([
      "option:follow-it",
      "option:seal-the-breach",
    ]);
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
      .mockResolvedValueOnce(snapshotFor(record, BF3B_DOGFOOD_RUNBOOK_MARKDOWN))
      .mockResolvedValue(snapshotFor(committed, BF3B_DOGFOOD_RUNBOOK_MARKDOWN, {
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
    const imported = markdownToTiptapDoc(prepareBody?.markdown ?? "");
    expect(imported.diagnostics).toEqual([]);
    const indexed = indexPlayableStructureV2(imported.doc);
    expect(indexed.status).toBe("ready");
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
  });
});
