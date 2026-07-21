import { useMemo } from "react";

import type { PlanGraphProjectionState } from "../reference/graphAwareReferenceResolver";
import { useOptionalPlanGraphLens } from "../PlanGraphLensContext";
import {
  REVIEW_CAMPAIGN_IDS,
  formatReviewCampaignLabel,
  type DerivedPlanGraphApiLens,
  type PlanGraphLens,
  type PlanGraphLensFocus,
  type ReviewCampaignId,
} from "../sessionCampaignContext";

export interface PlanGraphLoadFocusOption {
  campaignId: ReviewCampaignId;
  sessionNumber: number;
  label: string;
}

/** Explicit lens controls for surfaces rendered outside PlanGraphLensProvider (Edit chrome). */
export interface PlanGraphLoadLensControls {
  lens: PlanGraphLens;
  derived: DerivedPlanGraphApiLens | null;
  summaryLabel: string;
  toggleCampaign: (campaignId: ReviewCampaignId) => void;
  setFocus: (focus: PlanGraphLensFocus | null) => void;
}

export interface PlanGraphLoadPanelProps {
  projectionState: PlanGraphProjectionState;
  projectionError?: string | null;
  nodeCount: number;
  /** Session focus choices; Edit may pass [] when no ingest bundle is loaded. */
  focusOptions?: PlanGraphLoadFocusOption[];
  /** When false, hide the “select at least one campaign” warning. Default true. */
  showEmptyLensWarning?: boolean;
  /**
   * Required when this panel is rendered outside PlanGraphLensProvider
   * (AppChrome Edit tools). Inside the provider (Ask Config), omit and use context.
   */
  lensControls?: PlanGraphLoadLensControls | null;
}

function formatProjectionLoadStatus(
  projectionState: PlanGraphProjectionState,
  nodeCount: number,
  projectionError: string | null | undefined,
): string {
  if (projectionState === "loading") {
    return "Loading…";
  }
  if (projectionState === "error") {
    return projectionError?.trim()
      ? `error: ${projectionError.trim()}`
      : "error";
  }
  if (projectionState === "unavailable") {
    return "unavailable";
  }
  return `${nodeCount} node${nodeCount === 1 ? "" : "s"} · ready`;
}

/**
 * Shared World Graph load/lens control for Edit → World Graph objects and Ask → Config.
 * Campaign/focus changes go through PlanGraphLensContext (URL + projection reload).
 */
export function PlanGraphLoadPanel({
  projectionState,
  projectionError = null,
  nodeCount,
  focusOptions = [],
  showEmptyLensWarning = true,
  lensControls = null,
}: PlanGraphLoadPanelProps) {
  const fromContext = useOptionalPlanGraphLens();
  const controls = lensControls ?? fromContext;

  const statusLine = useMemo(() => {
    if (!controls) {
      return formatProjectionLoadStatus(projectionState, nodeCount, projectionError);
    }
    return `${controls.summaryLabel} · ${formatProjectionLoadStatus(projectionState, nodeCount, projectionError)}`;
  }, [controls, nodeCount, projectionError, projectionState]);

  if (!controls) {
    return (
      <div
        className="plan-graph-load-panel"
        aria-label="World Graph load"
        data-testid="plan-graph-load-panel"
      >
        <p className="plan-graph-load-panel__status" role="status" data-testid="plan-graph-load-status">
          {statusLine}
        </p>
      </div>
    );
  }

  const { lens, derived, toggleCampaign, setFocus } = controls;
  const focusSelectValue = lens.focus
    ? `${lens.focus.campaignId}:${lens.focus.sessionNumber}`
    : "";

  function applyFocusFromSelect(value: string) {
    if (!value) {
      setFocus(null);
      return;
    }
    const [campaignId, sessionRaw] = value.split(":");
    const sessionNumber = Number.parseInt(sessionRaw ?? "", 10);
    if (
      !REVIEW_CAMPAIGN_IDS.includes(campaignId as ReviewCampaignId)
      || !Number.isFinite(sessionNumber)
    ) {
      setFocus(null);
      return;
    }
    const next: PlanGraphLensFocus = {
      campaignId: campaignId as ReviewCampaignId,
      sessionNumber,
    };
    setFocus(next);
  }

  return (
    <div
      className="plan-graph-load-panel"
      aria-label="World Graph load"
      data-testid="plan-graph-load-panel"
    >
      <p className="plan-graph-load-panel__status" role="status" data-testid="plan-graph-load-status">
        {statusLine}
      </p>
      <p className="plan-graph-load-panel__label">Graph campaigns</p>
      <div className="plan-graph-load-panel__campaigns">
        {REVIEW_CAMPAIGN_IDS.map((campaignId) => {
          const checked = lens.selectedCampaignIds.includes(campaignId);
          return (
            <label key={campaignId} className="plan-graph-load-panel__campaign">
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggleCampaign(campaignId)}
              />
              <span>{formatReviewCampaignLabel(campaignId)}</span>
            </label>
          );
        })}
      </div>
      <label className="plan-graph-load-panel__focus">
        <span>Focus session</span>
        <select
          value={focusSelectValue}
          onChange={(event) => applyFocusFromSelect(event.currentTarget.value)}
          disabled={lens.selectedCampaignIds.length === 0}
          aria-label="Focus session"
        >
          <option value="">None (plain union)</option>
          {focusOptions.map((option) => (
            <option
              key={`${option.campaignId}:${option.sessionNumber}`}
              value={`${option.campaignId}:${option.sessionNumber}`}
            >
              {option.label}
            </option>
          ))}
        </select>
      </label>
      {showEmptyLensWarning && derived == null ? (
        <p className="plan-graph-load-panel__warning" role="status">
          Select at least one campaign.
        </p>
      ) : null}
    </div>
  );
}
