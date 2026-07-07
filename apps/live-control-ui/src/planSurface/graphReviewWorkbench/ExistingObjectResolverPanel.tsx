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
  buildMergeCandidateFromPillAndExisting,
  type GraphObjectMergeCandidate,
} from "./graphObjectMergeCandidates";

export const QUERY_SEARCH_NODE_ID = "__graph_review_query_search__";

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

export function buildQueryOnlySelectedNode(
  query: string,
): GraphReviewResolverSelectedNode {
  const trimmed = query.trim();
  return {
    node_id: QUERY_SEARCH_NODE_ID,
    label: trimmed || "(search)",
    kind: null,
    role: null,
    aliases: [],
    summary: null,
    source_domains: [],
    adjacent_labels: [],
    evidence_ref_ids: [],
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
  linkSourceNode = null,
  mergeReviewSourceNode = null,
  projectionGraphId = null,
  liveRunManifestPath = null,
  nodeViews = null,
  onStageLinkIntent,
  onStageLinkIntentComplete,
  onReviewMerge,
}: {
  campaignId: string;
  sessionId: string;
  laneRole: GraphReviewProjectionLaneRole;
  /** Optional recap pill used only when staging a link intent — not for search. */
  linkSourceNode?: GraphProjectionNodeView | null;
  /** Selected recap pill for merge review (independent of link-intent opt-in). */
  mergeReviewSourceNode?: GraphProjectionNodeView | null;
  projectionGraphId?: string | null;
  liveRunManifestPath?: string | null;
  nodeViews?: Record<string, GraphProjectionNodeView> | null;
  onStageLinkIntent?: (candidate: GraphReviewExistingObjectCandidate) => void;
  onStageLinkIntentComplete?: () => void;
  onReviewMerge?: (candidate: GraphObjectMergeCandidate) => void;
}) {
  const [status, setStatus] = useState<"idle" | "loading" | "ready" | "error">(
    "idle",
  );
  const [response, setResponse] =
    useState<GraphReviewExistingObjectResolverResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [stagedCandidateId, setStagedCandidateId] = useState<string | null>(
    null,
  );
  const [query, setQuery] = useState("");

  useEffect(() => {
    setStatus("idle");
    setResponse(null);
    setError(null);
    setStagedCandidateId(null);
  }, [laneRole, projectionGraphId, liveRunManifestPath]);

  const groupedCandidates = useMemo(
    () => groupCandidatesByScope(response?.candidates ?? []),
    [response],
  );

  const canStageLinkIntent = Boolean(linkSourceNode && onStageLinkIntent);
  const searchPhrase = query.trim();

  const runResolver = () => {
    if (!searchPhrase) {
      setError("Enter a search phrase to find existing objects.");
      setStatus("error");
      return;
    }

    const request: GraphReviewExistingObjectResolverRequest = {
      schema: "dmb_graph_review_existing_object_resolver_request_v1",
      campaign_id: campaignId,
      session_id: sessionId,
      lane_role: laneRole,
      selected_node: buildQueryOnlySelectedNode(searchPhrase),
      projection_graph_id: projectionGraphId,
      live_run_manifest_path: liveRunManifestPath,
      query: searchPhrase,
      node_views: nodeViews,
      include_gm_private: true,
    };
    setStatus("loading");
    setError(null);
    setStagedCandidateId(null);
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
      <h3>Search campaign sources</h3>
      <p>
        Search across current recap, authored memory, party / PC data,
        worldbuilding, campaign memory, and GM-private graph sources. Results
        are independent of any recap pill you may have clicked.
      </p>
      <label className="graph-review-existing-object-resolver-query">
        Search phrase
        <input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              runResolver();
            }
          }}
          placeholder="PC, party, location, or worldbuilding name"
        />
      </label>
      <button
        type="button"
        onClick={runResolver}
        disabled={status === "loading" || !searchPhrase}
      >
        Find existing object
      </button>
      {status === "idle" ? (
        <p>Type a name and press Enter or click Find.</p>
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
                    data-staged={
                      candidate.candidate_id === stagedCandidateId
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
                    {canStageLinkIntent ? (
                      <div className="graph-review-local-link-intent-action">
                        <button
                          type="button"
                          onClick={() => {
                            onStageLinkIntent?.(candidate);
                            setStagedCandidateId(candidate.candidate_id);
                            onStageLinkIntentComplete?.();
                          }}
                        >
                          Stage link intent
                        </button>
                        {mergeReviewSourceNode && nodeViews?.[candidate.candidate_id] ? (
                          <button
                            type="button"
                            onClick={() => {
                              const mergeCandidate = buildMergeCandidateFromPillAndExisting(
                                mergeReviewSourceNode,
                                nodeViews[candidate.candidate_id],
                              );
                              if (mergeCandidate) {
                                onReviewMerge?.(mergeCandidate);
                              }
                            }}
                          >
                            Review merge
                          </button>
                        ) : null}
                        {candidate.candidate_id === stagedCandidateId ? (
                          <p role="status" className="graph-review-info">
                            Link intent staged locally. Open{" "}
                            <strong>Stage &amp; commit</strong> to review and
                            prepare.
                          </p>
                        ) : (
                          <p>
                            Links{" "}
                            <strong>{linkSourceNode?.label ?? "recap object"}</strong>{" "}
                            to this existing match. No identity merge is
                            performed automatically.
                          </p>
                        )}
                      </div>
                    ) : onStageLinkIntent ? (
                      <p className="graph-review-muted">
                        Enable “Link to recap pill” above to stage link
                        intents from these results.
                      </p>
                    ) : null}
                  </article>
                ))}
              </section>
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
