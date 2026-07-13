import { useMemo } from "react";

import type { UnionSupergraphProjectionResponse } from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { ReviewCampaignPicker } from "../ReviewCampaignPicker";
import type { RecapProjectionSource } from "./RecapGraphModule";

interface UnionSupergraphRecapProjectionProps {
  payload: UnionSupergraphProjectionResponse;
  selectedSessionId: string;
  onSelectSession: (sessionId: string) => void;
  sessionOptions: string[];
  selectedCampaignId?: string;
  onSelectCampaign?: (campaignId: string) => void;
  onOpenLegacy?: () => void;
  projectionSource?: RecapProjectionSource;
}

export function UnionSupergraphRecapProjection({
  payload,
  selectedSessionId,
  onSelectSession,
  sessionOptions,
  selectedCampaignId = "longmont-c2",
  onSelectCampaign = () => undefined,
  onOpenLegacy,
  projectionSource = "default-preview-source",
}: UnionSupergraphRecapProjectionProps) {
  const paragraphSourceSpans = useMemo(
    () => (payload.source_spans ?? [])
      .filter((span) => span.kind === "paragraph")
      .sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0)),
    [payload.source_spans],
  );
  const sourceCopy = {
    "latest-graph-ingest": {
      label: "latest graph-ingest preview",
      description: "This recap is projected from the latest preview union supergraph for this campaign/session.",
    },
    "recap-only": {
      label: "recap memory only",
      description: "This session has ingested recap memory, but no graph projection is ready yet, so graph chips are unavailable.",
    },
    "default-preview-source": {
      label: "default preview fixture",
      description: "No latest graph-ingest preview store was available for this session, so this is using the default preview source.",
    },
    legacy: {
      label: "legacy recap preview",
      description: "This recap is using the legacy recap preview projection.",
    },
    unavailable: {
      label: "no graph projection available",
      description: "No graph projection is available for this session yet. Generate Recap Memory first, then retry.",
    },
  }[projectionSource];
  const projectedMarkdown = payload.markdown
    ?? "# Session recap projection unavailable\n\nThe union-supergraph payload did not include projected recap Markdown.";


  return (
    <div className="recap-reader-root union-supergraph-recap-root">
      <header className="recap-reader-header">
        <div>
          <p className="plan-surface-kicker">Preview union · session extract</p>
          <h2>Session focus lens</h2>
          <p>
            This view projects the latest <strong>session preview union</strong> for Session{" "}
            {payload.focus.focus_session_id?.replace("session-", "") ?? "?"} — not the campaign-wide
            world supergraph. Chips are alias matches in this recap; prior-session history only appears
            if that memory was merged into this preview store (it usually is not).
          </p>
          <p className="union-supergraph-source-note">
            Source: {sourceCopy.label}. {sourceCopy.description}
          </p>
        </div>
        <span className="union-supergraph-graph-id">{payload.graph_id ?? "union-supergraph"}</span>
      </header>

      <div className="recap-reader-toolbar">
        <ReviewCampaignPicker selectedCampaignId={selectedCampaignId} onSelect={onSelectCampaign} />
        <label className="graph-preview-run-picker">
          <span>Focus session</span>
          <select
            value={selectedSessionId}
            onChange={(event) => onSelectSession(event.target.value)}
          >
            {sessionOptions.map((sessionId) => (
              <option key={sessionId} value={sessionId}>
                {sessionId.replace("session-", "Session ")}
              </option>
            ))}
          </select>
        </label>
        {onOpenLegacy ? (
          <button type="button" className="union-supergraph-legacy-button" onClick={onOpenLegacy}>
            Legacy recap preview
          </button>
        ) : null}
      </div>

      <p className="recap-reader-hint union-supergraph-mentions-hint">
        Read-only TipTap projection of ingested recap Markdown. Editing and corpus writes are intentionally out of
        scope here. Graph chips are preview memory candidates; evidence highlights show the recap paragraph that supports the selected graph context. {payload.mentions.length} graph mention{payload.mentions.length === 1 ? "" : "s"} projected.
      </p>

      <GraphProjectionReader
        markdown={projectedMarkdown}
        nodeViews={payload.node_views}
        sourceSpans={paragraphSourceSpans}
        graphId={payload.graph_id}
        documentLabel="Projected recap"
      />
    </div>
  );
}
