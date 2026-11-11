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
