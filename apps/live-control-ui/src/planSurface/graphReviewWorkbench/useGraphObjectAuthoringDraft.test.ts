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

describe("useGraphObjectAuthoringDraft stageMergeProposal", () => {
  it("does not append a duplicate merge for the same object pair", () => {
    const { result } = renderHook(() => useGraphObjectAuthoringDraft());
    const survivorRef = buildObjectRefFromInspectedNode({
      node_id: "edge-a",
      label: "Edge",
      kind: "location",
    });
    const mergedRef = buildObjectRefFromInspectedNode({
      node_id: "edge-b",
      label: "the Edge",
      kind: "location",
    });
    const mergeInput = {
      survivorObjectRef: survivorRef,
      mergedObjectRefs: [mergedRef],
      mergeReason: "Exact normalized label match",
      matchedFeatures: ["Exact normalized label match"],
    };

    act(() => {
      expect(result.current.stageMergeProposal(mergeInput)).toBe(true);
    });
    act(() => {
      expect(result.current.stageMergeProposal(mergeInput)).toBe(false);
    });

    expect(result.current.proposals).toHaveLength(1);
    expect(result.current.proposals[0]?.proposalKind).toBe("merge_objects");
  });
});

describe("useGraphObjectAuthoringDraft clearCommittedProposals", () => {
  it("clears sessionStorage synchronously so a remounted hook does not reload committed drafts", () => {
    const scope = { campaignId: "longmont-c1", sessionId: "session-remount" };
    const storageKey = `graph-object-authoring-staged:${scope.campaignId}:${scope.sessionId}`;
    sessionStorage.removeItem(storageKey);

    const { result, unmount } = renderHook(() => useGraphObjectAuthoringDraft(scope));
    const survivorRef = buildObjectRefFromInspectedNode({
      node_id: "hub",
      label: "Hub",
      kind: "npc",
    });
    const mergedRef = buildObjectRefFromInspectedNode({
      node_id: "dup",
      label: "Dup",
      kind: "npc",
    });

    act(() => {
      result.current.stageMergeProposal({
        survivorObjectRef: survivorRef,
        mergedObjectRefs: [mergedRef],
        mergeReason: "test merge",
        matchedFeatures: ["label"],
      });
    });

    const proposalId = result.current.proposals[0]?.localProposalId;
    expect(proposalId).toBeTruthy();
    expect(sessionStorage.getItem(storageKey)).toBeTruthy();

    act(() => {
      result.current.clearCommittedProposals([proposalId!]);
    });

    expect(result.current.proposals).toHaveLength(0);
    expect(sessionStorage.getItem(storageKey)).toBeNull();

    unmount();

    const { result: remounted } = renderHook(() => useGraphObjectAuthoringDraft(scope));
    expect(remounted.current.proposals).toHaveLength(0);
    sessionStorage.removeItem(storageKey);
  });
});
