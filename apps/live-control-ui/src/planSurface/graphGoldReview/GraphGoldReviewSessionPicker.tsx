import type { GoldReviewSessionSummary } from "../../api/types";
import { goldReviewSessionLabel } from "../sessionCampaignContext";

interface GraphGoldReviewSessionPickerProps {
  sessions: GoldReviewSessionSummary[];
  selectedSessionId: string;
  onSelect: (sessionId: string) => void;
}

export function GraphGoldReviewSessionPicker({
  sessions,
  selectedSessionId,
  onSelect,
}: GraphGoldReviewSessionPickerProps) {
  return (
    <div className="graph-gold-review-session-picker" role="tablist" aria-label="Gold-backed sessions">
      {sessions.map((session) => {
        const active = session.session_id === selectedSessionId;
        return (
          <button
            key={session.session_id}
            type="button"
            role="tab"
            aria-selected={active}
            className={active ? "graph-gold-review-pill active" : "graph-gold-review-pill"}
            onClick={() => onSelect(session.session_id)}
          >
            {goldReviewSessionLabel(session)}
          </button>
        );
      })}
    </div>
  );
}
