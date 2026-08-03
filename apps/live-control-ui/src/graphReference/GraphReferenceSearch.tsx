import { useEffect, useMemo, useState } from "react";

import type { GraphReferenceProjectionState, GraphReferenceSearchItem } from "./types";
import { searchGraphReferences, sortGraphReferenceItems } from "./searchGraphReferences";
import type { RunbookReferenceAttrs } from "../tiptap/references/runbookReferences";

export interface GraphReferenceSearchProps {
  items: GraphReferenceSearchItem[];
  projectionState: GraphReferenceProjectionState;
  projectionError?: string | null;
  /** Disables chip insert only. Search and view stay available while editing is locked. */
  insertDisabled?: boolean;
  /** Seeds the search field when opened from another Build surface action. */
  initialQuery?: string;
  onInsert: (attrs: RunbookReferenceAttrs) => void;
  onView?: (item: GraphReferenceSearchItem) => void;
}

export function GraphReferenceSearch({
  items,
  projectionState,
  projectionError = null,
  insertDisabled = false,
  initialQuery = "",
  onInsert,
  onView,
}: GraphReferenceSearchProps) {
  const [query, setQuery] = useState(initialQuery);

  useEffect(() => {
    setQuery(initialQuery);
  }, [initialQuery]);

  const results = useMemo(() => {
    const matched = sortGraphReferenceItems(searchGraphReferences(items, query));
    return matched.slice(0, 40);
  }, [items, query]);

  return (
    <section
      className="graph-reference-search"
      aria-label="World Graph objects"
      data-testid="graph-reference-search"
    >
      {projectionState === "loading" ? (
        <p className="graph-reference-search__status" role="status">
          Loading…
        </p>
      ) : null}
      {projectionState === "error" ? (
        <p className="graph-reference-search__status graph-reference-search__status--error" role="alert">
          Could not load World Graph{projectionError ? `: ${projectionError}` : "."}
        </p>
      ) : null}
      {projectionState === "unavailable" ? (
        <p className="graph-reference-search__status" role="status">
          World Graph unavailable.
        </p>
      ) : null}

      {projectionState === "ready" ? (
        <>
          <label className="graph-reference-search__label" htmlFor="graph-reference-search-input">
            Find objects
          </label>
          <input
            id="graph-reference-search-input"
            className="graph-reference-search__input"
            type="search"
            value={query}
            placeholder="Tripod, Mireward, npc…"
            autoComplete="off"
            onChange={(event) => setQuery(event.target.value)}
          />
          {insertDisabled ? (
            <p className="graph-reference-search__status" role="status">
              Unlock editing to insert chips into the board. View still works.
            </p>
          ) : null}

          {items.length === 0 ? (
            <p className="graph-reference-search__empty">No nodes in the current projection.</p>
          ) : results.length === 0 ? (
            <p className="graph-reference-search__empty">No objects match “{query.trim()}”.</p>
          ) : (
            <ul className="graph-reference-search__results" data-testid="graph-reference-search-results">
              {results.map((item) => (
                <li key={item.nodeId} className="graph-reference-search__row">
                  <div className="graph-reference-search__copy">
                    <strong>{item.label}</strong>
                    <span className="graph-reference-search__meta">
                      {item.kind}
                      {item.role ? ` · ${item.role}` : ""}
                      {` · ${item.scopeLabel}`}
                    </span>
                  </div>
                  <div className="graph-reference-search__actions">
                    {onView ? (
                      <button
                        type="button"
                        className="graph-reference-search__button"
                        onClick={() => onView(item)}
                      >
                        View
                      </button>
                    ) : null}
                    <button
                      type="button"
                      className="graph-reference-search__button graph-reference-search__button--primary"
                      disabled={insertDisabled}
                      onClick={() => onInsert(item.reference)}
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
