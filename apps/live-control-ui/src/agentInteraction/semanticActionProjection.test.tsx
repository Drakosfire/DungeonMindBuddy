import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider, useAgentInteraction } from "./AgentInteractionProvider";
import * as liveApi from "../api/liveApi";
import type { WorldGraphProjection } from "../api/types";
import { BUILD_DOCUMENT_SAVE_CONFLICTS_WITH } from "../buildSurface/buildDocumentCommands";
import { BUILD_MARKDOWN_CANVAS } from "../buildSurface/buildMarkdownCanvasAdapter";
import { BuildReferenceCapability } from "../buildSurface/reference/BuildReferenceCapability";
import {
  BUILD_FIND_EXISTING_TOOL_ID,
  BUILD_REFERENCE_SEARCH_PROJECTION_ID,
} from "../buildSurface/reference/buildReferenceIds";
import { LegacyProjectionHostAdapter } from "../planSurface/projection/LegacyProjectionHostAdapter";
import { MarkdownCanvasSessionProvider } from "../markdownCanvas/MarkdownCanvasSession";
import { ToolHost } from "../surfaceInteraction/toolHost/ToolHost";
import type { SurfaceInteractionPublication } from "../surfaceInteraction/types";
import { buildBuildSurfaceIdentity } from "./projectionSurfacePublication";
import {
  activateBuildSemanticAction,
  describeBuildSemanticAction,
} from "./semanticActionProjection";

const DOC_A = "11111111-1111-4111-8111-111111111111";
const DOC_B = "22222222-2222-4222-8222-222222222222";

vi.mock("../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    postWorldGraphProjection: vi.fn(),
  };
});

function snapshotFixture(documentId: string) {
  return {
    schema_version: "dmb_workspace_document_snapshot_v1" as const,
    record: {
      schema_version: "dmb_workspace_document_record_v1" as const,
      document_id: documentId,
      title: "Faction Notes",
      campaign_id: "longmont-c1",
      target_session: null,
      kind: "worldbuilding_source" as const,
      target_relpath: `out/workspace/worldbuilding/${documentId}.md`,
      status: "active" as const,
      content_status: "draft" as const,
      revision: 1,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
      source_domain: "worldbuilding" as const,
      document_class: "faction" as const,
      authority_state: "draft" as const,
      visibility_state: "internal" as const,
    },
    markdown: "",
    content_sha256: "sha-empty",
    file_fingerprint: "absent" as const,
    file_exists: false,
    loaded_revision: 1,
  };
}

function graphProjectionFixture(): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c1",
      revisionId: "rev-1",
      headRevisionId: "rev-1",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
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
  };
}

type InteractionState = ReturnType<typeof useAgentInteraction>;

function InteractionProbe({ capture }: { capture: (state: InteractionState) => void }) {
  capture(useAgentInteraction());
  return null;
}

function withDocument(
  publication: SurfaceInteractionPublication,
  documentId: string,
): SurfaceInteractionPublication {
  return {
    ...publication,
    identity: buildBuildSurfaceIdentity({ documentId }),
    canvas: publication.canvas
      ? { ...publication.canvas, workObject: { kind: "document", id: documentId } }
      : null,
  };
}

