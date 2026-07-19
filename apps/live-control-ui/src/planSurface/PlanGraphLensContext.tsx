import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";

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
  setSelectedCampaignIds: (ids: ReviewCampaignId[]) => void;
  toggleCampaign: (campaignId: ReviewCampaignId) => void;
  setFocus: (focus: PlanGraphLensFocus | null) => void;
}

const PlanGraphLensContext = createContext<PlanGraphLensContextValue | null>(null);

interface PlanGraphLensProviderProps {
  planCampaignId: string;
  children: ReactNode;
}

function sortCampaignIds(ids: readonly ReviewCampaignId[]): ReviewCampaignId[] {
  return REVIEW_CAMPAIGN_IDS.filter((id) => ids.includes(id));
}

export function PlanGraphLensProvider({
  planCampaignId,
  children,
}: PlanGraphLensProviderProps) {
  const [lens, setLens] = useState<PlanGraphLens>(() =>
    resolvePlanGraphLens(
      planCampaignId,
      typeof window !== "undefined" ? window.location.search : "",
    ),
  );

  const setSelectedCampaignIds = useCallback(
    (ids: ReviewCampaignId[]) => {
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
    setLens((previous) => {
      const next: PlanGraphLens = {
        selectedCampaignIds: previous.selectedCampaignIds,
        focus:
          focus && previous.selectedCampaignIds.includes(focus.campaignId) ? focus : null,
      };
      syncPlanGraphLensUrl(next);
      return next;
    });
  }, []);

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
      setSelectedCampaignIds,
      toggleCampaign,
      setFocus,
    }),
    [derived, lens, setFocus, setSelectedCampaignIds, summaryLabel, toggleCampaign],
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
