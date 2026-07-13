import { useMemo, useState } from "react";

import type { GraphProjectionNodeView } from "../../api/types";
import type { PlanGraphProjectionState } from "../reference/graphAwareReferenceResolver";
import { runbookReferenceFromGraphNode } from "../reference/runbookReferenceFromGraphNode";
import {
  searchGraphProjectionNodes,
  sortGraphProjectionNodes,
} from "../reference/searchGraphProjectionNodes";
import type { RunbookReferenceAttrs } from "../../tiptap/references/runbookReferences";

export interface PlanGraphRefSearchProps {
  nodes: GraphProjectionNodeView[];
  projectionState: PlanGraphProjectionState;
  projectionError?: string | null;
  disabled?: boolean;
  onInsert: (attrs: RunbookReferenceAttrs) => void;
  onView?: (node: GraphProjectionNodeView) => void;
}

export function PlanGraphRefSearch({
  nodes,
  projectionState,
  projectionError = null,
  disabled = false,
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
      aria-label="Search graph objects"
      data-testid="plan-graph-ref-search"
    >
      <header className="plan-graph-ref-search__header">
        <h3 className="plan-graph-ref-search__title">Search graph objects</h3>
        <p className="plan-graph-ref-search__subtitle">
          Find World Graph nodes by label, alias, kind, or id — not the old sample ref list.
        </p>
      </header>

      {projectionState === "loading" ? (
        <p className="plan-graph-ref-search__status" role="status">
          Loading graph projection…
        </p>
      ) : null}
      {projectionState === "error" ? (
        <p className="plan-graph-ref-search__status plan-graph-ref-search__status--error" role="alert">
          Could not load graph projection{projectionError ? `: ${projectionError}` : "."}
        </p>
      ) : null}
      {projectionState === "unavailable" ? (
        <p className="plan-graph-ref-search__status" role="status">
          Graph projection unavailable for this session.
        </p>
      ) : null}

      {projectionState === "ready" ? (
        <>
          <label className="plan-graph-ref-search__label" htmlFor="plan-graph-ref-search-input">
            Search
          </label>
          <input
            id="plan-graph-ref-search-input"
            className="plan-graph-ref-search__input"
            type="search"
            value={query}
            placeholder="e.g. Glowkindle, inn, quest…"
            disabled={disabled}
            onChange={(event) => setQuery(event.target.value)}
          />

          {nodes.length === 0 ? (
            <p className="plan-graph-ref-search__empty">No nodes in the current projection.</p>
          ) : results.length === 0 ? (
            <p className="plan-graph-ref-search__empty">No graph objects match “{query.trim()}”.</p>
          ) : (
            <ul className="plan-graph-ref-search__results" data-testid="plan-graph-ref-search-results">
              {results.map((node) => (
                <li key={node.node_id} className="plan-graph-ref-search__row">
                  <div className="plan-graph-ref-search__copy">
                    <strong>{node.label}</strong>
                    <span className="plan-graph-ref-search__meta">
                      {node.kind}
                      {node.role ? ` · ${node.role}` : ""}
                    </span>
                  </div>
                  <div className="plan-graph-ref-search__actions">
                    {onView ? (
                      <button
                        type="button"
                        className="plan-graph-ref-search__button"
                        disabled={disabled}
                        onClick={() => onView(node)}
                      >
                        View
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="plan-graph-ref-search__button plan-graph-ref-search__button--primary"
                      disabled={disabled}
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
