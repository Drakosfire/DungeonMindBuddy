import { useState } from "react";
import { authenticatedApiFetch } from "../api/liveApi";
import type { PdfLocator } from "../api/retainedPdfRegions";

export function StartPdfStatblockReview({ worldId, region }: { worldId: string; region: PdfLocator }) {
  const [id] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  async function start(file: File) {
    setPending(true);
    setError("");
    try {
      const definition: unknown = JSON.parse(await file.text());
      const source = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources/statblock-reviews/${id}`;
      const { response } = await authenticatedApiFetch(source, {
        method: "PUT",
        body: JSON.stringify({ definition, regions: [region], expected_revision: 0 }),
      });
      if (!response.ok) throw new Error();
      setSaved(true);
    } catch {
      setError("Could not start a review. Select a complete statblock definition JSON file.");
    } finally {
      setPending(false);
    }
  }

  return <details>
    <summary>Import a statblock definition</summary>
    {saved ? <a target="_blank" rel="noopener" href={`/build?${new URLSearchParams({ world: worldId, pdfReview: id })}`}>
      Open statblock review
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
