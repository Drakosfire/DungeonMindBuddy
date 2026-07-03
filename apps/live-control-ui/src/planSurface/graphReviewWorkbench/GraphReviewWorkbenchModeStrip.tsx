import type { GraphReviewInteractionMode } from "./graphReviewAuthoringState";

const modes: Array<{ id: GraphReviewInteractionMode; label: string }> = [
  { id: "inspect", label: "Inspect" },
  { id: "select_span", label: "Select span" },
  { id: "draw_edge", label: "Draw edge" },
  { id: "review_proposals", label: "Review proposals" },
  { id: "evidence_debug", label: "Evidence / Debug" },
];

export function GraphReviewWorkbenchModeStrip({ activeMode, onModeChange }: { activeMode: GraphReviewInteractionMode; onModeChange: (mode: GraphReviewInteractionMode) => void }) {
  return (
    <div className="graph-review-authoring-mode-strip" aria-label="Interaction mode">
      {modes.map((mode) => (
        <button key={mode.id} type="button" aria-pressed={activeMode === mode.id} onClick={() => onModeChange(mode.id)}>
          {mode.label}
        </button>
      ))}
    </div>
  );
}
