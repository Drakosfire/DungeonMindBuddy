import { useEffect, useMemo, useRef, useState } from "react";

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
  groupCandidatesByScope,
} from "./graphObjectCandidateScope";
import {
  buildMergeCandidateFromPillAndExisting,
  type GraphObjectMergeCandidate,
} from "./graphObjectMergeCandidates";
import {
  buildSearchMergeStageInput,
  candidateSelectionRole,
  clearCanonicalCandidate,
  clearIdentitySelection,
  createEmptyIdentitySelection,
  formatCandidateIdentitySubline,
  isSearchMergeAlreadyStaged,
  possibleDuplicateCount,
  readStoredIdentityWorkbenchState,
  rehydrateIdentitySelection,
  serializeIdentitySelection,
  setCanonicalCandidate,
  toggleDuplicateCandidate,
  writeStoredIdentityWorkbenchState,
  type ExistingObjectIdentitySelectionState,
  type SearchMergeStageInput,
} from "./graphExistingObjectIdentityWorkbench";
import type { GraphObjectAuthoringProposal } from "./graphObjectAuthoringDraft";
import { GraphReviewExistingObjectIdentityCompare } from "./GraphReviewExistingObjectIdentityCompare";

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
  overlayProposals = [],
  onStageLinkIntent,
  onStageLinkIntentComplete,
  onReviewMerge,
  onStageSearchMerge,
  onStageSearchMergeComplete,
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
  overlayProposals?: GraphObjectAuthoringProposal[];
  onStageLinkIntent?: (candidate: GraphReviewExistingObjectCandidate) => void;
  onStageLinkIntentComplete?: () => void;
  onReviewMerge?: (candidate: GraphObjectMergeCandidate) => void;
  onStageSearchMerge?: (input: SearchMergeStageInput) => boolean;
  onStageSearchMergeComplete?: () => void;
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
  const [query, setQuery] = useState(() => {
    const stored = readStoredIdentityWorkbenchState({ campaignId, sessionId });
    return stored?.query ?? "";
  });
  const [identitySelection, setIdentitySelection] =
    useState<ExistingObjectIdentitySelectionState>(createEmptyIdentitySelection());
  const [stageMergeFeedback, setStageMergeFeedback] = useState<
    "idle" | "staged" | "duplicate" | "blocked"
  >("idle");
  const stagedMergeSeenInOverlayRef = useRef(false);
  const lastSearchQueryRef = useRef("");

  const storageScope = useMemo(
    () => ({ campaignId, sessionId }),
    [campaignId, sessionId],
  );

  const persistIdentityWorkbenchState = (
    nextQuery: string,
    nextSelection: ExistingObjectIdentitySelectionState,
  ) => {
    writeStoredIdentityWorkbenchState(
      storageScope,
      serializeIdentitySelection(nextQuery, nextSelection),
    );
  };

  useEffect(() => {
    setStatus("idle");
    setResponse(null);
    setError(null);
    setStagedCandidateId(null);
    setIdentitySelection(createEmptyIdentitySelection());
    setStageMergeFeedback("idle");
    stagedMergeSeenInOverlayRef.current = false;
    lastSearchQueryRef.current = "";
    sessionStorage.removeItem(
      `graph-existing-object-identity-workbench:${campaignId}:${sessionId}`,
    );
  }, [campaignId, sessionId, laneRole]);

  const groupedCandidates = useMemo(
    () => groupCandidatesByScope(response?.candidates ?? []),
    [response],
  );

  const allCandidates = response?.candidates ?? [];
  const searchPhrase = query.trim();

  const searchMergeInput = useMemo(
    () => buildSearchMergeStageInput(identitySelection, projectionGraphId),
    [identitySelection, projectionGraphId],
  );

  useEffect(() => {
    if (stageMergeFeedback !== "staged" || !searchMergeInput) {
      stagedMergeSeenInOverlayRef.current = false;
      return;
    }
    if (isSearchMergeAlreadyStaged(searchMergeInput, overlayProposals)) {
      stagedMergeSeenInOverlayRef.current = true;
      return;
    }
    if (!stagedMergeSeenInOverlayRef.current) {
      return;
    }
    setStageMergeFeedback("idle");
    const cleared = clearIdentitySelection();
    setIdentitySelection(cleared);
    persistIdentityWorkbenchState(searchPhrase, cleared);
    stagedMergeSeenInOverlayRef.current = false;
  }, [overlayProposals, searchMergeInput, stageMergeFeedback, searchPhrase, storageScope]);

  useEffect(() => {
    if (!response?.candidates.length) {
      return;
    }
    const stored = readStoredIdentityWorkbenchState(storageScope);
    if (!stored || stored.query !== searchPhrase) {
      return;
    }
    setIdentitySelection((prev) => {
      if (prev.canonical || prev.duplicates.length > 0) {
        return prev;
      }
      return rehydrateIdentitySelection(stored, response.candidates);
    });
  }, [response, searchPhrase, storageScope]);

  const canStageIdentityMerge = Boolean(onStageSearchMerge && searchMergeInput);
  const mergeAlreadyStaged = searchMergeInput
    ? isSearchMergeAlreadyStaged(searchMergeInput, overlayProposals)
    : false;

  const canStageLinkIntent = Boolean(linkSourceNode && onStageLinkIntent);

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
    if (lastSearchQueryRef.current !== searchPhrase) {
      setIdentitySelection(createEmptyIdentitySelection());
      setStageMergeFeedback("idle");
      stagedMergeSeenInOverlayRef.current = false;
    }
    lastSearchQueryRef.current = searchPhrase;
    void resolveGraphReviewExistingObjectCandidates(request)
      .then((next) => {
        setResponse(next);
        setStatus("ready");
        const stored = readStoredIdentityWorkbenchState(storageScope);
        if (stored?.query === searchPhrase) {
          setIdentitySelection(
            rehydrateIdentitySelection(stored, next.candidates),
          );
        } else {
          persistIdentityWorkbenchState(searchPhrase, createEmptyIdentitySelection());
        }
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

  const handleStageSearchMerge = () => {
    if (!searchMergeInput || !onStageSearchMerge) {
      setStageMergeFeedback("blocked");
      return;
    }
    if (isSearchMergeAlreadyStaged(searchMergeInput, overlayProposals)) {
      setStageMergeFeedback("duplicate");
      return;
    }
    const staged = onStageSearchMerge(searchMergeInput);
    if (staged) {
      setStageMergeFeedback("staged");
      onStageSearchMergeComplete?.();
    } else {
      setStageMergeFeedback("duplicate");
    }
  };

  const compareDuplicate =
    identitySelection.duplicates.length === 1
      ? identitySelection.duplicates[0]
      : null;

  return (
    <aside
      className="graph-review-existing-object-resolver"
      aria-label="Existing object resolver suggestions"
    >
      <p className="plan-surface-kicker">Find existing object</p>
      <h3>Search campaign sources</h3>
      <p>
        Search across current recap, authored memory, party / PC data,
        worldbuilding, campaign memory, and GM-private graph sources. Pick a
        canonical hub and duplicate records to stage identity merges without
        selecting a recap pill.
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
          {identitySelection.canonical || identitySelection.duplicates.length ? (
            <section className="graph-review-existing-object-identity-selection">
              <h4>Identity selection</h4>
              <p className="graph-review-muted">
                {identitySelection.canonical
                  ? `Canonical hub: ${identitySelection.canonical.label} (${identitySelection.canonical.candidate_id})`
                  : "Choose one result as the canonical hub."}
                {identitySelection.duplicates.length
                  ? ` · ${identitySelection.duplicates.length} duplicate(s) selected`
                  : ""}
              </p>
              <div className="graph-review-existing-object-identity-selection-actions">
                <button
                  type="button"
                  onClick={() => {
                    const cleared = clearIdentitySelection();
                    setIdentitySelection(cleared);
                    setStageMergeFeedback("idle");
                    persistIdentityWorkbenchState(searchPhrase, cleared);
                  }}
                >
                  Clear selection
                </button>
                {canStageIdentityMerge ? (
                  <button
                    type="button"
                    onClick={handleStageSearchMerge}
                    disabled={mergeAlreadyStaged}
                  >
                    Stage merge into canonical
                  </button>
                ) : null}
              </div>
              {stageMergeFeedback === "staged" ? (
                <p role="status" className="graph-review-info">
                  Identity merge staged in authored overlay. Open{" "}
                  <strong>Stage &amp; commit</strong> to prepare and commit.
                </p>
              ) : null}
              {stageMergeFeedback === "duplicate" || mergeAlreadyStaged ? (
                <p role="status" className="graph-review-warning">
                  This merge pair is already staged in the authored overlay tray.
                </p>
              ) : null}
            </section>
          ) : null}
          {identitySelection.canonical && compareDuplicate ? (
            <GraphReviewExistingObjectIdentityCompare
              canonical={identitySelection.canonical}
              duplicate={compareDuplicate}
            />
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
                {group.candidates.map((candidate) => {
                  const selectionRole = candidateSelectionRole(
                    identitySelection,
                    candidate,
                  );
                  const duplicatePeers = possibleDuplicateCount(
                    candidate,
                    allCandidates,
                  );

                  return (
                    <article
                      key={`${candidate.graph_scope ?? candidate.source}-${candidate.candidate_id}`}
                      className="graph-review-existing-object-candidate"
                      data-staged={
                        candidate.candidate_id === stagedCandidateId
                          ? "true"
                          : "false"
                      }
                      data-identity-role={selectionRole ?? "none"}
                    >
                      <h6>{formatResolverCandidateLabel(candidate)}</h6>
                      <p className="graph-review-existing-object-candidate-id">
                        <code>{candidate.candidate_id}</code>
                      </p>
                      <p>{formatCandidateIdentitySubline(candidate)}</p>
                      <p>{candidate.reason}</p>
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
                      {candidate.authored ? (
                        <p>
                          <strong>Authored:</strong> yes
                        </p>
                      ) : null}
                      {duplicatePeers > 0 ? (
                        <p className="graph-review-existing-object-duplicate-badge">
                          Possible duplicate cluster ({duplicatePeers + 1}{" "}
                          related result{duplicatePeers + 1 === 1 ? "" : "s"})
                        </p>
                      ) : null}
                      {onStageSearchMerge ? (
                        <div className="graph-review-existing-object-identity-actions">
                          <button
                            type="button"
                            aria-pressed={selectionRole === "canonical"}
                            onClick={() => {
                              setIdentitySelection((prev) => {
                                const next =
                                  selectionRole === "canonical"
                                    ? clearCanonicalCandidate(prev)
                                    : setCanonicalCandidate(prev, candidate);
                                persistIdentityWorkbenchState(searchPhrase, next);
                                return next;
                              });
                              setStageMergeFeedback("idle");
                            }}
                          >
                            {selectionRole === "canonical"
                              ? "Clear canonical"
                              : "Set as canonical"}
                          </button>
                          <button
                            type="button"
                            aria-pressed={selectionRole === "duplicate"}
                            disabled={selectionRole === "canonical"}
                            onClick={() => {
                              setIdentitySelection((prev) => {
                                const next = toggleDuplicateCandidate(prev, candidate);
                                persistIdentityWorkbenchState(searchPhrase, next);
                                return next;
                              });
                              setStageMergeFeedback("idle");
                            }}
                          >
                            {selectionRole === "duplicate"
                              ? "Clear duplicate"
                              : "Select as duplicate"}
                          </button>
                        </div>
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
                            Link staged in authored overlay. Open{" "}
                            <strong>Stage &amp; commit</strong> to review and
                            prepare.
                          </p>
                        ) : (
                          <p>
                            Links{" "}
                            <strong>{linkSourceNode?.label ?? "recap object"}</strong>{" "}
                            to this existing match as an overlay link_existing
                            draft. This is not the gold whole-graph fixture path.
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
                  );
                })}
              </section>
            ))}
          </div>
        </div>
      ) : null}
    </aside>
  );
}
