import { useState } from "react";
import { authenticatedApiFetch } from "../api/liveApi";
import { pdfRegionKey, type PdfLocator } from "../api/retainedPdfRegions";

export function StartPdfStatblockReview({
  worldId, regions, onRemoveRegion,
}: {
  worldId: string;
  regions: PdfLocator[];
  onRemoveRegion: (region: PdfLocator) => void;
}) {
  const [id] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState("");
  const [instruction, setInstruction] = useState("");

  async function start() {
    if (!regions.length || pending) return;
    setPending(true);
    setError("");
    try {
      const source = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources/statblock-reviews/${id}/from-regions`;
      const { response } = await authenticatedApiFetch(source, {
        method: "POST",
        body: JSON.stringify({ regions, instruction }),
      });
      if (response.status === 409) {
        setConflict(true);
        return;
      }
      const result = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = result?.detail;
        if (detail?.code === "pdf_statblock_extraction_incomplete") {
          const missing = Array.isArray(detail.missing_details)
            ? detail.missing_details.filter((item: unknown) => typeof item === "string")
            : [];
          throw new Error(missing.length
            ? `The selected regions do not support a complete statblock yet: ${missing.join("; ")}`
            : "The selected regions do not support a complete statblock yet.");
        }
        if (detail?.code === "pdf_statblock_output_invalid") {
          throw new Error("Buddy’s response did not match the statblock format. No review was saved.");
        }
        throw new Error("Buddy could not create a statblock review from these regions.");
      }
      setSaved(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Buddy could not create a statblock review.");
    } finally {
      setPending(false);
    }
  }

  return <section aria-label="Statblock review source regions">
    <h4>Selected statblock regions</h4>
    <ul>
      {regions.map(region => <li key={pdfRegionKey(region)}>
        Page {region.page}
        <button type="button" onClick={() => onRemoveRegion(region)} disabled={pending || saved}>
          Remove
        </button>
      </li>)}
    </ul>
    {saved || conflict ? <a target="_blank" rel="noopener" href={`/build?${new URLSearchParams({ world: worldId, pdfReview: id }).toString()}`}>
      {conflict ? "Open existing statblock review" : "Open statblock review"}
    </a> : <>
      <label>Guidance for Buddy (optional)
        <textarea rows={2} value={instruction} onChange={event => setInstruction(event.target.value)} disabled={pending} />
      </label>
      <button type="button" onClick={() => void start()} disabled={!regions.length || pending}>
        {pending ? "Preparing review…" : "Create statblock review"}
      </button>
    </>}
    {pending && <p role="status">Reading selected regions and preparing the review…</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
