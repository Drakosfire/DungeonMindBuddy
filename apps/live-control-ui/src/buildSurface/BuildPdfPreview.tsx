import { StartPdfStatblockReview } from "./StartPdfStatblockReview";
import { completePdfTextLines, hasClippedPdfTextLine, pdfTextBoundsOverlap } from "./completePdfTextLines";
import { hasRecognizablePdfStatblockStructure, PdfStatblockCandidate } from "./PdfStatblockCandidate";
import { PdfTableCandidate } from "./PdfTableCandidate";
import type { PdfRegionTextRun } from "./parsePdfDiceTable";
import { pdfRegionKey, readRetainedPdfRegions, retainedPdfKey, type PdfLocator, type PdfReceipt, type RetainedPdf } from "../api/retainedPdfRegions";
import { authenticatedApiFetch } from "../api/liveApi";
import { useEffect, useRef, useState, type PointerEvent } from "react";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

type PagePoint = { x: number; y: number };
type PageRectangle = { left: number; top: number; width: number; height: number };

function captureLocator(source: PdfReceipt, page: number, selected: PageRectangle): PdfLocator {
  return {
    source_revision_id: source.source_revision_id,
    content_sha256: source.content_sha256,
    page,
    left: selected.left,
    top: selected.top,
    right: Math.min(1, selected.left + selected.width),
    bottom: Math.min(1, selected.top + selected.height),
  };
}


function pagePoint(event: PointerEvent<HTMLCanvasElement>): PagePoint {
  const bounds = event.currentTarget.getBoundingClientRect();
  const clamp = (value: number) => Math.max(0, Math.min(1, value));
  return {
    x: clamp((event.clientX - bounds.left) / bounds.width),
    y: clamp((event.clientY - bounds.top) / bounds.height),
  };
}

export function CropOcr({ worldId, region, hasPdfText }: { worldId: string; region: PdfLocator; hasPdfText: boolean }) {
  const [instruction, setInstruction] = useState("");
  const [review, setReview] = useState(false);
  const [pending, setPending] = useState(false);
  const [text, setText] = useState("");
  const imageOnly = /^(?:\s*<\|ref\|>image<\|\/ref\|><\|det\|>\[\[[\d,\s]+\]\]<\|\/det\|>)+\s*$/.test(text);
  const [error, setError] = useState("");

  async function read(withBuddy: boolean) {
    setReview(withBuddy);
    setPending(true);
    setError("");
    setText("");
    try {
      const { response } = await authenticatedApiFetch(`/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources/${withBuddy ? "review" : "ocr"}`, {
        method: "POST",
        body: JSON.stringify(withBuddy ? { region, instruction } : region),
      });
      const result = await response.json();
      if (!response.ok || typeof result.text !== "string") {
        throw new Error(typeof result.detail === "string" ? result.detail : "Could not read the capture.");
      }
      if (withBuddy && !Object.entries(region).every(([key, value]) => result.region?.[key] === value)) {
        throw new Error("Buddy’s reply did not match the selected PDF region.");
      }
      setText(result.text);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Could not read the capture.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <button type="button" disabled={pending} onClick={() => void read(false)}>
        {pending ? "Reading capture…" : hasPdfText ? "Try OCR instead" : "Read capture with OCR"}
      </button>
      <label>Instructions for Buddy (optional)
        <textarea rows={2} value={instruction} onChange={event => setInstruction(event.target.value)} />
      </label>
      <button type="button" disabled={pending} onClick={() => void read(true)}>Ask Buddy about this capture</button>
      {error && <p role="alert">{error}</p>}
      {imageOnly && <p role="status">OCR found an image in this region without transcribing any text.</p>}
      {text && !imageOnly && <label>{review ? `Buddy’s review · Page ${region.page}` : "OCR transcription"}<textarea readOnly rows={8} value={text} /></label>}
      {!review && text && !imageOnly && hasRecognizablePdfStatblockStructure(text) && <PdfStatblockCandidate text={text} locator={region} />}
    </div>
  );
}

function CropPreviewImage({ canvas, page }: { canvas: HTMLCanvasElement; page: number }) {
  const [url, setUrl] = useState<string>();
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let active = true;
    let objectUrl: string | undefined;
    canvas.toBlob(blob => {
      if (!active) return;
      if (!blob) {
        setFailed(true);
        return;
      }
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
    });
    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [canvas]);
  if (failed) return <p role="alert">Could not generate the crop preview.</p>;
  if (!url) return <p role="status">Preparing crop preview…</p>;
  return <img src={url} alt={`Captured region of page ${page}`} style={{ maxWidth: "100%" }} />;
}

