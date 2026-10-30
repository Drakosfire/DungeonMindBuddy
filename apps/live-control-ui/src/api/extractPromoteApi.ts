/**
 * Product client for extract → World Supergraph promote (PR011A2 + PR011A3).
 */

import type {
  ExactRunReviewPackage,
  RecapEvidenceCorrectionResponse,
  ExactRunEvidenceCorrectionResponse,
  WorldbuildingEvidenceCorrectionRequest,
  WorldbuildingFrozenSpanCatalog,
  ExactRunEvidenceQuoteCorrection,
  ExtractPromoteConfirmReceipt,
  ExtractPromoteConfirmRequest,
  ExtractPromoteErrorBody,
  ExtractPromotePrepareRequest,
  ExtractPromotePrepareResponse,
  FirstWorldGraphConfirmReceipt,
  FirstWorldGraphConfirmRequest,
  FirstWorldGraphPlan,
  FirstWorldGraphPrepareRequest,
} from "./types";

import { authenticatedApiFetch } from "./liveApi";

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

async function extractPromoteFetch<T>(path: string, init?: RequestInit, authenticated = false): Promise<T> {
  const response = authenticated ? (await authenticatedApiFetch(path, init)).response : await fetch(`${baseUrl}${path}`, {
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

export async function getExactRunReviewPackage(runId: string): Promise<ExactRunReviewPackage> {
  return extractPromoteFetch<ExactRunReviewPackage>(
    `/api/live/extract-promote/runs/${encodeURIComponent(runId)}/review-package`,
  );
}

export async function getWorldbuildingFrozenSpans(runId: string): Promise<WorldbuildingFrozenSpanCatalog> {
  return extractPromoteFetch<WorldbuildingFrozenSpanCatalog>(
    `/api/live/extract-promote/runs/${encodeURIComponent(runId)}/frozen-source-spans`);
}

export async function correctExactRunEvidence(input: WorldbuildingEvidenceCorrectionRequest): Promise<ExactRunEvidenceCorrectionResponse> {
  return extractPromoteFetch<ExactRunEvidenceCorrectionResponse>(
    `/api/live/extract-promote/runs/${encodeURIComponent(input.parentRunId)}/evidence-corrections`,
    {
      method: "POST",
      body: JSON.stringify(input),
    },
  );
}

/** Only this recap mutation uses the authenticated GM transport. */
export async function correctRecapRunEvidence(input: {
  parentRunId: string;
  parentCandidateSha256: string;
  corrections: ExactRunEvidenceQuoteCorrection[];
}): Promise<RecapEvidenceCorrectionResponse> {
  const { response } = await authenticatedApiFetch(
    `/api/live/extract-promote/runs/${encodeURIComponent(input.parentRunId)}/recap-evidence-corrections`,
    { method: "POST", body: JSON.stringify({ schema: "dmb_exact_run_evidence_correction_request_v1", ...input }) },
  );
  if (!response.ok) {
    let body: ExtractPromoteErrorBody | null = null;
    try { body = await parseJsonBody<ExtractPromoteErrorBody>(response); } catch { /* HTTP remains authoritative. */ }
    throw new ExtractPromoteApiError(body?.message || `Quote correction failed (HTTP ${response.status}).`,
      response.status, body?.code ?? null, body);
  }
  const result = await parseJsonBody<RecapEvidenceCorrectionResponse>(response);
  const digest = (value: unknown) => typeof value === "string" && /^(?:sha256:)?[a-f0-9]{64}$/.test(value);
  if (result?.schema !== "dmb_recap_evidence_correction_response_v1"
    || result.status !== "reviewable" || typeof result.runId !== "string" || !result.runId.trim()
    || result.runId === input.parentRunId || result.parentRunId !== input.parentRunId
    || result.parentCandidateSha256 !== input.parentCandidateSha256
    || !digest(result.candidateSha256) || !digest(result.correctionDigest)
    || !digest(result.semanticBasisSha256) || !["held", "accepted", "rejected"].includes(result.semanticState)) {
    throw new ExtractPromoteApiError("The correction receipt could not be verified. Recover the saved request deliberately.", 0);
  }
  return result;
}

export async function prepareExtractPromote(
  body: Omit<ExtractPromotePrepareRequest, "schema"> & {
    schema?: ExtractPromotePrepareRequest["schema"];
  },
): Promise<ExtractPromotePrepareResponse> {
  const payload: ExtractPromotePrepareRequest = {
    schema: "dmb_extract_promote_prepare_request_v2",
    runId: body.runId,
    managedWorldId: body.managedWorldId,
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
    true,
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
    true,
  );
}
