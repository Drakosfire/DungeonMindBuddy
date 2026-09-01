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

import { getSourceBundle, getWorldGraphCampaigns } from "../api/liveApi";
import type { IngestionSourceBundle } from "../api/types";
import {
  getCampaignRegistry,
  getWorldIdForCampaign,
  setCampaignRegistry,
} from "../worldGraph/worldGraphSurfaceContext";
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
   * - pending: focus present, bundles still loading / lens key changed
   * - valid: focus confirmed in a successful bundle (or operator override for this lens key)
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
   * successful bundle ground truth (unblocks projection + Ask for this lens key only).
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
   * Injectable for tests; defaults to the live authority registry read.
   * When `null`, the registry fetch is skipped (seeded fallback stays).
   */
  loadCampaignRegistry?: typeof getWorldGraphCampaigns | null;
  /**
   * Test override: skip network and use these options immediately.
   * When set (including `[]`), bundle loading is skipped.
   */
  focusOptions?: PlanGraphLoadFocusOption[];
}

function sortCampaignIds(ids: readonly ReviewCampaignId[]): ReviewCampaignId[] {
  const registryOrder = getCampaignRegistry().map((entry) => entry.campaignId);
  const known = registryOrder.filter((id) => ids.includes(id));
  // Admitted via the shipped fallback map but not (yet) in the registry.
  const rest = ids.filter((id) => !registryOrder.includes(id));
  return [...known, ...rest];
}

/**
 * One world per projection: adding a campaign from another world switches the
 * selection to that world; adding within the same world unions campaigns.
 */
function sameWorldSelection(
  current: readonly ReviewCampaignId[],
  added: ReviewCampaignId,
): ReviewCampaignId[] {
  const addedWorld = getWorldIdForCampaign(added);
  const currentWorld = current.length > 0 ? getWorldIdForCampaign(current[0]) : null;
  if (current.length > 0 && currentWorld && addedWorld && currentWorld !== addedWorld) {
    return [added];
  }
  return [...current.filter((id) => id !== added), added];
}

/** Exact focus + selected-campaign identity for atomic validation binding. */
export function planGraphLensValidationKey(lens: PlanGraphLens): string {
  const campaigns = lens.selectedCampaignIds.join(",");
  const focus = lens.focus
    ? `${lens.focus.campaignId}:${lens.focus.sessionNumber}`
    : "";
  return `${campaigns}::${focus}`;
}

/**
 * If stored validation was computed for a different lens key, treat it as
 * pending/none immediately — do not leak a stale `valid` across lens changes.
 */
export function effectiveFocusValidationStatus(
  stored: { status: PlanGraphFocusValidationStatus; boundKey: string },
  currentKey: string,
  hasFocus: boolean,
): PlanGraphFocusValidationStatus {
  if (stored.boundKey === currentKey) return stored.status;
  return hasFocus ? "pending" : "none";
}

interface BundleLoadState {
  ready: boolean;
  loadedCampaignIds: readonly ReviewCampaignId[];
  failedCampaignIds: readonly ReviewCampaignId[];
  /** Campaign selection this load result belongs to. */
  selectedCampaignKey: string;
}

const BUNDLE_LOAD_IDLE: BundleLoadState = {
  ready: false,
  loadedCampaignIds: [],
  failedCampaignIds: [],
  selectedCampaignKey: "",
};

