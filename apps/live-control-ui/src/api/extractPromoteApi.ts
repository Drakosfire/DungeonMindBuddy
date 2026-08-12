/**
 * Product client for extract → World Supergraph promote (PR011A2 + PR011A3).
 */

import type {
  ExactRunReviewPackage,
  ExtractPromoteConfirmReceipt,
  ExtractPromoteConfirmRequest,
  ExtractPromoteErrorBody,
  ExtractPromotePrepareRequest,
  ExtractPromotePrepareResponse,
  ExtractPromoteStatusResponse,
  FirstWorldGraphConfirmReceipt,
  FirstWorldGraphConfirmRequest,
  FirstWorldGraphPlan,
  FirstWorldGraphPrepareRequest,
} from "./types";

const baseUrl = (import.meta.env.VITE_LIVE_API_BASE_URL as string | undefined) ?? "";

export class ExtractPromoteApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly body: ExtractPromoteErrorBody | null;

  constructor(
    message: string,
    status: number,
    code: string | null = null,
    body: ExtractPromoteErrorBody | null = null,
  ) {
    super(message);
    this.name = "ExtractPromoteApiError";
    this.status = status;
    this.code = code;
    this.body = body;
  }
}

async function parseJsonBody<T>(response: Response): Promise<T> {
  const text = await response.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new ExtractPromoteApiError(
      `API response is not valid JSON (HTTP ${response.status}).`,
      response.status,
    );
  }
}

async function extractPromoteFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!response.ok) {
    let detail = response.statusText;
    let code: string | null = null;
    let body: ExtractPromoteErrorBody | null = null;
    try {
      body = await parseJsonBody<ExtractPromoteErrorBody>(response);
      if (typeof body.message === "string" && body.message.trim()) {
        detail = body.message;
      }
      if (typeof body.code === "string" && body.code.trim()) {
        code = body.code;
      }
    } catch {
      // Keep status text.
    }
    throw new ExtractPromoteApiError(detail, response.status, code, body);
  }
  return parseJsonBody<T>(response);
}

export async function getExtractPromoteStatus(): Promise<ExtractPromoteStatusResponse> {
  return extractPromoteFetch<ExtractPromoteStatusResponse>("/api/live/extract-promote/status");
}

export async function getExactRunReviewPackage(runId: string): Promise<ExactRunReviewPackage> {
  return extractPromoteFetch<ExactRunReviewPackage>(
    `/api/live/extract-promote/runs/${encodeURIComponent(runId)}/review-package`,
  );
}

export async function prepareExtractPromote(
  body: Omit<ExtractPromotePrepareRequest, "schema"> & {
    schema?: ExtractPromotePrepareRequest["schema"];
  },
): Promise<ExtractPromotePrepareResponse> {
  const payload: ExtractPromotePrepareRequest = {
    schema: "dmb_extract_promote_prepare_request_v2",
    runId: body.runId,
    ...(body.nodeIds != null ? { nodeIds: body.nodeIds } : {}),
  };
  return extractPromoteFetch<ExtractPromotePrepareResponse>("/api/live/extract-promote/prepare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function confirmExtractPromote(
  body: Omit<ExtractPromoteConfirmRequest, "schema"> & {
    schema?: ExtractPromoteConfirmRequest["schema"];
  },
): Promise<ExtractPromoteConfirmReceipt> {
  const payload: ExtractPromoteConfirmRequest = {
    schema: "dmb_extract_promote_confirm_request_v2",
    reviewPackage: body.reviewPackage,
    assertionIds: body.assertionIds,
  };
  return extractPromoteFetch<ExtractPromoteConfirmReceipt>("/api/live/extract-promote/confirm", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function prepareFirstWorldGraph(
  body: Omit<FirstWorldGraphPrepareRequest, "schema"> & {
    schema?: FirstWorldGraphPrepareRequest["schema"];
  },
): Promise<FirstWorldGraphPlan> {
  const payload: FirstWorldGraphPrepareRequest = {
    schema: "dmb_first_world_graph_prepare_request_v1",
    runId: body.runId,
    decisions: body.decisions,
  };
  return extractPromoteFetch<FirstWorldGraphPlan>(
    "/api/live/extract-promote/worldbuilding/first-world/prepare",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export async function confirmFirstWorldGraph(
  body: Omit<FirstWorldGraphConfirmRequest, "schema"> & {
    schema?: FirstWorldGraphConfirmRequest["schema"];
  },
): Promise<FirstWorldGraphConfirmReceipt> {
  const payload: FirstWorldGraphConfirmRequest = {
    schema: "dmb_first_world_graph_confirm_request_v1",
    plan: body.plan,
  };
  return extractPromoteFetch<FirstWorldGraphConfirmReceipt>(
    "/api/live/extract-promote/worldbuilding/first-world/confirm",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}
