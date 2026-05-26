import type { LiveEvent, LiveState, SurfaceModuleDefinition } from "../../api/types";

interface RollStackModuleProps {
  state: LiveState;
  catalogEntry?: SurfaceModuleDefinition;
  events: LiveEvent[];
}

/** Build human table labels from roll_result events when the API only exposes table IDs in state. */
export function rollLabelsFromEvents(events: LiveEvent[]): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const event of events) {
    if (event.event_type !== "roll_result") {
      continue;
    }
    const tableId = event.derived_fields?.table_id;
    if (typeof tableId !== "string") {
      continue;
    }
    const match = event.summary.match(/^Resolved (\S+) roll/);
    if (match) {
      labels[tableId] = tableId;
    }
    const answerMatch = event.summary.match(/Resolved (\S+) roll \d+: ([^.]+)/);
    if (answerMatch) {
      labels[tableId] = answerMatch[2].trim();
    }
  }
  return labels;
}

/** Session 22 table IDs → titles mirrored from live packet roll_stack (display-only, not file reads). */
const SESSION_22_TABLE_TITLES: Record<string, string> = {
  "T-WX": "Storm weather",
  "T-NPC": "NPC spotlight",
  R5: "Road encounter",
  "T-DIL": "Travel dilemma",
  "T-DIL-G": "Gate dilemma",
  "T-CF": "Campfire roleplay",
  "T-WATCH": "Night watch",
  R6: "Conical hills night camp",
};

export function labelForTableId(tableId: string, events: LiveEvent[]): string {
  return (
    rollLabelsFromEvents(events)[tableId] ??
    SESSION_22_TABLE_TITLES[tableId] ??
    tableId
  );
}

export function RollStackModule({ state, catalogEntry, events }: RollStackModuleProps) {
  const title = catalogEntry?.title ?? "Roll stack";

  return (
    <div className="module-panel roll-stack-module" data-module-id="roll_stack">
      <h2 className="module-title">{title}</h2>
      {state.pending_roll_tables.length === 0 ? (
        <p className="module-muted">No pending roll tables.</p>
      ) : (
        <ul className="roll-stack-list">
          {state.pending_roll_tables.map((tableId) => (
            <li key={tableId}>
              <span className="roll-label">{labelForTableId(tableId, events)}</span>
              <span className="roll-status">pending</span>
              <span className="roll-id">{tableId}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
