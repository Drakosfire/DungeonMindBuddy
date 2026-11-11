import { useEffect, useRef, useState } from "react";
import type { PDFDocumentProxy, RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

function PdfPages({ file }: { file: File }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const [document, setDocument] = useState<PDFDocumentProxy>();
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");

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

  return (
    <section aria-label="PDF preview">
      <p>{file.name}</p>
      {error ? <p role="alert">{error}</p> : !document ? <p role="status">Opening PDF…</p> : (
        <>
          <button type="button" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous page</button>
          <span role="status"> Page {page} of {document.numPages} </span>
          <button type="button" disabled={page === document.numPages} onClick={() => setPage(page + 1)}>Next page</button>
          <canvas key={page} ref={canvas} aria-label={`PDF page ${page}`} style={{ display: "block", maxWidth: "100%", height: "auto" }} />
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