describe("Build semantic action projection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    window.history.replaceState({}, "", `/build?documentId=${DOC_A}&campaign=longmont-c1`);
  });

  it("uses the current publication for the UI and Agent action and rejects stale lease, selection, disabled, and removed states", async () => {
    const user = userEvent.setup();
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture(DOC_A));
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue(graphProjectionFixture());

    let current: InteractionState | null = null;
    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_A}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_DOCUMENT_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_A} />
        </MarkdownCanvasSessionProvider>
        <ToolHost />
        <LegacyProjectionHostAdapter />
        <InteractionProbe capture={(state) => { current = state; }} />
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(current?.surfaceInteractionPublication?.tools.map((tool) => tool.id))
        .toContain(BUILD_FIND_EXISTING_TOOL_ID);
    });

    const publication = current?.surfaceInteractionPublication;
    if (!publication) throw new Error("Build publication did not become available");
    const descriptor = describeBuildSemanticAction(publication);
    expect(descriptor).not.toBeNull();
    if (!descriptor) throw new Error("Build action descriptor was not produced");

    expect(descriptor.id).toBe(BUILD_FIND_EXISTING_TOOL_ID);
    expect(descriptor.target).toEqual({ kind: "document", id: DOC_A });
    expect(descriptor.effect).toEqual({
      kind: "open-projection",
      projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
    });
    expect(descriptor.availability).toEqual({ status: "enabled" });
    expect(Object.keys(descriptor).sort()).toEqual([
      "availability",
      "effect",
      "id",
      "label",
      "surfaceIdentity",
      "target",
    ]);
    expect(JSON.stringify(descriptor)).not.toContain("projectionBindings");
    expect(JSON.stringify(descriptor)).not.toContain("invoke");

    const openProjection = vi.fn(() => true);
    const disabledPublication: SurfaceInteractionPublication = {
      ...publication,
      tools: publication.tools.map((tool) => tool.id === BUILD_FIND_EXISTING_TOOL_ID
        ? { ...tool, availability: { status: "disabled", disabledReason: "Graph lens is invalid." } }
        : tool),
    };
    const disabledDescriptor = describeBuildSemanticAction(disabledPublication);
    expect(disabledDescriptor?.availability).toEqual({
      status: "disabled",
      disabledReason: "Graph lens is invalid.",
    });
    const disabledResult = await activateBuildSemanticAction(
      disabledDescriptor!,
      disabledPublication,
      openProjection,
    );
    expect(disabledResult).toEqual({ status: "ignored", reason: "disabled" });
    expect(openProjection).not.toHaveBeenCalled();

    const declinedOpen = vi.fn(() => false);
    expect(await activateBuildSemanticAction(descriptor, publication, declinedOpen))
      .toEqual({ status: "ignored", reason: "unsupported" });
    expect(declinedOpen).toHaveBeenCalledWith(BUILD_FIND_EXISTING_TOOL_ID);

    const removedPublication = { ...publication, tools: [] };
    expect(describeBuildSemanticAction(removedPublication)).toBeNull();
    expect(await activateBuildSemanticAction(descriptor, removedPublication, openProjection))
      .toEqual({ status: "ignored", reason: "stale" });

    const nextLeasePublication = { ...publication };
    expect(nextLeasePublication.identity).toEqual(publication.identity);
    expect(nextLeasePublication.canvas?.workObject).toEqual(publication.canvas?.workObject);
    expect(await activateBuildSemanticAction(descriptor, nextLeasePublication, openProjection))
      .toEqual({ status: "ignored", reason: "stale" });

    const selectedOtherDocument = withDocument(publication, DOC_B);
    const otherDocumentDescriptor = describeBuildSemanticAction(selectedOtherDocument);
    expect(otherDocumentDescriptor?.target).toEqual({ kind: "document", id: DOC_B });
    expect(await activateBuildSemanticAction(descriptor, selectedOtherDocument, openProjection))
      .toEqual({ status: "ignored", reason: "stale" });
    expect(openProjection).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Tools" }));
    await user.click(screen.getByRole("button", { name: /Find existing object/ }));
    await waitFor(() => {
      expect(screen.getByTestId("build-reference-search-projection")).toBeInTheDocument();
    });
    expect(document.querySelector(".surface-projection-host"))
      .toHaveAttribute("data-projection-key", BUILD_REFERENCE_SEARCH_PROJECTION_ID);

    await act(async () => {
      current?.close();
    });
    await waitFor(() => {
      expect(screen.queryByTestId("build-reference-search-projection")).not.toBeInTheDocument();
    });

    const liveState = current;
    const livePublication = liveState?.surfaceInteractionPublication;
    if (!livePublication) throw new Error("Current Build publication was withdrawn");
    const agentDescriptor = describeBuildSemanticAction(livePublication);
    if (!agentDescriptor) throw new Error("Current Build action descriptor was withdrawn");

    let agentSelectedId: string | null = null;
    let agentResult: Awaited<ReturnType<typeof activateBuildSemanticAction>>;
    await act(async () => {
      agentResult = await activateBuildSemanticAction(
        agentDescriptor,
        livePublication,
        (toolId) => {
          agentSelectedId = toolId;
          return liveState.activateProjectionTool(toolId);
        },
      );
    });
    expect(agentSelectedId).toBe(BUILD_FIND_EXISTING_TOOL_ID);
    expect(agentResult!).toEqual({
      status: "opened",
      mode: "projection",
      projectionId: BUILD_REFERENCE_SEARCH_PROJECTION_ID,
    });
    await waitFor(() => {
      expect(screen.getByTestId("build-reference-search-projection")).toBeInTheDocument();
    });
  });
});
