import { useEffect, useRef, useState } from "react";
import { authenticatedApiFetch } from "../api/liveApi";
import { pdfRegionKey, type PdfLocator } from "../api/retainedPdfRegions";

export function StartPdfStatblockReview({
  worldId, regions, onRemoveRegion, prepareRegions, prepareWholePdf,
}: {
  worldId: string;
  regions: PdfLocator[];
  prepareWholePdf?: () => Promise<PdfLocator[]>;
  prepareRegions?: () => Promise<PdfLocator[]>;
  onRemoveRegion: (region: PdfLocator) => void;
}) {
  const mounted = useRef(false);
  useEffect(() => {
    mounted.current = true;
    return () => { mounted.current = false; };
  }, []);
  const [id] = useState(() => crypto.randomUUID());
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [error, setError] = useState("");
  const [edition, setEdition] = useState("");
  const [instruction, setInstruction] = useState("");

  function describeFailure(detail: unknown): string {
    const record = detail && typeof detail === "object" ? detail as Record<string, unknown> : {};
    const code = typeof record.code === "string" && /^[a-z0-9][a-z0-9_-]{0,79}$/.test(record.code)
      ? record.code
      : null;
    const suffix = code ? ` (${code})` : "";
    if (code === "pdf_statblock_extraction_incomplete") {
      const missing = Array.isArray(record.missing_details)
        ? record.missing_details.filter((item): item is string => typeof item === "string" && item.trim().length > 0)
        : [];
      return missing.length
        ? `The selected regions do not support a complete statblock yet: ${missing.join("; ")}.${suffix}`
        : `The selected regions do not support a complete statblock yet.${suffix}`;
    }
    if (code === "pdf_statblock_output_invalid") {
      return `Buddy’s response did not match the statblock format.${suffix}`;
    }
    if (code === "pdf_statblock_ocr_unavailable") {
      return `Buddy could not read the selected regions with OCR. Try again later or adjust the regions.${suffix}`;
    }
    if (code === "pdf_statblock_generation_unavailable") {
      return `Buddy could not generate a structured statblock from the selected regions. Try again later.${suffix}`;
    }
    if (code === "invalid_pdf_statblock_extraction_request") {
      return `The selected regions could not be used for this review. Re-select them and try again.${suffix}`;
    }
    return `Buddy could not create a statblock review from these regions${suffix}.`;
  }

  async function start(prepare = prepareRegions) {
    if ((!regions.length && !prepare) || pending) return;
    const startUrl = window.location.href;
    setPending(true);
    setError("");
    try {
      const selected = prepare ? await prepare() : regions;
      const source = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources/statblock-reviews/${id}/from-regions`;
      const { response } = await authenticatedApiFetch(source, {
        method: "POST",
        body: JSON.stringify({ regions: selected, instruction, ...(edition ? { edition } : {}) }),
      });
      if (response.status === 409) {
        setConflict(true);
        return;
      }
      const result = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(describeFailure(result?.detail));
      }
      if (prepare && mounted.current && window.location.href === startUrl) {
        const location = new URL(startUrl);
        location.searchParams.set("world", worldId);
        location.searchParams.set("pdfReview", id);
        window.history.pushState(window.history.state, "", location);
        window.dispatchEvent(new PopStateEvent("popstate"));
      }
      setSaved(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Buddy could not create a statblock review.");
    } finally {
      setPending(false);
    }
  }

  if (!regions.length && !prepareRegions && !prepareWholePdf && !pending && !saved && !conflict && !error) return null;

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
    {saved || conflict ? <>
      <a target="_blank" rel="noopener" href={`/build?${new URLSearchParams({ world: worldId, pdfReview: id }).toString()}`}>
        {conflict ? "Open existing statblock review" : "Open statblock review"}
      </a>
    </> : <>
      <label>D&D edition (optional)
        <select value={edition} onChange={event => setEdition(event.target.value)} disabled={pending}>
          <option value="">Use source edition</option>
          <option value="2014">2014</option>
          <option value="2024">2024</option>
        </select>
      </label>
      <label>Guidance for Buddy (optional)
        <textarea rows={2} value={instruction} onChange={event => setInstruction(event.target.value)} disabled={pending} />
      </label>
      {prepareWholePdf && <button type="button" disabled={pending} onClick={() => void start(prepareWholePdf)}>
        Extract whole PDF
      </button>}
      {(regions.length > 0 || prepareRegions) && <button type="button" onClick={() => void start()} disabled={(!regions.length && !prepareRegions) || pending}>
        {pending ? "Preparing statblock…" : prepareRegions ? "Extract statblock" : "Create statblock review"}
      </button>}
    </>}
    {pending && <p role="status">Reading selected regions and preparing the review…</p>}
    {error && <p role="alert">{error}</p>}
  </section>;
}
