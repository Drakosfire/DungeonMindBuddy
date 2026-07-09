import type { ResolvedRollResponse } from "../../api/types";

export function formatResolvedRoll(command: string, result: ResolvedRollResponse): string {
  return `${command} → ${result.roll}`;
}
