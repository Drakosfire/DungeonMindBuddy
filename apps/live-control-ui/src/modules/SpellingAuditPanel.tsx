import type { RecapIngestStatus } from "../api/types";

interface SpellingAuditPanelProps {
  result: RecapIngestStatus | null;
}

export function SpellingAuditPanel({ result }: SpellingAuditPanelProps) {
  const rows = result?.entity_spelling_audit ?? [];
  return (
    <section className="spelling-audit-panel">
      <h4>Spelling / Entity audit</h4>
      <p className="module-muted">Review only. No auto-corrections are applied.</p>
      {rows.length === 0 ? (
        <p className="module-muted">No spelling variants detected.</p>
      ) : (
        <ul>
          {rows.map((row, idx) => {
            const canonical = String(row.canonical_guess ?? "unknown");
            const variants = Array.isArray(row.variants)
              ? row.variants.map((v) => String(v)).join(", ")
              : "unknown";
            const action = String(row.action ?? "review_only");
            return (
              <li key={`${canonical}-${idx}`}>
                <strong>{canonical}</strong> ← {variants} ({action})
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
