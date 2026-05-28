import type { PlanViewProjection, SurfaceModuleDefinition } from "../../api/types";

interface TimelineModuleProps {
  planView: PlanViewProjection;
  catalogEntry?: SurfaceModuleDefinition;
}

export function TimelineModule({ planView, catalogEntry }: TimelineModuleProps) {
  const title = catalogEntry?.title ?? "Timeline";

  return (
    <div className="module-panel timeline-module" data-module-id="timeline">
      <h2 className="module-title">{title}</h2>
      <p className="module-muted timeline-derived-note">
        Derived plan · session {planView.session}
      </p>
      {planView.timeline.length === 0 ? (
        <p className="module-muted">No projected beats yet.</p>
      ) : (
        <ol className="timeline-list">
          {planView.timeline.map((row) => (
            <li key={row.id} className="timeline-row">
              <div className="timeline-row-header">
                <span className="badge timeline-status">{row.status}</span>
                <span className="timeline-label">{row.label}</span>
              </div>
              {row.time_hint ? <p className="timeline-time">{row.time_hint}</p> : null}
              <p className="timeline-summary">{row.summary}</p>
              {row.table_ready_prompt ? (
                <p className="timeline-prompt">Prompt: {row.table_ready_prompt}</p>
              ) : null}
              {row.refs.length > 0 ? (
                <ul className="timeline-ref-list">
                  {row.refs.map((ref) => (
                    <li key={`${row.id}-${ref.target_type}-${ref.target_id}`}>
                      <span className="timeline-ref-chip">
                        {ref.target_type.replace("_", " ")} · {ref.label}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
