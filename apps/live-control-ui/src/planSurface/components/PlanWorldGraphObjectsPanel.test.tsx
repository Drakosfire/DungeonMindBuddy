import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, type ComponentProps } from "vitest";

import type { WorldGraphProjection } from "../../api/types";
import { WorldGraphLensInformationChannelProvider } from "../../graphLens/useWorldGraphLensProjection";
import { createSurfaceInformationChannel } from "../../surfaceInformation";
import { worldGraphLensInformationDescriptor } from "../../graphLens/worldGraphLensSurfaceInformation";
import type { GraphReferenceSearchItem } from "../../graphReference/types";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";
import { insertPlanGraphReferenceIfLive } from "./PlanSurfaceCanvas";
import { PlanWorldGraphObjectsPanel } from "./PlanWorldGraphObjectsPanel";

const openGraphReference = vi.fn();
const retainedSearch = vi.hoisted(() => ({
  onView: undefined as ((item: GraphReferenceSearchItem) => void) | undefined,
  onInsert: undefined as ((item: GraphReferenceSearchItem) => void) | undefined,
  items: [] as readonly GraphReferenceSearchItem[],
}));

vi.mock("../../agentInteraction/AgentInteractionProvider", () => ({
  useOptionalAgentInteraction: () => ({ openGraphReference }),
}));

vi.mock("../../graphReference/GraphReferenceSearch", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../../graphReference/GraphReferenceSearch")>();
  return {
    ...actual,
    GraphReferenceSearch: (props: ComponentProps<typeof actual.GraphReferenceSearch>) => {
      retainedSearch.onView = props.onView;
      retainedSearch.onInsert = props.onInsert;
      retainedSearch.items = props.items;
      return actual.GraphReferenceSearch(props);
    },
  };
});

const request = {
  schema: "dmb_world_graph_projection_request_v1" as const,
  worldId: "eldyrwild",
  campaignId: "longmont-c2",
  scopeMode: "campaign" as const,
  focus: { kind: "none" as const, sessionId: null },
  admissibility: "gm" as const,
};

const glowkindleNode = {
  nodeId: "npc:glowkindle",
  label: "Glowkindle",
  kind: "npc",
  role: "merchant",
  aliases: ["Glow"],
  sourceDomains: ["recap"],
  evidenceBadges: [],
  adjacency: [],
  suggestedExpansions: [],
  anchoredToFocusSession: true,
  summary: "A friendly merchant.",
  campaignScope: "longmont-c2",
  evidenceRefIds: [],
  sourceArtifactIds: [],
};

