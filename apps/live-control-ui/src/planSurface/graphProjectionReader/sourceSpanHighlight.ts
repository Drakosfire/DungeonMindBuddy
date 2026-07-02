import type { RecapProjectionSourceSpan } from "../../api/types";

export function normalizeEvidenceText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
}

function readableNodeText(node: HTMLElement): string {
  const clone = node.cloneNode(true) as HTMLElement;
  clone.querySelectorAll(".recap-node-hover-card").forEach((hiddenContext) => hiddenContext.remove());
  return clone.textContent ?? "";
}

export function attachSourceSpanDataAttributes(
  root: HTMLElement,
  sourceSpans: RecapProjectionSourceSpan[],
  selectedEvidenceSpanId: string | null,
): HTMLElement | null {
  const candidates = Array.from(
    root.querySelectorAll<HTMLElement>(".ProseMirror p, .ProseMirror li, .ProseMirror blockquote p"),
  );
  candidates.forEach((candidate) => {
    delete candidate.dataset.sourceSpanId;
    candidate.classList.remove("recap-source-span-highlight");
  });

  const unused = new Set(candidates);
  const claimed = new Map<string, HTMLElement>();

  for (const span of sourceSpans) {
    const excerpt = normalizeEvidenceText(span.text_excerpt ?? "");
    if (!excerpt) continue;
    const matches = Array.from(unused).filter((node) => {
      const nodeText = normalizeEvidenceText(readableNodeText(node));
      return nodeText === excerpt || nodeText.includes(excerpt);
    });
    if (matches.length === 1) {
      claimed.set(span.span_id, matches[0]);
      unused.delete(matches[0]);
    }
  }

  for (const span of sourceSpans) {
    if (claimed.has(span.span_id)) continue;
    const ordinal = span.ordinal ?? 0;
    const ordinalCandidate = ordinal > 0 ? candidates[ordinal - 1] : undefined;
    if (ordinalCandidate && unused.has(ordinalCandidate)) {
      claimed.set(span.span_id, ordinalCandidate);
      unused.delete(ordinalCandidate);
    }
  }

  let highlighted: HTMLElement | null = null;
  for (const [spanId, node] of claimed.entries()) {
    node.dataset.sourceSpanId = spanId;
    const isHighlighted = spanId === selectedEvidenceSpanId;
    node.classList.toggle("recap-source-span-highlight", isHighlighted);
    if (isHighlighted) highlighted = node;
  }
  return highlighted;
}
