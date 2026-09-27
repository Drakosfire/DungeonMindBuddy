import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { webcrypto } from "node:crypto";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../selectedWorld/SelectedWorldContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../selectedWorld/SelectedWorldContext")>();
  return {
    ...actual,
    useSelectedWorld: () => ({
      kind: "managed" as const,
      worldId: "longmont-c2",
      name: "Test World",
      documentId: null,
    }),
  };
});

import * as liveApi from "../api/liveApi";
import type { WorkspaceDocumentSnapshot } from "../api/types";
import type { AppChromeToolsGeneration } from "../chrome/AppChrome";
import { mockPlanView } from "../test/fixtures";
import { readWorkspaceDocumentLocalState } from "../tiptap/state/tiptapLocalState";
import { AgentInteractionProjectionTestHost } from "./projection/projectionTestHost";
import { fixturePlanSessionDescriptor, fixtureWorkspaceDocumentRecord } from "./config/planSessionDescriptor";
import { createPlanSurfaceConfig } from "./config/planSurfaceConfig";
import { EditCapabilityProvider, useEditCapability } from "./edit/editCapability";
import { PlanGraphLensProvider } from "./PlanGraphLensContext";
import { PlanGraphReferenceResolverProvider } from "./reference/usePlanGraphReferenceResolver";
import { PlanSurfaceCanvas } from "./components/PlanSurfaceCanvas";
import { adoptCreatedPlanIdentity } from "./planBlankAuthoringState";
import { createWorkspaceDocumentCreationController } from "../workspaceDocument/workspaceDocumentCreation";
import { admitPlanEditProposal, type PlanEditBridge } from "./agentEdit/planAgentEditProposal";

const record = fixtureWorkspaceDocumentRecord();
const sourceMarkdown = "# Opening\n\nOpening frame\n";
const originalSha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";
const savedSha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";
const sessionDescriptor = fixturePlanSessionDescriptor();
const config = createPlanSurfaceConfig(mockPlanView, sessionDescriptor.planningDocument, "");

function UnlockEditor() {
  const { toggleLock } = useEditCapability();
  return <button type="button" onClick={toggleLock}>Unlock test editor</button>;
}

function MountedPlan({
  onBridge,
  onTools,
}: {
  onBridge: (bridge: PlanEditBridge | null) => void;
  onTools: (tools: AppChromeToolsGeneration | null) => void;
}) {
  const [status, setStatus] = useState("");
  return (
    <EditCapabilityProvider>
      <AgentInteractionProjectionTestHost config={config}>
        <PlanGraphLensProvider planCampaignId={sessionDescriptor.campaignId}>
          <PlanGraphReferenceResolverProvider sessionDescriptor={sessionDescriptor}>
            <UnlockEditor />
            <output data-testid="save-status">{status}</output>
            <PlanSurfaceCanvas
              sessionDescriptor={sessionDescriptor}
              theme={config.theme}
              shellState={adoptCreatedPlanIdentity(sessionDescriptor.planningDocument)}
              selectorListAvailable
              createController={createWorkspaceDocumentCreationController()}
              onSaveStatusChange={setStatus}
              onAgentEditBridgeChange={onBridge}
              onEditorToolsChange={onTools}
            />
          </PlanGraphReferenceResolverProvider>
        </PlanGraphLensProvider>
      </AgentInteractionProjectionTestHost>
    </EditCapabilityProvider>
  );
}