function projection(
  overrides: Partial<WorldGraphProjection> = {},
  snapshotOverrides: Partial<WorldGraphProjection["snapshot"]> = {},
): WorldGraphProjection {
  return {
    schema: "dmb_world_graph_projection_v1",
    snapshot: {
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      revisionId: "rev:abc",
      headRevisionId: "rev:abc",
      isHead: true,
      focus: { kind: "none", sessionId: null },
      admissibility: "gm",
      scopeMode: "campaign",
      ...snapshotOverrides,
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
    ...overrides,
  };
}

const observed = {
  revision: { kind: "exact" as const, value: "rev:abc" },
  provenance: [{ kind: "world_graph_revision" as const, id: "rev:abc" }],
  inspectionTargets: [
    { kind: "world" as const, id: "eldyrwild" },
    { kind: "campaign" as const, id: "longmont-c2" },
    { kind: "world_graph_revision" as const, id: "rev:abc" },
  ],
  diagnostics: [] as const,
};

function renderPanel(
  channel: ReturnType<typeof createSurfaceInformationChannel<WorldGraphProjection>> | null,
  onInsertReference = vi.fn(),
  insertEnabled = true,
  isInsertCurrentlyEnabled?: () => boolean,
) {
  return render(
    <WorldGraphLensInformationChannelProvider channel={channel}>
      <PlanWorldGraphObjectsPanel
        insertEnabled={insertEnabled}
        isInsertCurrentlyEnabled={isInsertCurrentlyEnabled}
        onInsertReference={onInsertReference}
      />
    </WorldGraphLensInformationChannelProvider>,
  );
}

describe("PlanWorldGraphObjectsPanel", () => {
  it("reports no exact channel without implying an empty projection", () => {
    renderPanel(null);
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toHaveAttribute(
      "data-status",
      "no-request",
    );
    expect(screen.getByText(/No active World Graph lens request/)).toBeInTheDocument();
    expect(screen.queryByText("No nodes in the current projection.")).not.toBeInTheDocument();
  });

  it("maps LOADING, READY, EMPTY, UNAVAILABLE, and INTEGRITY_ERROR without using the channel as props", async () => {
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    renderPanel(channel);
    expect(screen.getByText("Loading World Graph projection…")).toBeInTheDocument();

    const readyTicket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(readyTicket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    expect(screen.getByText("Glowkindle")).toBeInTheDocument();
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toHaveAttribute(
      "data-status",
      "ready",
    );

    let emptyTicket: ReturnType<typeof channel.beginObservation> = null;
    act(() => {
      emptyTicket = channel.beginObservation();
    });
    act(() => {
      channel.commit(emptyTicket!, { status: "empty", ...observed });
    });
    expect(screen.getByText("No nodes in the current projection.")).toBeInTheDocument();
    expect(screen.queryByText("World Graph unavailable for this session.")).not.toBeInTheDocument();

    let unavailableTicket: ReturnType<typeof channel.beginObservation> = null;
    act(() => {
      unavailableTicket = channel.beginObservation();
    });
    act(() => {
      channel.commit(unavailableTicket!, {
        status: "unavailable",
        reason: "authority down",
        diagnostics: [],
      });
    });
    expect(screen.getByText("World Graph unavailable for this session.")).toBeInTheDocument();
    expect(screen.queryByText("Glowkindle")).not.toBeInTheDocument();

    let integrityTicket: ReturnType<typeof channel.beginObservation> = null;
    act(() => {
      integrityTicket = channel.beginObservation();
    });
    act(() => {
      channel.commit(integrityTicket!, {
        status: "integrity_error",
        reason: "campaign mismatch",
        diagnostics: [],
      });
    });
    expect(screen.getByRole("alert")).toHaveTextContent(/campaign mismatch/);
    expect(screen.queryByText("No nodes in the current projection.")).not.toBeInTheDocument();
  });

  it("Views the exact selected node and scope from the displayed READY snapshot", async () => {
    openGraphReference.mockReset();
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    const user = userEvent.setup();
    renderPanel(channel);
    const ticket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(ticket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    await user.click(screen.getByRole("button", { name: "View" }));
    expect(openGraphReference).toHaveBeenCalledTimes(1);
    const args = openGraphReference.mock.calls[0][0];
    expect(args.resolution.kind).toBe("resolved_graph");
    expect(args.resolution.graphNodeId).toBe("npc:glowkindle");
    expect(args.resolution.graphScope).toEqual({
      worldId: "eldyrwild",
      campaignId: "longmont-c2",
      scopeMode: "campaign",
      revisionId: "rev:abc",
    });
  });

  it("inserts the exact graph-native reference when READY and insert is enabled", async () => {
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    const onInsertReference = vi.fn();
    const user = userEvent.setup();
    renderPanel(channel, onInsertReference, true);
    const ticket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(ticket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    await user.click(screen.getByRole("button", { name: "Insert chip" }));
    expect(onInsertReference).toHaveBeenCalledWith(
      expect.objectContaining({
        refType: "graph-node",
        refId: "npc:glowkindle",
        label: "Glowkindle",
      } satisfies Partial<RunbookReferenceAttrs>),
    );
  });

  it("fails closed on insert for STALE information", async () => {
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    const onInsertReference = vi.fn();
    const user = userEvent.setup();
    renderPanel(channel, onInsertReference, true);
    const ticket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(ticket!, {
        status: "stale",
        value: projection({ nodes: [glowkindleNode] }),
        reason: "refreshing",
        ...observed,
      });
    });
    expect(screen.getByText(/World Graph information is stale/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Insert chip" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Insert chip" }));
    expect(onInsertReference).not.toHaveBeenCalled();
  });

  it("keeps the connected panel mounted across a same-channel refresh", () => {
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    renderPanel(channel);
    const panel = screen.getByTestId("plan-world-graph-objects-panel");
    const readyTicket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(readyTicket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toBe(panel);
    act(() => {
    act(() => {
      channel.beginObservation();
    });
    });
    expect(screen.getByTestId("plan-world-graph-objects-panel")).toBe(panel);
    expect(screen.getByText("Loading World Graph projection…")).toBeInTheDocument();
  });

  it("fails closed when a retained View callback runs after the live observation leaves READY/STALE", () => {
    openGraphReference.mockReset();
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    renderPanel(channel);
    const ticket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(ticket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    const retainedView = retainedSearch.onView;
    const retainedItem = retainedSearch.items[0];
    expect(retainedView).toEqual(expect.any(Function));
    expect(retainedItem?.nodeId).toBe("npc:glowkindle");

    act(() => {
      channel.beginObservation();
    });
    retainedView!(retainedItem!);
    expect(openGraphReference).not.toHaveBeenCalled();

    let unavailableTicket: ReturnType<typeof channel.beginObservation> = null;
    act(() => {
      unavailableTicket = channel.beginObservation();
    });
    act(() => {
      channel.commit(unavailableTicket!, {
        status: "unavailable",
        reason: "authority down",
        diagnostics: [],
      });
    });
    retainedView!(retainedItem!);
    expect(openGraphReference).not.toHaveBeenCalled();

    let integrityTicket: ReturnType<typeof channel.beginObservation> = null;
    act(() => {
      integrityTicket = channel.beginObservation();
    });
    act(() => {
      channel.commit(integrityTicket!, {
        status: "integrity_error",
        reason: "campaign mismatch",
        diagnostics: [],
      });
    });
    retainedView!(retainedItem!);
    expect(openGraphReference).not.toHaveBeenCalled();
  });

  it("Views against the current observation, not the snapshot captured when the handler was rendered", () => {
    openGraphReference.mockReset();
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    renderPanel(channel);
    const firstTicket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(firstTicket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    const retainedView = retainedSearch.onView!;
    const retainedItem = retainedSearch.items[0]!;

    const laterObserved = {
      revision: { kind: "exact" as const, value: "rev:later" },
      provenance: [{ kind: "world_graph_revision" as const, id: "rev:later" }],
      inspectionTargets: [
        { kind: "world" as const, id: "eldyrwild" },
        { kind: "campaign" as const, id: "longmont-c2" },
        { kind: "world_graph_revision" as const, id: "rev:later" },
      ],
      diagnostics: [] as const,
    };
    const laterTicket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(laterTicket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }, { revisionId: "rev:later", headRevisionId: "rev:later" }),
        ...laterObserved,
      });
    });
    retainedView(retainedItem);
    expect(openGraphReference).toHaveBeenCalledTimes(1);
    expect(openGraphReference.mock.calls[0][0].resolution.graphScope.revisionId).toBe("rev:later");
  });

  it("fails closed when a retained callback's node is absent from the current READY observation", () => {
    openGraphReference.mockReset();
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    const onInsertReference = vi.fn();
    renderPanel(channel, onInsertReference, true);
    const ticket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(ticket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    const retainedView = retainedSearch.onView!;
    const retainedInsert = retainedSearch.onInsert!;
    const retainedItem = retainedSearch.items[0]!;

    const replacementTicket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(replacementTicket!, {
        status: "ready",
        value: projection({
          nodes: [{ ...glowkindleNode, nodeId: "npc:other", label: "Other" }],
        }),
        ...observed,
      });
    });
    retainedView(retainedItem);
    retainedInsert(retainedItem);
    expect(openGraphReference).not.toHaveBeenCalled();
    expect(onInsertReference).not.toHaveBeenCalled();
  });

  it("fails closed when a retained Insert callback runs after the live observation leaves READY", () => {
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    const onInsertReference = vi.fn();
    renderPanel(channel, onInsertReference, true);
    const ticket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(ticket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    const retainedInsert = retainedSearch.onInsert;
    const retainedItem = retainedSearch.items[0];
    expect(retainedInsert).toEqual(expect.any(Function));

    act(() => {
      channel.beginObservation();
    });
    retainedInsert!(retainedItem!);
    expect(onInsertReference).not.toHaveBeenCalled();

    const staleTicket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(staleTicket!, {
        status: "stale",
        value: projection({ nodes: [glowkindleNode] }),
        reason: "refreshing",
        ...observed,
      });
    });
    retainedInsert!(retainedItem!);
    expect(onInsertReference).not.toHaveBeenCalled();
  });

  it("fails closed when a retained Insert callback runs after the live Plan editor gate closes", () => {
    const channel = createSurfaceInformationChannel<WorldGraphProjection>(
      worldGraphLensInformationDescriptor(request),
    );
    const onInsertReference = vi.fn();
    const editorGate = { enabled: true };
    renderPanel(channel, onInsertReference, true, () => editorGate.enabled);
    const ticket = channel.beginObservation({ publishLoading: false });
    act(() => {
      channel.commit(ticket!, {
        status: "ready",
        value: projection({ nodes: [glowkindleNode] }),
        ...observed,
      });
    });
    const retainedInsert = retainedSearch.onInsert!;
    const retainedItem = retainedSearch.items[0]!;
    editorGate.enabled = false;
    retainedInsert(retainedItem);
    expect(onInsertReference).not.toHaveBeenCalled();
  });
});

