import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  buildObjectRefFromInspectedNode,
  buildManualObjectRef,
} from "./graphObjectAuthoringDraft";
import { useGraphObjectAuthoringDraft } from "./useGraphObjectAuthoringDraft";

describe("useGraphObjectAuthoringDraft stageRelationshipProposal", () => {
  it("does not append a proposal when source and target are the exact same object ref", () => {
    const { result } = renderHook(() => useGraphObjectAuthoringDraft());
    const sameRef = buildObjectRefFromInspectedNode({ node_id: "bonogo", label: "Bonogo", kind: "pc" });

    act(() => {
      result.current.updateRelationshipField("sourceObjectRef", sameRef);
    });
    act(() => {
      result.current.updateRelationshipField("targetObjectRef", sameRef);
    });
    act(() => {
      result.current.updateRelationshipField("relationshipType", "threatens");
    });
    act(() => {
      result.current.stageRelationshipProposal();
    });

    expect(result.current.proposals).toHaveLength(0);
  });

  it("appends a proposal when source and target differ", () => {
    const { result } = renderHook(() => useGraphObjectAuthoringDraft());
    const sourceRef = buildObjectRefFromInspectedNode({ node_id: "bonogo", label: "Bonogo", kind: "pc" });
    const targetRef = buildManualObjectRef("Questionable Company");

    act(() => {
      result.current.updateRelationshipField("sourceObjectRef", sourceRef);
    });
    act(() => {
      result.current.updateRelationshipField("targetObjectRef", targetRef);
    });
    act(() => {
      result.current.updateRelationshipField("relationshipType", "has_member");
    });
    act(() => {
      result.current.stageRelationshipProposal();
    });

    expect(result.current.proposals).toHaveLength(1);
    expect(result.current.proposals[0]?.proposalKind).toBe("relationship");
  });
});
