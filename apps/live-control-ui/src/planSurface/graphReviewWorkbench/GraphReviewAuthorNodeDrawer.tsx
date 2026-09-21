import { useEffect, useState, type ReactNode } from "react";

import {
  GraphReviewAuthorNodePanel,
  authorNodeProjectionReady,
  type GraphReviewAuthorNodeMode,
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
  mode?: GraphReviewAuthorNodeMode;
  publishedLocalPanel?: ReactNode;
  publishedLocalPreview?: ReactNode;
}

export function GraphReviewAuthorNodeDrawer({
  open,
  onOpenChange,
  onRequestLoad,
  mode = "exact-run",
  publishedLocalPanel,
  publishedLocalPreview,
}: GraphReviewAuthorNodeDrawerProps) {
  if (mode === "published-local") {
    return (
      <GraphReviewPublishedAuthorNodeDrawer
        open={open}
        onOpenChange={onOpenChange}
        publishedLocalPanel={publishedLocalPanel}
        publishedLocalPreview={publishedLocalPreview}
        onRequestLoad={onRequestLoad}
      />
    );
  }

  return (
    <GraphReviewExactAuthorNodeDrawer
      open={open}
      onOpenChange={onOpenChange}
      onRequestLoad={onRequestLoad}
    />
  );
}

function GraphReviewPublishedAuthorNodeDrawer({
  open,
  onOpenChange,
  publishedLocalPanel,
  publishedLocalPreview,
  onRequestLoad,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  publishedLocalPanel?: ReactNode;
  publishedLocalPreview?: ReactNode;
  onRequestLoad?: () => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <GraphReviewAuthorNodeDrawerFrame
      open={open}
      onOpenChange={onOpenChange}
      mode="published-local"
      ready
      expanded={expanded}
      onToggleExpanded={() => setExpanded((current) => !current)}
      preview={publishedLocalPreview}
    >
      <GraphReviewAuthorNodePanel
        mode="published-local"
        publishedLocalPanel={publishedLocalPanel}
        onRequestLoad={onRequestLoad}
      />
    </GraphReviewAuthorNodeDrawerFrame>
  );
}

function GraphReviewExactAuthorNodeDrawer({
  open,
  onOpenChange,
  onRequestLoad,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onRequestLoad?: () => void;
}) {

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
  }, [authorDraft.setAuthorMode, open]);

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
    <GraphReviewAuthorNodeDrawerFrame
      open={open}
      onOpenChange={onOpenChange}
      mode="exact-run"
      ready={ready}
    >
      <GraphReviewAuthorNodePanel onRequestLoad={onRequestLoad} />
    </GraphReviewAuthorNodeDrawerFrame>
  );
}

function GraphReviewAuthorNodeDrawerFrame({
  open,
  onOpenChange,
  mode,
  ready,
  expanded = false,
  onToggleExpanded,
  preview = null,
  children,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: GraphReviewAuthorNodeMode;
  ready: boolean;
  expanded?: boolean;
  onToggleExpanded?: () => void;
  preview?: ReactNode;
  children: ReactNode;
}) {
  return (
    <div
      className={["graph-review-author-node", open ? "open" : ""].filter(Boolean).join(" ")}
      data-testid="graph-review-author-node"
      data-ready={ready ? "true" : "false"}
      data-mode={mode}
      data-expanded={expanded ? "true" : "false"}
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
            <p className="plan-surface-kicker">
              {mode === "published-local" ? "Published recap" : "Graph Review"}
            </p>
            <h2>{mode === "published-local" ? "Author Node · local staging" : "Author Node"}</h2>
          </div>
          <div className="graph-review-author-node-header-actions">
            {onToggleExpanded ? (
              <button
                type="button"
                className="graph-review-author-node-expand-toggle"
                onClick={onToggleExpanded}
                aria-label={expanded ? "Collapse Author Node" : "Expand Author Node"}
                title={expanded ? "Use compact Author Node" : "Expand Author Node"}
              >
                {expanded ? "⇥" : "⇤"}
              </button>
            ) : null}
            <button
              type="button"
              onClick={() => onOpenChange(false)}
              aria-label="Close Author Node"
            >
              ×
            </button>
          </div>
        </header>
        {mode === "published-local" && preview ? (
          <div className="graph-review-author-node-preview">{preview}</div>
        ) : null}
        <div className="graph-review-author-node-body">
          {open || mode === "published-local" ? children : null}
        </div>
      </aside>
    </div>
  );
}
