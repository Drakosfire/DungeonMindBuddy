import { useMemo, useState } from "react";

import type { GraphProjectionNodeView } from "../../api/types";
import { GraphReviewMergeCandidateCard } from "./GraphReviewMergeCandidateCard";
import {
  findDuplicateMergeProposal,
  mergeObjectPairKey,
  stagedMergePairKeys,
  type GraphObjectAuthoringProposal,
} from "./graphObjectAuthoringDraft";
import {
  findProjectionMergeCandidates,
  type GraphObjectMergeCandidate,
} from "./graphObjectMergeCandidates";
import type { UseGraphObjectAuthoringDraftResult } from "./useGraphObjectAuthoringDraft";

type MergeCandidateDecision = "pending" | "accepted" | "rejected" | "deferred";

function nodeForRef(
  ref: GraphObjectMergeCandidate["survivorObjectRef"],
  nodeViews: Record<string, GraphProjectionNodeView> | null | undefined,
): GraphProjectionNodeView | null {
  if (!nodeViews || !ref.nodeId) {
    return null;
  }
  return nodeViews[ref.nodeId] ?? null;
}

function candidatePairKey(candidate: GraphObjectMergeCandidate): string | null {
  return mergeObjectPairKey(candidate.survivorObjectRef, candidate.mergedObjectRef);
}

function decisionForCandidate(
  candidate: GraphObjectMergeCandidate,
  decisions: Record<string, MergeCandidateDecision>,
  stagedPairKeys: Set<string>,
): MergeCandidateDecision {
  const explicit = decisions[candidate.candidateId];
  if (explicit) {
    return explicit;
  }
  const pairKey = candidatePairKey(candidate);
  if (pairKey && stagedPairKeys.has(pairKey)) {
    return "accepted";
  }
  return "pending";
}

export function GraphReviewMergeCandidatesPanel({
  nodeViews,
  graphObjectAuthoringDraft,
  selectedPillLabel,
  focusedCandidate,
}: {
  nodeViews: Record<string, GraphProjectionNodeView> | null | undefined;
  graphObjectAuthoringDraft: UseGraphObjectAuthoringDraftResult;
  selectedPillLabel?: string | null;
  focusedCandidate?: GraphObjectMergeCandidate | null;
}) {
  const [scanRan, setScanRan] = useState(false);
  const [scannedCandidates, setScannedCandidates] = useState<GraphObjectMergeCandidate[]>([]);
  const [decisions, setDecisions] = useState<Record<string, MergeCandidateDecision>>({});

  const stagedPairKeys = useMemo(
    () => stagedMergePairKeys(graphObjectAuthoringDraft.proposals),
    [graphObjectAuthoringDraft.proposals],
  );
  const stagedMergeCount = useMemo(
    () =>
      graphObjectAuthoringDraft.proposals.filter(
        (proposal): proposal is Extract<GraphObjectAuthoringProposal, { proposalKind: "merge_objects" }> =>
          proposal.proposalKind === "merge_objects",
      ).length,
    [graphObjectAuthoringDraft.proposals],
  );

  const candidates = useMemo(() => {
    const base = scanRan ? scannedCandidates : [];
    if (focusedCandidate) {
      const exists = base.some((item) => item.candidateId === focusedCandidate.candidateId);
      return exists ? base : [focusedCandidate, ...base];
    }
    return base;
  }, [focusedCandidate, scanRan, scannedCandidates]);

  const visibleCandidates = candidates.filter(
    (candidate) => decisionForCandidate(candidate, decisions, stagedPairKeys) !== "rejected",
  );

  const runDuplicateScan = () => {
    const found = findProjectionMergeCandidates(nodeViews);
    setScannedCandidates(found);
    setScanRan(true);
  };

  const acceptCandidate = (candidate: GraphObjectMergeCandidate) => {
    const alreadyStaged = Boolean(
      findDuplicateMergeProposal(
        candidate.survivorObjectRef,
        [candidate.mergedObjectRef],
        graphObjectAuthoringDraft.proposals,
      ),
    );
    if (alreadyStaged) {
      setDecisions((prev) => ({ ...prev, [candidate.candidateId]: "accepted" }));
      return;
    }

    const staged = graphObjectAuthoringDraft.stageMergeProposal({
      survivorObjectRef: candidate.survivorObjectRef,
      mergedObjectRefs: [candidate.mergedObjectRef],
      mergeReason: candidate.reason,
      matchedFeatures: candidate.matchedFeatures,
    });
    if (!staged) {
      return;
    }
    setDecisions((prev) => ({ ...prev, [candidate.candidateId]: "accepted" }));
  };

  return (
    <section
      className="graph-review-merge-candidates-panel"
      data-testid="graph-review-merge-candidates-panel"
    >
      <header>
        <p className="plan-surface-kicker">Merge candidates</p>
        <h3>Review likely duplicate objects</h3>
        <p className="graph-object-authoring-surface-hint">
          Compare objects side by side and accept merges you agree with. The bulk scan
          only surfaces high-confidence identity duplicates (label or alias matches),
          not every object that shares a kind or neighbor. Accepting stages a local
          identity merge proposal — nothing is deleted until you prepare and commit
          authored graph memory.
        </p>
        {selectedPillLabel ? (
          <p className="graph-review-muted">
            Selected recap pill: <strong>{selectedPillLabel}</strong>. Use Existing
            object search → Review merge to compare a pill against a search result.
          </p>
        ) : null}
      </header>

      <div className="graph-review-merge-candidates-scan-action">
        <button type="button" onClick={runDuplicateScan}>
          Find likely duplicates in this recap
        </button>
        {scanRan ? (
          <p className="graph-review-muted">
            Found {scannedCandidates.length} candidate
            {scannedCandidates.length === 1 ? "" : "s"} from current projection signals.
          </p>
        ) : null}
      </div>

      {visibleCandidates.length === 0 ? (
        <p className="graph-review-muted">
          {scanRan
            ? "No likely duplicate pairs matched the deterministic scan rules."
            : "Run the duplicate scan or open Review merge from Existing object search."}
        </p>
      ) : (
        <div className="graph-review-merge-candidate-list">
          {visibleCandidates.map((candidate) => (
            <GraphReviewMergeCandidateCard
              key={candidate.candidateId}
              candidate={candidate}
              survivorNode={nodeForRef(candidate.survivorObjectRef, nodeViews)}
              mergedNode={nodeForRef(candidate.mergedObjectRef, nodeViews)}
              decision={decisionForCandidate(candidate, decisions, stagedPairKeys)}
              onAccept={() => acceptCandidate(candidate)}
              onReject={() =>
                setDecisions((prev) => ({ ...prev, [candidate.candidateId]: "rejected" }))
              }
              onDefer={() =>
                setDecisions((prev) => ({ ...prev, [candidate.candidateId]: "deferred" }))
              }
            />
          ))}
        </div>
      )}

      {stagedMergeCount > 0 ? (
        <p role="status" className="graph-review-info">
          {stagedMergeCount} merge{stagedMergeCount === 1 ? "" : "s"} staged locally. Keep
          reviewing candidates here, then open <strong>Stage &amp; commit</strong> when
          you are ready to prepare and commit.
        </p>
      ) : null}
    </section>
  );
}