function PdfPages({ file, worldId, restored, onRetained }: {
  file: File; worldId?: string; restored?: PdfLocator;
  onRetained: (locator: PdfLocator) => void;
}) {
  const [admission] = useState(() => ({ id: crypto.randomUUID(), createdAt: new Date().toISOString() }));
  const [receipt, setReceipt] = useState<PdfReceipt | undefined>(restored);
  const [sourcePending, setSourcePending] = useState(false);
  const [sourceError, setSourceError] = useState("");
  const [statblockRegions, setStatblockRegions] = useState<PdfLocator[]>(() => restored ? [restored] : []);

  async function retainSource(): Promise<PdfReceipt> {
    if (receipt) return receipt;
    const path = `/api/live/agent/worlds/${encodeURIComponent(worldId!)}/build-pdf-sources`;
    const { response } = await authenticatedApiFetch(`${path}?admission_id=${admission.id}`, {
          method: "POST",
          headers: { "Content-Type": "application/pdf", "X-Pdf-Created-At": admission.createdAt },
          body: file,
        });
        if (!response.ok) throw new Error();
        const admitted: PdfReceipt = await response.json();
    setReceipt(admitted);
    return admitted;
  }

  async function retainOrReopen(selected: PageRectangle) {
    if (!worldId || sourcePending) return;
    const path = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources`;
    setSourcePending(true);
    setSourceError("");
    try {
      if (!receipt) {
        const admitted = await retainSource();
        onRetained(captureLocator(admitted, page, selected));
      } else {
        const locator = captureLocator(receipt, page, selected);
        const { response } = await authenticatedApiFetch(`${path}/region:validate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(locator),
        });
        if (response.status !== 204) throw new Error();
        onRetained(locator);
      }
    } catch {
      setSourceError(receipt ? "Could not validate this retained PDF region." : "Could not retain this PDF.");
    } finally {
      setSourcePending(false);
    }
  }

  const canvas = useRef<HTMLCanvasElement>(null);
  const [document, setDocument] = useState<PDFDocumentProxy>();
  const [page, setPage] = useState(restored?.page ?? 1);
  const [error, setError] = useState("");
  const [renderedPage, setRenderedPage] = useState<number>();
  const drag = useRef<{ pointerId: number; start: PagePoint } | undefined>(undefined);
  const [region, setRegion] = useState<{ start: PagePoint; end: PagePoint } | undefined>(
    restored && { start: { x: restored.left, y: restored.top },
      end: { x: restored.right, y: restored.bottom } },
  );
  const captureSequence = useRef(0);
  const [capture, setCapture] = useState<{ id: number; canvas: HTMLCanvasElement; region: PageRectangle }>();
  const [capturedText, setCapturedText] = useState<string>();
  const [capturedRuns, setCapturedRuns] = useState<PdfRegionTextRun[]>([]);
  const [completeLines, setCompleteLines] = useState("");
  const [clippedText, setClippedText] = useState(false);
  const [textError, setTextError] = useState(false);
  const rectangle = region && {
    left: Math.min(region.start.x, region.end.x),
    top: Math.min(region.start.y, region.end.y),
    width: Math.abs(region.start.x - region.end.x),
    height: Math.abs(region.start.y - region.end.y),
  };

  function changePage(next: number) {
    drag.current = undefined;
    setRegion(undefined);
    setCapture(undefined);
    setRenderedPage(undefined);
    setPage(next);
  }

  const selectedRegion = rectangle?.width && rectangle.height ? rectangle : undefined;

  function captureRegion() {
    const source = canvas.current;
    if (!rectangle || !source || !rectangle.width || !rectangle.height) return;
    const crop = window.document.createElement("canvas");
    crop.width = Math.ceil(rectangle.width * source.width);
    crop.height = Math.ceil(rectangle.height * source.height);
    const context = crop.getContext("2d");
    if (!context) return;
    context.drawImage(source, rectangle.left * source.width, rectangle.top * source.height,
      rectangle.width * source.width, rectangle.height * source.height,
      0, 0, crop.width, crop.height);
    setCapturedText(undefined);
    setCapturedRuns([]);
    setCompleteLines("");
    setClippedText(false);
    setTextError(false);
    setCapture({ id: ++captureSequence.current, canvas: crop, region: rectangle });
  }

  useEffect(() => {
    let cancelled = false;
    let destroy: (() => Promise<void>) | undefined;
    async function load() {
      try {
        if (file.size > 32 * 1024 * 1024) {
          if (!cancelled) setError("Choose a PDF that is 32 MiB or smaller.");
          return;
        }
        const data = new Uint8Array(await file.arrayBuffer());
        if (new TextDecoder().decode(data.subarray(0, 5)) !== "%PDF-") {
          throw new Error("Invalid PDF header");
        }
        const pdf = await import("pdfjs-dist");
        if (cancelled) return;
        pdf.GlobalWorkerOptions.workerSrc = workerUrl;
        const task = pdf.getDocument({ data, enableXfa: false });
        destroy = () => task.destroy();
        const loaded = await task.promise;
        if (!cancelled) setDocument(loaded);
      } catch {
        if (!cancelled) setError("This PDF could not be opened. Check that the file is readable and unlocked.");
      }
    }
    void load();
    return () => {
      cancelled = true;
      void destroy?.().catch(() => {});
    };
  }, [file]);

  useEffect(() => {
    if (!document) return;
    let cancelled = false;
    let render: RenderTask | undefined;
    async function draw(pdf: PDFDocumentProxy) {
      try {
        const source = await pdf.getPage(page);
        const target = canvas.current;
        if (cancelled || !target) return;
        const natural = source.getViewport({ scale: 1 });
        const viewport = source.getViewport({ scale: 1000 / Math.max(natural.width, natural.height) });
        target.width = Math.ceil(viewport.width);
        target.height = Math.ceil(viewport.height);
        render = source.render({ canvas: target, viewport, annotationMode: 0 });
        await render.promise;
        if (!cancelled) setRenderedPage(page);
      } catch {
        if (!cancelled) setError("This page could not be rendered.");
      }
    }
    void draw(document);
    return () => {
      cancelled = true;
      render?.cancel();
    };
  }, [document, page]);

  useEffect(() => {
    if (!document || !capture) return;
    let cancelled = false;
    async function readRegion(pdf: PDFDocumentProxy, region: PageRectangle) {
      try {
        const source = await pdf.getPage(page);
        const viewport = source.getViewport({ scale: 1 });
        const { items } = await source.getTextContent();
        const runs = items.flatMap(item => {
          if (!("str" in item)) return [];
          const [a, b, c, d, x, y] = item.transform;
          const vertical = item.dir === "ttb";
          const advanceScale = vertical ? Math.hypot(c, d) : Math.hypot(a, b);
          const extent = vertical ? item.height : item.width;
          const advance = advanceScale ? extent / advanceScale : 0;
          const point = (along: number, across: number): [number, number] => {
            const [viewX, viewY] = viewport.convertToViewportPoint(
              vertical ? x + a * across - c * along : x + a * along + c * across,
              vertical ? y + b * across - d * along : y + b * along + d * across,
            );
            return [viewX / viewport.width, viewY / viewport.height];
          };
          const inside = ([nx, ny]: [number, number]) =>
            nx >= region.left && nx <= region.left + region.width
              && ny >= region.top && ny <= region.top + region.height;
          const corners = [point(0, 0), point(advance, 0), point(0, 1), point(advance, 1)];
          const xs = corners.map(([nx]) => nx);
          const ys = corners.map(([, ny]) => ny);
          return [{
            text: item.str,
            endOfLine: item.hasEOL,
            included: inside(point(advance / 2, 0.5)),
            complete: advance > 0 && corners.every(inside),
            overlaps: advance > 0 && pdfTextBoundsOverlap(corners, region),
            bounds: {
              left: Math.min(...xs),
              right: Math.max(...xs),
              top: Math.min(...ys),
              bottom: Math.max(...ys),
            },
          }];
        });
        if (!cancelled) {
          setCapturedRuns(runs.filter(run => run.included && run.text.trim()).map(run => ({
            text: run.text,
            ...run.bounds,
          })));
          setCapturedText(runs.map(run => (run.included ? run.text : " ")
            + (run.endOfLine ? "\n" : "")).join("").trim());
          setCompleteLines(completePdfTextLines(runs));
          setClippedText(hasClippedPdfTextLine(runs));
        }
      } catch {
        if (!cancelled) setTextError(true);
      }
    }
    void readRegion(document, capture.region);
    return () => { cancelled = true; };
  }, [document, page, capture]);

  return (
    <section aria-label="PDF preview">
      <p>{file.name}</p>
      {error ? <p role="alert">{error}</p> : !document ? <p role="status">Opening PDF…</p> : (
        <>
          <button type="button" disabled={page === 1} onClick={() => changePage(page - 1)}>Previous page</button>
          <span role="status"> Page {page} of {document.numPages} </span>
          <button type="button" disabled={page === document.numPages} onClick={() => changePage(page + 1)}>Next page</button>
          <p>Drag across the page to select a region.</p>
          <div style={{ position: "relative", width: "fit-content", maxWidth: "100%" }}>
            <canvas
              key={page}
              ref={canvas}
              aria-label={`PDF page ${page}`}
              style={{ display: "block", maxWidth: "100%", height: "auto", touchAction: "none", cursor: "crosshair" }}
              onPointerDown={event => {
                if (renderedPage !== page || event.button !== 0 || drag.current) return;
                const start = pagePoint(event);
                event.currentTarget.setPointerCapture(event.pointerId);
                drag.current = { pointerId: event.pointerId, start };
                setCapture(undefined);
                setRegion({ start, end: start });
              }}
              onPointerMove={event => {
                if (drag.current?.pointerId !== event.pointerId) return;
                setRegion({ start: drag.current.start, end: pagePoint(event) });
              }}
              onPointerUp={event => {
                if (drag.current?.pointerId !== event.pointerId) return;
                setRegion({ start: drag.current.start, end: pagePoint(event) });
                drag.current = undefined;
              }}
              onLostPointerCapture={() => {
                if (!drag.current) return;
                drag.current = undefined;
                setRegion(undefined);
              }}
            />
            {rectangle && <div aria-hidden="true" style={{
              position: "absolute", pointerEvents: "none", outline: "2px solid #b18127",
              background: "#b1812733", left: `${rectangle.left * 100}%`, top: `${rectangle.top * 100}%`,
              width: `${rectangle.width * 100}%`, height: `${rectangle.height * 100}%`,
            }} />}
          </div>
          <button type="button" disabled={!rectangle?.width || !rectangle.height} onClick={captureRegion}>
            Capture region
          </button>
          {region && <button type="button" onClick={() => { setRegion(undefined); setCapture(undefined); }}>
            Clear selection
          </button>}
          {capture && (
            <section aria-label={`Capture from page ${page}`}>
              <CropPreviewImage key={capture.id} canvas={capture.canvas} page={page} />
              {worldId && receipt && <button type="button" onClick={() => {
                const locator = captureLocator(receipt, page, capture.region);
                setStatblockRegions(current => current.some(region => pdfRegionKey(region) === pdfRegionKey(locator))
                  ? current : [...current, locator]);
              }} disabled={statblockRegions.some(region =>
                pdfRegionKey(region) === pdfRegionKey(captureLocator(receipt, page, capture.region)))}>
                {statblockRegions.some(region =>
                  pdfRegionKey(region) === pdfRegionKey(captureLocator(receipt, page, capture.region)))
                  ? "Region added" : "Add another region"}
              </button>}
              <details>
                <summary>Crop tools</summary>
                {worldId && <button type="button" disabled={sourcePending}
                  onClick={() => void retainOrReopen(capture.region)}>
                  {receipt ? "Reopen retained region" : "Retain PDF source"}
                </button>}
                {sourceError && <p role="alert">{sourceError}</p>}
                {textError ? <p role="alert">The PDF text layer could not be read.</p>
                  : capturedText === undefined ? <p role="status">Reading the PDF text layer…</p>
                  : capturedText ? (
                    <label>
                      Approximate text from the PDF layer
                      <span>Text can extend beyond the crop or miss partial lines. Check it against the image.</span>
                      <textarea readOnly value={capturedText} rows={5} />
                    </label>
                  ) : <p role="status">No PDF text runs were selected. The crop may still contain visible text.</p>}
                {clippedText && <p role="status">Some PDF text lines may extend outside the capture. Widen the selection or check the image before using the extracted fields.</p>}
                {receipt && capturedText && <PdfStatblockCandidate
                  key={JSON.stringify([page, capture.region, capturedText])}
                  text={completeLines}
                  locator={captureLocator(receipt, page, capture.region)}
                />}
                {receipt && capturedText && <PdfTableCandidate
                  key={JSON.stringify([page, capture.region, capturedText, clippedText])}
                  items={capturedRuns}
                  locator={captureLocator(receipt, page, capture.region)}
                  clipped={clippedText}
                />}
                {worldId && receipt && (textError || capturedText !== undefined) && (
                  <CropOcr key={capture.id} worldId={worldId} region={captureLocator(receipt, page, capture.region)} hasPdfText={Boolean(capturedText)} />
                )}
              </details>
            </section>
          )}
        </>
      )}
      {worldId && <StartPdfStatblockReview
        worldId={worldId}
        regions={statblockRegions}
        prepareWholePdf={document ? async () => {
          if (sourcePending) throw new Error("Wait for the PDF source to finish opening.");
          const source = await retainSource();
          const fullPage = { left: 0, top: 0, width: 1, height: 1 };
          const pages = Array.from({ length: document.numPages }, (_, index) =>
            captureLocator(source, index + 1, fullPage));
          onRetained(pages[0]);
          return pages;
        } : undefined}
        prepareRegions={selectedRegion || capture || statblockRegions.length ? async () => {
          const activeRegion = selectedRegion ?? capture?.region;
          if (!activeRegion) return statblockRegions;
          if (sourcePending) throw new Error("Wait for the PDF source to finish opening.");
          const locator = captureLocator(await retainSource(), page, activeRegion);
          onRetained(locator);
          return statblockRegions.some(region => pdfRegionKey(region) === pdfRegionKey(locator))
            ? statblockRegions : [...statblockRegions, locator];
        } : undefined}
        onRemoveRegion={removed => setStatblockRegions(current =>
          current.filter(region => pdfRegionKey(region) !== pdfRegionKey(removed)))}
      />}
    </section>
  );
}

