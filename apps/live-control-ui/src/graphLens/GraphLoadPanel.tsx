import { useMemo } from "react";

import type { PlanGraphProjectionState } from "../planSurface/reference/graphAwareReferenceResolver";
import { useOptionalPlanGraphLens } from "./WorldGraphLensContext";
import "./graphLens.css";
import {
  focusOptionKey,
  optionsIncludeFocus,
  type PlanGraphFocusValidationStatus,
  type PlanGraphLoadFocusOption,
} from "./planGraphFocusOptions";
import {
  REVIEW_CAMPAIGN_IDS,
  formatReviewCampaignLabel,
  type DerivedPlanGraphApiLens,
  type PlanGraphLens,
  type PlanGraphLensFocus,
  type ReviewCampaignId,
} from "./sessionCampaignContext";

export type { PlanGraphLoadFocusOption } from "./planGraphFocusOptions";
export {
  buildFocusOptionsFromBundles,
  sessionNumbersFromBundle,
} from "./planGraphFocusOptions";

/** Explicit lens controls for surfaces rendered outside PlanGraphLensProvider. */
export interface PlanGraphLoadLensControls {
  lens: PlanGraphLens;
  derived: DerivedPlanGraphApiLens | null;
  summaryLabel: string;
  focusOptions: PlanGraphLoadFocusOption[];
  focusValidationStatus: PlanGraphFocusValidationStatus;
  toggleCampaign: (campaignId: ReviewCampaignId) => void;
  setFocus: (focus: PlanGraphLensFocus | null) => void;
  retryFocusValidation: () => void;
  acceptUnverifiedFocus: () => void;
}

export interface PlanGraphLoadPanelProps {
  projectionState: PlanGraphProjectionState;
  projectionError?: string | null;
  nodeCount: number;
  /** When false, hide the “select at least one campaign” warning. Default true. */
  showEmptyLensWarning?: boolean;
  /**
   * Optional override when rendered outside PlanGraphLensProvider.
   * Prefer context (Plan Board) when available.
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

function formatLensStatusLine(
  summaryLabel: string,
  focusValidationStatus: PlanGraphFocusValidationStatus,
  projectionState: PlanGraphProjectionState,
  nodeCount: number,
  projectionError: string | null | undefined,
): string {
  const projectionPart = formatProjectionLoadStatus(
    projectionState,
    nodeCount,
    projectionError,
  );
  if (focusValidationStatus === "pending") {
    return `${summaryLabel} · validating focus · ${projectionPart}`;
  }
  if (focusValidationStatus === "unavailable") {
    return `${summaryLabel} · focus validation unavailable · gated`;
  }
  return `${summaryLabel} · ${projectionPart}`;
}

function shortCampaignLabel(campaignId: ReviewCampaignId): string {
  return formatReviewCampaignLabel(campaignId).replace(/^Longmont /, "");
}

/**
 * World Graph load/lens control for Plan Board (primary) and optional test harnesses.
 * Campaign/focus changes go through PlanGraphLensContext (URL + projection reload).
 * Focus options and validation are owned by the lens provider (shared with Ask + resolver).
 */
export function PlanGraphLoadPanel({
  projectionState,
  projectionError = null,
  nodeCount,
  showEmptyLensWarning = true,
  lensControls = null,
}: PlanGraphLoadPanelProps) {
  const fromContext = useOptionalPlanGraphLens();
  const controls = lensControls ?? fromContext;

  const statusLine = useMemo(() => {
    if (!controls) {
      return "Graph lens unavailable";
    }
    return formatLensStatusLine(
      controls.summaryLabel,
      controls.focusValidationStatus,
      projectionState,
      nodeCount,
      projectionError,
    );
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

  const {
    lens,
    derived,
    toggleCampaign,
    setFocus,
    focusOptions,
    focusValidationStatus,
    retryFocusValidation,
    acceptUnverifiedFocus,
  } = controls;

  const heldFocusOption =
    lens.focus && !optionsIncludeFocus(focusOptions, lens.focus)
      ? {
          campaignId: lens.focus.campaignId,
          sessionNumber: lens.focus.sessionNumber,
          label:
            focusValidationStatus === "unavailable"
              ? `${shortCampaignLabel(lens.focus.campaignId)} · Session ${lens.focus.sessionNumber} (unverified)`
              : `${shortCampaignLabel(lens.focus.campaignId)} · Session ${lens.focus.sessionNumber} (accepted unverified)`,
        }
      : null;

  const selectOptions =
    heldFocusOption && !optionsIncludeFocus(focusOptions, lens.focus)
      ? [heldFocusOption, ...focusOptions]
      : focusOptions;

  const focusSelectValue =
    lens.focus && optionsIncludeFocus(selectOptions, lens.focus)
      ? focusOptionKey(lens.focus)
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
    if (optionsIncludeFocus(focusOptions, next)) {
      setFocus(next);
      return;
    }
    // Held / accepted-unverified option: keep selection; unlock via Clear or grounded pick.
    if (
      lens.focus
      && next.campaignId === lens.focus.campaignId
      && next.sessionNumber === lens.focus.sessionNumber
    ) {
      return;
    }
    setFocus(null);
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
          {selectOptions.map((option) => (
            <option
              key={focusOptionKey(option)}
              value={focusOptionKey(option)}
            >
              {option.label}
            </option>
          ))}
        </select>
      </label>
      {focusValidationStatus === "unavailable" ? (
        <div
          className="plan-graph-load-panel__validation"
          role="status"
          data-testid="plan-graph-focus-validation-unavailable"
        >
          <p className="plan-graph-load-panel__warning">
            Session focus could not be validated (ingest bundle unavailable). Projection and Ask stay gated until you retry, clear focus, or explicitly use the unverified focus.
          </p>
          <div className="plan-graph-load-panel__validation-actions">
            <button type="button" onClick={() => retryFocusValidation()}>
              Retry validation
            </button>
            <button type="button" onClick={() => setFocus(null)}>
              Clear focus
            </button>
            <button type="button" onClick={() => acceptUnverifiedFocus()}>
              Use focus anyway
            </button>
          </div>
        </div>
      ) : null}
      {showEmptyLensWarning && derived == null ? (
        <p className="plan-graph-load-panel__warning" role="status">
          Select at least one campaign.
        </p>
      ) : null}
    </div>
  );
}

/** Alias for neutral graph-lens surfaces. */
export const GraphLoadPanel = PlanGraphLoadPanel;
