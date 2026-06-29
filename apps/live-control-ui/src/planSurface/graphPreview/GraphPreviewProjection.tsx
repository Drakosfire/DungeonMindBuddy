import { useEffect, useState } from "react";

import type {
  GraphPreviewCandidateRow,
  GraphPreviewHealth,
  GraphPreviewRunSummary,
  GraphPreviewSurfaceResponse,
} from "../../api/types";
import { SourceExcerptPanel } from "./SourceExcerptPanel";
import { sectionLabel } from "./graphPreviewUtils";

interface GraphPreviewHealthStripProps {
  health: GraphPreviewHealth;
  runDir: string;
}

function GraphPreviewHealthStrip({ health, runDir }: GraphPreviewHealthStripProps) {
  return (
    <section className="graph-preview-health" aria-label="Graph preview health">
      <div className="graph-preview-health-row">
        <span className={health.canonical_ir_valid ? "graph-preview-badge ok" : "graph-preview-badge warn"}>
          {health.canonical_ir_valid ? "IR valid" : "IR invalid"}
        </span>
        {health.model_id ? <span className="graph-preview-meta">model {health.model_id}</span> : null}
        {health.scenario_estimated_cost_usd != null ? (
          <span className="graph-preview-meta">
            cost ${health.scenario_estimated_cost_usd.toFixed(4)}
          </span>
        ) : null}
      </div>
      <dl className="graph-preview-counts">
        <div><dt>Nodes</dt><dd>{health.node_count}</dd></div>
        <div><dt>Edges</dt><dd>{health.edge_count}</dd></div>
        <div><dt>Beats</dt><dd>{health.beat_count}</dd></div>
        <div><dt>Evidence</dt><dd>{health.evidence_ref_count}</dd></div>
        <div><dt>Resolvable</dt><dd>{health.resolvable_evidence_ref_count}</dd></div>
      </dl>
      <p className="graph-preview-run-dir"><code>{runDir}</code></p>
      {health.reconcile_error ? (
        <p className="graph-preview-error" role="alert">{health.reconcile_error}</p>
      ) : null}
    </section>
  );
}

interface GraphPreviewProjectionProps {
  payload: GraphPreviewSurfaceResponse;
  runs: GraphPreviewRunSummary[];
  selectedRunDir: string;
  onSelectRun: (runDir: string) => void;
  selectedCandidateId: string | null;
  onSelectCandidate: (objectId: string) => void;
}

export function GraphPreviewProjection({
  payload,
  runs,
  selectedRunDir,
  onSelectRun,
  selectedCandidateId,
  onSelectCandidate,
}: GraphPreviewProjectionProps) {
  const sections = ["nodes", "edges", "beats", "ignored_items", "deferred_items"] as const;
  const grouped = sections.map((section) => ({
    section,
    rows: payload.candidates.filter((row) => row.section === section),
  }));

  const selected: GraphPreviewCandidateRow | undefined = payload.candidates.find(
    (row) => row.object_id === selectedCandidateId,
  );
  const [evidenceIndex, setEvidenceIndex] = useState(0);

  useEffect(() => {
    setEvidenceIndex(0);
  }, [selectedCandidateId]);

  const activeEvidence = selected?.evidence_refs[evidenceIndex] ?? selected?.evidence_refs[0];

  return (
    <div className="graph-preview-root">
      <GraphPreviewHealthStrip health={payload.health} runDir={payload.run_dir} />

      {runs.length > 1 ? (
        <label className="graph-preview-run-picker">
          <span>Run artifact</span>
          <select value={selectedRunDir} onChange={(event) => onSelectRun(event.target.value)}>
            {runs.map((run) => (
              <option key={run.run_dir} value={run.run_dir}>
                {run.model_id ?? "model"} · {run.run_dir.split("/").slice(-1)[0]}
                {run.canonical_ir_valid ? " · valid" : ""}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      <div className="graph-preview-layout">
        <section className="graph-preview-list" aria-label="Candidate objects">
          {grouped.map(({ section, rows }) =>
            rows.length ? (
              <div key={section} className="graph-preview-list-group">
                <h3>{sectionLabel(section)}</h3>
                <ul>
                  {rows.map((row) => (
                    <li key={`${section}:${row.object_id}`}>
                      <button
                        type="button"
                        className={
                          selectedCandidateId === row.object_id ? "graph-preview-list-item active" : "graph-preview-list-item"
                        }
                        onClick={() => onSelectCandidate(row.object_id)}
                      >
                        <strong>{row.label}</strong>
                        <span>{row.kind}</span>
                        <small>{row.evidence_count} evidence</small>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null,
          )}
        </section>

        <section className="graph-preview-detail" aria-label="Selected candidate detail">
          {!selected ? (
            <p className="plan-projection-empty">Select a candidate to inspect evidence and source excerpts.</p>
          ) : (
            <>
              <header className="graph-preview-detail-header">
                <p className="plan-surface-kicker">{sectionLabel(selected.section)}</p>
                <h3>{selected.label}</h3>
                <p className="graph-preview-detail-kind">{selected.kind}</p>
              </header>
              {selected.description ? (
                <p className="graph-preview-detail-description">{selected.description}</p>
              ) : null}
              {selected.evidence_refs.length > 1 ? (
                <ul className="graph-preview-evidence-tabs" aria-label="Evidence refs">
                  {selected.evidence_refs.map((ref, index) => (
                    <li key={`${ref.source_span_ref_id ?? ref.label ?? index}`}>
                      <button
                        type="button"
                        className={evidenceIndex === index ? "active" : undefined}
                        onClick={() => setEvidenceIndex(index)}
                      >
                        {ref.label ?? ref.source_span_ref_id ?? `Evidence ${index + 1}`}
                      </button>
                    </li>
                  ))}
                </ul>
              ) : null}
              {activeEvidence ? <SourceExcerptPanel evidence={activeEvidence} /> : null}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
