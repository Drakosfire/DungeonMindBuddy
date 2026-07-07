import { useEffect, useMemo, useState } from "react";

import { resolveGraphReviewExistingObjectCandidates } from "../../api/liveApi";
import type {
  GraphProjectionNodeView,
  GraphReviewExistingObjectCandidate,
  GraphReviewExistingObjectResolverRequest,
  GraphReviewExistingObjectResolverResponse,
  GraphReviewResolverSelectedNode,
} from "../../api/types";
import type { GraphReviewProjectionLaneRole } from "./GraphReviewProjectionLane";
import {
  candidateScopeLabel,
  formatResolverCandidateLabel,
  formatResolverCandidateMeta,
  groupCandidatesByScope,
} from "./graphObjectCandidateScope";

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

export function ExistingObjectResolverPanel({
  campaignId,
  sessionId,
  laneRole,
  selectedNode,
  projectionGraphId = null,
  liveRunManifestPath = null,
  nodeViews = null,
  onStageLinkIntent,
}: {
  campaignId: string;
  sessionId: string;
  laneRole: GraphReviewProjectionLaneRole;
  selectedNode: GraphProjectionNodeView | null;
  projectionGraphId?: string | null;
  liveRunManifestPath?: string | null;
  nodeViews?: Record<string, GraphProjectionNodeView> | null;
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
  const [query, setQuery] = useState("");

  useEffect(() => {
    setStatus("idle");
    setResponse(null);
    setError(null);
    setSelectedCandidateId(null);
    setQuery(selectedNode?.label ?? "");
  }, [selectedNode?.node_id, laneRole, projectionGraphId, liveRunManifestPath]);

  const groupedCandidates = useMemo(
    () => groupCandidatesByScope(response?.candidates ?? []),
    [response],
  );

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
      query: query.trim() || selectedNode.label,
      node_views: nodeViews,
      include_gm_private: true,
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
        Search across current recap, authored memory, party / PC data,
        worldbuilding, campaign memory, and GM-private graph sources. Each row
        keeps its source label — choosing a candidate stages a link/reference,
        not an automatic identity merge.
      </p>
      <label className="graph-review-existing-object-resolver-query">
        Search phrase
        <input
          type="text"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={selectedNode.label}
        />
      </label>
      <button
        type="button"
        onClick={runResolver}
        disabled={status === "loading"}
      >
        Find existing object
      </button>
      {status === "idle" ? (
        <p>
          Use the selected pill label or type a phrase such as a PC, party, or
          worldbuilding name.
        </p>
      ) : null}
      {status === "loading" ? (
        <p role="status">Searching campaign graph scopes…</p>
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
          {(response.diagnostics ?? [])
            .filter((diagnostic) => diagnostic.severity !== "error")
            .map((diagnostic) => (
              <p key={`${diagnostic.code}-${diagnostic.message}`} className="graph-review-info">
                {diagnostic.message}
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
            {groupedCandidates.map((group) => (
              <section
                key={group.scope}
                className="graph-review-existing-object-candidate-group"
                aria-label={candidateScopeLabel({ graph_scope: group.scope === "unknown" ? null : group.scope, source_label: null })}
              >
                <h5>{group.scope === "unknown" ? "Other sources" : candidateScopeLabel({ graph_scope: group.scope, source_label: null })}</h5>
                {group.candidates.map((candidate) => (
                  <article
                    key={`${candidate.graph_scope ?? candidate.source}-${candidate.candidate_id}`}
                    className="graph-review-existing-object-candidate"
                    data-selected={
                      candidate.candidate_id === selectedCandidateId
                        ? "true"
                        : "false"
                    }
                  >
                    <h6>{formatResolverCandidateLabel(candidate)}</h6>
                    <p>{formatResolverCandidateMeta(candidate)}</p>
                    <p>
                      {candidate.confidence[0].toUpperCase() +
                        candidate.confidence.slice(1)}{" "}
                      confidence · {candidate.score.toFixed(2)}
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
                        <p>
                          Selecting an existing object stages a link/reference.
                          It does not merge identities automatically.
                        </p>
                      </div>
                    ) : null}
                  </article>
                ))}
              </section>
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
