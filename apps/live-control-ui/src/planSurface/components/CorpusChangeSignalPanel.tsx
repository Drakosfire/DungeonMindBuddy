import type { CitationFreshnessStatus } from "../../api/types";

interface CorpusChangeSignalPanelProps {
  status: CitationFreshnessStatus;
  snapshotCount: number;
  checkedAt?: string | null;
  warnings?: string[];
  checking?: boolean;
  onCheck: () => void;
}

const copy: Record<CitationFreshnessStatus, { title: string; body: string }> = {
  current: {
    title: "Corpus signal: Current",
    body: "Cited source locator still matches the stored snapshot.",
  },
  changed: {
    title: "Corpus signal: Changed",
    body: "The cited source appears to have changed since this answer was stored. Re-ask before relying on it.",
  },
  unknown: {
    title: "Corpus signal: Unknown",
    body: "This turn does not have enough snapshot data to compare current corpus state.",
  },
  unavailable: {
    title: "Corpus signal: Unavailable",
    body: "The cited source could not be checked. It may have moved or been removed.",
  },
};

export function CorpusChangeSignalPanel({
  status,
  snapshotCount,
  checkedAt,
  warnings = [],
  checking = false,
  onCheck,
}: CorpusChangeSignalPanelProps) {
  const details = copy[status] ?? copy.unknown;
  return (
    <section className="plan-agent-corpus-signal" data-status={status} aria-label="Corpus change signal">
      <div>
        <p className="plan-surface-kicker">Corpus change signal</p>
        <h4>{details.title}</h4>
        <p>{details.body}</p>
        <p className="plan-agent-muted">
          {snapshotCount ? `${snapshotCount} lightweight evidence snapshot${snapshotCount === 1 ? "" : "s"} stored.` : "No evidence snapshots stored."}
          {checkedAt ? ` Checked ${new Date(checkedAt).toLocaleString()}.` : ""}
        </p>
        {warnings.length ? <p className="plan-agent-warning">{warnings.join(" ")}</p> : null}
      </div>
      <button type="button" onClick={onCheck} disabled={checking || snapshotCount === 0}>
        {checking ? "Checking…" : "Check current source state"}
      </button>
    </section>
  );
}
