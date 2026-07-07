import { describe, expect, it } from "vitest";

import { applyAuthoringPillSelection } from "./GraphReviewAuthoringRail";
import type { GraphObjectAuthoringRelationshipFormState } from "./graphObjectAuthoringDraft";
import { createDefaultGraphObjectAuthoringRelationshipFormState } from "./graphObjectAuthoringDraft";

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
