import type { GoldReviewCompareResponse } from "../../api/types";
import {
  buildMissGroups,
  type GoldReviewObjectKind,
  type GoldReviewSelection,
} from "./graphGoldReviewUtils";

interface GraphGoldReviewMissTablesProps {
  compare: GoldReviewCompareResponse | null;
  selection: GoldReviewSelection | null;
  onSelect: (selection: GoldReviewSelection) => void;
}

function missButtonClass(active: boolean): string {
  return active ? "graph-gold-review-miss-item active" : "graph-gold-review-miss-item";
}

export function GraphGoldReviewMissTables({
  compare,
  selection,
  onSelect,
}: GraphGoldReviewMissTablesProps) {
  const groups = buildMissGroups(compare).filter(
    (group) => group.missing.length > 0 || group.extra.length > 0,
  );

  if (!groups.length) {
    return <p className="graph-gold-review-note">No misses detected for the selected live run.</p>;
  }

  return (
    <section className="graph-gold-review-misses" aria-label="Gold misses and live extras">
      {groups.map((group) => (
        <div key={group.kind} className="graph-gold-review-miss-group">
          <header>
            <h4>{group.label}</h4>
            <span>
              {group.missing.length} missing · {group.extra.length} extra
            </span>
          </header>
          {group.missing.length ? (
            <div>
              <p className="graph-gold-review-miss-heading">Missing gold</p>
              <ul>
                {group.missing.map((entry) => {
                  const active =
                    selection?.objectKind === group.kind && selection.objectId === entry.id;
                  return (
                    <li key={entry.id}>
                      <button
                        type="button"
                        className={missButtonClass(active)}
                        onClick={() =>
                          onSelect({
                            objectKind: group.kind as GoldReviewObjectKind,
                            objectId: entry.id,
                          })
                        }
                      >
                        <strong>{entry.label || entry.id}</strong>
                        <code>{entry.id}</code>
                      </button>
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
          {group.extra.length ? (
            <div>
              <p className="graph-gold-review-miss-heading">Extra live</p>
              <ul>
                {group.extra.map((entry) => (
                  <li key={entry.id}>
                    <div className="graph-gold-review-miss-item readonly">
                      <strong>{entry.label || entry.id}</strong>
                      <code>{entry.id}</code>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ))}
    </section>
  );
}
