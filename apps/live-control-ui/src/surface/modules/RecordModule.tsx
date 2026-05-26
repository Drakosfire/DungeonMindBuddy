import type { LiveEvent } from "../../api/types";

interface RecordModuleProps {
  events: LiveEvent[];
}

export function RecordModule({ events }: RecordModuleProps) {
  const tail = [...events].slice(-50).reverse();

  return (
    <div className="module-panel record-module" data-module-id="record">
      <h2 className="module-title">Record</h2>
      {tail.length === 0 ? (
        <p className="module-muted">No events yet. Chat submissions append here.</p>
      ) : (
        <ul className="record-list">
          {tail.map((event) => (
            <li key={event.id} className="record-item">
              <div className="record-meta">
                <time dateTime={event.created_at}>{event.created_at}</time>
                <span className="badge">{event.event_type}</span>
                <span className="badge muted">{event.latency_mode}</span>
                {event.origin ? <span className="badge muted">{event.origin}</span> : null}
              </div>
              <p className="record-summary">{event.summary}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
