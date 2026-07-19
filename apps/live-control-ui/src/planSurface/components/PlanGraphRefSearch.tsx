import { useMemo, useState } from "react";

import type { GraphProjectionNodeView } from "../../api/types";
import type { PlanGraphProjectionState } from "../reference/graphAwareReferenceResolver";
import { runbookReferenceFromGraphNode } from "../reference/runbookReferenceFromGraphNode";
import {
  searchGraphProjectionNodes,
  sortGraphProjectionNodes,
} from "../reference/searchGraphProjectionNodes";
import { formatReviewCampaignLabel } from "../sessionCampaignContext";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";

function nodeCampaignProvenanceLabel(node: GraphProjectionNodeView): string {
  const scope = node.campaign_scope?.trim();
  if (!scope) {
    return "world";
  }
  return formatReviewCampaignLabel(scope);
}

export interface PlanGraphRefSearchProps {
  nodes: GraphProjectionNodeView[];
  projectionState: PlanGraphProjectionState;
  projectionError?: string | null;
  /** Disables chip insert only. Search and view stay available while editing is locked. */
  insertDisabled?: boolean;
  onInsert: (attrs: RunbookReferenceAttrs) => void;
  onView?: (node: GraphProjectionNodeView) => void;
}

export function PlanGraphRefSearch({
  nodes,
  projectionState,
  projectionError = null,
  insertDisabled = false,
  onInsert,
  onView,
}: PlanGraphRefSearchProps) {
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    const matched = sortGraphProjectionNodes(searchGraphProjectionNodes(nodes, query));
    return matched.slice(0, 40);
  }, [nodes, query]);

  return (
    <section
      className="plan-graph-ref-search"
      aria-label="World Graph objects"
      data-testid="plan-graph-ref-search"
    >
      {projectionState === "loading" ? (
        <p className="plan-graph-ref-search__status" role="status">
          Loading World Graph projection…
        </p>
      ) : null}
      {projectionState === "error" ? (
        <p className="plan-graph-ref-search__status plan-graph-ref-search__status--error" role="alert">
          Could not load World Graph{projectionError ? `: ${projectionError}` : "."}
        </p>
      ) : null}
      {projectionState === "unavailable" ? (
        <p className="plan-graph-ref-search__status" role="status">
          World Graph unavailable for this session.
        </p>
      ) : null}

      {projectionState === "ready" ? (
        <>
          <label className="plan-graph-ref-search__label" htmlFor="plan-graph-ref-search-input">
            Find objects
          </label>
          <input
            id="plan-graph-ref-search-input"
            className="plan-graph-ref-search__input"
            type="search"
            value={query}
            placeholder="Tripod, Mireward, npc…"
            autoComplete="off"
            onChange={(event) => setQuery(event.target.value)}
          />
          {insertDisabled ? (
            <p className="plan-graph-ref-search__status" role="status">
              Unlock editing to insert chips into the board. View still works.
            </p>
          ) : null}

          {nodes.length === 0 ? (
            <p className="plan-graph-ref-search__empty">No nodes in the current projection.</p>
          ) : results.length === 0 ? (
            <p className="plan-graph-ref-search__empty">No objects match “{query.trim()}”.</p>
          ) : (
            <ul className="plan-graph-ref-search__results" data-testid="plan-graph-ref-search-results">
              {results.map((node) => (
                <li key={node.node_id} className="plan-graph-ref-search__row">
                  <div className="plan-graph-ref-search__copy">
                    <strong>{node.label}</strong>
                    <span className="plan-graph-ref-search__meta">
                      {node.kind}
                      {node.role ? ` · ${node.role}` : ""}
                      {` · ${nodeCampaignProvenanceLabel(node)}`}
                    </span>
                  </div>
                  <div className="plan-graph-ref-search__actions">
                    {onView ? (
                      <button
                        type="button"
                        className="plan-graph-ref-search__button"
                        onClick={() => onView(node)}
                      >
                        View
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="plan-graph-ref-search__button plan-graph-ref-search__button--primary"
                      disabled={insertDisabled}
                      onClick={() => onInsert(runbookReferenceFromGraphNode(node))}
                    >
                      Insert chip
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : null}
    </section>
  );
}
