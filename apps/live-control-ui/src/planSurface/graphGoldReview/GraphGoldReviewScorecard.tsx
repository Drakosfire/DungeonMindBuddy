import type { GoldReviewCompareResponse } from "../../api/types";
import { coverageRows, headlineScores } from "./graphGoldReviewUtils";

interface GraphGoldReviewScorecardProps {
  compare: GoldReviewCompareResponse | null;
}

export function GraphGoldReviewScorecard({ compare }: GraphGoldReviewScorecardProps) {
  const headlines = headlineScores(compare);
  const rows = coverageRows(compare);

  return (
    <section className="graph-gold-review-scorecard" aria-label="Gold vs live recall">
      <header>
        <p className="plan-surface-kicker">Recall overview</p>
        <h3>Gold vs live graph</h3>
      </header>
      <div className="graph-gold-review-stat-grid">
        {headlines.map((item) => (
          <div key={item.label} className="graph-gold-review-stat">
            <span>{item.label}</span>
            <strong>{item.value}</strong>
          </div>
        ))}
      </div>
      {rows.length ? (
        <table className="graph-gold-review-coverage-table">
          <thead>
            <tr>
              <th>Class</th>
              <th>Gold</th>
              <th>Live</th>
              <th>Matched</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.kind}>
                <td>{row.kind}</td>
                <td>{row.goldTotal}</td>
                <td>{row.liveTotal}</td>
                <td>{row.matched}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </section>
  );
}
