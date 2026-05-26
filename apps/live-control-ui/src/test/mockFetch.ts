import { vi } from "vitest";

import type { LiveSurfaceResponse } from "../api/types";
import { mockCatalog, mockLayout, mockState } from "./fixtures";

export function mockSurfaceResponse(
  overrides: Partial<LiveSurfaceResponse> = {},
): LiveSurfaceResponse {
  return {
    catalog: mockCatalog,
    layout: mockLayout,
    state: mockState,
    ...overrides,
  };
}

export function installFetchMock(
  handler: (input: RequestInfo | URL, init?: RequestInit) => Response | Promise<Response>,
): void {
  vi.stubGlobal("fetch", vi.fn(handler));
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
