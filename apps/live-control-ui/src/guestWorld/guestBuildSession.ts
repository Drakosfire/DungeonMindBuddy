/** In-memory guest session for the existing Build API, never a World authority. */
let active: { csrf: string; worldId: string; name: string } | null = null;
let epoch = 0;

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function clearGuestBuildSession(): void {
  epoch += 1;
  active = null;
}

export function guestBuildActive(): boolean { return active !== null; }

export function guestBuildRequestEpoch(path: string, method: string): number | null {
  if (!active) return null;
  const pathname = path.split("?", 1)[0];
  const conversation = import.meta.env.VITE_HOSTED_GUEST_BUDDY === "1" &&
    ((/^\/api\/live\/native-(?:graph|source)-inspection\/(?:catalog|read)$/.test(pathname)) && method === "POST" ||
      pathname === "/api/live/agent/turn" && method === "POST" ||
      pathname === `/api/live/agent/worlds/${active.worldId}/conversation` && method === "GET" ||
      pathname === `/api/live/agent/worlds/${active.worldId}/conversations/active/messages` && method === "GET" ||
      method === "GET" && pathname.startsWith(`/api/live/agent/worlds/${active.worldId}/conversation/turns/`) &&
        /^\/api\/live\/agent\/worlds\/guest-[0-9a-f]{32}\/conversation\/turns\/[0-9a-f-]{36}\/(?:native-source-clauses|native-assertion-sources|native-body-excerpts|native-source-sections|source-passages)\/[0-9]+$/.test(pathname) ||
      pathname === `/api/live/agent/worlds/${active.worldId}/conversation/new` && method === "POST");
  const media = import.meta.env.VITE_HOSTED_GUEST_MEDIA === "1" &&
    (pathname === "/api/live/media/images/capabilities" || pathname === "/api/live/media/images/library" || pathname === "/api/live/media/images/generate" ||
      /^\/api\/live\/media\/images\/[0-9a-f-]{36}(?:\/metadata|\/original)?$/.test(pathname));
  const play = import.meta.env.VITE_HOSTED_GUEST_PLAY === "1" &&
    (pathname === "/api/live/world-play-runs/v2" || pathname === "/api/live/world-play-runs/v2/active" ||
      pathname === "/api/live/world-play-runs/v2/preparation" || pathname === "/api/live/workspace-documents/world-runbooks" ||
      /^\/api\/live\/world-play-runs\/v2\/[0-9a-f-]{36}(?:\/progress|\/reference-manifest|\/content|\/creation)?$/.test(pathname) ||
      /^\/api\/live\/workspace-documents\/[0-9a-f-]{36}\/committed-revision(?:\/[1-9][0-9]*)?$/.test(pathname));
  const playContent = import.meta.env.VITE_HOSTED_GUEST_PLAY === "1" && (
    method === "GET" && /^\/api\/live\/world-play-runs\/v2\/[0-9a-f-]{36}\/content\/(?:revisions\/[0-9]+|commands\/[0-9a-f-]{36})$/.test(pathname)
    || method === "PUT" && /^\/api\/live\/world-play-runs\/v2\/[0-9a-f-]{36}\/content\/commands\/[0-9a-f-]{36}$/.test(pathname));
  const combat = import.meta.env.VITE_HOSTED_GUEST_PLAY === "1" &&
    (pathname === "/api/live/combat/encounters" || /^\/api\/live\/combat\/encounters\/[0-9a-f-]{36}$/.test(pathname)) &&
    ((method === "GET") || (method === "POST" && pathname === "/api/live/combat/encounters") ||
      (method === "PUT" && pathname !== "/api/live/combat/encounters"));
  const read = method === "GET" && (pathname === "/api/live/workspace-documents/pages/inventory"
    || import.meta.env.VITE_HOSTED_GUEST_PLAN === "1" && (pathname === "/api/live/workspace-documents/world-plans" || pathname === "/api/live/plan-view")
    || import.meta.env.VITE_HOSTED_GUEST_PLAN === "1" && import.meta.env.VITE_HOSTED_GUEST_BUDDY === "1" && /^\/api\/live\/workspace-documents\/[0-9a-f-]{36}\/committed-revision(?:\/[1-9][0-9]*)?$/.test(pathname)
    || /^\/api\/live\/workspace-documents\/[0-9a-f-]{36}(?:\/snapshot)?$/.test(pathname));
  const write = method === "POST" && (pathname === "/api/live/workspace-documents"
    || pathname === "/api/live/tiptap/markdown-write/prepare" || pathname === "/api/live/tiptap/markdown-write/commit"
    || import.meta.env.VITE_HOSTED_GUEST_PLAN === "1" && pathname === "/api/live/workspace-documents/world-plans");
  return read || write || conversation || combat || playContent || play && ["GET", "POST", "PUT"].includes(method) || media && ["GET", "POST"].includes(method) ? epoch : null;
}

