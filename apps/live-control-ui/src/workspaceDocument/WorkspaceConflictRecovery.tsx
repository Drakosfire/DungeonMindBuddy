import { WorkspaceConflictDiff } from "./WorkspaceConflictDiff";
import { useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import type { WorkspaceConflictRecovery as Recovery, WorkspaceConflictReview } from "./workspaceConflictRecovery";
import "./workspaceConflictRecovery.css";

function CopiesDownload({ text }: { text: string }) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    const next = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    setUrl(next);
    return () => URL.revokeObjectURL(next);
  }, [text]);
  return url ? <a href={url} download="document-conflict-copies.json">Download protected copies</a> : null;
}

/** Comparison is independent of a mounted editor: conflicts intentionally have none. */
export function WorkspaceConflictRecovery({ recovery, allowReview = true }: { recovery?: Recovery; allowReview?: boolean }) {
  const [review, setReview] = useState<WorkspaceConflictReview | null>(null);
  const [viewOnly, setViewOnly] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const dialog = useRef<HTMLDialogElement>(null);
  const label = useId();
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);
  useEffect(() => { if (review && dialog.current && !dialog.current.open) dialog.current.showModal(); }, [review]);
  if (!recovery) return null;
  const choose = async (choice: "local" | "saved") => {
    if (!review || busy || viewOnly) return;
    setBusy(true); setError(null);
    try { await recovery.resolve(review, choice); if (alive.current) setReview(null); }
    catch (cause) { if (alive.current) setError(cause instanceof Error ? cause.message : "The copies were kept. Reopen the comparison."); }
    finally { if (alive.current) setBusy(false); }
  };
  return <div className="workspace-conflict-recovery">
    {allowReview ? <button type="button" onClick={() => {
      try { setReview(recovery.prepare()); setViewOnly(false); setError(null); }
      catch (cause) { setError(cause instanceof Error ? cause.message : "The comparison could not be opened."); }
    }}>Review conflicting copies</button> : null}
    {recovery.protectedCopies ? <>
      <button type="button" onClick={() => {
        try {
          const bundle = JSON.parse(recovery.protectedCopies!);
          const copy = bundle.schema === "dmb_workspace_conflict_copies_v1" && Array.isArray(bundle.copies) ? bundle.copies.at(-1) : null;
          if (!copy || typeof copy.local?.exported_markdown !== "string" || !copy.local.tiptap_json || typeof copy.saved?.markdown !== "string") throw new Error("Protected copies could not be displayed. Download them to inspect the retained data.");
          setReview({ ...copy, fence:"" }); setViewOnly(true); setError(null);
        } catch (cause) { setError(cause instanceof Error ? cause.message : "Protected copies could not be displayed."); }
      }}>Review protected copies</button>
      <CopiesDownload text={recovery.protectedCopies} />
    </> : null}
    {error && !review ? <p role="alert">{error}</p> : null}
    {review ? createPortal(<dialog ref={dialog} className="workspace-conflict-review" aria-labelledby={label}
      onCancel={event => { if (busy) event.preventDefault(); else setReview(null); }}>
      <h2 id={label}>{viewOnly ? "Protected recovery copies" : "Choose a working copy"}</h2>
      <p>{viewOnly ? "These copies were protected during a previous resolution. Reviewing them does not change your current document." : "The browser draft and saved document differ. Both complete copies will be protected in this browser before your choice replaces the working copy."}</p>
      <WorkspaceConflictDiff saved={review.saved.markdown} local={review.local.exported_markdown} />
      <details><summary>Full browser draft · based on version {review.local.base_revision}</summary>
        <pre>{review.local.exported_markdown}</pre>
        <details><summary>Full browser editor data (including media)</summary><pre>{JSON.stringify(review.local.tiptap_json, null, 2)}</pre></details>
      </details>
      <details><summary>Full saved document · version {review.saved.loaded_revision}</summary><pre>{review.saved.markdown}</pre></details>
      <CopiesDownload text={JSON.stringify({ local: review.local, saved: review.saved }, null, 2)} />
      {!viewOnly ? <p>Use saved version leaves the server unchanged. Use browser draft opens your local content against the reviewed saved version and resumes normal saving.</p> : null}
      {!viewOnly && review.local.exported_markdown_authoritative ? <p>This browser draft also has protected Markdown. If you choose it, review the protected draft in the editor before saving; that separate protection stays in place.</p> : null}
      {error ? <p role="alert">{error}</p> : null}
      <footer>
        {!viewOnly ? <>
          <button type="button" disabled={busy} onClick={() => { void choose("saved"); }}>Use saved version</button>
          <button type="button" disabled={busy} onClick={() => { void choose("local"); }}>Use browser draft</button>
        </> : null}
        <button type="button" disabled={busy} onClick={() => setReview(null)}>{viewOnly ? "Close" : "Cancel"}</button>
      </footer>
      {busy ? <p role="status">Checking both copies and protecting a backup…</p> : null}
    </dialog>, document.body) : null}
  </div>;
}
