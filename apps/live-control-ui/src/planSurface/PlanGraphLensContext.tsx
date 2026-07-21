import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";

import { getSourceBundle } from "../api/liveApi";
import type { IngestionSourceBundle } from "../api/types";
import {
  buildFocusOptionsFromBundles,
  isFocusValidationBlocking,
  optionsIncludeFocus,
  type PlanGraphFocusValidationStatus,
  type PlanGraphLoadFocusOption,
} from "./planGraphFocusOptions";
import {
  REVIEW_CAMPAIGN_IDS,
  deriveApiLens,
  formatPlanGraphLensSummary,
  isReviewCampaignId,
  resolvePlanGraphLens,
  syncPlanGraphLensUrl,
  type DerivedPlanGraphApiLens,
  type PlanGraphLens,
  type PlanGraphLensFocus,
  type ReviewCampaignId,
} from "./sessionCampaignContext";

interface PlanGraphLensContextValue {
  lens: PlanGraphLens;
  derived: DerivedPlanGraphApiLens | null;
  summaryLabel: string;
  /** Grounded Focus session options from ingest bundles (or test override). */
  focusOptions: PlanGraphLoadFocusOption[];
  /**
   * Shared gate for projection + Ask:
   * - none: no focus to validate
   * - pending: focus present, bundles still loading
   * - valid: focus confirmed in a successful bundle (or operator override)
   * - invalid: focus absent from successful bundles (cleared next)
   * - unavailable: focused campaign bundle failed; URL focus kept, backend gated
   */
  focusValidationStatus: PlanGraphFocusValidationStatus;
  setSelectedCampaignIds: (ids: ReviewCampaignId[]) => void;
  toggleCampaign: (campaignId: ReviewCampaignId) => void;
  setFocus: (focus: PlanGraphLensFocus | null) => void;
  /** Re-fetch ingest bundles and re-validate the retained URL focus. */
  retryFocusValidation: () => void;
  /**
   * Intentional operator override: accept the retained URL focus without a
   * successful bundle ground truth (unblocks projection + Ask).
   */
  acceptUnverifiedFocus: () => void;
}

const PlanGraphLensContext = createContext<PlanGraphLensContextValue | null>(null);

interface PlanGraphLensProviderProps {
  planCampaignId: string;
  children: ReactNode;
  /** Injectable for tests; defaults to live `getSourceBundle`. */
  loadBundle?: typeof getSourceBundle;
  /**
   * Test override: skip network and use these options immediately.
   * When set (including `[]`), bundle loading is skipped.
   */
  focusOptions?: PlanGraphLoadFocusOption[];
}

function sortCampaignIds(ids: readonly ReviewCampaignId[]): ReviewCampaignId[] {
  return REVIEW_CAMPAIGN_IDS.filter((id) => ids.includes(id));
}

interface BundleLoadState {
  ready: boolean;
  loadedCampaignIds: readonly ReviewCampaignId[];
  failedCampaignIds: readonly ReviewCampaignId[];
}

const BUNDLE_LOAD_IDLE: BundleLoadState = {
  ready: false,
  loadedCampaignIds: [],
  failedCampaignIds: [],
};