export function PlanGraphLensProvider({
  planCampaignId,
  children,
  loadBundle = getSourceBundle,
  loadCampaignRegistry = getWorldGraphCampaigns,
  focusOptions: focusOptionsOverride,
}: PlanGraphLensProviderProps) {
  const [lens, setLens] = useState<PlanGraphLens>(() =>
    resolvePlanGraphLens(
      planCampaignId,
      typeof window !== "undefined" ? window.location.search : "",
    ),
  );
  const [registryReady, setRegistryReady] = useState(false);
  const [focusOptions, setFocusOptions] = useState<PlanGraphLoadFocusOption[]>(
    () => focusOptionsOverride ?? [],
  );
  const [bundleLoadState, setBundleLoadState] = useState<BundleLoadState>(() => {
    const initialLens = resolvePlanGraphLens(
      planCampaignId,
      typeof window !== "undefined" ? window.location.search : "",
    );
    if (focusOptionsOverride !== undefined) {
      return {
        ready: true,
        loadedCampaignIds: sortCampaignIds(
          focusOptionsOverride.map((option) => option.campaignId),
        ),
        failedCampaignIds: [],
        selectedCampaignKey: initialLens.selectedCampaignIds.join(","),
      };
    }
    return BUNDLE_LOAD_IDLE;
  });
  const [storedValidation, setStoredValidation] = useState<{
    status: PlanGraphFocusValidationStatus;
    boundKey: string;
  }>(() => {
    const initialLens = resolvePlanGraphLens(
      planCampaignId,
      typeof window !== "undefined" ? window.location.search : "",
    );
    return {
      status: initialLens.focus ? "pending" : "none",
      boundKey: planGraphLensValidationKey(initialLens),
    };
  });
  const [bundleReloadToken, setBundleReloadToken] = useState(0);
  /**
   * Operator override is valid only while this exact lens key is current.
   * Changing campaigns/focus invalidates it without waiting for an effect.
   */
  const unverifiedOverrideKeyRef = useRef<string | null>(null);

  const selectedCampaignKey = lens.selectedCampaignIds.join(",");
  const focusKey = lens.focus
    ? `${lens.focus.campaignId}:${lens.focus.sessionNumber}`
    : "";
  const currentValidationKey = planGraphLensValidationKey(lens);

  const focusValidationStatus = effectiveFocusValidationStatus(
    storedValidation,
    currentValidationKey,
    lens.focus != null,
  );

  const bindValidation = useCallback(
    (status: PlanGraphFocusValidationStatus, boundKey: string) => {
      setStoredValidation((previous) =>
        previous.status === status && previous.boundKey === boundKey
          ? previous
          : { status, boundKey },
      );
    },
    [],
  );

  const setSelectedCampaignIds = useCallback(
    (ids: ReviewCampaignId[]) => {
      unverifiedOverrideKeyRef.current = null;
      // One world per projection: keep only campaigns sharing the first id's world.
      const worldId = ids.length > 0 ? getWorldIdForCampaign(ids[0]) : null;
      const sameWorld = worldId
        ? ids.filter((id) => getWorldIdForCampaign(id) === worldId)
        : ids;
      setLens((previous) => {
        const next: PlanGraphLens = {
          selectedCampaignIds: sortCampaignIds(sameWorld),
          focus:
            previous.focus && sameWorld.includes(previous.focus.campaignId)
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
    unverifiedOverrideKeyRef.current = null;
    setLens((previous) => {
      const nextIds = previous.selectedCampaignIds.includes(campaignId)
        ? previous.selectedCampaignIds.filter((id) => id !== campaignId)
        : sameWorldSelection(previous.selectedCampaignIds, campaignId);
      const selectedCampaignIds = sortCampaignIds(nextIds);
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

  const setFocus = useCallback(
    (focus: PlanGraphLensFocus | null) => {
      unverifiedOverrideKeyRef.current = null;
      setLens((previous) => {
        const nextFocus =
          focus && previous.selectedCampaignIds.includes(focus.campaignId)
            ? focus
            : null;
        if (
          previous.focus?.campaignId === nextFocus?.campaignId
          && previous.focus?.sessionNumber === nextFocus?.sessionNumber
        ) {
          return previous;
        }
        const next: PlanGraphLens = {
          selectedCampaignIds: previous.selectedCampaignIds,
          focus: nextFocus,
        };
        syncPlanGraphLensUrl(next);
        return next;
      });
      // Bind to the post-update lens key using current selection + requested focus.
      const nextFocus =
        focus && lens.selectedCampaignIds.includes(focus.campaignId) ? focus : null;
      const nextLens: PlanGraphLens = {
        selectedCampaignIds: lens.selectedCampaignIds,
        focus: nextFocus,
      };
      bindValidation(nextFocus ? "valid" : "none", planGraphLensValidationKey(nextLens));
    },
    [bindValidation, lens.selectedCampaignIds],
  );

  const retryFocusValidation = useCallback(() => {
    unverifiedOverrideKeyRef.current = null;
    bindValidation(lens.focus ? "pending" : "none", currentValidationKey);
    setBundleReloadToken((token) => token + 1);
  }, [bindValidation, currentValidationKey, lens.focus]);

  const acceptUnverifiedFocus = useCallback(() => {
    if (!lens.focus) return;
    unverifiedOverrideKeyRef.current = currentValidationKey;
    bindValidation("valid", currentValidationKey);
  }, [bindValidation, currentValidationKey, lens.focus]);

  // Fetch the authority campaign registry once; the seeded fallback stays on failure.
  useEffect(() => {
    if (loadCampaignRegistry === null) {
      setRegistryReady(true);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const entries = await loadCampaignRegistry();
        if (!cancelled) setCampaignRegistry(entries);
      } catch {
        // Authority unavailable: shipped fallback registry remains in effect.
      } finally {
        if (!cancelled) setRegistryReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadCampaignRegistry]);

  // Once the registry is live, re-resolve the lens from the URL so campaigns
  // outside the shipped default set (e.g. a module world) are admitted. The URL
  // is kept in sync with user toggles, so this never overrides a live choice.
  useEffect(() => {
    if (!registryReady) return;
    setLens((previous) => {
      const reresolved = resolvePlanGraphLens(
        planCampaignId,
        typeof window !== "undefined" ? window.location.search : "",
      );
      return planGraphLensValidationKey(reresolved) === planGraphLensValidationKey(previous)
        ? previous
        : reresolved;
    });
  }, [registryReady, planCampaignId]);

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
        selectedCampaignKey,
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
        selectedCampaignKey,
      });
      return;
    }

    let cancelled = false;
    setBundleLoadState({
      ...BUNDLE_LOAD_IDLE,
      selectedCampaignKey,
    });

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
        selectedCampaignKey,
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

  // Validate active focus against grounded options once bundles resolve for this selection.
  useEffect(() => {
    const bundlesMatchSelection =
      bundleLoadState.ready
      && bundleLoadState.selectedCampaignKey === selectedCampaignKey;

    if (!bundlesMatchSelection) {
      bindValidation(lens.focus ? "pending" : "none", currentValidationKey);
      return;
    }

    const focus = lens.focus;
    if (!focus) {
      unverifiedOverrideKeyRef.current = null;
      bindValidation("none", currentValidationKey);
      return;
    }

    const focusCampaignFailed =
      bundleLoadState.failedCampaignIds.includes(focus.campaignId)
      && !bundleLoadState.loadedCampaignIds.includes(focus.campaignId);

    // Transient API failure: keep URL focus; stay gated unless override matches this lens key.
    if (focusCampaignFailed) {
      if (unverifiedOverrideKeyRef.current === currentValidationKey) {
        bindValidation("valid", currentValidationKey);
        return;
      }
      bindValidation("unavailable", currentValidationKey);
      return;
    }

    if (optionsIncludeFocus(focusOptions, focus)) {
      unverifiedOverrideKeyRef.current = null;
      bindValidation("valid", currentValidationKey);
      return;
    }

    // Successful bundle(s) for the focus campaign genuinely lack this session.
    unverifiedOverrideKeyRef.current = null;
    bindValidation("invalid", currentValidationKey);
    setFocus(null);
  }, [
    bindValidation,
    bundleLoadState.failedCampaignIds,
    bundleLoadState.loadedCampaignIds,
    bundleLoadState.ready,
    bundleLoadState.selectedCampaignKey,
    currentValidationKey,
    focusKey,
    focusOptions,
    lens.focus,
    selectedCampaignKey,
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

/** Aliases for neutral graph-lens surfaces. */
export const WorldGraphLensProvider = PlanGraphLensProvider;
export const useWorldGraphLens = usePlanGraphLens;
export const useOptionalWorldGraphLens = useOptionalPlanGraphLens;
