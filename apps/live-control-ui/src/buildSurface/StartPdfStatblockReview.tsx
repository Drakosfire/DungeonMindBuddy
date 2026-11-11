import { useState } from "react";
import { authenticatedApiFetch } from "../api/liveApi";
import type { PdfLocator } from "../api/retainedPdfRegions";

export function StartPdfStatblockReview({ worldId, region }: { worldId: string; region: PdfLocator }) {
  const [id] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState("");

  async function start(file: File) {
    setPending(true);
    setError("");
    let definition: unknown;
    try {
      definition = JSON.parse(await file.text());
    } catch {
      setError("Choose a readable statblock definition JSON file.");
      setPending(false);
      return;
    }
    try {
      const source = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources/statblock-reviews/${id}`;
      const { response } = await authenticatedApiFetch(source, {
        method: "PUT",
        body: JSON.stringify({ definition, regions: [region], expected_revision: 0 }),
      });
      if (response.status === 409) {
        setConflict(true);
        return;
      }
      if (!response.ok) throw new Error();
      setSaved(true);
    } catch {
      setError("Could not confirm the review save. Check that the definition is complete, then retry.");
    } finally {
      setPending(false);
    }
  }

  return <details>
    <summary>Import a statblock definition</summary>
    {saved || conflict ? <a target="_blank" rel="noopener" href={`/build?${new URLSearchParams({ world: worldId, pdfReview: id })}`}>
      {conflict ? "Check existing statblock review" : "Open statblock review"}
    </a> : <label>
      Statblock definition JSON
      <input type="file" accept=".json,application/json" disabled={pending} onChange={event => {
        const file = event.currentTarget.files?.[0];
        event.currentTarget.value = "";
        if (file) void start(file);
      }} />
    </label>}
    {pending && <p role="status">Saving review draft…</p>}
    {error && <p role="alert">{error}</p>}
  </details>;
}
