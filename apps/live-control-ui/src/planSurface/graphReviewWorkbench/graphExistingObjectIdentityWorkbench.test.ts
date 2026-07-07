import { describe, expect, it } from "vitest";

import type { GraphReviewExistingObjectCandidate } from "../../api/types";
import {
  buildGraphObjectAuthoringMergeProposal,
  findDuplicateMergeProposal,
} from "./graphObjectAuthoringDraft";
import {
  buildLinkExistingFormStateFromResolverCandidate,
  buildObjectRefFromExistingObjectCandidate,
  buildSearchMergeStageInput,
  candidateClusterKeys,
  canStageSearchMerge,
  clearIdentitySelection,
  createEmptyIdentitySelection,
  isSearchMergeAlreadyStaged,
  possibleDuplicateCount,
  searchMergePairKey,
  setCanonicalCandidate,
  toggleDuplicateCandidate,
} from "./graphExistingObjectIdentityWorkbench";

const lysandraSession: GraphReviewExistingObjectCandidate = {
  candidate_id: "node:lysandra",
  label: "Lysandra",
  kind: "npc",
  role: "captain",
  confidence: "high",
  score: 0.91,
  reason: "label match",
  source: "live_projection",
  suggested_action: "manual_review_needed",
  matched_features: ["label"],
  graph_scope: "current_recap_projection",
  source_label: "Current recap",
  aliases: ["Lysandra"],
};

const lysandraParty: GraphReviewExistingObjectCandidate = {
  candidate_id: "party:captain_lysandra_ironveil",
  label: "Captain Lysandra Ironveil",
  kind: "character",
  role: "companion",
  confidence: "high",
  score: 0.95,
  reason: "alias match",
  source: "union_supergraph",
  suggested_action: "link_existing_later",
  matched_features: ["alias", "label"],
  graph_scope: "party_pc",
  source_label: "Party / PCs",
  aliases: ["Lysandra", "Captain Ironveil"],
};

const lysandraMemory: GraphReviewExistingObjectCandidate = {
  candidate_id: "character_captain_lysandra_ironveil",
  label: "Captain Lysandra Ironveil",
  kind: "character",
  role: "companion",
  confidence: "medium",
  score: 0.82,
  reason: "alias overlap",
  source: "union_supergraph",
  suggested_action: "manual_review_needed",
  matched_features: ["alias"],
  graph_scope: "campaign_memory",
  source_label: "Campaign memory",
  aliases: ["Lysandra"],
};

describe("graphExistingObjectIdentityWorkbench", () => {
  it("maps resolver candidates to existing_graph_node object refs", () => {
    expect(buildObjectRefFromExistingObjectCandidate(lysandraParty)).toMatchObject({
      refKind: "existing_graph_node",
      nodeId: "party:captain_lysandra_ironveil",
      label: "Captain Lysandra Ironveil",
      graphScope: "party_pc",
      sourceLabel: "Party / PCs",
    });
  });

  it("builds link-existing form state from resolver candidates", () => {
    expect(buildLinkExistingFormStateFromResolverCandidate(lysandraParty)).toMatchObject({
      operation: "alias",
      aliasText: "Captain Lysandra Ironveil",
      existingObjectRef: {
        nodeId: "party:captain_lysandra_ironveil",
      },
    });
  });

  it("tracks canonical and duplicate selection without self-overlap", () => {
    let state = createEmptyIdentitySelection();
    state = setCanonicalCandidate(state, lysandraParty);
    state = toggleDuplicateCandidate(state, lysandraSession);
    expect(canStageSearchMerge(state)).toBe(true);
    expect(state.canonical?.candidate_id).toBe("party:captain_lysandra_ironveil");
    expect(state.duplicates.map((item) => item.candidate_id)).toEqual([
      "node:lysandra",
    ]);

    state = toggleDuplicateCandidate(state, lysandraParty);
    expect(state.duplicates).toHaveLength(1);

    state = setCanonicalCandidate(state, lysandraSession);
    expect(state.canonical?.candidate_id).toBe("node:lysandra");
    expect(state.duplicates).toHaveLength(0);
  });

  it("builds merge stage input for search-selected identity pairs", () => {
    let state = createEmptyIdentitySelection();
    state = setCanonicalCandidate(state, lysandraParty);
    state = toggleDuplicateCandidate(state, lysandraSession);

    const input = buildSearchMergeStageInput(state, "graph-live-1");
    expect(input).toMatchObject({
      mergeReason:
        "Search result identity merge: node:lysandra → party:captain_lysandra_ironveil",
      sourceGraphId: "graph-live-1",
    });
    expect(input?.survivorObjectRef.nodeId).toBe("party:captain_lysandra_ironveil");
    expect(input?.mergedObjectRefs.map((ref) => ref.nodeId)).toEqual([
      "node:lysandra",
    ]);
    expect(input?.matchedFeatures).toContain("search_identity_workbench");
  });

  it("detects duplicate staged merge pairs", () => {
    let state = createEmptyIdentitySelection();
    state = setCanonicalCandidate(state, lysandraParty);
    state = toggleDuplicateCandidate(state, lysandraSession);
    const input = buildSearchMergeStageInput(state);
    expect(input).toBeTruthy();

    const proposal = buildGraphObjectAuthoringMergeProposal({
      survivorObjectRef: input!.survivorObjectRef,
      mergedObjectRefs: input!.mergedObjectRefs,
      mergeReason: input!.mergeReason,
      matchedFeatures: input!.matchedFeatures,
    });
    expect(proposal).toBeTruthy();
    expect(isSearchMergeAlreadyStaged(input!, [proposal!])).toBe(true);
    expect(
      findDuplicateMergeProposal(
        input!.survivorObjectRef,
        input!.mergedObjectRefs,
        [proposal!],
      ),
    ).toBeTruthy();
  });

  it("generates stable merge pair keys regardless of survivor direction", () => {
    const forward = searchMergePairKey(lysandraParty, lysandraSession);
    const reverse = searchMergePairKey(lysandraSession, lysandraParty);
    expect(forward).toBeTruthy();
    expect(forward).toBe(reverse);
  });

  it("counts possible duplicate peers from label and alias overlap", () => {
    const peers = possibleDuplicateCount(lysandraSession, [
      lysandraSession,
      lysandraParty,
      lysandraMemory,
    ]);
    expect(peers).toBe(2);
    expect(candidateClusterKeys(lysandraParty)).toContain("lysandra");
  });

  it("clears identity selection", () => {
    let state = setCanonicalCandidate(createEmptyIdentitySelection(), lysandraParty);
    state = toggleDuplicateCandidate(state, lysandraSession);
    expect(clearIdentitySelection()).toEqual(createEmptyIdentitySelection());
    expect(state.duplicates).toHaveLength(1);
  });
});
