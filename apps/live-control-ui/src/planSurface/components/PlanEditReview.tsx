import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { MarkdownDocumentReader } from "../../markdownReader/MarkdownDocumentReader";
import type { WorldPlanEditContextualPreview } from "../agentEdit/planAgentEditProposal";
import "./PlanEditReview.css";

export type PlanEditReviewPreview = WorldPlanEditContextualPreview["before"];
export interface PlanEditReviewProps {
  targetLabel: string;
  before: PlanEditReviewPreview;
  after: PlanEditReviewPreview;
  status: "review" | "applying" | "applied" | "saved" | "stale";
  onApply: () => void;
  onDiscard: () => void;
  saveAction?: { onSave: () => void; disabled?: boolean; label?: string };
  details?: ReactNode;
}

/** Presentation only: the owning controller supplies frozen Apply-equivalent previews and guarded actions. */
export function PlanEditReview({ targetLabel, before, after, status, onApply, onDiscard, saveAction, details }: PlanEditReviewProps) {
  const id = useId();
  const [large, setLarge] = useState(false);
  const expand = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  function restore() { setLarge(false); expand.current?.focus({ preventScroll: true }); }
  function keys(event: KeyboardEvent<HTMLElement>) {
    if (!large) return;
    if (event.key === "Escape" || event.key === "Tab") event.stopPropagation();
    if (event.key === "Escape") { event.preventDefault(); restore(); }
    if (event.key === "Tab") {
      const controls = Array.from(panel.current?.querySelectorAll<HTMLElement>("button:not(:disabled),a[href],summary") ?? []).filter(node => node.getClientRects().length > 0 && (!node.closest("details") || node.closest("details")!.open || node.tagName === "SUMMARY"));
      const first = controls[0], last = controls[controls.length - 1];
      if (event.shiftKey && document.activeElement === first && last) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last && first) { event.preventDefault(); first.focus(); }
    }
  }
  const message = status === "applied" ? "Applied to your draft. Save Plan keeps this change."
    : status === "saved" ? "Saved to your Plan."
    : status === "stale" ? "The Plan changed. This preview cannot be applied."
    : status === "applying" ? "Applying to your draft…" : "Review the highlighted change before applying it.";
  return <section ref={panel} className={`plan-edit-review ${large ? "is-large" : ""}`} role={large ? "dialog" : "region"} aria-modal={large || undefined} aria-labelledby={`${id}-title`} onKeyDown={keys}>
    <header className="plan-edit-review__heading">
      <div><h4 id={`${id}-title`}>Change {targetLabel}</h4><p>{message}</p></div>
      <button ref={expand} type="button" aria-expanded={large} onClick={() => setLarge(!large)}>{large ? "Restore inline review" : "Expand review"}</button>
    </header>
    <div className="plan-edit-review__comparison">
      {([ ["Before", before], ["After", after] ] as const).map(([label, preview]) => <section key={label} aria-label={`${label} ${targetLabel}`} className="plan-edit-review__version">
        <h5>{label}</h5>{preview.placementLabel && <p className="plan-edit-review__placement">{preview.placementLabel}</p>}
        <MarkdownDocumentReader markdown={preview.markdown} sourceLineTarget={preview.sourceLineTarget} />
      </section>)}
    </div>
    {details && <details className="plan-edit-review__details"><summary>Details</summary>{details}</details>}
    <footer className="plan-edit-review__actions">
      {status === "review" ? <><button type="button" onClick={onDiscard}>Discard proposal</button><button type="button" onClick={onApply}>Apply to draft</button></> : null}
      {status === "applying" && <button type="button" disabled>Applying…</button>}
      {status === "applied" && (saveAction ? <button type="button" disabled={saveAction.disabled} onClick={saveAction.onSave}>{saveAction.label ?? "Save Plan"}</button> : <p>Open Edit, then choose Save Plan to keep this change.</p>)}
    </footer>
  </section>;
}
