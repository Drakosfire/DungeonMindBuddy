import { useId, useMemo, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { splitLeadingYamlFrontmatter } from "../../tiptap/markdown/stripLeadingYamlFrontmatter";
import { parsePlayableHtmlComment } from "../../tiptap/playable/playableElementIdentity";
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

/** Derive display coordinates only; the controller's frozen source is never rewritten. */
function changedSourceRanges(before: PlanEditReviewPreview, after: PlanEditReviewPreview) {
  const oldLines = before.markdown.split("\n"), newLines = after.markdown.split("\n");
  let prefix = 0;
  while (prefix < oldLines.length && prefix < newLines.length && oldLines[prefix] === newLines[prefix]) prefix++;
  let suffix = 0;
  while (suffix < oldLines.length - prefix && suffix < newLines.length - prefix
    && oldLines[oldLines.length - suffix - 1] === newLines[newLines.length - suffix - 1]) suffix++;
  const target = (preview: PlanEditReviewPreview, lines: string[], end: number, side: string) => {
    const changed = end > prefix;
    if (prefix === oldLines.length && prefix === newLines.length) return { target: null, changed: false, unchanged: true };
    const removedLength = splitLeadingYamlFrontmatter(preview.markdown).removedLength;
    const firstBodyLine = (preview.markdown.slice(0, removedLength).match(/\n/g) ?? []).length;
    const meaningful = (index: number) => index >= firstBodyLine && Boolean(lines[index]?.trim())
      && parsePlayableHtmlComment(lines[index]).status !== "canonical";
    let start = prefix;
    if (changed && !lines.slice(prefix, end).some((_, offset) => meaningful(prefix + offset))) {
      return { target: null, changed: true, unchanged: false };
    }
    if (!changed) {
      // Pure insertions/deletions show their adjacent context on the unchanged side.
      start = Math.min(prefix, lines.length - 1);
      while (start < lines.length && !meaningful(start)) start++;
      if (start === lines.length) {
        start = Math.min(prefix - 1, lines.length - 1);
        while (start >= 0 && !meaningful(start)) start--;
      }
      if (start < 0) return { target: null, changed: false, unchanged: false };
    }
    return { target: { startLine: start + 1, endLine: changed ? end : start + 1,
      targetKey: `${preview.sourceLineTarget?.targetKey ?? side}:change:${prefix}:${end}` }, changed, unchanged: false };
  };
  return { before: target(before, oldLines, oldLines.length - suffix, "before"),
    after: target(after, newLines, newLines.length - suffix, "after") };
}

/** Presentation only: the owning controller supplies frozen Apply-equivalent previews and guarded actions. */
export function PlanEditReview({ targetLabel, before, after, status, onApply, onDiscard, saveAction, details }: PlanEditReviewProps) {
  const id = useId();
  const [large, setLarge] = useState(false);
  const expand = useRef<HTMLButtonElement>(null);
  const panel = useRef<HTMLElement>(null);
  const changes = useMemo(() => changedSourceRanges(before, after), [before, after]);
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
    : status === "stale" ? "This preview is no longer current. It cannot be applied."
    : status === "applying" ? "Applying to your draft…" : "Review the highlighted change before applying it.";
  return <section ref={panel} className={`plan-edit-review ${large ? "is-large" : ""}`} role={large ? "dialog" : "region"} aria-modal={large || undefined} aria-labelledby={`${id}-title`} onKeyDown={keys}>
    <header className="plan-edit-review__heading">
      <div><h4 id={`${id}-title`}>Change {targetLabel}</h4><p>{message}</p></div>
      <button ref={expand} type="button" aria-expanded={large} onClick={() => setLarge(!large)}>{large ? "Restore inline review" : "Expand review"}</button>
    </header>
    <div className="plan-edit-review__comparison">
      {([ ["Before", before, changes.before], ["After", after, changes.after] ] as const).map(([label, preview, change]) => <section key={label} aria-label={`${label} ${targetLabel}`} className="plan-edit-review__version" data-change-kind={change.unchanged ? "unchanged" : change.changed ? label === "Before" ? "removed" : "added" : "context"}>
        <h5>{label} <span className="plan-edit-review__change-label">{change.unchanged ? "Unchanged" : change.changed ? label === "Before" ? "Removed / replaced" : "Added / replaced" : label === "Before" ? "Insertion point · no text removed" : "Deletion point · no text added"}</span></h5>{preview.placementLabel && <p className="plan-edit-review__placement">{preview.placementLabel}</p>}
        <MarkdownDocumentReader markdown={preview.markdown} sourceLineTarget={change.target ? { ...change.target, targetKey: `${change.target.targetKey}:${large ? "expanded" : "inline"}` } : change.target} hidePlayableMarkers />
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
