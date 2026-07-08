import { describe, expect, it } from "vitest";

import type {
  GraphProjectionNodeView,
  GraphReviewExistingObjectCandidate,
} from "../../api/types";
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
  getSearchMergeStageBlockReason,
  isClusterPeerOfSelection,
  isSearchMergeAlreadyStaged,
  isSearchMergeStageInputBlocked,
  possibleDuplicateCount,
  rehydrateIdentitySelection,
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
    state = setCanonicalCandidate(state, lysandraParty);
    expect(state.canonical?.candidate_id).toBe("party:captain_lysandra_ironveil");
    state = toggleDuplicateCandidate(state, lysandraSession);
    expect(canStageSearchMerge(state)).toBe(true);
    expect(state.duplicates.map((item) => item.candidate_id)).toEqual([
      "node:lysandra",
    ]);

    state = toggleDuplicateCandidate(state, lysandraParty);
    expect(state.duplicates).toHaveLength(1);

    state = setCanonicalCandidate(state, lysandraSession);
    expect(state.canonical?.candidate_id).toBe("node:lysandra");
    expect(state.duplicates).toHaveLength(0);
  });

  it("rehydrates identity selection from stored candidate ids", () => {
    const restored = rehydrateIdentitySelection(
      {
        canonicalCandidateId: "party:captain_lysandra_ironveil",
        duplicateCandidateIds: ["node:lysandra"],
      },
      [lysandraSession, lysandraParty, lysandraMemory],
    );
    expect(restored.canonical?.candidate_id).toBe("party:captain_lysandra_ironveil");
    expect(restored.duplicates.map((item) => item.candidate_id)).toEqual([
      "node:lysandra",
    ]);
  });

  it("highlights cluster peers of the current identity selection", () => {
    let state = createEmptyIdentitySelection();
    state = setCanonicalCandidate(state, lysandraParty);
    expect(isClusterPeerOfSelection(lysandraSession, state)).toBe(true);
    expect(isClusterPeerOfSelection(lysandraMemory, state)).toBe(true);
    expect(isClusterPeerOfSelection(lysandraParty, state)).toBe(false);
  });

  it("builds merge stage input for search-selected identity pairs", () => {
    let state = createEmptyIdentitySelection();
    state = setCanonicalCandidate(state, lysandraParty);
    state = toggleDuplicateCandidate(state, lysandraSession);

    const input = buildSearchMergeStageInput(state, "graph-live-1");
    expect(input).toMatchObject({
      mergeReason:
        "Search result identity merge: party:captain_lysandra_ironveil ← node:lysandra",
      sourceGraphId: "graph-live-1",
    });
    expect(input?.survivorObjectRef.nodeId).toBe("party:captain_lysandra_ironveil");
    expect(input?.mergedObjectRefs.map((ref) => ref.nodeId)).toEqual([
      "node:lysandra",
    ]);
    expect(input?.matchedFeatures).toContain("search_identity_workbench");
  });

  it("preserves external canonical survivor ids when duplicate maps to projection node", () => {
    const nodeViews: Record<string, GraphProjectionNodeView> = {
      character_lysandra: {
        node_id: "character_lysandra",
        label: "Captain Lysandra Ironveil",
        kind: "character",
        role: "companion",
        aliases: ["Lysandra", "Captain Ironveil"],
        source_domains: ["recap"],
        evidence_badges: [
          {
            evidence_ref_id: "evidence-1",
            source_artifact_id: "artifact-1",
            source_domain: "recap",
            evidence_role: "mention",
            is_focus_session_evidence: true,
            can_open_source: true,
            can_highlight_span: false,
            label: "Session 23 recap",
          },
        ],
        adjacency: [
          {
            edge_id: "edge-1",
            node_id: "location_mireward",
            label: "Mireward Reach",
            kind: "location",
            predicate: "located_in",
            direction: "outgoing",
            anchored_to_focus_session: true,
            source_domains: ["recap"],
            evidence_ref_ids: ["evidence-1"],
          },
        ],
        anchored_to_focus_session: true,
        summary: "Captain of the party at Mireward Reach.",
      },
    };

    let state = createEmptyIdentitySelection();
    state = setCanonicalCandidate(state, lysandraParty);
    state = toggleDuplicateCandidate(state, lysandraSession);

    const input = buildSearchMergeStageInput(state, "graph-live-1", nodeViews);
    expect(input?.survivorObjectRef.nodeId).toBe("party:captain_lysandra_ironveil");
    expect(input?.mergedObjectRefs.map((ref) => ref.nodeId)).toEqual([
      "character_lysandra",
    ]);
    expect(isSearchMergeStageInputBlocked(input)).toBe(false);
  });

  it("blocks staging when survivor and merged-away refs share a projection node id", () => {
    const input = buildSearchMergeStageInput({
      canonical: lysandraParty,
      duplicates: [lysandraSession],
    });
    expect(input).toBeTruthy();
    if (!input) {
      return;
    }
    input.mergedObjectRefs[0] = {
      ...input.mergedObjectRefs[0],
      nodeId: input.survivorObjectRef.nodeId,
    };
    expect(getSearchMergeStageBlockReason(input)).toBe(
      "survivor_collides_with_merged_away",
    );
    expect(isSearchMergeStageInputBlocked(input)).toBe(true);
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
