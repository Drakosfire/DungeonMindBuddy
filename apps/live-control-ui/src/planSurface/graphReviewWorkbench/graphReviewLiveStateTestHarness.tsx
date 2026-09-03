import { type ReactNode } from "react";
import { render, type RenderResult } from "@testing-library/react";

import type { GraphIngestRunSummary } from "../../api/types";
import type { GraphReviewCatalogRun } from "./graphReviewWorkbenchUtils";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import type { PlanContextDescriptor } from "../types";
import { AgentInteractionProjectionTestHost } from "../projection/projectionTestHost";
import type { GraphReviewCommittedBinding } from "./graphReviewCommittedAuthority";
import { GraphReviewLiveStateProvider } from "./GraphReviewLiveStateContext";

const defaultContext: PlanContextDescriptor = {
  campaignId: "longmont-c2",
  liveSession: 24,
  ingestSession: 23,
  headerLabel: "Ingest",
};

export interface RenderGraphReviewLiveHarnessOptions {
  campaignId?: string;
  sessionId?: string;
  liveRun?: GraphIngestRunSummary | GraphReviewCatalogRun | null;
  hasGold?: boolean;
  committedBinding?: GraphReviewCommittedBinding | null;
  context?: PlanContextDescriptor;
  children: ReactNode;
}

export function renderGraphReviewLiveHarness({
  campaignId = "longmont-c2",
  sessionId = "session-23",
  liveRun = null,
  hasGold = false,
  committedBinding = null,
  context = defaultContext,
  children,
}: RenderGraphReviewLiveHarnessOptions): RenderResult {
  const config = createIngestSurfaceConfig(context);
  return render(
    <AgentInteractionProjectionTestHost config={config}>
      <GraphReviewLiveStateProvider
        campaignId={campaignId}
        sessionId={sessionId}
        liveRun={(liveRun as unknown as GraphReviewCatalogRun | null | undefined) ?? null}
        committedBinding={committedBinding}
        hasGold={hasGold}
        compare={null}
        compareStatus="idle"
        compareError={null}
        selection={null}
        onSelectSelection={() => undefined}
      >
        {children}
      </GraphReviewLiveStateProvider>
    </AgentInteractionProjectionTestHost>,
  );
}

export { defaultContext as graphReviewLiveTestContext };