export function guestBuildEpochCurrent(value: number): boolean { return active !== null && epoch === value; }

export function guestBuildCsrf(path: string, method: string): string | null {
  if (!active || method === "GET" || method === "HEAD") return null;
  const pathname = path.split("?", 1)[0];
  if (import.meta.env.VITE_HOSTED_GUEST_BUDDY === "1" && method === "POST" &&
      (pathname === "/api/live/agent/turn" || /^\/api\/live\/native-(?:graph|source)-inspection\/(?:catalog|read)$/.test(pathname) || pathname === `/api/live/agent/worlds/${active.worldId}/conversation/new`)) return active.csrf;
  if (import.meta.env.VITE_HOSTED_GUEST_PLAY === "1" && guestBuildRequestEpoch(path, method) !== null && pathname.startsWith("/api/live/combat/encounters")) return active.csrf;
  if (import.meta.env.VITE_HOSTED_GUEST_PLAY === "1" && method === "PUT" && /^\/api\/live\/world-play-runs\/v2\/[0-9a-f-]{36}\/content\/commands\/[0-9a-f-]{36}$/.test(pathname)) return active.csrf;
  if (import.meta.env.VITE_HOSTED_GUEST_MEDIA === "1" && pathname === "/api/live/media/images/generate" && method === "POST") return active.csrf;
  if (import.meta.env.VITE_HOSTED_GUEST_PLAY === "1" &&
      (pathname === "/api/live/world-play-runs/v2/preparation" || pathname === "/api/live/world-play-runs/v2/active" ||
        /^\/api\/live\/world-play-runs\/v2\/[0-9a-f-]{36}(?:\/progress)?$/.test(pathname))) return active.csrf;
  if (path === "/api/live/workspace-documents" || path === "/api/live/tiptap/markdown-write/prepare"
      || path === "/api/live/tiptap/markdown-write/commit"
      || import.meta.env.VITE_HOSTED_GUEST_PLAN === "1" && path === "/api/live/workspace-documents/world-plans") return active.csrf;
  return null;
}

export async function openGuestBuildWorld(signal: AbortSignal): Promise<{ worldId: string; name: string }> {
  const started = epoch;
  const init: RequestInit = { method: "POST", credentials: "same-origin", redirect: "error", cache: "no-store", signal };
  const session = await fetch("/api/live/index-graph/session", init);
  if (!session.ok) throw new Error("Could not open your guest session.");
  const credentials: unknown = await session.json();
  if (!record(credentials) || typeof credentials.csrf_token !== "string" || !credentials.csrf_token) {
    throw new Error("Could not verify your guest session.");
  }
  const response = await fetch("/api/live/index-graph/world", {
    ...init, headers: { "X-DMB-Index-Graph-CSRF": credentials.csrf_token },
  });
  if (!response.ok) throw new Error("Could not open your guest World.");
  const world: unknown = await response.json();
  if (!record(world) || typeof world.world_id !== "string" || !/^guest-[0-9a-f]{32}$/.test(world.world_id)
      || typeof world.name !== "string" || !world.name.trim() || signal.aborted || started !== epoch) {
    throw new Error("Could not verify your guest World.");
  }
  active = { csrf: credentials.csrf_token, worldId: world.world_id, name: world.name };
  return { worldId: active.worldId, name: active.name };
}
