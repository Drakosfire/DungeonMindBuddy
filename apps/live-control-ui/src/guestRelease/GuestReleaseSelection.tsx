import { useState } from "react";

type Field = { assertion_id: string; entity_id: string; kind: "name" | "classification" | "relationship"; value: string; predicate: string; target_id: string | null; temporal: string; evidence_ids: string[] };
type Source = { document_id: string; document_title: string; visibility: string; revision_n: number; sha256: string; start: number; end: number; excerpt: string; evidence_id: string };
type Options = { graph_revision: string; fields: Field[]; sources: Source[] };

/** Private owner selection; every field and supporting excerpt starts unselected. */
export function GuestReleaseSelection({ worldId, onPrepared }: { worldId: string; onPrepared: () => void }) {
  const [options, setOptions] = useState<Options | null>(null);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prepared, setPrepared] = useState(false);
  const base = `/api/live/worlds/${encodeURIComponent(worldId)}/guest-releases`;
  async function load() {
    setBusy(true); setError(null); setOptions(null); setChosen({}); setPrepared(false);
    try {
      const response = await fetch(`${base}/selection-options`, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error("unavailable");
      setOptions(await response.json() as Options);
    } catch { setError("Could not load release options. Try again."); }
    finally { setBusy(false); }
  }
  const selected = options?.fields.filter(field => Object.hasOwn(chosen, field.assertion_id)) ?? [];
  const nodes = new Map<string, { name?: Field; classification?: Field; duplicate: boolean }>();
  for (const field of selected) {
    if (field.kind === "relationship") continue;
    const item = nodes.get(field.entity_id) ?? { duplicate: false };
    if (item[field.kind]) item.duplicate = true;
    item[field.kind] = field;
    nodes.set(field.entity_id, item);
  }
  const sources = new Map(options?.sources.map(source => [source.evidence_id, source]) ?? []);
  const ready = nodes.size > 0 && [...nodes.values()].every(node => node.name && node.classification && !node.duplicate)
    && selected.every(field => field.evidence_ids.includes(chosen[field.assertion_id]) && sources.has(chosen[field.assertion_id]))
    && selected.filter(field => field.kind === "relationship").every(field => nodes.has(field.entity_id) && field.target_id !== null && nodes.has(field.target_id));
  async function prepare() {
    if (!options || !ready) return;
    const evidenceIds = [...new Set(selected.map(field => chosen[field.assertion_id]))];
    const body = {
      graph_revision: options.graph_revision,
      nodes: [...nodes].map(([entity_id, item]) => ({ entity_id, name_assertion_id: item.name!.assertion_id,
        kind_assertion_id: item.classification!.assertion_id, name_source_index: evidenceIds.indexOf(chosen[item.name!.assertion_id]),
        kind_source_index: evidenceIds.indexOf(chosen[item.classification!.assertion_id]) })),
      relationships: selected.filter(field => field.kind === "relationship").map(field => ({ assertion_id: field.assertion_id,
        subject_id: field.entity_id, predicate: field.predicate, evidence_id: chosen[field.assertion_id],
        source_index: evidenceIds.indexOf(chosen[field.assertion_id]) })),
      sources: evidenceIds.map(id => { const source = sources.get(id)!; return { document_id: source.document_id,
        revision_n: source.revision_n, sha256: source.sha256, start: source.start, end: source.end,
        excerpt: source.excerpt, evidence_id: source.evidence_id }; }), asset_ids: [],
    };
    setBusy(true); setError(null);
    try {
      const response = await fetch(base, { method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      if (!response.ok) throw new Error("unavailable");
      setPrepared(true); onPrepared();
    } catch { setError("Could not prepare this copy. Options may have changed or preparation may be unavailable; reload and try again."); }
    finally { setBusy(false); }
  }
  const labels = new Map(options?.fields.filter(field => field.kind === "name").map(field => [field.entity_id, field.value]) ?? []);
  return <section aria-labelledby="guest-selection-heading">
    <h3 id="guest-selection-heading">Choose what to share</h3>
    <p>Choose each name, classification, relationship and supporting excerpt. Preparing a copy does not publish it.</p>
    <p>Only supported, evidenced facts with unknown or timeless scope are shown. Other claims, summaries, dated events, and images cannot yet be selected here.</p>
    <button type="button" disabled={busy} onClick={load}>Load selection options</button>
    {error && <p role="alert">{error}</p>}
    {prepared && <p role="status">Copy prepared. Load prepared copies below to review it.</p>}
    {options && <div>
      {options.fields.length === 0 && <p>No eligible fields found for this Graph revision.</p>}
      <ul>{options.fields.map(field => <li key={field.assertion_id}>
        <label><input type="checkbox" checked={Object.hasOwn(chosen, field.assertion_id)} disabled={busy}
          onChange={event => { const checked = event.target.checked; setChosen(previous => { const next = { ...previous }; if (checked) next[field.assertion_id] = ""; else delete next[field.assertion_id]; return next; }); }} />{" "}
          {labels.get(field.entity_id) ?? "Unnamed object"} · {field.kind}: {field.value}{field.target_id ? ` → ${labels.get(field.target_id) ?? "unnamed object"}` : ""} · {field.temporal}
        </label>
        {Object.hasOwn(chosen, field.assertion_id) && <label> Supporting excerpt <select value={chosen[field.assertion_id]} disabled={busy}
          onChange={event => { const value = event.target.value; setChosen(previous => ({ ...previous, [field.assertion_id]: value })); }}>
          <option value="">Choose an excerpt</option>{field.evidence_ids.map(id => <option key={id} value={id}>{sources.get(id)?.document_title ?? "Source"} · {sources.get(id)?.visibility === "internal" ? "private" : "player-safe"}</option>)}
        </select></label>}
      </li>)}</ul>
      {[...new Set(Object.values(chosen).filter(Boolean))].map(id => { const source = sources.get(id); return source && <section key={id}>
        <h4>{source.document_title} · {source.visibility === "internal" ? "private source" : "player-safe source"}</h4><p style={{ whiteSpace: "pre-wrap" }}>{source.excerpt}</p>
      </section>; })}
      <p>For each object, select exactly one name and classification. Relationships require both objects and an excerpt.</p>
      <button type="button" disabled={!ready || busy} onClick={prepare}>Prepare copy for review</button>
    </div>}
  </section>;
}
