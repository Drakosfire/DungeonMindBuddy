import { useEffect } from "react";

import {
  GraphReviewAuthorNodePanel,
  authorNodeProjectionReady,
} from "./GraphReviewAuthorNodePanel";
import { useGraphReviewLiveState } from "./GraphReviewLiveStateContext";

const LEGACY_AUTHOR_DRAFT_TOOL = "graph-review-author-draft";

export function consumeLegacyAuthorDraftToolQuery(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  if (params.get("tool") !== LEGACY_AUTHOR_DRAFT_TOOL) return false;
  params.delete("tool");
  const query = params.toString();
  const path = window.location.pathname;
  window.history.replaceState({}, "", query ? `${path}?${query}` : path);
  return true;
}

interface GraphReviewAuthorNodeDrawerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRequestLoad?: () => void;
}

export function GraphReviewAuthorNodeDrawer({
  open,
  onOpenChange,
  onRequestLoad,
}: GraphReviewAuthorNodeDrawerProps) {
  const { authorDraft, projectionStatus, projection, liveRun } =
    useGraphReviewLiveState();

  useEffect(() => {
    if (!open) {
      authorDraft.setAuthorMode("review");
      return;
    }
    authorDraft.setAuthorMode("author_draft");
    return () => {
      authorDraft.setAuthorMode("review");
    };
  }, [open, authorDraft.setAuthorMode]);

  useEffect(() => {
    if (!open) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") onOpenChange(false);
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, onOpenChange]);

  useEffect(() => {
    document.body.classList.toggle("graph-review-author-node-open", open);
    return () => document.body.classList.remove("graph-review-author-node-open");
  }, [open]);

  const ready = authorNodeProjectionReady({
    projectionStatus,
    projection,
    liveRun,
  });

  return (
    <div
      className={["graph-review-author-node", open ? "open" : ""].filter(Boolean).join(" ")}
      data-testid="graph-review-author-node"
      data-ready={ready ? "true" : "false"}
    >
      <button
        type="button"
        className="graph-review-author-node-toggle"
        aria-expanded={open}
        aria-controls="graph-review-author-node-drawer"
        title="Author Node"
        onClick={() => onOpenChange(!open)}
      >
        Author Node
      </button>
      <div
        className="graph-review-author-node-backdrop"
        hidden={!open}
        onClick={() => onOpenChange(false)}
        aria-hidden="true"
      />
      <aside
        id="graph-review-author-node-drawer"
        className="graph-review-author-node-drawer"
        aria-label="Author Node"
        aria-hidden={!open}
      >
        <header className="graph-review-author-node-header">
          <div>
            <p className="plan-surface-kicker">Graph Review</p>
            <h2>Author Node</h2>
          </div>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            aria-label="Close Author Node"
          >
            ×
          </button>
        </header>
        <div className="graph-review-author-node-body">
          {open ? <GraphReviewAuthorNodePanel onRequestLoad={onRequestLoad} /> : null}
        </div>
      </aside>
    </div>
  );
}
