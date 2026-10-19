import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { changeWorkspaceTrash, listWorkspaceTrash, type WorkspaceTrashItem, type WorkspaceTrashTarget } from "./workspaceTrashApi";
import "./workspaceTrash.css";

/** Lifecycle controls share a view; each owning writer still controls whether deletion is safe. */
export function WorkspaceTrashControl({ worldId, current, blocked = false, onTrashed, onRestored }: {
  worldId: string;
  current: WorkspaceTrashTarget | null;
  blocked?: boolean;
  onTrashed: () => void;
  onRestored?: () => void;
}) {
  const [view, setView] = useState<"closed" | "delete" | "trash">("closed");
  const [confirmation, setConfirmation] = useState<{ worldId: string; identity: string; target: WorkspaceTrashTarget } | null>(null);
  const [items, setItems] = useState<WorkspaceTrashItem[]>([]);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const sequence = useRef(0);
  const mounted = useRef(true);
  const identity = JSON.stringify([worldId, current?.kind, current?.id, current?.surface, current?.revision, current?.content_revision]);
  const latest = useRef({ worldId, current, blocked, identity });
  latest.current = { worldId, current, blocked, identity };
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; sequence.current++; }; }, []);
  useEffect(() => { sequence.current++; setView("closed"); setConfirmation(null); setPending(false); setError(null); setNotice(null); }, [worldId, current?.id]);
  useEffect(() => {
    if (confirmation && confirmation.identity !== identity) {
      sequence.current++;
      setView("closed"); setConfirmation(null); setPending(false);
    }
  }, [identity, confirmation]);
  useEffect(() => {
    const node = dialog.current;
    if (view !== "closed" && node && !node.open) node.showModal();
    return () => { if (node?.open) node.close(); };
  }, [view]);

  const open = async (next: "delete" | "trash") => {
    if (next === "delete" && (!current || blocked)) return;
    setConfirmation(next === "delete" && current ? { worldId, identity, target: { ...current } } : null);
    setView(next); setError(null); setNotice(null);
    if (next !== "trash") return;
    const stamp = ++sequence.current;
    setPending(true); setItems([]);
    try {
      const loaded = await listWorkspaceTrash(worldId);
      if (mounted.current && sequence.current === stamp) setItems(loaded);
    } catch (cause) {
      if (mounted.current && sequence.current === stamp) setError(cause instanceof Error ? cause.message : "Trash could not be loaded.");
    } finally { if (mounted.current && sequence.current === stamp) setPending(false); }
  };
  const change = async (target: WorkspaceTrashTarget, action: "trash" | "restore") => {
    if (pending || (action === "trash" && (latest.current.blocked || (!confirmation || latest.current.identity !== confirmation.identity)))) return;
    const stamp = ++sequence.current;
    const capturedWorld = action === "trash" ? confirmation!.worldId : worldId;
    setPending(true); setError(null); setNotice(null);
    try {
      await changeWorkspaceTrash(capturedWorld, target, action);
      if (!mounted.current || sequence.current !== stamp || latest.current.worldId !== capturedWorld || (action === "trash" && latest.current.identity !== confirmation!.identity)) return;
      if (action === "trash") { setView("closed"); onTrashed(); }
      else { setItems(old => old.filter(item => item.id !== target.id || item.kind !== target.kind)); setNotice(`Restored “${target.title}”.`); onRestored?.(); }
    } catch (cause) {
      if (mounted.current && sequence.current === stamp) setError(cause instanceof Error ? cause.message : "The action could not be confirmed. Reload to check its state.");
    } finally { if (mounted.current && sequence.current === stamp) setPending(false); }
  };
  return <>
    {current ? <button type="button" disabled={blocked || pending} title={blocked ? "Finish saving changes before deleting." : undefined}
      onClick={() => { void open("delete"); }}>Delete</button> : null}
    <button type="button" onClick={() => { void open("trash"); }}>Trash</button>
    {view !== "closed" && (view !== "delete" || confirmation?.identity === identity) ? createPortal(<dialog ref={dialog} className="workspace-trash" aria-label={view === "delete" ? "Move to Trash" : "World Trash"}
      onCancel={event => { if (pending) event.preventDefault(); else setView("closed"); }}>
      <header><h2>{view === "delete" ? "Move to Trash?" : "Trash"}</h2><button type="button" disabled={pending} onClick={() => setView("closed")} aria-label="Close Trash">×</button></header>
      {view === "delete" && confirmation ? <>
        <p><strong>{confirmation.target.title}</strong></p>
        <p>{confirmation.target.kind === "session" ? "This moves the whole Play session, including its scene notes, out of your session list. The Plan stays unchanged."
          : confirmation.target.surface === "plan" ? "This removes the Plan from your document list. Sessions already created from it stay available."
          : "This removes the Build document from your source list. Published graph evidence stays available."}</p>
        <p>You can restore it from Trash. Images and saved history are retained.</p>
        {blocked ? <p role="status">Finish saving your changes before deleting.</p> : null}
        <button type="button" disabled={blocked || pending} onClick={() => { void change(confirmation.target, "trash"); }}>Move to Trash</button>
        <button type="button" disabled={pending} onClick={() => setView("closed")}>Cancel</button>
      </> : <>
        <p>Deleted documents and sessions in this World. Restore keeps their content, notes and history.</p>
        {!pending && !error && items.length === 0 ? <p>Trash is empty.</p> : null}
        <ul>{items.map(item => <li key={`${item.kind}:${item.id}`}><div><strong>{item.title}</strong><small>{item.surface === "play" ? "Play session" : item.surface === "plan" ? "Plan" : "Build document"}</small></div>
          <button type="button" disabled={pending} onClick={() => { void change(item, "restore"); }}>Restore <span className="workspace-trash__sr">{item.title}</span></button></li>)}</ul>
      </>}
      {pending ? <p role="status">Working…</p> : null}
      {notice ? <p role="status">{notice}</p> : null}
      {error ? <p role="alert">{error}</p> : null}
    </dialog>, document.body) : null}
  </>;
}
