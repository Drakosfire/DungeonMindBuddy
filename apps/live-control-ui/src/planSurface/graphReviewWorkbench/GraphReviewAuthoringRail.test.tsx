import { describe, expect, it } from "vitest";

import {
  applyAuthoringPillSelection,
  resolveAuthoringWorkingNodeContext,
} from "./GraphReviewAuthoringRail";
import type { GraphObjectAuthoringRelationshipFormState } from "./graphObjectAuthoringDraft";
import {
  createDefaultGraphObjectAuthoringFormState,
  createDefaultGraphObjectAuthoringRelationshipFormState,
} from "./graphObjectAuthoringDraft";

describe("applyAuthoringPillSelection", () => {
  const projection = {
    node_views: {
      alden: { node_id: "alden", label: "Alden", kind: "npc", role: "warden" },
      bera: { node_id: "bera", label: "Bera", kind: "npc", role: "scout" },
    },
  } as const;

  it("sets source on the first pill click", () => {
    let formState: GraphObjectAuthoringRelationshipFormState =
      createDefaultGraphObjectAuthoringRelationshipFormState();
    const selected = applyAuthoringPillSelection({
      nodeId: "alden",
      projection: projection as never,
      goldProjection: null,
      relationshipFormState: formState,
      updateRelationshipField: (field, value) => {
        formState = { ...formState, [field]: value };
      },
    });

    expect(selected).toEqual({ laneRole: "live", nodeId: "alden" });
    expect(formState.sourceObjectRef?.label).toBe("Alden");
    expect(formState.targetObjectRef).toBeNull();
  });

  it("sets target on the second different pill click", () => {
    let formState: GraphObjectAuthoringRelationshipFormState = {
      ...createDefaultGraphObjectAuthoringRelationshipFormState(),
      sourceObjectRef: {
        refKind: "existing_graph_node",
        nodeId: "alden",
        label: "Alden",
        kind: "npc",
        role: "warden",
        graphScope: null,
        sourceLabel: null,
        sourceGraphId: null,
        sourcePath: null,
        visibility: null,
      },
    };
    const selected = applyAuthoringPillSelection({
      nodeId: "bera",
      projection: projection as never,
      goldProjection: null,
      relationshipFormState: formState,
      updateRelationshipField: (field, value) => {
        formState = { ...formState, [field]: value };
      },
    });

    expect(selected).toEqual({ laneRole: "live", nodeId: "bera" });
    expect(formState.targetObjectRef?.label).toBe("Bera");
  });
});

describe("resolveAuthoringWorkingNodeContext", () => {
  it("prefers the selected projected node name and type", () => {
    const context = resolveAuthoringWorkingNodeContext({
      selectedNode: {
        node_id: "bbq",
        label: "BBQ",
        kind: "event",
        role: null,
      } as never,
      relationshipSource: null,
      formState: createDefaultGraphObjectAuthoringFormState(null),
      selectedSource: null,
    });

    expect(context).toEqual({ name: "BBQ", typeLabel: "event" });
  });

  it("falls back to relationship source when no selected node", () => {
    const context = resolveAuthoringWorkingNodeContext({
      selectedNode: null,
      relationshipSource: {
        refKind: "existing_graph_node",
        nodeId: "bbq",
        label: "BBQ",
        kind: "event",
        role: null,
      },
      formState: createDefaultGraphObjectAuthoringFormState(null),
      selectedSource: null,
    });

    expect(context).toEqual({ name: "BBQ", typeLabel: "event" });
  });
});