export function BuildPdfPreview({ worldId, initialFile, onPdfOpen }: { worldId?: string; initialFile?: File; onPdfOpen?: () => void }) {
  const [selection, setSelection] = useState<{ file: File; version: number; restored?: PdfLocator } | undefined>(() => initialFile ? { file: initialFile, version: 0 } : undefined);
  const [reopenError, setReopenError] = useState("");
  const [reopening, setReopening] = useState(false);
  const [retained, setRetained] = useState<RetainedPdf[]>(() =>
    worldId ? readRetainedPdfRegions(worldId) : []);
  function saveLocator(locator: PdfLocator) {
    if (!worldId || !selection) return;
    const entry = { name: selection.file.name, locator };
    setRetained(previous => [entry, ...previous.filter(
      saved => pdfRegionKey(saved.locator) !== pdfRegionKey(locator),
    )]);
    try {
      localStorage.setItem(retainedPdfKey(worldId) + pdfRegionKey(locator), JSON.stringify(entry));
    } catch {
      setReopenError("Browser storage is unavailable. This region can be reopened until you leave this view.");
    }
  }
  async function reopen({ name, locator: restored }: RetainedPdf) {
    if (!worldId || reopening) return;
    setReopening(true);
    setReopenError("");
    try {
      const path = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources/open`;
      const { response } = await authenticatedApiFetch(path, {
        method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(restored),
      });
      if (!response.ok) throw new Error();
      const file = new File([await response.blob()], name, { type: "application/pdf" });
      onPdfOpen?.();
      setSelection(previous => ({ file, restored, version: (previous?.version ?? 0) + 1 }));
    } catch {
      setReopenError("Could not reopen the retained PDF.");
    } finally {
      setReopening(false);
    }
  }
  function select(file: File) {
    onPdfOpen?.();
    setSelection(previous => ({ file, version: (previous?.version ?? 0) + 1 }));
  }

  return (
    <div
      onDragOver={event => event.preventDefault()}
      onDrop={event => {
        event.preventDefault();
        const file = event.dataTransfer.files[0];
        if (file) select(file);
      }}
    >
      <label>
        Choose or drop a PDF
        <input type="file" accept="application/pdf,.pdf" onChange={event => {
          const file = event.currentTarget.files?.[0];
          if (file) select(file);
          event.currentTarget.value = "";
        }} />
      </label>
      {retained.length > 0 && <ul aria-label="Retained PDFs">
        {retained.map(entry => <li key={pdfRegionKey(entry.locator)}>
          <button type="button" disabled={reopening} onClick={() => void reopen(entry)}>
            {entry.name} · Page {entry.locator.page}
          </button>
        </li>)}
      </ul>}
      {reopenError && <p role="alert">{reopenError}</p>}
      {selection && <PdfPages key={`${worldId ?? ""}:${selection.version}`} file={selection.file} worldId={worldId} restored={selection.restored} onRetained={saveLocator} />}
    </div>
  );
}
