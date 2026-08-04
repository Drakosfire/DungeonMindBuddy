import { render, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AgentInteractionProvider, useAgentInteraction } from "../../agentInteraction/AgentInteractionProvider";
import * as liveApi from "../../api/liveApi";
import { MarkdownCanvasSessionProvider } from "../../markdownCanvas/MarkdownCanvasSession";
import { BUILD_MARKDOWN_CANVAS } from "../buildMarkdownCanvasAdapter";
import { BUILD_SAVE_CONFLICTS_WITH } from "../buildDocumentCommands";
import { BUILD_FIND_EXISTING_TOOL_ID } from "./buildReferenceIds";
import { BuildReferenceCapability } from "./BuildReferenceCapability";

const DOC_ID = "11111111-1111-4111-8111-111111111111";

function PublicationProbe() {
  const { surfaceInteractionPublication } = useAgentInteraction();
  const toolIds = surfaceInteractionPublication?.tools.map((tool) => tool.id) ?? [];
  return (
    <p data-testid="build-publication-tools">{toolIds.length ? toolIds.join(",") : "none"}</p>
  );
}

vi.mock("../../api/liveApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../api/liveApi")>();
  return {
    ...actual,
    getWorkspaceDocumentSnapshot: vi.fn(),
    postWorldGraphProjection: vi.fn(),
    prepareTiptapMarkdownWrite: vi.fn(),
    commitTiptapMarkdownWrite: vi.fn(),
  };
});

function snapshotFixture(documentId: string = DOC_ID) {
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

describe("BuildReferenceCapability", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("publishes empty tools without a markdown canvas session", () => {
    render(
      <AgentInteractionProvider>
        <BuildReferenceCapability documentId={null} />
        <PublicationProbe />
      </AgentInteractionProvider>,
    );

    expect(document.querySelector('[data-testid="build-publication-tools"]')).toHaveTextContent("none");
  });

  it("publishes Find existing tool when session is accepted", async () => {
    vi.mocked(liveApi.getWorkspaceDocumentSnapshot).mockResolvedValue(snapshotFixture());
    vi.mocked(liveApi.postWorldGraphProjection).mockResolvedValue({
      schema: "dmb_world_graph_projection_v1",
      snapshot: {
        worldId: "eldyrwild",
        campaignId: "longmont-c1",
        revisionId: "rev-1",
        headRevisionId: "rev-1",
        isHead: true,
        focus: { kind: "none", sessionId: null },
        admissibility: "gm",
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

    render(
      <AgentInteractionProvider>
        <MarkdownCanvasSessionProvider
          documentId={DOC_ID}
          surface={BUILD_MARKDOWN_CANVAS.surface}
          kind={BUILD_MARKDOWN_CANVAS.kind}
          saveConflictsWith={BUILD_SAVE_CONFLICTS_WITH}
        >
          <BuildReferenceCapability documentId={DOC_ID} />
          <PublicationProbe />
        </MarkdownCanvasSessionProvider>
      </AgentInteractionProvider>,
    );

    await waitFor(() => {
      expect(document.querySelector('[data-testid="build-publication-tools"]')).toHaveTextContent(
        BUILD_FIND_EXISTING_TOOL_ID,
      );
    });
  });
});
