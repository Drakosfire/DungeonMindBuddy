import { useEffect, useMemo, useState } from "react";

import { getSourceBundle } from "../../api/liveApi";
import type { IngestionSourceBundle } from "../../api/types";
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

/** Explicit lens controls for surfaces rendered outside PlanGraphLensProvider. */
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
  /**
   * Session focus choices. When omitted, options are loaded from each selected
   * campaign’s ingest source bundle (real sessions only — never invented).
   */
  focusOptions?: PlanGraphLoadFocusOption[];
  /** When false, hide the “select at least one campaign” warning. Default true. */
  showEmptyLensWarning?: boolean;
  /**
   * Optional override when rendered outside PlanGraphLensProvider.
   * Prefer context (Plan Board) when available.
   */
  lensControls?: PlanGraphLoadLensControls | null;
  /** Injectable for tests; defaults to live `getSourceBundle`. */
  loadBundle?: typeof getSourceBundle;
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

function shortCampaignLabel(campaignId: ReviewCampaignId): string {
  return formatReviewCampaignLabel(campaignId).replace(/^Longmont /, "");
}

function numberField(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function focusOptionKey(option: Pick<PlanGraphLoadFocusOption, "campaignId" | "sessionNumber">): string {
  return `${option.campaignId}:${option.sessionNumber}`;
}

function optionsIncludeFocus(
  options: readonly PlanGraphLoadFocusOption[],
  focus: PlanGraphLensFocus | null,
): boolean {
  if (!focus) return false;
  const key = focusOptionKey(focus);
  return options.some((option) => focusOptionKey(option) === key);
}

/** Session numbers present in an ingest source bundle (newest first). */
export function sessionNumbersFromBundle(bundle: IngestionSourceBundle): number[] {
  const sessions = new Set<number>();
  for (const unit of bundle.units ?? []) {
    const session = numberField(unit.fields.sessionNumber);
    if (session !== null) sessions.add(session);
  }
  return Array.from(sessions).sort((a, b) => b - a);
}

export function buildFocusOptionsFromBundles(
  selectedCampaignIds: readonly ReviewCampaignId[],
  bundlesByCampaign: ReadonlyMap<ReviewCampaignId, IngestionSourceBundle>,
): PlanGraphLoadFocusOption[] {
  const options: PlanGraphLoadFocusOption[] = [];
  for (const campaignId of REVIEW_CAMPAIGN_IDS) {
    if (!selectedCampaignIds.includes(campaignId)) continue;
    const bundle = bundlesByCampaign.get(campaignId);
    if (!bundle) continue;
    for (const sessionNumber of sessionNumbersFromBundle(bundle)) {
      options.push({
        campaignId,
        sessionNumber,
        label: `${shortCampaignLabel(campaignId)} · Session ${sessionNumber}`,
      });
    }
  }
  return options;
}

/**
 * World Graph load/lens control for Plan Board (primary) and optional test harnesses.
 * Campaign/focus changes go through PlanGraphLensContext (URL + projection reload).
 */
export function PlanGraphLoadPanel({
  projectionState,
  projectionError = null,
  nodeCount,
  focusOptions,
  showEmptyLensWarning = true,
  lensControls = null,
  loadBundle = getSourceBundle,
}: PlanGraphLoadPanelProps) {
  const fromContext = useOptionalPlanGraphLens();
  const controls = lensControls ?? fromContext;
  const [bundleFocusOptions, setBundleFocusOptions] = useState<PlanGraphLoadFocusOption[]>([]);
  /** True once bundle-derived options have been resolved for the current selection. */
  const [bundleOptionsReady, setBundleOptionsReady] = useState(false);

  const selectedCampaignKey = (controls?.lens.selectedCampaignIds ?? []).join(",");
  const focusKey = controls?.lens.focus
    ? focusOptionKey(controls.lens.focus)
    : "";

  useEffect(() => {
    if (!controls) {
      setBundleFocusOptions([]);
      setBundleOptionsReady(false);
      return;
    }
    // Explicit prop overrides bundle loading (including empty arrays).
    if (focusOptions !== undefined) {
      setBundleFocusOptions([]);
      setBundleOptionsReady(false);
      return;
    }

    const selected = controls.lens.selectedCampaignIds;
    if (selected.length === 0) {
      setBundleFocusOptions([]);
      setBundleOptionsReady(true);
      return;
    }

    let cancelled = false;
    setBundleOptionsReady(false);

    void (async () => {
      const bundles = new Map<ReviewCampaignId, IngestionSourceBundle>();
      await Promise.all(
        selected.map(async (campaignId) => {
          try {
            const bundle = await loadBundle("campaign-ingested", campaignId);
            if (!cancelled) bundles.set(campaignId, bundle);
          } catch {
            // Fail closed per campaign: omit sessions rather than invent them.
          }
        }),
      );
      if (cancelled) return;
      setBundleFocusOptions(buildFocusOptionsFromBundles(selected, bundles));
      setBundleOptionsReady(true);
    })();

    return () => {
      cancelled = true;
    };
  }, [controls, focusOptions, loadBundle, selectedCampaignKey]);

  // After grounded options are known, drop URL/lens focus that is not in the bundle set.
  useEffect(() => {
    if (!controls) return;
    const grounded =
      focusOptions !== undefined ? focusOptions : bundleFocusOptions;
    const optionsReady = focusOptions !== undefined || bundleOptionsReady;
    if (!optionsReady) return;

    const focus = controls.lens.focus;
    if (!focus) return;
    if (optionsIncludeFocus(grounded, focus)) return;
    controls.setFocus(null);
  }, [bundleFocusOptions, bundleOptionsReady, controls, focusKey, focusOptions]);

  const statusLine = useMemo(() => {
    if (!controls) {
      return "Graph lens unavailable";
    }
    return `${controls.summaryLabel} · ${formatProjectionLoadStatus(projectionState, nodeCount, projectionError)}`;
  }, [controls, nodeCount, projectionError, projectionState]);

  const resolvedFocusOptions = useMemo(() => {
    if (!controls) return [] as PlanGraphLoadFocusOption[];
    return focusOptions !== undefined ? focusOptions : bundleFocusOptions;
  }, [bundleFocusOptions, controls, focusOptions]);

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
  const focusSelectValue =
    lens.focus && optionsIncludeFocus(resolvedFocusOptions, lens.focus)
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
    // Only accept focus that is present in the grounded option list.
    if (!optionsIncludeFocus(resolvedFocusOptions, next)) {
      setFocus(null);
      return;
    }
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
          {resolvedFocusOptions.map((option) => (
            <option
              key={focusOptionKey(option)}
              value={focusOptionKey(option)}
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
