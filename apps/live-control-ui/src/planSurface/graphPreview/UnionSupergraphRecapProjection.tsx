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
  projectionSource = "world-graph",
}: UnionSupergraphRecapProjectionProps) {
  const paragraphSourceSpans = useMemo(
    () => (payload.source_spans ?? [])
      .filter((span) => span.kind === "paragraph")
      .sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0)),
    [payload.source_spans],
  );
  const sourceCopy = {
    "world-graph": {
      label: "World Graph head",
      description:
        "This recap is projected from the persistent World Graph with a session focus lens. Chips resolve to durable world identities; prior-session evidence appears when present on those identities.",
    },
    "recap-only": {
      label: "recap memory only",
      description: "This session has ingested recap memory, but no graph projection is ready yet, so graph chips are unavailable.",
    },
    "default-preview-source": {
      label: "default preview fixture",
      description: "No World Graph recap projection was available for this session, so this is using the default preview source.",
    },
    legacy: {
      label: "legacy recap preview",
      description: "This recap is using the legacy recap preview projection.",
    },
    unavailable: {
      label: "no graph projection available",
      description: "No graph projection is available for this session yet. Ensure the World Graph head and normalized recap exist, then retry.",
    },
  }[projectionSource];
  const projectedMarkdown = payload.markdown
    ?? "# Session recap projection unavailable\n\nThe World Graph recap payload did not include projected recap Markdown.";

  const isWorldGraph = projectionSource === "world-graph";

  return (
    <div className="recap-reader-root union-supergraph-recap-root">
      <header className="recap-reader-header">
        <div>
          <p className="plan-surface-kicker">
            {isWorldGraph ? "World Graph · session focus lens" : "Recap projection"}
          </p>
          <h2>Session focus lens</h2>
          <p>
            {isWorldGraph ? (
              <>
                This view projects the persistent <strong>World Graph</strong> with Session{" "}
                {payload.focus.focus_session_id?.replace("session-", "") ?? "?"} as the focus
                lens. Chips are alias matches against durable world identities; adjacency and
                evidence can span prior sessions when those assertions live on the world head.
              </>
            ) : (
              <>
                This view projects Session{" "}
                {payload.focus.focus_session_id?.replace("session-", "") ?? "?"}. Graph chips
                resolve when a projection source is available.
              </>
            )}
          </p>
          <p className="union-supergraph-source-note">
            Source: {sourceCopy.label}. {sourceCopy.description}
          </p>
        </div>
        <span className="union-supergraph-graph-id">{payload.graph_id ?? "world-graph"}</span>
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
        scope here. Graph chips resolve to World Graph identities; evidence highlights show the recap paragraph that
        supports the selected graph context. {payload.mentions.length} graph mention
        {payload.mentions.length === 1 ? "" : "s"} projected.
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
