import {
  createNativeGraphDemoApi,
  type NativeGraphDemoApi,
  type NativeGraphDemoTransport,
} from "./nativeGraphDemoApi";

const INDEX_GRAPH_API = "/api/live/index-graph";
const CSRF_HEADER = "X-DMB-Index-Graph-CSRF";

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function errorResponse(message: string, code: string, status = 502): Response {
  return new Response(JSON.stringify({ error: message, code }), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function buddyPath(nativePath: string): string | null {
  if (nativePath === "/api/graph") return `${INDEX_GRAPH_API}/graph`;
  if (nativePath === "/api/prepare") return `${INDEX_GRAPH_API}/prepare`;
  if (nativePath === "/api/confirm") return `${INDEX_GRAPH_API}/confirm`;
  if (nativePath.startsWith("/api/operations/")) {
    return `${INDEX_GRAPH_API}/operations/${nativePath.slice("/api/operations/".length)}`;
  }
  return null;
}

/**
 * Creates the Buddy index client. Its authority is a same-origin, HttpOnly
 * browser session scoped by the server to this synthetic graph, never the
 * selected managed World. The common client still validates every native DTO.
 */
export interface GuestSource { readonly text: string; readonly role: string; readonly claim: string; readonly qualification: string }

export function createBuddyIndexGraphApi(options: { readonly fetcher?: FetchLike } = {}): NativeGraphDemoApi & { reset: () => Promise<void>; readSources: (id: string) => Promise<readonly GuestSource[]> } {
  const fetcher = options.fetcher ?? ((input, init) => globalThis.fetch(input, init));
  let csrfToken: string | null = null;
  let bootstrapInFlight: Promise<string | Response> | null = null;

  async function bootstrap(): Promise<string | Response> {
    if (csrfToken) return csrfToken;
    if (!bootstrapInFlight) {
      bootstrapInFlight = (async () => {
        const response = await fetcher(`${INDEX_GRAPH_API}/session`, {
          method: "POST",
          headers: { Accept: "application/json" },
          cache: "no-store",
          credentials: "same-origin",
          redirect: "error",
        });
        if (!response.ok) {
          // Return the server response to the shared client so it can preserve
          // the status and message. The caller's API operation is not sent.
          return response;
        }
        const body: unknown = await response.json().catch(() => null);
        if (!record(body) || typeof body.csrf_token !== "string" || !body.csrf_token.trim()) {
          throw new Error("Buddy could not verify the private graph session response.");
        }
        csrfToken = body.csrf_token;
        return csrfToken;
      })().finally(() => {
        bootstrapInFlight = null;
      });
    }
    return bootstrapInFlight;
  }

  const transport: NativeGraphDemoTransport = async (nativePath, init) => {
    const target = buddyPath(nativePath);
    if (!target) return errorResponse("The Buddy graph request is unsupported.", "unsupported_request", 400);

    const session = await bootstrap();
    if (typeof session !== "string") return session.clone();

    const headers = new Headers(init.headers);
    const method = (init.method ?? "GET").toUpperCase();
    if (method !== "GET" && method !== "HEAD") headers.set(CSRF_HEADER, session);
    const response = await fetcher(target, {
      ...init,
      headers,
      cache: "no-store",
      credentials: "same-origin",
      redirect: "error",
    });
    if (response.status === 401 || response.status === 403) csrfToken = null;
    return response;
  };

  async function reset(): Promise<void> {
    const session = await bootstrap();
    if (typeof session !== "string") throw new Error("Could not open the guest session.");
    const response = await fetcher(`${INDEX_GRAPH_API}/reset`, {
      method: "POST", headers: { [CSRF_HEADER]: session }, cache: "no-store",
      credentials: "same-origin", redirect: "error",
    });
    if (!response.ok) throw new Error("Could not reset the guest World.");
    const body: unknown = await response.json();
    if (!record(body) || typeof body.csrf_token !== "string" || !body.csrf_token.trim()) {
      csrfToken = null;
      throw new Error("Could not verify the reset guest session.");
    }
    csrfToken = body.csrf_token;
  }

  async function readSources(id: string): Promise<readonly GuestSource[]> {
    const session = await bootstrap();
    if (typeof session !== "string") throw new Error("Could not open the guest session.");
    const response = await fetcher(`${INDEX_GRAPH_API}/nodes/${encodeURIComponent(id)}/sources`, {
      cache: "no-store", credentials: "same-origin", redirect: "error",
    });
    if (!response.ok) throw new Error("Could not open the sources.");
    const body: unknown = await response.json();
    if (!record(body) || !Array.isArray(body.sources) || !body.sources.every(
      (source: unknown) => record(source) && typeof source.text === "string" && typeof source.role === "string" && typeof source.claim === "string" && typeof source.qualification === "string",
    )) throw new Error("Could not verify the sources.");
    return body.sources;
  }

  return Object.assign(createNativeGraphDemoApi({ transport }), { reset, readSources });
}
