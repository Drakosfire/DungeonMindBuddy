import { useCallback, useState } from "react";

import {
  commitGraphObjectAuthoringWrite,
  prepareGraphObjectAuthoringWrite,
} from "../../api/liveApi";
import type { GraphObjectAuthoringProposalPayload } from "../../api/types";
import { parseGraphObjectAuthoringApiError } from "./graphObjectAuthoringApiErrors";
import {
  serializeGraphObjectAuthoringProposalForApi,
  type GraphObjectAuthoringObjectProposal,
} from "./graphObjectAuthoringDraft";

export interface GraphObjectAuthoringQuickCommitScope {
  campaignId: string;
  sessionId: string;
  sourceRunId?: string | null;
  sourceGraphId?: string | null;
  previewUnionStorePath?: string | null;
}

export interface GraphObjectAuthoringQuickCommitResult {
  committed: boolean;
  nodeId: string | null;
}

function toProposalPayload(
  proposal: GraphObjectAuthoringObjectProposal,
): GraphObjectAuthoringProposalPayload {
  return serializeGraphObjectAuthoringProposalForApi(
    proposal,
  ) as unknown as GraphObjectAuthoringProposalPayload;
}

export function useGraphObjectAuthoringQuickCommit(scope: GraphObjectAuthoringQuickCommitScope) {
  const [committing, setCommitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const commitObjectProposal = useCallback(
    async (proposal: GraphObjectAuthoringObjectProposal): Promise<GraphObjectAuthoringQuickCommitResult> => {
      setCommitting(true);
      setError(null);
      try {
        const apiProposal = toProposalPayload(proposal);
        const prepared = await prepareGraphObjectAuthoringWrite({
          campaignId: scope.campaignId,
          sessionId: scope.sessionId,
          sourceRunId: scope.sourceRunId,
          sourceGraphId: scope.sourceGraphId,
          proposals: [apiProposal],
        });
        const committed = await commitGraphObjectAuthoringWrite({
          campaignId: scope.campaignId,
          sessionId: scope.sessionId,
          sourceRunId: scope.sourceRunId,
          sourceGraphId: scope.sourceGraphId,
          proposals: [apiProposal],
          confirmToken: prepared.confirm_token,
          currentOverlayToken: prepared.current_overlay_token,
          previewUnionStorePath: scope.previewUnionStorePath,
        });
        if (!committed.committed) {
          const message =
            committed.diagnostics[0]?.message ?? "Commit did not complete. Review diagnostics and try again.";
          setError(message);
          return { committed: false, nodeId: null };
        }
        const nodeId = committed.created_node_ids?.[proposal.localProposalId] ?? null;
        return { committed: true, nodeId };
      } catch (err) {
        const message = parseGraphObjectAuthoringApiError(err);
        setError(message);
        return { committed: false, nodeId: null };
      } finally {
        setCommitting(false);
      }
    },
    [
      scope.campaignId,
      scope.previewUnionStorePath,
      scope.sessionId,
      scope.sourceGraphId,
      scope.sourceRunId,
    ],
  );

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    commitObjectProposal,
    committing,
    error,
    clearError,
  };
}
