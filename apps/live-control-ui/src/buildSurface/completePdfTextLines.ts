type PdfRun = { text: string; complete: boolean; endOfLine: boolean };

export function completePdfTextLines(runs: PdfRun[]): string {
  const lines: string[] = [];
  let line = "";
  let complete = true;

  for (const run of runs) {
    line += run.text;
    if (run.text.trim() && !run.complete) complete = false;
    if (run.endOfLine) {
      lines.push(complete ? line : "");
      line = "";
      complete = true;
    }
  }
  if (complete && line) lines.push(line);
  return lines.join("\n");
}

export function pdfTextBoundsOverlap(
  corners: readonly (readonly [number, number])[],
  region: { left: number; top: number; width: number; height: number },
): boolean {
  const xs = corners.map(([x]) => x);
  const ys = corners.map(([, y]) => y);
  return Math.max(...xs) > region.left && Math.min(...xs) < region.left + region.width
    && Math.max(...ys) > region.top && Math.min(...ys) < region.top + region.height;
}

export function hasClippedPdfTextLine(runs: (PdfRun & { overlaps: boolean })[]): boolean {
  let included = false;
  let incomplete = false;
  for (const run of runs) {
    if (run.text.trim()) {
      included ||= run.overlaps || run.complete;
      incomplete ||= !run.complete;
    }
    if (included && incomplete) return true;
    if (run.endOfLine) {
      included = false;
      incomplete = false;
    }
  }
  return false;
}
