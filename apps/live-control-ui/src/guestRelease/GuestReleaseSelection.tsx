import { useState } from "react";
import { isSavedChoice } from "./savedChoice";

type Field = { assertion_id: string; entity_id: string; kind: "name" | "classification" | "relationship"; value: string; predicate: string; target_id: string | null; temporal: string; basis: string; source_option_ids: string[] };
type Source = { option_id: string; document_id: string; document_title: string; visibility: string; revision_n: number; sha256: string; start: number; end: number; excerpt: string; evidence_id: string; evidence_role: "support" | "context" };
type Options = { graph_revision: string; fields: Field[]; sources: Source[]; source_options_truncated: boolean; context_documents: { document_id: string; title: string }[]; next_offset: number | null };
type Asset = { id: string; width: number; height: number; created_at: string };
type Cursor = { before_time: string; before_id: string };

/** Private owner selection; every field and supporting excerpt starts unselected. */
export function GuestReleaseSelection({ worldId, onPrepared }: { worldId: string; onPrepared: () => void }) {
  const [options, setOptions] = useState<Options | null>(null);
  const [chosen, setChosen] = useState<Record<string, string>>({});
  const [independentSources, setIndependentSources] = useState<Set<string>>(new Set());
  const [contextDocument, setContextDocument] = useState("");
  const [contextOffset, setContextOffset] = useState<number | null>(0);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prepared, setPrepared] = useState(false);
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [nextAssets, setNextAssets] = useState<Cursor | null>(null);
  const [selectedAssets, setSelectedAssets] = useState<Set<string>>(new Set());
  const [loadedAssets, setLoadedAssets] = useState<Set<string>>(new Set());
  const [exampleEnabled, setExampleEnabled] = useState(false);
  const [exampleTitle, setExampleTitle] = useState("");
  const [exampleBody, setExampleBody] = useState("");
  const [exampleReferences, setExampleReferences] = useState<Set<string>>(new Set());
  const [exampleImage, setExampleImage] = useState("");
  const [exampleImageDescription, setExampleImageDescription] = useState("");
  const [choiceEnabled, setChoiceEnabled] = useState(false);
  const [choicePrompt, setChoicePrompt] = useState("");
  const [choiceLabels, setChoiceLabels] = useState<[string, string]>(["", ""]);
  const [choiceOutcomes, setChoiceOutcomes] = useState<[string, string]>(["", ""]);
  const base = `/api/live/worlds/${encodeURIComponent(worldId)}/guest-releases`;
  async function load() {
    setBusy(true); setError(null); setOptions(null); setChosen({}); setIndependentSources(new Set()); setContextDocument(""); setContextOffset(0); setPrepared(false);
    setExampleEnabled(false); setExampleTitle(""); setExampleBody(""); setExampleReferences(new Set()); setExampleImage(""); setExampleImageDescription("");
    setChoiceEnabled(false); setChoicePrompt(""); setChoiceLabels(["", ""]); setChoiceOutcomes(["", ""]);
    try {
      const response = await fetch(`${base}/selection-options`, { credentials: "same-origin", cache: "no-store" });
      if (!response.ok) throw new Error("unavailable");
      setOptions(await response.json() as Options);
    } catch { setError("Could not load release options. Try again."); }
    finally { setBusy(false); }
  }
  async function loadContext() {
    if (!options || !contextDocument || contextOffset === null) return;
    setBusy(true); setError(null);
    try {
      const response = await fetch(`${base}/selection-context`, { method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ document_id: contextDocument, offset: contextOffset }) });
      if (!response.ok) throw new Error("unavailable");
      const page = await response.json() as Options;
      if (page.graph_revision !== options.graph_revision) throw new Error("changed");
      setOptions(previous => previous && { ...previous, sources: [...previous.sources, ...page.sources.filter(source =>
        !previous.sources.some(existing => existing.document_id === source.document_id && existing.revision_n === source.revision_n
          && existing.evidence_id === source.evidence_id && existing.start === source.start && existing.end === source.end))] });
      setContextOffset(page.next_offset);
    } catch { setError("Could not load excerpts. The Graph or source may have changed; reload selection options."); }
    finally { setBusy(false); }
  }
  async function loadImages(cursor?: Cursor) {
    setBusy(true); setError(null);
    if (!cursor) { setAssets(null); setSelectedAssets(new Set()); setLoadedAssets(new Set()); setExampleImage(""); setExampleImageDescription(""); }
    try {
      const response = await fetch(`${base}/selection-media/list`, { method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(cursor ?? {}) });
      if (!response.ok) throw new Error("unavailable");
      const page = await response.json() as { assets: Asset[]; next: Cursor | null };
      setAssets(previous => cursor ? [...(previous ?? []), ...page.assets.filter(item => !(previous ?? []).some(old => old.id === item.id))] : page.assets);
      setNextAssets(page.next);
    } catch { setError("Could not load World images. Try again."); }
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
  const sources = new Map(options?.sources.map(source => [source.option_id, source]) ?? []);
  const evidenceIds = [...new Set([...selected.map(field => chosen[field.assertion_id]).filter(Boolean), ...independentSources])];
  const referenceSpans = [...exampleReferences].map(id => {
    const source = sources.get(id);
    return source && JSON.stringify([source.document_id, source.revision_n, source.start, source.end]);
  });
  const exampleReady = !exampleEnabled || (exampleTitle.trim().length > 0 && exampleBody.trim().length > 0
    && exampleReferences.size >= 2 && exampleReferences.size <= 10
    && [...exampleReferences].every(id => evidenceIds.includes(id))
    && referenceSpans.every(Boolean) && new Set(referenceSpans).size === referenceSpans.length
    && (!exampleImage || (selectedAssets.has(exampleImage) && loadedAssets.has(exampleImage) && exampleImageDescription.trim().length > 0)));
  const choiceReady = !choiceEnabled || (exampleEnabled && isSavedChoice({ version: "owner_saved_choice_v1", prompt: choicePrompt,
    options: choiceLabels.map((label, index) => ({ label, outcome: choiceOutcomes[index] })) }));
  const ready = nodes.size > 0 && [...nodes.values()].every(node => node.name && node.classification && !node.duplicate)
    && evidenceIds.length <= 500 && [...independentSources].every(id => sources.get(id)?.evidence_role === "context")
    && selected.every(field => field.source_option_ids.includes(chosen[field.assertion_id]) && sources.has(chosen[field.assertion_id]))
    && selected.filter(field => field.kind === "relationship").every(field => nodes.has(field.entity_id) && field.target_id !== null && nodes.has(field.target_id));
  async function prepare() {
    if (!options || !ready || !exampleReady || !choiceReady) return;
    const body = {
      graph_revision: options.graph_revision,
      nodes: [...nodes].map(([entity_id, item]) => ({ entity_id, name_assertion_id: item.name!.assertion_id,
        kind_assertion_id: item.classification!.assertion_id, name_source_index: evidenceIds.indexOf(chosen[item.name!.assertion_id]),
        kind_source_index: evidenceIds.indexOf(chosen[item.classification!.assertion_id]) })),
      relationships: selected.filter(field => field.kind === "relationship").map(field => ({ assertion_id: field.assertion_id,
        subject_id: field.entity_id, predicate: field.predicate, evidence_id: sources.get(chosen[field.assertion_id])!.evidence_id,
        source_index: evidenceIds.indexOf(chosen[field.assertion_id]) })),
      sources: evidenceIds.map(id => { const source = sources.get(id)!; return { document_id: source.document_id,
        revision_n: source.revision_n, sha256: source.sha256, start: source.start, end: source.end,
        excerpt: source.excerpt, evidence_id: source.evidence_id }; }), asset_ids: [...selectedAssets],
      ...(exampleEnabled ? { saved_example: { title: exampleTitle, body: exampleBody,
        source_indexes: [...exampleReferences].map(id => evidenceIds.indexOf(id)),
        asset_id: exampleImage || null, image_description: exampleImage ? exampleImageDescription : null } } : {}),
      ...(choiceEnabled ? { saved_choice: { prompt: choicePrompt, options: choiceLabels.map((label, index) => ({ label, outcome: choiceOutcomes[index] })) } } : {}),
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
    <p>Choose each name, classification, relationship and source excerpt. Context is not direct support. Preparing a copy does not publish it.</p>
    <p>Only established facts with unknown or timeless scope are shown. Other claims, summaries, and dated events cannot yet be selected here.</p>
    <button type="button" disabled={busy} onClick={load}>Load selection options</button>
    {error && <p role="alert">{error}</p>}
    {prepared && <p role="status">Copy prepared. Load prepared copies below to review it.</p>}
    {options && <div>
      {options.source_options_truncated && <p>Excerpt discovery reached its current limit. Additional excerpts cannot yet be selected here.</p>}
      {options.fields.length === 0 && <p>No eligible fields found for this Graph revision.</p>}
      <ul>{options.fields.map(field => <li key={field.assertion_id}>
        <label><input type="checkbox" checked={Object.hasOwn(chosen, field.assertion_id)} disabled={busy}
          onChange={event => { const checked = event.target.checked; setChosen(previous => { const next = { ...previous }; if (checked) next[field.assertion_id] = ""; else delete next[field.assertion_id]; return next; }); }} />{" "}
          {labels.get(field.entity_id) ?? "Unnamed object"} · {field.kind}: {field.value}{field.target_id ? ` → ${labels.get(field.target_id) ?? "unnamed object"}` : ""} · {field.basis} · {field.temporal}
        </label>
        {Object.hasOwn(chosen, field.assertion_id) && <label> Source excerpt <select value={chosen[field.assertion_id]} disabled={busy}
          onChange={event => { const value = event.target.value; setChosen(previous => ({ ...previous, [field.assertion_id]: value })); }}>
          <option value="">Choose an excerpt</option>{field.source_option_ids.map(id => <option key={id} value={id}>{sources.get(id)?.document_title ?? "Source"} · {sources.get(id)?.visibility === "internal" ? "private" : "player-safe"} · {sources.get(id)?.evidence_role === "context" ? "context, not direct support" : "support"} · {sources.get(id)?.excerpt.slice(0, 60)}</option>)}
        </select></label>}
      </li>)}</ul>
      <fieldset><legend>Additional source excerpts</legend>
        <p>Choose individual context excerpts to include. These do not establish a Graph fact or automatically support a saved scene.</p>
        <label>Source document <select value={contextDocument} disabled={busy} onChange={event => { setContextDocument(event.target.value); setContextOffset(0); }}>
          <option value="">Choose a document</option>{(options.context_documents ?? []).map(item => <option key={item.document_id} value={item.document_id}>{item.title}</option>)}
        </select></label>
        <button type="button" disabled={busy || !contextDocument || contextOffset === null} onClick={loadContext}>Load source excerpts</button>
        {options.sources.filter(source => source.evidence_role === "context" && (source.document_id === contextDocument || independentSources.has(source.option_id))).map(source => <label key={source.option_id}>
          <input type="checkbox" disabled={busy} checked={independentSources.has(source.option_id)} onChange={event => {
            const checked = event.target.checked; setIndependentSources(previous => { const next = new Set(previous); if (checked) next.add(source.option_id); else next.delete(source.option_id); return next; });
          }} /> {source.document_title} · {source.visibility === "internal" ? "private source" : "player-safe source"} · context, not direct support
          <span style={{ whiteSpace: "pre-wrap", display: "block" }}>{source.excerpt}</span>
        </label>)}
      </fieldset>
      {[...new Set(Object.values(chosen).filter(Boolean))].map(id => { const source = sources.get(id); return source && <section key={id}>
        <h4>{source.document_title} · {source.visibility === "internal" ? "private source" : "player-safe source"} · {source.evidence_role === "context" ? "context, not direct support" : "support"}</h4><p style={{ whiteSpace: "pre-wrap" }}>{source.excerpt}</p>
      </section>; })}
      <h4>Images to include</h4><p>Choose images from this World. The reviewed copy will contain sanitized image bytes.</p>
      <button type="button" disabled={busy} onClick={() => loadImages()}>Load World images</button>
      {assets && assets.length === 0 && <p>No images found.</p>}
      {assets && <div className="guest-release-image-choices">{assets.map((asset, index) => <label key={asset.id}>
        <img src={`${base}/selection-media/${encodeURIComponent(asset.id)}`} alt={`World image ${index + 1}`} onLoad={() => setLoadedAssets(previous => new Set(previous).add(asset.id))}
          onError={() => { setLoadedAssets(previous => { const next = new Set(previous); next.delete(asset.id); return next; }); setSelectedAssets(previous => { const next = new Set(previous); next.delete(asset.id); return next; }); setExampleImage(previous => previous === asset.id ? "" : previous); setError("An image preview could not be loaded, so it cannot be selected."); }} />
        <span><input type="checkbox" disabled={busy || !loadedAssets.has(asset.id) || (selectedAssets.size >= 100 && !selectedAssets.has(asset.id))} checked={selectedAssets.has(asset.id)} onChange={event => { const checked = event.target.checked; setSelectedAssets(previous => { const next = new Set(previous); if (checked) next.add(asset.id); else next.delete(asset.id); return next; }); if (!checked) setExampleImage(previous => previous === asset.id ? "" : previous); }} /> Include image {index + 1}</span>
      </label>)}</div>}
      {nextAssets && <button type="button" disabled={busy} onClick={() => loadImages(nextAssets)}>Load more images</button>}
      {assets && <p>{selectedAssets.size} of 100 images selected.</p>}
      <h4>Optional saved scene example</h4>
      <label><input type="checkbox" checked={exampleEnabled} disabled={busy} onChange={event => { setExampleEnabled(event.target.checked); if (!event.target.checked) setChoiceEnabled(false); }} /> Include an owner-authored saved example</label>
      {exampleEnabled && <div>
        <p>This is a saved example, not a live generation. Choose related excerpts; they do not automatically prove the scene. The entire example will be reviewed before publication.</p>
        <label>Example title <input value={exampleTitle} maxLength={120} onChange={event => setExampleTitle(event.target.value)} /></label>
        <label>Scene text <textarea value={exampleBody} maxLength={10000} onChange={event => setExampleBody(event.target.value)} /></label>
        <fieldset><legend>Choose at least two distinct related excerpts</legend>
          {[...new Set([...evidenceIds, ...exampleReferences])].map(id => { const source = sources.get(id); return source && <label key={id}><input type="checkbox" checked={exampleReferences.has(id)} onChange={event => { const checked = event.target.checked; setExampleReferences(previous => { const next = new Set(previous); if (checked) next.add(id); else next.delete(id); return next; }); }} /> {source.document_title} · {source.evidence_role === "context" ? "context, not direct support" : "support"} · {source.excerpt.slice(0, 80)}{!evidenceIds.includes(id) && " · no longer included; remove this reference or include its excerpt again"}</label>; })}
        </fieldset>
        <label>Inline image <select value={exampleImage} onChange={event => setExampleImage(event.target.value)}><option value="">No image</option>{(assets ?? []).map((asset, index) => selectedAssets.has(asset.id) && loadedAssets.has(asset.id) ? <option key={asset.id} value={asset.id}>Selected image {index + 1}</option> : null)}</select></label>
        {exampleImage && <label>Describe the image for guests <input value={exampleImageDescription} maxLength={240} onChange={event => setExampleImageDescription(event.target.value)} /></label>}
        {!exampleReady && <p>Complete the scene and select at least two different included excerpts. An inline image must remain selected and have a description.</p>}
        <label><input type="checkbox" checked={choiceEnabled} onChange={event => setChoiceEnabled(event.target.checked)} /> Include a prewritten guest choice</label>
        {choiceEnabled && <fieldset><legend>Prewritten choice</legend>
          <p>Both outcomes will be public, even before someone chooses. They are possibilities, not a record of play.</p>
          <label>Choice prompt <input value={choicePrompt} maxLength={480} onChange={event => setChoicePrompt(event.target.value)} /></label>
          {([0, 1] as const).map(index => <div key={index}>
            <label>Option {index + 1} label <input value={choiceLabels[index]} maxLength={160} onChange={event => { const value = event.target.value; setChoiceLabels(previous => { const next: [string, string] = [...previous]; next[index] = value; return next; }); }} /></label>
            <label>Option {index + 1} outcome <textarea value={choiceOutcomes[index]} maxLength={4000} onChange={event => { const value = event.target.value; setChoiceOutcomes(previous => { const next: [string, string] = [...previous]; next[index] = value; return next; }); }} /></label>
          </div>)}
          {!choiceReady && <p>Complete the prompt and both distinct options and outcomes.</p>}
        </fieldset>}
      </div>}
      <p>For each object, select exactly one name and classification. Relationships require both objects and an excerpt.</p>
      <button type="button" disabled={!ready || !exampleReady || !choiceReady || busy} onClick={prepare}>Prepare copy for review</button>
    </div>}
  </section>;
}
