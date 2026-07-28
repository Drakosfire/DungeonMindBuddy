import { type ReactNode } from "react";
import { render, type RenderResult } from "@testing-library/react";

import type { GraphIngestRunSummary } from "../../api/types";
import { createIngestSurfaceConfig } from "../config/ingestSurfaceConfig";
import type { PlanContextDescriptor } from "../types";
import { ProjectionProvider } from "../projection/projectionContext";
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
  liveRun?: GraphIngestRunSummary | null;
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
    <ProjectionProvider config={config}>
      <GraphReviewLiveStateProvider
        campaignId={campaignId}
        sessionId={sessionId}
        liveRun={liveRun}
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
    </ProjectionProvider>,
  );
}

export { defaultContext as graphReviewLiveTestContext };