export function PlanGraphLensProvider({
  planCampaignId,
  children,
  loadBundle = getSourceBundle,
  focusOptions: focusOptionsOverride,
}: PlanGraphLensProviderProps) {
  const [lens, setLens] = useState<PlanGraphLens>(() =>
    resolvePlanGraphLens(
      planCampaignId,
      typeof window !== "undefined" ? window.location.search : "",
    ),
  );
  const [focusOptions, setFocusOptions] = useState<PlanGraphLoadFocusOption[]>(
    () => focusOptionsOverride ?? [],
  );
  const [bundleLoadState, setBundleLoadState] = useState<BundleLoadState>(() =>
    focusOptionsOverride !== undefined
      ? {
          ready: true,
          loadedCampaignIds: sortCampaignIds(
            (focusOptionsOverride ?? []).map((option) => option.campaignId),
          ),
          failedCampaignIds: [],
        }
      : BUNDLE_LOAD_IDLE,
  );
  const [focusValidationStatus, setFocusValidationStatus] =
    useState<PlanGraphFocusValidationStatus>(() => (lens.focus ? "pending" : "none"));
  const [bundleReloadToken, setBundleReloadToken] = useState(0);
  /** Operator accepted unverified URL focus during a bundle outage. */
  const unverifiedFocusAcceptedRef = useRef(false);

  const selectedCampaignKey = lens.selectedCampaignIds.join(",");
  const focusKey = lens.focus
    ? `${lens.focus.campaignId}:${lens.focus.sessionNumber}`
    : "";

  const setSelectedCampaignIds = useCallback(
    (ids: ReviewCampaignId[]) => {
      unverifiedFocusAcceptedRef.current = false;
      setLens((previous) => {
        const next: PlanGraphLens = {
          selectedCampaignIds: sortCampaignIds(ids),
          focus:
            previous.focus && ids.includes(previous.focus.campaignId)
              ? previous.focus
              : null,
        };
        syncPlanGraphLensUrl(next);
        return next;
      });
    },
    [],
  );

  const toggleCampaign = useCallback((campaignId: ReviewCampaignId) => {
    unverifiedFocusAcceptedRef.current = false;
    setLens((previous) => {
      const selected = new Set(previous.selectedCampaignIds);
      if (selected.has(campaignId)) {
        selected.delete(campaignId);
      } else {
        selected.add(campaignId);
      }
      const selectedCampaignIds = sortCampaignIds([...selected]);
      const next: PlanGraphLens = {
        selectedCampaignIds,
        focus:
          previous.focus && selectedCampaignIds.includes(previous.focus.campaignId)
            ? previous.focus
            : null,
      };
      syncPlanGraphLensUrl(next);
      return next;
    });
  }, []);

  const setFocus = useCallback((focus: PlanGraphLensFocus | null) => {
    unverifiedFocusAcceptedRef.current = false;
    setLens((previous) => {
      const next: PlanGraphLens = {
        selectedCampaignIds: previous.selectedCampaignIds,
        focus:
          focus && previous.selectedCampaignIds.includes(focus.campaignId) ? focus : null,
      };
      syncPlanGraphLensUrl(next);
      return next;
    });
    // User-driven focus changes are grounded picks or intentional clear (override).
    setFocusValidationStatus(focus ? "valid" : "none");
  }, []);

  const retryFocusValidation = useCallback(() => {
    unverifiedFocusAcceptedRef.current = false;
    setFocusValidationStatus((previous) =>
      previous === "none" ? "none" : "pending",
    );
    setBundleReloadToken((token) => token + 1);
  }, []);

  const acceptUnverifiedFocus = useCallback(() => {
    if (!lens.focus) return;
    unverifiedFocusAcceptedRef.current = true;
    setFocusValidationStatus("valid");
  }, [lens.focus]);

  // Load grounded focus options for the selected campaigns.
  useEffect(() => {
    if (focusOptionsOverride !== undefined) {
      setFocusOptions(focusOptionsOverride);
      setBundleLoadState({
        ready: true,
        loadedCampaignIds: sortCampaignIds(
          focusOptionsOverride.map((option) => option.campaignId),
        ),
        failedCampaignIds: [],
      });
      return;
    }

    const selected = lens.selectedCampaignIds;
    if (selected.length === 0) {
      setFocusOptions([]);
      setBundleLoadState({
        ready: true,
        loadedCampaignIds: [],
        failedCampaignIds: [],
      });
      return;
    }

    let cancelled = false;
    setBundleLoadState(BUNDLE_LOAD_IDLE);

    void (async () => {
      const bundles = new Map<ReviewCampaignId, IngestionSourceBundle>();
      const failedCampaignIds: ReviewCampaignId[] = [];
      await Promise.all(
        selected.map(async (campaignId) => {
          try {
            const bundle = await loadBundle("campaign-ingested", campaignId);
            if (!cancelled) bundles.set(campaignId, bundle);
          } catch {
            if (!cancelled) failedCampaignIds.push(campaignId);
          }
        }),
      );
      if (cancelled) return;
      setFocusOptions(buildFocusOptionsFromBundles(selected, bundles));
      setBundleLoadState({
        ready: true,
        loadedCampaignIds: [...bundles.keys()],
        failedCampaignIds,
      });
    })();

    return () => {
      cancelled = true;
    };
  }, [
    bundleReloadToken,
    focusOptionsOverride,
    loadBundle,
    selectedCampaignKey,
    lens.selectedCampaignIds,
  ]);

  // Validate active focus against grounded options once bundles resolve.
  useEffect(() => {
    if (!bundleLoadState.ready) {
      setFocusValidationStatus(lens.focus ? "pending" : "none");
      return;
    }

    const focus = lens.focus;
    if (!focus) {
      setFocusValidationStatus("none");
      return;
    }

    const focusCampaignFailed =
      bundleLoadState.failedCampaignIds.includes(focus.campaignId)
      && !bundleLoadState.loadedCampaignIds.includes(focus.campaignId);

    // Transient API failure: keep URL focus; stay gated unless operator overrides.
    if (focusCampaignFailed) {
      if (unverifiedFocusAcceptedRef.current) {
        setFocusValidationStatus("valid");
        return;
      }
      setFocusValidationStatus("unavailable");
      return;
    }

    if (optionsIncludeFocus(focusOptions, focus)) {
      unverifiedFocusAcceptedRef.current = false;
      setFocusValidationStatus("valid");
      return;
    }

    // Successful bundle(s) for the focus campaign genuinely lack this session.
    unverifiedFocusAcceptedRef.current = false;
    setFocusValidationStatus("invalid");
    setFocus(null);
  }, [
    bundleLoadState.failedCampaignIds,
    bundleLoadState.loadedCampaignIds,
    bundleLoadState.ready,
    focusKey,
    focusOptions,
    lens.focus,
    setFocus,
  ]);

  const derived = useMemo(
    () => deriveApiLens(lens, planCampaignId),
    [lens, planCampaignId],
  );

  const summaryLabel = useMemo(
    () => formatPlanGraphLensSummary(lens, planCampaignId),
    [lens, planCampaignId],
  );

  const value = useMemo(
    () => ({
      lens,
      derived,
      summaryLabel,
      focusOptions,
      focusValidationStatus,
      setSelectedCampaignIds,
      toggleCampaign,
      setFocus,
      retryFocusValidation,
      acceptUnverifiedFocus,
    }),
    [
      acceptUnverifiedFocus,
      derived,
      focusOptions,
      focusValidationStatus,
      lens,
      retryFocusValidation,
      setFocus,
      setSelectedCampaignIds,
      summaryLabel,
      toggleCampaign,
    ],
  );

  return (
    <PlanGraphLensContext.Provider value={value}>{children}</PlanGraphLensContext.Provider>
  );
}

export function usePlanGraphLens(): PlanGraphLensContextValue {
  const value = useContext(PlanGraphLensContext);
  if (!value) {
    throw new Error("usePlanGraphLens must be used within PlanGraphLensProvider");
  }
  return value;
}

/** Optional hook for surfaces that may render outside the provider (tests). */
export function useOptionalPlanGraphLens(): PlanGraphLensContextValue | null {
  return useContext(PlanGraphLensContext);
}

export function defaultPlanGraphLensForPlanCampaign(planCampaignId: string): PlanGraphLens {
  if (isReviewCampaignId(planCampaignId)) {
    return resolvePlanGraphLens(planCampaignId, "");
  }
  return {
    selectedCampaignIds: [...REVIEW_CAMPAIGN_IDS],
    focus: null,
  };
}

export { isFocusValidationBlocking };
