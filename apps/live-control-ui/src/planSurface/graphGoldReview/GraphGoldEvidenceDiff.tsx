import type { GoldReviewEvidenceDiffResponse, GoldReviewEvidenceResolvedRef } from "../../api/types";
import { lineRangeLabel } from "../graphPreview/graphPreviewUtils";

interface GraphGoldEvidenceDiffProps {
  diff: GoldReviewEvidenceDiffResponse | null;
  loading: boolean;
  error: string | null;
}

function EvidenceColumn({
  title,
  side,
}: {
  title: string;
  side: GoldReviewEvidenceDiffResponse["gold"] | GoldReviewEvidenceDiffResponse["live"];
}) {
  if (!side) {
    return (
      <article className="graph-gold-review-evidence-column">
        <header>
          <p className="plan-surface-kicker">{title}</p>
          <h4>No live match</h4>
        </header>
        <p className="graph-gold-review-note">The live graph did not produce a comparable object.</p>
      </article>
    );
  }

  return (
    <article className="graph-gold-review-evidence-column">
      <header>
        <p className="plan-surface-kicker">{title}</p>
        <h4>{side.label || side.object_id}</h4>
        <code>{side.object_id}</code>
      </header>
      {side.summary ? <p className="graph-gold-review-beat-summary">{side.summary}</p> : null}
      {side.object_kind === "beats" ? (
        <p className="graph-gold-review-meta">
          involved_node_ids:{" "}
          <code>{JSON.stringify(side.payload.involved_node_ids ?? [])}</code>
        </p>
      ) : null}
      {side.object_kind === "edges" ? (
        <p className="graph-gold-review-meta">
          {String(side.payload.from_node_id ?? side.payload.source_node_id ?? "?")} →{" "}
          {String(side.payload.relationship_type ?? side.payload.predicate ?? "?")} →{" "}
          {String(side.payload.to_node_id ?? side.payload.target_node_id ?? "?")}
        </p>
      ) : null}
      <div className="graph-gold-review-evidence-list">
        {side.evidence.map((ref, index) => (
          <EvidenceSnippet key={`${side.object_id}-${index}`} evidence={ref} />
        ))}
      </div>
    </article>
  );
}

function EvidenceSnippet({ evidence }: { evidence: GoldReviewEvidenceResolvedRef }) {
  const text = evidence.paragraph_text ?? evidence.preview_snippet ?? "";
  return (
    <section className="graph-gold-review-evidence-snippet">
      <header>
        <strong>{evidence.label ?? evidence.source_anchor_id ?? "Evidence"}</strong>
        <span>{lineRangeLabel(evidence.line_start, evidence.line_end)}</span>
      </header>
      {evidence.source_anchor_id ? <code>{evidence.source_anchor_id}</code> : null}
      <p>{text || "No resolved source text for this evidence ref."}</p>
    </section>
  );
}

export function GraphGoldEvidenceDiff({ diff, loading, error }: GraphGoldEvidenceDiffProps) {
  if (loading) {
    return <p className="graph-gold-review-note">Loading evidence diff…</p>;
  }
  if (error) {
    return <p className="graph-gold-review-error">{error}</p>;
  }
  if (!diff) {
    return (
      <p className="graph-gold-review-note">
        Select a missing gold node, edge, or beat to compare evidence against the live graph.
      </p>
    );
  }

  return (
    <section className="graph-gold-review-evidence-diff" aria-label="Evidence diff">
      <header>
        <p className="plan-surface-kicker">Evidence inspector</p>
        <h3>
          {diff.object_kind} · {diff.object_id}
        </h3>
        <p className="graph-gold-review-meta">
          {diff.matched ? "Matched live object" : "Closest live candidate"}
          {diff.match_score != null ? ` · score ${diff.match_score.toFixed(2)}` : ""}
        </p>
      </header>
      <div className="graph-gold-review-evidence-columns">
        <EvidenceColumn title="Gold expected" side={diff.gold} />
        <EvidenceColumn title="Live constructed" side={diff.live} />
      </div>
    </section>
  );
}
