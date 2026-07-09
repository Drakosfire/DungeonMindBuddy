export function parseGraphObjectAuthoringApiError(error: unknown): string {
  if (error instanceof Error) {
    const message = error.message;
    try {
      const parsed = JSON.parse(message) as { code?: string; message?: string };
      if (parsed.message) {
        return parsed.message;
      }
    } catch {
      // keep raw message
    }
    return message;
  }
  return "Request failed.";
}