describe("insertPlanGraphReferenceIfLive", () => {
  const reference = {
    kind: "ref" as const,
    refType: "graph-node",
    refId: "npc:glowkindle",
    label: "Glowkindle",
  } satisfies RunbookReferenceAttrs;

  it("inserts through the current editor when the live gate is open", () => {
    const editor = { id: "live-editor" } as never;
    const insert = vi.fn();
    const gate = {
      editor,
      isLocked: false,
      editorInteractive: true,
    };
    const retained = (next: typeof reference) =>
      insertPlanGraphReferenceIfLive({
        getGate: () => gate,
        reference: next,
        insert,
      });
    retained(reference);
    expect(insert).toHaveBeenCalledWith(editor, reference);
  });

  it("does not insert when a retained callback runs after lock or a lost editor", () => {
    const unlockedEditor = { id: "unlocked-editor" } as never;
    const insert = vi.fn();
    const gate = {
      editor: unlockedEditor as { id: string } | null,
      isLocked: false,
      editorInteractive: true,
    };
    const retained = (next: typeof reference) =>
      insertPlanGraphReferenceIfLive({
        getGate: () => ({
          editor: gate.editor as never,
          isLocked: gate.isLocked,
          editorInteractive: gate.editorInteractive,
        }),
        reference: next,
        insert,
      });

    gate.isLocked = true;
    retained(reference);
    expect(insert).not.toHaveBeenCalled();

    gate.isLocked = false;
    gate.editorInteractive = false;
    retained(reference);
    expect(insert).not.toHaveBeenCalled();

    gate.editorInteractive = true;
    gate.editor = null;
    retained(reference);
    expect(insert).not.toHaveBeenCalled();
  });
});
