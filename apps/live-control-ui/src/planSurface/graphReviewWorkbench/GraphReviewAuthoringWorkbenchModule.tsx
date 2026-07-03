import { useMemo, useState } from "react";

import { GraphReviewAuthoringStagingTray } from "./GraphReviewAuthoringStagingTray";
import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import { GraphReviewRelationshipCard } from "./GraphReviewRelationshipCard";
import { GraphReviewRelationshipChips } from "./GraphReviewRelationshipChips";
import { GraphReviewWorkbenchLaneHeader } from "./GraphReviewWorkbenchLaneHeader";
import { GraphReviewWorkbenchModeStrip } from "./GraphReviewWorkbenchModeStrip";
import { mockAuthoringLanes, mockAuthoringProposals, mockRecapPassage, mockRelationships, mockTripodNode } from "./graphReviewAuthoringMockData";
import type { GraphReviewInteractionMode, GraphReviewProposalStatus } from "./graphReviewAuthoringState";
import { stagedProposalCount, updateProposalStatus } from "./graphReviewAuthoringState";

function MockProjectedProse({ laneTitle, acceptedProposalCount, onNodeSelect }: { laneTitle: string; acceptedProposalCount: number; onNodeSelect: () => void }) {
  return (
    <article className="graph-review-authoring-prose" aria-label={`${laneTitle} projected prose`}>
      <p>{mockRecapPassage.split("Tripod Null-Calf")[0]}<button type="button" className="graph-review-prose-pill" onClick={onNodeSelect}>Tripod Null-Calf</button>{mockRecapPassage.split("Tripod Null-Calf")[1]}</p>
      <p className="graph-review-prose-note">Accepted mock proposals visible in this draft: {acceptedProposalCount}. Staged proposals remain in the tray until accepted.</p>
    </article>
  );
}

export function GraphReviewAuthoringWorkbenchModule() {
  const [activeMode, setActiveMode] = useState<GraphReviewInteractionMode>("inspect");
  const [rightRailOpen, setRightRailOpen] = useState(false);
  const [selectedRelationshipId, setSelectedRelationshipId] = useState<string | null>(null);
  const [selectedNodeOpen, setSelectedNodeOpen] = useState(false);
  const [proposals, setProposals] = useState(mockAuthoringProposals);

  const acceptedProposalCount = useMemo(() => proposals.filter((proposal) => proposal.status === "accepted").length, [proposals]);
  const selectedRelationship = mockRelationships.find((relationship) => relationship.id === selectedRelationshipId) ?? mockRelationships[0];
  const lanes = mockAuthoringLanes.map((lane) => lane.laneId === "left" ? { ...lane, activeInteractionMode: activeMode, stagedProposalCount: stagedProposalCount(proposals) } : lane);

  const changeProposalStatus = (id: string, status: GraphReviewProposalStatus) => {
    setProposals((current) => updateProposalStatus(current, id, status));
  };

  return (
    <section className="graph-review-authoring-workbench" aria-label="Graph Review and Gold Authoring visual skeleton">
      <header className="graph-review-authoring-hero">
        <p className="plan-surface-kicker">Prose-first authoring walkthrough</p>
        <h2>Graph Review + Gold Authoring Workbench</h2>
        <p>Read the campaign chronicle first. Graph meaning is woven into the prose; editing is explicit and safe; evidence/debug stays behind deliberate drill-in.</p>
      </header>
      <GraphReviewWorkbenchModeStrip activeMode={activeMode} onModeChange={setActiveMode} />
      <div className="graph-review-authoring-layout">
        <main className="graph-review-authoring-lanes">
          {lanes.map((lane) => (
            <section key={lane.laneId} className="graph-review-authoring-lane">
              <GraphReviewWorkbenchLaneHeader lane={lane} onModeChange={setActiveMode} />
              <MockProjectedProse laneTitle={lane.title} acceptedProposalCount={lane.laneId === "left" ? acceptedProposalCount : 0} onNodeSelect={() => { setSelectedNodeOpen(true); setRightRailOpen(true); }} />
              <GraphReviewRelationshipChips relationships={mockRelationships} selectedId={selectedRelationshipId} onSelect={(id) => { setSelectedRelationshipId(id); setRightRailOpen(true); }} />
            </section>
          ))}
          <GraphReviewAuthoringStagingTray proposals={proposals} onStatusChange={changeProposalStatus} />
        </main>
        <aside className="graph-review-authoring-rail" data-open={rightRailOpen} aria-label="Inspector rail">
          <button type="button" onClick={() => setRightRailOpen((open) => !open)}>{rightRailOpen ? "Collapse inspector" : "Inspector"}</button>
          {rightRailOpen ? (
            <div className="graph-review-authoring-rail-content">
              {selectedNodeOpen ? <GraphReviewNodeGameCard node={mockTripodNode} onShowRelationships={() => setSelectedRelationshipId("rel_tripod_gate")} /> : null}
              <GraphReviewRelationshipCard relationship={selectedRelationship} />
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
