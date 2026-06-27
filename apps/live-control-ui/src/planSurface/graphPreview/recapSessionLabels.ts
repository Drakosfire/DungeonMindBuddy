import type { RecapArtifactRecord } from "../../api/types";

export function recapSessionNumber(sessionId: string): number | null {
  const match = sessionId.match(/^session-(\d+)$/);
  return match ? Number.parseInt(match[1], 10) : null;
}

export function isNumericRecapSessionId(sessionId: string): boolean {
  return recapSessionNumber(sessionId) !== null;
}

export function recapArtifactSessionLabel(record: RecapArtifactRecord): string {
  const sessionNumber = recapSessionNumber(record.session_id);
  const fileName = record.source_recap_path.split("/").pop()?.replace(/\.md$/i, "") ?? record.session_id;
  if (sessionNumber === null) {
    return fileName;
  }
  const title = fileName.replace(/^Session\s+\d+\s*[-–—]\s*/i, "").trim();
  return title ? `Session ${sessionNumber} · ${title}` : `Session ${sessionNumber}`;
}

export function sortRecapArtifactRecords(records: RecapArtifactRecord[]): RecapArtifactRecord[] {
  return [...records].sort((left, right) => {
    const leftNum = recapSessionNumber(left.session_id) ?? 0;
    const rightNum = recapSessionNumber(right.session_id) ?? 0;
    if (leftNum !== rightNum) {
      return leftNum - rightNum;
    }
    return left.session_id.localeCompare(right.session_id);
  });
}

export function filterNumericRecapArtifactRecords(records: RecapArtifactRecord[]): RecapArtifactRecord[] {
  return records.filter((record) => isNumericRecapSessionId(record.session_id));
}
