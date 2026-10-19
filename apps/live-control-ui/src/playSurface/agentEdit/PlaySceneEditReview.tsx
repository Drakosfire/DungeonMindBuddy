import { useEffect, useRef, useState } from "react";
import { listPlaySceneEdits, proposePlaySceneEdit, type PlaySceneEditRecord } from "../../api/playSceneEditApi";
import type { PlaySceneEditBridge } from "./playSceneEditBridge";
import { ReadOnlyBodyContent } from "../../markdownReader/ReadOnlyBodyContent";
import { markdownToTiptapDoc } from "../../tiptap/markdown/markdownToTiptap";

export function usePlaySceneEdits({ worldId, runId, bridge }: { worldId: string; runId: string | null; bridge: PlaySceneEditBridge | null }) {
  const scope = `${worldId}:${runId ?? ""}`;
  const live = useRef({ scope, bridge }); live.current = { scope, bridge };
  const mounted = useRef(true);
  const [records, setRecords] = useState<{ scope: string; items: PlaySceneEditRecord[] }>({ scope, items: [] });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const running = useRef(false);
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; }; }, []);
  useEffect(() => {
    if (!runId) return;
    let active = true;
    listPlaySceneEdits(worldId, runId).then(items => { if (active) setRecords({ scope, items }); })
      .catch(() => { if (active) setError("Earlier session proposals could not be loaded."); });
    return () => { active = false; };
  }, [scope, worldId, runId, refresh]);
  async function submit(instruction: string) {
    if (!bridge || !runId || running.current) return false;
    running.current = true; setBusy(true); setError(null);
    try {
      const captured = bridge.capture();
      const record = await proposePlaySceneEdit(captured.worldId, captured.runId, crypto.randomUUID(), { ...captured.request, instruction });
      if (!mounted.current || live.current.scope !== scope) return false;
      setRecords(previous => ({ scope, items: [record, ...(previous.scope === scope ? previous.items.filter(item => item.proposal_id !== record.proposal_id) : [])].slice(0, 20) }));
      return true;
    } catch (reason) {
      if (mounted.current && live.current.scope === scope) {
        setError(`${reason instanceof Error ? reason.message : "The proposal outcome is unknown."} Refresh proposals to check it; it will not be sent again automatically.`);
        setRefresh(value => value + 1);
      }
      return false;
    } finally { running.current = false; if (mounted.current) setBusy(false); }
  }
  async function apply(record: PlaySceneEditRecord) {
    setError(null);
    try { if (!live.current.bridge) throw new Error("Open the saved session copy first."); await live.current.bridge.apply(record); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "The scene edit could not be applied."); }
  }
  const review = runId ? <section aria-label="Session scene edit proposals">
    {records.scope === scope ? records.items.map(record => <article key={record.proposal_id} className="build-compose-proposal">
      <h3>Scene edit · session copy</h3>
      <p>{record.instruction}</p>
      {record.status === "pending" ? <p role="status">Generation has not confirmed an outcome. Refresh to check; a new request is never sent automatically.</p> : null}
      {record.status === "failed" ? <p role="alert">Buddy could not prepare this scene edit. Your session was not changed.</p> : null}
      {record.result ? <>
        <p>{record.result.summary}</p>
        <details><summary>Before</summary><ReadOnlyBodyContent content={markdownToTiptapDoc(record.result.before_markdown).doc.content} fallbackText={record.result.before_markdown} /></details>
        <details open><summary>Proposed scene</summary><ReadOnlyBodyContent content={markdownToTiptapDoc(record.result.replacement_markdown).doc.content} fallbackText={record.result.replacement_markdown} /></details>
        {record.result.assumptions.length ? <details><summary>Assumptions</summary><ul>{record.result.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul></details> : null}
        <button type="button" disabled={!bridge?.matches(record) || busy} onClick={() => { void apply(record); }}>Apply to session copy</button>
        {!bridge?.matches(record) ? <p>This proposal is historical or the scene has changed. Ask for a fresh edit to apply changes.</p> : null}
      </> : null}
    </article>) : null}
    <button type="button" onClick={() => setRefresh(value => value + 1)} disabled={busy}>Refresh scene proposals</button>
    {error ? <p role="alert">{error}</p> : null}
  </section> : null;
  return { busy, error, submit, review };
}
