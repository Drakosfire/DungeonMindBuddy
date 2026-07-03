import type { GraphReviewInteractionMode, GraphReviewLaneUiState } from "./graphReviewAuthoringState";
import { canShowLaneEditControls } from "./graphReviewAuthoringState";

interface Props {
  lane: GraphReviewLaneUiState;
  onModeChange: (mode: GraphReviewInteractionMode) => void;
}

export function GraphReviewWorkbenchLaneHeader({ lane, onModeChange }: Props) {
  const editable = canShowLaneEditControls(lane);
  return (
    <header className="graph-review-authoring-lane-header">
      <div>
        <p className="plan-surface-kicker">{lane.laneId === "left" ? "Left lane" : "Right lane"}</p>
        <h3>{lane.title}</h3>
        <p>{lane.sourceKind.replace(/_/g, " ")} · {lane.mutability.replace(/_/g, "-")} · {lane.sourceLabel}</p>
      </div>
      <div className="graph-review-authoring-lane-badges" aria-label={`${lane.title} state`}>
        {editable ? <span>{lane.unsavedChangeCount} unsaved changes</span> : <span>read-only</span>}
        <span>{lane.stagedProposalCount} staged</span>
        {editable ? <button type="button" onClick={() => onModeChange("select_span")}>Select span</button> : null}
      </div>
    </header>
  );
}
