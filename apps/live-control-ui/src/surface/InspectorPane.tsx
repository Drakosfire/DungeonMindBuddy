import { formatTargetType, type PaneTarget } from "./targetTypes";

export type InspectorPaneState =
  | { status: "closed" }
  | { status: "open"; target: PaneTarget | null };

interface InspectorPaneProps {
  state: InspectorPaneState;
  onClose: () => void;
}

export function InspectorPane({ state, onClose }: InspectorPaneProps) {
  if (state.status === "closed") {
    return null;
  }

  return (
    <aside className="inspector-pane" aria-label="Inspector pane">
      <header className="inspector-pane-header">
        <h2>Inspector</h2>
        <button type="button" onClick={onClose}>
          Close
        </button>
      </header>
      {state.target == null ? (
        <p className="module-muted">Select a timeline ref or record event to inspect.</p>
      ) : (
        <div className="inspector-pane-target">
          <p className="inspector-pane-title">
            {formatTargetType(state.target.target_type)} · {state.target.label}
          </p>
          <ul className="inspector-pane-metadata">
            <li>
              <span className="inspector-key">source:</span> {state.target.source_status}
            </li>
            {state.target.role ? (
              <li>
                <span className="inspector-key">role:</span> {state.target.role}
              </li>
            ) : null}
            <li>
              <span className="inspector-key">id:</span> {state.target.target_id}
            </li>
            {state.target.origin ? (
              <li>
                <span className="inspector-key">origin:</span> {state.target.origin.module_id}
                {state.target.origin.row_id ? ` / ${state.target.origin.row_id}` : ""}
              </li>
            ) : null}
          </ul>
          <p className="module-muted">
            Read renderer not implemented yet. Artifact and capability reads arrive in PR83.
          </p>
        </div>
      )}
    </aside>
  );
}