describe("mounted Plan reviewed edit integration", () => {
  beforeEach(() => {
    Object.defineProperty(globalThis, "crypto", { configurable: true, value: webcrypto });
    vi.restoreAllMocks();
    localStorage.clear();
  });

  it("applies a prose + two-component proposal locally, then saves and reloads the exact Plan", async () => {
    let storedMarkdown = sourceMarkdown;
    let committed = false;
    const snapshot = (): WorkspaceDocumentSnapshot => ({
      schema_version: "dmb_workspace_document_snapshot_v1",
      record: committed ? { ...record, revision: record.revision + 1, content_status: "committed" } : record,
      markdown: storedMarkdown,
      content_sha256: committed ? savedSha : originalSha,
      file_fingerprint: committed ? "file-fp-2" : "file-fp-1",
      file_exists: true,
      loaded_revision: committed ? record.revision + 1 : record.revision,
    });
    vi.spyOn(liveApi, "getWorkspaceDocumentSnapshot").mockImplementation(async () => snapshot());
    const prepare = vi.spyOn(liveApi, "prepareTiptapMarkdownWrite").mockImplementation(async () => ({
      schema_version: "dmb_tiptap_markdown_write_prepare_v1",
      document_id: record.document_id,
      title: record.title,
      target_relpath: record.target_relpath,
      target_display_path: record.target_relpath,
      file_exists: true,
      writer_ok: true,
      writer_phase: "prepare",
      writer_confirm_token: "confirm-token",
      writer_diff: "+Agent edit",
      warnings: [],
      diagnostics: [],
    } as never));
    const commit = vi.spyOn(liveApi, "commitTiptapMarkdownWrite").mockImplementation(async (request) => {
      storedMarkdown = request.markdown;
      committed = true;
      return {
        schema_version: "dmb_tiptap_markdown_write_commit_v1",
        document_id: record.document_id,
        title: record.title,
        target_relpath: record.target_relpath,
        target_display_path: record.target_relpath,
        registry_revision: record.revision + 1,
        committed_revision: record.revision + 1,
        committed_record: snapshot().record,
        normalized_content_sha256: savedSha,
        writer_ok: true,
        writer_phase: "commit",
        bytes_written: storedMarkdown.length,
        file_fingerprint: "file-fp-2",
        diagnostics: [],
      } as never;
    });
    vi.spyOn(liveApi, "postWorldGraphProjection").mockRejectedValue(new Error("No graph head needed for editor test"));

    let bridge: PlanEditBridge | null = null;
    let tools: AppChromeToolsGeneration | null = null;
    const callbacks = {
      onBridge: (next: PlanEditBridge | null) => { bridge = next; },
      onTools: (next: AppChromeToolsGeneration | null) => { tools = next; },
    };
    const mounted = render(<MountedPlan {...callbacks} />);
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByTestId("plan-surface-canvas-editor")).toHaveAttribute("data-markdown-editor-status", "ready"));
    await user.click(screen.getByRole("button", { name: "Unlock test editor" }));
    await waitFor(() => expect(bridge).not.toBeNull());
    const captured = await bridge!.capture();
    const markdown = [
      "The children gather at the waystation.",
      "",
      "> [!READ-ALOUD]",
      "> Stacy waits beside the gate.",
      "",
      "> [!DECISION-CONSEQUENCE]",
      "> ### Decision",
      "> Invite the children inside.",
      ">",
      "> ### Consequence",
      "> Stacy remembers the kindness.",
    ].join("\n");
    const admitted = await admitPlanEditProposal(captured, {
      schema_version: "dmb_plan_document_edit_proposal_v1",
      document_id: captured.request.document_id,
      world_id: captured.request.world_id,
      session: captured.request.session,
      base_revision: captured.request.base_revision,
      base_content_sha256: captured.request.base_content_sha256,
      draft_sha256: captured.request.draft_sha256,
      target_kind: captured.request.target_kind,
      selected_text_sha256: originalSha,
      replacement_markdown: markdown,
      summary: "Opening with choices",
      assumptions: [],
      model: "test-model",
      model_observed: true,
      model_latency_ms: 1,
      wall_latency_ms: 1,
      usage: null,
    });
    await act(async () => { await bridge!.apply(captured, admitted); });
    expect(prepare).not.toHaveBeenCalled();
    const local = readWorkspaceDocumentLocalState(localStorage, record.document_id, "plan");
    expect(local?.dirty).toBe(true);
    expect(local?.exported_markdown).toContain("Stacy remembers the kindness.");
    await act(async () => { captured.editor.commands.undo(); });
    expect(screen.getByTestId("plan-surface-canvas-editor")).not.toHaveTextContent("Stacy remembers the kindness.");
    await act(async () => { captured.editor.commands.redo(); });
    expect(screen.getByTestId("plan-surface-canvas-editor")).toHaveTextContent("Stacy remembers the kindness.");

    await waitFor(() => expect(tools?.tools.sections.flatMap((section) => section.actions)
      .find((action) => action.id === "plan-save-markdown")?.disabled).toBe(false));
    const save = tools!.tools.sections.flatMap((section) => section.actions)
      .find((action) => action.id === "plan-save-markdown");
    await act(async () => { save?.onClick?.(); });
    await waitFor(() => expect(commit).toHaveBeenCalledTimes(1));
    expect(prepare.mock.calls[0][0].markdown).toContain("[!READ-ALOUD]");
    expect(prepare.mock.calls[0][0].markdown).toContain("[!DECISION-CONSEQUENCE]");
    await waitFor(() => expect(screen.getByTestId("save-status")).toHaveTextContent(/Committed/i));

    mounted.unmount();
    bridge = null;
    render(<MountedPlan {...callbacks} />);
    await waitFor(() => expect(screen.getByTestId("plan-surface-canvas-editor")).toHaveTextContent("Stacy remembers the kindness."));
    expect(commit).toHaveBeenCalledTimes(1);
  });
});
