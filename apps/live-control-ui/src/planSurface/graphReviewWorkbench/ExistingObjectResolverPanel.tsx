import { useEffect, useState } from "react";

import { resolveGraphReviewExistingObjectCandidates } from "../../api/liveApi";
import type {
  GraphProjectionNodeView,
  GraphReviewExistingObjectCandidate,
  GraphReviewExistingObjectResolverRequest,
  GraphReviewExistingObjectResolverResponse,
  GraphReviewResolverSelectedNode,
} from "../../api/types";
import type { GraphReviewProjectionLaneRole } from "./GraphReviewProjectionLane";

export function buildResolverSelectedNode(
  node: GraphProjectionNodeView,
): GraphReviewResolverSelectedNode {
  return {
    node_id: node.node_id,
    label: node.label,
    kind: node.kind ?? null,
    role: node.role ?? null,
    aliases: node.aliases ?? [],
    summary: node.summary ?? null,
    source_domains: node.source_domains ?? [],
    adjacent_labels: (node.adjacency ?? [])
      .map((adjacent) => adjacent.label)
      .filter(Boolean),
    evidence_ref_ids: (node.evidence_badges ?? [])
      .map((badge) => badge.evidence_ref_id)
      .filter(Boolean),
  };
}

function actionLabel(
  action: GraphReviewExistingObjectCandidate["suggested_action"],
): string {
  if (action === "link_existing_later") return "Link existing later";
  if (action === "create_new_later") return "Create new later";
  return "Manual review needed";
}

function sourceLabel(
  source: GraphReviewExistingObjectCandidate["source"],
): string {
  return source.replaceAll("_", " ");
}

export function ExistingObjectResolverPanel({
  campaignId,
  sessionId,
  laneRole,
  selectedNode,
  projectionGraphId = null,
  liveRunManifestPath = null,
  onStageLinkIntent,
}: {
  campaignId: string;
  sessionId: string;
  laneRole: GraphReviewProjectionLaneRole;
  selectedNode: GraphProjectionNodeView | null;
  projectionGraphId?: string | null;
  liveRunManifestPath?: string | null;
  onStageLinkIntent?: (candidate: GraphReviewExistingObjectCandidate) => void;
}) {
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [response, setResponse] =
    useState<GraphReviewExistingObjectResolverResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    setStatus("idle");
    setResponse(null);
    setError(null);
    setSelectedCandidateId(null);
  }, [selectedNode?.node_id, laneRole, projectionGraphId, liveRunManifestPath]);

  if (!selectedNode) {
    return (
      <aside className="graph-review-existing-object-resolver">
        <p>
          Select a graph pill to inspect how this object is used in the
          campaign.
        </p>
      </aside>
    );
  }

  const runResolver = () => {
    const request: GraphReviewExistingObjectResolverRequest = {
      schema: "dmb_graph_review_existing_object_resolver_request_v1",
      campaign_id: campaignId,
      session_id: sessionId,
      lane_role: laneRole,
      selected_node: buildResolverSelectedNode(selectedNode),
      projection_graph_id: projectionGraphId,
      live_run_manifest_path: liveRunManifestPath,
    };
    setStatus("loading");
    setError(null);
    setSelectedCandidateId(null);
    void resolveGraphReviewExistingObjectCandidates(request)
      .then((next) => {
        setResponse(next);
        setStatus("ready");
      })
      .catch((err) => {
        setResponse(null);
        setError(
          err instanceof Error
            ? err.message
            : "Could not load resolver suggestions.",
        );
        setStatus("error");
      });
  };

  return (
    <aside
      className="graph-review-existing-object-resolver"
      aria-label="Existing object resolver suggestions"
    >
      <p className="plan-surface-kicker">Find existing object</p>
      <h3>Check for existing match</h3>
      <p>
        DungeonBuddy checks same-session gold/live graph sources to see whether
        this selected object may already correspond to a known object.
        Campaign-wide search is not available yet.
      </p>
      <p>
        Suggestions are read-only. In Author Draft, you can stage a link intent
        for later prepare/commit review. No link or merge is written here.
      </p>
      <button
        type="button"
        onClick={runResolver}
        disabled={status === "loading"}
      >
        Find existing object
      </button>
      {status === "idle" ? (
        <p>
          Check whether this object already appears in same-session graph
          sources.
        </p>
      ) : null}
      {status === "loading" ? (
        <p role="status">Checking same-session graph sources…</p>
      ) : null}
      {status === "error" ? (
        <p role="alert">{error ?? "Could not load resolver suggestions."}</p>
      ) : null}
      {status === "ready" && response ? (
        <div>
          {response.warnings.map((warning) => (
            <p key={warning} className="graph-review-warning">
              {warning}
            </p>
          ))}
          {response.candidates.length === 0 ? (
            <p>
              No likely existing objects found. This may be new, or match
              sources may be incomplete.
            </p>
          ) : null}
          {response.candidates.length ? <h4>Likely existing objects</h4> : null}
          <div className="graph-review-existing-object-candidate-list">
            {response.candidates.map((candidate) => (
              <article
                key={`${candidate.source}-${candidate.candidate_id}`}
                className="graph-review-existing-object-candidate"
                data-selected={
                  candidate.candidate_id === selectedCandidateId
                    ? "true"
                    : "false"
                }
              >
                <h5>{candidate.label}</h5>
                <p>
                  {[candidate.kind, candidate.role]
                    .filter(Boolean)
                    .join(" / ") || "Object"}
                </p>
                <p>
                  {candidate.confidence[0].toUpperCase() +
                    candidate.confidence.slice(1)}{" "}
                  confidence · {candidate.score.toFixed(2)}
                </p>
                <p>
                  <strong>Reason:</strong> {candidate.reason}
                </p>
                <p>
                  <strong>Source:</strong> {sourceLabel(candidate.source)}
                </p>
                <p>
                  <strong>Suggested action:</strong>{" "}
                  {actionLabel(candidate.suggested_action)}
                </p>
                {candidate.matched_features.length ? (
                  <p>
                    <strong>Matched features:</strong>{" "}
                    {candidate.matched_features.join(", ")}
                  </p>
                ) : null}
                <button
                  type="button"
                  onClick={() => setSelectedCandidateId(candidate.candidate_id)}
                >
                  Review candidate
                </button>
                {onStageLinkIntent ? (
                  <div className="graph-review-local-link-intent-action">
                    <button
                      type="button"
                      onClick={() => onStageLinkIntent(candidate)}
                    >
                      Stage link intent
                    </button>
                    <p>Draft only — no link will be written.</p>
                  </div>
                ) : null}
              </article>
            ))}
          </div>
          {selectedCandidateId ? (
            <p>
              Selected suggestion for review only. No link has been written.
            </p>
          ) : null}
        </div>
      ) : null}
    </aside>
  );
}
