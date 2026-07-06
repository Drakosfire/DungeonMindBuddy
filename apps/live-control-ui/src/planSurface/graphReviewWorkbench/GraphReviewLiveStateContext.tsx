import { createContext, useContext, type ReactNode } from "react";

import type { GoldReviewCompareResponse, GraphIngestRunSummary } from "../../api/types";
import type { GoldReviewSelection } from "../graphGoldReview/graphGoldReviewUtils";
import {
  useGraphReviewLiveReviewState,
  type GraphReviewLiveReviewState,
  type UseGraphReviewLiveReviewStateOptions,
} from "./graphReviewLiveReviewState";

export interface GraphReviewLiveStateContextValue extends GraphReviewLiveReviewState {
  campaignId: string;
  sessionId: string;
  liveRun: GraphIngestRunSummary | null;
  hasGold: boolean;
  compare: GoldReviewCompareResponse | null;
  compareStatus: "idle" | "loading" | "ready" | "error";
  compareError: string | null;
  selection: GoldReviewSelection | null;
  onSelectSelection: (selection: GoldReviewSelection) => void;
  manualBeds: UseGraphReviewLiveReviewStateOptions["manualBeds"];
  manualBedsStatus: UseGraphReviewLiveReviewStateOptions["manualBedsStatus"];
  manualBedsError: UseGraphReviewLiveReviewStateOptions["manualBedsError"];
  selectedManualBed: UseGraphReviewLiveReviewStateOptions["selectedManualBed"];
  selectedVariantLaneView: UseGraphReviewLiveReviewStateOptions["selectedVariantLaneView"];
  selectedManualVariant: UseGraphReviewLiveReviewStateOptions["selectedManualVariant"];
  onSelectManualBedId: NonNullable<
    UseGraphReviewLiveReviewStateOptions["onSelectManualBedId"]
  >;
  onSelectManualVariantName: NonNullable<
    UseGraphReviewLiveReviewStateOptions["onSelectManualVariantName"]
  >;
}

const GraphReviewLiveStateContext =
  createContext<GraphReviewLiveStateContextValue | null>(null);

export interface GraphReviewLiveStateProviderProps
  extends UseGraphReviewLiveReviewStateOptions {
  hasGold?: boolean;
  compareError: string | null;
  selection: GoldReviewSelection | null;
  onSelectSelection: (selection: GoldReviewSelection) => void;
  children: ReactNode;
}

export function GraphReviewLiveStateProvider({
  compareError,
  selection,
  onSelectSelection,
  children,
  hasGold = false,
  compare = null,
  compareStatus = "idle",
  manualBeds = [],
  manualBedsStatus = "idle",
  manualBedsError = null,
  selectedManualBed = null,
  selectedVariantLaneView = null,
  selectedManualVariant = null,
  onSelectManualBedId = () => undefined,
  onSelectManualVariantName = () => undefined,
  ...hookOptions
}: GraphReviewLiveStateProviderProps) {
  const liveReviewState = useGraphReviewLiveReviewState({
    ...hookOptions,
    hasGold,
    compare,
    compareStatus,
    manualBeds,
    manualBedsStatus,
    manualBedsError,
    selectedManualBed,
    selectedVariantLaneView,
    selectedManualVariant,
    onSelectManualBedId,
    onSelectManualVariantName,
  });

  const value: GraphReviewLiveStateContextValue = {
    ...liveReviewState,
    campaignId: hookOptions.campaignId,
    sessionId: hookOptions.sessionId,
    liveRun: hookOptions.liveRun,
    hasGold,
    compare: compare ?? null,
    compareStatus: compareStatus ?? "idle",
    compareError,
    selection,
    onSelectSelection,
    manualBeds,
    manualBedsStatus,
    manualBedsError,
    selectedManualBed,
    selectedVariantLaneView,
    selectedManualVariant,
    onSelectManualBedId,
    onSelectManualVariantName,
  };

  return (
    <GraphReviewLiveStateContext.Provider value={value}>
      {children}
    </GraphReviewLiveStateContext.Provider>
  );
}

export function useGraphReviewLiveState(): GraphReviewLiveStateContextValue {
  const context = useContext(GraphReviewLiveStateContext);
  if (!context) {
    throw new Error(
      "useGraphReviewLiveState must be used within GraphReviewLiveStateProvider",
    );
  }
  return context;
}
