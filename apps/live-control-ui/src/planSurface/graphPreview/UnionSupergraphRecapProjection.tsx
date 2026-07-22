import { useCallback, useMemo } from "react";

import type { UnionSupergraphProjectionResponse } from "../../api/types";
import { GraphProjectionReader } from "../graphProjectionReader/GraphProjectionReader";
import { useProjection } from "../projection/projectionContext";
import { openGraphNodeFromChip } from "../reference/openGraphNodeFromChip";
import { planReferenceResolutionFromNodeView } from "../reference/planReferenceResolutionFromNodeView";
import { usePlanGraphReferenceResolver } from "../reference/usePlanGraphReferenceResolver";
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
  /** When embedded (Graph Review post-merge), hide Recap session/campaign pickers. */
  chrome?: "full" | "embedded";
}

function sessionLabel(sessionId: string | null | undefined): string {
  const raw = (sessionId ?? "").trim();
  if (!raw) return "Session";
  return raw.replace(/^session-/i, "Session ");
}

/** Drop a leading `# Session N` that only repeats chrome already shown in the workbench header. */
export function stripLeadingSessionHeading(
  markdown: string,
  sessionId: string | null | undefined,
): string {
  const label = sessionLabel(sessionId);
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const pattern = new RegExp(`^\\s*#\\s*${escaped}\\s*(?:\\n+|$)`, "i");
  return markdown.replace(pattern, "").replace(/^\s+/, "");
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
  chrome = "full",
}: UnionSupergraphRecapProjectionProps) {
  const { openContentFromChip } = useProjection();
  const { resolvePlanReference, projectionState } = usePlanGraphReferenceResolver();

  const paragraphSourceSpans = useMemo(
    () => (payload.source_spans ?? [])
      .filter((span) => span.kind === "paragraph")
      .sort((a, b) => (a.ordinal ?? 0) - (b.ordinal ?? 0)),
    [payload.source_spans],
  );

  const handleInspectNode = useCallback(
    (nodeId: string) => {
      const nodeView = payload.node_views[nodeId];
      const label = nodeView?.label ?? nodeId;
      if (nodeView) {
        const { ref, resolution } = planReferenceResolutionFromNodeView(nodeView, label);
        openContentFromChip(ref, resolution, true, "ready");
        return;
      }
      void openGraphNodeFromChip(
        nodeId,
        {
          resolvePlanReference,
          openContentFromChip,
          projectionState,
        },
        label,
      );
    },
    [openContentFromChip, payload.node_views, projectionState, resolvePlanReference],
  );

  const focusSessionLabel = sessionLabel(
    payload.focus.focus_session_id ?? selectedSessionId,
  );
  const rawMarkdown = payload.markdown
    ?? `# ${focusSessionLabel}\n\nNo recap text is available for this session yet.`;
  const projectedMarkdown =
    chrome === "embedded"
      ? stripLeadingSessionHeading(
          rawMarkdown,
          payload.focus.focus_session_id ?? selectedSessionId,
        )
      : rawMarkdown;

  const statusNote =
    projectionSource === "unavailable"
      ? "No linked memory for this session yet."
      : projectionSource === "recap-only"
        ? "Recap text only — linked names are not ready yet."
        : null;

  return (
    <div className="recap-reader-root union-supergraph-recap-root">
      {chrome === "full" ? (
        <>
          <header className="recap-reader-header">
            <div>
              <p className="plan-surface-kicker">Recap</p>
              <h2>{focusSessionLabel}</h2>
              {statusNote ? (
                <p className="union-supergraph-source-note">{statusNote}</p>
              ) : (
                <p>Click a highlighted name to open it in memory.</p>
              )}
            </div>
          </header>
          <div className="recap-reader-toolbar">
            <ReviewCampaignPicker selectedCampaignId={selectedCampaignId} onSelect={onSelectCampaign} />
            <label className="graph-preview-run-picker">
              <span>Session</span>
              <select
                value={selectedSessionId}
                onChange={(event) => onSelectSession(event.target.value)}
              >
                {sessionOptions.map((sessionId) => (
                  <option key={sessionId} value={sessionId}>
                    {sessionLabel(sessionId)}
                  </option>
                ))}
              </select>
            </label>
            {onOpenLegacy ? (
              <button type="button" className="union-supergraph-legacy-button" onClick={onOpenLegacy}>
                Older preview
              </button>
            ) : null}
          </div>
        </>
      ) : null}

      <GraphProjectionReader
        markdown={projectedMarkdown}
        nodeViews={payload.node_views}
        sourceSpans={paragraphSourceSpans}
        documentLabel={`${focusSessionLabel} recap`}
        onInspectNode={handleInspectNode}
      />
    </div>
  );
}
