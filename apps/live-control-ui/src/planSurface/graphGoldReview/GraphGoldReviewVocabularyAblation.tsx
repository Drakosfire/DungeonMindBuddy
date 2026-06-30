import type { VocabularyAblationDogfoodResponse } from "../../api/types";

interface GraphGoldReviewVocabularyAblationProps {
  data: VocabularyAblationDogfoodResponse | null;
  loading: boolean;
  error: string | null;
}

function formatRate(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value * 1000) / 10}%`;
}

function formatScore(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return String(value);
}

function formatNames(names: string[] | null | undefined): string {
  if (!names?.length) return "none";
  return names.join(", ");
}

function variantFlags(row: { enable_node_packet: boolean; enable_edge_packet: boolean }): string {
  const parts: string[] = [];
  if (row.enable_node_packet) parts.push("node");
  if (row.enable_edge_packet) parts.push("edge");
  return parts.length ? parts.join(" + ") : "none";
}

export function GraphGoldReviewVocabularyAblation({
  data,
  loading,
  error,
}: GraphGoldReviewVocabularyAblationProps) {
  if (loading) {
    return <p className="graph-gold-review-note">Loading vocabulary ablation dogfood…</p>;
  }
  if (error) {
    return <p className="graph-gold-review-error">{error}</p>;
  }
  if (!data) {
    return null;
  }

  const comparison = data.comparison as {
    best_variant?: string;
    summary?: Record<string, string>;
    warnings?: string[];
  };
  const bestVariant = comparison.best_variant ?? null;
  const summary = comparison.summary ?? {};

  return (
    <section className="graph-gold-review-vocab-ablation" aria-label="Vocabulary ablation dogfood">
      <header>
        <p className="plan-surface-kicker">Vocabulary ablation</p>
        <h3>C2S23 Mireward dogfood</h3>
        <p className="graph-gold-review-lede">
          Four extraction variants over the S23 normalized recap with a hand-authored vocabulary
          packet. Recognition measures present-set names; contamination flags absent-set names
          induced by the packet. Harness scores are heuristic review signals, not benchmark truth.
        </p>
      </header>

      <div className="graph-gold-review-stat-grid">
        <div className="graph-gold-review-stat">
          <span>Best variant</span>
          <strong>{bestVariant ?? "—"}</strong>
        </div>
        <div className="graph-gold-review-stat">
          <span>Model</span>
          <strong>{data.model_id}</strong>
        </div>
        <div className="graph-gold-review-stat">
          <span>Source spans</span>
          <strong>{data.source_span_count}</strong>
        </div>
        <div className="graph-gold-review-stat">
          <span>Generated</span>
          <strong>{data.generated_at.replace("T", " ").replace("Z", " UTC")}</strong>
        </div>
      </div>

      <p className="graph-gold-review-vocab-recommendation">{data.recommendation}</p>

      <table className="graph-gold-review-coverage-table graph-gold-review-vocab-table">
        <thead>
          <tr>
            <th>Variant</th>
            <th>Packets</th>
            <th>Score</th>
            <th>Recognition</th>
            <th>Contamination</th>
            <th>Pooled pickup</th>
            <th>Combat</th>
            <th>Predicates</th>
            <th>Unsafe blocked</th>
            <th>Nodes</th>
            <th>Edges</th>
          </tr>
        </thead>
        <tbody>
          {data.variant_setup.map((row) => (
            <tr
              key={row.variant_name}
              className={row.variant_name === bestVariant ? "graph-gold-review-vocab-best" : undefined}
            >
              <td>
                <code>{row.variant_name}</code>
              </td>
              <td>{variantFlags(row)}</td>
              <td>{formatScore(row.score)}</td>
              <td title={formatNames(row.present_recognized)}>{formatRate(row.recognition_rate)}</td>
              <td title={formatNames(row.absent_contaminated)}>
                {formatRate(row.contamination_rate)}
                {row.contamination_count != null ? ` (${row.contamination_count})` : ""}
              </td>
              <td>{formatRate(row.known_name_pickup_rate)}</td>
              <td>{row.combat_encounter_match_count ?? "—"}</td>
              <td>{row.predicate_hint_match_count ?? "—"}</td>
              <td>{row.unsafe_cross_class_blocked_count ?? "—"}</td>
              <td>{row.node_count}</td>
              <td>{row.edge_count}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.partition ? (
        <div className="graph-gold-review-vocab-partition">
          <div>
            <h4>Present set</h4>
            <p>{formatNames(data.partition.present_set)}</p>
          </div>
          <div>
            <h4>Absent set</h4>
            <p>{formatNames(data.partition.absent_set)}</p>
          </div>
        </div>
      ) : null}

      <dl className="graph-gold-review-vocab-summary">
        <div>
          <dt>Pooled pickup leader</dt>
          <dd>{summary.known_name_pickup_best_variant ?? "—"}</dd>
        </div>
        <div>
          <dt>Predicate hint leader</dt>
          <dd>{summary.predicate_hint_best_variant ?? "—"}</dd>
        </div>
        <div>
          <dt>Combat encounter leader</dt>
          <dd>{summary.combat_encounter_best_variant ?? "—"}</dd>
        </div>
        <div>
          <dt>Safest collision profile</dt>
          <dd>{summary.safest_collision_variant ?? "—"}</dd>
        </div>
      </dl>

      {comparison.warnings?.length ? (
        <ul className="graph-gold-review-vocab-warnings">
          {comparison.warnings.map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      ) : null}

      <p className="graph-gold-review-meta">
        Report · <code>{data.report_path}</code> · packet · <code>{data.packet_id}</code>
      </p>
    </section>
  );
}
