import { useMemo, useState } from "react";

import { GraphReviewAuthoringStagingTray } from "./GraphReviewAuthoringStagingTray";
import { GraphReviewNodeGameCard } from "./GraphReviewNodeGameCard";
import { GraphReviewRelationshipCard } from "./GraphReviewRelationshipCard";
import { GraphReviewRelationshipChips } from "./GraphReviewRelationshipChips";
import { GraphReviewWorkbenchLaneHeader } from "./GraphReviewWorkbenchLaneHeader";
import { GraphReviewWorkbenchModeStrip } from "./GraphReviewWorkbenchModeStrip";
import { mockAuthoringLanes, mockAuthoringProposals, mockRecapPassage, mockRelationships, mockTripodNode } from "./graphReviewAuthoringMockData";
import type { GraphProjectionAdjacencyCandidate, GraphProjectionNodeView } from "../../api/types";
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
  const mockAdjacency: GraphProjectionAdjacencyCandidate[] = mockRelationships.map((relationship) => ({
    edge_id: relationship.id,
    node_id: `node_${relationship.target.toLowerCase().replace(/[^a-z0-9]+/g, "_")}`,
    label: relationship.target,
    kind: "campaign object",
    predicate: relationship.predicate,
    direction: relationship.source === mockTripodNode.label ? "outgoing" : "incoming",
    anchored_to_focus_session: true,
    source_domains: ["mock"],
    evidence_ref_ids: [relationship.id],
    session_ids: ["mock-session"],
  }));
  const mockNodeView: GraphProjectionNodeView = {
    node_id: mockTripodNode.id,
    label: mockTripodNode.label,
    kind: "Threat",
    role: mockTripodNode.gameKind,
    aliases: [],
    source_domains: ["mock"],
    evidence_badges: [],
    adjacency: mockAdjacency,
    anchored_to_focus_session: true,
    summary: mockTripodNode.summary,
  };
  const mockViewModel = { laneRole: "gold" as const, node: mockNodeView, status: "matched" as const, deltaId: "mock-delta", counterpart: { laneRole: "live" as const, nodeId: mockTripodNode.id, label: mockTripodNode.label, node: mockNodeView } };
  const selectedRelationship = selectedRelationshipId
    ? mockAdjacency.find((relationship) => relationship.edge_id === selectedRelationshipId) ?? null
    : null;
  const lanes = mockAuthoringLanes.map((lane) => lane.laneId === "left" ? { ...lane, activeInteractionMode: activeMode, stagedProposalCount: stagedProposalCount(proposals) } : lane);

  const changeProposalStatus = (id: string, status: GraphReviewProposalStatus) => {
    setProposals((current) => updateProposalStatus(current, id, status));
  };

  return (
    <section className="graph-review-authoring-workbench" aria-label="Graph Review and Gold Authoring visual skeleton">
      <header className="graph-review-authoring-hero">
        <p className="plan-surface-kicker">Visual walkthrough / mock UX scaffold — no live data, no writes</p>
        <h2>Graph Review + Gold Authoring Workbench</h2>
        <p>Read the campaign chronicle first. Graph meaning is woven into the prose; editing is explicit and safe; evidence/debug stays behind deliberate drill-in.</p>
        <p className="graph-review-authoring-demo-note">This panel uses demo-only Gold Draft, Live Run, proposal counts, and game objects to validate the future authoring experience. The real Workbench controls remain below.</p>
      </header>
      <GraphReviewWorkbenchModeStrip activeMode={activeMode} onModeChange={setActiveMode} />
      <div className="graph-review-authoring-layout">
        <main className="graph-review-authoring-lanes">
          {lanes.map((lane) => (
            <section key={lane.laneId} className="graph-review-authoring-lane">
              <GraphReviewWorkbenchLaneHeader lane={lane} onModeChange={setActiveMode} />
              <MockProjectedProse laneTitle={lane.title} acceptedProposalCount={lane.laneId === "left" ? acceptedProposalCount : 0} onNodeSelect={() => { setSelectedNodeOpen(true); setRightRailOpen(true); }} />
              <GraphReviewRelationshipChips sourceLabel={mockTripodNode.label} relationships={mockAdjacency} selectedEdgeId={selectedRelationshipId} onSelect={(relationship) => { setSelectedRelationshipId(relationship.edge_id); setRightRailOpen(true); }} />
            </section>
          ))}
          <GraphReviewAuthoringStagingTray proposals={proposals} onStatusChange={changeProposalStatus} />
        </main>
        <aside className="graph-review-authoring-rail" data-open={rightRailOpen} aria-label="Inspector rail">
          <button type="button" onClick={() => setRightRailOpen((open) => !open)}>{rightRailOpen ? "Collapse inspector" : "Inspector"}</button>
          {rightRailOpen ? (
            <div className="graph-review-authoring-rail-content">
              {!selectedNodeOpen && !selectedRelationship ? (
                <p className="graph-review-authoring-empty-state">Select a pill or relationship to inspect game-facing details.</p>
              ) : null}
              {selectedNodeOpen ? <GraphReviewNodeGameCard viewModel={mockViewModel} selectedEdgeId={selectedRelationshipId} onSelectRelationship={(relationship) => setSelectedRelationshipId(relationship.edge_id)} /> : null}
              {selectedRelationship ? <GraphReviewRelationshipCard sourceNode={mockNodeView} relationship={selectedRelationship} /> : null}
            </div>
          ) : null}
        </aside>
      </div>
    </section>
  );
}
