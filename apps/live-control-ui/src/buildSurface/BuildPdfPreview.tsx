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

function PdfPages({ file }: { file: File }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [document, setDocument] = useState<PDFDocumentProxy>();
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const [renderedPage, setRenderedPage] = useState<number>();
  const drag = useRef<{ pointerId: number; start: PagePoint } | undefined>(undefined);
  const [region, setRegion] = useState<{ start: PagePoint; end: PagePoint }>();
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
              {textError ? <p role="alert">The PDF text layer could not be read.</p>
                : capturedText === undefined ? <p role="status">Reading selected text…</p>
                : capturedText ? (
                  <label>
                    Captured text
                    <textarea readOnly value={capturedText} rows={5} />
                  </label>
                ) : <p role="status">No selectable text in this region.</p>}
            </section>
          )}
        </>
      )}
    </section>
  );
}

export function BuildPdfPreview() {
  const [selection, setSelection] = useState<{ file: File; version: number }>();
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
      {selection && <PdfPages key={selection.version} file={selection.file} />}
    </div>
  );
}
