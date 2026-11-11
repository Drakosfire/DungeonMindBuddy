import { PdfStatblockCandidate } from "./PdfStatblockCandidate";
import { pdfRegionKey, readRetainedPdfRegions, retainedPdfKey, type PdfLocator, type PdfReceipt, type RetainedPdf } from "../api/retainedPdfRegions";
import { authenticatedApiFetch } from "../api/liveApi";
import { useEffect, useRef, useState, type PointerEvent } from "react";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

type PagePoint = { x: number; y: number };
type PageRectangle = { left: number; top: number; width: number; height: number };

function pagePoint(event: PointerEvent<HTMLCanvasElement>): PagePoint {
  const bounds = event.currentTarget.getBoundingClientRect();
  const clamp = (value: number) => Math.max(0, Math.min(1, value));
  return {
    x: clamp((event.clientX - bounds.left) / bounds.width),
    y: clamp((event.clientY - bounds.top) / bounds.height),
  };
}

function CropOcr({ image, hasPdfText }: { image: string; hasPdfText: boolean }) {
  const [pending, setPending] = useState(false);
  const [text, setText] = useState("");
  const imageOnly = /^(?:\s*<\|ref\|>image<\|\/ref\|><\|det\|>\[\[[\d,\s]+\]\]<\|\/det\|>)+\s*$/.test(text);
  const [error, setError] = useState("");

  async function read() {
    setPending(true);
    setError("");
    setText("");
    try {
      const { response } = await authenticatedApiFetch("/api/live/agent/build-pdf-ocr", {
        method: "POST",
        body: JSON.stringify({ png_base64: image.split(",", 2)[1] }),
      });
      const result = await response.json();
      if (!response.ok || typeof result.text !== "string") {
        throw new Error(typeof result.detail === "string" ? result.detail : "Could not read the capture.");
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
      <button type="button" disabled={pending} onClick={() => void read()}>
        {pending ? "Reading capture…" : hasPdfText ? "Try OCR instead" : "Read capture with OCR"}
      </button>
      {error && <p role="alert">{error}</p>}
      {imageOnly && <p role="status">OCR found an image in this region without transcribing any text.</p>}
      {text && !imageOnly && <label>OCR transcription<textarea readOnly rows={8} value={text} /></label>}
    </div>
  );
}

function PdfPages({ file, worldId, restored, onRetained }: {
  file: File; worldId?: string; restored?: PdfLocator;
  onRetained: (locator: PdfLocator) => void;
}) {
  const [sourceFile, setSourceFile] = useState(file);
  const [admission] = useState(() => ({ id: crypto.randomUUID(), createdAt: new Date().toISOString() }));
  const [receipt, setReceipt] = useState<PdfReceipt | undefined>(restored);
  const [sourcePending, setSourcePending] = useState(false);
  const [sourceError, setSourceError] = useState("");

  async function retainOrReopen(selected: PageRectangle) {
    if (!worldId || sourcePending) return;
    const path = `/api/live/agent/worlds/${encodeURIComponent(worldId)}/build-pdf-sources`;
    setSourcePending(true);
    setSourceError("");
    const locator = (source: PdfReceipt): PdfLocator => ({
      ...source, page, left: selected.left, top: selected.top,
      right: Math.min(1, selected.left + selected.width),
      bottom: Math.min(1, selected.top + selected.height),
    });
    try {
      if (!receipt) {
        const { response } = await authenticatedApiFetch(`${path}?admission_id=${admission.id}`, {
          method: "POST",
          headers: { "Content-Type": "application/pdf", "X-Pdf-Created-At": admission.createdAt },
          body: file,
        });
        if (!response.ok) throw new Error();
        const admitted: PdfReceipt = await response.json();
        onRetained(locator(admitted));
        setReceipt(admitted);
      } else {
        const { response } = await authenticatedApiFetch(`${path}/open`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(locator(receipt)),
        });
        if (!response.ok) throw new Error();
        onRetained(locator(receipt));
        setSourceFile(new File([await response.blob()], file.name, { type: "application/pdf" }));
      }
    } catch {
      setSourceError(receipt ? "Could not reopen the retained PDF." : "Could not retain this PDF.");
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
  const [capture, setCapture] = useState<{ image: string; region: PageRectangle }>();
  const [capturedText, setCapturedText] = useState<string>();
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
    setTextError(false);
    setCapture({ image: crop.toDataURL(), region: rectangle });
  }

  useEffect(() => {
    let cancelled = false;
    let destroy: (() => Promise<void>) | undefined;
    async function load() {
      try {
        const data = new Uint8Array(await sourceFile.arrayBuffer());
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
  }, [sourceFile]);

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
        const text = items.map(item => {
          if (!("str" in item)) return "";
          const [a, b, c, d, x, y] = item.transform;
          const vertical = item.dir === "ttb";
          const advanceScale = vertical ? Math.hypot(c, d) : Math.hypot(a, b);
          const extent = vertical ? item.height : item.width;
          const offset = advanceScale ? extent / (2 * advanceScale) : 0;
          // Vertical PDF text advances down from its origin in PDF coordinates.
          const [viewX, viewY] = viewport.convertToViewportPoint(
            vertical ? x + a / 2 - c * offset : x + a * offset + c / 2,
            vertical ? y + b / 2 - d * offset : y + b * offset + d / 2,
          );
          const nx = viewX / viewport.width;
          const ny = viewY / viewport.height;
          const included = nx >= region.left && nx <= region.left + region.width
            && ny >= region.top && ny <= region.top + region.height;
          return (included ? item.str : "") + (item.hasEOL ? "\n" : "");
        }).join("").replace(/\n{2,}/g, "\n").trim();
        if (!cancelled) setCapturedText(text);
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
              <img src={capture.image} alt={`Captured region of page ${page}`} style={{ maxWidth: "100%" }} />
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
              {receipt && capturedText && <PdfStatblockCandidate
                key={JSON.stringify([page, capture.region, capturedText])}
                text={capturedText}
                locator={{
                  source_revision_id: receipt.source_revision_id,
                  content_sha256: receipt.content_sha256,
                  page, left: capture.region.left, top: capture.region.top,
                  right: Math.min(1, capture.region.left + capture.region.width),
                  bottom: Math.min(1, capture.region.top + capture.region.height),
                }}
              />}
              {(textError || capturedText !== undefined) && (
                <CropOcr key={capture.image} image={capture.image} hasPdfText={Boolean(capturedText)} />
              )}
            </section>
          )}
        </>
      )}
    </section>
  );
}

export function BuildPdfPreview({ worldId }: { worldId?: string }) {
  const [selection, setSelection] = useState<{ file: File; version: number; restored?: PdfLocator }>();
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
      setSelection(previous => ({ file, restored, version: (previous?.version ?? 0) + 1 }));
    } catch {
      setReopenError("Could not reopen the retained PDF.");
    } finally {
      setReopening(false);
    }
  }
  function select(file: File) {
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
